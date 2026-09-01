---
name: wuhoo-trade-diagnose
description: "持仓诊断与调仓建议（Workflow D）。扫描 OpenD 持仓，逐只重新评估（调用 Workflow B），生成组合级风险报告和调仓信号（HOLD/ADD/REDUCE/CLEAR）。支持 A股/港股/美股。wuhoo 冠名 skill 为 Hermes 企业级关键 skill，需重点维护。"
tags: ["wuhoo"]
category: wuhoo
metadata: { "hermes": { "emoji": "🩺", "requires": { "bins": ["python3.11"], "pip": ["pandas", "numpy"] } } }
---

# wuhoo-trade-diagnose — 持仓诊断与调仓建议（Workflow D）

> **⚠️ 企业级关键 Skill**
> 以 `wuhoo-` 冠头的 skill 是当前 Hermes 系统的**企业级关键 skill**，承担核心业务价值。
> 这些 skill 的代码质量、稳定性和可维护性需要特别关注。

## 功能概述

对**当前持仓组合**进行全方位诊断，逐只股票重新评估基本面和技术面，生成组合级风险指标和调仓建议。是 Workflow C（选股交易）的配套"定期体检"工具。

**与 Workflow B 的关系**：Workflow B 是单股深度分析（用户指定个股），Workflow D 自动扫描持仓后调用 Workflow B 对每只持仓做重评估。

**适用场景**：
- 定期体检：检查现有持仓是否仍值得持有
- 调仓前评估：生成加/减/清仓信号
- 风险排查：发现集中度、相关性、回撤等组合级风险

**⚠️ 美股限制**：本脚本（diagnose.py）的 Workflow B 调用依赖 akshare，akshare **不支持美股**数据。对于美股持仓，应使用 `us-stock-portfolio-diagnosis` skill，改用 yfinance 获取数据。Workflow D 原生支持 A股/港股；美股需走独立诊断流程。

## 完整流程

```
Step 1: 扫描 OpenD 持仓 (futu-api get_portfolio)
    ↓
Step 2: 逐只股票重新评估 (调用 Workflow B 分析每只持仓)
    ↓
Step 3: 组合级风险分析 (risk_manager + portfolio_metrics)
    ↓
Step 4: 生成调仓建议 (HOLD / ADD / REDUCE / CLEAR)
    ↓
Step 5: 输出 openD 调仓信号 (JSON 机器可读)
    ↓
Step 6: 保存为行动指南 (供下次定时任务使用)
```

## 使用方式

```bash
# 直接调用 skill
python3.11 ~/wuhoo-workspace/skills/wuhoo-trade-diagnose/diagnose.py

# 全市场诊断
python3.11 ~/wuhoo-workspace/skills/wuhoo-trade-diagnose/diagnose.py

# 仅港股诊断
python3.11 ~/wuhoo-workspace/skills/wuhoo-trade-diagnose/diagnose.py --market HK

# A股指定账户
python3.11 ~/wuhoo-workspace/skills/wuhoo-trade-diagnose/diagnose.py --market CN --account-id 18767295

# 快速模式：跳过 Workflow B 重评估（仅持仓扫描 + 组合风险）
python3.11 ~/wuhoo-workspace/skills/wuhoo-trade-diagnose/diagnose.py --market HK --skip-re-eval

# 仅诊断前 5 只持仓（按市值排序）
python3.11 ~/wuhoo-workspace/skills/wuhoo-trade-diagnose/diagnose.py --top-n 5

# 指定日期
python3.11 ~/wuhoo-workspace/skills/wuhoo-trade-diagnose/diagnose.py --market US --date 2026-04-13

# 仅输出 JSON（不生成 Markdown 报告）
python3.11 ~/wuhoo-workspace/skills/wuhoo-trade-diagnose/diagnose.py --skip-re-eval --json
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--market` | 市场 (CN/HK/US/all) | all |
| `--account-id` | 富途账户 ID | 自动检测 |
| `--date` | 诊断日期 (YYYY-MM-DD) | 今天 |
| `--skip-re-eval` | 跳过 Workflow B 重评估 | False |
| `--top-n` | 最多诊断持仓数（按市值排序） | 全部 |
| `--json` | 仅输出 JSON，不生成 Markdown | False |

## 输出

> ⚠️ **路径已变更**（2026-05-07 实测）：diagnose.py 实际输出到 `~/wuhoo-workspace/data/trade/data/workflow_d/{DATE}/`，非旧版 `data/diagnose/` 路径。

```
~/wuhoo-workspace/data/trade/data/workflow_d/{DATE}/
├── 01_portfolio_scan.json           # 持仓原始数据（Futu 返回）
├── 02_stock_diagnoses.json          # 逐股诊断结果（Workflow B）
├── 03_portfolio_risk.json           # 组合风险指标
├── 04_rebalancing_suggestions.json  # 调仓建议（HOLD/ADD/REDUCE/CLEAR）
├── 05_rebalancing_signals.json      # 机器可读调仓信号
├── workflow_d_report.md             # 人类可读诊断报告
└── action_guide.json                # 下次定时任务的行动指南
```

### ⚠️ 输出目录覆盖问题（Confirmed v1.5, 2026-05-07; v1.6, 2026-05-08 再次实测）

CN 和 HK 并行运行时，两者写入**同一输出目录**，后完成的进程**覆盖**先完成进程的中间文件（`01_portfolio_scan.json` 等）。当前无按市场分目录机制。

**串行执行 + 备份模式**（推荐）：

```bash
# 1. 先跑 CN
python3.11 diagnose.py --market CN --account-id 18767295

# 2. 备份 CN 结果
mkdir -p /home/admin/wuhoo-workspace/data/trade/data/workflow_d/{DATE}_CN
cp /home/admin/wuhoo-workspace/data/trade/data/workflow_d/{DATE}/* \
   /home/admin/wuhoo-workspace/data/trade/data/workflow_d/{DATE}_CN/

# 3. 再跑 HK（会覆盖 workflow_d/{DATE}/ 下的文件）
python3.11 diagnose.py --market HK --account-id 18767294

# 4. 备份 HK 结果
mkdir -p /home/admin/wuhoo-workspace/data/trade/data/workflow_d/{DATE}_HK
cp /home/admin/wuhoo-workspace/data/trade/data/workflow_d/{DATE}/* \
   /home/admin/wuhoo-workspace/data/trade/data/workflow_d/{DATE}_HK/

# 最终：{DATE}_CN/ 和 {DATE}_HK/ 各自包含完整结果
```

**影响**：并行运行会导致 JSON 中间数据不可恢复，必须串行 + 备份。

### 组合级指标

| 指标 | 说明 | 参考阈值 |
|------|------|----------|
| Sharpe Ratio | 风险调整后收益 | > 1.0 良好 |
| HHI 集中度 | Herfindahl-Hirschman 指数 | < 0.15 分散 |
| 最大单股权重 | 持仓占比最高的股票 | ≤ 20% |
| Top-3 集中度 | 前三大持仓占比之和 | ≤ 50% |
| 估算最大回撤 | 基于个股盈亏的加权回撤 | ≤ 15% |
| 现金比率 | 可用现金占总资产比例 | ≥ 10% |
| 盈亏比分布 | 持仓中盈利/亏损股票分布 | — |

### 调仓信号

每只持仓输出以下之一：

| 信号 | 含义 | 触发条件 |
|------|------|----------|
| **HOLD** | 维持现状 | 估值合理，无重大风险 |
| **ADD** | 建议加仓 | Workflow B 强烈买入 + 仓位偏低 |
| **REDUCE** | 建议减仓 | 触发风控 / Workflow B 建议卖出 / 亏损 > 8% |
| **CLEAR** | 建议清仓 | Workflow B 强烈卖出 / 亏损 > 15% |

### ⚠️ 解读所有 REDUCE 时的注意事项

当诊断结果出现全仓 REDUCE 时，需区分两类驱动因素：

1. **风控驱动 REDUCE**：`risk_manager` 的 `position_limit` 检查触发。当前仓位已 ≥ 90% 时，任何 ADD 模拟都会导致「新仓位 > 90%」违规 → 触发 REDUCE。**即使 Workflow B 给出"持有"也无济于事**。
2. **基本面驱动 REDUCE**：Workflow B 给出"卖出"或"强烈卖出"。

**辨别方法**：检查 `04_rebalancing_suggestions.json` 中的 `workflow_b_decision` 字段：
- WB 说"持有"但信号是 REDUCE → 纯风控驱动（如港股 2026-05-08：中信/港交所/中银香港全部"持有"→ REDUCE）
- WB 说"卖出"或"强烈卖出"且信号是 REDUCE → 基本面+风控双重确认（如 A 股 2026-05-08）

**行动建议**：风控驱动的 REDUCE 优先处理集中度最高的持仓；基本面驱动的 REDUCE 可考虑清仓而非减仓。

## 数据源

| 数据源 | 内容 | 说明 |
|--------|------|------|
| **用户直接粘贴** | 成本/现价/仓位/盈亏 | WeChat/CLI 模式，绕过 OpenD |
| **akshare** | K线/技术指标/全市场覆盖 | ⭐ Futu无A股权限时的主力数据源，覆盖全A股 |
| **Futu OpenD** | 实时持仓、资金、盈亏 | 通过 futu-api get_portfolio（需A股行情权限）|
| **Futu 快照** | PE/PB/市值/振幅 | OpenQuoteContext.get_market_snapshot |
| **web_search** | Q1业绩/研报/分析师评级/行业动态 | 每只股票 1-2 次搜索 |
| **daily_data** | 历史K线（仅~1000只） | 选股因子覆盖股票，可能有缺失 |
| **Workflow B** | 逐股深度分析 | 调用 wuhoo-stock-deep-analysis/deep_analysis.py |
| **risk_manager** | 风控规则检查 | 仓位/止损/黑名单 |
| **portfolio_metrics** | 组合级指标计算 | Sharpe/HHI/集中度/回撤 |

> 📁 **参考文件**：`references/futu-portfolio-fetch.py`（持仓获取脚本模板）、`references/analyst-data-sources.md`（分析师数据源指南）

## 用户直接提供持仓数据的快速诊断模式（2026-05-12 新增）

**触发条件**：用户通过 WeChat/CLI 直接粘贴持仓数据（含成本、现价、盈亏、市值），无需拉取 OpenD。

**数据获取优先级链**（当 Futu OpenD A股无权限时）：

```
用户粘贴的持仓数据（成本/现价/仓位）  ← 始终可用
    ↓
akshare stock_zh_a_hist()            ← ✅ 覆盖全A股，获取技术指标
    ↓
web_search（基本面/Q1业绩/研报）      ← 每只股票 1-2 次搜索
    ↓
daily_data（仅~1000只股票，可能缺失） ← 补充因子数据
```

**快速诊断步骤**：

```bash
# Step 1: 解析用户粘贴的持仓（成本/现价/仓位/盈亏）
# Step 2: akshare 拉取每只个股近60日K线，计算技术指标
python3.11 -c "
import akshare as ak
import numpy as np
# 对每只个股：mom5/mom10/mom20, volatility, RSI, volume_ratio, turnover
"
# Step 3: web_search 获取最新基本面/Q1业绩/研报评级
# Step 4: 识别组合集中度风险（行业/单票/Top-N）
# Step 5: 按模板生成诊断报告（见 references/rapid-diagnosis-template.md）
```

**⚠️ 已知陷阱**：

1. **ETF 代码易混淆**：华泰柏瑞航空航天ETF → **563380**（非 512770 战略新兴ETF华夏，非 512770）。ETF简称相同但基金公司不同时代码不同，务必搜索确认。
2. **daily_data 覆盖不全**：daily_data 仅含 ~1000 只选股因子覆盖的股票。天华新能(300390)、英维克(002837)、多数ETF **不在 daily_data 中**，须回退到 akshare。
3. **daily_data 最新日期可能滞后**：202605.csv 实测仅含 5月6日数据（5月7-12日缺失），用户 OpenD 数据可能更新 → **优先相信用户提供的持仓数据**。
4. **锂电产业链集中度风险**：若多只持仓属同一产业链（锂电电解液/氢氧化锂/溶剂 → 均为锂电上游），须在报告顶部用红色标注组合级行业集中度风险。

**报告格式**：见 `references/rapid-diagnosis-template.md`

## 降级策略

| 场景 | 降级行为 |
|------|----------|
| OpenD 不可用 | 返回空持仓列表，报告标注"OpenD 不可用" |
| Workflow B 不可用 | 使用 `--skip-re-eval` 模式，仅做持仓扫描 + 组合风险 |
| 单只股票分析失败 | 标记该股票为"分析失败"，继续处理其余持仓 |
| 所有分析失败 | 输出持仓概览 + 基础风控检查，报告标注"降级模式" |
| daily_data 缺失个股 | 回退到 akshare（覆盖全A股），无额外限制 |
| Futu 无A股权限 | 跳过Futu行情，直接用用户数据+akshare+web_search |

## 依赖

```bash
# 使用 Python 3.11 环境
pip3.11 install pandas numpy
```

## 与其他 Workflow 的关系

| Skill | 对应 Workflow | 用途 |
|-------|--------------|------|
| wuhoo-stock-deep-analysis | Workflow B | 单股深度分析，用户指定个股 |
| wuhoo-stock-trade | Workflow C | 多市场自动选股交易流水线 |
| wuhoo-trade-diagnose | Workflow D | 持仓诊断与调仓建议（本 skill） |

**调用关系**：Workflow D 调用 Workflow B 对每只持仓做重评估，复用 risk_manager 做风控检查。

## 已知问题与降级方案

### Hermes Agent 并行执行注意（2026-05-07 实测）

`process wait` 的 timeout 被平台 clamp 到 **60 秒**上限。Workflow B 逐股分析耗时长（>5 min），单次 `wait(timeout=600)` 会被截断。**必须循环轮询**：

```python
# ✅ 正确：循环等待长任务
while True:
    result = process(action='wait', session_id='...', timeout=600)
    if result.get('status') == 'exited':
        break
    # status == 'timeout' → 继续等待
```

### diagnose.py 脚本问题

**1. MARKET_ACCOUNTS 映射** (2026-05-01 实测验证):
- `HK=18767294` (CASH, SIMULATE) ✅
- `CN=18767295` (CASH, SIMULATE) ✅ — **实测存在，非之前认为的"不存在"**
- `HK=18767296` (MARGIN, SIMULATE) ✅ — 注意是 HK 市场，非 US

**2. US 模拟账户 accinfo_query 返回全零** (2026-05-03 实测):
- 账户 18767293（US MARGIN SIMULATE）的 `accinfo_query()` 返回所有字段为 0.0
- 导致**无法获取**：总资产、现金、购买力、现金比率
- **影响**：组合级现金比率指标不可计算，报告中需标注"OpenD 模拟账户限制"
- **状态**：疑似模拟账户权限或 API 版本问题，待排查

**3. Futu API 字段返回 'N/A' 字符串**（通用问题）:
- `unrealized_pl`、`pl_ratio_avg_cost`、部分 snapshot 字段（PE/PB/市值）可能返回字符串 `'N/A'`
- 直接 `float()` 转换会抛 `ValueError`
- **必须使用 safe_float 包装函数**（见 `references/futu-safe-float.py`）
- 参考：`wuhoo-futuapi` skill 的「非保证金账户字段返回 N/A」章节

**4. 模拟账户 position_list_query 返回 `average_cost=0.0` / `unrealized_pl=0.0`（全市场通用，2026-06-17 实测）**:
- CN 模拟账户 (18767295) 和 HK 模拟账户 (18767294) 的 `position_list_query()` 均返回 `average_cost=0.0`、`unrealized_pl=0.0`、`pl_ratio_avg_cost=0.0`
- 不止 US 账户受影响——**所有模拟账户**的持仓成本/盈亏数据均不可用
- **影响**：
  - 盈亏比分布全部显示 "break_even"（无盈利/亏损区分）
  - Sharpe Ratio 恒为 0.0（无收益序列可计算）
  - 估算最大回撤恒为 0.0（无盈亏数据）
  - 止损检查（亏损 > 8%）永远不会触发（pl_ratio 恒为 0）
  - 意味着**风控中的亏损止损规则（single_stop_loss 8%）在模拟账户上完全失效**
- **应对**：组合指标中 Sharpe/Max DD 标注「模拟账户限制，不可用」；止损信号依赖 Workflow B 基本面判断而非 API 盈亏数据

### 数据源限制

| 市场 | Workflow B (akshare) | 替代方案 |
|------|---------------------|----------|
| A股 | ✅ 可用 | — |
| 港股 | ❌ akshare 不支持 | web_search 获取分析师评级 + futu snapshot |
| 美股 | ❌ akshare 不支持 | web_search 获取分析师评级 + futu snapshot (PE/PB) |

### 手动诊断流程（当 diagnose.py 不可用时，2026-05-03 端到端验证可用）

```bash
# Step 0: 启动 OpenD (如未运行)
bash ~/wuhoo-workspace/scripts/start_opend.sh start

# Step 1: 获取账户列表确认映射（可选）
python3.11 ~/wuhoo-workspace/skills/trader/wuhoo-futuapi/scripts/trade/get_accounts.py --json

# Step 2: 使用 OpenSecTradeContext 获取持仓（非 OpenQuoteContext！）
# 完整脚本模板见 references/futu-portfolio-fetch.py
# 必须使用 safe_float 处理 Futu API 返回的 'N/A' 值

# Step 3: 获取快照 (PE/PB/振幅/市值等)
# 使用 OpenQuoteContext.get_market_snapshot(all_codes)，每次最多 400 个

# Step 4: 使用 web_search 获取分析师评级和目标价
# 搜索 "{ticker} stock analyst rating target price 2026"
# 推荐数据源: MarketBeat, TipRanks, StockAnalysis, public.com

# Step 5: 手动计算组合指标
# HHI = sum(weight²), 集中度 = top-N weights 求和
# 现金比率 = cash / total_assets（⚠️ US 模拟账户 accinfo_query 返回全零）
# 风控信号: 亏损 > 8% → REDUCE, > 15% → CLEAR
# 调仓信号: 分析师目标价上行 > 15% + Strong Buy → ADD
#            分析师目标价下行 > 10% 或 Underperform → REDUCE
```

### 数据源限制

| 市场 | Workflow B (akshare) | 替代方案 |
|------|---------------------|----------|
| A股 | ✅ 可用 | — |
| 港股 | ❌ akshare 不支持 | 需 yfinance 或第三方数据 |
| 美股 | ❌ akshare 不支持 | us-stock-portfolio-diagnosis skill (yfinance) |

## 定时任务配置

> **更新时间**: 2026-05-03

原「每日持仓诊断」已拆分为两个按市场分时执行的任务，均含交易日检查：

| 任务 | 时间 | 市场 | 交易日检查 | 脚本 |
|------|------|------|:---:|------|
| A股/港股 持仓诊断 | 10:00 | CN + HK | akshare 日历 | `~/.hermes/scripts/check_cn_trading_day.py` |
| 美股 持仓诊断 | 23:00 | US | yfinance S&P 500 | `~/.hermes/scripts/check_us_trading_day.py` |

**交易日检查逻辑**：
- CN/HK：`akshare.tool_trade_date_hist_sina()` 查询 A 股交易日历
- US：通过 yfinance 获取 S&P 500 最近 10 天记录，结合 weekday 判断
- 非交易日时任务自动跳过，输出"非交易日，跳过诊断"

**共享库**：`~/wuhoo-workspace/scripts/check_trading_day.py`（被上述两个脚本 import）

**⚠️ 微信推送限制**：由于 Hermes Gateway 存在 asyncio `Timeout context manager should be used inside a task` 框架级 bug，所有定时任务必须使用 `deliver: local`。执行结果保存在本地 cron output 目录，需手动查看。

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.9 | 2026-06-17 | 新增「模拟账户 position_list_query 返回 average_cost=0.0」已知问题（全市场通用：CN/HK 均受影响，非仅 US）；说明此问题导致 Sharpe/Max DD/止损检查在模拟账户上完全失效 |
| 1.7 | 2026-05-08 | 新增串行执行+备份模式的具体命令；新增「解读所有 REDUCE 时的注意事项」章节（区分风控驱动 vs 基本面驱动 REDUCE） |
| 1.6 | 2026-05-07 | 修正输出路径文档（actual→`workflow_d/`，非旧 `data/diagnose/`）；新增 Hermes Agent 并行 process wait 60s clamp 注意事项；确认输出目录覆盖问题在 CN/HK 并行时仍存在 |（sys.path 缺失 wuhoo-trade 目录）；发现输出目录覆盖问题（CN/HK 并行运行时 HK 覆盖 CN 的 01_portfolio_scan 等文件） |
| 1.4 | 2026-05-03 | 定时任务拆分：CN/HK 10:00 + US 23:00，新增交易日检查脚本；确认微信推送不可用（Gateway asyncio bug），全部改为 local delivery |
| 1.3 | 2026-05-03 | 新增 US 模拟账户 accinfo_query 返回全零的已知问题；完善手动诊断流程（添加 safe_float 模板、分析师数据源推荐）；添加 `references/futu-portfolio-fetch.py` 持仓获取脚本模板 |
| 1.2 | 2026-05-01 | 修正账户映射 (18767293=US ✅, 18767296=HK, 18767295=CN ✅); 更新手动诊断流程替代方案 (web_search + futu snapshot) |
| 1.1 | 2026-04-25 | 添加已知问题、账户映射修正、降级方案、数据源限制 |
| 1.0 | 2026-04-13 | 初始版本，支持手动触发 + 组合指标 + 调仓信号 |

---

*创建时间：2026-04-13*
*版本：1.8*
