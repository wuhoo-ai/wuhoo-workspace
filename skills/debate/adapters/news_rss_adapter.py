#!/usr/bin/env python3
"""
RSS News Adapter — wuhoo-news-rss 舆情适配器

为辩论系统提供基于 RSS 资讯的舆情评分，与 TrendRadar 互补：
- TrendRadar: 热搜榜单（大家在搜什么）
- wuhoo-news-rss: 资讯内容（大家在关注什么新闻）

数据流:
  wuhoo-news-rss (SQLite FTS5) → 按股票名/公司名搜索 → 情感评分 → DataAggregator 合并
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


# wuhoo-news-rss skill 路径
RSS_SKILL_DIR = Path.home() / "wuhoo-skills" / "wuhoo-news-rss"
RSS_DB_PATH = RSS_SKILL_DIR / "data" / "news.db"


class RSSNewsAdapter:
    """
    RSS 舆情适配器

    功能:
    - 按股票名称/代码在 RSS 数据库中搜索相关新闻
    - 基于标题和摘要匹配计算情感倾向
    - 返回与 TrendRadar 兼容的格式供 DataAggregator 合并
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else RSS_DB_PATH
        self._available = self.db_path.exists()

        if not self._available:
            print(f"[RSSNews] ⚠️ 数据库不存在: {self.db_path}")
            print(f"[RSSNews]    请先运行: /usr/bin/python3.11 {RSS_SKILL_DIR}/src/fetcher.py --fetch")
        else:
            print(f"[RSSNews] ✅ 数据库已就绪: {self.db_path}")

    def is_available(self) -> bool:
        return self._available

    def get_sentiment_data(self, symbol: str, company_name: Optional[str] = None) -> Dict:
        """
        获取指定股票的 RSS 舆情数据

        Args:
            symbol: 股票代码 (如 US.NVDA, HK.00700, 600519)
            company_name: 公司名称 (如 英伟达, 腾讯)

        Returns:
            与 TrendRadar 兼容的舆情数据格式
        """
        if not self._available:
            return self._unavailable_result()

        # 构建搜索关键词列表
        search_terms = self._build_search_terms(symbol, company_name)

        if not search_terms:
            return self._unavailable_result()

        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row

            all_articles = []
            for term in search_terms:
                articles = self._search_by_term(conn, term)
                all_articles.extend(articles)

            # 去重（同一篇文章可能匹配多个关键词）
            seen_links = set()
            unique_articles = []
            for art in all_articles:
                link = art.get("link", "") or art.get("title", "")
                if link not in seen_links:
                    seen_links.add(link)
                    unique_articles.append(art)

            if not unique_articles:
                return self._no_news_result(search_terms)

            # 计算情感评分
            sentiment_score = self._calc_sentiment(unique_articles)
            hot_topics = self._extract_topics(unique_articles)

            # 统计
            categories = {}
            for art in unique_articles:
                cat = art.get("category", "未知")
                categories[cat] = categories.get(cat, 0) + 1

            return {
                "source": "rss_news",
                "sentiment_score": round(sentiment_score, 3),
                "sentiment_label": self._label(sentiment_score),
                "positive_ratio": round(self._positive_ratio(unique_articles), 3),
                "negative_ratio": round(self._negative_ratio(unique_articles), 3),
                "news_count": len(unique_articles),
                "search_terms": search_terms,
                "hot_topics": hot_topics[:5],
                "category_breakdown": categories,
                "last_updated": datetime.now().isoformat(),
                "articles": [
                    {
                        "title": a["title"],
                        "category": a.get("category", ""),
                        "feed_name": a.get("feed_name", ""),
                        "hot_score": a.get("hot_score", 0),
                        "link": a.get("link", ""),
                    }
                    for a in unique_articles[:10]  # 只返回前 10 条摘要
                ],
            }

        except Exception as e:
            print(f"[RSSNews] ⚠️ 查询失败: {e}")
            return self._unavailable_result()
        finally:
            if conn:
                conn.close()

    def _build_search_terms(self, symbol: str, company_name: Optional[str]) -> List[str]:
        """构建搜索关键词"""
        terms = []

        # 1. 公司名（最重要）
        if company_name and len(company_name) > 1:
            terms.append(company_name)

        # 2. 股票代码的有意义的部分
        bare = symbol.upper().replace("US.", "").replace("HK.", "").replace("SH.", "").replace("SZ.", "")
        if bare and len(bare) >= 3:
            terms.append(bare)

        # 3. 去除标点后的公司名（英文）
        if company_name:
            cleaned = company_name.strip()
            if cleaned and cleaned != company_name:
                terms.append(cleaned)

        # 去重保序
        seen = set()
        unique = []
        for t in terms:
            if t and t not in seen and len(t) >= 2:
                seen.add(t)
                unique.append(t)

        return unique

    def _search_by_term(self, conn: sqlite3.Connection, term: str, hours: int = 168) -> List[Dict]:
        """按关键词搜索 RSS 文章（最近 7 天）"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        # 优先使用 FTS5
        try:
            rows = conn.execute("""
                SELECT a.* FROM articles a
                JOIN articles_fts fts ON a.id = fts.rowid
                WHERE articles_fts MATCH ?
                  AND a.fetched_at > ?
                ORDER BY a.hot_score DESC, a.fetched_at DESC
                LIMIT 30
            """, (term, cutoff)).fetchall()
            if rows:
                return [dict(r) for r in rows]
        except Exception:
            pass

        # 降级到 LIKE 搜索
        rows = conn.execute("""
            SELECT * FROM articles
            WHERE (title LIKE ? OR summary LIKE ?)
              AND fetched_at > ?
            ORDER BY hot_score DESC, fetched_at DESC
            LIMIT 30
        """, (f"%{term}%", f"%{term}%", cutoff)).fetchall()

        return [dict(r) for r in rows]

    def _calc_sentiment(self, articles: List[Dict]) -> float:
        """
        基于文章特征计算情感评分 (-1 ~ +1)

        评分因子:
        - 热点评分 > 0 → 正面，< 0 → 负面（通过关键词告警判断）
        - 告警文章 → 通常更重要（可能是重大利好/利空）
        - 多源覆盖 → 重要新闻
        """
        if not articles:
            return 0.0

        scores = []
        for art in articles:
            art_score = 0.0

            # 热点评分归一化 (-1 ~ +1)
            hot = art.get("hot_score", 0)
            if hot > 0:
                # 有热点分数 → 通常正面或中性
                art_score = min(hot / 50.0, 1.0)  # 50 分封顶
            elif art.get("is_alert"):
                # 告警文章 → 中性偏重要
                art_score = 0.1  # 轻微正面（关注度高本身就是信号）
            else:
                art_score = 0.0

            # 多源覆盖加分
            source_count = art.get("source_count", 1)
            if source_count > 1:
                art_score = min(art_score + (source_count - 1) * 0.1, 1.0)

            scores.append(art_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _positive_ratio(self, articles: List[Dict]) -> float:
        """正面文章比例"""
        if not articles:
            return 0.0
        positive = sum(1 for a in articles if a.get("hot_score", 0) > 0 or not a.get("is_alert"))
        return positive / len(articles)

    def _negative_ratio(self, articles: List[Dict]) -> float:
        """负面文章比例（简化：非正面即负面）"""
        return 1.0 - self._positive_ratio(articles)

    def _extract_topics(self, articles: List[Dict]) -> List[str]:
        """提取热点话题（从高热度文章标题中提取）"""
        topics = []
        for art in sorted(articles, key=lambda x: x.get("hot_score", 0), reverse=True)[:5]:
            title = art.get("title", "")
            if title and title != "无标题":
                topics.append(title)
        return topics

    def _label(self, score: float) -> str:
        if score > 0.2:
            return "positive"
        elif score < -0.2:
            return "negative"
        return "neutral"

    def _unavailable_result(self) -> Dict:
        return {
            "source": "rss_news",
            "sentiment_score": 0.0,
            "sentiment_label": "unavailable",
            "news_count": 0,
            "hot_topics": [],
            "positive_ratio": 0,
            "negative_ratio": 0,
            "note": "RSS 资讯不可用",
        }

    def _no_news_result(self, search_terms: List[str]) -> Dict:
        return {
            "source": "rss_news",
            "sentiment_score": 0.0,
            "sentiment_label": "no_news",
            "news_count": 0,
            "hot_topics": [],
            "search_terms": search_terms,
            "positive_ratio": 0,
            "negative_ratio": 0,
            "note": "未找到相关新闻",
        }

    def get_status(self) -> Dict:
        """获取适配器状态"""
        if not self._available:
            return {"available": False, "db_path": str(self.db_path)}

        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            count = conn.execute("SELECT count(*) FROM articles").fetchone()[0]
            alert_count = conn.execute("SELECT count(*) FROM articles WHERE is_alert = 1").fetchone()[0]
            return {
                "available": True,
                "db_path": str(self.db_path),
                "total_articles": count,
                "alert_articles": alert_count,
            }
        except Exception:
            return {"available": False, "db_path": str(self.db_path)}
