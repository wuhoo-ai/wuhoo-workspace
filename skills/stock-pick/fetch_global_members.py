#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取港股 Top 500 和美股标普 500 成分股列表

使用富途 OpenAPI 获取实时市值数据，按市值排序

数据保存到：
- data/stock-pick/index_members_hk_top500.csv
- data/stock-pick/index_members_us_sp500.csv

使用方法：
    source /home/admin/.openclaw/workspace/agents/trade/venv-futu/bin/activate
    cd /home/admin/.openclaw/workspace/agents/main/skills/stock-pick
    python3 fetch_global_members.py
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
import shutil

import pandas as pd

# 导入富途 API
try:
    from futu import *
except ImportError:
    print("错误：futu-api 未安装")
    sys.exit(1)

# ============== 配置 ==============
DATA_DIR = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'data' / 'stock-pick'
BACKUPS_DIR = DATA_DIR / 'backups'

# 富途连接配置
FUTU_HOST = os.environ.get('FUTU_HOST', '127.0.0.1')
FUTU_PORT = int(os.environ.get('FUTU_PORT', 11111))

def ensure_dirs():
    for d in [DATA_DIR, BACKUPS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def backup_file(filepath):
    if filepath.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = BACKUPS_DIR / f"{filepath.stem}_{timestamp}{filepath.suffix}"
        shutil.copy(filepath, backup_path)
        print(f"  已备份：{backup_path.name}")

def convert_hk_code(futu_code):
    """转换富途港股代码：HK.00001 -> 00001.HK"""
    if futu_code.startswith('HK.'):
        return f"{futu_code[3:]}.HK"
    return futu_code

def convert_us_code(futu_code):
    """转换富途美股代码：US.AAPL -> AAPL.US"""
    if futu_code.startswith('US.'):
        return f"{futu_code[3:]}.US"
    return futu_code

def get_hk_top500():
    """获取港股 Top 500（按市值排序）"""
    print("\n[港股 Top 500] 获取中...")
    
    quote_ctx = OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
    
    try:
        ret, data = quote_ctx.get_stock_basicinfo(market=Market.HK, stock_type='STOCK')
        if ret != RET_OK:
            print(f"  错误：{data}")
            return [], None
        
        print(f"  获取 {len(data)} 只")
        
        # 过滤
        data = data[~data['delisting']]
        data = data[data['exchange_type'].str.contains('MAIN', na=False)]
        
        cutoff = datetime.now() - pd.Timedelta(days=180)
        data['listing_date'] = pd.to_datetime(data['listing_date'], errors='coerce')
        data = data[data['listing_date'] < cutoff]
        print(f"  有效股票：{len(data)} 只")
        
        # 获取市值
        stock_codes = data['code'].tolist()
        all_data = []
        batch_size = 30
        
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i+batch_size]
            ret, snapshot = quote_ctx.get_market_snapshot(batch)
            if ret == RET_OK and not snapshot.empty:
                all_data.append(snapshot[['code', 'total_market_val']])
            time.sleep(0.1)  # 避免请求过快
            if (i // batch_size + 1) % 20 == 0:
                print(f"    进度：{min(i+batch_size, len(stock_codes))}/{len(stock_codes)}")
        
        if not all_data:
            print("  错误：无法获取市值")
            return [], None
        
        market_data = pd.concat(all_data, ignore_index=True)
        result = data.merge(market_data, on='code', how='inner')
        result = result.dropna(subset=['total_market_val'])
        result = result.sort_values('total_market_val', ascending=False).head(500)
        
        result['ts_code'] = result['code'].apply(convert_hk_code)
        codes = result['ts_code'].tolist()
        
        print(f"  成功：{len(codes)} 只")
        return codes, result[['ts_code', 'code', 'name', 'total_market_val']]
        
    finally:
        quote_ctx.close()

def get_us_sp500():
    """获取美股标普 500（使用 yfinance）"""
    print("\n[美股 Top 500] 获取中 (yfinance)...")

    # 标普 500 成分股列表（硬编码主要成分股）
    # 由于网络访问限制，使用硬编码的标普 500 成分股列表
    SP500_SYMBOLS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'BRK.B', 'UNH', 'JNJ', 'JPM',
        'V', 'PG', 'XOM', 'MA', 'HD', 'CVX', 'MRK', 'ABBV', 'KO', 'PEP',
        'COST', 'AVGO', 'LLY', 'WMT', 'MCD', 'TMO', 'CSCO', 'ACN', 'ABT', 'DHR',
        'ADBE', 'NKE', 'TXN', 'NEE', 'BAC', 'CRM', 'VZ', 'DIS', 'INTC', 'CMCSA',
        'PFE', 'WFC', 'ORCL', 'AMD', 'NFLX', 'PM', 'UPS', 'RTX', 'T', 'QCOM',
        'HON', 'MS', 'UNP', 'LOW', 'IBM', 'SPGI', 'INTU', 'CAT', 'GS', 'AMGN',
        'ELV', 'AXP', 'BKNG', 'DE', 'SYK', 'TJX', 'BLK', 'GILD', 'LMT', 'MMC',
        'ADI', 'CVS', 'TMUS', 'ADP', 'CB', 'ISRG', 'PLD', 'MDT', 'CI', 'ZTS',
        'DUK', 'SO', 'BDX', 'SCHW', 'TGT', 'LRCX', 'PYPL', 'C', 'AMAT', 'MU',
        'REGN', 'NOW', 'CME', 'MO', 'EQIX', 'ITW', 'CL', 'APD', 'CSX', 'FI',
        'HUM', 'GD', 'PNC', 'ATVI', 'SHW', 'KLAC', 'EOG', 'SNPS', 'CDNS', 'MCK',
        'TFC', 'USB', 'NSC', 'AON', 'NXPI', 'ROP', 'ICE', 'SRE', 'FCX', 'WM',
        'ADSK', 'MCO', 'AFL', 'EMR', 'COF', 'PSA', 'GM', 'F', 'MCHP', 'TT',
        'AJG', 'NOC', 'DXCM', 'ORLY', 'WELL', 'HCA', 'TRV', 'AIG', 'CARR', 'PSX',
        'A', 'MNST', 'AEP', 'ROST', 'COP', 'MSCI', 'JCI', 'TEL', 'KMB',
        'GIS', 'AZO', 'IDXX', 'PCAR', 'OXY', 'CMG', 'EXC', 'YUM', 'CTAS',
        'BIIB', 'KMI', 'WBA', 'HES', 'EW', 'WEC', 'EA', 'CTSH', 'IQV',
        'ALL', 'PRU', 'SYY', 'DLTR', 'FTNT', 'MPC', 'VLO', 'APTV', 'DLR', 'EBAY',
        'PAYX', 'TSCO', 'WMB', 'O', 'MAR', 'OKE', 'SPG', 'EXR', 'KHC',
        'CHTR', 'GWW', 'HIG', 'AWK', 'ETN', 'VICI', 'RSG', 'FITB', 'MTD', 'SBAC',
        'FIS', 'CPRT', 'CBRE', 'ROK', 'HBAN', 'STZ', 'KEYS', 'NTRS', 'DFS', 'WAB',
        'ZBH', 'ANSS', 'TYL', 'TDG', 'FAST', 'ODFL', 'PPG', 'EXPE', 'TTWO', 'VRSN',
        'WY', 'MPWR', 'LVS', 'NTAP', 'GLW', 'CAH', 'ALGN', 'ENPH', 'WDC', 'ARE',
        'ZBRA', 'K', 'LH', 'DGX', 'SYF', 'CINF', 'VMC', 'MLM', 'PWR', 'INVH',
        'RMD', 'AVB', 'EQR', 'ESS', 'MAA', 'UDR', 'CPT', 'HST', 'REG', 'BXP',
        'FRT', 'KIM', 'PEAK', 'VTR', 'HCP', 'AMT', 'CCI',
    ]

    import yfinance as yf

    results = []
    batch_size = 10
    print(f"  开始获取 {len(SP500_SYMBOLS)} 只股票市值数据...")

    for i in range(0, len(SP500_SYMBOLS), batch_size):
        batch = SP500_SYMBOLS[i:i+batch_size]
        batch_data = []

        for symbol in batch:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                market_cap = info.get('marketCap')
                name = info.get('shortName', symbol)

                if market_cap and market_cap > 0:
                    batch_data.append({
                        'code': symbol,
                        'ts_code': f"{symbol}.US",
                        'name': name,
                        'total_market_val': market_cap
                    })
            except Exception as e:
                continue

        if batch_data:
            results.extend(batch_data)

        if (i // batch_size + 1) % 10 == 0:
            print(f"    进度：{min(i+batch_size, len(SP500_SYMBOLS))}/{len(SP500_SYMBOLS)} (成功：{len(results)})")

        time.sleep(0.5)  # 避免请求过快

    if not results:
        print("  错误：无法获取市值数据")
        return [], None

    # 按市值排序取前 500
    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values('total_market_val', ascending=False).head(500)

    codes = result_df['ts_code'].tolist()
    print(f"  成功：{len(codes)} 只")
    return codes, result_df[['ts_code', 'code', 'name', 'total_market_val']]

def save_members(codes, filepath, metadata_df=None):
    """保存成分股列表"""
    ensure_dirs()
    backup_file(filepath)
    
    pd.DataFrame({'code': codes}).to_csv(filepath, index=False)
    print(f"  已保存：{filepath}")
    
    if metadata_df is not None:
        meta_name = filepath.stem.replace('index_members', 'stock_info') + '.csv'
        meta_filepath = filepath.parent / meta_name
        metadata_df.to_csv(meta_filepath, index=False)
        print(f"  已保存：{meta_filepath}")

def main():
    ensure_dirs()
    
    print("=" * 60)
    print("获取港股 Top 500 和美股 Top 500 成分股")
    print("=" * 60)
    
    # 港股
    hk_codes, hk_meta = get_hk_top500()
    if hk_codes:
        save_members(hk_codes, DATA_DIR / 'index_members_hk_top500.csv', hk_meta)
    else:
        # 检查是否已有数据
        existing = DATA_DIR / 'index_members_hk_top500.csv'
        if existing.exists():
            print(f"\n  使用已有数据：{existing}")
        else:
            print("\n⚠️  港股数据获取失败")
    
    # 美股
    us_codes, us_meta = get_us_sp500()
    if us_codes:
        save_members(us_codes, DATA_DIR / 'index_members_us_top500.csv', us_meta)
    else:
        existing = DATA_DIR / 'index_members_us_top500.csv'
        if existing.exists():
            print(f"\n  使用已有数据：{existing}")
        else:
            print("\n⚠️  美股数据获取失败")
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
    
    print("\n成分股文件:")
    for f in ['index_members_hk_top500.csv', 'index_members_us_top500.csv']:
        fp = DATA_DIR / f
        if fp.exists():
            df = pd.read_csv(fp)
            print(f"  - {f}: {len(df)} 只")

if __name__ == '__main__':
    main()