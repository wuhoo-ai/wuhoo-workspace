"""
新闻情感分析模块 - 增强版
基于关键词词典的足球新闻情感分析，用于评估球队近期新闻情绪
支持对接 wuhoo-news-rss 数据库
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class SentimentAnalyzer:
    """足球新闻情感分析器"""
    
    def __init__(self):
        # 情感关键词词典
        self.positive_words = [
            'win', 'victory', 'triumph', 'brilliant', 'excellent', 'outstanding',
            'dominant', 'impressive', 'confident', 'strong', 'fit', 'ready',
            'return', 'recovered', 'renewed', 'momentum', 'streak', 'form',
            'goal', 'assist', 'clean sheet', 'save', 'penalty',
            'celebrate', 'joy', 'boost', 'surge', 'climb', 'rise'
        ]
        
        self.negative_words = [
            'lose', 'loss', 'defeat', 'injury', 'injured', 'hurt', 'suspended',
            'ban', 'red card', 'foul', 'error', 'mistake', 'poor', 'weak',
            'struggle', 'crisis', 'doubt', 'out', 'absent', 'miss',
            'fatigue', 'tired', 'exhausted', 'blame', 'criticize',
            'controversy', 'scandal', 'fine', 'investigation'
        ]
        
        self.intensity_multipliers = {
            'severely': 1.5, 'heavily': 1.4, 'massively': 1.4,
            'slightly': 0.5, 'marginally': 0.6, 'potentially': 0.7,
            'major': 1.3, 'minor': 0.6, 'serious': 1.3
        }
    
    def analyze_text(self, text: str) -> float:
        """分析单条新闻的情感分数 (-1 到 1)"""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        words = text_lower.split()
        
        score = 0
        for word in words:
            multiplier = self.intensity_multipliers.get(word, 1.0)
            if word in self.positive_words:
                score += 0.3 * multiplier
            elif word in self.negative_words:
                score -= 0.4 * multiplier
        
        if score > 0:
            return min(1.0, score / 3)
        else:
            return max(-1.0, score / 3)
    
    def analyze_news_batch(self, news_items: List[Dict]) -> Dict[str, float]:
        """分析一批新闻，返回每支球队的情感得分"""
        team_scores = {}
        team_counts = {}
        
        for item in news_items:
            team = item.get('team', '').lower()
            if not team:
                continue
            
            title = item.get('title', '')
            content = item.get('content', '')
            text = f"{title} {content}"
            
            score = self.analyze_text(text)
            
            if team not in team_scores:
                team_scores[team] = 0
                team_counts[team] = 0
            
            days_old = self._days_since(item.get('date', ''))
            recency_weight = max(0.3, 1.0 - days_old * 0.1)
            
            team_scores[team] += score * recency_weight
            team_counts[team] += 1
        
        for team in team_scores:
            if team_counts[team] > 0:
                team_scores[team] /= team_counts[team]
        
        return team_scores
    
    def get_sentiment_impact(self, team: str, sentiment_scores: Dict[str, float]) -> float:
        """获取球队新闻情绪对实力的影响系数"""
        score = sentiment_scores.get(team.lower(), 0)
        
        if score < -0.5:
            return -0.15
        elif score < -0.2:
            return -0.08
        elif score < 0:
            return -0.03
        elif score < 0.2:
            return 0.01
        elif score < 0.5:
            return 0.03
        else:
            return 0.05
    
    def _days_since(self, date_str: str) -> int:
        """计算日期距今的天数"""
        if not date_str:
            return 30
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            delta = datetime.now() - date
            return max(0, delta.days)
        except:
            return 30


class RSSConnector:
    """RSS 新闻连接器 - 对接 wuhoo-news-rss 数据库"""
    
    def __init__(self, news_rss_dir: str = None):
        if news_rss_dir is None:
            possible_paths = [
                Path(__file__).parent.parent.parent / "news-rss",
                Path.home() / "wuhoo-workspace" / "skills" / "news-rss",
            ]
            for p in possible_paths:
                if p.exists():
                    news_rss_dir = str(p)
                    break
        
        self.news_rss_dir = Path(news_rss_dir) if news_rss_dir else None
        self.db_path = self.news_rss_dir / "data" / "news.db" if self.news_rss_dir else None
    
    def fetch_football_news(self, teams: List[str], days_back: int = 7) -> List[Dict]:
        """从 news-rss 数据库获取球队相关新闻"""
        if not self.db_path or not self.db_path.exists():
            print(f"⚠️ news-rss 数据库不存在：{self.db_path}")
            return []
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        news_items = []
        for team in teams:
            query = """
                SELECT title, summary, pub_date, feed_name
                FROM articles
                WHERE (title LIKE ? OR summary LIKE ?)
                AND pub_date >= ?
                AND category = '足球'
                ORDER BY pub_date DESC
                LIMIT 20
            """
            search_pattern = f"%{team}%"
            cursor.execute(query, (search_pattern, search_pattern, cutoff_date))
            
            for row in cursor.fetchall():
                news_items.append({
                    'team': team,
                    'title': row['title'],
                    'content': row['summary'] or '',
                    'date': row['pub_date'],
                    'source': row['feed_name']
                })
        
        conn.close()
        return news_items
    
    def get_latest_football_news(self, limit: int = 10) -> List[Dict]:
        """获取最新足球新闻"""
        if not self.db_path or not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT title, summary, pub_date, feed_name
            FROM articles
            WHERE category = '足球'
            ORDER BY pub_date DESC
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'title': row['title'],
                'content': row['summary'] or '',
                'date': row['pub_date'],
                'source': row['feed_name']
            })
        
        conn.close()
        return results


if __name__ == "__main__":
    # 测试情感分析
    analyzer = SentimentAnalyzer()
    
    test_texts = [
        "Messi brilliant victory goal Argentina win",
        "Player injured out with serious knee injury",
        "Team struggle poor form defeat crisis",
        "Excellent performance clean sheet dominant win",
        "Coach criticize error mistake red card ban"
    ]
    
    print("情感分析测试:")
    for text in test_texts:
        score = analyzer.analyze_text(text)
        print(f"  {score:+.2f} - {text}")
    
    # 测试 RSS 连接
    print("\nRSS 连接测试:")
    connector = RSSConnector()
    print(f"  数据库路径：{connector.db_path}")
    
    if connector.db_path and connector.db_path.exists():
        news = connector.get_latest_football_news(3)
        print(f"  最新足球新闻：{len(news)} 条")
        for n in news:
            print(f"    - {n['title'][:60]}...")
    
    teams = ['Arsenal', 'Barcelona', 'Real Madrid']
    team_news = connector.fetch_football_news(teams, days_back=7)
    print(f"  球队相关新闻：{len(team_news)} 条")

