---
name: wuhoo-football-predictor
description: WC2026 单场+全赛事预测系统 v4.1 — Elo+Poisson+Monte Carlo，7层模型栈(含热身赛状态因子)，支持 --match 单场审计预测 + --full 全赛事MC + --report 中文报告 + 伤病/教练/venue/新闻情感/手动调整。v4.1 热身赛数据大刷新(46场→47/48队覆盖)
version: 4.1.0
dependencies:
  - wuhoo-news-rss
  - pandas
  - numpy
tags: ["wuhoo"]
category: wuhoo
---

# 足球赛事预测系统 v4.1

## 概述

基于 Elo 评分 + Poisson 分布 + Monte Carlo 模拟的多层次预测系统，支持世界杯、欧洲杯等国际赛事。

### v4.1 更新 (2026-06-08) — 热身赛数据大刷新

- ✅ **22场新热身赛**: 从 football365/ESPN/BBC 采集，覆盖 Argentina, Portugal, Scotland 等
- ✅ **47/48队覆盖**: 仅 Uruguay 无公开热身赛数据
- ✅ **Scotland 从无到 +20**: 4-0 Bolivia, 4-1 Curacao 两场大胜
- ✅ **Argentina +8**: 2-0 Honduras (Messi轮休, Lautaro+Giuliano进球)
- ✅ **Portugal +7**: 2-1 Chile (Leao红牌, Bruno进球)
- ✅ **移除 XHS 双通道**: 小红书采集命中率仅12%，回退至 RSS 单通道。详见 [references/xhs-integration-postmortem.md](references/xhs-integration-postmortem.md)
- ✅ **46场完整热身赛记录**: fetch_friendlies.py --list 查看全量。采集流程见 [references/friendly-match-refresh-workflow.md](references/friendly-match-refresh-workflow.md)

### v3.0 更新 (2026-06-02) — 比赛日单场预测管线

- ✅ **新增单场预测 CLI**: `wc2026_predict.py --match "A" "B"` 带完整 6 层审计链路
- ✅ **赛程数据**: `data/wc2026_schedule.json` — 72 场小组赛完整赛程（含北京时间）
- ✅ **6.1 大名单数据大刷新**: 伤病确认更新（11 队 22 球员），8 个 DOUBTFUL 状态更新
- ✅ **元数据全覆盖**: team_metadata.json 从 36→48 队（100% 覆盖）
- ✅ **预测历史**: 自动记录到 `data/prediction_history.jsonl`
- ✅ **手动调整**: `--adj "Team:+N"` 支持主观微调
- ✅ **预测前检查**: `scripts/pre_match_refresh.py` 数据新鲜度自动检查

### v2.5 更新 (2026-05-30) — 俱乐部单场预测 + 审计框架

- ✅ 新增俱乐部单场预测能力：欧冠决赛 Arsenal vs PSG 实战验证
- ✅ 俱乐部 ELO 数据源文档化：elofootball.com / clubelo.com / clubelo.com/UCL
- ✅ 5层调整框架：伤病/停赛 → 锦标赛背景 → 近期状态 → H2H → 新闻情绪
- ✅ 审计要求制度化：数据来源清单、调整链路、已知局限性
- ✅ 参考案例: references/club-prediction-example.md

### v2.4 更新 (2026-05-26) — 赛前数据大刷新

**伤病数据 v2.0:** 7队→10队, 11→15名球员
- 🔴 NEW England: Foden+Palmer+TAA 三人缺阵 (-90) — 夺冠概率 2.3%→0.2%
- 🔴 NEW Japan: Mitoma 因伤落选 (-30), 总 penalty -25→-50
- 🔴 Germany: Gnabry DOUBTFUL→OUT, 总 -35→-45
- 🔴 Brazil: Estevao DOUBTFUL→OUT, 总 -60→-80
- 🟢 Egypt: Salah 确认入队, 移除 penalty
- 🟡 NEW Argentina: Romero DOUBTFUL (-15)
- 🟡 NEW Ghana: Kudus DOUBTFUL (-20)
- 🟡 NEW Canada: Davies DOUBTFUL (-10)
- 🟡 Spain: Merino DOUBTFUL 新增 (-15), 总 -15→-30

**教练/磨合数据 v2.0:** 20队→36队 (覆盖率 75%)
- 新增: Norway, Sweden, South Korea, Scotland, Tunisia, Egypt, Ivory Coast, New Zealand, Cape Verde, DR Congo, Bosnia, Haiti, Curacao, Algeria, Austria, Ghana, Canada
- 更新: England (Foden/Palmer/TAA OUT→稳定性↓), Brazil (Ancelotti+伤病→稳定性↓), Argentina, Germany, Japan

### 预测模型栈 (7 层)

| 层 | 模型 | 说明 | 类型 |
|------|------|------|------|
| 1 | **ELO 评分** | 基于实力差值的胜负概率 (international-football.net, 64队) | 基础 |
| 2 | **Poisson 分布** | 基于预期进球的比分概率 | 基础 |
| 3 | **伤病扣分** | 真实伤病数据 (injuries.json, 手动维护) | v2.3 |
| 4 | **教练/磨合因子** | 教练 WC 经验 + 阵容稳定性 + 球队化学反应 (team_metadata.json) | v2.3 |
| 4.5 | **热身赛状态** | 近期友谊赛结果 vs ELO期望，指数衰减加权 (friendly_form_adjustments.json) | v3.1 |
| 5 | **锦标赛形态** | 每队每轮抽取持久 N(0,60) ELO boost, 模拟"状态火热的黑马" | v2.3 |
| 6 | **比赛级扰动** | 动态冷门上界 22% + 每场 N(0,25) 抖动 + 40% 比分扰动 | v2.3 |
| 7 | **新闻情感 (RSS)** | RSS 英文媒体情感分析 ±40 ELO | v2.2 |

## CLI 命令

```bash
# === v3.0: 比赛日单场预测（核心新增）===
# 按对阵预测
python3.11 wc2026_predict.py --match "Argentina" "France"

# 按赛程编号预测
python3.11 wc2026_predict.py --match-id 1

# 按小组+轮次预测（查赛程自动找对阵）
python3.11 wc2026_predict.py --group A --matchday 1

# 带 venue、新闻情感、手动调整
python3.11 wc2026_predict.py --match "Argentina" "France" --venue "MetLife Stadium" --news --adj "Argentina:-10"

# 淘汰赛模式（平局→点球概率打破）
python3.11 wc2026_predict.py --match "Argentina" "France" --ko

# 输出 JSON 审计文件
python3.11 wc2026_predict.py --match "Argentina" "France" -o prediction.json

# === 全赛事模拟（保留）===
# 2026 世界杯全流程 Monte Carlo
python3.11 wc2026_predict.py --full --sims 5000

# 生成中文综合报告
python3.11 wc2026_predict.py --report --sims 5000 --news

# 仅小组赛
python3.11 wc2026_predict.py --groups

# === 数据维护 ===
# 预测前数据刷新检查
python3.11 scripts/pre_match_refresh.py

# 更新 ELO 数据
python3.11 scripts/fetch_elo.py --output=data/elo_ratings.json
python3.11 scripts/fetch_elo.py --diff

# === v3.1: 热身赛数据维护 ===
# 手动添加一场热身赛结果
python3.11 scripts/fetch_friendlies.py --add '{"team_a":"France","team_b":"Ivory Coast","score_a":1,"score_b":2,"date":"2026-06-04"}'

# 列出所有已采集的热身赛
python3.11 scripts/fetch_friendlies.py --list

# 查看待确认结果的比赛
python3.11 scripts/fetch_friendlies.py --pending

# 重新计算近期状态调整值（采集新数据后必须运行）
python3.11 scripts/fetch_friendlies.py --compute-form

# 通用预测 CLI (保留，非 WC2026 专用)
python3.11 fp_predict.py --predict "Argentina" "France" --tournament worldcup
python3.11 fp_predict.py --backtest --tournament worldcup --year 2022
```

## 俱乐部赛事单场预测 (v2.5 新增)

本系统同时支持俱乐部赛事单场预测（如欧冠决赛、联赛焦点战），使用与世界杯相同的模型栈。

## 开发陷阱

### execute_code 中 read_file 返回 dict (v2.4)

`hermes_tools.read_file()` 在 `execute_code` 沙箱中返回 **dict** (`{"content": "...", "total_lines": N}`)，不是字符串。直接 `json.loads(read_file(...))` 会报 `TypeError`。

**正确**: 在 `execute_code` 中使用 `read_file(path)["content"]` 获取文本内容，或改用 `terminal()` 执行数据扫描脚本。

### prediction_models API 陷阱 (v3.0 新增)

**类而非函数**: `prediction_models` 全部通过类暴露 (`PoissonModel`, `EloModel`, `FactorModel`, `EnsembleModel`)，没有 `elo_win_probability()` 等独立函数。不要 `from prediction_models import elo_win_probability`。

**EnsembleModel 返回嵌套结构**: `predict()` 返回 `{'predictions': {'ensemble': {...}, 'poisson': {...}, ...}, 'recommendation': ..., 'expected_goals': {...}}`。访问集成概率用 `result['predictions']['ensemble']['home_win']`，**不是** `result['ensemble']['home_win']`。

**便捷函数**: 使用 `from prediction_models import predict_match` 代替手动构造，参数: `(team_a, team_b, elo_a, elo_b, goals_a, goals_b, is_neutral)`。

```python
from prediction_models import predict_match
result = predict_match('Canada', 'Switzerland', elo_a=1829, elo_b=1889,
                        goals_a=1.3, goals_b=1.5, is_neutral=True)
probs = result['predictions']['ensemble']  # → {'home_win': 0.327, 'draw': 0.240, 'away_win': 0.433}
print(result['recommendation'])            # → '客胜 (Switzerland)'
```

本系统同时支持俱乐部赛事单场预测（如欧冠决赛、联赛焦点战），使用与世界杯相同的模型栈但采用不同的数据源和调整框架。

### 俱乐部 ELO 数据源

| 来源 | URL | 适用范围 | 说明 |
|------|-----|----------|------|
| **elofootball.com** | https://elofootball.com | 欧洲俱乐部 | ~2300 scale，更新频率高 |
| **clubelo.com** | http://clubelo.com | 全球俱乐部 | ~2000 scale，含联赛/欧冠分类 |
| **clubelo.com/UCL** | http://clubelo.com/UCL | 欧冠专属 | 仅计算欧冠比赛 ELO |

> ⚠️ 俱乐部 ELO 主要针对联赛校准。欧冠决赛需额外调整以反映锦标赛背景。

### 调整框架（俱乐部单场）

在基础 ELO 之上依次应用以下调整（顺序无关但需全部计入）：

| 层级 | 类别 | 调整依据 | 示例 |
|------|------|----------|------|
| 1 | **伤病/停赛** | 核心球员 -25~-40, 重要球员 -15~-25, 角色球员 -5~-15 | Partey 停赛 -25 |
| 2 | **锦标赛背景** | 卫冕冠军 +10~20, 决赛初哥 -5~15 | PSG 卫冕 +15 |
| 3 | **近期状态** | 基于最后 5-10 场比赛结果 ±10 | 赛季末段下滑 -5 |
| 4 | **交锋记录 (H2H)** | Factor 模型输入, -0.2~+0.2 | 近期连败 -0.10 |
| 5 | **新闻情绪** | 可选, 通过 SentimentAnalyzer 计算 | 舆论偏向 -0.10 |

调整原则：
- 所有调整必须有**可追溯来源**（媒体/官方公告/数据平台）
- 伤病扣分使用 injuries.json 相同体系（核心-40/重要-25/角色-15）
- 锦标赛背景调整需保守：冠军级差距通常在 ±20 以内
- Factor 模型各因子归一化到 [-1, 1] 区间

### 审计要求

单场预测必须输出完整审计链路：
1. **数据来源清单** — 每个数据点标注来源 URL 和采集日期
2. **调整计算过程** — 展示 base ELO → 各项调整 → final ELO 完整链路
3. **模型输入参数** — xG, ELO, factors 全部显式列出
4. **已知局限性** — 数据缺口、估算假设、未建模因素

详见 [references/club-prediction-example.md](references/club-prediction-example.md) 完整案例。

## 2026 世界杯预测结果 (v2.4, 5,000 sims, 2026-05-26)

> ⚠️ 基于 international-football.net 2026-05-24 数据 + v2.4 伤病/元数据刷新 (10队伤员, 36队教练因子)

| 阶段 | 球队 | 概率 |
|------|------|------|
| 🏆 冠军 | Argentina | 38.1% |
| | Spain | 33.7% |
| | France | 22.0% |
| | Portugal | 2.3% |
| | Colombia | 2.2% |
| | Ecuador | 0.4% |
| | Croatia | 0.4% |
| | Netherlands | 0.3% |
| | England | 0.2% |
| | Senegal | 0.1% |
| 🥈 决赛 | France | 63.3% |
| | Argentina | 52.4% |
| | Spain | 41.9% |
| 🏅 四强 | Argentina | 90.6% |
| | Spain | 89.5% |
| | France | 81.9% |
| | Colombia | 37.4% |
| | Portugal | 36.8% |

> v2.4 关键变化: England Foden+Palmer+TAA 三人 OUT (-90 ELO) → 夺冠率 2.3%→0.2% (↓91%)。Brazil 伤病 -60→-80。Japan Mitoma 落选 -50。Argentina 仍居首但 Romero 伤疑 ↓3.5%。

### 回测基线
- WC 2022: 57.8% 准确率 (64场)
- Euro 2024: 51.0% 准确率 (51场)

## 架构

```
wuhoo-football-predictor/
├── wc2026_predict.py         # 2026世界杯全流程 Monte Carlo (v4.0 双通道)
├── fp_predict.py             # 通用预测 CLI
├── scripts/
│   ├── prediction_models.py    # Poisson + Elo + Factor + Ensemble
│   ├── backtest.py             # 回测引擎
│   ├── fetch_data.py           # 数据采集
│   ├── fetch_elo.py            # ELO 评分更新脚本 (v2.0, 多源级联)
│   ├── fetch_friendlies.py     # 热身赛采集+状态计算 (v3.1)
│   ├── sentiment_analyzer.py   # 新闻情感分析 v4.0 — 中英文双通道 + RSS连接器
│   ├── xiaohongshu_collector.py # [DEPRECATED v4.1] 小红书采集，命中率仅12%已弃用
│   ├── download_data.py        # 历史比赛数据下载
│   └── pre_match_refresh.py    # v3.0: 预测前数据新鲜度检查
├── data/
│   ├── elo_ratings.json        # 64队 ELO (2100-scale, static fallback)
│   ├── friendly_matches.json    # 46场热身赛原始数据 (v4.1 刷新)
│   ├── friendly_form_adjustments.json # 47/48队热身赛状态调整值 (v4.1)
│   ├── team_profiles.json      # 48队中英文元数据
│   ├── team_metadata.json      # 48/48队教练/磨合/阵容 (100% 覆盖 ✅)
│   ├── injuries.json           # v3.0: 11队22名球员伤病 (10 DOUBTFUL)
│   ├── venues.json             # 16球场 venue 数据库
│   ├── group_venues.json       # 12组小组赛 venue 映射
│   ├── wc2026_schedule.json    # v3.0: 72场小组赛完整赛程 ✅
│   ├── prediction_history.jsonl # v3.0: 预测历史记录 ✅
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
  ├── references/
│   ├── bracket-2026.md          # 官方对阵表、R32分配算法
│   ├── elo-pipeline-status.md   # ELO 管线状态、数据源迁移记录
│   ├── group-venue-mapping.md   # 小组赛 venue 映射
│   ├── injury-data-sources.md   # 伤病数据源与更新流程
│   ├── plan-review-checklist.md # 计划审查清单
│   ├── friendly-form-algorithm.md # 热身赛状态因子算法文档 (v3.1)
│   ├── club-prediction-example.md # 俱乐部单场预测完整案例 (v2.5)
│   └── 20260526-wc-data-audit.md # v2.4 数据更新审计 (2026-05-26)
│   ├── friendly-match-pipeline.md # v3.1 热身赛采集管线+网页抓取陷阱
│   ├── friendly-match-refresh-workflow.md # v4.1 热身赛数据批量刷新工作流
│   └── xhs-integration-postmortem.md # v4.0→v4.1 XHS集成事后分析
│   └── xiaohongshu-integration-analysis.md # v3.3 小红书数据整合分析与方案 (2026-06-08)
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

## 常见问题与陷阱

### 新增数据源前先验证质量

**教训 (v4.0→v4.1)**：在投入代码集成之前，先验证数据源能否产生有效信号。
- Brave Search API 不支持 `site:` 域名过滤 → XHS采集命中率仅12%
- 情感信号范围 (-8~+2 ELO) 远小于伤病 (-125~0) 和教练 (+3~+59)
- 用户决策：快速回退，保留分析器代码以备将来使用
- 详见 [references/xhs-integration-postmortem.md](references/xhs-integration-postmortem.md)

详见 [references/prediction-audit-walkthrough.md](references/prediction-audit-walkthrough.md) — 完整的单场预测审计走查方法论，包含 6 层模型逐层解释模板。

### RSS 情感分析 Graceful Degradation (v3.2)

详见 [references/rss-graceful-degradation.md](references/rss-graceful-degradation.md) — 三层 fallback 设计模式、代理策略、反模式警示。核心原则：**宁可返回中性也不返回空，宁可降级也不放弃。**

### --news 模式静默失效

**现象**: `--news` 不报错但也不显示任何情感调整。

**根因 (v3.1-)**: `load_news_sentiment()` 硬编码 `days_back=14`。RSS cron job 暂停后，新闻数据库最新文章可能超过 14 天。即使 DB 中有 751 篇足球文章（category='足球'），只要没有 14 天内的，查询就返回空 → `return {}` 跳过所有情感分析。

**v3.2 修复**: 移除硬切断 + 两层窗口 fallback:
1. 先查 14 天窗口
2. 为空则 fallback 到 30 天窗口
3. 仍为空 → 走空 `sentiment_scores = {}` 的代理策略路径（全部返回中性 0）
4. 全程不 `return {}`，始终走完代理策略，确保 graceful degradation

**诊断**:
```bash
sqlite3 ~/wuhoo-workspace/skills/wuhoo/wuhoo-news-rss/data/news.db \
  "SELECT MAX(pub_date), COUNT(*) FROM articles WHERE category='足球'"
```
- 最新日期 >30 天 → 全部 48 队返回中性（0 ELO 调整）
- 最新日期 14-30 天 → fallback 30 天窗口生效
- 最新日期 <14 天 → 正常直接搜索

### 大 ELO 差时 Poisson xG 畸高

**现象**: 当有效 ELO 差 >300 时，Poisson lambda 公式给出极高预期进球（如 Mexico vs SA: xG 13.59 vs 0.20, 预测比分 6-0）。

**根因**: `predict_score()` 使用 `lambda = 1.45 × 10^(elo_diff/500)`。当 elo_diff=474 时，10^0.948=8.86，lambda=12.86。

**缓解**: 
- **不要**对单场比分预测过于依赖——关注胜/平/负概率方向
- 未来可考虑添加 lambda 上限或引入"领先降速"因子

### eloratings.net 数据采集 (v3.2 新增)

**现象**: `curl eloratings.net/2026_World_Cup` 返回空 HTML 骨架（JS 动态渲染），`web_extract` 同样失败。

**根因**: eloratings.net 使用 SlickGrid + JavaScript 在前端渲染所有数据，静态 HTML 无内容。

**可用方式**:
- `web_search("eloratings.net Team_Name")` — 搜索 snippet 会包含 ELO 数值（如 "South Africa. 1518"）
- 用 `cntrl+F` 对照现有 ELO 文件检查差异
- international-football.net 返回 429 时，search snippet 是备选方案

## 已知限制

1. **ELO 数据可能过期**: 最后更新 2026-06-06（static fallback），国际比赛日无更新
2. **伤病数据手动维护**: 11 队伤员，需赛前逐队确认（Neymar DOUBTFUL 为关键变量）
3. **RSS 新闻覆盖不均**: 偏重欧洲豪门，非主流球队通过同洲代理策略降级
4. **fp_predict.py `--full` 为桩代码**: 仅配置了多赛事框架
5. **7 个测试失败**: v2.3 参数变更后测试断言未同步更新
6. **Uruguay 无热身赛数据**: 47/48 队覆盖，Uruguay 未安排公开热身赛
7. **ELO 采集受限**: international-football.net 持续 429 限速，依赖 static fallback
10. **情感信号占比过弱**: 情感调整范围 (-8~+2 ELO) 远小于伤病 (-125~0) 和教练 (+3~+59)，实际预测中几乎不产生影响。`impact * 250` 换算公式可能需要重新校准

### v4.0 审计案例
- [references/20260608-group-c-audit.md](references/20260608-group-c-audit.md) — C组第一轮完整审计 (Brazil vs Morocco, Haiti vs Scotland)，含各层调整链路、XHS质量分析、优化建议
