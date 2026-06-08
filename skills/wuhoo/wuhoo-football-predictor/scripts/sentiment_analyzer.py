"""
新闻情感分析模块 - 增强版 v4.0
基于关键词词典的足球新闻情感分析，用于评估球队近期新闻情绪
v4.0: 支持中文情感分析 (小红书/社区内容) + 英文双通道
支持对接 wuhoo-news-rss 数据库 + xiaohongshu_collector 缓存
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class SentimentAnalyzer:
    """足球新闻情感分析器 v4.0 — 中文+英文双通道，支持同洲代理策略"""

    # Confederation mapping for proxy sentiment strategy
    CONFEDERATIONS = {
        'UEFA': ['Spain', 'France', 'England', 'Portugal', 'Netherlands', 'Germany',
                 'Italy', 'Belgium', 'Croatia', 'Denmark', 'Switzerland', 'Austria',
                 'Norway', 'Sweden', 'Poland', 'Ukraine', 'Serbia', 'Scotland',
                 'Czech Republic', 'Hungary', 'Wales', 'Slovenia', 'Ireland', 'Slovakia'],
        'CONMEBOL': ['Argentina', 'Brazil', 'Colombia', 'Ecuador', 'Uruguay',
                     'Paraguay', 'Peru', 'Venezuela', 'Chile', 'Bolivia'],
        'CAF': ['Senegal', 'Morocco', 'Nigeria', 'Algeria', 'Egypt', 'Ivory Coast',
                'DR Congo', 'Tunisia', 'Cameroon', 'Ghana', 'South Africa', 'Cape Verde'],
        'AFC': ['Japan', 'South Korea', 'Iran', 'Australia', 'Uzbekistan',
                'Saudi Arabia', 'Iraq', 'Jordan', 'Qatar'],
        'CONCACAF': ['Mexico', 'United States', 'Canada', 'Panama', 'Costa Rica',
                     'Haiti', 'Jamaica', 'Curacao'],
        'OFC': ['New Zealand'],
    }

    # Reverse mapping: team → confederation
    TEAM_CONFED = {}
    for confed, teams in CONFEDERATIONS.items():
        for team in teams:
            TEAM_CONFED[team.lower()] = confed

    # Teams most likely to have news coverage (used as confederation proxies)
    CONFED_PROXIES = {
        'UEFA': ['spain', 'france', 'england', 'germany', 'portugal'],
        'CONMEBOL': ['argentina', 'brazil', 'colombia'],
        'CAF': ['senegal', 'morocco', 'egypt'],
        'AFC': ['japan', 'south korea', 'australia'],
        'CONCACAF': ['united states', 'mexico', 'canada'],
        'OFC': ['new zealand'],
    }

    def __init__(self):
        # === 英文情感关键词词典 ===
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

        # === 中文情感关键词词典 (v4.0 新增 - 小红书/社区中文内容) ===
        self.zh_positive = [
            # 状态/实力
            '状态火热', '势不可挡', '王者归来', '王者之师', '不可战胜',
            '攻无不克', '无懈可击', '如日中天', '士气高涨', '气势如虹',
            '实力碾压', '统治级', '绝对统治', '碾压', '完胜', '大胜',
            # 球员/阵容
            '伤愈复出', '阵容齐整', '全主力', '最强阵', '满员出战',
            '核心回归', '大腿回归', '王牌出战', '定海神针', '杀手锏',
            # 前景/预测
            '夺冠热门', '头号热门', '稳了', '冠军相', '黑马相',
            '有望夺冠', '势在必得', '信心满满', '来势汹汹',
            # 教练/战术
            '战术得当', '用兵如神', '调教有方', '妙手回春',
            # 团队氛围
            '众志成城', '团结一致', '上下一心', '更衣室和谐',
            # 社区热度
            '热搜', '刷屏', '出圈', '爆火',
        ]

        self.zh_negative = [
            # 状态/实力
            '状态低迷', '状态堪忧', '一落千丈', '一蹶不振', '溃不成军',
            '不堪一击', '形同虚设', '漏洞百出', '防守漏勺', '弱不禁风',
            # 伤病/阵容
            '伤病困扰', '伤兵满营', '伤病潮', '核心缺阵', '主力缺阵',
            '伤停', '因伤缺席', '赛季报销', '带伤出战', '勉强出战',
            '阵容不整', '残阵', '缺兵少将',
            # 前景/预测
            '夺冠无望', '没戏了', '凉了', '爆冷出局', '一轮游',
            '前景堪忧', '不被看好', '陪跑',
            # 教练/战术
            '战术混乱', '用兵失误', '指挥不当', '换人失误',
            # 团队氛围
            '内讧', '不和', '矛盾', '将帅失和', '更衣室危机',
            '内部动荡', '士气低落', '军心涣散',
            # 外部因素
            '争议判罚', '黑哨', '误判', '争议',
        ]

        # 中文强度修饰词
        self.zh_intensity = {
            '非常': 1.5, '极其': 1.6, '超级': 1.5, '极度': 1.5,
            '略微': 0.5, '稍微': 0.5, '有点': 0.6, '略显': 0.6,
            '严重': 1.4, '重大': 1.3, '致命': 1.5, '毁灭性': 1.6,
        }

    def _is_chinese(self, text: str) -> bool:
        """检测文本是否为中文为主"""
        if not text:
            return False
        cn_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        return cn_chars > len(text) * 0.15  # 15%以上中文字符

    def analyze_text_cn(self, text: str) -> float:
        """分析中文文本的情感分数 (-1 到 1) — v4.0 新增
        
        使用子串匹配而非分词，因为中文没有空格分隔。
        """
        if not text:
            return 0.0

        score = 0.0
        hits = 0

        # 正向关键词匹配
        for kw in self.zh_positive:
            count = text.count(kw)
            if count > 0:
                score += 0.3 * count
                hits += count

        # 负向关键词匹配
        for kw in self.zh_negative:
            count = text.count(kw)
            if count > 0:
                score -= 0.4 * count
                hits += count

        # 强度修饰词
        for mod, mult in self.zh_intensity.items():
            if mod in text:
                score *= mult

        if abs(score) < 0.01:
            return 0.0

        # 归一化
        if score > 0:
            return min(1.0, score / max(hits * 0.3, 1))
        else:
            return max(-1.0, score / max(hits * 0.3, 1))

    def analyze_text(self, text: str) -> float:
        """分析单条新闻的情感分数 (-1 到 1)
        
        v4.0: 自动检测语言，中文走 analyze_text_cn，英文走原有逻辑。
        """
        if not text:
            return 0.0

        if self._is_chinese(text):
            return self.analyze_text_cn(text)

        # 英文原有逻辑
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

    def get_proxy_sentiment(self, team: str, sentiment_scores: Dict[str, float]) -> float:
        """v2.3: 对无新闻球队使用同洲代理策略。
        
        优先级：
        1. 球队有直接新闻 → 返回直接情感
        2. 球队无新闻但有同洲代理 → 返回同洲强队的中位数情感 × 0.5（衰减）
        3. 完全无数据 → 返回 0（中性）
        """
        direct = sentiment_scores.get(team.lower())
        if direct is not None and direct != 0:
            return direct

        confed = self.TEAM_CONFED.get(team.lower())
        if not confed:
            return 0.0

        proxies = self.CONFED_PROXIES.get(confed, [])
        proxy_scores = []
        for proxy in proxies:
            if proxy == team.lower():
                continue
            score = sentiment_scores.get(proxy)
            if score is not None and score != 0:
                proxy_scores.append(score)

        if not proxy_scores:
            return 0.0

        proxy_scores.sort()
        median = proxy_scores[len(proxy_scores) // 2]
        return round(median * 0.5, 3)

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
                Path(__file__).parent.parent.parent / "wuhoo-news-rss",
                Path.home() / "wuhoo-workspace" / "skills" / "wuhoo" / "wuhoo-news-rss",
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


class XHSConnector:
    """小红书数据连接器 v4.0 — 对接 xiaohongshu_collector 缓存
    
    从小红书采集缓存中读取中文社区讨论数据，
    转换为与 RSSConnector 兼容的格式供情感分析使用。
    """

    def __init__(self, cache_path: str = None):
        if cache_path is None:
            cache_path = Path(__file__).parent.parent / "data" / "xhs_sentiment_cache.json"
        self.cache_path = Path(cache_path)

    def fetch_football_news(self, teams: List[str], days_back: int = 7) -> List[Dict]:
        """从小红书缓存获取球队相关讨论"""
        if not self.cache_path or not self.cache_path.exists():
            print(f"📱 XHS cache not found: {self.cache_path}")
            return []

        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception as e:
            print(f"📱 XHS cache load error: {e}")
            return []

        news_items = []

        # 读取球队级数据
        team_news = cache.get('team_news', {})
        for team in teams:
            items = team_news.get(team, [])
            for item in items:
                news_items.append({
                    'team': team,
                    'title': item.get('title', ''),
                    'content': item.get('description', ''),
                    'date': item.get('date', ''),
                    'source': f"小红书/{item.get('keyword', '世界杯')}",
                })

        # 读取通用关键词数据 (无特定球队标记，尝试从标题匹配)
        keyword_news = cache.get('keyword_news', [])
        for item in keyword_news:
            title = item.get('title', '')
            desc = item.get('description', '')
            text = f"{title} {desc}"

            # 尝试匹配球队名
            matched_teams = []
            for team in teams:
                team_lower = team.lower()
                if team_lower in text.lower():
                    matched_teams.append(team)

            if matched_teams:
                for team in matched_teams:
                    news_items.append({
                        'team': team,
                        'title': title,
                        'content': desc,
                        'date': item.get('date', ''),
                        'source': f"小红书/{item.get('keyword', '关键词')}",
                    })

        return news_items

    def get_latest_football_news(self, limit: int = 10) -> List[Dict]:
        """获取最新小红书足球讨论"""
        news = self.fetch_football_news([], days_back=30)
        # 去重按 title
        seen = set()
        unique = []
        for item in news:
            key = item['title'][:50]
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique[:limit]

    def is_fresh(self, max_age_hours: int = 24) -> bool:
        """检查缓存是否新鲜"""
        if not self.cache_path.exists():
            return False
        try:
            with open(self.cache_path) as f:
                cache = json.load(f)
            collected = cache.get('collected_at', '')
            if not collected:
                return False
            collected_dt = datetime.fromisoformat(collected)
            age = datetime.now() - collected_dt
            return age.total_seconds() < max_age_hours * 3600
        except Exception:
            return False


if __name__ == "__main__":
    # 测试情感分析
    analyzer = SentimentAnalyzer()

    # 英文测试
    print("=== 英文情感分析测试 ===")
    test_texts_en = [
        "Messi brilliant victory goal Argentina win",
        "Player injured out with serious knee injury",
        "Team struggle poor form defeat crisis",
        "Excellent performance clean sheet dominant win",
        "Coach criticize error mistake red card ban"
    ]
    for text in test_texts_en:
        score = analyzer.analyze_text(text)
        print(f"  {score:+.2f} - {text}")

    # 中文测试
    print("\n=== 中文情感分析测试 ===")
    test_texts_cn = [
        "阿根廷状态火热，梅西王者归来，阵容齐整夺冠热门",
        "巴西伤病困扰，核心缺阵，内马尔赛季报销前景堪忧",
        "法国队更衣室危机，姆巴佩与主帅不和，内部动荡",
        "德国队势不可挡，战术得当用兵如神，头号热门稳了",
        "英格兰状态低迷不堪一击，后防漏洞百出，不被看好",
        "日本队士气高涨，三笘薫伤愈复出，黑马相十足",
    ]
    for text in test_texts_cn:
        score = analyzer.analyze_text(text)
        print(f"  {score:+.2f} - {text}")

    # RSS 连接测试
    print("\n=== RSS 连接测试 ===")
    connector = RSSConnector()
    print(f"  数据库路径：{connector.db_path}")
    if connector.db_path and connector.db_path.exists():
        news = connector.get_latest_football_news(3)
        print(f"  最新足球新闻：{len(news)} 条")

    # XHS 连接测试
    print("\n=== 小红书连接测试 ===")
    xhs = XHSConnector()
    print(f"  缓存路径：{xhs.cache_path}")
    print(f"  缓存新鲜度：{'✅ 24h内' if xhs.is_fresh(24) else '⚠️ 过期或不存在'}")
    if xhs.cache_path.exists():
        news = xhs.fetch_football_news(['Argentina', 'France', 'Brazil'], days_back=30)
        print(f"  球队讨论：{len(news)} 条")
