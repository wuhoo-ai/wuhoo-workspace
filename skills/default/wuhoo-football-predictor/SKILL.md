---
name: wuhoo-football-predictor
description: WC2026 单场+全赛事预测系统 v5.11 — Elo+Poisson+Monte Carlo+LLM非结构化信号+客观条件因子+出线动机(QMF)+半区路径(BPP)+淘汰赛校准(KBC)+规则推理引擎(InferenceEngine)+Layer 6手动调整+全量推演(BracketSimulator)，12层模型栈，未来N场预测+全中文报告+体彩串关+数据保鲜检查
version: 5.11.0
dependencies:
  - wuhoo-news-rss
  - pandas
  - numpy
tags: ["wuhoo"]
category: wuhoo
---

# 足球赛事预测系统 v5.3

### v5.11.2 更新 (2026-07-18) — 决赛/季军赛管线修复（3个根因Bug）

**触发**: 预测F/3rd时发现休息天数取错（18/17天，应为4/3）+ 同场比赛被预测两次。

**修复（3个根因）**:
- ✅ **compute_schedule_density 只读小组赛schedule**: `wc2026_predict.py` 只加载 `wc2026_schedule.json`，淘汰赛prev-match完全不可见 → 修复：合并 `knockout_schedule.json` stages 到 matches 列表
- ✅ **wc2026_schedule.json 97-104为null占位条目**: 既挡住合并去重（match_id已存在）又无法匹配球队 → 修复：从 knockout_schedule + results 同步 team_a/team_b/round/status/score 到占位条目
- ✅ **predict_by_date 重复预测**: schedule同步后两个文件都含103/104 → 修复：按 (match_id, team_a, team_b) 去重
- ✅ **knockout标志Bug（历史性）**: `knockout=round.startswith('R')` 导致 QF/SF/F/3rd 全部未启用平局tiebreaker → 修复：白名单 `('R32','R16','QF','SF','F','3rd','Final')`。注意：本届QF/SF预测都跑在knockout=False下（仅影响平局note，不影响概率）
- ✅ **results重复条目**: M98/98 Spain-Belgium双录（字符串"M98" vs 整数98）→ 按(team_a,team_b,score_a,score_b,date)五元组去重
- ⚠️ **赛果录入时match_id格式必须与schedule一致（int）**，"M98"字符串格式会绕过去重

## 概述

基于 Elo 评分 + Poisson 分布 + Monte Carlo 模拟 + **LLM 非结构化信号** + **客观条件因子** + **Layer 6 手动调整** 的多层次预测系统。

### v5.6.1 更新 (2026-06-28) — ELO非对称降权 + 关键Bug修复

**触发**: 用户指出对称降权不合理——轮换还能赢球说明板凳深度强，不应降权。同时发现Poisson λ溢出和赛果status缺失两个Bug。

**修复**:
- ✅ **MD3 ELO非对称降权**: 锁定队赢球→K=60(全额)，平/输→K=30(降权)。见 `references/md3-locked-elo-dampening.md`
- ✅ **Poisson λ上限**: bracket_simulator 中 λ 上限 4.0，防止大ELO差时 λ 溢出（24.85→求和截断致概率颠倒）
- ✅ **赛果 status 补全**: 手动录入的MD3赛果缺失 `status: "completed"` → `update_elo_from_results.py` 静默跳过 → 已补全
- ✅ **FIFA官方对阵覆盖**: 用户明确指示淘汰赛对阵以FIFA官方为准。seed_knockout约束算法仅用于验证和降级，最终对阵始终用FIFA官方数据覆盖
- ✅ **最终推演**: France 41.8%, Argentina 38.3%, Mexico 8.0%（基于非对称ELO+λ上限+官方对阵）

### v5.11 更新 (2026-07-12) — SF 半决赛 PDF 适配 + 3模型分拆 + ELO轨迹注入

**触发**: SF 半决赛 PDF 的 3 模型对比表数值全部相同、ELO 轨迹缺失，用户指出「数值看起来不正常」。

**根因**: `predict_by_date.py` 的 daily JSON 只存 ensemble 值（无 Poisson/Logit 分模型），且 elo_trajectory 未注入 SF 管线。

**修复**:
- ✅ **gen_qf_pdfs.py SF 段**: 从 `sub_models` 读分模型、从 `e_data.trajectory` 读 ELO 轨迹
- ✅ **SF enrich 脚本**: 独立计算 Poisson(xG 全矩阵 0-7×0-7) + Logit(有序 Logit) + ELO trajectory
- ✅ **3 模型值不再相同**: Poisson 纯 xG 校准、Logit 纯 ELO 差校准、Ensemble = 管线综合
- ✅ **SF 赛程填充**: knockout_schedule.json SF 对阵 team_a/team_b 需手动填充（原为 null）
- ✅ **PDF 命名规范**: SF{id}_{TeamA}_vs_{TeamB}_{YYYYMMDD}.pdf，纯英文短路径投递

**陷阱**:
- ⚠️ **SF 赛程 team_a/team_b 为 null**: predict_by_date 需要先手动填入
- ⚠️ **微信投递 PDF 命名规范**: `{YYYYMMDD}_{TeamA_ISO}_{TeamB_ISO}.pdf`，下划线>2个或含短横线静默失败
- ⚠️ **Poisson 分模型需独立计算**: xG 全矩阵 0-7×0-7 枚举而非从 JSON 读取
- ⚠️ **赛程密度取错上一场**: pipeline 可能取到更早的比赛→休息天数异常（14天→应为4-5天），需手动修正 daily JSON 的 prev_match_id

**参考**: 原 `wuhoo-football-sf-pdf` skill 已合并入本 skill（2026-07-13），详见下文「v5.11.1 Skill 合并」章节。

### v5.11.1 更新 (2026-07-13) — Skill 合并 + 单场 PDF 统一

**触发**: 用户发现存在两个 WC2026 预测 skill（wuhoo-football-predictor 和 wuhoo-football-sf-pdf），使用中存在困惑。后者是 7/12 SF 阶段的紧急补丁。

**合并内容**:
- ✅ **新脚本 `scripts/enrich_predictions.py`**: 从 sf-pdf inline 代码提取，独立可运行 + 可作为模块导入
  - Poisson 分模型（xG 全矩阵 0-7×0-7）
  - Logit 分模型（ordered_logit 查表）
  - ELO 轨迹注入
  - 支持 `--date` / `--all` / `--latest` CLI
- ✅ **`gen_qf_pdfs.py` → `gen_match_pdf.py` 重命名 + 全面升级**:
  - 修复所有硬编码 "QF" → 动态 round 检测
  - 统一 QF+SF 双路径 → 单一 daily_predictions 读取
  - Auto-enrich: sub_models 缺失时自动计算（无需手动 enrich）
  - 小组赛+淘汰赛通用（支持 GS1-3/R32/R16/QF/SF/F/3rd）
  - 新增 `--date` / `--round` / `--no-enrich` CLI 参数
- ✅ **`generate_single_match_pdf.py` 标记为 deprecated**: 保留用于向后兼容
- ✅ **删除 `wuhoo-football-sf-pdf` skill**: 内容全部合并入本 skill
- ✅ **陷阱合并**: sf-pdf 独有陷阱（3模型相同、ELO轨迹缺失、休息天数14天Bug等）已整合

**简化后的单场 PDF 工作流**:
```bash
# 旧（3 步，enrich 需手动 inline 代码）
python3.11 scripts/predict_by_date.py --date 2026-07-15 --news
python3.11 -c "…(40行enrich代码)…"
python3.11 scripts/gen_qf_pdfs.py

# 新（2 步，auto-enrich 内置）
python3.11 scripts/predict_by_date.py --date 2026-07-15 --news
python3.11 scripts/gen_match_pdf.py --date 2026-07-15
```

### v5.10.1 更新 (2026-07-08) — QF单场PDF完整版 + 推演报告增强

**触发**: 用户要求QF预测报告包含教练/阵容/技战术/伤病/场地/天气/旅途/本届表现/新闻等全部信息用于决策。

**新增/变更**:
- ✅ **gen_qf_pdfs.py 完全重写** (v5.10→v5.10.1): 从1页裸预测→3页10模块完整分析
  - [风格战术] 两队战术对比（阵型/主帅/进攻/防守/转换/定位球/优势/短板/核心球员）
  - [伤病报告] 球员伤停明细 + ELO扣分合计
  - [教练/磨合] FIFA排名/教练/阵容稳定/团队化学/风格
  - [场地/天气/旅途] venue+Open-Meteo天气+近两场旅途
  - [本届比赛表现] 每场比分+胜负记录+总得失球
  - [新闻/RSS] 近5日相关报道（RSSHub+BBC+懂球帝+卫报）
  - [ELO实力+轨迹] ELO汇总+动态轨迹因子
  - [预测模型] Ensemble/Poisson/Logit三模型对比
  - [比分概率] **Top 5** Poisson全矩阵(0-5×0-4=30组合排序)
  - [判定] 综合预测+置信度+数据源清单
- ✅ **gen_bracket_pdf.py 增强**: 冠军概率+晋级路径矩阵+QF详情+暗马预警+方法论
- ✅ **日期自动解析**: knockout_schedule → bracket_recursive_results 双重降级，解决QF赛程日期为"?"问题
- ✅ **比分从Top 3 → Top 5**: Poisson独立计算全矩阵，不依赖JSON中仅有的3条
- ✅ **RSS HTML清理**: nohtml()预处理，防止ReportLab Paragraph解析崩溃

**陷阱**:
- ⚠️ **knockout_schedule QF team_a/team_b为null**: QF对阵尚未写入schedule，需从bracket_recursive_results.json取日期
- ⚠️ **match_weather QF forecast team_a/team_b为None**: 天气按venue匹配而非team
- ⚠️ **RSS summary含HTML标签**: 需nohtml()清理后再入Paragraph，否则ReportLab报unclosed tags
- ⚠️ **v5.10 JSON仅含3条scoreline**: 需从expected_goals独立计算Poisson全矩阵

### v5.9 更新 (2026-07-04) — R16 全面升级 + Cron 合并 + 递归推演

**触发**: R32 全部完赛，16 强产生。Cron 从 3 个合并为 1 个 14:30，新增递归单场推演替代 bracket_simulator，v5.5 推理引擎默认启用。

**新增/变更**:
- ✅ **Cron 合并**: 删除 `5154715032ec`(14:30) / `86912ff0a4aa`(15:00) / `0b1749fba510`(15:30)，新建 `c1e357b05736`(14:30 统一执行全部管线)
- ✅ **递归推演**: `scripts/bracket_recursive.py` 替代 `bracket_simulator.py`。每场用完整 12 层栈（含 v5.5 推理引擎）预测，5000 次 Monte Carlo 递归推进。输出 `bracket_recursive_results.json`
- ✅ **v5.5 默认启用**: `predict_by_date.py` 默认调用 `predict_with_engine()`（v5.5 wrapper），不再需要手动开启。失败时自动降级到 `predict_single_match()`
- ✅ **ELO 去重保护**: `update_elo_from_results.py` 改用 `(team_a, team_b, score)` 三元组去重，解决 2211→91 的 ELO 重复应用问题
- ✅ **knockout_schedule 自动读取**: `predict_by_date.py` 现在同时读取 `wc2026_schedule.json` 和 `knockout_schedule.json`，淘汰赛对阵自动纳入预测
- ✅ **战术数据扩展**: `team_tactics.json` 从 24→29 队，R16 全部 16 队覆盖（新增 Paraguay/Canada/Morocco/Brazil/USA）
- ✅ **规则学习全量**: phase0_rule_learning 应从所有已完成比赛（88 场）学习，非仅 44 场小组赛
- ✅ **推送顺序**: 单场 PDF 优先 → 推演报告 PDF（按场次拆分，<100KB）

**关键陷阱**:
- ⚠️ **predict_by_date 旧 schedule 有 null 队名残留**: 小组赛 schedule 中的 TBD 比赛会混入结果。修复：从 knockout_schedule.json 读取后过滤 `team_a/team_b` 为 null 的匹配
- ⚠️ **bracket_recursive QF/SF/F 无队名**: 初始 team_a/team_b 为 null，需在 Monte Carlo 循环中从上一轮胜者动态解析（`source: "W89 vs W90"` → 查 `winners[89]`/`winners[90]`）
- ⚠️ **低 sims 统计噪声大**: <100 次 Monte Carlo 冠军概率可能有 10-20% 波动。默认 5000 sims 已消除此问题，概率稳定在 ±2% 以内。减少 sims 仅用于快速验证

**触发**: 用户发现 PDF 报告始终缺少球队风格战术分析，且 daily_predictions JSON 缺少比分概率分布。

**修复**:
- ✅ **战术模块实现**: `_add_tactical_section()` 从空壳改为完整实现——阵型/教练窄表 + 攻防优缺段落式排版（避免 A4 溢出）
- ✅ **战术数据补全**: `team_tactics.json` 新增 6 队（阿根廷/哥伦比亚/加纳/澳大利亚/埃及/佛得角），覆盖 24 队
- ✅ **比分概率输出**: `predict_by_date.py` 和 `predict_next_n.py` JSON 输出增加 `scoreline_probs`、`expected_goals_a/b`
- ✅ **Cron 修复**: 15:00 预测 job 更新为 `--tomorrow`（原为今天剩余比赛）
- ✅ **PDF 格式修复**: 战术表从 3 列宽表改为段落式，防止溢出 A4

### v5.8.0 更新 (2026-06-30) — 球队风格战术概述

**触发**: 用户要求在PDF报告中增加球队风格和战术概述。

**新增功能**:
- ✅ **战术数据库**: `data/team_tactics.json` — 球队完整战术档案（阵型、主帅、风格、进攻/防守策略、优劣势、转换、定位球、核心球员、本届表现）
- ✅ **PDF战术模块**: `generate_single_match_pdf.py` 新增 `[风格战术]` 模块，于ELO层之前渲染两队战术对比
- ✅ **独立加载**: PDF生成器独立加载 `team_tactics.json`，不依赖预测管线修改
- ✅ **数据来源**: web_search 采集（Guardian/Squawka/The Athletic/TacticalFootballAnalysis等战术分析源）

**数据结构** (team_tactics.json):
```json
{
  "France": {
    "formation": "4-2-3-1 / 4-3-3",
    "coach": "Didier Deschamps (执教第14年)",
    "style_summary": "攻守平衡的锦标赛型球队...",
    "attacking": "快速纵向推进...",
    "defensive": "4-4-2中位防守block...",
    "strengths": ["转换进攻世界顶级", ...],
    "weaknesses": ["阵地战破密集能力一般", ...],
    "key_players": ["Kylian Mbappé (FW)", ...],
    "set_pieces": "定位球威胁中等...",
    "transitions": "由守转攻世界顶级...",
    "tournament_form_note": "小组赛3场全胜..."
  }
}
```

**扩展方式**: 新增球队往 `team_tactics.json` 添加条目即可，PDF自动渲染。当前覆盖24队。

**⚠️ 战术模块验证陷阱（2026-07-03 教训）**:
v5.8.0 在 SKILL.md 中记录了战术功能，但实际代码中 `_add_tactical_section()` 只有空壳（`return` 静默跳过），且 `team_tactics.json` 只覆盖了 18 队（不含当天的 6 队）。PDF 生成器正常运行但只输出「数据暂缺」，**不会报错**。用户反复提醒"没有战术分析"才暴露。
修复后必须验证：
1. `team_tactics.json` 包含当日所有出赛队伍
2. PDF 中有 `[风格战术] 球队战术对比` 表格（阵型/教练/风格/进攻/防守/转换/定位球/核心球员）
3. 验证命令：`python3.11 -c "import json; t=json.load(open('data/team_tactics.json')); print([k for k in ['Argentina','Colombia','Ghana','Australia','Egypt','Cape Verde'] if k not in t])"` — 输出为空则覆盖完整

### v5.7.0 更新 (2026-06-28) — 比分概率分布

**触发**: 用户要求每场预测增加比分概率分布。

**新增功能**:
- ✅ **比分概率分布**: `predict_single_match()` 返回 Top 3 或概率 >10% 的比分及概率
- ✅ **PDF 比分表**: `generate_single_match_pdf.py` 新增`比分概率分布`模块（比分/概率/累计三列，标注胜负方）
- ✅ **终端输出**: `print_match_prediction()` 在胜平负后输出各比分概率
- ✅ **自动继承**: `predict_by_date.py` 无需改动，比分概率自动写入 daily JSON

**输出规则**:
- 展示 Top 3 个比分，若第 4+ 比分概率 >10% 也展示
- 每个比分标注胜负方: `2-0 (阿根廷胜)`
- 保留累计概率列
- 仅展示 90 分钟结果，不含加时

### v5.6.1 关键修复 (2026-06-28)

**修复**:
- ⚠️ **λ 溢出**: `bracket_simulator.py` 中 Poisson λ 未设上限，极端 ELO 差时 λ 可达 24.85，导致概率求和截断（0-11 球范围遗漏大量概率质量）→ 阿根廷 9% vs 佛得角 91%。**修复: λ 上限 4.0**
- ⚠️ **ELO 非对称降权**: MD3 锁定出线球队仅对平/输降权 K=30，赢球保持 K=60（轮换能赢=板凳深度强）
- ⚠️ **中文队名**: `generate_single_match_pdf.py` 的 `cn()` 函数从 `TEAM_PROFILES` 顶层查找队名，但实际数据在 `TEAM_PROFILES['teams']` 下 → 南非/加拿大等队名显示英文。**修复: 改为 `_TEAMS = TEAM_PROFILES.get('teams', TEAM_PROFILES)`**
- ⚠️ **淘汰赛日期**: knockout_schedule.json 使用 FIFA 原文的北美当地时间，未转北京时间（时差+12~15h，所有比赛+1天）。**修复: 统一+1天**
- ⚠️ **FIFA 对阵覆盖**: `seed_knockout.py` 的约束算法与 FIFA 官方 495 项对照表结果不同。**修复: 手动覆盖为 FIFA 官方对阵，seed_knockout.py 检测 `_source='FIFA'` 时跳过写回**
- ⚠️ **赛果漏采**: M67-M72 缺少 `status='completed'` → ELO 更新跳过。**修复: 补全 status**

### v5.6.0 更新 (2026-06-28) — 淘汰赛阶段升级

**触发**: 小组赛结束（54/72 完赛），6/29 起进入 R32 淘汰赛阶段（32 场比赛，7/19 Final）。

**新增功能**:
- ✅ **淘汰赛赛程**: `data/knockout_schedule.json` — 32 场比赛（R32→R16→QF→SF→F→3rd），基于 FIFA 官方公告
- ✅ **种子排位**: `scripts/seed_knockout.py` — 从小组赛结果计算 R32 对阵（12 组前两名 + 8 个最优第三名）
- ✅ **全量推演**: `scripts/bracket_simulator.py` — 5000 次 Monte Carlo 推演全部剩余淘汰赛（ELO+Poisson+KBC分轮次校准）
- ✅ **推演报告**: `scripts/generate_bracket_report.py` — 冠军概率/晋级路径/暗马预警 Markdown 报告
- ✅ **每日 Cron**: 新增 15:30 全量推演 job（`0b1749fba510`）
- ✅ **KBC v5.6**: 按轮次分层（R32:0.75→F:0.88）+ 防守型+10/传控-5 风格加成 + 弱队300+→+30
- ✅ **推理规则**: +5 条（KO_001/002/003, REC_001, CHM_001）淘汰赛/近期表现/磨合规则
- ✅ **数据保鲜**: Portugal -30 手动调整已删除（6/28 过期），manual_adjustments 清空
- ✅ **Cron 更新**: 14:30/15:00 job 移除小组赛限制，适配淘汰赛

**已知差异**:
- ✅ R32对阵已以FIFA官方公告为准覆盖（16/16匹配）。用户明确指示"淘汰赛名单和赛程要以官方为准"——任何时候优先FIFA官方对阵，不依赖约束算法输出。
- ⚠️ 第三名分配约束算法 vs FIFA 495项对照表: 算法产出的合法分配可能与FIFA公告不同。算法用于快速验证和降级方案，最终对阵始终以FIFA官方为准。

### v5.5.0 更新 (2026-06-24) — 规则推理引擎

**触发**: 12层ELO天真加法叠加存在结构性缺陷：无交互效应、无置信度衰减、无饱和约束。需要从"逐步加ELO"进化为"带约束的推理系统"。

- ✅ **新增 `scripts/inference_engine.py`**: 规则驱动的推理引擎。支持条件评估(regex)、模板解析(`{{key}}`)、置信度缩放、交互约束、sigmoid饱和
- ✅ **新增 `scripts/data_provider.py`**: 统一数据抽象层。动态构建Context dict，支持freshness检查和模板注入
- ✅ **新增 `scripts/predict_v55.py`**: v5.5推理包装器。零侵入设计——引擎计算ELO delta → 作为manual_adjustments注入现有管线
- ✅ **新增 `scripts/phase0_rule_learning.py`**: 44场完赛复盘+网格搜索学习最优参数
- ✅ **新增 `configs/rules_v1.json`**: 16条规则定义(14层+2交互) + 4条交互约束 + sigmoid参数
- ✅ **规则学习结果**: 基线准确率70.5%(44场), 13/13错误全是漏判平局, 交互系数通过网格搜索标定
- ✅ **推理路径报告**: 每条规则显示原始值→置信度折扣→交互修正→最终值，保留足够信息供人工决策
- ✅ **推理路径渲染**: `generate_daily_report.py` — 上限80行全量trace（从30行扩展），新增规则明细表格（优先级/原始值/置信度/交互修正/最终值），引擎增量行显示在有效ELO汇总中
- ✅ **单场PDF生成器**: `generate_single_match_pdf.py` — ReportLab直出，无emoji乱码，按场次拆分，每份50KB左右，含完整12层数据源标注+RSS报道+推理路径
- ✅ **A/B双轨**: `rules_v1.json`(生产) / `rules_v2.json`(实验), `--rules-version v2`切换
- ✅ **向后兼容**: `use_inference_engine=True` 默认启用（v5.9 起），`predict_by_date.py` 自动调用 `predict_with_engine()`。失败时降级到 `predict_single_match()`
- ⚠️ **wrapper模式**: 引擎通过predict_v55.py包装调用, 未修改predict_single_match内部

### v5.5.0 更新 (2026-06-24) — 规则推理引擎重构

**触发**: 12层天真加法叠加存在6个结构性缺陷（无交互、无置信度、无饱和、无动态数据、无权重、无可解释性）。引入离散规则+概率框架替代ELO加法。

- ✅ **新增 `scripts/inference_engine.py`**: 规则推理引擎 — 条件评估(正则+eval)、交互约束(conflicts/amplified/dampened)、sigmoid饱和、置信度缩放(high=1.0/medium=0.7/low=0.4)、推理trace格式化
- ✅ **新增 `scripts/data_provider.py`**: 动态数据抽象层 — freshness检查、context构建、模板值注入
- ✅ **新增 `scripts/predict_v55.py`**: 零侵入wrapper — 引擎计算ELO delta→作为manual_adjustments传入原管线→注入推理trace
- ✅ **新增 `configs/rules_v1.json`**: 16条声明式规则(14层+2条覆写) + 4条交互约束(INT_001~004)
- ✅ **新增 `scripts/phase0_rule_learning.py`**: 44场完赛回测→网格搜索5个交互系数+2个sigmoid参数→最优参数写入rules_v1.json
- ✅ **`scripts/generate_daily_report.py` 更新**: 新增[v5.5推理路径]模块（80行全量trace）、`🧠 规则明细`表格（每队12条规则的优先级/原始值/置信度/交互修正/最终值）、🧠引擎增量行、🎯MD3动机badge。推理路径渲染上限从30行→80行，inference_trace结构化数据转为markdown表格
- ✅ **Cron更新**: 14:30加compute_motivation+compute_third_place；15:00改用predict_v55.py引擎
- ✅ **推理路径报告**: 每条规则显示原始值→置信度折扣→交互修正→最终值，保留足够信息供人工决策
- ✅ **推理路径渲染**: `generate_daily_report.py` — 上限80行全量trace（从30行扩展），新增规则明细表格（优先级/原始值/置信度/交互修正/最终值），引擎增量行显示在有效ELO汇总中
- ✅ **单场PDF生成器**: `generate_single_match_pdf.py` — ReportLab直出，无emoji乱码，按场次拆分，每份50KB左右，含完整12层数据源标注+RSS报道+推理路径
- ✅ **A/B双轨**: `rules_v1.json`(生产) / `rules_v2.json`(实验), `--rules-version v2`切换
- ⚠️ **venue/weather/density未传入引擎context**: 当前为0，需从predict_single_match提取

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

- ✅ **SKILL.md 去重**: 删除 `~/.hermes/skills/default/wuhoo-football-predictor/`，只保留 workspace 副本，解决 skill_view ambiguous 错误
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
- ⚠️ **技能碰撞问题**: `wuhoo-football-predictor` 同时存在于 `~/.hermes/skills/` 和 `~/wuhoo-workspace/skills/`，导致 cron job 运行时 skill 无法加载（输出 `Skill(s) not found and skipped`）。如需修复，删除 `~/.hermes/skills/default/wuhoo-football-predictor/` 只保留 workspace 版本。
- 📋 **赛后数据更新流程** → [references/post-match-workflow.md](references/post-match-workflow.md)

| v4.4 更新 (2026-06-12) — 伤病数据刷新+Polymarket交叉验证
|- ✅ **伤病数据大更新**: 从 ESPN/The Athletic 采集 Canada(Davies OUT), USA(Cardoso OUT), Brazil(Neymar/Rodrygo), Netherlands(Timber/Simons) 等9队最新伤病
|- ✅ **injuries.json 格式规范**: 必须使用 `injuries` 键（非 `teams`），每队含 `total_penalty` + `players[]`（name/position/status/injury/elo_penalty），见 `references/injury-format.md`
|- ✅ **热身赛数据补全**: 从 ESPN 补充 USA 14场 + Paraguay 9场，数据源见 `references/friendly-data-collection.md`
|- ✅ **Polymarket 交叉验证**: 使用 Gamma API 查询预测市场赔率并与模型对比，发现 Davies 伤缺被市场定价为 Canada 胜率从94.7%→53.5%
|- ✅ **predict_next_n.py 优化**: --n 2 覆盖未来2场（6.13仅2场），需先 collect_results 后 update_elo_from_results 再预测

| v4.3 更新 (2026-06-11) — 中文报告+体彩串关+竞彩赔率
### v2.1 更新 (2026-07-03) — 比分概率修复 + JSON 格式增强 + Cron 日期修复

**触发**: 用户查询葡萄牙vs克罗地亚 0:0 概率时发现 daily_predictions JSON 中缺少比分概率分布（scoreline_probs / expected_goals_a / expected_goals_b）。同时发现 15:00 cron 预测的是当天比赛而非明天比赛。

**根因 (JSON)**:
- `predict_next_n.py` 保存 JSON 时直接用原始 `all_audits`（嵌套 audit 结构），未提取 `wc2026_predict.py` 中 `predict_single_match()` 已计算的 Poisson 比分数据
- `predict_by_date.py` 的 `save_reports()` 同样遗漏了 `expected_goals_a`、`expected_goals_b`、`scoreline_probs` 三个字段

**根因 (Cron)**: 15:00 cron job 使用了 `--all-today-remaining` 参数，预测的是当天剩余比赛，但 15:00 时今天比赛已经/即将开始。应该用 `--tomorrow` 预测次日比赛。

**修复**:
- ✅ `predict_next_n.py` 新增扁平化 `predictions` 列表，每场比赛包含：`scoreline_probs`（Top 3）、`expected_goals_a`、`expected_goals_b`
- ✅ `predict_by_date.py` 同步补全 `expected_goals_a`、`expected_goals_b`、`scoreline_probs` 三个字段
- ✅ 保留原始 `matches`（raw audit）用于调试
- ✅ Cron `86912ff0a4aa` 更新为 `--tomorrow`（predict_by_date.py --tomorrow 而非 predict_next_n.py --all-today-remaining）
- ✅ 输出格式与已有 daily_predictions JSON 兼容

**数据样例**:
```json
{
  "predictions": [{
    "team_a": "Portugal", "team_b": "Croatia",
    "expected_goals_a": 1.67, "expected_goals_b": 1.10,
    "most_likely_score": "1-1",
    "scoreline_probs": [
      {"score": "1-1", "prob_pct": 11.5},
      {"score": "1-0", "prob_pct": 10.5},
      {"score": "2-1", "prob_pct": 9.6}
    ]
  }]
}
```

**陷阱**:
- `predict_score()` 的 `scores` 字典含完整 49 种比分概率，但 `scoreline_probs` 仅取 Top 3。需 0:0 等低频比分时用 expected_goals 手算：`P(0:0)=e^(-λ_a)×e^(-λ_b)`
- **两个脚本都需同步修复**：`predict_next_n.py` 和 `predict_by_date.py` 各自维护了独立的 JSON 序列化逻辑，修复一者必须修复另一者
- **Cron 必须用 `--tomorrow` 而非 `--all-today-remaining`**：15:00 时今日比赛已进入/接近开赛，预测明天才有意义

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
| 球队元数据 | `team_tactics.json` | 7d | 30d | web_search 采集 + 手动更新 |
| 基础设施 | `venues.json` | 30d | 60d | 静态，赛事期间不变 |
| 基础设施 | `group_venues.json` | 30d | 60d | 静态 |

### 静态文件刷新

赛事基础设施文件（venues、team_profiles、schedule、metadata、group_venues）内容本身在赛事期间不变，但元数据时间戳可能过期。刷新时只需更新 `updated` 字段和元数据 — 不改变核心数据内容。赛程表可同步 `wc2026_results.json` 中的赛果。

## CLI 命令

```bash
# === v5.9: 递归单场推演 (NEW — 替代 bracket_simulator) ===
# 递归推演：每场完整12层预测 + 10次Monte Carlo递归
python3.11 scripts/bracket_recursive.py                    # 5000 sims (默认，稳定概率)
python3.11 scripts/bracket_recursive.py --sims 100         # 快速验证
python3.11 scripts/bracket_recursive.py --sims 10000       # 超高精度
python3.11 scripts/bracket_recursive.py --from-round R16   # 从R16开始
# 输出: data/bracket_recursive_results.json (含每场详细预测 + 冠军/晋级概率)
#      data/reports/bracket_recursive_YYYYMMDD_HHMM.md

# 推演报告
python3.11 scripts/generate_bracket_report.py --from-json data/bracket_recursive_results.json
# 输出: data/reports/bracket_report_YYYY-MM-DD.md

# === v5.6: 淘汰赛全量推演 (DEPRECATED — 用 bracket_recursive 替代) ===
# 种子排位（从小组赛结果计算R32对阵）
python3.11 scripts/seed_knockout.py
python3.11 scripts/seed_knockout.py --dry-run

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

# === v5.5: 单场PDF报告（干净排版+数据源标注+RSS+推理路径）===
# 生成第N场比赛的单场PDF（1-indexed）
python3.11 scripts/generate_single_match_pdf.py 1    # 瑞士 vs 加拿大
python3.11 scripts/generate_single_match_pdf.py 2    # 波黑 vs 卡塔尔
# 输出: data/reports/single/report_<中文队名>_vs_<中文队名>.pdf (~50KB/场)
# ReportLab直出，无emoji乱码，12层数据源标注，含RSS报道和v5.5推理路径

# 生成单场PDF报告(v5.5模板，含客观条件+RSS+推理路径)
python3.11 scripts/generate_single_match_pdf.py --date 2026-06-25 --all
# 输出: data/reports/single/report_YYYY-MM-DD_主队_vs_客队.pdf (每场50-60KB)
# 详见: references/single-match-pdf-generator.md

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

## Cron 配置 (v5.9 — 2026-07-04 合并)

### 统一 Cron Job（14:30 每日执行）

单个 Cron Job 执行全部管线：`c1e357b05736`，14:30 每日触发，`deliver=local,origin`。

**管线程步骤**:
1. 数据保鲜检查（check_football_freshness.py --quiet）
2. 采集赛果（**回溯前 2 天** — 不只用 collect_results.py --check 查当天，还要检查 schedule 中 date < today 且不在 results 中的比赛 → web_search → --manual）
3. 更新 ELO（update_elo_from_results.py，带去重保护）
4. 同步 schedule + knockout_schedule（赛果 + 对阵填充）
5. 伤病扫描（ESPN + web_search 定向搜索）
6. 天气采集（fetch_weather.py --tomorrow）
7. 明日预测（predict_by_date.py --tomorrow --news，v5.5 引擎默认启用）
8. 生成单场 PDF（generate_single_match_pdf.py --date tomorrow --all）
9. 递归推演（bracket_recursive.py --sims 5000）
10. 推演报告（generate_bracket_report.py --from-json）
11. 串关建议（lottery_parlay.py）
12. 数据完整性审计
13. 推送（单场 PDF → 推演报告 PDF → 摘要）

**推送顺序（用户指定）**: 先各单场 PDF → 推演报告 PDF（按场次拆分确保 <100KB）→ 每日摘要

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
cd /home/admin/wuhoo-workspace/skills/default/wuhoo-football-predictor

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

29. **⚠️ v5.6: TEAM_PROFILES 嵌套结构**: `team_profiles.json` 使用 `{"teams": {...}}` 格式。`cn()` 需用 `_TEAMS = TEAM_PROFILES.get('teams', TEAM_PROFILES)` 而非直接 `.get(team_en)`。
30. **⚠️ v5.6: 淘汰赛日期时区**: FIFA 赛程用北美当地时间，需 +1 天转北京时间。32 场全部需修正。
31. **⚠️ v5.6: seed_knockout 覆盖 FIFABracket**: 约束算法结果与 FIFA 495 项对照表不同。每次运行 `seed_knockout.py` 会覆盖手动设置的官方对阵。**修复: 检测 `_source='FIFA'` 时跳过写回**。
32. **⚠️ v5.6: MD3 ELO非对称降权 — 赢球不降**: 锁定球队轮换赢球保持 K=60，平/输才降 K=30。对称降权（赢也降）被用户否定："轮换都能大胜，上主力岂不是更厉害？"详见 `references/elo-md3-asymmetric-dampening.md`。
34. **⚠️ v5.7: 比分概率输出规则**: Top 3 或概率 >10%。标注胜负方 `2-0 (阿根廷胜)`。保留累计概率列。仅 90 分钟结果。`predict_score()` 返回的 `scores` 字段包含完整 49 种比分概率，`predict_single_match` 自动提取。
35. **⚠️ v5.8: 战术模块静默失败 — SKILL.md 声称已实现但代码是空壳**: `_add_tactical_section()` 在 PDF 生成器中只有 `return` 一行，`team_tactics.json` 未覆盖当天比赛球队。PDF 正常生成但不含战术内容，无任何报错。验证：检查 PDF 含 `[风格战术] 球队战术对比` 表格 + 确认 `team_tactics.json` 覆盖所有出赛队伍。

36. **⚠️ v5.8.1: PDF 阵型/教练表格排版错误 — 中文文本溢出列宽无法阅读**: 阵型和教练信息放在 ReportLab 窄表格（col_widths=[50, 110, 110]）中，中文队名和长文本（如 "4-2-3-1 / 4-3-3 (灵活切换)"）超出列宽导致排版崩溃。**修复: 移除表格，改为段落式排版** — 阵型+教练放在段落首行（`阵型: ... | 主帅: ...`），其余战术信息保持段落格式。修改位置: `generate_single_match_pdf.py` 的 `_add_tactical_section()`。

37. **⚠️ v5.8.1: 淘汰赛赛果录入数据完整性底线 — 必须检查 date_beijing/penalties/aet/round 字段**: 手动录入 R32 淘汰赛赛果时容易遗漏关键字段。**每次录入后必须检查**：
   - `date_beijing`：与 `date` 字段一致（北京时间），缺失会导致历史比赛数据显示空白
   - `penalties`：PK 决胜的比赛必须有（如 `"3-4"` 或 `"PK"`）
   - `aet`：加时赛的比赛必须设为 `true`
   - `round`：淘汰赛比赛必须有（`"R32"`/`"R16"`/`"QF"` 等）
   - `winner`：淘汰赛必须显式标注胜者（即使能从比分推断）
   验证命令见 `references/data-quality-checklist.md`

38. **⚠️ v5.8.1: ELO applied_results 必须去重**: `update_elo_from_results.py` 在 cron 管线中被多次调用时，同一赛果可能被重复应用。已修复为按 `(team_a, team_b, score)` 三元组去重（同时检查正反序）。cron agent 调用时必须确保 `update_elo_from_results.py` 在 `collect_results` 之后、`predict_by_date` 之前执行。

39. **⚠️ v5.8.1: predict_by_date.py 不读取 knockout_schedule.json**: 原脚本只从 `wc2026_schedule.json` (小组赛赛程) 读取比赛。淘汰赛阶段需要同时读取 `knockout_schedule.json`。已修复: `predict_by_date()` 函数中增加 knockout schedule 查找逻辑，自动识别 `round` 字段并设置 `knockout=True`。

40. **✅ v5.8.1: v5.5 推理引擎默认启用**: `predict_by_date.py` 现在默认使用 `predict_with_engine()`（v5.5 wrapper），`bracket_recursive.py` 同样。`use_inference_engine` 不再需要手动传入。降级: 如 `predict_v55` 导入失败则回退 `predict_single_match`。
34. **⚠️ v5.7: Poisson λ 溢出**: `bracket_simulator.py` 用指数公式 λ=1.45×10^(diff/500)，极端 ELO 差时 λ 可达 24.85 → 概率求和截断 → 强队被低估。**修复: λ 上限 4.0**（`wc2026_predict.py` 已用线性公式+上限 3.0，不受影响）。

## 数据源维护

| 文件 | 更新方式 | 频率 |
|------|---------|------|
| `elo_ratings.json` | `fetch_elo.py --diff` + `update_elo_from_results.py` | 赛前+赛后 |
| `friendly_matches.json` | ESPN 手动采集 → `fetch_friendlies.py --compute-form` | 有新知即补 |
| `injuries.json` | ESPN/The Athletic/BBC/Fox Sports → 手动更新 | 赛前每 1-2 天必查 |
| | | 刷新流程见 [references/injury-data-refresh.md](references/injury-data-refresh.md) | |
| `wc2026_results.json` | `collect_results.py` | 赛后立即 |

见参考文档：
- `references/md3-locked-elo-dampening.md` — v5.6.1 MD3锁定出线ELO非对称降权技术文档
- `references/system-health-check.md` — 系统健康检查清单（8 项审计 + 一键脚本）
- `references/data-freshness-workflow.md` — 数据保鲜刷新工作流、静态文件刷新、predict_next_n 存盘修复
- `references/injury-format.md` — injuries.json 格式规范与常见错误
- `references/friendly-data-collection.md` — 热身赛数据采集流程
- `references/polymarket-cross-validation.md` — Polymarket API 交叉验证
- `references/objective-factors-analysis.md` — 客观条件因子分析（降水/风力/温度/旅途疲劳/休息天数），含数据验证发现
- `references/manual-adjustments.md` — Layer 6 手动调整创建流程+Portugal案例+常见错误
- `references/knockout-stage-statistics.md` — WC1998-2022 淘汰赛历史统计 (94场), Poisson校准参数
- `references/matchday3-motivation-patterns.md` — MD3 出线动机分类框架 (QMF 6类型), 同时开球效应, 48队第3名出线阈值
- `references/v55-inference-merge.md` — v5.5推理数据合并到标准JSON的脚本和流程（报告PDF含推理路径的前提）
- `references/missed-results-recovery.md` — v5.9.1: 遗漏赛果诊断+恢复工作流（回溯采集→手动录入→ELO更新→重跑推演），含 2026-07-05 真实恢复案例
- `references/cron-pipeline-v5.9.1.md` — v5.9.1 cron 管线关键更新：5000 sims、completed match 预种子、赛果回溯、knockout_schedule 同步、iLink 限流防御

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
26. **⚠️ v5.6: Poisson λ 必须设上限**: bracket_simulator 中 λ = 1.45 × 10^(Δ/500) 对大ELO差产生荒谬值（Argentina 2399 vs Cape Verde 1782 → λ=24.85）。求和仅到 i=11 时截断大部分概率质量，导致概率颠倒（强者胜率 < 10%）。**修复**: λ 上限 4.0，见 bracket_simulator.py `MAX_LAM = 4.0`。

27. **⚠️ v5.6: 赛果 status 缺失导致 ELO 静默跳过**: `update_elo_from_results.py` 只处理 `status == 'completed'` 的比赛。手动录入 `wc2026_results.json` 时若忘记设置 `"status": "completed"`，比赛会被静默跳过，ELO 永不更新。**修复**: 录入后立即检查所有 match 是否有 status 字段。

28. **⚠️ v5.6: 淘汰赛对阵必须以FIFA官方为准**: seed_knockout 约束算法产出合法但可能与FIFA公告不同。**用户明确指示**"淘汰赛名单和赛程要以官方为准"——任何时候优先FIFA官方对阵，不依赖约束算法输出。算法用于快速验证和降级方案。

29. **⚠️ v5.6: MD3 ELO非对称降权 — 平局也降权**: 锁定队平局时实际得分 ≈ 预期，但用户逻辑是"轮换阵容结果不反映真实实力"，K仍降为30。不要因为 Δ≈0 就认为应该保留 K=60。见 `references/md3-locked-elo-dampening.md`。

30. **⚠️ v5.8.1: 淘汰赛数据录入后必须执行质量审计**: 手动录入 R32+ 赛果后易遗漏 `date_beijing`、`penalties`、`aet`、`round`、`winner` 等字段。**每次录入后必须执行一键全检**。检查清单和验证命令见 `references/data-quality-checklist.md`。
17. **⚠️ v5.5: 推理引擎是wrapper模式**: `predict_v55.py` 包装 `predict_single_match`，引擎计算ELO delta后作为manual_adjustments注入。不要直接修改 `predict_single_match` 内部来集成引擎——wrapper模式避免了300+行代码的重新缩进
21. **⚠️ v5.5: 微信PDF文件大小限制 ~100KB**: 通过MEDIA标签或hermes send发送PDF时，超过约100KB会导致CDN上传HTTP 500。单场报告按场次切分(每场50-60KB)，总报告需分part(如part1/part2各<100KB)。`generate_single_match_pdf.py --all` 自动生成按场次切分的报告。
22. **⚠️ xhtml2pdf字体乱码**: emoji字符(🧠📋⚡)在xhtml2pdf生成的PDF中会显示为乱码。使用reportlab方案(`generate_single_match_pdf.py`)替代，所有emoji替换为文字标签([规则]/[修正]等)。
23. **⚠️ RSS搜索窗口**: 3天窗口对部分球队覆盖不足(如瑞士/加拿大仅SoccerNews有报道)。改用5天窗口 + 搜索title和summary两个字段提高命中率。
19. **⚠️ v5.5: 模板解析 `{{key}}` 从context取值**: 规则中的 `base_value: "{{motivation_elo}}"` 会在引擎中解析为 `context['motivation_elo']`。如果context中缺少该key，静默返回0
20. **⚠️ v5.5: tournament_form使用确定性种子**: `get_tournament_form()` 用 `sum(ord(c)*(i+1))` 做确定性hash，同一球队每次调用返回相同值。不要用 `random.gauss()` 直接调用——那会每次返回不同值
21. **⚠️ v5.5: 推理数据不自动合并到报告PDF**: `predict_v55.py` 产出 `_v55.json`（含 inference_trace/reasoning_path），与标准 `YYYY-MM-DD.json`（predict_by_date.py产出）结构不同。`generate_daily_report.py` 只读标准JSON，不会自动包含推理路径。**必须手动合并两个JSON后再生成报告**，否则PDF中无 `[v5.5推理路径]` 和 `🧠规则明细` 表格。合并脚本见 `references/v55-inference-merge.md`

22. **⚠️ emoji在xhtml2pdf PDF中显示为乱码 — 禁止在报告中用emoji**: `xhtml2pdf` 对emoji字符（🧠📋⚡🎯等）无法正确渲染，PDF中显示为方框或乱码。`generate_daily_report.py` 的v5.5推理路径原用emoji标注规则/修正，在PDF中全部变成乱码。**解决方案**: 用纯文本标签替代emoji——`[规则]` 替代 `📋`, `[修正]` 替代 `⚡`, `[引擎]` 替代 `🧠`。`generate_single_match_pdf.py`（ReportLab直出）已内置emoji→文本替换。xhtml2pdf方案需在markdown生成阶段就做替换。

23. **⚠️ xhtml2pdf中文字体渲染差 — ReportLab直出更可靠**: `xhtml2pdf` 依赖NotoSansSC-VF可变字体，渲染中文时字重/间距不一致，代码块（```）内的align只能靠空格对齐非常脆弱。**推荐 `generate_single_match_pdf.py`** 用ReportLab直接构建PDF——完整控制字体嵌入、表格样式（TableStyle）、段落间距，输出干净无乱码。缺点是不能复用markdown渲染流程，需单独维护layout逻辑。

24. **⚠️ 微信PDF大小限制 ~100KB — 超大文件CDN HTTP 500**: 微信通道文件上传CDN对PDF有隐形大小限制，约 **100KB** 为阈值（85KB√、126KB✗）。与文件总大小相关，与页数无关。`MEDIA:` 和 `hermes send` 走同一CDN，超限时统一报 `CDN upload HTTP 500`。**三步降级策略**（按优先级）：
   1. **压缩PDF**: `python3.11 -c "import fitz; d=fitz.open('r.pdf'); d.save('out.pdf', garbage=4, deflate=True, clean=True); d.close()"` — 通常节省10-15%，对大文件不够
   2. **拆分PDF**（推荐）: `python3.11 -c "import fitz; d=fitz.open('r.pdf'); mid=N; d1=fitz.open(); d1.insert_pdf(d,from_page=0,to_page=mid-1); d1.save('part1.pdf',garbage=4,deflate=True); d1.close(); d2=fitz.open(); d2.insert_pdf(d,from_page=mid,to_page=d.page_count-1); d2.save('part2.pdf',garbage=4,deflate=True); d2.close()"` — 6场报告从154KB拆为95KB+84KB两部分，各在100KB内
   3. **转图片**（最后手段）: 逐页转PNG，`[d[i].get_pixmap(dpi=200).save(f'p{i+1:02d}.png') for i in range(d.page_count)]`，28页报告需发28张图，体验差且`hermes send`可能超时
   安装依赖: `pip3.11 install pymupdf`。如果网关hang（`hermes send` 超时），需从外部shell重启: `hermes gateway restart`
   **最佳实践**: 用 `generate_single_match_pdf.py` 按场次生成单场PDF，每份~50KB远低于阈值，无需拆分即可直接发送。

25. **⚠️ RSS近3天窗口对弱队覆盖不足 — 用5天+搜摘要**: `generate_daily_report.py` 的RSS查询用3天窗口且只搜标题（`title LIKE`），对小球队（如瑞士/加拿大）几乎无高质量源覆盖——仅SoccerNews有报道且该源被排除列表过滤。`generate_single_match_pdf.py` 已修复为**5天窗口 + 同时搜title和summary**（`title LIKE ? OR summary LIKE ?`），覆盖率从0→7篇。但摘要搜索会引入噪音（如球员转会新闻），可接受——有噪音优于无数据。日后所有RSS查询统一用5天+title+summary。

36. **⚠️ v5.9: predict_by_date 需同时读取两个 schedule**: 淘汰赛对阵在 `knockout_schedule.json` 而非 `wc2026_schedule.json`。`predict_by_date.py` 必须同时检查两个文件，否则预测输出 `None vs None`。同时需过滤 group stage schedule 中 team_a/team_b 为 null 的残留记录。

37. **⚠️ v5.9: bracket_recursive 递归推演需动态解析对阵**: QF/SF/F 比赛的 team_a/team_b 初始为 null，必须通过 source 字段（如 `"W89 vs W90"`）在 Monte Carlo 循环中从上一轮胜者动态解析。Phase 1 仅预测 R16 已知对阵，Phase 2 在每轮 sim 中为 QF+ 实时预测。

38. **⚠️ v5.9: ELO 去重必须用 score 做 key**: `update_elo_from_results.py` 旧去重用 `(team_a, team_b, date)` 但 applied_results 无 date 字段 → 去重失效。修复：改用 `(team_a, team_b, score)` 三元组 + 双向检查。

39. **⚠️ v5.9: 低 sims 冠军概率有统计噪声**: <100 次 Monte Carlo 对 16 支球队的冠军概率估计有显著随机波动。**v5.9.1 起默认 5000 sims**，概率稳定在 ±2% 以内。推送报告中标注 `n_sims=5000`。

40. **⚠️ v5.9: 规则学习应从全量比赛学习**: `phase0_rule_learning.py` 最初从 44 场小组赛学习。淘汰赛阶段应重新运行，从所有已完成比赛（88 场含 R32）学习。用户明确指示「规则应该从截止目前所有比赛中学习确定」。

41. **⚠️ v5.9: generate_single_match_pdf tournament form 格式字符串错误导致历史数据静默缺失**: 原代码 `f'{adj:+d}'` 将 team-level ELO 调整值 `adj` 用 detail 字符串 `d` 做格式说明符，Python 抛出 ValueError → 表格为空 → 用户看到空的历史比赛数据。**修复**: 改为段落式输出：`'{tc} (调整 {adj:+d} ELO):'  + 逐条 details[:4]`。此 Bug 不影响 JSON 数据（数据正确），仅影响 PDF 渲染。验证：检查 PDF 中 `[L4.6] 本届比赛表现` 模块是否有 4 条比赛详情而非空表。

42. **⚠️ v5.9: 微信 PDF 批量发送 — 每 30 秒发 1 个**: 用户明确指令「批量发送 PDF 操作一律每 30s 发 1 个」。连续快速发送会触发 WeChat CDN rate limit 或 iLink 限流。使用 MEDIA: 标签发送，每条 MEDIA 之间至少间隔 30 秒。

43. **⚠️ v5.9: bracket_recursive 淘汰赛推演必须追踪败者（losers）**: 季军赛 source 为 `"L101 vs L102"`（SF 败者），而非 `"W101 vs W102"`（SF 胜者/决赛）。必须同时维护 `winners` 和 `losers` 两个 dict，否则 M103（季军赛）对阵会与 M104（决赛）相同。修复：`loser = tb if winner == ta else ta; losers[mid] = loser`。

44. **⚠️ v5.9: advancement 追踪容易在 patch 中丢失**: `bracket_recursive.py` 中 `advancement[winner][stage] += 1` 是关键行，patch 操作时容易误删。每次修改后必须验证 `bracket_recursive_results.json` 中 `advancement_probs` 非空。验证命令：`python3.11 -c "import json; r=json.load(open('data/bracket_recursive_results.json')); print(len(r.get('advancement_probs',{})))"` — 输出应 >0。

45. **⚠️ v5.9: MEDIA 标签中文文件名可能静默失败**: 微信 CDN 对包含中文的 PDF 文件路径偶尔失败且无报错（用户收到空消息）。**建议**: 长中文路径的 PDF 复制到 `/tmp/` 下用简短 ASCII 名发送（如 `/tmp/br.pdf`）。所有 PDF >100KB 必须先 pymupdf 压缩再发送。

46. **⚠️ v5.9: 后台进程 notify_on_complete 日志会推送给用户**: `terminal(background=True, notify_on_complete=True)` 会将进程 stdout/stderr 作为消息推送给用户。避免在 cron 外使用 notify_on_complete，或提前用 `grep -v` 过滤敏感/冗余输出。此 session 中 bracket_recursive.py 的 200+ 行 RSS 日志被推送给用户。

47. **⚠️ v5.9.1: collect_results.py --check 仅检查当日 → 前一天赛果漏采不会被追溯**: `collect_results.py --check` 只检查 `date_beijing == today` 的比赛。若前一天的比赛因任何原因未被采集（cron 漏跑、iLink 限流、ESPN 未更新），第二天 14:30 cron 不会自动回溯 → bracket_recursive 基于过期 ELO 运行 → 推演报告与真实结果不符。**2026-07-05 真实案例**: 7/4 的 2 场 R16（Canada 0-3 Morocco, Paraguay 0-1 France）未被录入 wc2026_results.json，导致推演报告中的 Canada/Morocco/Paraguay 仍被当作未比赛队伍预测。**修复**: cron 第 2 步采集赛果时**回溯前 2 天** schedule，检查是否有 date < today 但不在 results 中的比赛。恢复流程见 `references/missed-results-recovery.md`。

48. **⚠️ v5.9.1: bracket_recursive 已完成比赛未注入 winners/losers → champion_probs 为空**: 当 knockout_schedule.json 中某场比赛 `status=completed` 时，`get_match_order()` 正确将其排除出 `remaining_matches`，但 Monte Carlo 循环中 `winners[mid]` 从未被设置 → QF 的 `"W89 vs W90"` source 解析时找不到 France/Morocco → 后续轮次全部断裂 → champion_probs 为空 dict。**根因**: 已完成比赛从 simulation 中移除后，其 winner 信息也应注入 sim 循环以支撑后续轮次的 source 解析。**修复 (3 处改动)**:
   - Phase 1b 前新增 `ko_completed_matches` 字典加载 completed matches 的 winner/stage
   - Phase 1b 的 `mlp_winners/mlp_losers` 用 completed matches 预种子（使"Most likely path"包含已完成比赛晋级者）
   - Phase 2 每个 sim 开始时用 `ko_completed_matches` 预种子 `winners/losers` 并跟踪 `advancement`
   **验证**: `bracket_recursive_results.json` 的 `champion_probs` 非空 + `advancement_probs` 包含已完成比赛的胜者（如 France R16=5000, Morocco R16=5000）。

49. **⚠️ v5.9.1: match_details 的 None 值 vs .get() 默认值陷阱**: `match_details[mid]["prediction"]` 对 pending 比赛（QF+ 的 None vs None）显式存储 `{"team_a_win_pct": None, ...}`。Python 的 `dict.get("team_a_win_pct", 50)` 在 key 存在但值为 None 时返回 None（不是 50）→ `sample_winner()` 中 `None/100.0` → TypeError。**修复**: 全部改用 `dict.get("key") or DEFAULT` 模式（`or` 对 None 和缺失都生效）。涉及位置: `sample_winner()` 的 `p.get("team_a_win") or 33`、Monte Carlo 循环的 `md.get("prediction", {}).get("team_a_win_pct") or 50`。

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
│   ├── generate_single_match_pdf.py  # v5.5: 单场报告(reportlab) [DEPRECATED → gen_match_pdf.py]\n│   ├── gen_qf_pdfs.py               # v5.10: QF单场PDF [RENAMED → gen_match_pdf.py]\n│   ├── gen_match_pdf.py             # v5.11: 单场PDF生成器(10模块, 小组赛+淘汰赛通用)\n│   ├── enrich_predictions.py        # v5.11: 分模型+ELO轨迹注入(独立脚本+模块)
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
│   ├── bracket_recursive.py     # v5.9: 递归单场预测推演(替代bracket_simulator)
│   ├── generate_bracket_pdf.py   # v5.9: 推演报告PDF生成器
│   ├── knockout_calibration.py   # v5.4: 淘汰赛行为校准(KBC)
│   ├── fetch_weather.py          # v5.2: Open-Meteo 天气采集
│   └── match_reminder.py       # 赛前1h提醒
├── data/
│   ├── elo_ratings.json        # 64队 ELO
│   ├── friendly_form_adjustments.json # 热身赛状态调整值
│   ├── match_weather.json      # v5.2: 比赛日天气预报缓存
│   ├── team_profiles.json      # 48队中英文元数据(含name_cn, style_category)
│   ├── team_tactics.json        # v5.8: 球队风格战术档案(阵型/主帅/优劣势/核心球员)
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
3. **串关 EV 始终为负**: 竞彩 29% 抽水的结构性结果，报告已如实标注
4. **WeChat iLink 限流**: Cron 推送可能静默失败，`deliver=local,origin` 保底
5. **非结构化信号需 LLM 回填**: Layer 5.5 依赖 agent 侧调用 LLM 后 merge_llm_response，cron 自动运行无 LLM 支持时优雅降级为 0
6. **KBC R32参数为外推**: 48队制首次，R32无历史数据。参数通过R16→Final历史数据外推，标注为实验性
7. ~~**全量推演使用ELO+Poisson近似，不包含12层完整栈**~~: **已修复 (v5.9)**。`bracket_recursive.py` 替代了旧的 `bracket_simulator.py`，每场比赛使用完整 12 层预测栈（含 v5.5 推理引擎）。QF/SF/F 比赛在 Monte Carlo 循环中动态解析对阵后实时预测。
8. **bracket_recursive 统计噪声**: <100 次 Monte Carlo 仅有方向性参考价值。**v5.9.1 起默认 5000 sims**，概率稳定在 ±2%，推送时标注 n_sims=5000。

30. **⚠️ v5.4: ELO重复应用导致幅度偏大**: `update_elo_from_results.py` 在cron管线中被多次调用，同一赛果可能被应用多次。短期修复：在 `update_elo_from_results.py` 中加入去重检查。MD3和淘汰赛前建议从 eloratings.net 手动采集基准ELO重新校准: 5000次×32场比赛若逐场调用 predict_single_match 需数小时。推演引擎内部计算 Poisson 概率（含KBC分轮次λ抑制+均值回归），然后 random 采样判定胜负。这保持了与主管线一致的数学基础，同时保证 Monte Carlo 速度。

31. **⚠️ v5.6: wc2026_predict.py v2.3 与 v5.5 管线是两套独立系统**: `wc2026_predict.py` 的 `run_monte_carlo()` 使用 v2.3 简单模型，未集成 v5.5 12层栈。淘汰赛全量推演使用独立 `bracket_simulator.py`（方案B wrapper模式）。不要将 v5.5 功能期望附加到 `--full --sims`。