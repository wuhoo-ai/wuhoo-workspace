#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多市场选股工具 (TA-Lib 专业版)

支持市场:
- cn: 中证 1000 (A 股) - 完整因子 (波动率 + 换手率 + 动量 + Beta)
- hk: 港股 Top 500 - 简化因子 (仅动量 + 波动率)
- us: 美股 Top 500 - 简化因子 (仅动量 + 波动率)

因子定义 (使用 TA-Lib 专业函数):
A 股完整因子:
1. 252 日残差波动率 - 越低越好，前 50%
2. 5 日平均换手率 - 越高越好，前 50%
3. 5 日价格动量 - 越高越好，前 30%
4. 20 日 Beta - 越高越好，前 30%
最终排序：10 日动量，越低越好，Top 10

港股/美股简化因子:
1. 252 日波动率 - 越低越好，前 50%
2. 5 日价格动量 - 越高越好，前 30%
最终排序：10 日动量，越低越好，Top 10
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import tushare as ts
import talib
import efinance as ef

warnings.filterwarnings('ignore')

# ============== 配置 ==============
DATA_DIR = Path.home() / 'wuhoo-workspace' / 'data' / 'stock-pick'
DAILY_DATA_DIR = DATA_DIR / 'daily_data'
TURNOVER_DATA_DIR = DATA_DIR / 'turnover_data'
FACTORS_DIR = DATA_DIR / 'factors'
BACKUPS_DIR = DATA_DIR / 'backups'

# 选股参数（默认值，可通过 CLI 或 JSON 覆盖）
VOLATILITY_PERCENTILE = 0.50
TURNOVER_PERCENTILE = 0.50
MOMENTUM_5D_PERCENTILE = 0.30
BETA_PERCENTILE = 0.20  # 前 20%（审查调整：从 0.30→0.15→0.20，平衡严格性与多样性）
BETA_HARD_FLOOR = 1.0    # Beta 绝对地板：低于 1.0 的防御型股票一律排除
TOP_N = 10
# 行业分散约束（2026-06-08 审查添加）
MAX_PER_INDUSTRY = 3
INDUSTRY_CACHE_FILE = DATA_DIR / 'stock_industry.csv'

def load_industry_map(pro=None):
    """加载行业映射，优先使用缓存"""
    if INDUSTRY_CACHE_FILE.exists():
        df = pd.read_csv(INDUSTRY_CACHE_FILE)
        return dict(zip(df['ts_code'], df['industry']))
    if pro is None:
        return {}
    try:
        basic = pro.stock_basic(fields='ts_code,industry')
        basic.to_csv(INDUSTRY_CACHE_FILE, index=False)
        return dict(zip(basic['ts_code'], basic['industry']))
    except Exception:
        return {}

def select_stocks_diverse(df, top_n, sort_factor='momentum_10d', ascending=True, industry_map=None, max_per_industry=MAX_PER_INDUSTRY):
    """行业分散选股：在排序基础上限制单行业集中度"""
    if industry_map is None or len(df) == 0:
        return df.head(top_n)
    
    df = df.sort_values(sort_factor, ascending=ascending)
    df = df.copy()
    df['_industry'] = df['ts_code'].map(industry_map).fillna('未知')
    
    selected = []
    industry_count = {}
    
    for _, row in df.iterrows():
        ind = row['_industry']
        if industry_count.get(ind, 0) >= max_per_industry:
            continue
        selected.append(row)
        industry_count[ind] = industry_count.get(ind, 0) + 1
        if len(selected) >= top_n:
            break
    
    if len(selected) < top_n:
        # 放宽约束：按排序补充（不限行业）
        selected_codes = {s['ts_code'] for s in selected}
        for _, row in df.iterrows():
            if len(selected) >= top_n:
                break
            if row['ts_code'] not in selected_codes:
                selected.append(row)
                selected_codes.add(row['ts_code'])
    
    result = pd.DataFrame(selected)
    if '_industry' in result.columns:
        result = result.drop(columns=['_industry'])
    return result

# 运行时因子配置（通过 --factors-json 加载）
FACTOR_CONFIG = {}

# 市场配置
MARKET_CONFIG = {
    'cn': {
        'name': 'A 股 (中证 1000)',
        'members_file': 'index_members.csv',
        'use_full_factors': True,  # 使用完整因子
    },
    'hk': {
        'name': '港股 Top 500',
        'members_file': 'index_members_hk_top500.csv',
        'use_full_factors': False,  # 使用简化因子
    },
    'us': {
        'name': '美股 Top 500',
        'members_file': 'index_members_us_top500.csv',
        'use_full_factors': False,  # 使用简化因子
    },
}

INDEX_CODE = '000852.SH'  # 中证 1000 指数代码

# ============== 因子配置 ==============

def load_factors_config(json_path=None):
    """加载因子配置，支持 JSON 文件或默认值"""
    global FACTOR_CONFIG
    if json_path and Path(json_path).exists():
        with open(json_path, 'r') as f:
            FACTOR_CONFIG = json.load(f)
        print(f"  因子配置已加载：{json_path}")
    return FACTOR_CONFIG

def get_percentile(factor_name, market='cn'):
    """获取指定因子的分位阈值，优先使用配置值"""
    defaults = {
        'residual_vol': VOLATILITY_PERCENTILE,
        'volatility': VOLATILITY_PERCENTILE,
        'turnover_5d': TURNOVER_PERCENTILE,
        'momentum_5d': MOMENTUM_5D_PERCENTILE,
        'beta_20d': BETA_PERCENTILE,
    }
    if market in FACTOR_CONFIG:
        pct = FACTOR_CONFIG[market].get('percentiles', {})
        return pct.get(factor_name, defaults.get(factor_name, 0.50))
    return defaults.get(factor_name, 0.50)

def get_top_n():
    """获取选股数量，优先使用配置值"""
    if 'cn' in FACTOR_CONFIG:
        return FACTOR_CONFIG['cn'].get('top_n', TOP_N)
    return TOP_N

def get_sort_config(market='cn'):
    """获取排序配置"""
    defaults = {'factor': 'momentum_10d', 'ascending': True}
    if market in FACTOR_CONFIG:
        cfg = FACTOR_CONFIG[market]
        return {
            'factor': cfg.get('sort_factor', defaults['factor']),
            'ascending': cfg.get('sort_ascending', defaults['ascending']),
        }
    return defaults

# ============== 工具函数 ==============

def ensure_dirs():
    for d in [DATA_DIR, DAILY_DATA_DIR, TURNOVER_DATA_DIR, FACTORS_DIR, BACKUPS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def get_pro_api():
    token = os.environ.get('TUSHARE_TOKEN')
    if not token:
        raise ValueError("TUSHARE_TOKEN 环境变量未设置")
    ts.set_token(token)
    return ts.pro_api()

def get_trade_cal(pro, start_date, end_date):
    cal = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date, is_open='1')
    return cal['cal_date'].tolist()

def backup_file(filepath):
    if filepath.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = BACKUPS_DIR / f"{filepath.stem}_{timestamp}{filepath.suffix}"
        shutil.copy(filepath, backup_path)

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return datetime.strptime(date_str, '%Y%m%d')

def format_date(dt):
    return dt.strftime('%Y%m%d')

# ============== 数据管理 ==============

def get_index_members(pro, target_date=None):
    """获取中证 1000 成分股"""
    if target_date:
        target_dt = parse_date(target_date)
        for i in range(3):
            check_dt = target_dt - pd.DateOffset(months=i)
            check_dt = check_dt.replace(day=1)
            start_str = check_dt.strftime('%Y%m%d')
            end_str = (check_dt + pd.DateOffset(months=1) - pd.Timedelta(days=1)).strftime('%Y%m%d')
            df = pro.index_weight(index_code=INDEX_CODE, start_date=start_str, end_date=end_str)
            if not df.empty:
                codes = df['con_code'].unique().tolist()
                print(f"  使用 {check_dt.strftime('%Y年%m月')} 成分股数据 ({len(codes)} 只)")
                return codes
    return []

def load_index_members():
    members_file = DATA_DIR / 'index_members.csv'
    if members_file.exists():
        return pd.read_csv(members_file)['code'].tolist()
    return None

def save_index_members(members):
    members_file = DATA_DIR / 'index_members.csv'
    backup_file(members_file)
    pd.DataFrame({'code': members}).to_csv(members_file, index=False)

def load_daily_data(start_date, end_date):
    """加载日线数据"""
    all_data = []
    start_dt = parse_date(start_date) if isinstance(start_date, str) else start_date
    end_dt = parse_date(end_date) if isinstance(end_date, str) else end_date
    
    current = start_dt.replace(day=1)
    while current <= end_dt:
        month_file = DAILY_DATA_DIR / f"{current.strftime('%Y')}" / f"{current.strftime('%Y%m')}.csv"
        if month_file.exists():
            all_data.append(pd.read_csv(month_file))
        current = current + pd.DateOffset(months=1)
        current = current.replace(day=1)
    
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

def save_daily_data(df, year_month):
    """保存日线数据"""
    year = year_month[:4]
    month_file = DAILY_DATA_DIR / year / f"{year_month}.csv"
    month_file.parent.mkdir(parents=True, exist_ok=True)
    if month_file.exists():
        existing = pd.read_csv(month_file)
        df = pd.concat([existing, df]).drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
    df.to_csv(month_file, index=False)

def load_turnover_data(start_date, end_date):
    """加载换手率数据"""
    all_data = []
    start_dt = parse_date(start_date) if isinstance(start_date, str) else start_date
    end_dt = parse_date(end_date) if isinstance(end_date, str) else end_date
    
    current = start_dt.replace(day=1)
    while current <= end_dt:
        month_file = TURNOVER_DATA_DIR / f"{current.strftime('%Y')}" / f"{current.strftime('%Y%m')}.csv"
        if month_file.exists():
            all_data.append(pd.read_csv(month_file))
        current = current + pd.DateOffset(months=1)
        current = current.replace(day=1)
    
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

def save_turnover_data(df, year_month):
    """保存换手率数据"""
    year = year_month[:4]
    month_file = TURNOVER_DATA_DIR / year / f"{year_month}.csv"
    month_file.parent.mkdir(parents=True, exist_ok=True)
    if month_file.exists():
        existing = pd.read_csv(month_file)
        df = pd.concat([existing, df]).drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
    df.to_csv(month_file, index=False)

def fetch_turnover_data_efinance(codes, start_date, end_date):
    """使用 efinance 获取换手率数据"""
    print("  使用 efinance 获取换手率数据...")
    all_data = []
    success_count = 0
    
    for i, ts_code in enumerate(codes):
        clean_code = ts_code.split('.')[0]
        try:
            df = ef.stock.get_quote_history(clean_code, start=start_date.replace('-', ''), end=end_date.replace('-', ''))
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
            
            if (i + 1) % 100 == 0:
                print(f"    进度：{i+1}/{len(codes)} (成功：{success_count})")
        except Exception as e:
            pass
    
    if all_data:
        result = pd.concat(all_data, ignore_index=True)
        result['year_month'] = pd.to_datetime(result['trade_date'], format='%Y%m%d').dt.strftime('%Y%m')
        for ym in result['year_month'].unique():
            ym_data = result[result['year_month'] == ym]
            save_turnover_data(ym_data, ym)
        print(f"  成功获取 {len(result)} 条换手率记录 ({success_count}/{len(codes)} 只股票)")
        return result
    return pd.DataFrame()

def fetch_daily_data(pro, codes, start_date, end_date, batch_size=20):
    """分月分批获取日线数据"""
    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)
    
    months = []
    current = start_dt.replace(day=1)
    while current <= end_dt:
        months.append(current.strftime('%Y%m'))
        current = current + pd.DateOffset(months=1)
        current = current.replace(day=1)
    
    total_months = len(months)
    print(f"  需要更新的月份：{len(months)} 个月")
    
    all_data = []
    for mi, ym in enumerate(months):
        month_start = ym + '01'
        month_end = end_date if ym == months[-1] else (parse_date(ym + '01') + pd.DateOffset(months=1)).strftime('%Y%m%d')
        
        month_data = []
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i+batch_size]
            try:
                df = pro.daily(ts_code=','.join(batch), start_date=month_start, end_date=month_end)
                if not df.empty:
                    month_data.append(df)
            except Exception:
                pass
        
        if month_data:
            month_df = pd.concat(month_data, ignore_index=True)
            all_data.append(month_df)
            print(f"  月份进度：{mi+1}/{total_months} ({ym}) - {len(month_df)} 条记录")
    
    if all_data:
        result = pd.concat(all_data, ignore_index=True)
        result['year_month'] = pd.to_datetime(result['trade_date'], format='%Y%m%d').dt.strftime('%Y%m')
        for ym in result['year_month'].unique():
            save_daily_data(result[result['year_month'] == ym], ym)
        return result
    return pd.DataFrame()

def update_data(pro, force=False):
    """更新数据（18 个月日线 + 换手率）"""
    print("\n=== 数据更新 ===")
    
    print("\n[1] 更新中证 1000 成分股...")
    members = get_index_members(pro, target_date=datetime.now().strftime('%Y-%m-%d'))
    
    print("  获取股票基本信息...")
    basic = pro.stock_basic(fields='ts_code,symbol,name,list_status')
    non_st = basic[~basic['name'].str.contains('ST|退', na=False)]
    members = [m for m in members if m in non_st['ts_code'].values]
    
    name_map = non_st.set_index('ts_code')['name'].to_dict()
    pd.Series(name_map).to_csv(DATA_DIR / 'stock_names.csv', header=['name'])
    save_index_members(members)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=550)
    start_str, end_str = format_date(start_date), format_date(end_date)
    
    print(f"\n[2] 拉取日线数据...")
    fetch_daily_data(pro, members, start_str, end_str, batch_size=20)
    
    print(f"\n[3] 拉取换手率数据 (efinance)...")
    turnover_df = fetch_turnover_data_efinance(members, start_str, end_str)
    if turnover_df.empty:
        print("  警告：换手率数据获取失败，将使用成交量作为代理指标")
    else:
        print(f"  成功获取 {len(turnover_df)} 条换手率记录")
    
    print("\n✓ 数据更新完成")

# ============== 因子计算 (TA-Lib 专业版) ==============

def calculate_factors_ta(pro, target_date):
    """使用 TA-Lib 专业函数计算所有因子 (A 股完整因子)"""
    target_dt = parse_date(target_date)
    target_str = format_date(target_dt)
    start_dt = target_dt - timedelta(days=400)
    start_str = format_date(start_dt)

    print(f"\n[数据准备] 加载 {start_str} 到 {target_str} 的数据...")

    # 加载日线数据
    data = load_daily_data(start_str, target_str)
    if data.empty:
        print("  错误：无可用数据")
        return None

    # 加载换手率数据
    turnover_data = load_turnover_data(start_str, target_str)
    has_turnover = not turnover_data.empty
    if has_turnover:
        print(f"  换手率数据：{len(turnover_data)} 条记录")
        turnover_data['trade_date'] = pd.to_datetime(turnover_data['trade_date'], format='%Y%m%d')
    else:
        print("  警告：无换手率数据，将使用成交量作为代理指标")

    # 准备数据
    data['trade_date'] = pd.to_datetime(data['trade_date'], format='%Y%m%d')
    target_pd = pd.Timestamp(target_dt)
    data = data[data['trade_date'] <= target_pd].copy()

    target_data = data[data['trade_date'] == target_pd].copy()
    if target_data.empty:
        latest = max(data['trade_date'].unique())
        target_data = data[data['trade_date'] == latest].copy()
        print(f"  使用最近交易日：{latest.strftime('%Y-%m-%d')}")

    print(f"  目标日期数据：{len(target_data)} 只股票")

    # 获取指数数据
    print("  获取指数数据...")
    index_data = pro.index_daily(ts_code=INDEX_CODE, start_date=start_str, end_date=target_str)
    if index_data.empty:
        return None
    index_data['trade_date'] = pd.to_datetime(index_data['trade_date'], format='%Y%m%d')
    index_data = index_data.sort_values('trade_date')

    # 计算因子
    codes = target_data['ts_code'].unique()
    results = []

    print("  计算因子 (TA-Lib 专业函数)...")
    skip_count = {'total': 0, 'len_stock': 0, 'len_merge': 0, 'min_len': 0, 'turnover': 0, 'mom5': 0, 'beta': 0, 'mom10': 0}
    for i, code in enumerate(codes):
        stock_df = data[data['ts_code'] == code].sort_values('trade_date')

        if len(stock_df) < 252:
            continue

        # 合并指数数据
        merged = stock_df.merge(index_data[['trade_date', 'close']], on='trade_date', how='inner', suffixes=('_stock', '_index'))
        if len(merged) < 252:
            continue

        stock_close = merged['close_stock'].values
        index_close = merged['close_index'].values

        # 计算收益率（小数形式，用于 Beta 计算）
        stock_ret = np.diff(stock_close) / stock_close[:-1]  # 小数形式，如 0.01 代表 1%
        index_ret = np.diff(index_close) / index_close[:-1]

        # 对齐长度
        min_len = min(len(stock_ret), len(index_ret))
        if min_len < 252:
            continue
        stock_ret = stock_ret[-min_len:]
        index_ret = index_ret[-min_len:]

        # 1. 252 日残差波动率 (手动计算残差标准差，用小数收益率)
        beta_252 = np.cov(stock_ret[-252:], index_ret[-252:])[0, 1] / np.var(index_ret[-252:])
        alpha_252 = np.mean(stock_ret[-252:]) - beta_252 * np.mean(index_ret[-252:])
        residual = stock_ret[-252:] - (alpha_252 + beta_252 * index_ret[-252:])
        residual_vol = np.std(residual) * np.sqrt(252)  # 年化波动率（小数形式）

        # 转换为百分比形式显示
        residual_vol_pct = residual_vol * 100

        # 2. 5 日平均换手率 (TA-Lib SMA)
        if has_turnover:
            stock_turnover = turnover_data[turnover_data['ts_code'] == code].sort_values('trade_date')
            if len(stock_turnover) >= 5:
                turnover_series = stock_turnover['turnover_rate'].values
                turnover_5d = talib.SMA(turnover_series, timeperiod=5)[-1]
            else:
                # 该股票无换手率数据，回退到成交量代理
                turnover_5d = np.log(stock_df.tail(5)['vol'].mean() + 1)
        else:
            # 使用成交量作为代理（对数转换使其更可比）
            turnover_5d = np.log(stock_df.tail(5)['vol'].mean() + 1)

        if np.isnan(turnover_5d):
            continue

        # 3. 5 日价格动量 (TA-Lib ROC) - 返回百分比
        momentum_5d = talib.ROC(stock_close, timeperiod=5)[-1]
        if np.isnan(momentum_5d):
            continue

        # 4. 20 日 Beta (手动计算，TA-Lib BETA 结果不可靠)
        beta_20d = np.cov(stock_ret[-20:], index_ret[-20:])[0, 1] / np.var(index_ret[-20:])
        if np.isnan(beta_20d) or np.isinf(beta_20d):
            continue

        # 5. 10 日价格动量 (TA-Lib ROC) - 返回百分比
        momentum_10d = talib.ROC(stock_close, timeperiod=10)[-1]
        if np.isnan(momentum_10d):
            continue

        results.append({
            'ts_code': code,
            'residual_vol': residual_vol_pct,  # 使用百分比形式
            'turnover_5d': turnover_5d,
            'momentum_5d': momentum_5d,
            'beta_20d': beta_20d,
            'momentum_10d': momentum_10d
        })

        if (i + 1) % 100 == 0:
            print(f"    进度：{i+1}/{len(codes)} (成功：{len(results)})")

    result_df = pd.DataFrame(results)

    # 添加股票名称
    name_file = DATA_DIR / 'stock_names.csv'
    if name_file.exists():
        names = pd.read_csv(name_file, index_col=0)
        result_df = result_df.merge(names, left_on='ts_code', right_index=True, how='left')

    print(f"  有效数据：{len(result_df)} 只股票")
    return result_df


def calculate_factors_us_complete(target_date):
    """
    美股完整因子计算（使用 yfinance 数据源）
    
    因子定义:
    1. 252 日残差波动率 - 相对于 SPY 的残差标准差，越低越好
    2. 5 日平均成交量 (log) - 流动性指标，越高越好
    3. 5 日价格动量 - TA-Lib ROC，越高越好
    4. 20 日 Beta - 相对于 SPY，越高越好
    5. 10 日价格动量 - 用于最终排序，越低越好
    """
    import yfinance as yf
    
    target_dt = parse_date(target_date)
    target_str = target_dt.strftime('%Y-%m-%d')
    start_dt = target_dt - timedelta(days=400)
    start_str = start_dt.strftime('%Y-%m-%d')

    print(f"\n[数据准备] 计算美股完整因子 (yfinance)...")

    # 加载成员股
    members_file = DATA_DIR / MARKET_CONFIG['us']['members_file']
    if not members_file.exists():
        print(f"  错误：成员股文件不存在 {members_file}")
        return None

    members_df = pd.read_csv(members_file)
    codes = members_df['code'].tolist() if 'code' in members_df.columns else members_df.iloc[:, 0].tolist()
    # 清理代码格式 (去除 US. 前缀，yfinance 不需要)
    codes = [c.replace('US.', '') for c in codes]
    print(f"  成分股数量：{len(codes)}")

    # 获取 SPY 数据作为基准
    print("  获取 SPY 基准数据...")
    try:
        spy = yf.Ticker("SPY")
        spy_df = spy.history(start=start_str, end=target_str, interval="1d")
        if len(spy_df) < 252:
            print("  警告：SPY 数据不足，使用简化模式")
            spy_df = None
        else:
            spy_returns = np.diff(spy_df['Close'].values) / spy_df['Close'].values[:-1]
            print(f"  SPY 数据：{len(spy_df)} 交易日")
    except Exception as e:
        print(f"  警告：SPY 数据获取失败：{e}")
        spy_df = None

    results = []
    batch_size = 20

    print("  获取个股数据并计算因子...")
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i+batch_size]

        for j, symbol in enumerate(batch):
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_str, end=target_str, interval="1d")

                if df is None or len(df) < 252:
                    continue

                close_prices = df['Close'].values
                volumes = df['Volume'].values

                # 计算收益率
                stock_returns = np.diff(close_prices) / close_prices[:-1]
                if len(stock_returns) < 252:
                    continue

                # 1. 252 日残差波动率 (相对于 SPY)
                if spy_df is not None and len(spy_returns) >= 252:
                    # 对齐长度
                    min_len = min(len(stock_returns[-252:]), len(spy_returns[-252:]))
                    stock_ret = stock_returns[-min_len:]
                    spy_ret = spy_returns[-min_len:]
                    
                    # 计算 Beta 和残差
                    beta_252 = np.cov(stock_ret, spy_ret)[0, 1] / np.var(spy_ret)
                    alpha_252 = np.mean(stock_ret) - beta_252 * np.mean(spy_ret)
                    residual = stock_ret - (alpha_252 + beta_252 * spy_ret)
                    residual_vol = np.std(residual) * np.sqrt(252) * 100  # 年化百分比
                else:
                    # 简化模式：使用简单波动率
                    residual_vol = np.std(stock_returns[-252:]) * np.sqrt(252) * 100

                # 2. 5 日平均成交量 (log 转换)
                turnover_5d = np.log(volumes[-5:].mean() + 1)

                # 3. 5 日价格动量 (TA-Lib ROC)
                momentum_5d = talib.ROC(close_prices, timeperiod=5)[-1]
                if np.isnan(momentum_5d):
                    continue

                # 4. 20 日 Beta (相对于 SPY)
                if spy_df is not None and len(spy_returns) >= 20:
                    min_len_20 = min(len(stock_returns[-20:]), len(spy_returns[-20:]))
                    beta_20d = np.cov(stock_returns[-min_len_20:], spy_returns[-min_len_20:])[0, 1] / np.var(spy_returns[-min_len_20:])
                    if np.isnan(beta_20d) or np.isinf(beta_20d):
                        beta_20d = 1.0
                else:
                    beta_20d = 1.0

                # 5. 10 日价格动量 (用于排序)
                momentum_10d = talib.ROC(close_prices, timeperiod=10)[-1]
                if np.isnan(momentum_10d):
                    continue

                results.append({
                    'ts_code': f"{symbol}.US",
                    'residual_vol': residual_vol,
                    'turnover_5d': turnover_5d,
                    'momentum_5d': momentum_5d,
                    'beta_20d': beta_20d,
                    'momentum_10d': momentum_10d
                })

            except Exception as e:
                continue

        print(f"    进度：{min(i+batch_size, len(codes))}/{len(codes)} (成功：{len(results)})")

    result_df = pd.DataFrame(results)

    # 添加股票名称
    info_file = DATA_DIR / 'stock_info_us_top500.csv'
    if info_file.exists():
        try:
            info_df = pd.read_csv(info_file)
            # 转换代码格式进行匹配
            info_df['symbol'] = info_df['ts_code'].str.replace('.US', '')
            result_df['symbol'] = result_df['ts_code'].str.replace('.US', '')
            result_df = result_df.merge(info_df[['symbol', 'name']], on='symbol', how='left')
            result_df = result_df.drop(columns=['symbol'])
        except Exception:
            pass

    # 添加 metadata 列
    if 'name' not in result_df.columns or result_df['name'].isna().all():
        result_df['name'] = 'N/A'
    result_df['market'] = 'us'

    print(f"  有效数据：{len(result_df)} 只股票")
    return result_df


# ============== 港股因子辅助函数 ==============

def _process_single_hk(df, hk_code, hsi_df, hsi_returns, results):
    """处理单只港股：从 yfinance DataFrame 提取 5 因子

    因子列表（对应 A 股/US 完整因子口径）：
    1. residual_vol  — 252 日残差波动率 (vs HSI)，越低越好
    2. turnover_5d   — 5 日 log 成交量（港股无换手率，用成交量代理）
    3. momentum_5d   — 5 日价格动量 (TA-Lib ROC)
    4. beta_20d      — 20 日 Beta (vs HSI)
    5. momentum_10d  — 10 日价格动量 (排序因子)
    """
    close_prices = df['Close'].values
    volumes = df['Volume'].values

    stock_returns = np.diff(close_prices) / close_prices[:-1]
    if len(stock_returns) < 252:
        return

    # 1. 残差波动率 (vs HSI)
    if hsi_df is not None and hsi_returns is not None and len(hsi_returns) >= 252:
        min_len = min(len(stock_returns[-252:]), len(hsi_returns[-252:]))
        stock_ret = stock_returns[-min_len:]
        hsi_ret = hsi_returns[-min_len:]
        beta_252 = np.cov(stock_ret, hsi_ret)[0, 1] / np.var(hsi_ret)
        alpha_252 = np.mean(stock_ret) - beta_252 * np.mean(hsi_ret)
        residual = stock_ret - (alpha_252 + beta_252 * hsi_ret)
        residual_vol = np.std(residual) * np.sqrt(252) * 100
    else:
        residual_vol = np.std(stock_returns[-252:]) * np.sqrt(252) * 100

    # 2. 换手率代理 (log 成交量)
    turnover_5d = np.log(volumes[-5:].mean() + 1)

    # 3. 5 日动量
    momentum_5d = talib.ROC(close_prices, timeperiod=5)[-1]
    if np.isnan(momentum_5d):
        return

    # 4. 20 日 Beta (vs HSI)
    if hsi_df is not None and hsi_returns is not None and len(hsi_returns) >= 20:
        min_len_20 = min(len(stock_returns[-20:]), len(hsi_returns[-20:]))
        beta_20d = np.cov(stock_returns[-min_len_20:], hsi_returns[-min_len_20:])[0, 1] / np.var(hsi_returns[-min_len_20:])
        if np.isnan(beta_20d) or np.isinf(beta_20d):
            beta_20d = 1.0
    else:
        beta_20d = 1.0

    # 5. 10 日动量
    momentum_10d = talib.ROC(close_prices, timeperiod=10)[-1]
    if np.isnan(momentum_10d):
        return

    results.append({
        'ts_code': hk_code,
        'residual_vol': residual_vol,
        'turnover_5d': turnover_5d,
        'momentum_5d': momentum_5d,
        'beta_20d': beta_20d,
        'momentum_10d': momentum_10d
    })


def _add_hk_names(result_df):
    """添加港股名称（优先 stock_info，回退成分股文件）"""
    if result_df.empty:
        return
    # 优先尝试 stock_info 文件
    info_file = DATA_DIR / 'stock_info_hk_top500.csv'
    if info_file.exists():
        try:
            info_df = pd.read_csv(info_file)
            merged = result_df.merge(info_df[['ts_code', 'name']], on='ts_code', how='left')
            result_df['name'] = merged['name']
        except Exception:
            pass
    # 回退到成分股文件
    if 'name' not in result_df.columns or result_df['name'].isna().all():
        members_file = DATA_DIR / 'index_members_hk_top500.csv'
        if members_file.exists():
            try:
                mem_df = pd.read_csv(members_file)
                mem_df = mem_df.rename(columns={'code': 'ts_code'})
                merged = result_df.merge(mem_df[['ts_code', 'name']], on='ts_code', how='left')
                result_df['name'] = merged['name']
            except Exception:
                pass
    if 'name' not in result_df.columns or result_df['name'].isna().all():
        result_df['name'] = 'N/A'
    result_df['market'] = 'hk'


def calculate_factors_simple(market, target_date):
    """
    简化因子计算 (港股/美股)
    - 港股: yfinance + HSI 基准，5 因子（残差波/换手率代理/动量/Beta）
    - 美股: 委托给 calculate_factors_us_complete

    注：港股因子输出列名与 US/A 股完整因子一致：
        residual_vol, turnover_5d, momentum_5d, beta_20d, momentum_10d
    """
    from futu import OpenQuoteContext, RET_OK, KLType

    # 美股已升级为完整因子
    if market == 'us':
        print("  提示：美股请使用完整因子模式 (calculate_factors_us_complete)")
        return calculate_factors_us_complete(target_date)

    # ============ 港股: yfinance + HSI 基准 ============
    if market == 'hk':
        import yfinance as yf

        target_dt = parse_date(target_date)
        target_str = target_dt.strftime('%Y-%m-%d')
        start_dt = target_dt - timedelta(days=400)
        start_str = start_dt.strftime('%Y-%m-%d')
        # yfinance end 参数不包含当日，+1 天
        end_dt = target_dt + timedelta(days=1)
        end_str = end_dt.strftime('%Y-%m-%d')

        print(f"\n[数据准备] 计算港股完整因子 (yfinance + HSI 基准)...")

        # 加载成员股
        members_file = DATA_DIR / MARKET_CONFIG['hk']['members_file']
        if not members_file.exists():
            print(f"  错误：成员股文件不存在 {members_file}")
            return None

        members_df = pd.read_csv(members_file)
        codes = members_df['code'].tolist() if 'code' in members_df.columns else members_df.iloc[:, 0].tolist()
        # HK.00700 → 0700.HK (yfinance 格式)
        yf_codes = [f"{c.replace('HK.', '')[-4:]}.HK" for c in codes]
        print(f"  成分股数量：{len(codes)}")

        # 获取 HSI 基准数据
        print("  获取 ^HSI 基准数据...")
        hsi_df = None
        hsi_returns = None
        try:
            hsi = yf.Ticker("^HSI")
            hsi_df_raw = hsi.history(start=start_str, end=end_str, interval="1d")
            if len(hsi_df_raw) < 252:
                print("  警告：^HSI 数据不足，使用简化模式")
            else:
                hsi_df = hsi_df_raw
                hsi_returns = np.diff(hsi_df['Close'].values) / hsi_df['Close'].values[:-1]
                print(f"  ^HSI 数据：{len(hsi_df)} 交易日")
        except Exception as e:
            print(f"  警告：^HSI 数据获取失败：{e}")

        results = []
        batch_size = 20

        print("  获取个股数据并计算因子...")
        for i in range(0, len(yf_codes), batch_size):
            batch = yf_codes[i:i+batch_size]
            tickers_str = ' '.join(batch)

            try:
                data = yf.download(tickers_str, start=start_str, end=end_str,
                                   group_by='ticker', progress=False, threads=True)
                if data.empty:
                    raise Exception("Empty download")
            except Exception:
                # Fallback: 单只股票下载
                for yf_code in batch:
                    try:
                        ticker = yf.Ticker(yf_code)
                        df = ticker.history(start=start_str, end=end_str, interval="1d")
                        if df is not None and len(df) >= 252:
                            hk_code = codes[yf_codes.index(yf_code)]
                            _process_single_hk(df, hk_code, hsi_df, hsi_returns, results)
                    except Exception:
                        pass
                continue

            for yf_code in batch:
                try:
                    if len(batch) == 1:
                        df = data
                    else:
                        has_levels = hasattr(data.columns, 'levels')
                        if has_levels and yf_code not in data.columns.levels[0]:
                            continue
                        df = data[yf_code]

                    if df is None or len(df) < 252:
                        continue

                    hk_code = codes[yf_codes.index(yf_code)]
                    _process_single_hk(df, hk_code, hsi_df, hsi_returns, results)

                except Exception:
                    continue

            print(f"    进度：{min(i+batch_size, len(yf_codes))}/{len(yf_codes)} (成功：{len(results)})")

        result_df = pd.DataFrame(results)
        _add_hk_names(result_df)

        print(f"  有效数据：{len(result_df)} 只股票")
        return result_df

    # 其他市场：使用 Futu（原逻辑）
    target_dt = parse_date(target_date)
    target_str = target_dt.strftime('%Y-%m-%d')
    start_dt = target_dt - timedelta(days=400)
    start_str = start_dt.strftime('%Y-%m-%d')

    print(f"\n[数据准备] 计算 {market} 简化因子...")
    members_file = DATA_DIR / MARKET_CONFIG[market]['members_file']
    if not members_file.exists():
        print(f"  错误：成员股文件不存在 {members_file}")
        return None

    members_df = pd.read_csv(members_file)
    codes = members_df['code'].tolist() if 'code' in members_df.columns else members_df.iloc[:, 0].tolist()
    print(f"  成分股数量：{len(codes)}")

    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    results = []

    print("  获取历史 K 线数据并计算因子...")
    for i in range(0, len(codes), 30):
        batch = codes[i:i+30]
        for code in batch:
            stock_code = code if code.startswith('HK.') else f"HK.{code}"
            try:
                result = quote_ctx.request_history_kline(
                    code=stock_code, start=start_str, end=target_str, ktype=KLType.K_DAY)
                ret, msg, df = result
                if ret == RET_OK and msg is not None and isinstance(msg, pd.DataFrame):
                    kline_df = msg
                elif ret == RET_OK and df is not None:
                    kline_df = df
                else:
                    continue
                if kline_df is None or len(kline_df) < 252:
                    continue
                close_prices = kline_df['close'].values
                returns = np.diff(close_prices) / close_prices[:-1]
                if len(returns) < 252:
                    continue
                volatility = np.std(returns[-252:]) * np.sqrt(252) * 100
                momentum_5d = talib.ROC(close_prices, timeperiod=5)[-1]
                if np.isnan(momentum_5d):
                    continue
                momentum_10d = talib.ROC(close_prices, timeperiod=10)[-1]
                if np.isnan(momentum_10d):
                    continue
                results.append({
                    'ts_code': code, 'volatility': volatility,
                    'momentum_5d': momentum_5d, 'momentum_10d': momentum_10d
                })
            except Exception:
                continue
        if (i + 30) % 60 == 0:
            print(f"    进度：{min(i+30, len(codes))}/{len(codes)}")

    quote_ctx.close()
    result_df = pd.DataFrame(results)
    _add_hk_names(result_df)
    result_df['market'] = market
    print(f"  有效数据：{len(result_df)} 只股票")
    return result_df

# ============== 选股逻辑 ==============

def select_stocks(factors_df, has_turnover=True):
    """执行选股逻辑 (A 股完整因子)，支持可配置因子"""
    if factors_df.empty:
        return factors_df
    df = factors_df.copy()
    vol_pct = get_percentile('residual_vol', 'cn')
    turn_pct = get_percentile('turnover_5d', 'cn')
    mom_pct = get_percentile('momentum_5d', 'cn')
    beta_pct = get_percentile('beta_20d', 'cn')
    top_n = get_top_n()
    sort_cfg = get_sort_config('cn')

    print("\n=== 选股过程 ===")
    print(f"\n1. 初始股票池：{len(df)} 只")

    # 1. 残差波动率 (越低越好)
    threshold = df['residual_vol'].quantile(vol_pct)
    df = df[df['residual_vol'] <= threshold]
    print(f"2. 252 日残差波动率 (≤{threshold:.4f}, 前{vol_pct*100:.0f}%)：{len(df)} 只")

    if len(df) == 0:
        return df

    # 2. 换手率/成交量 (越高越好)
    threshold = df['turnover_5d'].quantile(1 - turn_pct)
    df = df[df['turnover_5d'] >= threshold]
    if has_turnover:
        print(f"3. 5 日平均换手率 (≥{threshold:.2f}%, 前{turn_pct*100:.0f}%)：{len(df)} 只")
    else:
        print(f"3. 5 日平均成交量 [代理] (≥{threshold:.2f}, 前{turn_pct*100:.0f}%)：{len(df)} 只")

    if len(df) == 0:
        return df

    # 3. 5 日动量 (越高越好)
    threshold = df['momentum_5d'].quantile(1 - mom_pct)
    df = df[df['momentum_5d'] >= threshold]
    print(f"4. 5 日价格动量 ROC(≥{threshold:.2f}%, 前{mom_pct*100:.0f}%)：{len(df)} 只")

    if len(df) == 0:
        return df

    # 4. Beta (越高越好) — 取分位阈值和硬地板的最大值
    pct_threshold = df['beta_20d'].quantile(1 - beta_pct)
    threshold = max(pct_threshold, BETA_HARD_FLOOR)
    df = df[df['beta_20d'] >= threshold]
    print(f"5. 20 日 Beta 值 (≥{threshold:.3f}, 分位阈值={pct_threshold:.3f}, 硬地板={BETA_HARD_FLOOR})：{len(df)} 只")

    if len(df) == 0:
        return df

    # 最终排序 + 行业分散：按配置的排序因子
    industry_map = load_industry_map()
    df = df.sort_values(sort_cfg['factor'], ascending=sort_cfg['ascending'])
    df = select_stocks_diverse(df, top_n, sort_cfg['factor'], sort_cfg['ascending'], industry_map)
    return df


def select_stocks_us_complete(factors_df):
    """执行选股逻辑 (美股完整因子)，支持可配置因子"""
    if factors_df.empty:
        return factors_df
    df = factors_df.copy()
    vol_pct = get_percentile('residual_vol', 'us')
    turn_pct = get_percentile('turnover_5d', 'us')
    mom_pct = get_percentile('momentum_5d', 'us')
    beta_pct = get_percentile('beta_20d', 'us')
    top_n = get_top_n()

    print("\n=== 选股过程 (美股完整因子) ===")
    print(f"\n1. 初始股票池：{len(df)} 只")

    # 1. 残差波动率 (越低越好)
    threshold = df['residual_vol'].quantile(vol_pct)
    df = df[df['residual_vol'] <= threshold]
    print(f"2. 252 日残差波动率 (≤{threshold:.4f}, 前{vol_pct*100:.0f}%)：{len(df)} 只")

    if len(df) == 0:
        return df

    # 2. 成交量 (越高越好)
    threshold = df['turnover_5d'].quantile(1 - turn_pct)
    df = df[df['turnover_5d'] >= threshold]
    print(f"3. 5 日平均成交量 [log] (≥{threshold:.2f}, 前{turn_pct*100:.0f}%)：{len(df)} 只")

    if len(df) == 0:
        return df

    # 3. 5 日动量 (越高越好)
    threshold = df['momentum_5d'].quantile(1 - mom_pct)
    df = df[df['momentum_5d'] >= threshold]
    print(f"4. 5 日价格动量 ROC(≥{threshold:.2f}%, 前{mom_pct*100:.0f}%)：{len(df)} 只")

    if len(df) == 0:
        return df

    # 4. Beta (越高越好)
    threshold = df['beta_20d'].quantile(1 - beta_pct)
    df = df[df['beta_20d'] >= threshold]
    print(f"5. 20 日 Beta 值 (≥{threshold:.3f}, 前{beta_pct*100:.0f}%)：{len(df)} 只")

    if len(df) == 0:
        return df

    # 最终排序
    sort_cfg = get_sort_config('us')
    df = df.sort_values(sort_cfg['factor'], ascending=sort_cfg['ascending'])
    return df.head(top_n)


def select_stocks_simple(factors_df, market='hk'):
    """执行选股逻辑 (港股简化因子)，支持可配置因子"""
    if factors_df.empty:
        return factors_df
    df = factors_df.copy()
    vol_pct = get_percentile('volatility', market)
    mom_pct = get_percentile('momentum_5d', market)
    top_n = get_top_n()

    print(f"\n=== 选股过程 ({market.upper()} 简化因子) ===")
    print(f"\n1. 初始股票池：{len(df)} 只")

    # 1. 波动率 (越低越好)
    threshold = df['volatility'].quantile(vol_pct)
    df = df[df['volatility'] <= threshold]
    print(f"2. 252 日波动率 (≤{threshold:.4f}, 前{vol_pct*100:.0f}%)：{len(df)} 只")

    if len(df) == 0:
        return df

    # 2. 5 日动量 (越高越好)
    threshold = df['momentum_5d'].quantile(1 - mom_pct)
    df = df[df['momentum_5d'] >= threshold]
    print(f"3. 5 日价格动量 ROC(≥{threshold:.2f}%, 前{mom_pct*100:.0f}%)：{len(df)} 只")

    if len(df) == 0:
        return df

    # 最终排序
    sort_cfg = get_sort_config(market)
    df = df.sort_values(sort_cfg['factor'], ascending=sort_cfg['ascending'])
    return df.head(top_n)

def print_results(result, target_date, has_turnover=True, market="cn", use_complete_factors=False):
    """打印选股结果"""
    print("\n" + "=" * 100)
    market_name = MARKET_CONFIG.get(market, {}).get('name', market.upper())
    print(f"=== {market_name} 选股报告 ===")
    print(f"选股日期：{target_date}")
    print("=" * 100)

    if result.empty:
        print("\n⚠️  未选出符合条件的股票")
        return

    print(f"\n✓ 共选出 {len(result)} 只股票")

    print("\n" + "-" * 100)

    # 根据市场和因子类型选择不同的输出格式
    if market == 'us' and use_complete_factors:
        # 美股完整因子
        print(f"{'排名':<4} {'代码':<10} {'名称':<15} {'10 日 ROC%':<10} {'残差波%':<10} {'5 日量 (log)':<12} {'5 日 ROC%':<10} {'20 日 Beta':<10}")
        print("-" * 100)
        for i, (_, row) in enumerate(result.iterrows(), 1):
            name = row.get('name', 'N/A')
            print(f"{i:<4} {row['ts_code']:<10} {name:<15} {row['momentum_10d']:<10.2f} {row['residual_vol']:<10.4f} {row['turnover_5d']:<12.2f} {row['momentum_5d']:<10.2f} {row['beta_20d']:<10.3f}")
    elif market in ['hk']:
        # 港股完整因子：残差波 + 换手率 + 动量 + Beta
        print(f"{'排名':<4} {'代码':<10} {'名称':<15} {'10 日 ROC%':<10} {'残差波%':<10} {'5 日量 (log)':<12} {'5 日 ROC%':<10} {'20 日 Beta':<10}")
        print("-" * 100)
        for i, (_, row) in enumerate(result.iterrows(), 1):
            name = row.get('name', 'N/A')
            print(f"{i:<4} {row['ts_code']:<10} {name:<15} {row['momentum_10d']:<10.2f} {row['residual_vol']:<10.4f} {row['turnover_5d']:<12.2f} {row['momentum_5d']:<10.2f} {row['beta_20d']:<10.3f}")
    else:
        # A 股完整因子
        if has_turnover:
            print(f"{'排名':<4} {'代码':<10} {'名称':<12} {'10 日 ROC%':<12} {'252 残差波%':<12} {'5 日换手%':<12} {'5 日 ROC%':<12} {'20 日 Beta':<12}")
        else:
            print(f"{'排名':<4} {'代码':<10} {'名称':<12} {'10 日 ROC%':<12} {'252 残差波%':<12} {'5 日量 (log)':<12} {'5 日 ROC%':<12} {'20 日 Beta':<12}")
        print("-" * 100)
        for i, (_, row) in enumerate(result.iterrows(), 1):
            name = row.get('name', 'N/A')
            print(f"{i:<4} {row['ts_code']:<10} {name:<12} {row['momentum_10d']:<12.2f} {row['residual_vol']:<12.4f} {row['turnover_5d']:<12.2f} {row['momentum_5d']:<12.2f} {row['beta_20d']:<12.3f}")

    print("-" * 100)

    output_file = FACTORS_DIR / f"result_{market}_{target_date.replace('-', '')}.csv"
    result.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n结果已保存：{output_file}")

# ============== 主程序 ==============

def main():
    parser = argparse.ArgumentParser(description='多市场选股工具 (TA-Lib 专业版)')
    parser.add_argument('--market', type=str, default='cn', choices=['cn', 'hk', 'us'],
                        help='市场选择：cn (A 股), hk (港股), us (美股)')
    parser.add_argument('--date', type=str, help='选股日期')
    parser.add_argument('--update-data', action='store_true', help='更新数据 (仅 A 股)')
    parser.add_argument('--force', action='store_true', help='强制更新')
    parser.add_argument('--top-n', type=int, default=None, help='最终选股数量（覆盖默认值）')
    parser.add_argument('--factors-json', type=str, default=None,
                        help='因子配置 JSON 文件路径')

    args = parser.parse_args()
    market = args.market
    ensure_dirs()

    # 加载因子配置
    if args.factors_json:
        load_factors_config(args.factors_json)

    # CLI --top-n 覆盖
    if args.top_n is not None:
        global TOP_N
        TOP_N = args.top_n
        FACTOR_CONFIG.setdefault(market, {})['top_n'] = TOP_N
    
    # 检查市场配置
    if market not in MARKET_CONFIG:
        print(f"错误：不支持的市场 {market}")
        sys.exit(1)
    
    market_info = MARKET_CONFIG[market]
    target_date = args.date if args.date else (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"\n{'='*60}")
    print(f"多市场选股工具 (TA-Lib 专业版)")
    print(f"{'='*60}")
    print(f"市场：{market_info['name']}")
    print(f"目标日期：{target_date}")
    
    # A 股需要 Tushare API
    if market == 'cn':
        if args.update_data:
            try:
                pro = get_pro_api()
            except ValueError as e:
                print(f"错误：{e}")
                sys.exit(1)
            update_data(pro, force=args.force)
            return
        
        try:
            pro = get_pro_api()
        except ValueError as e:
            print(f"错误：{e}")
            sys.exit(1)
        
        print(f"\n[成分股加载]")
        members = load_index_members()
        if not members:
            print("  未找到成分股数据，请先运行 --update-data")
            sys.exit(1)
        print(f"  中证 1000 成分股数量：{len(members)}")
        
        print("\n[因子计算]")
        factors = calculate_factors_ta(pro, target_date)
        
        if factors is None or factors.empty:
            print("\n错误：因子计算失败")
            sys.exit(1)
        
        has_turnover = 'turnover_5d' in factors.columns and factors['turnover_5d'].median() < 50
        factors.to_csv(FACTORS_DIR / f"factors_cn_{target_date.replace('-', '')}.csv", index=False, encoding='utf-8-sig')
        
        result = select_stocks(factors, has_turnover=has_turnover)
        print_results(result, target_date, has_turnover=has_turnover, market=market)
    
    else:
        # 港股/美股
        print(f"\n[成分股加载]")
        members_file = DATA_DIR / market_info['members_file']
        if not members_file.exists():
            print(f"  错误：成员股文件不存在 {members_file}")
            print(f"  提示：请先运行 python fetch_global_members.py 获取 {market} 成分股")
            sys.exit(1)
        
        members_df = pd.read_csv(members_file)
        print(f"  成分股数量：{len(members_df)}")
        
        # 美股和港股使用完整因子
        if market in ('us', 'hk'):
            if market == 'us':
                print("\n[因子计算 (美股完整因子：残差波 + 成交量 + 动量 + Beta)]")
                factors = calculate_factors_us_complete(target_date)
            else:
                print("\n[因子计算 (港股完整因子：残差波 + 换手率 + 动量 + Beta)]")
                factors = calculate_factors_simple(market, target_date)
            
            if factors is None or factors.empty:
                print("\n错误：因子计算失败")
                sys.exit(1)
            
            factors.to_csv(FACTORS_DIR / f"factors_{market}_{target_date.replace('-', '')}.csv", index=False, encoding='utf-8-sig')
            
            result = select_stocks_us_complete(factors)
            print_results(result, target_date, market=market, use_complete_factors=True)

if __name__ == '__main__':
    main()
