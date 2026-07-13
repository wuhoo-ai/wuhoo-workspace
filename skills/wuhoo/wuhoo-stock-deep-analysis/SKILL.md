---
name: wuhoo-stock-deep-analysis
description: "单股深度分析与决策建议（Workflow B 增强版）。整合 akshare 财务数据 + 因子数据 + 多空辩论，输出 4 部分完整投资分析报告（定性→定量→估值→决策）。wuhoo 冠名 skill 为 Hermes 企业级关键 skill，需重点维护。"
tags: ["wuhoo"]
category: wuhoo
metadata: { "hermes": { "emoji": "🔬", "requires": { "bins": ["python3.11"], "pip": ["akshare", "pandas", "numpy"] } } }
---

# wuhoo-stock-deep-analysis — 单股深度分析（Workflow B 增强版）

> **⚠️ 企业级关键 Skill**
> 以 `wuhoo-` 冠头的 skill 是当前 Hermes 系统的**企业级关键 skill**，承担核心业务价值。
> 这些 skill 的代码质量、稳定性和可维护性需要特别关注。

> **✅ 2026-06-08 修复**：6 处修复全部完成，报告恢复正常产出。详见 `references/20260608-root-cause-fix.md`。

## 功能概述

对**单只股票**进行全方位深度分析，整合多源数据（akshare 财务 + DataAggregator 因子 + 技术面），生成结构化的 4 部分投资决策报告。

**适用场景**：用户指定某只股票（如 "帮我深度分析一下 600519"），需要全面的投资视角。

## 报告结构

### 第一部分：定性分析 — 商业模式与经济护城河
- 商业模式阐释（如何赚钱、客户、收入来源）
- 经济护城河评估（品牌/网络效应/成本优势/转换成本/无形资产）
- 管理层与资本配置评估
- 行业格局与成长空间（波特五力模型）

### 第二部分：定量分析 — 财务健康与盈利能力
- 财务健康状况（资产负债率、利息保障倍数、自由现金流）
- 盈利能力与效率（ROE、毛利率/净利率趋势、资产周转率）
- 成长性分析（营收/净利润/FCF 的 5 年 CAGR）
- 财务异常检测（应收/存货/现金流背离等红旗信号）

### 第三部分：估值分析 — 内在价值与安全边际
- 三阶段 DCF 模型（乐观/中性/悲观三情景，含详细计算过程）
- 相对估值（PE/PB/PS/EV-EBITDA 历史分位 + 同业对比）
- 安全边际计算与理想买入价格

### 第四部分：投资决策建议 — 综合研判与交易计划
- 核心优势总结（1-3 点）
- 主要风险识别（1-3 点）
- 明确决策：【强烈买入/买入/持有/卖出/强烈卖出】
- 仓位建议（核心/卫星）、买入策略、卖出纪律

## 使用方式

```bash
# 增强版深度分析（推荐，整合 akshare 财务数据）
python3.11 ~/wuhoo-workspace/skills/wuhoo-stock-deep-analysis/deep_analysis.py --code 600519

# 港股（需显式指定市场，纯数字代码无法自动检测）
python3.11 ~/wuhoo-workspace/skills/wuhoo-stock-deep-analysis/deep_analysis.py --code 01398 --name 工商银行 --market hk

# 美股
python3.11 ~/wuhoo-workspace/skills/wuhoo-stock-deep-analysis/deep_analysis.py --code AAPL --name Apple --market us
# 或带 market 标记
python3.11 ~/wuhoo-workspace/skills/wuhoo-stock-deep-analysis/deep_analysis.py --code AAPL --market us --name Apple

# --market 参数: auto(自动检测，默认) / cn(A股) / hk(港股) / us(美股)
# 纯数字代码（如 01398）必须手动指定 --market hk，否则会误判为 A 股

# 策略报告版（因子数据 + 辩论）
python3.11 ~/wuhoo-workspace/skills/wuhoo-stock-deep-analysis/strategy_report.py --symbol 600519.SH
```

## 输出

```
~/wuhoo-workspace/data/deep-analysis/{code}_{date}/
├── akshare_data.json           # akshare 原始财务数据
├── factor_data.json            # DataAggregator 因子数据
├── valuation_data.json         # 估值计算结果
├── debate_data.json            # 多空辩论结果
├── audit_report.json           # 审计报告（结构化）
├── audit_report.md             # 审计报告（可读 Markdown）
├── all_data.json               # 完整合并数据（含审计）
└── decision_report.md          # 4 部分完整报告
```

### 审计报告

审计报告是分析质量的"质检证书"，包含 8 个审计维度：

| 维度 | 审计内容 |
|------|----------|
| 数据获取 | akshare/Tushare/DataAggregator 可用性与完整性 |
| 公开信息 | 网络搜索、券商研报覆盖度 |
| 定性分析 | 行业识别、护城河证据、管理层分析深度 |
| 定量分析 | ROE/现金流/成长数据覆盖度、数据期数充足性 |
| 估值分析 | DCF 可用性+参数合理性、相对估值+历史分位 |
| 多空辩论 | 辩论方法、多空观点数量、置信度 |
| 一致性校验 | 基本面/估值/辩论结论是否自洽 |
| 红旗检测 | 财务异常识别、极端估值警示 |

**可靠性等级**: A(80+) / B(60-79) / C(40-59) / D(<40)

扣分规则详见 `b_audit.py` 中的 `DEDUCTION_RULES`。

## 数据源

| 数据源 | 内容 | 适用范围 |
|--------|------|----------|
| **akshare** | 利润表、资产负债表、现金流、财务指标、股东、分红 | A 股 |
| **DataAggregator** | 技术因子、基本面因子、舆情面 | A/港/美 |
| **debate 模块** | Bull/Bear/Trader/Risk 四角色辩论 | A/港/美 |

## 降级策略

| 场景 | 降级行为 |
|------|----------|
| akshare 不可用 | 使用 DataAggregator 因子数据，报告标注"基础版" |
| debate 模块不可用 | 回退到纯规则推理多空判断 |
| DCF 数据不完整 | 仅做相对估值，跳过 DCF |
| 港股/美股 | 无 akshare 财务，使用因子数据 + 辩论 |

## 依赖

```bash
# A 股完整分析
pip3.11 install akshare pandas numpy

# 因子数据（trade-agent 环境）
# 使用 ~/wuhoo-workspace 下的 Python 环境
```

## 🐛 已知陷阱与修复

### 1. 报告全模板占位符（10 项修复，2026-06-08 分批完成）

以下是导致所有报告章节退化为模板占位符的根因及修复——分两轮完成：

**第一轮（4 根因联动）**：

| # | 根因 | 修复 |
|---|------|------|
| 1 | `stock_individual_info_em()` JSON 解析失败 → 行业/PE/PB 全空 | 降级到 `stock_profile_cninfo`（行业+名称） |
| 2 | `_get_indicators()` 只取前 10/80 行 → ROE/毛利率等缺失 | 改为返回全部 80 行 |
| 3 | 指标名不匹配（`销售毛利率(%)` vs `毛利率`） | 加 `_INDICATOR_NAME_MAP` 名映射表 |
| 4 | 辩论路径不存在 → 退化到空白 `quick_analysis` | 直读 batch_debate JSON 结果 |

**第二轮（6 项深化修复）**：

| # | 根因 | 修复 |
|---|------|------|
| 5 | `current_price` 始终 0 → 安全边际恒 100% | 从 Tushare `daily_data/` CSV 读最新收盘价 |
| 6 | DCF 取 Q1 利润(1695万)而非 FY(6459万) → 低估 3.8x | `_extract_metric_from_indicators` 优先取 '1231' 结尾的年报列 |
| 7 | DCF 任何负安全边际统一扣 1.5 → 无区分度 | 三情景分层: 乐观溢价<30% 不扣, 30-100% 扣 0.5, >100% 扣 1.5 |
| 8 | ROE 混季度和年度 → 被 Q1 低值拉低 | `_make_final_decision` 仅取 '1231' 年报 ROE |
| 9 | 纯数字代码 `01398` 被误判为 A 股 | 加 `--market hk/cn/us/auto` 参数 |
| 10 | 辩论文件名格式 `SZ_300151` vs `300151_SZ` 不匹配 | 双格式尝试查找 |

### 2. get_portfolio 缓存脏数据

#### 根因 A: `_get_basic()` 失败 → 行业/PE/PB 全空
`stock_individual_info_em()` 在某些 akshare 版本返回 JSON decode error。
**修复**：降级到 `stock_profile_cninfo(symbol=code)`，字段映射：`公司名称`→name, `所属行业`→industry, `注册资金`→market_cap。

#### 根因 B: `_get_indicators()` 只取前 10 行 → 丢失关键指标
`stock_financial_abstract` 返回 80 行指标（ROE/毛利率在 11-30 行），但 `limit=10` 只取前 10 行（归母净利润/营收/成本等）。**所有后续查找全部落空。**
**修复**：`limit=200`，确保覆盖全部行。同时增加 early-exit（仅当 `len(df) > limit` 才截断）。

#### 根因 C: 指标名不匹配 → `_extract_indicator_value` 返回 None
代码期望 `销售毛利率(%)` / `加权净资产收益率(%)` / `资产负债率(%)` 等带括号后缀的名称，但 `stock_financial_abstract` 实际返回 `毛利率` / `净资产收益率(ROE)` / `资产负债率`。
**修复**：新增模块级 `_INDICATOR_NAME_MAP` 映射表，`_extract_indicator_value()` 自动 fallback 到映射名。

#### 根因 D: 辩论降级 + 符号格式不匹配
`DebateRunner.run()` 引用不存在的 `skills/debate/run_debate` → 降级到空白 `quick_analysis`。且 Futu 格式 `SZ.300151` 与 batch_debate 格式 `300151_SZ` 不匹配。
**修复** (1): 检查 `data/debate/{date}/deepseek/debate_{symbol}.json` 是否存在，存在则直接加载 batch_debate 结果。
**修复** (2): 符号转换—检测 Futu 格式 `exchange.code`，翻转为 `code_exchange`。

#### 增强 E: 价格降级到 Tushare 日线数据
`stock_bid_ask_em()` 受网络限制不可用。**修复**：新增降级路径——从 `data/stock-pick/daily_data/{year}/{month}.csv`（Tushare 日线）读取最新 `close` 价，匹配 `ts_code` 格式（300151.SZ / 603267.SH / code.BJ）。**效果**：昌红 0.00→24.29，鸿远 0.00→74.80。**局限**：Tushare 数据有 T+2 延迟。

#### 增强 G: DCF 估值三情景分层扣分（替换旧一刀切）

旧逻辑：安全边际 `< -20%` 统一扣 1.5。导致溢价 29% 和溢价 1783% 同等对待，缺乏区分度。
**修复**：`_make_final_decision()` 改按三情景（悲观/中性/乐观）逐情景计算安全边际：
- 3 情景全正安全边际 → +2.0（极度低估）
- 2 情景正 → +1.5
- 仅乐观情景正 → +0.5
- 全负但乐观溢价 < 30% → 0（接近合理价）
- 乐观溢价 30-100% → -0.5（温和高估）
- 乐观溢价 > 100% → -1.5（严重高估）
**效果**：鸿远电子乐观溢价 29%→0 分（之前 -1.5），从【卖出】→【持有】。富乐德乐观溢价 47%→-0.5（之前 -1.5），强烈卖出 1.0→3.0。

#### 增强 H: 决策 ROE 仅取年报列

旧逻辑：`_make_final_decision` 取 `dates[:5]` 的 ROE 平均值，混合了季度（Q1 ROE 2.15%）和年度（FY ROE 5.77%）数据，拉低平均。
**修复**：仅取列名以 `1231` 结尾的年报列，取最近 5 个财年。无年报列时降级到全部。
**效果**：鸿远电子 ROE 从 3.75%（混季）→ 4.72%（年报纯），仍 <5% 触发扣分但更准确；昌红科技 ROE 改善至 >5% 不再扣分，从【卖出 4.0】→【持有 5.0】。
`_extract_metric_from_indicators()` 取第一个非元数据列，对于 `stock_financial_abstract` 这是最近季度（Q1），导致 DCF 基准利润被低估 3-4 倍。**修复**：优先查找列名以 `1231` 结尾的年报列。**效果**：昌红 DCF 基准 1695万(Q1)→6459万(FY2025)，内在价值 0.62→2.37 元（3.8x）。

### 2. 输出路径是 `data/trade/data/workflow_b/` 而非 `data/deep-analysis/`

SKILL.md 文档写的输出路径与实际脚本路径不一致。实际脚本写 `~/wuhoo-workspace/data/trade/data/workflow_b/{code}_{date}/`。

### 5. 辩论文件双格式匹配

batch_debate 保存的文件名格式因市场而异：A 股 `debate_300151_SZ.json`（CODE_EXCH），港股 `debate_HK_01398.json`（EXCH_CODE）。`DebateRunner.run()` 会自动尝试两种映射顺序（先 `symbol.replace('.', '_')`，不存在时翻转为 `parts[1]_parts[0]`）。

### 7. current_price=0.00 当股票不在 Tushare 日线数据中（2026-06-09 发现）

增强 E 的价格降级路径依赖 `data/stock-pick/daily_data/{year}/{month}.csv`（Tushare），但部分股票（如 002261 拓维信息）**从未被 Tushare 拉取过**，该目录无数据。

**症状**：`current_price=0.00`，安全边际恒 100%（误导性极高），DCF 对比完全失效。

**当前绕过**：手动从 akshare sina 端点获取最新价格：
```python
import akshare as ak
df = ak.stock_zh_a_daily(symbol='sz002261', start_date='20260101', end_date='20260609', adjust='qfq')
price = float(df.iloc[-1]['close'])  # 真实最新价
```

**建议修复**：在 `deep_analysis.py` 的价格降级链末端追加 akshare sina 端点作为最终 fallback。

### 8. 并行运行辩论导致报告使用降级辩论（2026-06-09 发现）

`deep_analysis.py` 在 Step 4（执行多空辩论）时从 `data/debate/{date}/deepseek/debate_{symbol}.json` 读取辩论结果。如果 LLM 辩论和 deep_analysis **并行运行**，deep_analysis 启动时辩论 JSON 尚未写入 → 回退到简化规则分析（`quick_analysis`，仅基于 PE 做简单判断）。

**症状**：报告「多空辩论摘要」显示「辩论方式: 简化规则分析」，看多观点「暂无」，与实际 LLM 辩论结果（如 Bull SELL 0.72 + Bear SELL 0.80）完全不同。

**处置**：
- **必须先跑完辩论，再跑 deep_analysis**（串行，不能并行）
- 如果已并行导致降级：直接用 LLM 辩论结果做综合报告，deep_analysis 仅作 akshare 财务 + DCF 估值参考

### 6. HK/美股 DCF 跳过

港股/美股无 akshare 财务数据，DCF 阶段自动跳过。报告仅依赖辩论 + 因子数据。港股深度分析需加 `--market hk` 参数（纯数字代码无法自动识别市场）。

`deep_analysis.py` 启动时从 `~/wuhoo-workspace/.hermes/.env` 加载（非 `~/.hermes/.env`），但 Hermes `terminal()` 中的 `source` 不传递 export。运行前必须 `export $(grep -v '^#' ~/.hermes/.env | xargs)` 或直接设 `DEEPSEEK_API_KEY`。

- `references/20260608-deep-analysis-degradation.md` — 2026-06-08 深度分析退化审计：三报告完全一致、价格0.00、辩论未加载

- `references/20260608-root-cause-fix.md` — 2026-06-08 4 根因全修复审计（basic/indicators/名映射/辩论加载）

## 四大师深度分析增强集成

v2.7 (2026-06-29) — 新增与 `wuhoo-value-investing` 的增强分析集成：

```bash
# 价值投资深度分析（7模块：生意/护城河/逆向/管理层/文明/估值/决策）
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-value-investing
python3.11 value_deep_analysis.py --code AAPL --market us --name Apple

# 与现有 deep_analysis.py 的关系：
#   deep_analysis.py — 快速量化分析（因子+财务+DCF）
#   value_deep_analysis.py — 价值投资深度分析（四大师7模块框架）
#   两者互补：量化版给数字，价值版给判断
#
# 推荐使用顺序：
#   1. investment_checklist.py（6关快速判断）
#   2. value_deep_analysis.py（Checklist通过后深度分析）
#   3. deep_analysis.py（补充量化数据）
```

**7模块分析框架**：
1. 数据收集 + 信息丰富度评级 (A/B/C)
2. 生意本质 — 段永平（收入漏斗/商业模式/生态粘性）
3. 护城河评估 — 巴菲特（5类验证/10年预判）
4. 逆向思考 — 芒格（失败路径/空方论点/历史类比）
5. 管理层 — 段+巴（决策复盘/资本配置/企业文化）
6. 文明趋势 — 李录（范式转移/TAM/赢家通吃判断）
7. 估值与安全边际 — 巴+段（反向DCF/三情景/安全边际）

详见 `wuhoo-value-investing` skill > `value_deep_analysis.py`。

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.6 | 2026-06-09 | 新增陷阱 #7: price=0.00 当股票不在 Tushare 日线数据中（akshare sina fallback）；新增陷阱 #8: 并行运行辩论导致降级（必须串行） |
| 2.5 | 2026-06-08 | 增强 E-H：价格从 Tushare 日线降级获取、DCF 基准盈利取年报而非 Q1、DCF 三情景分层扣分、决策 ROE 仅取年报列；加 `--market hk/cn/us/auto` CLI 参数；辩论文件双格式匹配、HK/美股 DCF 跳过说明 |
| 2.4 | 2026-06-08 | 追加 2 增强：DCF 三情景分层扣分、ROE 决策取年报列 |
| 2.2 | 2026-06-08 | 修复 4 根因：basic 降级到 stock_profile_cninfo、indicators limit→200、指标名映射、辩论直读 batch_debate JSON + 符号转换 |
| 2.1 | 2026-06-08 | 新增常见陷阱 |
| 2.0 | 2026-04-09 | 整合 akshare 财务数据，4 部分报告结构，三阶段 DCF |
| 1.0 | 2026-04-09 | 初始版本（因子数据 + 辩论） |

---

*创建时间：2026-04-09 | 版本：2.4*
