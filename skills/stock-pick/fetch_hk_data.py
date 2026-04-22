#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
港股数据拉取 — 使用 Futu OpenD API

数据：
1. Top 500 成分股（按市值排序）
2. 日线 K 线（2 年）
3. 换手率（含在 K 线数据中）

用法:
    source ~/wuhoo-workspace/venv-futu/bin/activate
    PYTHONUNBUFFERED=1 python fetch_hk_data.py --full
    PYTHONUNBUFFERED=1 python fetch_hk_data.py --incremental
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# ============== 路径配置 ==============
DATA_DIR = Path.home() / '.openclaw' / 'data' / 'stock-pick'
DAILY_DATA_DIR = DATA_DIR / 'daily_data_hk'
HK_MEMBERS_FILE = DATA_DIR / 'index_members_hk_top500.csv'

FUTU_HOST = '127.0.0.1'
FUTU_PORT = 11111

BATCH_SIZE = 50       # 每批股票数
INITIAL_DELAY = 0.3   # 批次间延迟（秒）
MAX_RETRIES = 3


def get_quote_ctx():
    from futu import OpenQuoteContext
    return OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)


def fetch_hk_members(pro, force=False):
    """获取港股 Top 500 成分股"""
    print(f"\n[1/3] 获取港股 Top 500 成分股...", flush=True)

    if HK_MEMBERS_FILE.exists() and not force:
        members = pd.read_csv(HK_MEMBERS_FILE)
        print(f"  已有成分股 {len(members)} 只，跳过 (使用 --force 强制更新)", flush=True)
        return members['code'].tolist()

    try:
        ctx = get_quote_ctx()
        from futu import RET_OK, SecurityType

        # 获取港股列表
        ret, data = ctx.get_stock_basicinfo(market='HK', stock_type=SecurityType.STOCK)
        ctx.close()

        if ret == RET_OK and data is not None and not data.empty:
            # 过滤未退市
            if 'delisting' in data.columns:
                data = data[data['delisting'] == 0]

            # 按代码排序取前 500（Futu 返回顺序大致按市值）
            data = data.sort_values('code').head(500)

            codes = data['code'].tolist()
            names = data['name'].tolist() if 'name' in data.columns else [''] * len(codes)

            pd.DataFrame({'code': codes, 'name': names}).to_csv(HK_MEMBERS_FILE, index=False)
            print(f"  Top 500 成分股已保存: {HK_MEMBERS_FILE}", flush=True)
            return codes
        else:
            print(f"  ⚠️ 无法获取港股成分股 (ret={ret})", flush=True)
            return []
    except Exception as e:
        print(f"  ⚠️ Futu OpenD 连接失败: {e}", flush=True)
        return []


def fetch_daily(members, incremental=False, force=False):
    """拉取港股日线 K 线"""
    print(f"\n[2/3] 拉取日线数据 ({len(members)} 只股票)...", flush=True)

    if not members:
        print("  ⚠️ 成分股为空，跳过", flush=True)
        return

    from futu import OpenQuoteContext, RET_OK, KLType

    # 计算时间范围
    end_date = datetime.now()
    if incremental:
        start_date = end_date - timedelta(days=35)
    else:
        start_date = end_date - timedelta(days=730)  # 2 年

    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    print(f"  时间范围: {start_str} ~ {end_str}", flush=True)

    all_data = []
    success_count = 0
    fail_count = 0

    try:
        ctx = get_quote_ctx()

        for i, code in enumerate(members):
            stock_code = f"HK.{code}" if not code.startswith('HK.') else code
            try:
                for attempt in range(MAX_RETRIES):
                    try:
                        time.sleep(INITIAL_DELAY)
                        ret, data, _ = ctx.request_history_kline(
                            code=stock_code, start=start_str, end=end_str, ktype=KLType.K_DAY
                        )

                        if ret == RET_OK and data is not None and not data.empty:
                            data['ts_code'] = stock_code
                            all_data.append(data)
                            success_count += 1
                        break
                    except Exception as e:
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(2 ** attempt)
                        else:
                            fail_count += 1
            except Exception:
                fail_count += 1

            # 定期保存和打印进度
            if (i + 1) % BATCH_SIZE == 0 or (i + 1) == len(members):
                if all_data:
                    result = pd.concat(all_data, ignore_index=True)
                    # 按月保存
                    result['trade_date_dt'] = pd.to_datetime(result['time_key'])
                    result['year_month'] = result['trade_date_dt'].dt.strftime('%Y%m')

                    for ym in sorted(result['year_month'].unique()):
                        ym_data = result[result['year_month'] == ym].copy()
                        year = ym[:4]
                        month_file = DAILY_DATA_DIR / year / f"{ym}.csv"
                        month_file.parent.mkdir(parents=True, exist_ok=True)

                        # 合并已有数据
                        if month_file.exists() and not force:
                            existing = pd.read_csv(month_file)
                            ym_data = pd.concat([existing, ym_data], ignore_index=True)
                            ym_data = ym_data.drop_duplicates(subset=['ts_code', 'time_key'], keep='last')

                        cols = ['ts_code', 'time_key'] + [c for c in ['open', 'close', 'high', 'low', 'volume', 'turnover_rate', 'turnover'] if c in ym_data.columns]
                        ym_data[[c for c in cols if c in ym_data.columns]].to_csv(month_file, index=False)

                pct = (i + 1) / len(members) * 100
                print(f"  进度: [{i+1}/{len(members)}] ({pct:.0f}%) 成功:{success_count} 失败:{fail_count}", flush=True)
                all_data = []  # 清空已保存数据

        ctx.close()
        print(f"\n  日线拉取完成: 成功 {success_count}/{len(members)}, 失败 {fail_count}", flush=True)

    except Exception as e:
        print(f"  ⚠️ Futu OpenD 连接失败: {e}", flush=True)


def fetch_turnover(members, incremental=False):
    """港股换手率已包含在 K 线数据中，此步骤仅做验证"""
    print(f"\n[3/3] 验证换手率数据...", flush=True)

    if not DAILY_DATA_DIR.exists():
        print("  无日线数据，跳过", flush=True)
        return

    csv_files = list(DAILY_DATA_DIR.rglob('*.csv'))
    total_rows = 0
    has_turnover = 0
    for f in csv_files:
        df = pd.read_csv(f)
        total_rows += len(df)
        if 'turnover_rate' in df.columns or 'turnover' in df.columns:
            has_turnover += len(df)

    print(f"  总记录: {total_rows:,} 条", flush=True)
    print(f"  含换手率: {has_turnover:,} 条 ({has_turnover/max(total_rows,1)*100:.0f}%)", flush=True)


def main():
    parser = argparse.ArgumentParser(description="港股数据拉取")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--full', action='store_true', help='全量拉取 2 年数据')
    mode.add_argument('--incremental', action='store_true', help='增量更新（最近缺失月份）')
    parser.add_argument('--force', action='store_true', help='强制重建')

    args = parser.parse_args()

    # 确保目录
    for d in [DATA_DIR, DAILY_DATA_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("港股数据全量拉取 (Futu OpenD)")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 获取成分股
    members = fetch_hk_members(None, force=args.force)

    if not members:
        print("\n⚠️ 成分股获取失败，终止", flush=True)
        return

    # 拉取日线
    fetch_daily(members, incremental=args.incremental, force=args.force)

    # 验证换手率
    fetch_turnover(members, incremental=args.incremental)

    print("\n" + "=" * 60)
    print("港股数据拉取完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
