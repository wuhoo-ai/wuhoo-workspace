---
name: wuhoo-football-predictor
description: 足球赛事预测系统 — Elo+Poisson+Monte Carlo v2.1，支持 2026 世界杯全流程模拟 + 中文 Markdown 综合报告
version: 2.1.0
dependencies:
  - wuhoo-news-rss
  - pandas
  - numpy
tags: ["wuhoo"]
category: wuhoo
---

# 足球赛事预测系统 v2.1

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

### v2.1 更新 (2026-05-02)
- ✅ `--report` 模式：生成中文 Markdown 综合报告（48队简介 + 分组分析 + 淘汰赛路径 + 比分预测）
- ✅ 新增 `data/team_profiles.json` — 48队结构化元数据（中英文名、FIFA排名、世界杯历史）
- ✅ `validate_data()` — 启动时校验 ELO/Profiles/Venues 数据完整性
- ✅ `analyze_group()` — 6条研判规则（绝对热门/死亡之组/争2白热化/东道主优势/黑马信号/送分队）
- ✅ `expected_score()` — 确定性预期比分（无随机扰动）
- ✅ 概率加权最大似然淘汰赛路径（R32→Final 完整对阵表 + 每场比分）
- ✅ 高海拔(🏔️)和高温(🔥)球场标记
- 🔧 R32 pair 追踪 Bug 修复 (slot 间单队→完整对阵 pair)

## CLI 命令

```bash
# 2026 世界杯全流程模拟
python3.11 wc2026_predict.py --full --sims 10000

# 生成中文综合报告 (Markdown)
python3.11 wc2026_predict.py --report --sims 10000

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

## 2026 世界杯预测结果 (v2.1, 10,000 sims, 2026-05-02)

| 阶段 | 球队 | 概率 |
|------|------|------|
| 🏆 冠军 | Argentina | 54.4% |
| | France | 32.1% |
| | Brazil | 13.4% |
| 🥈 亚军 | France | 32.1% |
| | Brazil | 13.4% |
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

> v2.1 变更：加入 3% 冷门扰动因子 + 约束分配路径 + 分离 Poisson/MC 决赛展示

### 回测基线
- WC 2022: 57.8% 准确率 (64场)
- Euro 2024: 51.0% 准确率 (51场)

## 架构

详见 [references/bracket-2026.md](references/bracket-2026.md) — 完整官方对阵表、第三名分配算法、模型参数。

```
wuhoo-football-predictor/
├── wc2026_predict.py       # 2026世界杯全流程 Monte Carlo (v2.1)
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
│   ├── team_profiles.json    # 48队中英文元数据 (v2.1)
│   ├── venues.json           # 16球场 venue 数据库
│   ├── wc2026_mc_report.json # MC 模拟 JSON (含 expected_bracket)
│   ├── wc2026_report_*.md    # 综合中文 Markdown 报告 (v2.1)
│   ├── international_full.csv # 8024场国际比赛 (2018+)
│   ├── worldcup_2022_full.csv # 2022世界杯64场
│   └── euro_2024_full.csv    # 2024欧洲杯51场
├── configs/
│   ├── tournaments.json      # 赛事配置
│   └── weights.json          # 模型权重
├── tests/
│   └── test_football.py      # 18个单元测试
└── .hermes/plans/            # 开发计划 (v2.1)
    └── 2026-05-02_180000-wc2026-report-enhancement.md
```

## 已知限制

1. **Top 3 集中度高**: 仅 Argentina/France/Brazil 夺冠（>99.9%），ELO 差异主导 —— 🔧 v2.1 已加入 3% 冷门扰动因子，效果温和但未根本改变
2. **无实时新闻集成**: 赛前伤病/状态新闻未接入 Monte Carlo
3. **无阵容/伤病数据**: 纯基于 ELO + 历史统计数据
4. **第3名分配 fallback**: 当组合不在 FIFA 495 种映射表中时使用最佳可用队替代
5. **ELO 静态**: 未在锦标赛期间动态更新
6. **无阵容磨合/教练因子**: 球队化学反应、战术体系未建模
7. **小组赛 venue 未建模**: 仅淘汰赛阶段应用 venue 惩罚
8. ~~概率加权路径不自洽~~ → ✅ v2.1 已修复：约束分配算法确保同一球队不跨 slot
9. ~~决赛比分-冠军矛盾~~ → ✅ v2.1 已修复：Poisson 预期(90min)与 MC 冠军(含加时)分开展示
10. **小组出线过度确定**: v2.1 冷门因子使弱队出线率从 0% → 0.3%~6.6%，但仍高度确定（top2 仍是 100%）

## 开发陷阱

### R32 pair 追踪 Bug
在 MC 循环中追踪淘汰赛对阵时，必须追踪**完整 pair `(t1, t2)`**，而非单队。使用单队会导致：
- `r32_slot_team[slot_id][team] += 1` → 只能取该 slot 最频繁的单队
- 报告渲染时对阵表显示 "韩国 vs ..." 缺少对手名

**正确做法**（已修复）:
```python
r32_slot_pair[slot_id][(t1, t2)] += 1  # 追踪完整对阵
r32_slot_winner[slot_id][winner] += 1  # 分离 winner 追踪
```
同样适用于 R16/QF/SF 的 pair 追踪。**Final 的 pair 和 winner 必须用独立的 dict**，避免混用 `defaultdict(int)` 中的 tuple key 和 str key 导致 `most_frequent()` 取出错误类型。

### 约束分配算法 (P2 fix)
从独立 slot 频率构建自洽路径时，如果每 slot 独立取 `most_frequent`，同一球队可能出现在多个 slot（如 Iran 同时出现在 Slot 6 和 13）。解决方案：贪心约束分配：

```python
def constrained_r32_assignment(slot_pairs):
    candidates = []
    for slot_id, pair_counts in slot_pairs.items():
        for pair, count in pair_counts.items():
            candidates.append((slot_id, pair, count))
    candidates.sort(key=lambda x: -x[2])  # 最高频优先
    
    assigned = {}
    used_teams = set()
    for slot_id, pair, count in candidates:
        if slot_id in assigned: continue
        t1, t2 = pair
        if t1 in used_teams or t2 in used_teams: continue
        assigned[slot_id] = pair
        used_teams.add(t1); used_teams.add(t2)
    return assigned
```

此模式适用于任何需要从频次统计中提取自洽路径的 bracket 类模拟。

### 决赛展示分离 (P3 fix)
Poisson `expected_score()` 返回的 `score` 是最可能 90 分钟比分（可为平局），而 `run_monte_carlo()` 返回的 `final_winner` 来自 MC 概率化 KO 打破。两者是独立概念，**必须在报告中分开展示**：
- Poisson → "90 分钟预期比分"
- MC → "含加时+点球的冠军预测"

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
