#!/usr/bin/env python3
"""
迁移和整合全市场股票数据到统一目录结构

源目录:
- A股: ~/.openclaw/data/ai-trader/data/A_stock/ (带技术指标)
- A股: ~/.openclaw/data/stock-pick/daily_data/ (原始)
- 港股: ~/.openclaw/data/stock-pick/daily_data_hk/
- 美股: ~/.openclaw/data/stock-pick/factors/ + ~/.hermes/data/stock-pick/

目标目录:
~/wuhoo-workspace/data/
├── cn/daily/      # A股日线 (带指标)
├── cn/hourly/     # A股小时线
├── cn/stock_info.csv
├── hk/daily/      # 港股日线
├── hk/stock_info.csv
├── us/daily/      # 美股日线 (待补充)
├── us/factors/    # 美股因子
├── us/stock_info.csv
└── us/index_members.csv
"""

import os
import shutil
import glob
from pathlib import Path

def safe_mkdir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    print(f"✓ 创建目录: {path}")

def copy_files(src_pattern, dest_dir, dry_run=False):
    """复制匹配的文件到目标目录"""
    files = glob.glob(src_pattern)
    if not files:
        print(f"  ⚠ 未找到匹配文件: {src_pattern}")
        return 0
    
    count = 0
    for src in files:
        dest = os.path.join(dest_dir, os.path.basename(src))
        if dry_run:
            print(f"  → {src}")
        else:
            shutil.copy2(src, dest)
        count += 1
    
    print(f"  ✓ 复制 {count} 个文件到 {dest_dir}")
    return count

def main():
    home = os.path.expanduser("~")
    base_data = os.path.join(home, "wuhoo-workspace/data")
    
    print("=" * 60)
    print("开始迁移全市场股票数据")
    print(f"目标目录: {base_data}")
    print("=" * 60)
    
    # 1. 创建统一目录结构
    print("\n📁 创建目录结构...")
    for d in [
        f"{base_data}/cn/daily", f"{base_data}/cn/hourly",
        f"{base_data}/hk/daily",
        f"{base_data}/us/daily", f"{base_data}/us/factors",
    ]:
        safe_mkdir(d)
    
    # 2. 迁移A股日线 (带技术指标版)
    print("\n📊 迁移A股日线数据 (带技术指标)...")
    a_daily_src = os.path.join(home, ".openclaw/data/ai-trader/data/A_stock/")
    dest_a_daily = os.path.join(base_data, "cn/daily/")
    copy_files(f"{a_daily_src}A_stock_daily_*.csv", dest_a_daily)
    
    # 3. 迁移A股小时线
    print("\n⏱️ 迁移A股小时线数据...")
    dest_a_hourly = os.path.join(base_data, "cn/hourly/")
    copy_files(f"{a_daily_src}A_stock_hourly_*.csv", dest_a_hourly)
    copy_files(f"{a_daily_src}merged_hourly*.jsonl", dest_a_hourly)
    
    # 4. 迁移A股选股信息
    print("\n📋 迁移A股选股信息...")
    a_stock_info = os.path.join(home, ".openclaw/data/stock-pick/stock_names.csv")
    if os.path.exists(a_stock_info):
        shutil.copy2(a_stock_info, os.path.join(base_data, "cn/stock_info.csv"))
        print("  ✓ stock_names.csv → cn/stock_info.csv")
    
    # 5. 迁移港股日线
    print("\n📊 迁移港股日线数据...")
    hk_src = os.path.join(home, ".openclaw/data/stock-pick/daily_data_hk/")
    dest_hk = os.path.join(base_data, "hk/daily/")
    # 按年份复制
    for year in ["2024", "2025", "2026"]:
        year_src = os.path.join(hk_src, year)
        if os.path.exists(year_src):
            dest_year = os.path.join(dest_hk, year)
            safe_mkdir(dest_year)
            copy_files(f"{year_src}/*.csv", dest_year)
    
    # 6. 迁移港股股票信息
    print("\n📋 迁移港股股票信息...")
    hk_info = os.path.join(home, ".openclaw/data/stock-pick/stock_info_hk_top500.csv")
    if os.path.exists(hk_info):
        shutil.copy2(hk_info, os.path.join(base_data, "hk/stock_info.csv"))
        print("  ✓ stock_info_hk_top500.csv → hk/stock_info.csv")
    
    # 7. 迁移美股因子数据
    print("\n📊 迁移美股因子数据...")
    factors_src = os.path.join(home, ".openclaw/data/stock-pick/factors/")
    dest_us_factors = os.path.join(base_data, "us/factors/")
    copy_files(f"{factors_src}factors_us_*.csv", dest_us_factors)
    copy_files(f"{factors_src}result_us_*.csv", dest_us_factors)
    
    # 8. 迁移美股股票信息
    print("\n📋 迁移美股股票信息...")
    us_info = os.path.join(home, ".openclaw/data/stock-pick/index_members_us_top500.csv")
    if os.path.exists(us_info):
        shutil.copy2(us_info, os.path.join(base_data, "us/index_members.csv"))
        print("  ✓ index_members_us_top500.csv → us/index_members.csv")
    
    us_stock_info = os.path.join(home, ".openclaw/data/stock-pick/stock_info_us_top500.csv")
    if os.path.exists(us_stock_info):
        shutil.copy2(us_stock_info, os.path.join(base_data, "us/stock_info.csv"))
        print("  ✓ stock_info_us_top500.csv → us/stock_info.csv")
    
    # 9. 生成README
    print("\n📝 生成数据说明文档...")
    readme = f"""# 全市场股票数据

## 目录结构
```
data/
├── cn/                          # A股
│   ├── daily/                   # 日线 (OHLCV + MA/EMA/RSI/DIF等技术指标)
│   ├── hourly/                  # 小时线
│   └── stock_info.csv           # 股票基本信息
├── hk/                          # 港股
│   ├── daily/                   # 日线 (OHLCV)
│   └── stock_info.csv           # 港股500成分股信息
├── us/                          # 美股
│   ├── daily/                   # 日线 (待补充)
│   ├── factors/                 # 选股因子数据
│   ├── stock_info.csv           # 美股500成分股信息
│   └── index_members.csv        # 指数成分股
└── README.md
```

## 数据来源
- A股: akshare (通过 wuhoo-stock-pick skill)
- 港股: akshare
- 美股: yfinance / akshare

## 更新频率
每日收盘后自动更新 (cron job)

## 数据格式
- A股日线: stock_name, stock_code, trade_date, open, close, high, low, volume, amount, MA_5/10/20/60, EMA_5/10/20/60, RSI, DIF, DEA, ATR, OBV
- 港股日线: ts_code, time_key, open, close, high, low, volume, turnover_rate, turnover
- 美股因子: 各因子列 + 筛选结果
"""
    
    with open(os.path.join(base_data, "README.md"), "w") as f:
        f.write(readme)
    print("  ✓ README.md 已生成")
    
    print("\n" + "=" * 60)
    print("✅ 数据迁移完成！")
    print("=" * 60)
    
    # 统计结果
    import subprocess
    result = subprocess.run(f"du -sh {base_data}", shell=True, capture_output=True, text=True)
    print(f"总大小: {result.stdout.strip()}")
    
    for d in ["cn", "hk", "us"]:
        path = os.path.join(base_data, d)
        if os.path.exists(path):
            r = subprocess.run(f"find {path} -type f | wc -l", shell=True, capture_output=True, text=True)
            print(f"  {d}/: {r.stdout.strip()} 个文件")

if __name__ == "__main__":
    main()
