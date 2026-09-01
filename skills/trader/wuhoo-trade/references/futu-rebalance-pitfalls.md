# 美股等权调仓 — Futu 执行参考

> 2026-05-05 端到端验证通过：12只→11只，22笔订单，仓位89.8%

## 执行流程

1. `stock_pick.py --market us` → 选股结果
2. `batch_debate.py --market us` → 辩论信号
3. 生成调仓方案（对比实盘持仓 `portfolio_us.json`）
4. Futu 批量下单执行

## Futu API 陷阱

### 价格精度
```python
# ✅ 正确：美股价格 round to 2 decimals
price = round(float(snap['last_price']), 2)

# ❌ 错误：直接传 float（如 275.895 → 报 "价格参数精度不符合规范"）
price = float(snap['last_price'])
```

### 市价单 qty=0 陷阱（「数量不合法」）
**美股/港股市价卖单不能传 qty=0 表示"全部卖出"**。Futu API 要求市价单必须传精确数量：
```python
# ❌ 错误：市价单 qty=0 企图卖/买全部
trd.place_order(price=0, qty=0, code='US.AAPL', trd_side=TrdSide.SELL, order_type=OrderType.MARKET, ...)
# → 返回 "数量不合法"

# ✅ 正确：先从持仓获取精确数量
ret, pos = trd.position_list_query(trd_env=TrdEnv.SIMULATE, acc_id=ACC_ID, refresh_cache=True)
qty = int(pos[pos['code']=='US.AAPL']['qty'].iloc[0])
trd.place_order(price=0, qty=qty, code='US.AAPL', trd_side=TrdSide.SELL, order_type=OrderType.MARKET, ...)
```
此问题影响所有市场的市价单（MARKET），不限美股。与限价单不同（限价单可以"全部卖出"by passing a large qty），市价单必须精确。

### 下单频率限制
- `place_order` 限 15次/30秒
- 批量下单需 `time.sleep(1.5)` 间隔
- 触发限频后需等待 35 秒再重试

### 限价单价格偏离
- 卖单价格高于 bid → 不会成交
- 买单价格低于 ask → 不会成交
- **卖单用 bid，买单用 ask**，确保立即成交

### 订单状态检查模式
```python
# 查未成交订单
data = trd_ctx.order_list_query(trd_env=TrdEnv.SIMULATE, acc_id=xxx, refresh_cache=True)
pending = data[data['order_status'] != 'FILLED_ALL']
```

## 完整执行脚本模板
见 `scripts/rebalance_us.py`
