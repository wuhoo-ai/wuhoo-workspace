# 2026-05-06 A股全链路审计

## 执行时间
2026-05-06 10:03 ~ 14:00 (UTC+8)

## 前置条件
- Tushare Token: ✅ (56 chars)
- Futu OpenD: ✅ (127.0.0.1:11111, v10.4.6408)
- python3.11 + tushare/pandas/yfinance: ✅
- 最新 A 股日线: 202604.csv (五一假期 5/1-5/5 无交易数据)

## 流程执行

### Step 1: 数据更新 (15分55秒)
- A股日线: 202604 已存在，跳过
- 换手率 (efinance): 999/999 成功

### Step 2: 选股 (1秒)
10 只入选: 300428/002681/603279/002421/300319/300098/688088/300459/002077/688327

### Step 3: 多空辩论 (9分53秒)
- 9/10 成功，1 失败 (002077 Trader JSON parse error)
- BUY: 300098 (conf=0.60), SELL: 002421 (conf=0.65), HOLD: 7

### Step 4: 调仓 — ✅ 成功 (14:00)
- **关键发现**: CN 账户 18767295 **存在**，需用 `filter_trdmarket=TrdMarket.CN` 查询
- 之前误判为"Nonexisting acc_id"是因为创建 `OpenSecTradeContext` 未传 `filter_trdmarket`
- 002421 不在持仓中 → SELL 跳过
- 300098 BUY: 1200股 市价单成交 @ ¥5.73（限价单 SUBMITTED 不成交，改市价单立即 FILLED_ALL）
- 辩论假设价格 ¥10.0 vs 实际 ¥5.51 — 止盈止损位需重算

## A股行情限制
- `get_market_snapshot()` / `request_history_kline()` 均返回「无权限获取行情」
- 价格替代: 从 `daily_data/2026/202604.csv` 读取最新 `close`
- 交易不受影响: 下单、查持仓、查资金均正常

## 已纠正的误判
- ❌ 旧结论: CN 账户 18767295 已删除 → ✅ 正确: `filter_trdmarket=TrdMarket.CN` 后可见
- ❌ 旧结论: OpenD 内部过滤 Bug → ✅ 正确: SDK 调用方式问题
- ❌ 旧结论: 需要重新开通 CN 账户 → ✅ 无需操作

## 待修复项
- [ ] 002077 大港股份 Trader JSON 失败（DeepSeek 纯文本输出 → 需 prompt 强化或 retry 降级）
- [ ] workflow_c 支持加载外部辩论结果
- [ ] 辩论价格假设与实际价格校验（避免 ¥10 vs ¥5.51 级误差）
