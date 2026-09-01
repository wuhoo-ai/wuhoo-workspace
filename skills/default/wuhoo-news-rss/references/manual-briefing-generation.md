# Manual RSS Briefing Generation Pattern

Use when the cron push fails (e.g., WeChat gateway timeout) or when you need an on-demand briefing.

## Flow

1. **Fetch**: `python3.11 fetcher.py --fetch`
2. **Multi-query**: For each category, run `--fts "<keywords>" --limit 20 --json`
3. **Dedup + Classify**: Python script with `seen = set()`, topic-specific FTS5 queries
4. **Format**: Markdown report with 4 categories, TOP10 each
5. **Deliver**: Save to file, then send via `send_message` or file

## Category Keywords (2026-05-02 tested)

```
科技/AI: AI OR 人工智能 OR 模型 OR 芯片 OR GPU OR 半导体 OR LLM OR GPT OR OpenAI OR NVIDIA OR 英伟达 OR 量子 OR robot OR 机器人 OR Apple OR 苹果 OR Google OR Microsoft OR agent OR 智能

财经/投资: 股市 OR 港股 OR 美股 OR IPO OR 量化 OR 基金 OR 比特币 OR Bitcoin OR 央行 OR 利率 OR 通胀 OR 关税 OR tariff OR trade OR 期货 OR 黄金 OR oil OR market

宏观政策: 政策 OR 监管 OR 立法 OR 地缘 OR Iran OR 伊朗 OR 特朗普 OR Trump OR Fed OR 美联储 OR 白宫 OR EU OR 欧盟 OR 中国 OR China OR 关税 OR 外交 OR 制裁

产业/公司: 财报 OR 收购 OR 并购 OR 上市 OR IPO OR 裁员 OR launch OR 发布 OR Tesla OR 特斯拉 OR Meta OR Amazon OR 亚马逊 OR 腾讯 OR 阿里 OR BYD OR 台积电 OR TSMC OR 华为 OR SpaceX
```

## Python Script Pattern

```python
from hermes_tools import terminal
import json, re
from datetime import datetime

categories = { ... }  # name → FTS query

all_articles = {}
seen = set()

for cat_name, query in categories.items():
    cmd = f'cd /path/to/news-rss && python3.11 fetcher.py --fts "{query}" --limit 20 --json'
    r = terminal(cmd, timeout=30)
    data = json.loads(r['output'])
    articles = data.get('articles', [])
    
    top10 = []
    for a in articles:
        title = clean_html(a.get('title') or '')
        if not title or title in seen: continue
        seen.add(title)
        
        # Date from pub_date field (NOT 'published')
        pub_date = a.get('pub_date') or a.get('fetched_at', '')
        date = parse_date(pub_date)
        
        summary = clean_html(a.get('summary') or '')[:60]
        
        top10.append({'title': title[:80], 'source': a.get('feed_name'), 
                       'date': date, 'summary': summary})
        if len(top10) >= 10: break
    
    all_articles[cat_name] = top10
```

## Date Parsing

The API returns `pub_date` (not `published`). Format varies by feed source:
- ISO: `2026-05-01T15:41:45.694548`
- Various other formats
- Fallback to `fetched_at`

## Format Rules

- Title **bold**, source *italic*, date appended
- Summary one line, ≤60 chars
- Categories separated by blank line + bold header
- Footer: total articles, unique sources, generation time
- HTML tags stripped from all fields
