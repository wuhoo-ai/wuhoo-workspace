#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据更新脚本 — 多数据源并行更新

数据源:
- Tushare Pro: A 股日线、成分股、财务数据
- Futu OpenD: 港股/美股 K 线、实时行情、成分股
- Akshare: A 股财务数据、换手率
- Efinance: A 股换手率（备用）
- Yfinance: 美股数据（备用）

确保 252 日残差等长周期因子数据充足（至少 18 个月日线）。

用法:
    source ~/wuhoo-workspace/skills/wuhoo-stock-pick/venv/bin/activate
    python update_all_data.py                    # 全量更新
    python update_all_data.py --market cn        # 仅 A 股
    python update_all_data.py --market hk        # 仅港股
    python update_all_data.py --market us        # 仅美股
    python update_all_data.py --incremental      # 增量更新（仅最新数据）
    python update_all_data.py --force            # 强制全量重建
"""

import os
import sys
import time
import argparse
import threading
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

# ============== 路径配置 ==============
DATA_DIR = Path.home() / 'wuhoo-workspace' / 'data' / 'stock-pick'
DAILY_DATA_DIR = DATA_DIR / 'daily_data'
TURNOVER_DATA_DIR = DATA_DIR / 'turnover_data'
FACTORS_DIR = DATA_DIR / 'factors'
BACKUPS_DIR = DATA_DIR / 'backups'

INDEX_CODE = '000852.SH'  # 中证 1000


def ensure_dirs():
    for d in [DATA_DIR, DAILY_DATA_DIR, TURNOVER_DATA_DIR, FACTORS_DIR, BACKUPS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return datetime.strptime(date_str, '%Y%m%d')


def format_date(dt):
    return dt.strftime('%Y%m%d')


# ============== Tushare 数据源 ==============

def get_pro_api():
    token = os.environ.get('TUSHARE_TOKEN')
    if not token:
        raise ValueError("TUSHARE_TOKEN 环境变量未设置")
    import tushare as ts
    ts.set_token(token)
    return ts.pro_api()


def update_cn_members(pro, force=False):
    """更新 A 股中证 1000 成分股"""
    print("\n[A 股] 更新中证 1000 成分股...")
    members_file = DATA_DIR / 'index_members.csv'

    if members_file.exists() and not force:
        print("  成分股已存在，跳过 (使用 --force 强制更新)")
        return pd.read_csv(members_file)['code'].tolist()

    # 获取最新成分股
    df = pro.index_weight(index_code=INDEX_CODE, start_date=format_date(datetime.now().replace(day=1)),
                          end_date=format_date(datetime.now()))
    if df.empty:
        # 回退：查上个月
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1)
        df = pro.index_weight(index_code=INDEX_CODE,
                              start_date=format_date(last_month),
                              end_date=format_date(last_month.replace(day=28)))

    if df.empty:
        print("  ⚠️  无法获取成分股数据")
        return []

    codes = df['con_code'].unique().tolist()
    print(f"  成分股数量：{len(codes)}")

    # 获取股票名称
    basic = pro.stock_basic(fields='ts_code,symbol,name,list_status')
    non_st = basic[~basic['name'].str.contains('ST|退', na=False)]
    members = [m for m in codes if m in non_st['ts_code'].values]
    print(f"  过滤 ST/退市后：{len(members)}")

    name_map = non_st.set_index('ts_code')['name'].to_dict()
    pd.DataFrame({'code': members}).to_csv(members_file, index=False)
    pd.Series(name_map).to_csv(DATA_DIR / 'stock_names.csv')

    return members


def update_cn_daily(pro, members, start_date=None, end_date=None, force=False, incremental=False):
    """更新 A 股日线数据"""
    print("\n[A 股] 更新日线数据...")

    if incremental and not force:
        # 增量：只更新最近缺失的月份
        end_date = end_date or datetime.now()
        start_date = end_date - timedelta(days=35)  # 更新最近 ~1.5 个月
    else:
        end_date = end_date or datetime.now()
        start_date = start_date or (end_date - timedelta(days=550))  # ~18 个月

    start_str = format_date(start_date)
    end_str = format_date(end_date)

    print(f"  时间范围：{start_str} ~ {end_str}")
    print(f"  股票数量：{len(members)}")

    # 按月分批获取
    months = []
    current = start_date.replace(day=1)
    while current <= end_date:
        months.append(current.strftime('%Y%m'))
        current = current + pd.DateOffset(months=1)
        current = current.replace(day=1)

    print(f"  需要更新 {len(months)} 个月")

    all_data = []
    for mi, ym in enumerate(months):
        month_start = ym + '01'
        month_end = end_str if ym == months[-1] else (parse_date(ym + '01') + pd.DateOffset(months=1) - timedelta(days=1)).strftime('%Y%m%d')

        # 检查是否已存在
        year = ym[:4]
        month_file = DAILY_DATA_DIR / year / f"{ym}.csv"
        if month_file.exists() and not force:
            print(f"  月份 {ym}: 已存在，跳过 (--force 强制更新)")
            continue

        month_data = []
        batch_size = 20
        for i in range(0, len(members), batch_size):
            batch = members[i:i+batch_size]
            try:
                df = pro.daily(ts_code=','.join(batch), start_date=month_start, end_date=month_end)
                if not df.empty:
                    month_data.append(df)
            except Exception as e:
                print(f"    批次 {i//batch_size + 1} 失败：{e}")
                time.sleep(0.5)

        if month_data:
            month_df = pd.concat(month_data, ignore_index=True)
            all_data.append(month_df)

            # 保存
            month_file.parent.mkdir(parents=True, exist_ok=True)
            month_df['year_month'] = pd.to_datetime(month_df['trade_date'], format='%Y%m%d').dt.strftime('%Y%m')
            ym_data = month_df[month_df['year_month'] == ym]
            if not ym_data.empty:
                ym_data.drop(columns=['year_month'], inplace=True)
                ym_data.to_csv(month_file, index=False)

            print(f"  月份 {ym}: {len(month_df)} 条记录")

        # 避免 API 限流
        time.sleep(0.3)

    print(f"  A 股日线更新完成：{len(all_data)} 个月")


def update_cn_turnover_efinance(members, start_date=None, end_date=None, force=False):
    """使用 efinance 更新 A 股换手率"""
    print("\n[A 股] 更新换手率数据 (efinance)...")

    try:
        import efinance as ef
    except ImportError:
        print("  ⚠️  efinance 未安装，跳过")
        return

    if not members:
        members_file = DATA_DIR / 'index_members.csv'
        if members_file.exists():
            members = pd.read_csv(members_file)['code'].tolist()
        else:
            print("  ⚠️  无成分股数据")
            return

    end_date = end_date or datetime.now()
    start_date = start_date or (end_date - timedelta(days=550))
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')

    all_data = []
    success_count = 0

    print(f"  股票数量：{len(members)}")
    for i, ts_code in enumerate(members):
        clean_code = ts_code.split('.')[0]
        try:
            df = ef.stock.get_quote_history(clean_code, start=start_str, end=end_str)
            if not df.empty:
                df_rename = df.rename(columns={
                    '股票代码': 'ts_code',
                    '日期': 'trade_date',
                    '换手率': 'turnover_rate',
                    '成交量': 'vol'
                })
                df_rename['ts_code'] = ts_code
                df_rename['trade_date'] = pd.to_datetime(df_rename['trade_date']).dt.strftime('%Y%m%d')
                all_data.append(df_rename[['ts_code', 'trade_date', 'turnover_rate', 'vol']])
                success_count += 1
        except Exception:
            pass

        if (i + 1) % 50 == 0:
            print(f"    进度：{i+1}/{len(members)} (成功：{success_count})")
            time.sleep(1)

    if all_data:
        result = pd.concat(all_data, ignore_index=True)
        result['year_month'] = pd.to_datetime(result['trade_date'], format='%Y%m%d').dt.strftime('%Y%m')
        for ym in result['year_month'].unique():
            ym_data = result[result['year_month'] == ym]
            year = ym[:4]
            month_file = TURNOVER_DATA_DIR / year / f"{ym}.csv"
            month_file.parent.mkdir(parents=True, exist_ok=True)
            ym_data.drop(columns=['year_month'], inplace=True)
            ym_data.to_csv(month_file, index=False)

        print(f"  换手率更新完成：{len(result)} 条记录 ({success_count}/{len(members)} 只股票)")
    else:
        print("  ⚠️  换手率数据获取失败")


# ============== Futu OpenD 数据源 ==============

def update_hk_members(force=False):
    """使用 Futu OpenD 更新港股 Top 500"""
    print("\n[港股] 更新 Top 500 成分股...")
    members_file = DATA_DIR / 'index_members_hk_top500.csv'

    if members_file.exists() and not force:
        print("  成分股已存在，跳过 (使用 --force 强制更新)")
        return pd.read_csv(members_file)['code'].tolist()

    try:
        from futu import OpenQuoteContext, RET_OK, SecurityType
    except ImportError:
        print("  ⚠️  futu-api 未安装")
        return []

    try:
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        # 获取港股股票列表 (get_stock_basicinfo 返回所有港股)
        ret, data = quote_ctx.get_stock_basicinfo(market='HK', stock_type=SecurityType.STOCK)
        quote_ctx.close()

        if ret == RET_OK and data is not None and not data.empty:
            # 过滤未退市股票
            if 'delisting' in data.columns:
                data = data[data['delisting'] == 0]

            # 获取市值信息并排序取 Top 500
            # get_market_state 提供实时行情数据
            codes = data['code'].tolist()
            names = data['name'].tolist() if 'name' in data.columns else [''] * len(codes)

            # 取前 500 只（按列表顺序，通常为市值排序）
            codes = codes[:500]
            names = names[:500]

            pd.DataFrame({'code': codes, 'name': names}).to_csv(members_file, index=False)
            print(f"  港股 Top 500 成分股：{len(codes)}")
            return codes
        else:
            print("  ⚠️  无法获取港股成分股")
            return []
    except Exception as e:
        print(f"  ⚠️  Futu OpenD 连接失败：{e}")
        return []


def update_hk_daily(members, start_date=None, end_date=None, force=False):
    """使用 Futu OpenD 更新港股日线"""
    print("\n[港股] 更新日线数据 (Futu OpenD)...")

    try:
        from futu import OpenQuoteContext, RET_OK, KLType
    except ImportError:
        print("  ⚠️  futu-api 未安装")
        return

    if not members:
        hk_file = DATA_DIR / 'index_members_hk_top500.csv'
        if hk_file.exists():
            members = pd.read_csv(hk_file)['code'].tolist()
        else:
            print("  ⚠️  无港股成分股")
            return

    end_date = end_date or datetime.now()
    start_date = start_date or (end_date - timedelta(days=550))
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    print(f"  时间范围：{start_str} ~ {end_str}")
    print(f"  股票数量：{len(members)}")

    all_data = []
    success_count = 0

    try:
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

        for i, code in enumerate(members):
            stock_code = f"HK.{code.replace('.HK', '')}"
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
            except Exception:
                pass

            if (i + 1) % 50 == 0:
                print(f"    进度：{i+1}/{len(members)} (成功：{success_count})")

        quote_ctx.close()

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            # 按月保存
            result['trade_date_dt'] = pd.to_datetime(result['time_key'])
            result['year_month'] = result['trade_date_dt'].dt.strftime('%Y%m')

            for ym in result['year_month'].unique():
                ym_data = result[result['year_month'] == ym].copy()
                year = ym[:4]
                month_file = DAILY_DATA_DIR / year / f"{ym}.csv"
                month_file.parent.mkdir(parents=True, exist_ok=True)
                # 只保留需要的列
                cols = ['ts_code', 'time_key'] + [c for c in ym_data.columns if c in ['open', 'close', 'high', 'low', 'volume', 'turnover_rate']]
                ym_data = ym_data[[c for c in cols if c in ym_data.columns]]
                ym_data.to_csv(month_file, index=False)

            print(f"  港股日线更新完成：{len(result)} 条记录 ({success_count}/{len(members)} 只股票)")
        else:
            print("  ⚠️  无港股数据")

    except Exception as e:
        print(f"  ⚠️  Futu OpenD 连接失败：{e}")


# ============== Yfinance 数据源 ==============

def update_us_members(force=False):
    """更新美股 Top 500 (标普 500)"""
    print("\n[美股] 更新 Top 500 成分股...")
    members_file = DATA_DIR / 'index_members_us_top500.csv'

    if members_file.exists() and not force:
        print("  成分股已存在，跳过 (使用 --force 强制更新)")
        return pd.read_csv(members_file)['code'].tolist()

    try:
        import yfinance as yf
    except ImportError:
        print("  ⚠️  yfinance 未安装")
        return []

    # 获取标普 500 成分股
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        symbols = sp500['Symbol'].tolist()
        names = sp500['Security'].tolist()

        pd.DataFrame({'code': [f"{s}.US" for s in symbols], 'name': names}).to_csv(members_file, index=False)
        print(f"  美股 Top 500 成分股：{len(symbols)}")
        return [f"{s}.US" for s in symbols]
    except Exception as e:
        print(f"  ⚠️  获取标普 500 成分股失败：{e}")
        return []


def update_us_daily(members, start_date=None, end_date=None, force=False):
    """使用 yfinance 更新美股日线"""
    print("\n[美股] 更新日线数据 (yfinance)...")

    try:
        import yfinance as yf
    except ImportError:
        print("  ⚠️  yfinance 未安装")
        return

    if not members:
        us_file = DATA_DIR / 'index_members_us_top500.csv'
        if us_file.exists():
            members = pd.read_csv(us_file)['code'].tolist()
        else:
            print("  ⚠️  无美股成分股")
            return

    end_date = end_date or datetime.now()
    start_date = start_date or (end_date - timedelta(days=550))
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    print(f"  时间范围：{start_str} ~ {end_str}")
    print(f"  股票数量：{len(members)}")

    all_data = []
    success_count = 0
    batch_size = 20

    for i in range(0, len(members), batch_size):
        batch = members[i:i+batch_size]
        tickers_str = ' '.join([m.replace('.US', '') for m in batch])

        try:
            data = yf.download(tickers_str, start=start_str, end=end_str, group_by='ticker', progress=False)

            if data is not None and not data.empty:
                for symbol in batch:
                    clean_symbol = symbol.replace('.US', '')
                    try:
                        if len(batch) == 1:
                            df = data
                        else:
                            df = data[clean_symbol]
                        if df is not None and not df.empty:
                            df = df.copy()
                            df.index = pd.to_datetime(df.index)
                            df['ts_code'] = symbol
                            df = df.reset_index()
                            all_data.append(df)
                            success_count += 1
                    except Exception:
                        pass
        except Exception:
            pass

        print(f"    进度：{min(i+batch_size, len(members))}/{len(members)} (成功：{success_count})")
        time.sleep(1)

    if all_data:
        result = pd.concat(all_data, ignore_index=True)
        result['year_month'] = pd.to_datetime(result['Date'] if 'Date' in result.columns else result.iloc[:, 0]).dt.strftime('%Y%m')

        for ym in result['year_month'].unique():
            ym_data = result[result['year_month'] == ym].copy()
            year = ym[:4]
            month_file = DAILY_DATA_DIR / year / f"{ym}.csv"
            month_file.parent.mkdir(parents=True, exist_ok=True)
            ym_data.to_csv(month_file, index=False)

        print(f"  美股日线更新完成：{len(result)} 条记录 ({success_count}/{len(members)} 只股票)")
    else:
        print("  ⚠️  无美股数据")


# ============== 主流程 ==============

def run_update(market='all', incremental=False, force=False):
    """执行数据更新"""
    ensure_dirs()
    print("=" * 60)
    print("统一数据更新")
    print("=" * 60)
    print(f"市场：{market}")
    print(f"模式：{'增量' if incremental else '全量'}")
    print(f"强制：{'是' if force else '否'}")

    if market in ['all', 'cn']:
        # A 股
        try:
            pro = get_pro_api()
            members = update_cn_members(pro, force=force)
            update_cn_daily(pro, members, force=force, incremental=incremental)
            update_cn_turnover_efinance(members, force=force)
        except Exception as e:
            print(f"\n[A 股] 更新失败：{e}")
            import traceback
            traceback.print_exc()

    if market in ['all', 'hk']:
        # 港股
        try:
            members = update_hk_members(force=force)
            update_hk_daily(members, force=force)
        except Exception as e:
            print(f"\n[港股] 更新失败：{e}")

    if market in ['all', 'us']:
        # 美股
        try:
            members = update_us_members(force=force)
            update_us_daily(members, force=force)
        except Exception as e:
            print(f"\n[美股] 更新失败：{e}")

    print("\n" + "=" * 60)
    print("数据更新完成")
    print("=" * 60)

    # 数据质量检查
    print("\n数据质量检查:")
    if DAILY_DATA_DIR.exists():
        total_files = list(DAILY_DATA_DIR.rglob('*.csv'))
        print(f"  日线数据文件：{len(total_files)} 个")
        if total_files:
            total_rows = sum(len(pd.read_csv(f)) for f in total_files[:10])
            print(f"  最近 10 个月数据量：{total_rows} 条")


def main():
    parser = argparse.ArgumentParser(description="统一数据更新脚本")
    parser.add_argument("--market", type=str, default='all', choices=['all', 'cn', 'hk', 'us'],
                        help="市场 (all/cn/hk/us)")
    parser.add_argument("--incremental", action="store_true", help="增量更新（仅最新数据）")
    parser.add_argument("--force", action="store_true", help="强制全量重建")
    parser.add_argument("--start-date", type=str, help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="结束日期 (YYYY-MM-DD)")

    args = parser.parse_args()

    start_date = parse_date(args.start_date) if args.start_date else None
    end_date = parse_date(args.end_date) if args.end_date else None

    run_update(market=args.market, incremental=args.incremental, force=args.force)


if __name__ == '__main__':
    main()
