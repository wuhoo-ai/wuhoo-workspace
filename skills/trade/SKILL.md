---
name: wuhoo-trade
description: 多市场交易执行（Workflow C）。接收选股结果、分析结果、辩论结果作为输入，执行风控检查、交易模拟/实盘、复盘。支持美股等权持仓策略。
metadata: { "hermes": { "requires": { "bins": ["python3.11"], "pip": ["pandas", "numpy", "futu-api"] } } }
---

# wuhoo-trade — 多市场交易执行

## 执行入口
- **交易执行**: `python3.11 skills/trade/workflow_c_multi_market.py --market us --date 2026-04-22`
- **定期交易**: `python3.11 skills/trade/workflow_e_periodic_trade.py`
- **风控管理**: `python3.11 skills/trade/risk_manager.py`
- **持仓审计**: `python3.11 skills/trade/audit_module.py`
- **组合指标**: `python3.11 skills/trade/portfolio_metrics.py`
- **每日复盘**: `python3.11 skills/trade/daily_review.py`
- **美股等权持仓**: `python3.11 skills/trade/us_equal_weight_portfolio.py [show|rebalance|check]`

## 依赖
- 富途 OpenD 运行在 127.0.0.1:11111
- python3.11 + pandas + numpy + futu-api
- 环境变量在 ~/.hermes/.env

## 账户配置 (path_config.py)
| 市场 | 账户 ID | 类型 | 环境 |
|------|---------|------|------|
| CN   | 18767295 | CASH | SIMULATE |
| HK   | 18767294 | CASH | SIMULATE |
| US   | 18767293 | MARGIN | SIMULATE |

## 美股等权持仓策略 (us_equal_weight_portfolio.py)

**策略逻辑:**
- 持仓范围: stock_pick.py 当天选出的结果（非 S&P 500 全量）
- 权重分配: 每只股票等权重 = (1 - 10%现金) / N
- 现金储备: 10%
- 再平衡: 每次选股结果更新后自动再平衡

**用法:**
```bash
python3.11 skills/trade/us_equal_weight_portfolio.py show      # 查看当前持仓
python3.11 skills/trade/us_equal_weight_portfolio.py rebalance # 执行再平衡
python3.11 skills/trade/us_equal_weight_portfolio.py check     # 检查是否需要再平衡
```

**数据文件:**
- 选股结果: ~/.hermes/data/stock-pick/factors/result_us_YYYYMMDD.csv
- 持仓记录: ~/wuhoo-workspace/data/us/portfolio.json

## 工作流

```
选股 (stock-pick) → 分析 (deep-analysis) → 辩论 (debate)
  → 风控检查 (risk_manager) → 交易执行 (workflow_c) → 复盘 (daily_review)
```

## 目录结构
```
skills/trade/
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
