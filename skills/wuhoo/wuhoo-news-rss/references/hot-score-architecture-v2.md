# Hot Score Architecture v2.0 (2026-07-03)

## Problem

Before v2.0, `hot_score` was always 0.0 for all 32,406 articles. Root causes:

1. **Keyword list too narrow** — only 40-50 keywords (量化交易/AI/芯片/电商), insufficient coverage
2. **Exact title matching for multi-source** — `all_titles.count(title)` almost never matched
3. **`insert_article` omitted score columns** — the SQL INSERT didn't include `hot_score`, `is_alert`, `alert_keywords` even though `calc_hot_score()` computed them correctly

## Solution: Three-layer Scoring

### Layer 1: Feed Base Weight (1-10)
Each feed has a baseline score based on quality/signal density:

```python
feed_weights = {
    "Financial Times": 10, "Seeking Alpha": 9, "华尔街见闻": 9,
    "IT之家": 7, "36氪": 7, ...
    "BBC Sport Football": 0,  # football = zero weight in investment briefings
}
```

### Layer 2: Keyword Enhancement (+3 per match)
`EXPANDED_KEYWORDS` list of 200+ keywords across 8 categories:
- Quantitative/trading, AI/LLM, semicon/chips, ecommerce/cross-border
- Market/macro (inflation, Fed, tariff, sanction), company/financials (earnings, IPO, M&A)
- Tech/industry (autonomous, EV, robot, blockchain, quantum)
- Individual stocks (腾讯, 阿里, Apple, Microsoft, Tesla...)
- Industry hot spots (新能源, solar, biotech, real estate)

Word boundary matching (`\b`) prevents substring false positives:
```python
pattern = re.compile(r'\b' + re.escape(kw_lower) + r'\b', re.IGNORECASE)
```

### Layer 3: Fuzzy Multi-source Coverage (+8 per extra source)
```python
def _fuzzy_normalize(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r'^(it之家\s*\d+\s*月\s*\d+\s*日\s*消息[，,]?)', '', t)
    t = re.sub(r'^36氪获悉[，,]?', '', t)
    t = re.sub(r'[：:，,。！!？?\s]+', ' ', t)
    return t.strip()[:40]
```

Uses `collections.Counter` to find how many sources covered the same event.

## Critical Pitfall: `insert_article` Column Mismatch

The hardest bug: `calc_hot_score()` returned correct scores, but DB had all zeros.

**Root cause**: `insert_article` INSERT statement lacked hot_score columns:

```sql
-- BROKEN (v1.x):
INSERT OR IGNORE INTO articles (feed_name, ..., hash)
VALUES (?, ..., ?)

-- FIXED (v2.0):
INSERT OR IGNORE INTO articles (feed_name, ..., hash, hot_score, is_alert, alert_keywords)
VALUES (?, ..., ?, ?, ?, ?)
```

**Debugging technique**: Test `calc_hot_score()` in isolation first:
```bash
/usr/bin/python3.11 -c "
import sys; sys.path.insert(0, 'src'); import fetcher
config = fetcher.load_config()
s, h = fetcher.calc_hot_score(
    {'title':'NVIDIA发布GPU', 'summary':'芯片'},
    {'name':'IT之家'},
    fetcher.load_alert_keywords(config),
    fetcher.load_feed_weights(config)
)
print(f'Score: {s}, Hits: {h}')
"
```

If the function returns correct scores but DB shows zero → check the INSERT statement.

## RSSNewsAdapter DB Path Fix

Also in v2.0: the adapter had a wrong DB path:
```python
# BROKEN:
RSS_SKILL_DIR = Path.home() / "wuhoo-workspace" / "skills" / "news-rss"
# FIXED:
RSS_SKILL_DIR = Path.home() / "wuhoo-workspace" / "skills" / "wuhoo" / "wuhoo-news-rss"
```

This meant the debate pipeline's 50% RSS sentiment weight was always returning 0.0 because it couldn't find the database.

## Verification After Fix

```bash
# Check score distribution
/usr/bin/python3.11 -c "
import sqlite3
conn = sqlite3.connect('data/news.db')
r = conn.execute(\"SELECT hot_score>0, count(*) FROM articles GROUP BY 1\").fetchall()
print(r)  # Should show both True and False counts
r2 = conn.execute(\"SELECT count(*) FROM articles WHERE is_alert=1\").fetchone()
print(f'Alerts: {r2[0]}')  # Should be > 0
conn.close()
"

# Test adapter
/usr/bin/python3.11 -c "
import sys; sys.path.insert(0, '.../wuhoo-debate/adapters')
from news_rss_adapter import RSSNewsAdapter
a = RSSNewsAdapter()
r = a.get_sentiment_data('US.NVDA', '英伟达')
print(f'Score: {r[\"sentiment_score\"]}, News: {r[\"news_count\"]}')
"
```
