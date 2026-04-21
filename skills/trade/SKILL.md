---
name: wuhoo-trade
description: 多市场交易执行（Workflow C）。接收选股结果、分析结果、辩论结果作为输入，执行风控检查、交易模拟/实盘、复盘。
metadata: { "hermes": { "requires": { "bins": ["python3.11"] } } }
---

# wuhoo-trade — 多市场交易执行

## 执行入口
- 交易执行: `python3.11 workflow_c_multi_market.py`
- 定期交易: `python3.11 workflow_e_periodic_trade.py`
- 风控管理: `python3.11 risk_manager.py`
- 持仓审计: `python3.11 audit_module.py`
- 组合指标: `python3.11 portfolio_metrics.py`
- 每日复盘: `python3.11 daily_review.py`

## 依赖
富途 OpenD 运行在 127.0.0.1:11111
