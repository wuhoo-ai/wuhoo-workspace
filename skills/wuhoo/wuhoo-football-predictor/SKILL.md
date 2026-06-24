---
name: wuhoo-football-predictor
description: WC2026 单场+全赛事预测系统 v5.5 — Elo+Poisson+Monte Carlo+LLM非结构化信号+客观条件因子+出线动机(QMF)+半区路径(BPP)+淘汰赛校准(KBC)+规则推理引擎(InferenceEngine)+Layer 6手动调整，12层模型栈，未来N场预测+全中文报告+体彩串关+数据保鲜检查
version: 5.5.0
dependencies:
  - wuhoo-news-rss
  - pandas
  - numpy
tags: ["wuhoo"]
category: wuhoo
---

# 足球赛事预测系统 v5.3

## 概述

基于 Elo 评分 + Poisson 分布 + Monte Carlo 模拟 + **LLM 非结构化信号** + **客观条件因子** + **Layer 6 手动调整** 的多层次预测系统。

### v5.5.0 更新 (2026-06-24) — 规则推理引擎

**触发**: 12层ELO天真加法叠加存在结构性缺陷：无交互效应、无置信度衰减、无饱和约束。需要从"逐步加ELO"进化为"带约束的推理系统"。

- ✅ **新增 `scripts/inference_engine.py`**: 规则驱动的推理引擎。支持条件评估(regex)、模板解析(`{{key}}`)、置信度缩放、交互约束、sigmoid饱和
- ✅ **新增 `scripts/data_provider.py`**: 统一数据抽象层。动态构建Context dict，支持freshness检查和模板注入
- ✅ **新增 `scripts/predict_v55.py`**: v5.5推理包装器。零侵入设计——引擎计算ELO delta → 作为manual_adjustments注入现有管线
- ✅ **新增 `scripts/phase0_rule_learning.py`**: 44场完赛复盘+网格搜索学习最优参数
- ✅ **新增 `configs/rules_v1.json`**: 16条规则定义(14层+2交互) + 4条交互约束 + sigmoid参数
- ✅ **规则学习结果**: 基线准确率70.5%(44场), 13/13错误全是漏判平局, 交互系数通过网格搜索标定
- ✅ **推理路径报告**: `audit['reasoning_path']` 含每条规则的原始值→置信度→交互→最终值全链
- ✅ **A/B双轨**: `rules_v1.json`(生产) / `rules_v2.json`(实验), `--rules-version v2`切换
- ✅ **向后兼容**: `use_inference_engine=False`默认关闭, 现有管线零影响
- ⚠️ **wrapper模式**: 引擎通过predict_v55.py包装调用, 未修改predict_single_match内部

### v5.4.0 更新 (2026-06-24) — 小组赛末轮+淘汰赛策略优化

**触发**: 小组赛MD3即将开始（24场），淘汰赛接踵而至（32场）。球队策略在末轮和淘汰赛发生根本性变化，现有模型未考虑出线动机、半区选择、淘汰赛行为差异。

- ✅ **新增 Layer 2.5 — QMF (出线动机因子)**: 基于积分表自动分类48队，6种动机分类（LOCKED_IN/DRAW_OK/NEED_RESULT/MUST_WIN/PRIDE_ONLY/TOP_SEED），ELO调整 -30~+25
- ✅ **新增 Layer 2.6 — BPP (半区路径偏好)**: 计算12组×2位置淘汰赛路径难度，头名之争组引入战略调整
- ✅ **新增 Layer 7 — KBC (淘汰赛行为校准)**: Poisson λ抑制(0.78×)、平局增强(均值回归15%)、弱队加成(ELO差>300→+25)、加时/点球模拟
- ✅ **新增 `scripts/compute_motivation.py`**: MD3动机自动计算，含第三名出线概率估计
- ✅ **新增 `scripts/compute_bracket_path.py`**: R32淘汰赛对阵路径难度分析
- ✅ **新增 `scripts/compute_third_place.py`**: 12组第三名实时排名+出线概率追踪
- ✅ **新增 `scripts/knockout_calibration.py`**: 基于WC1998-2022 (94场淘汰赛) 历史统计校准
- ✅ **新增数据文件**: `matchday3_motivation.json`, `bracket_paths.json`, `third_place_standings.json`
- ✅ **`predict_single_match()` 新增参数**: `matchday`, `motivation_data`
- ✅ **`predict_by_date.py` 自动加载**: MD3比赛自动激活QMF+BPP
- ✅ **审计链从7层扩展到12层**: +2.5_motivation, +2.6_bracket_path, +7_knockout_calibration
- ⚠️ **KBC仅在knockout=True时激活**: 淘汰赛阶段需显式设置
- ⚠️ **BPP仅在TOP_SEED组激活**: 路径偏好仅影响头名之争
- ⚠️ **ELO数据存在重复应用问题**: update_elo_from_results.py被多次调用，ELO值方向正确但幅度被放大

### v5.3.0 更新 (2026-06-23) — Layer 6 手动调整集成

**触发**: Portugal 队内公开裂痕（C罗 vs Diogo Costa 当场对峙 + 姐姐攻击队友 + 名宿集体批评）
——此事件无法被前 5.5 层（伤病/天气/情感/信号）捕获，暴露模型盲区。

- ✅ **新增 `data/manual_adjustments.json`**: 持久化 Layer 6 手动调整，每队含 `elo_adjustment` / `evidence` / `expires`
- ✅ **`predict_by_date.py` 自动加载**: 无需额外 CLI 参数，预测时自动读取并传入 `predict_single_match(manual_adjustments=...)`
- ✅ **调整幅度指南**: ±5~±50 ELO 范围，含事件类型→幅度映射
- ✅ **过期管理**: 每轮比赛后检查 `expires` 字段
- ✅ **参考文档**: `references/manual-adjustments.md` — 含 Portugal 完整案例 + 创建流程 + 常见错误
- 📊 **首次使用**: Portugal -30 ELO (vs Uzbekistan, 胜率 69.8%→68.3%)

### v5.2.0 更新 (2026-06-23) — 客观条件因子集成

**触发**: France vs Iraq (6/22) 因雷暴中断2小时，暴露当前模型完全忽略天气等客观条件。

- ✅ **Layer 4a — Weather (天气因子)**: 降水(含球队风格因子)+ 风力(露天球场) + 实时温度, 权重 5%
- ✅ **Layer 4b — Schedule Density (赛程密度)**: 旅途距离 + 休息天数 合并复合因子, 权重 3%
- ✅ **数据源**: Open-Meteo Forecast API (免费, 无需 key), 三重降级
- ✅ **`scripts/fetch_weather.py`**: 新建天气采集脚本, WMO code 映射, indoor 豁免
- ✅ **`data/venues.json`**: 补充 16 场馆 lat/lon 坐标 + pitch_type
- ✅ **`data/team_profiles.json`**: 新增 48 队 `style_category` 枚举 (possession/physical/counter/defensive/high_press/balanced)
- ✅ **报告增强**: 终端+Markdown 底部新增「客观条件因子」模块, 实验性标注
- ✅ **Cron 更新**: 14:30 管线 Step 3.5 天气采集; 15:00 管线 Step 0.5 天气保鲜验证
- ⚠️ 实验性因子, 低权重 (5%/3%), 仅供附加参考, 不做方向性判断

**触发**: France vs Iraq (6/22 Philadelphia) 因雷暴中断2小时，当前模型完全忽略天气/旅途等客观条件。

**新增 Layer 4a — Weather (天气因子)**:
- ✅ **降水**: 基于 Open-Meteo 实时预报 + WMO 天气码，4级惩罚 (none/light/moderate/heavy)，含球队风格因子 (possession×1.3 / physical×0.7)
- ✅ **风力**: 3级 (calm/breezy/windy)，室内球场自动豁免
- ✅ **实时温度**: 替换 venues.json 静态均温，用比赛日预报温度重新计算 heat_penalty
- ✅ **数据源**: Open-Meteo Forecast API (免费, 无需 key)，三重降级 (API→静态→0)
- ✅ **权重**: 基准 5%，rain max ±30 ELO

**新增 Layer 4b — Schedule Density (赛程密度)**:
- ✅ **旅途疲劳**: Haversine 距离计算，每500km扣5 ELO，上限-20
- ✅ **休息天数**: 两队休息天数差 × 8 ELO，上限±24
- ✅ **合并为赛程密度**: net = (travel + rest) / 2，上限±20 ELO
- ✅ **权重**: 基准 3%

**数据增强**:
- ✅ `venues.json`: 16场馆补充 lat/lon 坐标 + pitch_type
- ✅ `team_profiles.json`: 48队新增 `style_category` 枚举字段 (possession/physical/counter/defensive/high_press/balanced)
- ✅ 新脚本: `scripts/fetch_weather.py` (Open-Meteo 天气采集)

**报告增强**:
- ✅ 终端 + Markdown 报告底部新增「客观条件因子」模块
- ✅ 实验性标注: "权重较低 (天气5%/赛程3%)，仅供附加参考"

**Cron 更新**:
- ✅ `5154715032ec` (14:30): 插入 Step 3.5 fetch_weather
- ✅ `86912ff0a4aa` (15:00): 新增 Step 0.5 天气保鲜验证

详见: `.hermes/plans/2026-06-23_weather-travel-factors-v5.2.md`

### v5.1.1 更新 (2026-06-22) — 系统健康修复

- ✅ **SKILL.md 去重**: 删除 `~/.hermes/skills/wuhoo/wuhoo-football-predictor/`，只保留 workspace 副本，解决 skill_view ambiguous 错误
- ✅ **ELO 全量刷新**: 40 场已完赛全部应用到 ELO，`update_elo_from_results.py` 从 6/13 stale → 今日实时
- ✅ **Schedule 同步修复**: 32 场有结果但未标记 completed → 自动同步脚本，schedule 与 results 一致
- ✅ **伤病数据刷新**: 6 队新增 + 3 状态更新 (Endo OUT, Ruben Dias DOUBTFUL, Wesley OUT, Bombito OUT, Malagon OUT, Aghehowa OUT; Neymar→OUT, Livramento→OUT)
- ✅ **Cron 作业清理**: 移除暂停的 `8f9437f71917` (赛前1h提醒)；更新 `5154715032ec` prompt 为 --check→web_search→--manual 标准流程
- ⚠️ **发现 ELO 静默过期陷阱**: `collect_results.py` 不自动调用 `update_elo_from_results.py`，cron 必须显式链式调用
- ⚠️ **发现 Schedule 不同步陷阱**: `wc2026_schedule.json` 不会自动从 results 同步状态，需单独维护

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

### 预测模型栈 (9 层) — 架构说明

**关键架构**: 模型采用 **ELO 逐层叠加** 而非集成加权。各层计算 ELO 调整量，直接加到 effective ELO 后输入 Poisson。`configs/weights.json` 仅供 `prediction_models.py` 的 EnsembleModel 路径使用（与主预测管线 `wc2026_predict.py` 不同）。

| 层 | 模型 | ELO 贡献 | 说明 |
|------|------|------|------|
| 1 | **ELO 评分** | 1500-2200 (基底) | 48 队 ELO (比赛结果反推) |
| 2 | **伤病扣分** | -100 ~ 0 | injuries.json 真实伤病数据 |
| **2.5** | **出线动机 (v5.4)** | **-30 ~ +25** | MD3末轮6分类动机因子 |
| **2.6** | **半区路径 (v5.4)** | **-10 ~ +10** | 淘汰赛路径难度偏好 |
| 3 | **教练/磨合因子** | -50 ~ +50 | coach + stability + chemistry (静态 metadata) |
| 4 | **场馆效应** | -80 ~ +60 | 海拔 + 静态均温 + 东道主优势 |
| **4a** | **天气 (v5.2)** | **-45 ~ 0** | 降水(风格加权) + 风力 + 实时温度, 权重5% |
| **4b** | **赛程密度 (v5.2)** | **-20 ~ +20** | 旅途距离 + 休息天数差 复合, 权重3% |
| 4.5 | **热身赛状态** | -50 ~ +50 | 友谊赛结果 vs ELO 期望，指数衰减 |
| 4.6 | **锦标赛形态** | N(0,60) | 每队一次性抽取持久 boost |
| 5 | **新闻情感 (RSS)** | -12 ~ +37 | keyword 词典 ±40 上限 |
| 5.5 | **非结构化信号** | LLM 因果信号融合 | 战术匹配 + 信号共识度, 降级为 0 |
| 6 | **手动调整** | 用户指定 | 覆写其他层 |
| **7** | **淘汰赛校准 (v5.4)** | **Poisson调整** | λ抑制0.78×, 平局增强, 加时/点球 |

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
# === v5.5: 规则推理引擎 ===
# 使用推理引擎预测单场 (wrapper模式)
python3.11 -c "
from scripts.predict_v55 import predict_with_engine
r = predict_with_engine('Brazil', 'Scotland', matchday=3)
print(r['reasoning_path'])
"

# 使用推理引擎预测整日比赛
python3.11 scripts/predict_v55.py  # 独立测试

# 44场复盘规则学习
python3.11 scripts/phase0_rule_learning.py

# 规则A/B测试
# rules_v1.json → 生产 | rules_v2.json → 实验
python3.11 -c "
from scripts.predict_v55 import predict_with_engine
r = predict_with_engine('Brazil', 'Scotland', matchday=3, rules_version='v2')
"

# === v5.4: MD3动机 + 淘汰赛校准 ===
# 自动计算48队出线动机分类（MD3使用）
python3.11 scripts/compute_motivation.py --all-groups

# 计算淘汰赛半区路径难度
python3.11 scripts/compute_bracket_path.py

# 追踪第三名出线排名
python3.11 scripts/compute_third_place.py

# 测试淘汰赛行为校准
python3.11 scripts/knockout_calibration.py

# === v5.2: 天气采集 ===
# 获取明日比赛天气 (Open-Meteo)
python3.11 scripts/fetch_weather.py --tomorrow

# 指定日期
python3.11 scripts/fetch_weather.py --date 2026-06-24

# 仅打印不保存
python3.11 scripts/fetch_weather.py --tomorrow --dry-run

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
| `5154715032ec` | 数据刷新+结果采集 | 14:30 | 保鲜→采集→伤病→ELO→摘要 |
| `86912ff0a4aa` | 赛前预测 | 15:00 | 未来4场预测+报告PDF+串关 |

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
- ✅ `trade.500.com/jczq` — **web_extract 可抓取**（2026-06-20 验证），含竞彩非让球胜平负赔率
- ✅ **合成模型**（71%返奖率 + T=5温度校准）— 500.com 抓取失败时的降级方案
- 🟡 `zgzcw.com` — 仅有让球盘，无胜平负直赔

### 串关陷阱

1. **竞彩@1.05法定下限**: 概率>67%的热门全部挤在@1.05，无法区分99%和70%优势
2. **子集枚举优于全量**: 4场全含EV仅为2场子集的40%，必须枚举所有子集大小
3. **中奖概率显示**: "总中奖概率143%"=多注概率之和(非互斥)，实为"期望中奖注数"

### 竞彩赔率数据源

中国竞彩 (sporttery.cn, lottery.gov.cn, jc.zhcw.com) 被 WAF 封锁。500.com (trade.500.com/jczq) 可通过 web_extract 正常抓取竞彩赔率。
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

### 赛前突发伤病扫描 ⚠️ NEW

现有 RSS 管线无法捕获赛前 24h 的突发球队公告（如 6/20 @BelRedDevils 宣布 Doku 因病缺席）。
预测生成后、交付用户前，必须对次日所有参赛队伍执行赛前伤病扫描。

**数据源（优先级从高到低）**：

| # | 来源 | 方法 | 频率 |
|---|------|------|------|
| 1 | ESPN 伤病追踪器 | `web_extract(\"https://www.espn.com/soccer/story/_/id/48572979/2026-fifa-world-cup-injuries-tracker\")` | 每日 1 次 |
| 2 | web_search 定向搜索 | `web_search(\"Team_Name World Cup 2026 injury news lineup OUT June XX\")` | 预测前 1-2h |
| 3 | 球队官方 X/Twitter | `web_search` 间接抓取 | 按需 |

**流程**：
1. 先抓 ESPN 伤病汇总 → 对照 injuries.json 更新
2. 对每个预测场次用 web_search 搜索"Team_A injury news World Cup June XX"
3. 发现新伤病 → 更新 injuries.json → **必须重跑预测**
4. 在最终报告中标注"⚠️ 赛前伤病扫描已执行"

### 手动录入比分陷阱 ⚠️ (累计 2 次：6/17 Iraq-Norway, 6/23 Norway-Senegal)

**案例 1 — Iraq 1-4 Norway 错录为 1-3**（6/17采集, 6/22纠正）
**案例 2 — Norway 3-2 Senegal 错录为 3-1**（6/23 cron采集, 同日纠正）

**共性**: 两起都是挪威比赛，score_b 偏差恰好 1 球，ESPN/BBC 赛后数小时内未更新完整比分（仅显示首轮数据），cron 采集时误用不完整数据。

**纠正时验证方法**（当 ESPN/BBC 未更新时）：
1. `web_search("Norway Senegal World Cup 2026 score")` — 搜索赛后报道
2. 社交媒体源（Instagram post-match accounts, Facebook news pages, NJ.com 等本地媒体）— 这些通常在终场哨响后 30 分钟内发布准确比分
3. 多源交叉确认（至少 2 个独立来源）后再写入

**教训**：
1. 手动录入比分后**必须执行数据完整性审计**（5 维检查）
2. 用户纠正比分时**无条件信任用户**，立即更新 `wc2026_results.json` + `wc2026_schedule.json` + 重新运行 `update_elo_from_results.py`
3. 任何时候看到报告中的比分与用户认知不符，**先查原始数据再辩解** — 数据正确性是底线
4. ⚠️ **cron 采集的比分不是最终真相** — ESPN/BBC 页面可能在赛后数小时仍为赛前状态。新录入比分需对照至少 2 个赛后报道源验证

### web_extract 比分解析陷阱

ESPN 等网站的 Team Stats 区块可能显示**部分进球数**而非全场比分。
例：6/21 Japan vs Tunisia，ESPN 页面 Team Stats 显示 Japan=2, Tunisia=1，
但 Facebook 进球直播证实为 4-0。用户纠正比分时**无条件信任用户**，
并立即更新 wc2026_results.json + 重跑 ELO 更新。

### 数据完整性审计底线

每次修改 wc2026_results.json 后，必须执行底线审计：

```python
# 1. 遗漏检查: schedule 中 date < today 但不在 results 中的比赛
# 2. 一致性检查: team_a/team_b/date 与 schedule 是否一致
# 3. 重复检查: match_id 是否唯一
# 4. 按日期统计: 赛程场次 vs 已采场次
```

**审计模板**: 用 execute_code 一次性输出 5 维检查（遗漏/今日/一致性/重复/按日统计）。
审计通过后再做任何预测或报告生成。

### 报告类型区分

| 类型 | 脚本 | 用途 | 交付物 |
|------|------|------|--------|
| 预测报告 | `generate_daily_report.py --date <date>` | 赛前发给用户 | report_<date>.pdf |
| 赛后简报 | 手动生成（MD+积分榜） | 赛后数据审计 | postmatch_<date>.md |

用户说"pdf发给我"时，确认是预测报告还是赛后简报，不要发错。

### RSS 情感分析 Graceful Degradation

详见 `references/rss-graceful-degradation.md` — 三层 fallback 设计模式。

### eloratings.net 数据采集

使用 `web_search("eloratings.net Team_Name")` 获取 search snippet 中的 ELO 数值。international-football.net 持续 429 限速。

## 每日预测管线 (v5.2)

```bash
cd /home/admin/wuhoo-workspace/skills/wuhoo/wuhoo-football-predictor

# 0. 数据保鲜
python3.11 scripts/check_football_freshness.py --quiet 2>&1

# 1. 采集历史赛果
python3.11 scripts/collect_results.py --check 2>&1
# 有遗漏→web_search→--manual 录入

# 2. 采集今日赛果（检查 schedule 中已过时但未采的比赛）
python3.11 scripts/collect_results.py --date <today> --manual '[...]' 2>&1

# 3. 赛前伤病扫描
# 抓 ESPN 伤病追踪器 + web_search 定向搜索明日所有球队

# 3.5. 获取明日天气 (v5.2)
python3.11 scripts/fetch_weather.py --tomorrow 2>&1
# 保存到 data/match_weather.json

# 3.6. 计算MD3出线动机 (v5.4 — 仅MD3阶段)
python3.11 scripts/compute_motivation.py --all-groups 2>&1

# 3.7. 计算半区路径难度 (v5.4)
python3.11 scripts/compute_bracket_path.py 2>&1

# 3.8. 更新第三名出线排名 (v5.4)
python3.11 scripts/compute_third_place.py 2>&1

# 4. 更新 ELO
python3.11 scripts/update_elo_from_results.py 2>&1

# 5. 拉取 RSS + 非结构化信号
python3.11 scripts/unstructured_extractor.py --teams "<tomorrow_teams>" 2>&1

# 6. 预测 (自动包含 v5.2 Layer 4a/4b)
python3.11 scripts/predict_by_date.py --tomorrow 2>&1

# 7. 生成报告 PDF
python3.11 scripts/generate_daily_report.py --date <tomorrow> 2>&1

# 8. 数据完整性底线审计
# 用 execute_code 运行 5 维检查（遗漏/今日/一致性/重复/按日统计）
```

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
- `references/system-health-check.md` — 系统健康检查清单（8 项审计 + 一键脚本）
- `references/data-freshness-workflow.md` — 数据保鲜刷新工作流、静态文件刷新、predict_next_n 存盘修复
- `references/injury-format.md` — injuries.json 格式规范与常见错误
- `references/friendly-data-collection.md` — 热身赛数据采集流程
- `references/polymarket-cross-validation.md` — Polymarket API 交叉验证
- `references/objective-factors-analysis.md` — 客观条件因子分析（降水/风力/温度/旅途疲劳/休息天数），含数据验证发现
- `references/manual-adjustments.md` — Layer 6 手动调整创建流程+Portugal案例+常见错误
- `references/knockout-stage-statistics.md` — WC1998-2022 淘汰赛历史统计 (94场), Poisson校准参数
- `references/matchday3-motivation-patterns.md` — MD3 出线动机分类框架 (QMF 6类型), 同时开球效应, 48队第3名出线阈值

## 常见陷阱

1. **injuries.json 键名错误**: 模型读取 `injuries` 键（不是 `teams`），用错会导致所有伤病数据不生效
2. **Team name 不匹配**: 必须用 ELO 数据中的规范名（`Bosnia and Herzegovina` 不是 `Bosnia`）
3. **form 因子假象**: 热身赛数据不全时 form 因子严重失真（1场→+25 vs 15场→+4）
4. **ELO 不更新就预测**: 必须先 `update_elo_from_results` 再 `predict_next_n`
5. **Polymarket 与模型背离**: Davies 伤缺导致 Canada 模型94.7% vs 市场53.5%——市场给伤病定了价
6. **重复添加热身赛**: 每次新增前检查 `(date, team_a, team_b)` 组合是否已存在（含反转）
7. **ELO 静默过期**: `collect_results.py` 采集赛果后不会自动调用 `update_elo_from_results.py`。Cron 必须显式链式调用，否则 ELO 永久停留在上次手动更新的时间点（如 6/13→6/22 期间 40 场赛果未反映）
8. **Schedule 不同步**: `wc2026_schedule.json` 不会自动从 `wc2026_results.json` 同步 `status`/`score_a`/`score_b`。每次采集赛果后需用 execute_code 脚本将 results 同步到 schedule
9. **injuries.json 静默过期**: 预置伤病数据在开赛后不会自动更新。Matchday 2/3 可能出现新的赛中伤病（如 Jérémy Doku 生病、Wataru Endo 退赛、Ruben Dias 缺阵），必须每天 web_search + ESPN 追踪器扫描
10. **⚠️ v5.2: style_category 是关键词自动分类，可能有误**: `team_profiles.json` 的 `style_category` 通过中文关键词规则自动生成（如 "技术"+"传控"→possession），存在误分类可能。手动复核 48 队分类结果后再投产
11. **⚠️ v5.2: Open-Meteo 免费 API 无 SLA**: 天气数据源 Open-Meteo 是免费服务，无可用性保证。已实现三重降级 (API→静态→0)，但极端情况下可能无法获取实时天气
12. **⚠️ v5.2: 客观条件因子权重很低**: 天气 5%、赛程 3%，设计意图是附加参考而非方向性判断。报告中已标注「实验性因子」，不可基于这些因子做决策
13. **⚠️ v5.2: predict_single_match 必须传入 match_id**: Layer 4a/4b 依赖 `match_id` 查找天气数据和计算赛程密度。调用 `predict_single_match()` 时若未传 `match_id`，天气和密度层会静默跳过（返回0）。`predict_by_date.py` 已修复，但 `wc2026_predict.py --match` 等直接调用模式需自行传入
14. **⚠️ v5.2: WMO 雷暴码 (85-99) 即使 precip=0mm 也判定为中/大雨**: Open-Meteo 的雷暴预报对应 WMO code 85-99，在 `fetch_weather.py` 中映射为 moderate/heavy rain。即使 `precipitation_sum=0mm`，雷暴预报本身代表了降水风险，模型仍然应用降水惩罚。这是设计行为而非 bug
15. **⚠️ cron 采集赛果不可盲信**: ESPN/BBC 页面在赛后数小时内可能仍显示赛前数据（仅首轮统计）。新采集的比分必须用 `web_search` 找至少 2 个独立赛后报道源（Instagram/Facebook 本地媒体/NJ.com 等）交叉验证。2 次挪威比赛出错（Iraq-Norway 1-4→1-3, Norway-Senegal 3-2→3-1）都是采集时用了未更新的 ESPN/BBC 数据
16. **⚠️ v5.4: ELO重复应用导致幅度偏大**: `update_elo_from_results.py` 在cron管线中被多次调用（14:30管线+15:00管线等），同一赛果可能被应用多次，导致ELO值方向正确但绝对值被放大。短期修复：在 `update_elo_from_results.py` 中加入去重检查（对比 `applied_results` 中的match_id）。MD3和淘汰赛开始前建议从 eloratings.net 手动采集基准ELO重新校准
17. **⚠️ v5.5: 推理引擎是wrapper模式**: `predict_v55.py` 包装 `predict_single_match`，引擎计算ELO delta后作为manual_adjustments注入。不要直接修改 `predict_single_match` 内部来集成引擎——wrapper模式避免了300+行代码的重新缩进
18. **⚠️ v5.5: 条件评估使用regex而非eval**: `evaluate_condition()` 使用 `re.match` 解析 `team.X == 'VALUE'` 模式，比 `eval()` 更安全。添加新条件模式时需同步更新regex列表
19. **⚠️ v5.5: 模板解析 `{{key}}` 从context取值**: 规则中的 `base_value: "{{motivation_elo}}"` 会在引擎中解析为 `context['motivation_elo']`。如果context中缺少该key，静默返回0
20. **⚠️ v5.5: tournament_form使用确定性种子**: `get_tournament_form()` 用 `sum(ord(c)*(i+1))` 做确定性hash，同一球队每次调用返回相同值。不要用 `random.gauss()` 直接调用——那会每次返回不同值

## Layer 6 — 手动调整 (v5.3 2026-06-23)

**数据文件**: `data/manual_adjustments.json`

用于记录模型其他层无法捕获的真实世界事件（队内矛盾、突发丑闻、场外干扰等），以 ELO 调整的形式直接注入 effective ELO。优先级最高——直接覆写其他层的累积结果。

### 文件格式

```json
{
  "last_updated": "2026-06-23T15:15:00+08:00",
  "adjustments": {
    "Portugal": {
      "elo_adjustment": -30,
      "reason": "队内信任裂痕: C罗当场怒斥门将...",
      "evidence": ["6/18 vs DR Congo 1-1: C罗0射正...", "..."],
      "expires": "2026-06-28",
      "confidence": "high"
    }
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `elo_adjustment` | int | ✅ | 直接加到 effective ELO。负=惩罚，正=奖励。建议范围 ±50 |
| `reason` | str | ✅ | 一句话摘要，嵌入报告 |
| `evidence` | list[str] | ✅ | 每条附带来源（媒体名/日期），用于验证和过期判断 |
| `expires` | str | 建议 | ISO 日期。过期后该调整应删除或review |
| `confidence` | str | 建议 | high/medium/low。low 时考虑减小幅度或跳过 |

### 自动加载

`scripts/predict_by_date.py` 调用 `predict_single_match()` 时自动加载 `data/manual_adjustments.json` 并传入 `manual_adjustments` 参数。无需额外 CLI 参数。

```python
# predict_by_date.py 内部
manual_adj = _load_manual_adjustments()
predict_single_match(..., manual_adjustments=manual_adj)
```

### 手动调用（单场测试）

```bash
# wc2026_predict.py 支持 --adj "Team:+N"
python3.11 wc2026_predict.py --match "Portugal" "Uzbekistan" --adj "Portugal:-30"
```

### 调整幅度指南

| 事件类型 | 建议幅度 | 示例 |
|----------|----------|------|
| 明星球员与队友公开冲突 | -20 ~ -40 | Portugal C罗 vs Costa (-30) |
| 教练下课/队内兵变 | -30 ~ -50 | — |
| 场外丑闻（队长涉法） | -25 ~ -45 | — |
| 极端球迷骚扰队友社媒 | -10 ~ -20 | Portugal 粉丝出征 B费/Neves |
| 飞机延误/旅途事故 | -5 ~ -15 | — |
| 主力门将赛前生病（非伤病追踪覆盖） | -10 ~ -20 | — |

> ⚠️ **原则**: 调整幅度应保守。Layer 6 设计用途是修正模型盲区，不是表达主观判断。每次添加必须附带至少 2 个独立媒体源的 evidence。

### 过期管理

每轮比赛后检查 `expires` 字段：
- 已过期的调整 → 删除该条或更新日期
- 事件已解决（如冲突公开和解）→ 删除
- 事件持续发酵 → 更新 evidence，考虑调整幅度

详见: `references/manual-adjustments.md`

## 模型-市场分歧分析（v5.1 例行）

每次 15:00 预测报告**必须**包含模型与市场赔率的分歧对比。

### 数据源
- **模型预测**: `predict_by_date.py` 输出的 team_a_win_pct / draw_pct / team_b_win_pct
- **市场赔率**: `web_extract(urls=["https://trade.500.com/jczq"])` 提取「非让球胜平负」

### 计算
```
市场隐含概率 = (1/赔率) / sum(1/所有赔率)   # 去水
分歧度 = |模型胜率 - 市场隐含概率|
```

### 判断标准
| 分歧度 | 标记 | 含义 |
|--------|------|------|
| > 15% | 显著分歧 | 模型与市场方向性差异 |
| 10-15% | 适度分歧 | 关注后续走势 |
| < 10% | 一致 | 模型与市场同步 |

### 简报格式
```
模型-市场分歧
| 比赛 | 模型 | 市场 | 分歧 | 提示 |
|------|------|------|------|------|
| 德国vs科特迪瓦 | 德37%/平25%/科38% | 德64%/平22%/科14% | 27% | 模型看平，市场碾压 |
```
高分歧场次附 1-2 句简短解读。

### 解读原则
- 只说「模型认为X，市场认为Y，分歧Z%」，不做胜负判断
- 客观陈述双方依据，让用户自行决策
- 参考历史案例：2018 德国 0-1 墨西哥（德国@1.44 模型看平）、2022 阿根廷 1-2 沙特（阿根廷@1.18 模型预警）

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
│   ├── compute_motivation.py     # v5.4: MD3出线动机自动分类
│   ├── compute_bracket_path.py   # v5.4: 淘汰赛半区路径难度
│   ├── compute_third_place.py    # v5.4: 第三名出线追踪
│   ├── inference_engine.py       # v5.5: 规则推理引擎(条件评估+置信度+饱和)
│   ├── data_provider.py          # v5.5: 动态数据抽象层(Context构建)
│   ├── predict_v55.py            # v5.5: 推理引擎wrapper(零侵入)
│   ├── phase0_rule_learning.py   # v5.5: 44场复盘网格搜索
│   ├── knockout_calibration.py   # v5.4: 淘汰赛行为校准(KBC)
│   ├── fetch_weather.py          # v5.2: Open-Meteo 天气采集
│   └── match_reminder.py       # 赛前1h提醒
├── data/
│   ├── elo_ratings.json        # 64队 ELO
│   ├── friendly_form_adjustments.json # 热身赛状态调整值
│   ├── match_weather.json      # v5.2: 比赛日天气预报缓存
│   ├── team_profiles.json      # 48队中英文元数据(含name_cn, style_category)
│   ├── venues.json             # 16场馆海拔/气候/坐标(含lat/lon)
│   ├── matchday3_motivation.json # v5.4: MD3动机分类数据
│   ├── bracket_paths.json        # v5.4: 淘汰赛路径难度
│   ├── third_place_standings.json # v5.4: 第三名排名
│   └── prediction_history.jsonl # 预测历史
├── references/
│   ├── rss-graceful-degradation.md
│   ├── friendly-form-algorithm.md
│   ├── daily-pipeline.md
│   └── v3.3-model-fix.md
└── configs/
    ├── tournaments.json
    ├── weights.json              # 遗留(未使用)
    └── rules_v1.json             # v5.5: 规则定义+交互约束+sigmoid参数
```

## 已知限制

1. **ELO 数据源不可靠**: international-football.net 持续 429，依赖 static fallback (2026-05-21)。ELO 更新完全依赖 `update_elo_from_results.py` 从赛果反推
2. **竞彩赔率为合成**: 无官方 API，71% 返奖率模型为最优替代
3. **Uruguay 无热身赛数据**: 47/48 队覆盖
4. **串关 EV 始终为负**: 竞彩 29% 抽水的结构性结果，报告已如实标注
5. **WeChat iLink 限流**: Cron 推送可能静默失败，`deliver=local,origin` 保底
6. **非结构化信号需 LLM 回填**: Layer 5.5 依赖 agent 侧调用 LLM 后 merge_llm_response，cron 自动运行无 LLM 支持时优雅降级为 0
7. **MD3/淘汰赛盲区 (v5.4计划)**: 当前模型未考虑出线动机(MD3轮换/生死战)、淘汰赛行为变化(进球-22%/平局+88%)、半区路径偏好。详见 `references/knockout-stage-statistics.md` + `references/matchday3-motivation-patterns.md` + `.hermes/plans/2026-06-24_000000-wc2026-md3-knockout-optimization.md`