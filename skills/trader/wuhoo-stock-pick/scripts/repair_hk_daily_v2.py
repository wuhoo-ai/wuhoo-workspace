#!/usr/bin/env python3
"""修复港股 daily_data_hk — 带延迟和重连的渐进式下载

解决两个问题：
1. Futu OpenD API 对连续调用的限流（~60次后开始拒绝）
2. HK 代码前缀双重 Bug（已在 update_all_data.py 修复）

策略：
- 每 100 次调用重建连接
- 每次调用间 0.1s 延迟
- 连接建立后 0.3s 等待稳定
"""
import sys, time
sys.path.insert(0, '/home/admin/wuhoo-workspace/skills/trader/wuhoo-stock-pick')

import pandas as pd
from datetime import datetime
from pathlib import Path
from futu import OpenQuoteContext, RET_OK, KLType

DATA_DIR = Path.home() / 'wuhoo-workspace' / 'data' / 'stock-pick'
DAILY_DATA_HK_DIR = DATA_DIR / 'daily_data_hk'

members = pd.read_csv(DATA_DIR / 'index_members_hk_top500.csv')['code'].tolist()
print(f"HK stocks: {len(members)}")
print(f"Date range: 2024-01-01 ~ 2026-05-02")

start_str = '2024-01-01'
end_str = '2026-05-02'

all_data = []
success_count = 0
fail_count = 0
batch_reconnect = 100

for i, code in enumerate(members):
    if i % batch_reconnect == 0:
        if i > 0:
            try:
                quote_ctx.close()
                time.sleep(0.5)
            except:
                pass
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        time.sleep(0.3)
    
    stock_code = code  # already has HK. prefix
    try:
        ret, msg, df = quote_ctx.request_history_kline(
            code=stock_code, start=start_str, end=end_str, ktype=KLType.K_DAY
        )
        if ret == RET_OK:
            kline_df = msg if isinstance(msg, pd.DataFrame) else df
            if kline_df is not None and not kline_df.empty:
                kline_df['ts_code'] = stock_code
                all_data.append(kline_df)
                success_count += 1
            else:
                fail_count += 1
        else:
            fail_count += 1
    except Exception as e:
        fail_count += 1
    
    time.sleep(0.1)
    
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(members)} (OK={success_count} FAIL={fail_count})")

try:
    quote_ctx.close()
except:
    pass

print(f"\nFinal: {success_count}/{len(members)} stocks, {fail_count} failed")

if all_data:
    result = pd.concat(all_data, ignore_index=True)
    result['trade_date_dt'] = pd.to_datetime(result['time_key'])
    result['year_month'] = result['trade_date_dt'].dt.strftime('%Y%m')
    
    written = 0
    for ym in result['year_month'].unique():
        ym_data = result[result['year_month'] == ym].copy()
        year = ym[:4]
        month_file = DAILY_DATA_HK_DIR / year / f"{ym}.csv"
        month_file.parent.mkdir(parents=True, exist_ok=True)
        cols = ['ts_code', 'time_key'] + [c for c in ym_data.columns if c in ['open', 'close', 'high', 'low', 'volume', 'turnover_rate']]
        ym_data = ym_data[[c for c in cols if c in ym_data.columns]]
        ym_data.to_csv(month_file, index=False)
        written += 1
    
    print(f"Wrote {written} monthly files, {len(result)} total rows")
