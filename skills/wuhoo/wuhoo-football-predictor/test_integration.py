"""
Football Predictor + News RSS 集成测试
验证完整的情感分析管线
"""

import sys
sys.path.insert(0, '.')

from scripts.sentiment_analyzer import SentimentAnalyzer, RSSConnector

# 1. 测试 RSS 连接
print("=" * 60)
print("RSS 集成测试")
print("=" * 60)

connector = RSSConnector()
print(f"✓ 数据库连接：{connector.db_path}")

# 2. 获取最新足球新闻
news = connector.get_latest_football_news(5)
print(f"✓ 获取最新足球新闻：{len(news)} 条")
for n in news:
    print(f"  [{n['source']}] {n['title'][:60]}...")

# 3. 获取球队相关新闻
teams = ['Arsenal', 'Barcelona', 'Real Madrid', 'Bayern']
team_news = connector.fetch_football_news(teams, days_back=7)
print(f"\n✓ 球队相关新闻：{len(team_news)} 条")
for n in team_news[:5]:
    print(f"  [{n['team']}] {n['title'][:50]}... ({n['source']})")

# 4. 情感分析
analyzer = SentimentAnalyzer()
team_sentiments = analyzer.analyze_news_batch(team_news)
print(f"\n✓ 球队情感分析结果：")
for team, score in sorted(team_sentiments.items(), key=lambda x: x[1], reverse=True):
    impact = analyzer.get_sentiment_impact(team, team_sentiments)
    print(f"  {team:15s}: {score:+.3f} → 实力影响 {impact:+.0%}")

# 5. 生成情感报告
print(f"\n{'=' * 60}")
print("情感分析报告")
print(f"{'=' * 60}")
for team in teams:
    score = team_sentiments.get(team.lower(), 0)
    impact = analyzer.get_sentiment_impact(team, team_sentiments)
    
    if score > 0.3:
        status = "🟢 积极"
    elif score > 0:
        status = "🟡 中性偏正"
    elif score > -0.2:
        status = "🟡 中性偏负"
    else:
        status = "🔴 消极"
    
    print(f"  {team:15s} | {status:8s} | {score:+.3f} | Elo 调整 {impact:+.0%}")

print(f"\n✅ 集成测试完成！")

