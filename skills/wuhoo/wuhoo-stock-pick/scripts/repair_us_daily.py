#!/usr/bin/env python3
"""修复美股 daily_data_us — 重新下载 2024-2026 历史数据

用法:
    python3.11 repair_us_daily.py

依赖: yfinance, pandas (update_all_data.py 同目录)
"""
import sys
sys.path.insert(0, '/home/admin/wuhoo-workspace/skills/wuhoo/wuhoo-stock-pick')
from update_all_data import update_us_daily, DATA_DIR
import pandas as pd
from datetime import datetime

# 加载成分股
members_file = DATA_DIR / 'index_members_us_top500.csv'
members = pd.read_csv(members_file)['code'].tolist()
print(f"US stocks: {len(members)}")
print(f"Date range: 2024-01-01 ~ 2026-05-02")

# 重新下载
update_us_daily(
    members=members,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2026, 5, 2),
    force=True  # 覆盖现有文件
)

print("\nDone!")
