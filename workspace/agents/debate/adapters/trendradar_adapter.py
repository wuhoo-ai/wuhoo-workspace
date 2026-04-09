#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrendRadar Adapter - 舆情数据适配器

从 TrendRadar 系统获取热点舆情数据。
支持 SQLite 数据库读取和 JSON 文件加载。
"""

import json
import os
import sqlite3
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta


class TrendRadarAdapter:
    """
    TrendRadar 舆情数据适配器

    功能:
    - 从 SQLite DB 读取热点新闻
    - 按股票名称/代码匹配相关舆情
    - 分析市场情绪倾向
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            possible_paths = [
                Path.home() / ".openclaw/data/trendradar",
                Path.home() / ".openclaw/workspace/projects/TrendRadar/output",
                Path("/home/admin/.openclaw/data/trendradar")
            ]

            for path in possible_paths:
                if path.exists():
                    self.data_dir = path
                    break
            else:
                self.data_dir = None

        self.cache: Dict[str, Dict] = {}

    def _find_db(self) -> Optional[Path]:
        """查找最新的 news.db 文件"""
        if not self.data_dir:
            return None

        db_files = list(self.data_dir.glob("**/news.db"))
        if not db_files:
            return None

        # 按修改时间排序，返回最新的
        return max(db_files, key=lambda p: p.stat().st_mtime)

    def _get_db_date(self, db_path: Path) -> Optional[str]:
        """从 DB 路径推断数据日期"""
        # 路径模式: .../2026-04-03/news.db
        parts = db_path.parts
        for part in parts:
            if re.match(r'\d{4}-\d{2}-\d{2}', part):
                return part
        # 返回文件修改日期
        mtime = datetime.fromtimestamp(db_path.stat().st_mtime)
        return mtime.strftime('%Y-%m-%d')

    def _get_trending_news(self, limit: int = 30) -> List[Dict]:
        """从 SQLite DB 获取热点新闻列表"""
        db_path = self._find_db()
        if not db_path:
            return []

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            c.execute("""
                SELECT n.id, n.title, n.platform_id, n.rank, n.url,
                       p.name as platform_name
                FROM news_items n
                JOIN platforms p ON n.platform_id = p.id
                WHERE n.rank <= ?
                ORDER BY n.rank ASC
            """, (limit,))

            rows = c.fetchall()
            result = []
            for row in rows:
                result.append({
                    'title': row['title'],
                    'platform': row['platform_name'],
                    'rank': row['rank'],
                    'url': row['url'],
                })
            conn.close()
            return result
        except Exception as e:
            print(f"TrendRadar DB read error: {e}")
            return []

    def _match_stock_news(self, symbol: str, company_name: Optional[str]) -> List[Dict]:
        """匹配与股票相关的新闻"""
        db_path = self._find_db()
        if not db_path:
            return []

        # 构建搜索关键词
        keywords = []

        # 提取股票简称（去掉交易所后缀）
        if company_name:
            keywords.append(company_name)

        # 尝试从代码推断名称
        code = symbol.replace('.SH', '').replace('.SZ', '').replace('.HK', '')
        keywords.append(code)

        if not keywords:
            return []

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            matched_news = []
            for kw in keywords:
                if len(kw) < 2:
                    continue
                c.execute("""
                    SELECT n.id, n.title, n.platform_id, n.rank, n.url,
                           p.name as platform_name
                    FROM news_items n
                    JOIN platforms p ON n.platform_id = p.id
                    WHERE n.title LIKE ?
                    ORDER BY n.rank ASC
                """, (f'%{kw}%',))

                for row in c.fetchall():
                    matched_news.append({
                        'title': row['title'],
                        'platform': row['platform_name'],
                        'rank': row['rank'],
                        'url': row['url'],
                        'matched_keyword': kw,
                    })

            conn.close()
            # 去重（按 title）
            seen = set()
            unique_news = []
            for item in matched_news:
                if item['title'] not in seen:
                    seen.add(item['title'])
                    unique_news.append(item)
            return unique_news
        except Exception as e:
            print(f"TrendRadar stock match error: {e}")
            return []

    def _analyze_market_sentiment(self) -> Dict:
        """分析整体市场情绪（基于热点分类）"""
        news_list = self._get_trending_news(50)
        if not news_list:
            return {'score': 0.0, 'label': 'unavailable', 'topics': []}

        # 正面关键词
        positive_keywords = ['增长', '上涨', '突破', '新高', '利好', '基金重仓', '获配',
                           '创新', '领先', '成功', '大单', '暴涨', '强势']
        # 负面关键词
        negative_keywords = ['下跌', '暴跌', '亏损', '风险', '警告', '制裁', '退市',
                           '违规', '处罚', '暴雷', '减持', '熔断', 'ST']

        pos_count = sum(1 for n in news_list
                       if any(kw in n['title'] for kw in positive_keywords))
        neg_count = sum(1 for n in news_list
                       if any(kw in n['title'] for kw in negative_keywords))

        total = max(len(news_list), 1)
        score = (pos_count - neg_count) / total

        # 提取热点话题
        topics = [n['title'][:15] for n in news_list[:10]]

        return {
            'score': round(score, 3),
            'label': 'positive' if score > 0.1 else ('negative' if score < -0.1 else 'neutral'),
            'positive_count': pos_count,
            'negative_count': neg_count,
            'total_items': len(news_list),
            'topics': topics,
        }

    def get_sentiment_data(self, symbol: str, company_name: Optional[str] = None) -> Dict:
        """
        获取股票舆情数据

        Args:
            symbol: 股票代码
            company_name: 公司名称 (可选，用于更精确匹配)

        Returns:
            舆情数据字典
        """
        cache_key = f"{symbol}_{company_name or 'unknown'}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        db_path = self._find_db()
        if not db_path:
            data = self._fallback_unavailable("TrendRadar 数据目录不存在")
            self.cache[cache_key] = data
            return data

        db_date = self._get_db_date(db_path)
        db_age_days = None
        if db_date:
            try:
                db_dt = datetime.strptime(db_date, '%Y-%m-%d')
                db_age_days = (datetime.now() - db_dt).days
            except ValueError:
                pass

        # 匹配股票相关新闻
        stock_news = self._match_stock_news(symbol, company_name)

        # 获取整体市场情绪
        market_sentiment = self._analyze_market_sentiment()

        # 构建结果
        if stock_news:
            # 有相关新闻
            titles = [n['title'] for n in stock_news]
            sentiment_data = {
                "source": "trendradar_sqlite",
                "data_date": db_date,
                "data_age_days": db_age_days,
                "sentiment_score": market_sentiment['score'],
                "sentiment_label": market_sentiment['label'],
                "stock_news_count": len(stock_news),
                "stock_news": stock_news[:10],
                "hot_topics": market_sentiment['topics'][:5],
                "market_positive_ratio": market_sentiment.get('positive_count', 0) / max(market_sentiment.get('total_items', 1), 1),
                "market_negative_ratio": market_sentiment.get('negative_count', 0) / max(market_sentiment.get('total_items', 1), 1),
                "news_count": market_sentiment.get('total_items', 0),
                "trending_rank": stock_news[0]['rank'] if stock_news else None,
                "last_updated": datetime.now().isoformat(),
            }
        else:
            # 无相关新闻，但提供市场整体情绪作为参考
            sentiment_data = {
                "source": "trendradar_sqlite",
                "data_date": db_date,
                "data_age_days": db_age_days,
                "sentiment_score": market_sentiment['score'],
                "sentiment_label": market_sentiment['label'],
                "stock_news_count": 0,
                "stock_news": [],
                "hot_topics": market_sentiment['topics'][:5],
                "market_positive_ratio": market_sentiment.get('positive_count', 0) / max(market_sentiment.get('total_items', 1), 1),
                "market_negative_ratio": market_sentiment.get('negative_count', 0) / max(market_sentiment.get('total_items', 1), 1),
                "news_count": market_sentiment.get('total_items', 0),
                "trending_rank": None,
                "last_updated": datetime.now().isoformat(),
                "note": f"未找到与 {company_name or symbol} 直接相关的新闻，以下为市场整体情绪",
            }

        # 数据时效性警告
        if db_age_days is not None and db_age_days > 2:
            sentiment_data['data_stale_warning'] = f"数据来自 {db_date}，距今 {db_age_days} 天，可能不是最新"

        self.cache[cache_key] = sentiment_data
        return sentiment_data

    def _fallback_unavailable(self, reason: str) -> Dict:
        """数据不可用时的降级返回"""
        return {
            "source": "trendradar",
            "sentiment_score": 0.0,
            "sentiment_label": "unavailable",
            "hot_topics": [],
            "news_count": 0,
            "positive_ratio": 0,
            "negative_ratio": 0,
            "neutral_ratio": 1,
            "trending_rank": None,
            "last_updated": datetime.now().isoformat(),
            "warning": f"⚠️ 舆情数据不可用: {reason}",
        }

    def get_market_overview(self) -> Dict:
        """获取市场舆情概览（不指定股票）"""
        db_path = self._find_db()
        if not db_path:
            return {"available": False}

        db_date = self._get_db_date(db_path)
        market_sentiment = self._analyze_market_sentiment()
        trending = self._get_trending_news(20)

        return {
            "available": True,
            "data_date": db_date,
            "trending_news": trending,
            "market_sentiment": market_sentiment,
        }

    def get_hot_topics(self, limit: int = 10) -> List[Dict]:
        """获取当前热点话题"""
        news = self._get_trending_news(limit)
        return [
            {"topic": n['title'][:20], "rank": n['rank'], "platform": n['platform'], "url": n['url']}
            for n in news[:limit]
        ]

    def is_available(self) -> bool:
        """检查 TrendRadar 数据是否可用"""
        return self._find_db() is not None

    def get_status(self) -> Dict:
        """获取适配器状态"""
        db_path = self._find_db()
        db_date = self._get_db_date(db_path) if db_path else None
        return {
            "available": db_path is not None,
            "data_dir": str(self.data_dir) if self.data_dir else None,
            "db_path": str(db_path) if db_path else None,
            "data_date": db_date,
            "cache_size": len(self.cache),
        }


if __name__ == "__main__":
    adapter = TrendRadarAdapter()

    print("TrendRadar 状态:", json.dumps(adapter.get_status(), indent=2, ensure_ascii=False))

    print("\n热点话题:")
    topics = adapter.get_hot_topics(5)
    for topic in topics:
        print(f"  #{topic['rank']} [{topic['platform']}] {topic['topic']}")

    print("\n市场概览:")
    overview = adapter.get_market_overview()
    print(json.dumps(overview['market_sentiment'], indent=2, ensure_ascii=False))

    print("\n300151.SZ 舆情:")
    sentiment = adapter.get_sentiment_data("300151.SZ", "振华科技")
    print(json.dumps(sentiment, indent=2, ensure_ascii=False))
