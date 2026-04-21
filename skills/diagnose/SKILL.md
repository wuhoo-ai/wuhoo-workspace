---
name: wuhoo-trade-diagnose
description: "持仓诊断与调仓建议（Workflow D）。扫描 OpenD 持仓，逐只重新评估（调用 Workflow B），生成组合级风险报告和调仓信号（HOLD/ADD/REDUCE/CLEAR）。支持 A股/港股/美股。wuhoo 冠名 skill 为 OpenClaw 企业级关键 skill，需重点维护。"
metadata: { "openclaw": { "emoji": "🩺", "requires": { "bins": ["python3"], "pip": ["pandas", "numpy"] } } }
---

# wuhoo-trade-diagnose — 持仓诊断与调仓建议（Workflow D）

> **⚠️ 企业级关键 Skill**
> 以 `wuhoo-` 冠头的 skill 是当前 OpenClaw 系统的**企业级关键 skill**，承担核心业务价值。
> 这些 skill 的代码质量、稳定性和可维护性需要特别关注。

## 功能概述

对**当前持仓组合**进行全方位诊断，逐只股票重新评估基本面和技术面，生成组合级风险指标和调仓建议。是 Workflow C（选股交易）的配套"定期体检"工具。

**与 Workflow B 的关系**：Workflow B 是单股深度分析（用户指定个股），Workflow D 自动扫描持仓后调用 Workflow B 对每只持仓做重评估。

**适用场景**：
- 定期体检：检查现有持仓是否仍值得持有
- 调仓前评估：生成加/减/清仓信号
- 风险排查：发现集中度、相关性、回撤等组合级风险

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
# 由 debate agent 触发（推荐，独立审计上下文）
cd ~/.openclaw/workspace/agents/debate
python workflow_diagnose.py

# 直接调用 skill
python ~/.openclaw/skills/wuhoo-trade-diagnose/diagnose.py

# 全市场诊断
python ~/.openclaw/skills/wuhoo-trade-diagnose/diagnose.py

# 仅港股诊断
python ~/.openclaw/skills/wuhoo-trade-diagnose/diagnose.py --market HK

# A股指定账户
python ~/.openclaw/skills/wuhoo-trade-diagnose/diagnose.py --market CN --account-id 18767295

# 快速模式：跳过 Workflow B 重评估（仅持仓扫描 + 组合风险）
python ~/.openclaw/skills/wuhoo-trade-diagnose/diagnose.py --market HK --skip-re-eval

# 仅诊断前 5 只持仓（按市值排序）
python ~/.openclaw/skills/wuhoo-trade-diagnose/diagnose.py --top-n 5

# 指定日期
python ~/.openclaw/skills/wuhoo-trade-diagnose/diagnose.py --market US --date 2026-04-13

# 仅输出 JSON（不生成 Markdown 报告）
python ~/.openclaw/skills/wuhoo-trade-diagnose/diagnose.py --skip-re-eval --json
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

```
~/.openclaw/workspace/agents/trade/data/workflow_d/{DATE}/
├── 01_portfolio_scan.json           # 持仓原始数据（Futu 返回）
├── 02_stock_diagnoses.json          # 逐股诊断结果（Workflow B）
├── 03_portfolio_risk.json           # 组合风险指标
├── 04_rebalancing_suggestions.json  # 调仓建议（HOLD/ADD/REDUCE/CLEAR）
├── 05_rebalancing_signals.json      # 机器可读调仓信号
├── workflow_d_report.md             # 人类可读诊断报告
└── action_guide.json                # 下次定时任务的行动指南
```

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

## 数据源

| 数据源 | 内容 | 说明 |
|--------|------|------|
| **Futu OpenD** | 实时持仓、资金、盈亏 | 通过 futu-api get_portfolio |
| **Workflow B** | 逐股深度分析 | 调用 wuhoo-stock-deep-analysis/deep_analysis.py |
| **risk_manager** | 风控规则检查 | 仓位/止损/黑名单 |
| **portfolio_metrics** | 组合级指标计算 | Sharpe/HHI/集中度/回撤 |

## 降级策略

| 场景 | 降级行为 |
|------|----------|
| OpenD 不可用 | 返回空持仓列表，报告标注"OpenD 不可用" |
| Workflow B 不可用 | 使用 `--skip-re-eval` 模式，仅做持仓扫描 + 组合风险 |
| 单只股票分析失败 | 标记该股票为"分析失败"，继续处理其余持仓 |
| 所有分析失败 | 输出持仓概览 + 基础风控检查，报告标注"降级模式" |

## 依赖

```bash
cd ~/.openclaw/workspace/agents/trade
source venv-futu/bin/activate
pip install pandas numpy
```

## 与其他 Workflow 的关系

| Skill | 对应 Workflow | 用途 |
|-------|--------------|------|
| wuhoo-stock-deep-analysis | Workflow B | 单股深度分析，用户指定个股 |
| wuhoo-stock-trade | Workflow C | 多市场自动选股交易流水线 |
| wuhoo-trade-diagnose | Workflow D | 持仓诊断与调仓建议（本 skill） |

**调用关系**：Workflow D 调用 Workflow B 对每只持仓做重评估，复用 risk_manager 做风控检查。

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-04-13 | 初始版本，支持手动触发 + 组合指标 + 调仓信号 |

---

*创建时间：2026-04-13*
*版本：1.0*
