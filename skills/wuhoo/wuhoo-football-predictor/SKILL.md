---
name: wuhoo-football-predictor
description: 足球赛事预测系统 — Elo+Poisson+Monte Carlo v2.0，支持 2026 世界杯全流程模拟
version: 2.0.0
dependencies:
  - wuhoo-news-rss
  - pandas
  - numpy
tags: ["wuhoo"]
category: wuhoo
---

# 足球赛事预测系统 v2.0

## 概述

基于 Elo 评分 + Poisson 分布 + Monte Carlo 模拟的多层次预测系统，支持世界杯、欧洲杯等国际赛事。

### 预测模型栈

| 模型 | 说明 | 权重 |
|------|------|------|
| Poisson 分布 | 基于预期进球的比分概率 | 30% |
| Elo 评分 | 基于实力差值的胜负概率 | 35% |
| 多因子模型 | 近期状态、交锋记录、进球能力 | 20% |
| 新闻情绪 | 对接 wuhoo-news-rss | 15% |

### v2.0 更新 (2026-05-01)
- ✅ FIFA 官方 R32 对阵表 (Yahoo Sports 来源)
- ✅ Monte Carlo 扩展到淘汰赛（全流程 10,000 次模拟）
- ✅ 完整第3名排序规则 (pts > GD > GF)
- ✅ 约束感知的第3名 R32 分配算法
- ✅ ELO 统一到国家队 2100-scale (55 队)
- ✅ 官方 12 组分组数据 (FIFA 2025-12-05 抽签)
- ✅ 16球场 Venue 数据库 (海拔 + 气候惩罚)
- ✅ KO 平局概率化 (非确定性强队胜)
- ✅ 代码复用：wc2026_predict.py 引入 prediction_models

## CLI 命令

```bash
# 2026 世界杯全流程模拟
python3.11 wc2026_predict.py --full --sims 10000

# 仅小组赛
python3.11 wc2026_predict.py --groups

# 通用预测 CLI
python3.11 fp_predict.py --predict "Brazil" "Germany" --tournament worldcup

# 回测
python3.11 fp_predict.py --backtest --tournament worldcup --year 2022

# 查看球队新闻情绪
python3.11 fp_predict.py --news "Argentina"

# 更新 ELO 数据
python3.11 scripts/fetch_elo.py --output=data/elo_ratings.json
```

## 2026 世界杯预测结果 (10,000 sims)

| 阶段 | 球队 | 概率 |
|------|------|------|
| 🏆 冠军 | Argentina | 54.8% |
| | France | 31.8% |
| | Brazil | 13.3% |
| 🥈 亚军 | Argentina | 54.8% |
| | France | 31.8% |
| | Brazil | 13.3% |
| 🏅 四强 | Argentina | 99.8% |
| | France | 67.8% |
| | Brazil | 30.1% |
| | Portugal | 2.0% |
| 🏟️ 八强 | Argentina | 100.0% |
| | France | 100.0% |
| | Brazil | 90.3% |
| | England | 79.9% |
| | Belgium | 11.1% |
| | Portugal | 9.9% |
| | Spain | 8.6% |

### 回测基线
- WC 2022: 57.8% 准确率 (64场)
- Euro 2024: 51.0% 准确率 (51场)

## 架构

详见 [references/bracket-2026.md](references/bracket-2026.md) — 完整官方对阵表、第三名分配算法、模型参数。

```
wuhoo-football-predictor/
├── wc2026_predict.py       # 2026世界杯全流程 Monte Carlo (v2.0)
├── fp_predict.py           # 通用预测 CLI
├── scripts/
│   ├── prediction_models.py  # Poisson + Elo + Factor + Ensemble
│   ├── backtest.py           # 回测引擎
│   ├── fetch_data.py         # 数据采集 (CSV + clubelo.com)
│   ├── fetch_elo.py          # Elo 评分更新脚本
│   ├── sentiment_analyzer.py # 新闻情感分析 + RSS 连接器
│   └── download_data.py      # 历史比赛数据下载
├── data/
│   ├── elo_ratings.json      # 55队 Elo (2100-scale)
│   ├── wc2026_mc_report.json # MC 模拟完整报告
│   ├── international_full.csv # 8024场国际比赛 (2018+)
│   ├── worldcup_2022_full.csv # 2022世界杯64场
│   └── euro_2024_full.csv    # 2024欧洲杯51场
├── configs/
│   ├── tournaments.json      # 赛事配置
│   └── weights.json          # 模型权重
└── tests/
    └── test_football.py      # 18个单元测试
```

## 已知限制

1. **Top 3 集中度高**: 仅 Argentina/France/Brazil 夺冠，ELO 差异仍主导，缺少冷门因子
2. **无实时新闻集成**: 赛前伤病/状态新闻未接入 Monte Carlo
3. **无阵容/伤病数据**: 纯基于 ELO + 历史统计数据
4. **第3名分配 fallback**: 当组合不在 FIFA 495 种映射表中时使用最佳可用队替代
5. **ELO 静态**: 未在锦标赛期间动态更新
6. **无阵容磨合/教练因子**: 球队化学反应、战术体系未建模
7. **小组赛 venue 未建模**: 仅淘汰赛阶段应用 venue 惩罚

## 新闻情感分析集成

```python
from scripts.sentiment_analyzer import SentimentAnalyzer, RSSConnector

# 获取球队新闻
connector = RSSConnector()
news = connector.fetch_football_news(['Arsenal', 'Barcelona'], days_back=7)

# 情感分析
analyzer = SentimentAnalyzer()
sentiments = analyzer.analyze_news_batch(news)
# → {'arsenal': 0.028, 'barcelona': 0.000}

# 实力影响系数
impact = analyzer.get_sentiment_impact('Arsenal', sentiments)
# → 0.01 (即 +1% Elo 调整)
```
