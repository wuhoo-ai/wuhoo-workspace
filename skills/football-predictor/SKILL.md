---
name: football-predictor
description: 足球赛事预测系统 - 新闻情感分析集成模块（对接 wuhoo-news-rss）
version: 1.1.0
dependencies:
  - wuhoo-news-rss
  - pandas
  - numpy
---

## 新闻情感分析集成

football-predictor 已对接 wuhoo-news-rss 数据库，实现实时新闻情感分析：

```
wuhoo-news-rss (9 个足球 RSS 源)
  ↓ SQLite (data/news.db)
football-predictor/sentiment_analyzer.py
  ↓ 情感分析 (-1 ~ +1)
预测模型 Elo 调整 (±15%)
```

### 可用足球 RSS 源

| 源名称 | 状态 | 类别 |
|--------|------|------|
| BBC Sport Football | ✅ 85 条 | 英超 |
| Sky Sports Football | ✅ 20 条 | 英超/转会 |
| The Guardian Football | ✅ 53 条 | 英超/欧冠 |
| ESPN Football | ❌ 解析失败 | - |
| FIFA/UEFA | ❌ 解析失败 | - |
| 懂球帝/直播吧 | ❌ RSSHub 路由不可用 | - |

### 使用示例

```python
from scripts.sentiment_analyzer import SentimentAnalyzer, RSSConnector

# 获取球队新闻
connector = RSSConnector()
news = connector.fetch_football_news(['Arsenal', 'Barcelona'], days_back=7)

# 情感分析
analyzer = SentimentAnalyzer()
sentiments = analyzer.analyze_news_batch(news)
# 输出：{'arsenal': 0.028, 'barcelona': 0.000}

# 获取实力影响系数
impact = analyzer.get_sentiment_impact('Arsenal', sentiments)
# 输出：0.01 (即 +1% Elo 调整)
```
