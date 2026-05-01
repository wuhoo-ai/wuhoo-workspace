# Data Update Troubleshooting — 2026-05-01 Session Findings

## Session Summary

Full data update cron job run on 2026-05-01. CN update hung on efinance, HK failed (OpenD down), US partially succeeded but exposed a directory bug.

## Key Issues Discovered

### 1. US Data Overwrites CN Daily Data (CRITICAL BUG)

**Root cause**: `update_all_data.py` line 473 — `update_us_daily()` writes to `DAILY_DATA_DIR` (`daily_data/`) instead of `daily_data_us/`.

Both `update_cn_daily()` (line 148) and `update_us_daily()` (line 473) use the same path:
```python
month_file = DAILY_DATA_DIR / year / f"{ym}.csv"
```

**Impact**: Running `--market us` overwrites A-share daily data from 2024/10 onwards. After one US run, `daily_data/` contains:
- 2024/04–2024/09: Genuine A-share Tushare data (~4000-5000 stocks/month)
- 2024/10–2026/04: US S&P 500 data (~504 stocks/month)

**Detection**: Check ts_code column of any post-2024/09 file:
```python
import pandas as pd
df = pd.read_csv('daily_data/2026/202604.csv', nrows=5)
# If ts_code shows 'AAPL', 'ABBV' etc → data is US, not CN
# Correct CN format: '000001.SZ' etc
```

### 2. efinance Turnover Download Hangs

**Symptom**: Process runs 10+ minutes with zero output, ~1.7% CPU, 140MB RAM.

**Root cause**: `update_cn_turnover_efinance()` iterates ~1000 stocks one-by-one:
```python
for i, ts_code in enumerate(members):  # line 212
    df = ef.stock.get_quote_history(clean_code, ...)
```
Each call takes ~30s+ and returns empty due to API issues. Total: 1000 × 30s ≈ 8+ hours.

**Workaround**: Kill the process and skip turnover update. Daily data download (Tushare) completes before turnover starts.

### 3. Futu OpenD Connectivity

- OpenD was not running (`ECONNREFUSED` on 127.0.0.1:11111)
- `fetch_hk_data.py` retries indefinitely (15+ connection attempts observed)
- `venv-futu` does not exist at `~/wuhoo-workspace/venv-futu/bin/activate`
- `futu_api 10.2.6208` is installed in system python3.11, no venv needed

### 4. Python Print Buffering

All `print()` calls in `update_all_data.py` are fully buffered when stdout is a pipe (Hermes terminal capture). Zero output visible during entire run. Fix: `PYTHONUNBUFFERED=1`.

## Data State After 2026-05-01 Run

| Directory | Files | Rows (latest) | Status |
|-----------|-------|---------------|--------|
| `daily_data/` | 25 CSV | 10,564 (US data!) | 🔴 Corrupted |
| `daily_data_us/` | 2 CSV | 10,521 (US data) | ✅ Updated |
| `daily_data_hk/` | 2 CSV | 1,520 (stale) | ⚠️ Not updated |
| `turnover_data/` | 388 CSV | — (all pre-1997) | 🔴 Broken |

## Recovery Steps

1. **Fix daily_data/ corruption**: Delete US-contaminated months & force-rebuild CN
2. **Start Futu OpenD** before next HK update
3. **Fix update_all_data.py** to write US data to `daily_data_us/` not `daily_data/`
4. **Replace efinance** with Tushare `daily_basic` or akshare for turnover data
