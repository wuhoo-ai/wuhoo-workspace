#!/usr/bin/env python3
"""
v5.0 非结构化信号提取器 (Unstructured Signal Extractor)
=======================================================
从 RSS 文章和网络评论中提取结构化足球比赛信号。

核心创新:
1. 使用 LLM (deepseek-v4-pro) 从聚合文本中提取因果信号
2. 支持中英文双语
3. 按 signal_type × novelty × consensus 加权
4. 信号缓存 + 增量更新

Usage:
  python3.11 scripts/unstructured_extractor.py --date 2026-06-18
  python3.11 scripts/unstructured_extractor.py --teams "Spain,Cape Verde" --news
  python3.11 scripts/unstructured_extractor.py --test  # 单元测试
"""

import sys
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# ── Project root ───────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

# ── Constants ──────────────────────────────────────────────
SIGNAL_TYPES = {
    "injury_impact": {
        "label_cn": "伤病影响",
        "direction": "signed",
        "default_weight": 0.30,
        "description": "伤病对球队实力的实质性影响"
    },
    "tactical_matchup": {
        "label_cn": "战术克制",
        "direction": "signed",
        "default_weight": 0.25,
        "description": "两队战术风格的克制关系"
    },
    "form_momentum": {
        "label_cn": "状态势头",
        "direction": "signed",
        "default_weight": 0.20,
        "description": "近期真实状态 (区别于热身赛成绩)"
    },
    "team_cohesion": {
        "label_cn": "团队氛围",
        "direction": "signed",
        "default_weight": 0.15,
        "description": "更衣室/团队化学反应/将帅关系"
    },
    "lineup_surprise": {
        "label_cn": "阵容变动",
        "direction": "signed",
        "default_weight": 0.20,
        "description": "首发阵容的意外调整或关键球员缺席"
    },
    "external_factor": {
        "label_cn": "外部因素",
        "direction": "signed",
        "default_weight": 0.10,
        "description": "天气/裁判/场地/旅行/政治因素"
    },
    "discipline_risk": {
        "label_cn": "纪律风险",
        "direction": "negative",
        "default_weight": 0.05,
        "description": "关键球员的黄牌/红牌风险"
    }
}

# ── LLM Prompt Design (中英双语) ──────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are a professional football analyst specializing in World Cup match prediction. 
Your task is to extract STRUCTURED signals from news articles that could affect match outcomes.

## Signal Types to Extract

For each team mentioned, identify these signal types:

1. **injury_impact** — Injuries affecting key players, their severity, and expected impact
2. **tactical_matchup** — How the team's style matches up against specific opponents  
3. **form_momentum** — Real match form beyond just results (e.g., "winning but playing poorly")
4. **team_cohesion** — Dressing room atmosphere, coach-player relationships, internal conflicts
5. **lineup_surprise** — Unexpected lineup changes, players benched, surprise inclusions
6. **external_factor** — Weather, referee assignments, travel fatigue, venue altitude/temperature
7. **discipline_risk** — Key players at risk of suspension, history of cards

## Scoring Rules

For each signal:
- **direction**: -1 (hurts team), 0 (neutral/uncertain), +1 (helps team)
- **strength**: 0.0-1.0 (how confident is this signal?)
- **novelty**: 0.0-1.0 (is this NEW info not already reflected in ELO/fifa rankings?)
  - 0.0 = "everyone knows this" (e.g., "Argentina has Messi")
  - 0.5 = "somewhat known but underappreciated"  
  - 1.0 = "brand new development" (e.g., sudden injury, surprise lineup change)
- **consensus**: 0.0-1.0 (how many independent sources report this?)
  - 0.3 = single source, unverified
  - 0.7 = 2-3 sources confirming
  - 1.0 = widespread agreement across 4+ sources
- **affected_opponent**: null or team name (for tactical_matchup signals)
- **key_quote**: A direct quote or paraphrase from the article that supports this signal (max 100 chars)

## Critical Rules

1. ONLY output signals with strength >= 0.3. Weak/ambiguous signals waste attention.
2. ONLY output signals where you have EVIDENCE in the text. Do NOT fabricate.
3. Distinguish between CONSENSUS info (already in ELO) and NOVEL info (not yet priced in).
4. If multiple articles describe the same event, merge into ONE signal with higher consensus.
5. Output ONLY valid JSON. No markdown, no explanations outside the JSON.

## Output Format (JSON)

{
  "teams": {
    "TeamName": {
      "signals": [...]
    }
  }
}
"""

EXTRACTION_USER_PROMPT_TEMPLATE = """Analyze the following World Cup news articles and extract structured signals for each team mentioned.

## Teams of Interest
{team_list}

## News Articles (titles + summaries)
{articles_text}

## Instructions
For EACH of the teams listed above, extract ALL relevant signals from the articles.

Return JSON following the format described, with signals per team.
"""


# ── RSS Database Connector ─────────────────────────────────

class RSSFeedConnector:
    """连接 wuhoo-news-rss SQLite 数据库，按球队拉取文章"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            possible = [
                PROJECT_DIR.parent / "wuhoo-news-rss" / "data" / "news.db",
                Path.home() / "wuhoo-workspace" / "skills" / "wuhoo" / "wuhoo-news-rss" / "data" / "news.db",
            ]
            for p in possible:
                if p.exists():
                    db_path = str(p)
                    break
        
        self.db_path = db_path
        self._conn = None
    
    @property
    def conn(self):
        if self._conn is None and self.db_path:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def is_available(self) -> bool:
        return bool(self.db_path and Path(self.db_path).exists())
    
    def fetch_team_articles(self, teams: List[str], days_back: int = 3, 
                            category: str = "足球") -> List[Dict]:
        """Fetch articles mentioning any of the given teams."""
        if not self.is_available():
            print(f"⚠️ RSS DB not found: {self.db_path}")
            return []
        
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        articles = []
        seen_ids = set()
        
        for team in teams:
            # Search both exact team name and Chinese/alternative names
            patterns = [team]
            # Add common variations
            name_variations = TEAM_NAME_VARIATIONS.get(team, [])
            patterns.extend(name_variations)
            
            for pattern in patterns:
                query = """
                    SELECT id, title, summary, pub_date, feed_name, link, category
                    FROM articles
                    WHERE (title LIKE ? OR summary LIKE ?)
                    AND pub_date >= ?
                    AND category = ?
                    ORDER BY pub_date DESC
                    LIMIT 15
                """
                try:
                    cursor = self.conn.execute(query, (f"%{pattern}%", f"%{pattern}%", cutoff, category))
                    for row in cursor.fetchall():
                        if row['id'] not in seen_ids:
                            seen_ids.add(row['id'])
                            articles.append({
                                'id': row['id'],
                                'title': row['title'],
                                'summary': row['summary'] or '',
                                'pub_date': row['pub_date'] or '',
                                'feed_name': row['feed_name'],
                                'link': row['link'] or '',
                            })
                except Exception as e:
                    print(f"⚠️ DB query error for {pattern}: {e}")
        
        return articles


# ── Team name variations for search ────────────────────────

TEAM_NAME_VARIATIONS = {
    'South Korea': ['韩国', 'Korea'],
    'Czech Republic': ['捷克', 'Czechia'],
    'United States': ['USA', '美国', 'USMNT'],
    'Netherlands': ['荷兰', 'Holland'],
    'Japan': ['日本'],
    'Germany': ['德国'],
    'Spain': ['西班牙'],
    'France': ['法国'],
    'Argentina': ['阿根廷'],
    'Brazil': ['巴西'],
    'England': ['英格兰'],
    'Portugal': ['葡萄牙'],
    'Belgium': ['比利时'],
    'Croatia': ['克罗地亚'],
    'Uruguay': ['乌拉圭'],
    'Colombia': ['哥伦比亚'],
    'Morocco': ['摩洛哥'],
    'Senegal': ['塞内加尔'],
    'Egypt': ['埃及'],
    'Iran': ['伊朗'],
    'Saudi Arabia': ['沙特', '沙特阿拉伯'],
    'Qatar': ['卡塔尔'],
    'Australia': ['澳大利亚', '澳洲'],
    'Canada': ['加拿大'],
    'Mexico': ['墨西哥'],
    'Scotland': ['苏格兰'],
    'Sweden': ['瑞典'],
    'Norway': ['挪威'],
    'Austria': ['奥地利'],
    'Switzerland': ['瑞士'],
    'Turkey': ['土耳其', 'Turkiye'],
    'Paraguay': ['巴拉圭'],
    'Ecuador': ['厄瓜多尔'],
    'Ivory Coast': ['科特迪瓦', 'Cote d\'Ivoire'],
    'Ghana': ['加纳'],
    'Tunisia': ['突尼斯'],
    'Algeria': ['阿尔及利亚'],
    'Nigeria': ['尼日利亚'],
    'Cameroon': ['喀麦隆'],
    'South Africa': ['南非'],
    'Cape Verde': ['佛得角'],
    'DR Congo': ['民主刚果', '刚果', '刚果民主'],
    'Iraq': ['伊拉克'],
    'Jordan': ['约旦'],
    'Uzbekistan': ['乌兹别克斯坦', '乌兹别克'],
    'New Zealand': ['新西兰'],
    'Panama': ['巴拿马'],
    'Haiti': ['海地'],
    'Curacao': ['库拉索'],
}


# ── Main Extractor Class ───────────────────────────────────

class UnstructuredExtractor:
    """非结构化信号提取器 v5.0
    
    工作流:
    1. 从 RSS DB 拉取目标球队的相关文章
    2. 聚合文章 (每队最多 3K tokens 文本)
    3. 调用 LLM 提取结构化信号
    4. 缓存结果到 data/signal_cache/
    """
    
    def __init__(self, db_path: str = None, signal_cache_dir: str = None):
        self.rss = RSSFeedConnector(db_path)
        
        if signal_cache_dir is None:
            signal_cache_dir = PROJECT_DIR / "data" / "signal_cache"
        self.cache_dir = Path(signal_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_for_teams(self, teams: List[str], match_date: str = None) -> Dict:
        """为指定球队提取信号。核心入口。
        
        Args:
            teams: 球队名列表 (英文规范名)
            match_date: 比赛日期 (YYYY-MM-DD)，用于缓存键
        
        Returns:
            {
                "teams": {team: {"signals": [...], "article_count": N}},
                "meta": {"extracted_at": "...", "source_count": N}
            }
        """
        # 1. Check cache
        cache_key = self._cache_key(teams, match_date)
        cached = self._load_cache(cache_key)
        if cached:
            print(f"📦 信号缓存命中: {cache_key}")
            return cached
        
        # 2. Fetch articles from RSS DB
        articles = self.rss.fetch_team_articles(teams, days_back=7)
        if not articles:
            print(f"⚠️ 未找到相关文章: {teams}")
            return self._empty_result(teams)
        
        # 3. Group articles by team
        team_articles = defaultdict(list)
        for art in articles:
            text = f"{art['title']} {art['summary']}"
            for team in teams:
                team_lower = team.lower()
                if team_lower in text.lower():
                    team_articles[team].append(art)
                    break
        
        # 4. Prepare text for LLM (per team, limit tokens)
        articles_text = ""
        for art in articles[:50]:  # Max 50 articles total
            src = art.get('feed_name', '?')
            date = art.get('pub_date', '?')[:10]
            title = art.get('title', '')[:200]
            summary = art.get('summary', '')[:400]
            articles_text += f"[{src} | {date}] {title}\n{summary}\n\n"
        
        # Truncate to ~8K chars (~2K tokens)
        if len(articles_text) > 8000:
            articles_text = articles_text[:8000] + "...[truncated]"
        
        # 5. Build prompt
        team_list = "\n".join(f"- {t}" for t in teams)
        prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
            team_list=team_list,
            articles_text=articles_text
        )
        
        # 6. Call LLM (handled by caller — we return the prompt + articles)
        #    The actual LLM call is done by the agent using this module's output
        
        result = {
            "teams": {team: {"articles": team_articles.get(team, [])} for team in teams},
            "meta": {
                "extracted_at": datetime.now().isoformat(),
                "total_articles": len(articles),
                "teams_with_articles": sum(1 for t in teams if team_articles.get(t)),
                "prompt": prompt,
                "system_prompt": EXTRACTION_SYSTEM_PROMPT,
                "needs_llm_call": True,
            }
        }
        
        # 7. Cache the intermediate result (pre-LLM)
        self._save_cache(cache_key, result)
        
        print(f"📰 已聚合 {len(articles)} 篇文章, 覆盖 {result['meta']['teams_with_articles']}/{len(teams)} 队")
        return result
    
    def merge_llm_response(self, cache_key: str, llm_json: Dict) -> Dict:
        """Merge LLM-extracted signals back into the cached result."""
        cached = self._load_cache(cache_key)
        if not cached:
            print(f"⚠️ 缓存未找到: {cache_key}")
            return llm_json
        
        # Merge signals into team data
        llm_teams = llm_json.get('teams', {})
        for team, data in cached.get('teams', {}).items():
            signals = llm_teams.get(team, {}).get('signals', [])
            data['signals'] = signals
            data['signal_count'] = len(signals)
        
        cached['meta']['llm_extracted_at'] = datetime.now().isoformat()
        cached['meta']['needs_llm_call'] = False
        cached['meta']['total_signals'] = sum(
            len(data.get('signals', [])) for data in cached.get('teams', {}).values()
        )
        
        self._save_cache(cache_key, cached)
        return cached
    
    def _cache_key(self, teams: List[str], match_date: str = None) -> str:
        """Generate cache key."""
        date = match_date or datetime.now().strftime('%Y-%m-%d')
        teams_sorted = '-'.join(sorted(t.replace(' ', '_') for t in teams))
        return f"{date}_{teams_sorted}"
    
    def _cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"
    
    def _load_cache(self, cache_key: str) -> Optional[Dict]:
        path = self._cache_path(cache_key)
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def _save_cache(self, cache_key: str, data: Dict):
        path = self._cache_path(cache_key)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _empty_result(self, teams: List[str]) -> Dict:
        return {
            "teams": {team: {"signals": [], "articles": [], "signal_count": 0} for team in teams},
            "meta": {
                "extracted_at": datetime.now().isoformat(),
                "total_articles": 0,
                "teams_with_articles": 0,
                "needs_llm_call": False,
            }
        }


# ── CLI ────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description='v5.0 非结构化信号提取器')
    parser.add_argument('--teams', type=str, help='Comma-separated team names')
    parser.add_argument('--date', type=str, help='Match date (YYYY-MM-DD)')
    parser.add_argument('--test', action='store_true', help='Run unit tests')
    parser.add_argument('--output', type=str, help='Output JSON file path')
    args = parser.parse_args()
    
    if args.test:
        run_tests()
        return
    
    extractor = UnstructuredExtractor()
    
    if args.teams:
        teams = [t.strip() for t in args.teams.split(',')]
        result = extractor.extract_for_teams(teams, args.date)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"✅ 已保存: {args.output}")
        else:
            # Print summary
            for team, data in result.get('teams', {}).items():
                n_articles = len(data.get('articles', []))
                n_signals = data.get('signal_count', 0)
                print(f"  {team}: {n_articles} articles, {n_signals} signals")
    else:
        print("Usage: python3.11 scripts/unstructured_extractor.py --teams 'Spain,Cape Verde'")
        print("       python3.11 scripts/unstructured_extractor.py --test")


def run_tests():
    """单元测试"""
    print("=" * 60)
    print("v5.0 UnstructuredExtractor 单元测试")
    print("=" * 60)
    
    # Test 1: RSS Feed Connector
    print("\n📋 Test 1: RSSFeedConnector availability")
    rss = RSSFeedConnector()
    print(f"  DB path: {rss.db_path}")
    print(f"  Available: {rss.is_available()}")
    assert rss.is_available(), "RSS DB should be available"
    print("  ✅ PASS")
    
    # Test 2: Team article fetch
    print("\n📋 Test 2: fetch_team_articles")
    if rss.is_available():
        articles = rss.fetch_team_articles(['Spain', 'Cape Verde'], days_back=10)
        print(f"  Spain/Cape Verde articles (10d): {len(articles)}")
        spain_arts = [a for a in articles if 'Spain' in (a['title'] + a['summary'])[:200]]
        cv_arts = [a for a in articles if 'Cape Verde' in (a['title'] + a['summary'])[:200]]
        print(f"    Spain-specific: {len(spain_arts)}")
        print(f"    Cape Verde-specific: {len(cv_arts)}")
        assert len(articles) > 0, "Should find articles about Spain-Cape Verde"
        print("  ✅ PASS")
    
    # Test 3: Extractor end-to-end (without LLM call)
    print("\n📋 Test 3: UnstructuredExtractor.extract_for_teams")
    extractor = UnstructuredExtractor()
    result = extractor.extract_for_teams(['Spain', 'Cape Verde'], '2026-06-16')
    print(f"  Teams with articles: {result['meta']['teams_with_articles']}")
    print(f"  Total articles: {result['meta']['total_articles']}")
    print(f"  Needs LLM call: {result['meta']['needs_llm_call']}")
    
    # Verify prompt
    prompt = result['meta'].get('prompt', '')
    print(f"  Prompt length: {len(prompt)} chars")
    assert 'Spain' in prompt, "Prompt should mention Spain"
    assert 'Cape Verde' in prompt, "Prompt should mention Cape Verde"
    assert result['meta']['total_articles'] > 0, "Should have articles"
    print("  ✅ PASS")
    
    # Test 4: Cache persistence
    print("\n📋 Test 4: Cache persistence")
    cache_key = extractor._cache_key(['Spain', 'Cape Verde'], '2026-06-16')
    cached = extractor._load_cache(cache_key)
    print(f"  Cache key: {cache_key}")
    print(f"  Cache exists: {cached is not None}")
    assert cached is not None, "Cache should exist after extract_for_teams"
    print("  ✅ PASS")
    
    # Test 5: LLM response merge
    print("\n📋 Test 5: merge_llm_response")
    mock_llm = {
        "teams": {
            "Spain": {
                "signals": [
                    {
                        "type": "injury_impact",
                        "direction": -1,
                        "strength": 0.7,
                        "novelty": 0.8,
                        "consensus": 0.9,
                        "description_cn": "多名评论员指出西班牙后防伤病影响进攻组织",
                        "key_quote": "西班牙缺乏渗透力，Cape Verde防守纪律性极强"
                    }
                ]
            },
            "Cape Verde": {
                "signals": [
                    {
                        "type": "form_momentum",
                        "direction": 1,
                        "strength": 0.6,
                        "novelty": 0.9,
                        "consensus": 0.7,
                        "description_cn": "门将沃齐尼亚状态极佳，非洲杯场均失0.6球",
                        "key_quote": "佛得角门将7次扑救获评全场最佳"
                    }
                ]
            }
        }
    }
    merged = extractor.merge_llm_response(cache_key, mock_llm)
    spain_signals = merged['teams']['Spain'].get('signals', [])
    cv_signals = merged['teams']['Cape Verde'].get('signals', [])
    print(f"  Spain signals: {len(spain_signals)}")
    print(f"  Cape Verde signals: {len(cv_signals)}")
    print(f"  LLM extracted: {merged['meta'].get('llm_extracted_at', 'N/A')}")
    assert len(spain_signals) == 1, "Spain should have 1 signal"
    assert len(cv_signals) == 1, "Cape Verde should have 1 signal"
    print("  ✅ PASS")
    
    # Test 6: Empty result for unknown teams
    print("\n📋 Test 6: Empty result handling")
    empty = extractor.extract_for_teams(['UnknownTeamX', 'FakeTeamY'])
    print(f"  Total articles: {empty['meta']['total_articles']}")
    print(f"  Needs LLM call: {empty['meta']['needs_llm_call']}")
    assert empty['meta']['total_articles'] == 0, "Should have 0 articles"
    print("  ✅ PASS")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)


if __name__ == '__main__':
    main()
