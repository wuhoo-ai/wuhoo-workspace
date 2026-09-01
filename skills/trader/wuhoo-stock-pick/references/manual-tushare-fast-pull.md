# Manual Tushare Daily Data Fast Pull

Use when `update_all_data.py --market cn --incremental` is stuck in the efinance turnover stage (50+ min) but you need to run stock picking NOW.

## When to use

- `daily_data/YYYY/YYYYMM.csv` stale — last date is days/weeks behind current
- Tushare phase of `--incremental` already completed (or skipped because monthly CSV exists)
- efinance turnover phase is the bottleneck, but stock_pick needs recent price data
- You can tolerate stale turnover data (turnover_5d factor will use last available turnover_data)

## How to run

```bash
cd ~/wuhoo-workspace/skills/trader/wuhoo-stock-pick
source ~/.hermes/.env

python3.11 -c "
import tushare as ts, pandas as pd, os
from pathlib import Path

pro = ts.pro_api(os.environ['TUSHARE_TOKEN'])

# Define date range to pull (skip weekends — Tushare returns empty)
dates_to_try = [
    '20260507','20260508','20260509','20260512','20260513',
    '20260514','20260515','20260516','20260519','20260520',
    '20260521','20260522','20260523'
]

all_data = []
for d in dates_to_try:
    try:
        chunk = pro.daily(trade_date=d)
        if len(chunk) > 0:
            all_data.append(chunk)
            print(f'{d}: {len(chunk)} rows')
    except Exception as e:
        pass

if all_data:
    new_data = pd.concat(all_data, ignore_index=True)
    new_data['trade_date'] = new_data['trade_date'].astype(int)  # ⚠️ CRITICAL

    existing = pd.read_csv('data/stock-pick/daily_data/2026/202605.csv')
    existing['trade_date'] = existing['trade_date'].astype(int)   # ⚠️ CRITICAL

    combined = pd.concat([existing, new_data], ignore_index=True)
    combined = combined.drop_duplicates(subset=['ts_code','trade_date'])
    combined = combined.sort_values(['trade_date','ts_code'])
    combined.to_csv('data/stock-pick/daily_data/2026/202605.csv', index=False)
    print(f'Updated: {len(combined)} rows, dates: {sorted(combined.trade_date.unique())}')
else:
    print('No new data available')
"
```

## ⚠️ Critical: trade_date type mismatch

Tushare returns `trade_date` as **string** (e.g. `'20260522'`). Existing CSV stores it as **numpy int64**.

Merging without `.astype(int)` on both sides causes:
- `TypeError: '<' not supported between instances of 'str' and 'int'` on `sort_values`
- Silent dedup failure (string `'20260522'` ≠ int `20260522`)

Always run `.astype(int)` on both `new_data['trade_date']` and `existing['trade_date']` before concat.

## Performance

- ~10 trading days × ~5500 stocks = ~55K rows in ~30 seconds
- Tushare free tier supports this easily (10 API calls with 5500 rows each)

## Fallback for missing month CSV

If `daily_data/2026/202605.csv` doesn't exist yet (beginning of month):
```python
# Create from first Tushare pull
new_data.to_csv('data/stock-pick/daily_data/2026/202605.csv', index=False)
```

## Post-pull: kill the stuck efinance process

After pulling daily data, the efinance process is no longer needed:
```bash
# Find and kill the efinance python process
CN_CHILD=$(pgrep -P <bash_pid>)
kill $CN_CHILD
# Or kill the whole background session
process kill <session_id>
```
