---
name: wuhoo-stock-autopick-trade
description: "多市场自动选股交易全链路（Workflow C）。支持 A股/港股/美股，覆盖选股→多维度分析→多空辩论→投资建议→风控→交易执行→复盘的完整流程。wuhoo 冠名 skill 为 OpenClaw 企业级关键 skill，需重点维护。"
metadata: { "openclaw": { "emoji": "⚡", "requires": { "bins": ["python3"] } } }
---

# wuhoo-stock-autopick-trade — 多市场自动选股交易（Workflow C）

> **⚠️ 企业级关键 Skill**
> 以 `wuhoo-` 冠头的 skill 是当前 OpenClaw 系统的**企业级关键 skill**，承担核心业务价值。
> 这些 skill 的代码质量、稳定性和可维护性需要特别关注。

## 功能概述

多市场（A股/港股/美股）自动化选股交易全链路。每日自动执行从选股到复盘的完整流程，是量化交易的核心引擎。

**适用场景**：
- 每日定时执行多市场选股和交易分析
- 对选定市场进行完整的量化投资流水线
- 生成当日投资建议和综合分析报告

## 完整流程

```
Step 1: 选股 (stock-pick)
    ↓
Step 2: 多维度分析 (技术面/基本面/舆情面)
    ↓
Step 3: 多空辩论 (Bull/Bear/Trader/Risk)
    ↓
Step 4: 投资建议生成
    ↓
Step 5: 风控检查 + 人工审批 + 交易执行
    ↓
Step 6: 每日复盘报告
    ↓
审计报告 (Audit)
```

## 市场支持

| 市场 | 代码 | 数据源 | 交易执行 | 因子配置 |
|------|------|--------|----------|----------|
| A股 | CN | Tushare | 富途 OpenAPI (OpenCNTradeContext) | 残差波动率 + 换手率 + 动量 + Beta |
| 港股 | HK | 富途 OpenAPI | 富途 OpenAPI (OpenHKTradeContext) | 波动率 + 动量 |
| 美股 | US | yfinance | 富途 OpenAPI (OpenUSTradeContext) | 残差波动率 + 成交量 + 动量 + Beta |

## 使用方式

```bash
cd ~/.openclaw/workspace/agents/trade
source venv-futu/bin/activate

# A股分析（推荐：跳过交易执行，仅分析）
python workflow_c_multi_market.py --market cn --date 2026-04-09 --skip-trades

# 港股完整流程（含交易执行）
python workflow_c_multi_market.py --market hk --date 2026-04-09

# 美股分析
python workflow_c_multi_market.py --market us --date 2026-04-09 --skip-trades

# 启用人工审批（大额交易需要确认）
python workflow_c_multi_market.py --market hk --with-approval

# A股深度分析版（使用 workflow_c_cn_analysis.py）
python workflow_c_cn_analysis.py
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--market` | 市场 (cn/hk/us) | HK |
| `--date` | 交易日期 (YYYY-MM-DD) | 今天 |
| `--top-n` | 选股数量 | 10 |
| `--skip-trades` | 跳过交易执行 | False |
| `--with-approval` | 启用人工审批 | False |
| `--skip-review` | 跳过每日复盘 | False |

## 输出目录

```
~/.openclaw/workspace/agents/trade/data/workflow_c/{MARKET}_{DATE}/
├── 01_selected_stocks.json       # 选股结果
├── 02_analysis_results.json      # 多维度分析
├── 03_debate_results.json        # 多空辩论结果
├── 04_recommendations.json       # 投资建议
├── 05_trade_results.json         # 交易执行结果（如有）
├── 05_audit_report.json          # 审计报告
├── audit_report.md               # 审计报告 (Markdown)
├── workflow_results.json         # 完整流程结果
└── workflow_analysis_report.md   # 综合分析报告
```

## 风控规则

| 规则 | 阈值 |
|------|------|
| 单股最大仓位 | ≤ 20% |
| 总仓位最低现金 | ≥ 10% |
| 单笔止损 | -8% |
| 账户总止损 | -15% |
| 大额交易确认 | > 5% 仓位需用户确认 |

## 数据质量与降级

- **Good**：使用真实市场数据
- **Degraded**：部分数据源不可用，使用估计值/降级数据
- 审计模块会记录每只股票的数据可靠性评分 (0-100)
- 可靠性低于阈值的股票会标记告警

## 依赖

```bash
# 富途交易环境
cd ~/.openclaw/workspace/agents/trade
source venv-futu/bin/activate
pip install futu-api pandas

# A股需要额外依赖
cd ~/.openclaw/workspace/agents/main/skills/stock-pick
source venv/bin/activate
pip install tushare pandas
```

## 与其他 Workflow 的关系

| Skill | 对应 Workflow | 用途 |
|-------|--------------|------|
| wuhoo-stock-deep-analysis | Workflow B | 单股深度分析，用户指定个股 |
| wuhoo-stock-autopick-trade | Workflow C | 多市场自动选股交易流水线 |
| stock-pick | 选股子模块 | A股多因子选股（被 Workflow C 调用） |

---

*创建时间：2026-04-09*
*版本：1.0*
*封装自 workflow_c_multi_market.py + workflow_c_cn_analysis.py*
