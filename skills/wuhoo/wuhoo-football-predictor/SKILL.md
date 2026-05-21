---
name: wuhoo-football-predictor
description: 足球赛事预测系统 — Elo+Poisson+Monte Carlo v2.3，6层模型栈，支持 2026 世界杯全流程模拟 + 伤病/教练因子 + 中文 Markdown 综合报告
version: 2.3.0
dependencies:
  - wuhoo-news-rss
  - pandas
  - numpy
tags: ["wuhoo"]
category: wuhoo
---

# 足球赛事预测系统 v2.3

## 概述

基于 Elo 评分 + Poisson 分布 + Monte Carlo 模拟的多层次预测系统，支持世界杯、欧洲杯等国际赛事。

### 预测模型栈 (6 层)

| 层 | 模型 | 说明 | 类型 |
|------|------|------|------|
| 1 | **ELO 评分** | 基于实力差值的胜负概率 (international-football.net, 64队) | 基础 |
| 2 | **Poisson 分布** | 基于预期进球的比分概率 | 基础 |
| 3 | **伤病扣分** | 真实伤病数据 (injuries.json, 手动维护) | v2.3 |
| 4 | **教练/磨合因子** | 教练 WC 经验 + 阵容稳定性 + 球队化学反应 (team_metadata.json) | v2.3 |
| 5 | **锦标赛形态** | 每队每轮抽取持久 N(0,60) ELO boost, 模拟"状态火热的黑马" | v2.3 |
| 6 | **比赛级扰动** | 动态冷门上界 22% + 每场 N(0,25) 抖动 + 40% 比分扰动 | v2.3 |

### v2.3 更新 (2026-05-21)

**数据管线:**
- ✅ ELO 采集管线完全重写: fetch_elo.py v2.0 — 多源级联 (international-football.net → eloratings.net → static fallback)
- ✅ 64 支球队完整覆盖 (48 WC + 16 非参赛队) — 之前 55 队
- ✅ 队名标准化: USA→United States, 全量 TEAM_ALIASES 去重映射

**模型增强:**
- ✅ 伤病数据集成: injuries.json (7 队 11 名球员, 真实来源 Al Jazeera/BBC)
- ✅ 教练因子 + 阵容磨合: team_metadata.json (20 队, coach/stability/chemistry)
- ✅ 锦标赛级形态因子: 每队抽取持久 N(0,60) form boost
- ✅ 冷门模型增强: 上界 0.18→0.22, 扰动 30%→40%

**工具链:**
- ✅ `fetch_elo.py --diff`: 输出相对现有文件的差异审计
- ✅ `fetch_elo.py --update-static`: Agent 通过 stdin 更新硬编码 fallback

**效果:**
- 冠军分布: Top3 99.4%→92.7%, 夺冠候选 6→10 队
- ELO 数据源: clubelo.com(废弃) → international-football.net(活跃)

### v2.2 更新 (2026-05-21)
- ELO 数据刷新到 2026-05-20 (eloratings.net)
- 动态冷门模型：ELO 差相关冷门概率 (max 18% for equal teams, min 2%)
- ELO 比赛级抖动：每场模拟前对 ELO 添加 N(0,35) 高斯噪声
- 比分扰动增强：20% → 30%
- `--news` 模式：集成 wuhoo-news-rss 新闻情感分析 → ±40 ELO 调整
- 修复: 决赛 runner_up 统计、South Africa 缺失 ELO、RSSConnector 路径解析

### v2.1 更新 (2026-05-02)
- `--report` 模式：生成中文 Markdown 综合报告
- 新增 `data/team_profiles.json` — 48队结构化元数据
- `validate_data()` — 启动时校验数据完整性
- `analyze_group()` — 6条研判规则
- 高海拔(🏔️)和高温(🔥)球场标记

### v2.0 更新 (2026-05-01)
- FIFA 官方 R32 对阵表 + Monte Carlo 全流程 10,000 次模拟
- 12 组分组数据 + 16 球场 Venue 数据库
- KO 平局概率化、约束感知第3名分配、代码复用

## CLI 命令

```bash
# 2026 世界杯全流程模拟
python3.11 wc2026_predict.py --full --sims 5000

# 生成中文综合报告 (Markdown) + --news 集成情感分析
python3.11 wc2026_predict.py --report --sims 5000 --news

# 仅小组赛
python3.11 wc2026_predict.py --groups

# 通用预测 CLI
python3.11 fp_predict.py --predict "Argentina" "France" --tournament worldcup

# 回测
python3.11 fp_predict.py --backtest --tournament worldcup --year 2022

# 更新 ELO 数据
python3.11 scripts/fetch_elo.py --output=data/elo_ratings.json
python3.11 scripts/fetch_elo.py --diff            # 审计变更
python3.11 scripts/fetch_elo.py --source          # 查看数据源
```

## 2026 世界杯预测结果 (v2.3, 2,000 sims, 2026-05-21)

> ⚠️ 基于 international-football.net 2026-05-21 数据 + v2.3 6层模型栈 (含伤病/教练/形态因子)

| 阶段 | 球队 | 概率 |
|------|------|------|
| 🏆 冠军 | Argentina | 41.6% |
| | Spain | 32.2% |
| | France | 18.9% |
| | England | 2.3% |
| | Portugal | 1.9% |
| | Colombia | 1.2% |
| | Netherlands | 0.8% |
| | Ecuador | 0.4% |
| | Brazil | 0.1% |
| | Croatia | 0.1% |
| 🥈 决赛 | France | 63.3% |
| | Argentina | 52.4% |
| | Spain | 41.9% |
| 🏅 四强 | Spain | 85.8% |
| | Argentina | 85.4% |
| | France | 75.9% |
| | Portugal | 36.4% |
| | Colombia | 30.6% |
| | Ecuador | 15.2% |

> v2.3 变更：6层模型栈 → Argentina 超越 Spain。Brazil 因 3 人伤病(-60 ELO)从 13.6%→0.1%。

### 回测基线
- WC 2022: 57.8% 准确率 (64场)
- Euro 2024: 51.0% 准确率 (51场)

## 架构

```
wuhoo-football-predictor/
├── wc2026_predict.py         # 2026世界杯全流程 Monte Carlo (v2.3)
├── fp_predict.py             # 通用预测 CLI
├── scripts/
│   ├── prediction_models.py    # Poisson + Elo + Factor + Ensemble
│   ├── backtest.py             # 回测引擎
│   ├── fetch_data.py           # 数据采集
│   ├── fetch_elo.py            # ELO 评分更新脚本 (v2.0, 多源级联)
│   ├── sentiment_analyzer.py   # 新闻情感分析 + RSS 连接器
│   └── download_data.py        # 历史比赛数据下载
├── data/
│   ├── elo_ratings.json        # 64队 ELO (2100-scale, international-football.net)
│   ├── team_profiles.json      # 48队中英文元数据
│   ├── team_metadata.json      # 20队教练/磨合/阵容 (v2.3)
│   ├── injuries.json           # 伤病数据 (v2.3, 手动维护)
│   ├── venues.json             # 16球场 venue 数据库
│   ├── group_venues.json       # 12组小组赛 venue 映射
│   ├── wc2026_mc_report.json   # MC 模拟 JSON (含 expected_bracket)
│   ├── wc2026_report_*.md      # 综合中文 Markdown 报告
│   ├── international_full.csv  # 8024场国际比赛 (2018+)
│   ├── worldcup_2022_full.csv  # 2022世界杯64场
│   └── euro_2024_full.csv      # 2024欧洲杯51场
├── configs/
│   ├── tournaments.json        # 赛事配置
│   └── weights.json            # 模型权重
├── tests/
│   ├── test_football.py        # 18个单元测试
│   └── test_wc2026_core.py     # 48个核心MC逻辑测试
└── references/
    ├── bracket-2026.md          # 官方对阵表、R32分配算法
    ├── elo-pipeline-status.md   # ELO 管线状态、数据源迁移记录
    └── group-venue-mapping.md   # 小组赛 venue 映射
```

## 模型参数 (v2.3)

| 参数 | 值 | 说明 |
|------|-----|------|
| TOURNAMENT_FORM_SIGMA | 60 | 锦标赛形态 N(0,σ) |
| ELO_JITTER_SIGMA | 25 | 每场比赛 ELO 扰动 |
| SCORE_PERTURBATION | 0.4 | 比分随机扰动概率 |
| UPSET_UPPER_BOUND | 0.22 | 冷门概率上界 |
| UPSET_SLOPE | 0.0003 | 冷门概率衰减率 |
| UPSET_LOWER_BOUND | 0.02 | 冷门概率下界 |
| HOME_ADV_HOST | 60 | 东道主 ELO 加成 |
| HOME_ADV_CONMEBOL | 15 | 南美队小组阶段加成 |

## 伤病数据集成 (v2.3)

文件: `data/injuries.json` — 手动维护，定期通过新闻更新

```json
{
  "Brazil": {
    "total_penalty": -60,
    "players": [{
      "name": "Rodrygo", "status": "OUT", "severity": "core",
      "elo_penalty": -30, "injury": "Torn meniscus + ACL"
    }]
  }
}
```

ELO 扣分体系:
| 状态 | 核心球员 | 重要球员 | 角色球员 |
|:---:|:---:|:---:|:---:|
| OUT (确定缺阵) | -40 | -25 | -15 |
| DOUBTFUL (可能缺阵) | -20 | -15 | -10 |
| MINOR (轻伤) | -10 | -5 | -3 |

## 教练因子 + 阵容磨合 (v2.3)

文件: `data/team_metadata.json` — 20 队手动维护

每队计算: `coach(8×WC次数) + result(冠军+25/决赛+15/...) + stability((保留率-0.5)×40) + chemistry((胜率-0.5)×30)`

示例:
- Argentina +46: Scaloni WC冠军教练 + 稳定阵容 + 高化学反应
- Spain +21: De la Fuente 首次 WC + 极高化学反应 (Euro 2024 冠军班底)
- Brazil +12: Junior 首次 WC + 伤病导致阵容不稳定

## ELO 自动采集管线 (v2.3)

详见 [references/elo-pipeline-status.md](references/elo-pipeline-status.md)

fetch_elo.py v2.0 架构:
```
1. HTTP fetch international-football.net (结构化 HTML, curl 可达)
   ↓ 失败 (429 rate limit)
2. Merge with existing elo_ratings.json (保留手动策划数据)
   ↓
3. STATIC_ELO fallback (64 队, 手动维护, --update-static 更新)
   ↓
输出: elo_ratings.json (向后兼容格式)
```

Agent 更新流程:
```bash
# Agent 通过 web_extract 获取最新数据, 然后:
python3.11 scripts/fetch_elo.py --update-static <<'EOF'
{"Spain": 2165, "Argentina": 2113, ...}
EOF
```

## 已知限制

1. **伤病数据手动维护**: injuries.json 需定期通过新闻手动更新，非自动采集
2. **教练/磨合数据手动维护**: team_metadata.json 需手动更新
3. **RSS 新闻覆盖不均**: 751 条新闻偏重欧洲豪门，非主流球队情感调整为零
4. **fp_predict.py `--full` 为桩代码**: 仅配置了多赛事框架，缺具体赛事的 Bracket 实现
5. **第3名分配 fallback**: 当组合不在 FIFA 495 种映射表中时使用最佳可用队替代
6. **冠军分布仍略集中**: v2.3 Top3 ~93%，真实世界杯有更多冷门

> ✅ 已解决 (v2.3): ELO 半静态管线、无伤病数据、无教练因子、冠军过度集中 — 全部通过 6层模型栈修复。

## 开发陷阱

### R32 pair 追踪 Bug
在 MC 循环中追踪淘汰赛对阵时，必须追踪**完整 pair `(t1, t2)`**，而非单队。

**正确做法**:
```python
r32_slot_pair[slot_id][(t1, t2)] += 1  # 追踪完整对阵
r32_slot_winner[slot_id][winner] += 1  # 分离 winner 追踪
```

### 决赛 runner_up 缺失 Bug (v2.2 修复)
`stage_winners['F'] = {1: champion}` 只存了冠军。修复: `{1: champion, 2: runner_up}`。

### 半决赛 SF 计数错误 (v2.2 修复)
需追踪全部 4 队（2 决赛队 + 2 负方），不仅 winner。验证: C% < F% < SF% 且 SF% < 100%。

### ELO 数据源失效 (v2.3 已修复)
clubelo.com API 已废弃。v2.3 通过 international-football.net + multi-source cascade + STATIC_ELO fallback 彻底解决。fetch_elo.py v2.0 不再依赖任何单一数据源。

### RSSConnector 路径解析
sentiment_analyzer.py 中的 RSSConnector 默认查找 `../news-rss`，实际目录为 `wuhoo-news-rss`。在 possible_paths 中增加 `wuhoo-news-rss` 路径。

### 队名标准化 (v2.3 新增)
不同数据源使用不同国家名 (USA vs United States, Korea vs South Korea)。统一使用 `TEAM_ALIASES` 映射 + `_canonical_name()` 函数。新增数据时必须检查别名表。

### 伤病/元数据集成陷阱 (v2.3 新增)
在 `simulate_one_tournament()` 中，ELO 调整的应用顺序为:
`ELO + elo_adjustments + injury_adjustments + META_ADJUSTMENTS + tournament_form`
顺序不影响最终值但影响调试。所有调整在 tournament_form 之前应用，确保形态因子覆盖所有基础调整。

### 约束分配算法
从独立 slot 频率构建自洽路径时的贪心约束分配:
```python
def constrained_r32_assignment(slot_pairs):
    candidates = sorted(
        [(sid, pair, cnt) for sid, counts in slot_pairs.items()
         for pair, cnt in counts.items()],
        key=lambda x: -x[2])
    assigned, used = {}, set()
    for sid, pair, cnt in candidates:
        if sid in assigned: continue
        if pair[0] in used or pair[1] in used: continue
        assigned[sid] = pair
        used.update(pair)
    return assigned
```

## 新闻情感分析集成

```python
from scripts.sentiment_analyzer import SentimentAnalyzer, RSSConnector

connector = RSSConnector()
news = connector.fetch_football_news(['Arsenal', 'Barcelona'], days_back=7)

analyzer = SentimentAnalyzer()
sentiments = analyzer.analyze_news_batch(news)
# → {'arsenal': 0.028, 'barcelona': 0.000}
```