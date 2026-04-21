#!/usr/bin/env python3
"""
全市场股票数据定期更新脚本

数据源:
- A股: akshare
- 港股: akshare
- 美股: akshare / yfinance

保存到: ~/wuhoo-workspace/data/

用法:
  python3.11 scripts/update_stock_data.py [--market cn|hk|us|all] [--days N]
"""

import argparse
import datetime
import os
import sys
import warnings
import json
from pathlib import Path

warnings.filterwarnings("ignore")

# 数据根目录
DATA_ROOT = Path(os.path.expanduser("~/wuhoo-workspace/data"))

def get_stock_info_cn():
    """获取A股股票列表"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        df = df[['序号','代码','名称','最新价','涨跌幅','成交量','成交额','振幅','最高','最低','今开','昨收','量比','换手率','市盈率-动态','市净率','总市值','流通市值']]
        df.to_csv(DATA_ROOT / "cn/stock_info.csv", index=False, encoding='utf-8-sig')
        print(f"✓ A股股票列表: {len(df)} 只")
        return df
    except Exception as e:
        print(f"✗ 获取A股列表失败: {e}")
        return None

def get_stock_info_hk():
    """获取港股股票列表"""
    try:
        import akshare as ak
        df = ak.stock_hk_spot_em()
        cols = [c for c in ['代码','名称','最新价','涨跌幅','成交量','成交额','市值','市盈率'] if c in df.columns]
        df[cols].to_csv(DATA_ROOT / "hk/stock_info.csv", index=False, encoding='utf-8-sig')
        print(f"✓ 港股股票列表: {len(df)} 只")
        return df
    except Exception as e:
        print(f"✗ 获取港股列表失败: {e}")
        return None

def update_a_daily(daily_dir, end_date=None):
    """更新A股日线数据 (带技术指标)"""
    import akshare as ak
    import pandas as pd
    import numpy as np
    
    if end_date is None:
        end_date = datetime.datetime.now().strftime("%Y%m%d")
    
    # 获取最新交易日
    try:
        df = ak.stock_zh_a_hist_min_em(symbol="000001", period="daily", adjust="qfq")
    except:
        print("✗ 获取A股日线失败")
        return
    
    # 获取全市场历史数据
    stock_list = pd.read_csv(DATA_ROOT / "cn/stock_info.csv", dtype={'代码': str})
    codes = stock_list['代码'].tolist()[:100]  # 示例：先更新前100只，避免超时
    
    # 按周更新
    today = datetime.datetime.now()
    week_key = today.strftime("%Y%m%d")
    output_file = daily_dir / f"A_stock_daily_{week_key}.csv"
    
    all_data = []
    success = 0
    for i, code in enumerate(codes):
        try:
            hist = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            hist = hist.tail(300)  # 保留近300天
            
            # 计算技术指标
            hist['MA_5'] = hist['收盘'].rolling(5).mean()
            hist['MA_10'] = hist['收盘'].rolling(10).mean()
            hist['MA_20'] = hist['收盘'].rolling(20).mean()
            hist['MA_60'] = hist['收盘'].rolling(60).mean()
            
            hist['EMA_5'] = hist['收盘'].ewm(span=5).mean()
            hist['EMA_10'] = hist['收盘'].ewm(span=10).mean()
            hist['EMA_20'] = hist['收盘'].ewm(span=20).mean()
            
            # MACD
            ema12 = hist['收盘'].ewm(span=12).mean()
            ema26 = hist['收盘'].ewm(span=26).mean()
            hist['DIF'] = ema12 - ema26
            hist['DEA'] = hist['DIF'].ewm(span=9).mean()
            hist['MACD'] = 2 * (hist['DIF'] - hist['DEA'])
            
            # RSI
            delta = hist['收盘'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            hist['RSI'] = 100 - (100 / (1 + rs))
            
            # ATR
            high_low = hist['最高'] - hist['最低']
            high_close = abs(hist['最高'] - hist['收盘'].shift(1))
            low_close = abs(hist['最低'] - hist['收盘'].shift(1))
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            hist['ATR'] = tr.rolling(14).mean()
            
            hist['stock_code'] = code
            hist['stock_name'] = stock_list[stock_list['代码'] == code]['名称'].values[0] if not stock_list[stock_list['代码'] == code].empty else code
            all_data.append(hist)
            success += 1
        except Exception as e:
            pass
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined.to_csv(output_file, index=False)
        print(f"✓ A股日线更新: {success} 只股票, {len(combined)} 条记录 → {output_file.name}")

def update_hk_daily():
    """更新港股月度数据"""
    import akshare as ak
    import pandas as pd
    
    today = datetime.datetime.now()
    month_key = today.strftime("%Y%m")
    year = today.strftime("%Y")
    
    dest = DATA_ROOT / f"hk/daily/{year}/"
    dest.mkdir(parents=True, exist_ok=True)
    
    stock_list = pd.read_csv(DATA_ROOT / "hk/stock_info.csv", dtype={'代码': str})
    codes = stock_list['代码'].tolist()[:50]  # 示例：前50只
    
    all_data = []
    for code in codes:
        try:
            hist = ak.stock_hk_hist(symbol=code, period="daily", adjust="qfq")
            hist = hist[hist['日期'].str[:7] >= today.replace(month=1).strftime("%Y-%m")]
            hist['ts_code'] = code
            all_data.append(hist)
        except:
            pass
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined.to_csv(dest / f"{month_key}.csv", index=False)
        print(f"✓ 港股月度更新: {len(combined)} 条记录 → {month_key}.csv")

def update_us_daily():
    """更新美股日线"""
    import yfinance as yf
    import pandas as pd
    
    stock_list = pd.read_csv(DATA_ROOT / "us/stock_info.csv")
    symbols = stock_list['symbol'].tolist()[:100]
    
    today = datetime.datetime.now()
    dest = DATA_ROOT / "us/daily/"
    dest.mkdir(parents=True, exist_ok=True)
    
    all_data = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="1y")
            if not hist.empty:
                hist['symbol'] = sym
                all_data.append(hist)
        except:
            pass
    
    if all_data:
        combined = pd.concat(all_data)
        combined.to_csv(dest / f"us_daily_{today.strftime('%Y%m%d')}.csv")
        print(f"✓ 美股日线更新: {len(all_data)} 只股票")

def main():
    parser = argparse.ArgumentParser(description="全市场股票数据更新")
    parser.add_argument("--market", choices=["cn", "hk", "us", "all"], default="all")
    parser.add_argument("--days", type=int, default=30, help="更新天数")
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"📊 全市场数据更新 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 确保目录存在
    for d in ["cn/daily", "cn/hourly", "hk/daily", "us/daily", "us/factors"]:
        (DATA_ROOT / d).mkdir(parents=True, exist_ok=True)
    
    if args.market in ["cn", "all"]:
        print("\n🇨🇳 更新A股...")
        get_stock_info_cn()
        update_a_daily(DATA_ROOT / "cn/daily")
    
    if args.market in ["hk", "all"]:
        print("\n🇭🇰 更新港股...")
        get_stock_info_hk()
        update_hk_daily()
    
    if args.market in ["us", "all"]:
        print("\n🇺🇸 更新美股...")
        try:
            update_us_daily()
        except Exception as e:
            print(f"⚠ 美股更新跳过: {e}")
    
    print("\n✅ 数据更新完成")

if __name__ == "__main__":
    main()
