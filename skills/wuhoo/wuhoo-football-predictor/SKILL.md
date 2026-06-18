---
name: wuhoo-football-predictor
description: WC2026 单场+全赛事预测系统 v5.0 — Elo+Poisson+Monte Carlo+LLM非结构化信号，8层模型栈，未来N场预测+全中文报告+体彩串关(双策略)+数据保鲜检查+Polymarket交叉验证
version: 5.0.0
dependencies:
  - wuhoo-news-rss
  - pandas
  - numpy
tags: ["wuhoo"]
category: wuhoo
---

# 足球赛事预测系统 v5.0

## 概述

基于 Elo 评分 + Poisson 分布 + Monte Carlo 模拟 + **LLM 非结构化信号** 的多层次预测系统。

### v5.0 更新 (2026-06-18) — 非结构化数据增强重构

- ✅ **新增 RSS 源**: 懂球帝早报 (中文), BBC Sport RSSHub (WC coverage), Breaking The Lines (战术分析) — 12→15 足球源
- ✅ **LLM 信号提取器**: `scripts/unstructured_extractor.py` — 从 RSS 文章聚合文本中用 LLM 提取结构化因果信号
- ✅ **信号融合引擎**: `scripts/signal_fusion.py` — 信号类型×共识度×新颖性×反向增强 → ±120 ELO
- ✅ **战术风格匹配**: 48 队 6 类主+副风格 × 克制矩阵 → 战术匹配度评分
- ✅ **第一轮全量复盘**: `data/round1_lessons.json` — 20 场比赛 307 篇文章, 信号-结果关联分析
- ✅ **Layer 5.5**: 非结构化信号层替换旧 keyword sentiment (±40 ELO), 目标 ±120 ELO
- ✅ **信号缓存**: `data/signal_cache/` — 每日信号持久化, 支持回溯验证
- ⚠️ **LLM 调用**: 当前 extractor 产出的信号需 agent 侧调用 LLM 后 merge_llm_response 回填, layer 5.5 在无 LLM 信号时优雅降级

### v4.5 更新 (2026-06-13) — 数据保鲜检查 + Cron 管线完善

- ✅ **新增保鲜检查脚本**: `scripts/check_football_freshness.py` — 12项数据源 3级阈值
- ✅ **Cron 第0步**: 14:30 管线集成保鲜检查，严重过期标注警告但继续执行
- ✅ **赛果 JSON 结构陷阱**: 文档化 `matches` 键（非 `results`）

### v4.5.1 更新 (2026-06-17) — collect_results 陷阱修复

- ⚠️ **修复**: `collect_results.py --manual` 必须带 JSON 数据，裸调用会静默失败（exit 1），**cron agent 误报「无新比赛结果」**导致 4 场完整比赛数据漏采
- 📄 **新参考**: `references/collect_results_usage.md` — 正确用法 + `--check` 工作流
- 📄 **更新**: `references/daily-pipeline.md` — 校正后的管线步骤（含陷阱说明）
- 🔧 **Cron 5154715032ec**: prompt 需更新为 `--check` → web_search → `--manual '[{...}]'` 模式

### v4.3 更新
### v4.3 更新 (2026-06-11) — 体彩串关 + 竞彩赔率

- ✅ **新增体彩串关投注**: `scripts/lottery_parlay.py` — 全组合枚举分散策略
- ✅ **竞彩赔率模型**: 返奖率 71%，赔率区间 1.01-20.00，60 档标准赔率表
- ✅ **串关 v2.0**: 笛卡尔积枚举所有主/平/客组合 → EV×概率加权 → Top-N 分配
- ✅ **预测管线升级**: `scripts/predict_next_n.py` 覆盖未来 4 场，末尾自动调用串关
- ✅ **全中文报告**: 判定 + xG 行均使用中文队名
- ✅ **跳过策略**: 赔率 < 1.05 且概率 > 90% 的超级热门自动跳过
- ✅ **Cron 调整**: 数据刷新 14:30，赛前预测 15:00，deliver=local,origin
- ⚠️ **技能碰撞问题**: `wuhoo-football-predictor` 同时存在于 `~/.hermes/skills/` 和 `~/wuhoo-workspace/skills/`，导致 cron job 运行时 skill 无法加载（输出 `Skill(s) not found and skipped`）。如需修复，删除 `~/.hermes/skills/wuhoo/wuhoo-football-predictor/` 只保留 workspace 版本。
- 📋 **赛后数据更新流程** → [references/post-match-workflow.md](references/post-match-workflow.md)

| v4.4 更新 (2026-06-12) — 伤病数据刷新+Polymarket交叉验证
|- ✅ **伤病数据大更新**: 从 ESPN/The Athletic 采集 Canada(Davies OUT), USA(Cardoso OUT), Brazil(Neymar/Rodrygo), Netherlands(Timber/Simons) 等9队最新伤病
|- ✅ **injuries.json 格式规范**: 必须使用 `injuries` 键（非 `teams`），每队含 `total_penalty` + `players[]`（name/position/status/injury/elo_penalty），见 `references/injury-format.md`
|- ✅ **热身赛数据补全**: 从 ESPN 补充 USA 14场 + Paraguay 9场，数据源见 `references/friendly-data-collection.md`
|- ✅ **Polymarket 交叉验证**: 使用 Gamma API 查询预测市场赔率并与模型对比，发现 Davies 伤缺被市场定价为 Canada 胜率从94.7%→53.5%
|- ✅ **predict_next_n.py 优化**: --n 2 覆盖未来2场（6.13仅2场），需先 collect_results 后 update_elo_from_results 再预测

| v4.3 更新 (2026-06-11) — 中文报告+体彩串关+竞彩赔率
### v2.0 更新 (2026-06-15) — predict_next_n 结构化重写 + 伤病数据大刷新

- ✅ **predict_next_n v2.0**: 直接调用 `predict_single_match()`（不再 subprocess），保存完整 7 层 audit 到 `daily_predictions/YYYY-MM-DD.json`（含 ELO、伤病、Venue、Poisson、verdict、reasoning）。文件大小从 ~900 bytes → ~9KB (10x)
- ✅ **伤病数据刷新 (6/15)**: `injuries.json` 从 2 队扩展到 18 队（Brazil/Netherlands/Germany/Japan/Morocco/Spain/Argentina/Australia/Scotland/Austria/England/Ghana/Uruguay/France/USA），数据源 ESPN/BBC/Fox Sports。刷新流程见 [references/injury-data-refresh.md](references/injury-data-refresh.md)
- ✅ **SKILL.md 同步**: `~/.hermes` v4.5 → workspace，解决 cron job 加载 SKILL.md 内容过旧问题。但两份副本的 ambiguous 问题仍需最终解决（见已知限制）
- ✅ **Cron 确认**: 14:30 数据刷新 + 15:00 预测 job 均正常运行。WeChat iLink rate limit 导致 15:00 推送偶尔失败，`deliver=local,origin` 确保本地留存

- ✅ **数据保鲜检查**: `scripts/check_football_freshness.py` — 12项数据源 3级阈值，详见 `references/freshness-check-pipeline.md`
- ✅ **Cron 第0步**: 14:30 管线集成保鲜检查，严重过期标注警告但继续执行
- ✅ **串关 v2.2 双策略**: 集中(50元/Top-2) + 全覆盖(50元/Top-8评分分配)，联合概率修正，详见 `references/lottery-parlay-v2.2.md`
- ✅ **predict_next_n v2.0**: 直接调用 `predict_single_match()`（不再 subprocess），保存完整 7 层 audit 到 `daily_predictions/YYYY-MM-DD.json`（含 ELO、伤病、Venue、Poisson、verdict）。文件大小从 ~900 bytes → ~9KB
- ✅ **静态数据全量刷新**: venues/team_profiles/schedule/metadata/group_venues 刷新至当日
- ✅ **伤病数据刷新 (6/15)**: injuries.json 从 2 队扩展到 18 队（Brazil/Netherlands/Germany/Japan/Morocco/Spain/Argentina/Australia/Scotland/Austria/England/Ghana/Uruguay/France/USA），数据源 ESPN/BBC/Fox Sports
- ✅ **保鲜阈值分层**: 核心(1-3d)→赛程(5-14d)→元数据(14-30d)→基础设施(30-60d)
- ✅ **赛程赛果同步**: `wc2026_schedule.json` 自动从 `wc2026_results.json` 同步已完成赛果
- ✅ **赛果 JSON 结构陷阱**: 文档化 `matches` 键（非 `results`）
- ✅ **预检脚本说明**: `pre_match_refresh.py` exit 2 = 警告非致命，非错误

### v4.1 更新 (2026-06-08) — 热身赛数据大刷新

- ✅ **22场新热身赛**: 从 football365/ESPN/BBC 采集，覆盖 Argentina, Portugal, Scotland 等
- ✅ **47/48队覆盖**: 仅 Uruguay 无公开热身赛数据
- ✅ **移除 XHS 双通道**: 小红书采集命中率仅12%，回退至 RSS 单通道

### v3.0 更新 (2026-06-02) — 比赛日单场预测管线

- ✅ **新增单场预测 CLI**: `wc2026_predict.py --match "A" "B"` 带完整 6 层审计链路
- ✅ **赛程数据**: `data/wc2026_schedule.json` — 72 场小组赛完整赛程（含北京时间）
- ✅ **预测历史**: 自动记录到 `data/prediction_history.jsonl`

### 预测模型栈 (7 层) — 架构说明

**关键架构**: 模型采用 **ELO 逐层叠加** 而非集成加权。各层计算 ELO 调整量，直接加到 effective ELO 后输入 Poisson。`configs/weights.json` 仅供 `prediction_models.py` 的 EnsembleModel 路径使用（与主预测管线 `wc2026_predict.py` 不同）。

| 层 | 模型 | ELO 贡献 | 说明 |
|------|------|------|------|
| 1 | **ELO 评分** | 1500-2000 (基底) | 64 队 ELO (international-football.net) |
| 2 | *(Poisson)* | 依赖 effective ELO | 无独立 ELO 调整 |
| 3 | **伤病扣分** | -100 ~ 0 | injuries.json 真实伤病数据 |
| 4 | **教练/磨合因子** | -50 ~ +50 | coach + stability + chemistry (静态 metadata) |
| 4.5 | **热身赛状态** | -50 ~ +50 | 友谊赛结果 vs ELO 期望，指数衰减 |
| 5 | **锦标赛形态** | N(0,60) | 每队一次性抽取持久 boost |
| 6 | **比赛级扰动** | N(0,25) | 每场独立抖动 + 冷门模型 (max 22%) |
| 7 | **新闻情感 (RSS)** | **-12 ~ +37 ELO** ⚠️ | keyword 词典 ±40 上限，实际有效贡献 ~2-3% |

> **注意**: `weights.json` 的 `default.news_sentiment: 0.15` 与主预测管线无关。主管线通过 `load_news_sentiment()` → `get_sentiment_impact()` → `impact × 250` 转换为 ELO 调整值直接加入 effective_elo。`weights.json` 用于 `prediction_models.EnsembleModel`（v4.0 前遗留，现不启用）。

### Round 1 准确率 (截至 2026-06-17)

| 指标 | 值 |
|------|-----|
| 总预测 | 18 场 |
| 正确 | 7 场 |
| 准确率 | 38.9% |
| Brier | 0.9916 (接近随机=1.0) |
| 关键漏判 | Spain 0-0 Cape Verde, Brazil 1-1 Morocco, Netherlands 2-2 Japan, Belgium 1-1 Egypt, Saudi 1-1 Uruguay |

### v5.0 重构计划

详见 `.hermes/plans/2026-06-18_020000-football-predictor-v5-unstructured-data-enhancement.md`：
- 非结构化数据深度利用：LLM 因果信号提取 + 战术匹配 + 中文社区接入
- Layer 7 从 keyword 词典 → LLM 多维信号融合（目标权重 15-25%）

## 数据保鲜检查

每日 14:30 cron 管线第 0 步自动执行。脚本: `scripts/check_football_freshness.py`

```bash
# 完整报告
python3.11 scripts/check_football_freshness.py

# 仅输出问题 (cron 模式)
python3.11 scripts/check_football_freshness.py --quiet

# JSON 输出 (程序消费)
python3.11 scripts/check_football_freshness.py --json
```

### 保鲜阈值

| 类别 | 文件 | 警告 | 严重 | 刷新方式 |
|------|------|------|------|---------|
| 核心实时 | `elo_ratings.json` | 1d | 3d | `fetch_elo.py` |
| 核心实时 | `wc2026_results.json` | 1d | 3d | `collect_results.py` |
| 核心实时 | `injuries.json` | 2d | 5d | 手动维护 |
| 赛程相关 | `wc2026_schedule.json` | 5d | 14d | 含赛果同步 |
| 赛程相关 | `friendly_matches.json` | 5d | 10d | `fetch_friendlies.py` |
| 球队元数据 | `team_metadata.json` | 14d | 30d | 手动刷新 |
| 球队元数据 | `team_profiles.json` | 14d | 30d | 手动刷新 |
| 基础设施 | `venues.json` | 30d | 60d | 静态，赛事期间不变 |
| 基础设施 | `group_venues.json` | 30d | 60d | 静态 |

### 静态文件刷新

赛事基础设施文件（venues、team_profiles、schedule、metadata、group_venues）内容本身在赛事期间不变，但元数据时间戳可能过期。刷新时只需更新 `updated` 字段和元数据 — 不改变核心数据内容。赛程表可同步 `wc2026_results.json` 中的赛果。

## CLI 命令

```bash
# === v2.0: 未来N场预测（结构化输出）===
# 直接调用 predict_single_match()，保存完整 audit 到 JSON
python3.11 scripts/predict_next_n.py --n 4 --news

# 跳过串关
python3.11 scripts/predict_next_n.py --n 4 --no-lottery

# 仅预测今天剩余比赛
python3.11 scripts/predict_next_n.py --all-today-remaining

# 预测结果 JSON 格式 (data/daily_predictions/YYYY-MM-DD.json):
#   matches[].audit.layers.{1_elo_base, 2_injuries, 3_coach_meta, 4_venue, 4.5_friendly_form, 5_news_sentiment, 6_manual}
#   matches[].audit.prediction.{team_a_win, draw, team_b_win, most_likely_score, expected_goals_a, expected_goals_b}
#   matches[].audit.verdict.{result, confidence}
#   matches[].audit.effective_elo.{team_a.effective, team_b.effective, diff}

# === v4.3: 体彩串关投注 ===
# 生成竞彩串关方案（100元预算，竞彩71%返奖率）
python3.11 scripts/lottery_parlay.py --matches 4

# 自定义预算
python3.11 scripts/lottery_parlay.py --matches 4 --budget 200

# 从JSON文件加载（跳过预测步骤）
python3.11 scripts/lottery_parlay.py --json data/daily_predictions/2026-06-12.json

# === v3.0: 比赛日单场预测（核心新增）===
# 预测未来4场比赛（含新闻情感 + 自动生成竞彩串关方案）
python3.11 scripts/predict_next_n.py --n 4 --news

# 跳过串关（仅预测）
python3.11 scripts/predict_next_n.py --n 4 --news --no-lottery

# 仅生成串关方案（从预测数据）
python3.11 scripts/lottery_parlay.py --matches 4

# 自定义预算
python3.11 scripts/lottery_parlay.py --matches 4 --budget 200

# === v3.0: 比赛日单场预测 ===
# 按对阵预测
python3.11 wc2026_predict.py --match "Argentina" "France"

# 跳过串关部分
python3.11 scripts/predict_next_n.py --n 4 --no-lottery

# === v3.0: 比赛日单场预测 ===
python3.11 wc2026_predict.py --match "Argentina" "France"
python3.11 wc2026_predict.py --match-id 1
python3.11 wc2026_predict.py --group A --matchday 1

# === v4.3: 体彩串关单独运行 ===
python3.11 scripts/lottery_parlay.py --matches 4
python3.11 scripts/lottery_parlay.py --budget 200

# === 全赛事模拟 ===
python3.11 wc2026_predict.py --full --sims 5000
python3.11 wc2026_predict.py --report --sims 5000 --news

# === 数据维护 ===
python3.11 scripts/pre_match_refresh.py          # 预测前数据新鲜度检查
python3.11 scripts/fetch_elo.py --diff           # ELO 数据更新
python3.11 scripts/fetch_friendlies.py --compute-form  # 热身赛状态计算
```

## 体彩串关算法 (v4.3, lottery_parlay.py)

### 竞彩赔率模型

```
竞彩赔率 = 1 / 模型概率 × 0.71  (返奖率 71%)
赔率区间: 1.01 (超级热门) ~ 20.00 (超级冷门)
60 档标准赔率表: 1.01, 1.02, 1.03, ... 15.00, 20.00
```

**重要**: 竞彩官方 sporttery.cn / lottery.gov.cn 全部被 EdgeOne WAF 封锁，无公开 API。当前为合成模型，已验证在竞彩真实区间内。

### 串关分散策略 (v2.0)

```
v1.0: 每场选单一最优方向 → 单注全押 → 中奖率 ~25%
v2.0: 枚举所有主/平/客组合 → 笛卡尔积 → EV×概率加权 → Top-N 分配 → 中奖率 ~50-78%
```

跳过逻辑: 赔率 < 1.05 且模型概率 > 90% 的超级热门自动跳过（鸡肋赔率不加回报只加风险）

### 资金分配

按 `score = EV × (概率^0.3)` 加权分配 100 元预算到 Top 4-6 个组合，最低 2 元/注。

## Cron 配置 (2026-06-11, updated 2026-06-13)

### 数据保鲜检查 (v4.5) — 第0步必做

14:30 cron 管线首先执行保鲜检查，确认所有数据源在有效期内。

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-football-predictor
python3.11 scripts/check_football_freshness.py          # 完整报告
python3.11 scripts/check_football_freshness.py --quiet  # 仅问题项（cron用）
```

**保鲜阈值**:
| 类别 | 文件 | 警告/严重 |
|------|------|-----------|
| 核心实时 | ELO、赛果、伤停、预测准确率 | 1-3d / 3-7d |
| 赛程相关 | 赛程表、热身赛 | 3-5d / 7-10d |
| 球队元数据 | 球队档案、元数据 | 7d / 14d |
| 基础设施 | 场馆、小组映射 | 14d / 30d |

**预检脚本**: `scripts/pre_match_refresh.py` 是保鲜检查增强版（含 ELO + 伤病 + 热身赛交叉验证）。exit code 2 = 有警告（非致命），不应阻断后续步骤。

**赛果 JSON 陷阱**: `wc2026_results.json` 使用 `matches` 键（非 `results`）。检查数量用 `len(data['matches'])`。

| Job ID | 名称 | 时间 | 说明 |
|--------|------|------|------|
| `5154715032ec` | 数据刷新+结果采集 | 14:30 | ELO+热身赛+RSS |
| `86912ff0a4aa` | 赛前预测 | 15:00 | 未来4场+串关方案 |
| `8f9437f71917` | 赛前1h提醒 | paused | |

交付模式: `deliver=local,origin` (微信+本地双保险)

### ⚠️ 例行工作（Daily Pipeline）

**赛后必做，不可遗漏：**

1. 采集当日赛果 → `data/wc2026_results.json`
2. 更新 ELO：`python3.11 scripts/update_elo_from_results.py`
3. 更新准确率 → `data/prediction_accuracy.json`
4. 生成下轮预测：`python3.11 scripts/predict_next_n.py --n 6`

详见 `references/daily-pipeline.md`。

## 🔧 v3.3 模型调参（2026-06-16）

**问题**：预测比分过于夸张（Spain λ=5.5→预测6-0，实际0-0），判词过度自信（60%即标"高置信度"）。

**修复**（`wc2026_predict.py` + `fp_predict.py`）：

| 维度 | 旧 | 新 |
|------|-----|-----|
| λ公式 | 指数 `1.45×10^(Δ/500)` | 线性 `1.4±Δ/300` (上限3.0) + 20%均值回归 + ±0.12噪声 |
| 高置信 | win%≥60 | win%≥70 |
| 中置信 | win%≥50 | win%≥55 且 win%>draw% |
| 平局检测 | draw%≥35 | draw%≥30 + "倾向平局"(draw%≥25) |

**效果**：Brier 0.871→0.613（↓30%），Netherlands vs Japan 从"荷兰胜"→"势均力敌" ✓

详见 `references/v3.3-model-fix.md`。

48 队全量在 `data/team_profiles.json`（`name_cn` 字段），`wc2026_predict.py` 判定行和 xG 行均输出中文队名。`predict_next_n.py` 和 `lottery_parlay.py` 同样使用中文队名。

## 体彩串关投注系统 (v4.3)

### 竞彩赔率模型

基于中国竞彩 71% 官方返奖率构建的赔率估算系统（官方 API 全部被 EdgeOne WAF 封锁，无法实时获取）。

| 参数 | 值 | 说明 |
|------|-----|------|
| `vig_factor` | 0.71 | 竞彩返奖率 ~71%（庄家抽水 29%） |
| 赔率区间 | 1.01-20.00 | 60 档标准赔率表 |
| 概率校准 | T=5.0 logit 收缩 | 99.9%→79.9%，修正 Poisson 模型过度自信 |
| 跳过阈值 | @1.05 + prob>90% | 极低赔率超级热门不加回报只加风险 |

### 串关策略演进

| 版本 | 策略 | 选场 | 分配 | EV | 中奖率 |
|------|------|------|------|:---:|:---:|
| v1.0 | 单注全押 | 每场单一最优 | 100元×1 | -21% | 25% |
| v2.0 | 全组合分散 | 笛卡尔积枚举 | 6注加权 | -47% | 100% |
| v2.1 | 子集枚举 | 2/3/4场子集 | Top-6分散 | -25% | 63% |
| v2.2 | **集中火力** | Top-2组合 | 各50元 | -20% | 40% |

> **关键发现**: v2.2 集中策略 EV 最优。竞彩固定赔率下各组合 EV/元 接近，分散只稀释回报不提升期望。

### 竞彩数据源现状

- ❌ `sporttery.cn` / `lottery.gov.cn` — EdgeOne WAF 567
- ❌ `jc.zhcw.com` API — 接口限流
- ❌ `500.com` — 403 Forbidden
- ✅ **合成模型**（71%返奖率 + T=5温度校准）— 当前唯一可行方案
- 🟡 `zgzcw.com` — 仅有让球盘，无胜平负直赔

### 串关陷阱

1. **竞彩@1.05法定下限**: 概率>67%的热门全部挤在@1.05，无法区分99%和70%优势
2. **子集枚举优于全量**: 4场全含EV仅为2场子集的40%，必须枚举所有子集大小
3. **中奖概率显示**: "总中奖概率143%"=多注概率之和(非互斥)，实为"期望中奖注数"

### 竞彩赔率数据源

中国竞彩 (sporttery.cn, lottery.gov.cn, jc.zhcw.com, 500.com) 全部被 WAF 封锁，无公开 API。
当前使用合成模型（71%返奖率+温度校准），已验证在竞彩真实区间。
完整实践记录和五个关键陷阱见 [references/jingcai-odds-pitfalls.md](references/jingcai-odds-pitfalls.md)。
**当前方案**: 合成模型（71% 返奖率），已验证赔率在竞彩真实区间内。
禁止在代码中声称"即将接入官方 API"——此方案已是稳定替代。

### 微信推送限流

iLink rate limit 会导致微信推送静默失败。Cron 配置 `deliver=local,origin` 确保本地有备份。

### 预测报告队名

**必须使用中文队名**。`wc2026_predict.py` 的 verdict 行和 xG 行均已修复为中文（`cn_a`/`cn_b` 而非 `team_a`/`team_b`）。新增脚本必须同样处理。

### 大 ELO 差时 Poisson xG 畸高

当有效 ELO 差 >300 时，Poisson lambda 公式给出极高预期进球。关注胜/平/负概率方向，不要依赖单场比分预测。

### 串关 EV 负值

竞彩 29% 抽水导致几乎所有串关 EV 为负（-20%~-47%），这是结构性现实。报告中如实标注红色 EV，并附加风险提示。

### RSS 情感分析 Graceful Degradation

详见 `references/rss-graceful-degradation.md` — 三层 fallback 设计模式。

### eloratings.net 数据采集

使用 `web_search("eloratings.net Team_Name")` 获取 search snippet 中的 ELO 数值。international-football.net 持续 429 限速。

## 每日预测管线 (v4.4)

```bash
# 1. 数据刷新管线（每天一次）
cd /path/to/wuhoo-football-predictor
python3.11 scripts/daily_pipeline.py --morning

# 2. 采集已结束比赛的赛果
python3.11 scripts/collect_results.py --date YYYY-MM-DD --manual '[...]'

# 3. 从赛果更新 ELO
python3.11 scripts/update_elo_from_results.py

# 4. 重新计算热身赛状态因子
python3.11 scripts/fetch_friendlies.py --compute-form

# 5. 预测未来 N 场
python3.11 scripts/predict_next_n.py --n N --news
```

**关键**: 步骤顺序不能乱！必须先 collect_results 再 update_elo，否则 ELO 不会反映最新赛果。

## 数据源维护

| 文件 | 更新方式 | 频率 |
|------|---------|------|
| `elo_ratings.json` | `fetch_elo.py --diff` + `update_elo_from_results.py` | 赛前+赛后 |
| `friendly_matches.json` | ESPN 手动采集 → `fetch_friendlies.py --compute-form` | 有新知即补 |
| `injuries.json` | ESPN/The Athletic/BBC/Fox Sports → 手动更新 | 赛前每 1-2 天必查 |
| | | 刷新流程见 [references/injury-data-refresh.md](references/injury-data-refresh.md) | |
| `wc2026_results.json` | `collect_results.py` | 赛后立即 |

见参考文档：
- `references/data-freshness-workflow.md` — 数据保鲜刷新工作流、静态文件刷新、predict_next_n 存盘修复
- `references/injury-format.md` — injuries.json 格式规范与常见错误
- `references/friendly-data-collection.md` — 热身赛数据采集流程
- `references/polymarket-cross-validation.md` — Polymarket API 交叉验证

## 常见陷阱

1. **injuries.json 键名错误**: 模型读取 `injuries` 键（不是 `teams`），用错会导致所有伤病数据不生效
2. **Team name 不匹配**: 必须用 ELO 数据中的规范名（`Bosnia and Herzegovina` 不是 `Bosnia`）
3. **form 因子假象**: 热身赛数据不全时 form 因子严重失真（1场→+25 vs 15场→+4）
4. **ELO 不更新就预测**: 必须先 `update_elo_from_results` 再 `predict_next_n`
5. **Polymarket 与模型背离**: Davies 伤缺导致 Canada 模型94.7% vs 市场53.5%——市场给伤病定了价
6. **重复添加热身赛**: 每次新增前检查 `(date, team_a, team_b)` 组合是否已存在（含反转）

## 架构

```
wuhoo-football-predictor/
├── wc2026_predict.py         # 2026世界杯全流程 Monte Carlo + 单场预测
├── fp_predict.py             # 通用预测 CLI
├── scripts/
│   ├── predict_next_n.py       # v4.3: 未来N场预测 + 中文报告 + 串关
│   ├── lottery_parlay.py       # v4.3: 体彩串关方案生成器(竞彩71%)
│   ├── predict_by_date.py      # v3.0: 按日期批量预测
│   ├── daily_pipeline.py       # cron 管线编排
│   ├── prediction_models.py    # Poisson + Elo + Factor + Ensemble
│   ├── fetch_elo.py            # ELO 评分更新
│   ├── fetch_friendlies.py     # 热身赛采集+状态计算
│   ├── sentiment_analyzer.py   # 新闻情感分析
│   ├── check_football_freshness.py  # 数据保鲜检查 (v4.5)
│   ├── pre_match_refresh.py    # 数据新鲜度检查
│   ├── collect_results.py      # 比赛结果采集
│   └── match_reminder.py       # 赛前1h提醒
├── data/
│   ├── elo_ratings.json        # 64队 ELO
│   ├── friendly_form_adjustments.json # 热身赛状态调整值
│   ├── team_profiles.json      # 48队中英文元数据(含name_cn)
│   ├── wc2026_schedule.json    # 72场小组赛完整赛程
│   └── prediction_history.jsonl # 预测历史
├── references/
│   ├── rss-graceful-degradation.md
│   ├── friendly-form-algorithm.md
│   ├── daily-pipeline.md
│   └── v3.3-model-fix.md
└── configs/
    ├── tournaments.json
    └── weights.json
```

## 已知限制

1. **ELO 数据可能过期**: international-football.net 持续 429，依赖 static fallback
2. **两份 SKILL.md 副本**: `~/.hermes/skills/` 和 `~/wuhoo-workspace/skills/` 各有副本。`skill_manage` 默认写 `.hermes` 副本，workspace 含实际脚本代码。更新 `.hermes` 后需手动 `cp` 到 workspace。Cron job 加载 skill 时可能因 ambiguous 报 "Skill not found"（prompt 已自含不阻塞执行）
3. **竞彩赔率为合成**: 无官方 API，71% 返奖率模型为最优替代
4. **Uruguay 无热身赛数据**: 47/48 队覆盖
5. **串关 EV 始终为负**: 竞彩 29% 抽水的结构性结果，报告已如实标注
6. **WeChat iLink 限流**: Cron 推送可能静默失败，`deliver=local,origin` 保底