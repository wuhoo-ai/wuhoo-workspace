#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A 股换手率数据拉取 — 使用 Tushare daily_basic API

策略：按交易日拉取（每天 1 次 API 调用，返回全市场 5000+ 股票）
- 全量：拉取所有交易日
- 增量：仅拉取最近缺失的交易日

用法:
    source venv/bin/activate
    PYTHONUNBUFFERED=1 python fetch_turnover.py --full
    PYTHONUNBUFFERED=1 python fetch_turnover.py --incremental
"""

import os
import sys

# Ensure unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# ============== 路径配置 ==============
DATA_DIR = Path.home() / '.openclaw' / 'data' / 'stock-pick'
DAILY_DATA_DIR = DATA_DIR / 'daily_data'
TURNOVER_DATA_DIR = DATA_DIR / 'turnover_data'
INDEX_FILE = DATA_DIR / 'index_members.csv'

BATCH_SIZE = 120    # 每批交易日数（Tushare 限流 ~120/min）
INITIAL_DELAY = 0.5 # 批次间延迟（秒）
MAX_RETRIES = 5


def get_pro_api():
    token = os.environ.get('TUSHARE_TOKEN')
    if not token:
        with open(Path.home() / '.openclaw' / '.env') as f:
            for line in f:
                if line.startswith('TUSHARE_TOKEN='):
                    token = line.strip().split('=', 1)[1]
                    break
    if not token:
        raise ValueError("TUSHARE_TOKEN 未设置")
    import tushare as ts
    ts.set_token(token)
    return ts.pro_api()


def get_trade_dates(pro, start_date, end_date):
    """获取 A 股交易日列表"""
    df = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)
    df = df[df['is_open'] == 1]
    return df['cal_date'].tolist()


def load_index_members():
    """加载中证 1000 成分股代码"""
    if INDEX_FILE.exists():
        return pd.read_csv(INDEX_FILE)['code'].tolist()
    return None


def fetch_turnover_full(pro, members=None):
    """全量拉取换手率数据"""
    print("=" * 60)
    print("A 股换手率数据全量拉取 (Tushare daily_basic)")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 获取交易日列表
    start_str = '20240401'
    end_str = datetime.now().strftime('%Y%m%d')
    print(f"\n获取交易日列表 ({start_str} ~ {end_str})...")
    trade_dates = get_trade_dates(pro, start_str, end_str)
    print(f"  交易日数量: {len(trade_dates)}")

    if not trade_dates:
        print("  ⚠️  无交易日，终止")
        return

    # 加载成分股（用于过滤）
    if members is None:
        members = load_index_members()
    if members:
        members_set = set(members)
        print(f"  成分股过滤: {len(members)} 只")
    else:
        members_set = None
        print("  无成分股过滤（拉取全市场）")

    # 按批次拉取
    success_days = 0
    fail_days = []
    total_calls = 0

    for bi in range(0, len(trade_dates), BATCH_SIZE):
        batch_dates = trade_dates[bi:bi + BATCH_SIZE]
        print(f"\n批次 [{bi//BATCH_SIZE + 1}/{(len(trade_dates)-1)//BATCH_SIZE + 1}]: {batch_dates[0]} ~ {batch_dates[-1]} ({len(batch_dates)} 天)...")

        batch_data = []
        for td in batch_dates:
            # 检查是否已存在
            year = td[:4]
            month = td[:6]
            month_file = TURNOVER_DATA_DIR / year / f"{month}.csv"

            # 尝试获取当月已有数据的日期
            existing_dates = set()
            if month_file.exists() and month_file.stat().st_size > 0:
                existing_df = pd.read_csv(month_file)
                if 'trade_date' in existing_df.columns:
                    existing_dates = set(existing_df['trade_date'].astype(str).unique())

            if td in existing_dates:
                continue

            for attempt in range(MAX_RETRIES):
                try:
                    time.sleep(INITIAL_DELAY)
                    df = pro.daily_basic(trade_date=td,
                                         fields='ts_code,trade_date,turnover_rate,volume_ratio,total_mv,circ_mv')
                    total_calls += 1
                    if df is not None and not df.empty:
                        # 过滤成分股
                        if members_set:
                            df = df[df['ts_code'].isin(members_set)]
                        if not df.empty:
                            batch_data.append(df)
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        wait = 2 ** attempt
                        print(f"    {td} 重试 {attempt+1}/{MAX_RETRIES}，等待 {wait}s")
                        time.sleep(wait)
                    else:
                        print(f"    {td} 失败: {e}")
                        fail_days.append(td)

        if batch_data:
            month_df = pd.concat(batch_data, ignore_index=True)
            # 按月份保存
            for ym in month_df['trade_date'].astype(str).str[:6].unique():
                ym_data = month_df[month_df['trade_date'].astype(str).str[:6] == ym]
                year = ym[:4]
                month_file = TURNOVER_DATA_DIR / year / f"{ym}.csv"
                month_file.parent.mkdir(parents=True, exist_ok=True)

                if month_file.exists():
                    existing = pd.read_csv(month_file)
                    ym_data = pd.concat([existing, ym_data], ignore_index=True)
                    ym_data = ym_data.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')

                ym_data.to_csv(month_file, index=False)
                print(f"  {ym}: {len(ym_data)} 条记录")

            success_days += len(batch_data)

        if bi + BATCH_SIZE < len(trade_dates):
            time.sleep(0.3)

    print(f"\n完成: 成功 {success_days} 天, 失败 {len(fail_days)} 天, API 调用 {total_calls} 次")
    if fail_days:
        print(f"失败日期: {fail_days[:10]}{'...' if len(fail_days) > 10 else ''}")


def fetch_turnover_incremental(pro, members=None):
    """增量更新：仅拉取最近 35 天的换手率"""
    print("=" * 60)
    print("A 股换手率数据增量更新")
    print("=" * 60)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=35)
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')

    trade_dates = get_trade_dates(pro, start_str, end_str)
    print(f"  交易日: {len(trade_dates)} 天 ({start_str} ~ {end_str})")

    if members is None:
        members = load_index_members()
    members_set = set(members) if members else None

    success = 0
    for td in trade_dates:
        year = td[:4]
        month = td[:6]
        month_file = TURNOVER_DATA_DIR / year / f"{month}.csv"

        existing_dates = set()
        if month_file.exists():
            existing_df = pd.read_csv(month_file)
            if 'trade_date' in existing_df.columns:
                existing_dates = set(existing_df['trade_date'].astype(str).unique())

        if td in existing_dates:
            continue

        try:
            time.sleep(INITIAL_DELAY)
            df = pro.daily_basic(trade_date=td,
                                 fields='ts_code,trade_date,turnover_rate,volume_ratio,total_mv,circ_mv')
            if df is not None and not df.empty:
                if members_set:
                    df = df[df['ts_code'].isin(members_set)]
                if not df.empty:
                    month_file.parent.mkdir(parents=True, exist_ok=True)
                    if month_file.exists():
                        existing = pd.read_csv(month_file)
                        df = pd.concat([existing, df], ignore_index=True)
                        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
                    df.to_csv(month_file, index=False)
                    success += 1
                    print(f"  {td}: {len(df)} 条")
        except Exception as e:
            print(f"  {td} 失败: {e}")

    print(f"\n增量更新完成: {success}/{len(trade_dates)} 天")


def main():
    parser = argparse.ArgumentParser(description="A 股换手率数据拉取")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--full', action='store_true', help='全量拉取')
    mode.add_argument('--incremental', action='store_true', help='增量更新（最近 35 天）')
    parser.add_argument('--force', action='store_true', help='强制重建')

    args = parser.parse_args()

    TURNOVER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    pro = get_pro_api()
    print("Tushare 连接成功")

    members = load_index_members()

    if args.full:
        fetch_turnover_full(pro, members)
    elif args.incremental:
        fetch_turnover_incremental(pro, members)


if __name__ == '__main__':
    main()
