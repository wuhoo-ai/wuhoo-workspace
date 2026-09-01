# 期货主力合约完整目录

> 2026-05-08 实测，来源: `get_stock_basicinfo(market, SecurityType.FUTURE)` 筛选 `main_contract=True`

## Phase 1 选品池（7 品种，US+HK 股指+贵金属）

| 代码 | 名称 | lot_size | 做多保证金 | 做空保证金 | 币种 | 类别 |
|------|------|:--------:|:----------:|:----------:|:----:|------|
| US.MESmain | 微型标普500 | 5 | $2,408 | $2,271 | USD | 股指 |
| US.MNQmain | 微型纳斯达克100 | 2 | $3,637 | $3,594 | USD | 股指 |
| US.MGCmain | 微黄金 | 10 | $2,817 | $2,817 | USD | 贵金属 |
| US.SImain | 白银 | 5,000 | $42,520 | $42,520 | USD | 贵金属 |
| HK.MHImain | 小恒指 | 10 | HK$17,630 | HK$17,630 | HKD | 股指 |
| HK.MCHmain | 小国指 | 10 | HK$6,730 | HK$6,730 | HKD | 股指 |
| HK.HTImain | 恒生科技指数 | 50 | HK$26,290 | HK$26,290 | HKD | 股指 |

> 保证金来源: `acctradinginfo_query` 逐品种实测。注意 SI(白银) 保证金 $42,520 偏高。

## 已知不可交易合约

| 代码 | 原因 |
|------|------|
| US.MYMmain | lot_size=0，微型道指当前不可交易 |
| 所有 US 期货 | `request_history_kline` 返回「行情权限不足」，需购买期货行情卡 |

## 市场归属注意

| 合约 | 正确市场 | 常见错误 |
|------|:------:|---------|
| CNmain (A50) | **SG** | 误认为是 HK |
| NKmain (日经) | **SG** | — |

## 全市场主力合约统计

| 市场 | 总合约数 | 主力合约数 |
|:----:|:------:|:--------:|
| HK | 1,308 | 168 |
| US | 13,619 | 102 |
| SG | 906 | 23 |
| JP | 117 | 10 |

## 期货模拟账户

| acc_id | trdmarket_auth | 状态 |
|--------|---------------|:----:|
| 18767297 | [FUTURES_SIMULATE_HK] | ACTIVE |
| 18767290 | [FUTURES_SIMULATE_US] | ACTIVE |
| 18767298 | [FUTURES_SIMULATE_SG] | ACTIVE |
| 18767291 | [FUTURES_SIMULATE_JP] | ACTIVE |

> `OpenFutureTradeContext.get_acc_list()` 无需 `filter_trdmarket` 即可返回全部账户。
