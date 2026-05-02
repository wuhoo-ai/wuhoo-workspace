#!/usr/bin/env python3
"""修复港股 daily_data_hk — 使用 yfinance 全量下载（无配额限制）"""
import sys, time

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path.home() / 'wuhoo-workspace' / 'data' / 'stock-pick'
DAILY_DATA_HK_DIR = DATA_DIR / 'daily_data_hk'

members = pd.read_csv(DATA_DIR / 'index_members_hk_top500.csv')['code'].tolist()
# Convert HK.00700 → 0700.HK (yfinance requires exactly 4-digit codes)
yf_codes = [f"{c.replace('HK.', '')[-4:]}.HK" for c in members]
print(f"HK stocks: {len(yf_codes)}")
print(f"Date range: 2024-01-01 ~ 2026-05-02")

start_str = '2024-01-01'
end_str = '2026-05-02'

all_data = []
success_count = 0
batch_size = 20

for i in range(0, len(yf_codes), batch_size):
    batch = yf_codes[i:i+batch_size]
    tickers_str = ' '.join(batch)
    
    try:
        data = yf.download(tickers_str, start=start_str, end=end_str, group_by='ticker', progress=False)
        
        if data is not None and not data.empty:
            for yf_code in batch:
                try:
                    if len(batch) == 1:
                        df = data
                    else:
                        df = data[yf_code]
                    if df is not None and not df.empty:
                        df = df.copy()
                        df.index = pd.to_datetime(df.index)
                        # Convert back to HK.XXXXX format
                        hk_code = f"HK.{yf_code.replace('.HK', '')}"
                        df['ts_code'] = hk_code
                        df = df.reset_index()
                        all_data.append(df)
                        success_count += 1
                except Exception:
                    pass
    except Exception:
        pass
    
    print(f"  进度：{min(i+batch_size, len(yf_codes))}/{len(yf_codes)} (成功：{success_count})")
    time.sleep(0.5)

if all_data:
    result = pd.concat(all_data, ignore_index=True)
    result['year_month'] = pd.to_datetime(result['Date']).dt.strftime('%Y%m')
    
    written = 0
    for ym in sorted(result['year_month'].unique()):
        ym_data = result[result['year_month'] == ym].copy()
        year = ym[:4]
        month_file = DAILY_DATA_HK_DIR / year / f"{ym}.csv"
        month_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Keep minimal columns for compatibility
        cols = ['ts_code', 'Date', 'Close', 'Volume']
        available = [c for c in cols if c in ym_data.columns]
        ym_data[available].to_csv(month_file, index=False)
        written += 1
    
    print(f"\nTotal: {written} monthly files, {len(result)} rows ({success_count}/{len(members)} stocks)")
else:
    print("\nERROR: No data downloaded")

print("Done!")
