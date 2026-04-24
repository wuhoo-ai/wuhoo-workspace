---
name: wuhoo-trade
description: 多市场交易执行（Workflow C）。接收选股结果、分析结果、辩论结果作为输入，执行风控检查、交易模拟/实盘、复盘。支持美股等权持仓策略。
tags: ["wuhoo"]
category: wuhoo
metadata: { "hermes": { "requires": { "bins": ["python3.11"], "pip": ["pandas", "numpy", "futu-api"] } } }
---

# wuhoo-trade — 多市场交易执行

## 执行入口
- **交易执行**: `python3.11 skills/wuhoo-trade/workflow_c_multi_market.py --market us --date 2026-04-22`
- **定期交易**: `python3.11 skills/wuhoo-trade/workflow_e_periodic_trade.py`
- **风控管理**: `python3.11 skills/wuhoo-trade/risk_manager.py`
- **持仓审计**: `python3.11 skills/wuhoo-trade/audit_module.py`
- **组合指标**: `python3.11 skills/wuhoo-trade/portfolio_metrics.py`
- **每日复盘**: `python3.11 skills/wuhoo-trade/daily_review.py`
- **美股等权持仓**: `python3.11 skills/wuhoo-trade/us_equal_weight_portfolio.py [show|rebalance|check]`

## 依赖
- 富途 OpenD 运行在 127.0.0.1:11111
- python3.11 + pandas + numpy + futu-api
- 环境变量在 ~/.hermes/.env

## 账户配置 (path_config.py)

> **⚠️ 已验证账户列表 (2026-04-24)**：
> - SIMULATE HK CASH: `18767294` ✅
> - SIMULATE US MARGIN: `18767296` ✅ (非 18767293)
> - CN 账户 `18767295` **不存在**
> - REAL MARGIN: `281756481352860561`, `281756455996103774`

| 市场 | 账户 ID | 类型 | 环境 | 状态 |
|------|---------|------|------|------|
| CN   | 18767295 | CASH | SIMULATE | ❌ 不存在 |
| HK   | 18767294 | CASH | SIMULATE | ✅ |
| US   | 18767296 | MARGIN | SIMULATE | ✅ 修正为 18767296 |

## 美股等权持仓策略 (us_equal_weight_portfolio.py)

**策略逻辑:**
- 持仓范围: stock_pick.py 当天选出的结果（非 S&P 500 全量）
- 权重分配: 每只股票等权重 = (1 - 10%现金) / N
- 现金储备: 10%
- 再平衡: 每次选股结果更新后自动再平衡

**用法:**
```bash
python3.11 skills/wuhoo-trade/us_equal_weight_portfolio.py show      # 查看当前持仓
python3.11 skills/wuhoo-trade/us_equal_weight_portfolio.py rebalance # 执行再平衡
python3.11 skills/wuhoo-trade/us_equal_weight_portfolio.py check     # 检查是否需要再平衡
```

**数据文件:**
- 选股结果: ~/.hermes/data/stock-pick/factors/result_us_YYYYMMDD.csv
- 持仓记录: ~/wuhoo-workspace/data/us/portfolio.json

## 工作流

```
选股 (stock-pick) → 分析 (deep-analysis) → 辩论 (debate)
  → 风控检查 (risk_manager / RiskAgent) → 交易执行 (workflow_c) → 复盘 (daily_review)
```

## 风控集成 (2026-04-24 更新)
- `_debate_quick()` 方法已集成 `RiskAgent.review()` 进行风控审核
- 构建 `trader_decision` 结构传递止损/止盈/仓位/RRR 给 RiskAgent
- 降级策略：RiskAgent 不可用时使用简化风控（波动率、涨幅、Beta 检查）
- RRR 计算修正：`潜在收益 / 潜在损失` = `(止盈价-现价) / (现价-止损价)`

## 风控规则差距分析 (2026-04-24)

**risk_rules.yaml 定义 13 条规则，实际仅 5 条生效：**

| 规则 | YAML 定义 | risk_agent.py | risk_manager.py | 状态 |
|------|-----------|--------------|-----------------|------|
| single_stock_max 20% | ✅ | ✅ | ✅ | 已实现 |
| single_industry_max 40% | ✅ | ❌ | ❌ | **未实现** |
| cash_min 10% | ✅ | ❌ | ✅ | risk_manager 实现 |
| 分层仓位管理 | ✅ | ❌ | ❌ | **未实现** |
| 动态止损（波动率调整） | ✅ | ❌ | ⚠️ 部分 | **需完善** |
| RRR min_ratio 2.0 | ✅ | ✅ | ❌ | RiskAgent 实现 |
| 流动性检查 | ✅ | ✅ | ❌ | RiskAgent 实现 |
| 事件风险（财报黑名单） | ✅ | ❌ | ❌ | **未实现** |
| 相关性检查 max_correlation 0.7 | ✅ | ❌ | ❌ | **未实现** |
| 自动审批条件 | ✅ | ⚠️ 未使用 | ❌ | **未生效** |
| CONDITIONAL 阻断 | ✅ | ❌ | ❌ | **未阻断** |
| max_drawdown 15% | ✅ | ❌ | ❌ | **未实现** |
| volatility high_threshold 0.60 | ✅ | ⚠️ pass当无数据 | ❌ | **形同虚设** |

**关键发现**：
1. RiskAgent `_check_volatility()` 无 market_data 时默认 pass，实际调用几乎从不传入 → 波动率检查形同虚设
2. RiskAgent `_check_concentration()` 依赖 `industry_exposure` 字段，但调用方从未传入 → 集中度检查永远 pass
3. CONDITIONAL 结果未阻断交易执行路径
4. 组合级风控（回撤/行业集中度/相关性）完全缺失

**计划新增 `portfolio_risk.py`** 模块，实现：
- `check_portfolio_drawdown()` → 组合级回撤检查（阈值 15%）
- `check_industry_concentration()` → 行业集中度（阈值 40%）
- `check_correlation()` → 持仓相关性（阈值 0.7）
- `check_event_risk()` → 事件风险（财报日检查）
- `apply_tier_position()` → 分层仓位管理（按 confidence 分配）
- `enforce_risk_decision()` → 强制 RiskAgent 结果执行（CONDITIONAL 需确认或阻断）

## 目录结构
```
skills/wuhoo-trade/
  workflow_c_multi_market.py   # 主交易执行流程
  workflow_e_periodic_trade.py # 定期交易
  us_equal_weight_portfolio.py # 美股等权策略
  risk_manager.py              # 风控模块
  audit_module.py              # 持仓审计
  portfolio_metrics.py         # 组合指标计算
  daily_review.py              # 每日复盘
  approval_manager.py          # 审批管理
  path_config.py               # 统一路径配置
  tests/                       # 测试
```
