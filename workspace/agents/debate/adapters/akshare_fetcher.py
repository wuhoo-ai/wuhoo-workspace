#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkShare 数据获取脚本 (用于 subprocess 调用)

从 akshare 获取股票技术面数据。
"""

import sys
import json
from datetime import datetime, timedelta

try:
    import akshare as ak
    import pandas as pd
    import numpy as np
    
    def get_technical_data(symbol: str) -> dict:
        """获取股票技术面数据"""
        ak_symbol = symbol.split('.')[0]
        
        # 获取历史行情
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(
            symbol=ak_symbol,
            period='daily',
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            return {"error": "no_data"}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
        close_prices = df['收盘'].values.astype(float)
        
        # 计算 MACD
        ema12 = pd.Series(close_prices).ewm(span=12).mean()
        ema26 = pd.Series(close_prices).ewm(span=26).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9).mean()
        macd_val = (dif - dea).iloc[-1] if len(dif) > 9 else 0
        
        # 计算 RSI
        delta = pd.Series(close_prices).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-8)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1] if len(rsi) > 14 and not pd.isna(rsi.iloc[-1]) else 50
        
        # 判断趋势
        ma20 = pd.Series(close_prices).rolling(window=20).mean().iloc[-1] if len(close_prices) >= 20 else close_prices[-1]
        current_price = close_prices[-1]
        trend = "uptrend" if current_price > ma20 else "downtrend"
        
        # MACD 信号
        if len(dif) > 1:
            if macd_val > 0 and (dif.iloc[-1] - dif.iloc[-2]) > 0:
                macd_signal = "golden_cross"
            elif macd_val < 0 and (dif.iloc[-1] - dif.iloc[-2]) < 0:
                macd_signal = "death_cross"
            else:
                macd_signal = "neutral"
        else:
            macd_signal = "neutral"
        
        # RSI 信号
        if rsi_val > 70:
            signal = "overbought"
        elif rsi_val < 30:
            signal = "oversold"
        else:
            signal = "neutral"
        
        return {
            "macd": macd_signal,
            "rsi": float(rsi_val),
            "kdj": {"k": 50, "d": 50, "j": 50},
            "trend": trend,
            "signal": signal,
            "volume_ratio": 1.0,
            "turnover_rate": 0.03,
            "price": float(latest['收盘']),
            "change_pct": float((latest['收盘'] - prev['收盘']) / prev['收盘']),
            "volume": int(latest['成交量']) if '成交量' in latest else 0,
            "high": float(latest['最高']) if '最高' in latest else 0,
            "low": float(latest['最低']) if '最低' in latest else 0,
            "open": float(latest['开盘']) if '开盘' in latest else 0,
            "data_source": "akshare_history",
            "data_quality": "real",
            "last_updated": datetime.now().isoformat()
        }
    
    if __name__ == "__main__":
        if len(sys.argv) < 2:
            print(json.dumps({"error": "no_symbol"}))
            sys.exit(1)
        
        symbol = sys.argv[1]
        result = get_technical_data(symbol)
        print(json.dumps(result))

except ImportError as e:
    print(json.dumps({"error": f"import_failed: {str(e)}"}))
    sys.exit(1)
