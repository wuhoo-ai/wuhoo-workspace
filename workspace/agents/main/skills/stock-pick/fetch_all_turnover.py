#!/usr/bin/env python3
"""后台获取全部 1000 只股票换手率数据"""

import efinance as ef
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import sys

DATA_DIR = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'data' / 'stock-pick'
TURNOVER_DATA_DIR = DATA_DIR / 'turnover_data'
TURNOVER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 读取成分股
members = pd.read_csv(DATA_DIR / 'index_members.csv')['code'].tolist()
print(f'成分股数量：{len(members)}', flush=True)

# 获取日期范围
end_date = datetime.now()
start_date = end_date - timedelta(days=550)
start_str = start_date.strftime('%Y%m%d')
end_str = end_date.strftime('%Y%m%d')

print(f'日期范围：{start_str} - {end_str}', flush=True)
print('开始获取全部股票换手率数据...', flush=True)

all_data = []
success_count = 0

for i, ts_code in enumerate(members):
    clean_code = ts_code.split('.')[0]
    try:
        df = ef.stock.get_quote_history(clean_code, start=start_str, end=end_str)
        if not df.empty:
            df['ts_code'] = ts_code
            df['日期'] = pd.to_datetime(df['日期'])
            df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)]
            if len(df) > 0:
                df_out = df[['ts_code', '日期', '换手率', '成交量']].copy()
                df_out.columns = ['ts_code', 'trade_date', 'turnover_rate', 'vol']
                df_out['trade_date'] = df_out['trade_date'].dt.strftime('%Y%m%d')
                all_data.append(df_out)
                success_count += 1
        
        if (i + 1) % 100 == 0:
            print(f'  进度：{i+1}/{len(members)} (成功：{success_count})', flush=True)
    except Exception as e:
        pass

if all_data:
    result = pd.concat(all_data, ignore_index=True)
    print(f'\n=== 完成 ===', flush=True)
    print(f'总计：{len(result)} 条记录', flush=True)
    print(f'成功：{success_count}/{len(members)} 只股票', flush=True)
    
    # 按月保存
    result['year_month'] = pd.to_datetime(result['trade_date'], format='%Y%m%d').dt.strftime('%Y%m')
    for ym in sorted(result['year_month'].unique()):
        ym_data = result[result['year_month'] == ym]
        year = ym[:4]
        month_file = TURNOVER_DATA_DIR / year / f'{ym}.csv'
        month_file.parent.mkdir(parents=True, exist_ok=True)
        ym_data.to_csv(month_file, index=False)
    
    print(f'\n✓ 全部换手率数据已保存', flush=True)
else:
    print('\n✗ 获取失败', flush=True)
    sys.exit(1)
