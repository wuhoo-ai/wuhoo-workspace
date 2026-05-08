#!/usr/bin/env python3.11
"""
交易日检查脚本 — cronjob pre-exec script
输出 JSON 到 stdout，注入到 cron job prompt 作为上下文。

用法:
  python3.11 check_trading_day.py cn    # 检查 A 股交易日
  python3.11 check_trading_day.py us    # 检查美股交易日
  python3.11 check_trading_day.py cn us # 同时检查
"""
import sys
import json
from datetime import date, timedelta

def check_cn_trading_day(today):
    """Check if today is a CN trading day using akshare calendar."""
    try:
        import akshare as ak
        import pandas as pd
        df = ak.tool_trade_date_hist_sina()
        trade_dates = set(pd.to_datetime(df['trade_date']).dt.date)
        if today in trade_dates:
            return {"market": "CN", "is_trading_day": True, "next_trading_day": None}
        # Find next trading day
        future = [d for d in sorted(trade_dates) if d > today]
        next_day = future[0] if future else None
        return {"market": "CN", "is_trading_day": False, "next_trading_day": str(next_day) if next_day else None}
    except Exception as e:
        return {"market": "CN", "is_trading_day": None, "error": str(e)}

def check_us_trading_day(today):
    """Check if today is a US trading day using yfinance S&P 500 data."""
    try:
        import yfinance as yf
        sp500 = yf.Ticker("^GSPC")
        # Get last 10 days of data
        hist = sp500.history(period="10d")
        trade_dates = set(hist.index.date)
        if today in trade_dates:
            return {"market": "US", "is_trading_day": True, "next_trading_day": None}
        # Simple heuristic: US market trades Mon-Fri, check if today is weekday
        if today.weekday() >= 5:  # Sat/Sun
            next_biz = today + timedelta(days=(7 - today.weekday()))
            return {"market": "US", "is_trading_day": False, "next_trading_day": str(next_biz), "reason": "weekend"}
        # Could be a holiday - check if yesterday was trading
        yesterday = today - timedelta(days=1)
        while yesterday.weekday() >= 5:
            yesterday -= timedelta(days=1)
        last_trade = max(trade_dates) if trade_dates else None
        return {
            "market": "US",
            "is_trading_day": False,
            "next_trading_day": None,
            "last_trading_day": str(last_trade) if last_trade else None,
            "reason": "holiday_or_closed"
        }
    except Exception as e:
        return {"market": "US", "is_trading_day": None, "error": str(e)}

def main():
    markets = sys.argv[1:] if len(sys.argv) > 1 else ["cn"]
    today = date.today()
    results = []
    
    for m in markets:
        m_lower = m.lower()
        if m_lower in ("cn", "a", "ashare"):
            results.append(check_cn_trading_day(today))
        elif m_lower in ("us", "usstock"):
            results.append(check_us_trading_day(today))
        elif m_lower in ("hk", "hkstock"):
            # HK shares same calendar as CN for simplicity
            # (actually HK has slightly different holidays but close enough)
            r = check_cn_trading_day(today)
            r["market"] = "HK"
            results.append(r)
    
    print(json.dumps({"check_date": str(today), "results": results}, ensure_ascii=False))

if __name__ == "__main__":
    main()
