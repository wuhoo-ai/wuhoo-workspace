#!/usr/bin/env python3.11
"""
Fetch A-share daily K-line data via akshare and compute technical factors.
Use when:
  - Futu OpenD has no A-share market permissions
  - daily_data doesn't contain the target stocks
  - User has provided portfolio data and needs technical context

Usage:
  python3.11 akshare_tech_factors.py 002326 300390 002837 603026

Output: per-stock technical factors printed to stdout
"""
import akshare as ak
import numpy as np
import sys


def calc_factors(code, start="20260401", end="20260512"):
    """Calculate technical factors for a single A-share stock."""
    try:
        df = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=start, end_date=end, adjust="qfq"
        )
    except Exception as e:
        print(f"{code}: ERROR fetching data - {e}")
        return None

    if df.empty:
        print(f"{code}: NO DATA from akshare")
        return None

    closes = df['收盘'].values
    volumes = df['成交量'].values if '成交量' in df.columns else None
    n = len(closes)

    result = {
        'code': code,
        'rows': n,
        'latest_date': str(df.iloc[-1]['日期']),
        'latest_close': float(closes[-1]),
    }

    # Momentum
    if n >= 5:
        result['mom5d'] = round((closes[-1]/closes[-5] - 1) * 100, 2)
    if n >= 10:
        result['mom10d'] = round((closes[-1]/closes[-10] - 1) * 100, 2)
    if n >= 20:
        result['mom20d'] = round((closes[-1]/closes[-20] - 1) * 100, 2)

    # Volatility (20-day annualized)
    if n >= 21:
        rets = np.diff(closes[-21:]) / closes[-21:-1]
        result['volatility_20d'] = round(np.std(rets) * np.sqrt(252) * 100, 1)

    # RSI(14)
    if n >= 15:
        deltas = np.diff(closes[-15:])
        gains = np.sum(deltas[deltas > 0])
        losses = -np.sum(deltas[deltas < 0])
        if losses > 0:
            rs = gains / losses
            result['rsi14'] = round(100 - (100 / (1 + rs)), 1)
        else:
            result['rsi14'] = 100.0

    # Volume ratio
    if volumes is not None and n >= 20:
        vol5 = np.mean(volumes[-5:])
        vol20 = np.mean(volumes[-20:])
        if vol20 > 0:
            result['vol_ratio'] = round(vol5 / vol20, 2)

    # Turnover rate
    if '换手率' in df.columns and n >= 5:
        result['turnover_5d'] = round(float(np.mean(df['换手率'].values[-5:])), 2)

    # MA
    if n >= 5:
        result['ma5'] = round(float(np.mean(closes[-5:])), 3)
    if n >= 10:
        result['ma10'] = round(float(np.mean(closes[-10:])), 3)
    if n >= 20:
        result['ma20'] = round(float(np.mean(closes[-20:])), 3)

    # Max drawdown (20-day)
    if n >= 20:
        peak = np.maximum.accumulate(closes[-20:])
        dd = (closes[-20:] - peak) / peak * 100
        result['max_dd_20d'] = round(float(np.min(dd)), 1)

    return result


def main():
    codes = sys.argv[1:] if len(sys.argv) > 1 else ['002326', '300390', '002837', '603026']
    
    for code in codes:
        factors = calc_factors(code)
        if factors is None:
            continue
        
        print(f"\n{'='*50}")
        print(f"{code}: close={factors['latest_close']} date={factors['latest_date']}")
        for k, v in factors.items():
            if k in ('code', 'rows', 'latest_date', 'latest_close'):
                continue
            print(f"  {k}: {v}")

    print(f"\n{'='*50}")
    print("Done. Use these factors alongside user portfolio data and web_search fundamentals.")


if __name__ == '__main__':
    main()
