---
name: wuhoo-futures-trade
description: 期货交易执行 — OpenFutureTradeContext 交易引擎，支持 US/HK 期货模拟盘下单/持仓查询/调仓/风控/审计。
version: 0.1.0
category: wuhoo
tags: [wuhoo, futures, trade]
metadata:
  hermes:
    emoji: "💹"
    requires:
      bins: [python3.11]
      pip: [pandas, numpy, futu-api]
---

# wuhoo-futures-trade — 期货交易执行引擎

对标 wuhoo-trade，基于 `OpenFutureTradeContext` 的期货交易系统。

## 账户

| 市场 | 账户 ID | 类型 | 环境 |
|------|---------|------|:----:|
| US | 18767290 | MARGIN | SIMULATE |
| HK | 18767297 | MARGIN | SIMULATE |

## Cron 持仓诊断（2026-05-09 新增）

两个定时诊断 cron 已配置，均使用 `deliver=local`，工作日执行：

| 名称 | Schedule | 市场 | Skills |
|------|----------|:----:|--------|
| 港股期货持仓诊断 | `0 9 * * 1-5` | HK | wuhoo-futures-trade |
| 美股期货持仓诊断 | `30 22 * * 1-5` | US | wuhoo-futures-trade |

**流程**: 检查工作日 → `futures_trade.py check` 查持仓 → `futures_diagnose.py` 诊断 → 输出盈亏+风控+调仓建议。无持仓则跳过。

## 使用方式

```bash
cd ~/wuhoo-workspace/skills/trader/wuhoo-futures-trade
VENV=~/.hermes/hermes-agent/venv/bin/python3

# 查询持仓
$VENV futures_trade.py check

# 模拟调仓（dry-run，不实际下单）
$VENV futures_trade.py rebalance --date 2026-05-08

# 实盘调仓（⚠️ 需确认）
$VENV futures_trade.py rebalance --date 2026-05-08 --execute

# 手动下单
$VENV futures_trade.py order --code US.MESmain --direction LONG --contracts 2 --price 5865.0

# 风控验证
$VENV futures_risk_manager.py validate-order --code US.MESmain --direction LONG --contracts 10 --price 5865.0 --stop-price 5780.0 --adx 28
```

## 风控规则

| 规则 | 阈值 | 说明 |
|------|:----:|------|
| 单品种保证金 | ≤ 20% | 单品种不超过总权益 20% |
| 总保证金 | ≤ 60% | 保留 40% 缓冲 |
| 单笔亏损 | ≤ 2% | 止损金额不超过权益 2% |
| 最大回撤 | ≤ 15% | 总回撤超限停止交易 |
| 关联品种 | ≤ 30% | 同类品种总保证金不超 30% |
| 最低 ADX | ≥ 10 | 无趋势不交易 |
| 到期预警 | 5 天 | 合约到期前 5 天预警 |

## 审计日志

所有交易操作记录到 `~/.futures_trade_audit.jsonl`，每行一条 JSON：
```json
{"action": "ORDER", "code": "US.MESmain", "direction": "LONG", "contracts": 5, "price": 5865.0, "status": "SUCCESS", "order_id": "...", "ts": "..."}
```

## 保证金计算方式

`accinfo_query.initial_margin` 对期货模拟账户返回 N/A。改用 `acctradinginfo_query` 逐品种查询 `long_required_im` / `short_required_im`，累加计算总保证金。

## 依赖

- Futu OpenD 运行在 127.0.0.1:11111
- hermes-agent venv: futu-api, pandas, numpy

---

*创建时间: 2026-05-08 | 版本: 0.2.0 — MVP (Phase 0+1+4) + Cron 持仓诊断*
