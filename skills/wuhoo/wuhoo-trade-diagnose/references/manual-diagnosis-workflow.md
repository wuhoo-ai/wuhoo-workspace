# Manual Diagnosis Workflow — Verified 2026-05-01

When `diagnose.py` fails due to missing dependencies (`risk_manager.py`, `portfolio_metrics.py`), use this Python-based fallback.

## Step 0: Start OpenD

```bash
bash ~/wuhoo-workspace/scripts/start_opend.sh start
bash ~/wuhoo-workspace/scripts/start_opend.sh status  # verify port 11111
```

## Step 1: Verify Accounts

```bash
python3.11 ~/wuhoo-workspace/skills/wuhoo/wuhoo-futuapi/scripts/trade/get_accounts.py --json
```

Check `trdmarket_auth` — not the old docs. Account-to-market mapping changes over time.

## Step 2: Fetch Portfolio + Account Info (single Python script)

Use `OpenSecTradeContext` — one connection per market, reuse it for both positions and account info to avoid repeated connection overhead.

```python
from futu import *

# US: filter_trdmarket=TrdMarket.US, acc_id=18767293
# HK: filter_trdmarket=TrdMarket.HK, acc_id=18767294
# Both need refresh_cache=True for position_list_query and accinfo_query
```

Key fields from position_list_query:
- `cost_price` (摊薄成本) — use `diluted_cost` as fallback
- `nominal_price` (现价), `market_val` (市值), `qty` (数量)
- `pl_val` (浮动盈亏), `pl_ratio` (盈亏比例)

Key fields from accinfo_query:
- `total_assets`, `cash`, `market_val`, `maintenance_margin`

## Step 3: Get Snapshots for PE/PB

```python
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, data = quote_ctx.get_market_snapshot(all_codes)  # max 400 per call
# Fields: last_price, pe_ratio, pe_ttm_ratio, pb_ratio, amplitude, volume
quote_ctx.close()
```

## Step 4: Web Search for Analyst Ratings

Search pattern: `"{TICKER} stock analyst rating target price 2026"` or `"{中文名} 港股 分析師 目標價 2026"`

Key sources that reliably return ratings:
- public.com/stocks/{ticker}/forecast-price-target
- marketbeat.com/stocks/{exchange}/{ticker}/forecast/
- stockanalysis.com/stocks/{ticker}/forecast/
- wallstreetzen.com (1Y price target)
- tipranks.com (consensus rating breakdown)
- 东方财富/pdf.dfcfw.com (港股研报)

## Step 5: Compute Portfolio Metrics

```python
# Weights
weight = stock.market_val / total_assets_usd

# HHI (Herfindahl-Hirschman Index)
hhi = sum(w**2 for w in weights)  # < 0.15 = 分散

# Top-N concentration
top3 = sum(sorted(weights, reverse=True)[:3])  # ≤ 50%
top5 = sum(sorted(weights, reverse=True)[:5])

# Cash ratio
cash_ratio = cash / total_assets  # ≥ 10%

# Currency conversion
# HKD → USD: divide by ~7.8
```

## Step 6: Generate Rebalancing Signals

| Signal | Trigger |
|--------|---------|
| CLEAR | Loss > 15% OR analyst Strong Sell |
| REDUCE | Loss > 8% OR analyst target < current price |
| ADD | Analyst Strong Buy + upside > 20% + loss < 5% |
| HOLD | Everything else |

## Special Considerations from 2026-05-01 Session

- **GOOGL + GOOG double position**: Same company, different share class. Combined weight 14.8% — suggest merging to avoid concentration risk.
- **BEN**: Analyst Hold + target below current → REDUCE despite +8.55% profit
- **ADI**: Analyst Buy but target below current → watch closely, consider REDUCE
- **COF**: -6% loss but Strong Buy with 43% upside → HOLD/ADD, not CLEAR
- **安踏**: -5.53% but analyst target +35% upside → ADD on dips
- **港股现金 50.7%**: Consider deploying idle cash or transferring to US account
