# A 股模拟交易实战手册 (2026-05-06)

## 账户必须按市场查询

`get_acc_list()` **不是全局查询** — 它只返回与 `OpenSecTradeContext` 的 `filter_trdmarket` 匹配的市场账户：

| filter_trdmarket | 返回的模拟账户 |
|:---:|------|
| (不传) | 18767294 (HK), 18767296 (HK) |
| HK | 18767294 (HK), 18767296 (HK) |
| US | **18767293** (US) |
| CN | **18767295** (CN) |

## A 股行情权限

`OpenQuoteContext.get_market_snapshot()` 对 A 股代码返回 `-1: 无权限获取行情`。
`quote_ctx.subscribe()` 同样失败（ret=-1）。

**替代方案**：
```python
import pandas as pd
df = pd.read_csv('~/wuhoo-workspace/data/stock-pick/daily_data/2026/202604.csv')
# 列名: ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
price = df[df['ts_code'] == '300098.SZ'].sort_values('trade_date', ascending=False).iloc[0]['close']
```

## A 股下单：市价单 vs 限价单

| 订单类型 | 状态 | 备注 |
|---------|------|------|
| NORMAL (限价) | SUBMITTED → 可能长时间不成交 | 需等待匹配 |
| MARKET (市价) | SUBMITTING → FILLED_ALL (秒级) | 推荐使用 |

限价单取消：
```python
trd.modify_order(modify_order_op=ModifyOrderOp.CANCEL, order_id='xxx', qty=0, price=0,
                  trd_env=TrdEnv.SIMULATE, acc_id=18767295)
```

## 完整 CN 交易示例

```python
from futu import *
trd = OpenSecTradeContext(
    filter_trdmarket=TrdMarket.CN,
    host='127.0.0.1', port=11111,
    security_firm=SecurityFirm.FUTUSECURITIES
)
# 市价买入 1200 股
ret, data = trd.place_order(
    price=0, qty=1200, code="SZ.300098",
    trd_side=TrdSide.BUY, order_type=OrderType.MARKET,
    trd_env=TrdEnv.SIMULATE, acc_id=18767295
)
# 查询成交
ret, orders = trd.order_list_query(trd_env=TrdEnv.SIMULATE, acc_id=18767295)
dealt = orders[orders['order_status'] == 'FILLED_ALL']
print(f"成交均价: {dealt.iloc[0]['dealt_avg_price']}")
trd.close()
```

## 账户资金

CN CASH 18767295:
- total_assets ≈ ¥1,025,882
- cash ≈ ¥110,188
- market_val ≈ ¥915,694
- 持仓约 10 只

## Python 运行环境

futu 安装路径: `/home/admin/.local/lib/python3.11/site-packages/futu/`
但系统 Python 缺 pandas，须使用:
```
/home/admin/.hermes/hermes-agent/venv/bin/python3
```
