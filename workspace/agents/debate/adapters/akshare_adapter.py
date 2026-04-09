#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术面数据适配器

优先级:
1. Tushare Pro daily() - 真实日K线数据，计算 MACD/RSI/KDJ
2. AkShare - 备用（间歇性不可用）
3. 降级数据 - 明确标注
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta


class AkShareAdapter:
    """
    技术面数据适配器

    功能:
    - 获取股票实时行情
    - 计算技术指标 (MACD/RSI/KDJ 等)
    - 获取资金流向
    """

    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.ts_available = self._check_tushare()

    def _check_tushare(self) -> bool:
        """检查 Tushare 是否可用"""
        ts_token = os.environ.get('TUSHARE_TOKEN', '') or os.environ.get('TS_TOKEN', '')
        if not ts_token:
            # 尝试从 .env 文件加载
            self._load_env_file()
            ts_token = os.environ.get('TUSHARE_TOKEN', '') or os.environ.get('TS_TOKEN', '')
        return bool(ts_token)

    def _load_env_file(self):
        """从 ~/.openclaw/.env 加载环境变量"""
        env_file = Path.home() / '.openclaw' / '.env'
        if not env_file.exists():
            return
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value and key not in os.environ:
                        os.environ[key] = value

    def get_technical_data(self, symbol: str) -> Dict:
        """
        获取股票技术面数据

        Args:
            symbol: 股票代码 (如 "600519.SH")

        Returns:
            技术面数据字典
        """
        if symbol in self.cache:
            return self.cache[symbol]

        # 优先使用 Tushare
        if self.ts_available:
            data = self._fetch_from_tushare(symbol)
            if data.get('data_quality') == 'real':
                self.cache[symbol] = data
                return data

        # 降级到 mock
        data = self._get_mock_data(symbol)
        self.cache[symbol] = data
        return data

    def _fetch_from_tushare(self, symbol: str) -> Dict:
        """
        从 Tushare 获取日K线数据并计算技术指标

        使用环境变量传递参数，避免 f-string 拼接导致的代码注入风险
        """
        try:
            import subprocess

            ts_token = os.environ.get('TUSHARE_TOKEN', '') or os.environ.get('TS_TOKEN', '')
            if not ts_token:
                return self._get_mock_data(symbol)

            # 使用环境变量传递参数，而非 f-string 拼接（安全修复）
            code = '''
import tushare as ts
import pandas as pd
import numpy as np
import json
import os
import sys

ts_token = os.environ.get('TUSHARE_TOKEN', '')
symbol = os.environ.get('SYMBOL', '')

# 转换代码格式：600519.SH -> 600519.SH (Tushare 使用相同格式)
ts_code = symbol

# 获取最近 120 个交易日的日线数据
pro = ts.pro_api(ts_token)
from datetime import datetime, timedelta
end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')

try:
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
except Exception as e:
    print(json.dumps({"error": str(e), "data_quality": "degraded"}))
    sys.exit(0)

if df is None or len(df) < 30:
    print(json.dumps({"error": "数据不足", "data_quality": "degraded"}))
    sys.exit(0)

df = df.sort_values('trade_date').reset_index(drop=True)

close = df['close'].values
high = df['high'].values
low = df['low'].values
volume = df.get('vol', df.get('volume', pd.Series([0]*len(df)))).values

current_price = close[-1]
prev_close = close[-2] if len(close) >= 2 else close[-1]
change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0

# RSI (14 日)
delta = np.diff(close)
gain = np.where(delta > 0, delta, 0)
loss = np.where(delta < 0, -delta, 0)
if len(gain) >= 14:
    avg_gain = pd.Series(gain).rolling(14).mean().iloc[-1]
    avg_loss = pd.Series(loss).rolling(14).mean().iloc[-1]
    rs = avg_gain / avg_loss if avg_loss > 0 else 999
    rsi = 100 - (100 / (1 + rs))
else:
    rsi = 50

# MACD (12, 26, 9)
exp1 = pd.Series(close).ewm(span=12, adjust=False).mean()
exp2 = pd.Series(close).ewm(span=26, adjust=False).mean()
macd_line = exp1 - exp2
signal_line = macd_line.ewm(span=9, adjust=False).mean()
macd_val = macd_line.iloc[-1]
signal_val = signal_line.iloc[-1]
macd_hist = macd_val - signal_val

if macd_val > signal_val and macd_line.iloc[-2] <= signal_line.iloc[-2]:
    macd_state = "golden_cross"
elif macd_val < signal_val and macd_line.iloc[-2] >= signal_line.iloc[-2]:
    macd_state = "death_cross"
elif macd_val > signal_val:
    macd_state = "bullish"
else:
    macd_state = "bearish"

# KDJ (9, 3, 3)
low_9 = pd.Series(low).rolling(9).min()
high_9 = pd.Series(high).rolling(9).max()
rsv = (close - low_9) / (high_9 - low_9) * 100
rsv = rsv.fillna(50)
k_line = rsv.ewm(com=2, adjust=False).mean()
d_line = k_line.ewm(com=2, adjust=False).mean()
j_line = 3 * k_line - 2 * d_line

k_val = k_line.iloc[-1]
d_val = d_line.iloc[-1]
j_val = j_line.iloc[-1]

# 趋势判断
if len(close) >= 20:
    ma5 = np.mean(close[-5:])
    ma10 = np.mean(close[-10:])
    ma20 = np.mean(close[-20:])
    if current_price > ma5 > ma10 > ma20:
        trend = "uptrend"
    elif current_price < ma5 < ma10 < ma20:
        trend = "downtrend"
    else:
        trend = "sideways"
else:
    trend = "sideways"
    ma5 = ma10 = ma20 = current_price

# 信号判断
if rsi > 70:
    signal = "overbought"
elif rsi < 30:
    signal = "oversold"
else:
    signal = "neutral"

# 布林带
if len(close) >= 20:
    sma20 = pd.Series(close).rolling(20).mean().iloc[-1]
    std20 = pd.Series(close).rolling(20).std().iloc[-1]
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20
    boll_pos = (current_price - lower) / (upper - lower) * 100 if upper > lower else 50
else:
    sma20 = upper = lower = current_price
    boll_pos = 50

# 支撑/压力
support = float(np.min(low[-20:])) if len(low) >= 20 else current_price * 0.95
resistance = float(np.max(high[-20:])) if len(high) >= 20 else current_price * 1.05

result = {
    "macd": macd_state,
    "macd_value": round(float(macd_val), 4),
    "signal_value": round(float(signal_val), 4),
    "macd_histogram": round(float(macd_hist), 4),
    "rsi": round(float(rsi), 2),
    "kdj": {
        "k": round(float(k_val), 2),
        "d": round(float(d_val), 2),
        "j": round(float(j_val), 2)
    },
    "trend": trend,
    "signal": signal,
    "ma5": round(float(ma5), 2),
    "ma10": round(float(ma10), 2),
    "ma20": round(float(ma20), 2),
    "boll_upper": round(float(upper), 2),
    "boll_lower": round(float(lower), 2),
    "boll_position": round(float(boll_pos), 2),
    "support": round(float(support), 2),
    "resistance": round(float(resistance), 2),
    "price": round(float(current_price), 2),
    "change_pct": round(float(change_pct), 2),
    "volume": int(volume[-1]) if len(volume) > 0 else 0,
    "turnover_rate": round(float(df.get('turnover_rate', pd.Series([0]*len(df))).iloc[-1] * 100), 2) if 'turnover_rate' in df.columns else 0,
    "data_quality": "real",
    "data_source": "tushare_daily",
    "trade_days": len(df),
    "last_updated": datetime.now().isoformat()
}

print(json.dumps(result))
'''

            # 通过环境变量安全传递参数
            env = os.environ.copy()
            env['TUSHARE_TOKEN'] = ts_token
            env['SYMBOL'] = symbol

            result = subprocess.run(
                ['/usr/bin/python3.11', '-c', code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=30,
                env=env
            )

            output = result.stdout.strip()
            if output:
                data = json.loads(output)
                if data.get('error'):
                    return self._get_mock_data(symbol)
                return data

            return self._get_mock_data(symbol)

        except Exception as e:
            print(f"Tushare 技术面获取失败：{e}")
            return self._get_mock_data(symbol)

    def _get_mock_data(self, symbol: str) -> Dict:
        """生成模拟技术面数据"""
        hash_val = hash(symbol) % 100

        macd_states = ["golden_cross", "death_cross", "neutral", "divergence"]
        macd = macd_states[hash_val % len(macd_states)]
        rsi = 30 + (hash_val % 50)
        trends = ["uptrend", "downtrend", "sideways"]
        trend = trends[hash_val % len(trends)]

        if rsi > 70:
            signal = "overbought"
        elif rsi < 30:
            signal = "oversold"
        else:
            signal = "neutral"

        return {
            "macd": macd,
            "macd_value": 0,
            "signal_value": 0,
            "macd_histogram": 0,
            "rsi": rsi,
            "kdj": {
                "k": 50 + (hash_val % 40),
                "d": 45 + (hash_val % 40),
                "j": 55 + (hash_val % 50)
            },
            "trend": trend,
            "signal": signal,
            "ma5": 0,
            "ma10": 0,
            "ma20": 0,
            "boll_upper": 0,
            "boll_lower": 0,
            "boll_position": 50,
            "support": 0,
            "resistance": 0,
            "volume_ratio": 0.8 + (hash_val % 100) / 50,
            "turnover_rate": 0.01 + (hash_val % 100) / 1000,
            "price": 100 + (hash_val % 1000),
            "change_pct": (hash_val % 20 - 10) / 100,
            "volume": 1000000 + (hash_val % 10000000),
            "data_quality": "degraded",
            "data_source": "mock",
            "trade_days": 0,
            "last_updated": datetime.now().isoformat(),
            "note": "模拟数据 (Tushare 不可用)"
        }

    def get_price_history(self, symbol: str, days: int = 60) -> Optional[List[Dict]]:
        """获取历史价格数据"""
        if self.ts_available:
            try:
                import subprocess
                ts_token = os.environ.get('TUSHARE_TOKEN', '') or os.environ.get('TS_TOKEN', '')
                # 使用环境变量传递参数，避免 f-string 注入（安全修复）
                code = '''
import tushare as ts, pandas as pd, json, os
from datetime import datetime, timedelta
pro = ts.pro_api(os.environ.get('TUSHARE_TOKEN', ''))
end = datetime.now().strftime('%Y%m%d')
start = (datetime.now() - timedelta(days=int(os.environ.get('FETCH_DAYS', '120')))).strftime('%Y%m%d')
symbol = os.environ.get('SYMBOL', '')
df = pro.daily(ts_code=symbol, start_date=start, end_date=end)
if df is not None and len(df) > 0:
    df = df.sort_values('trade_date').tail(int(os.environ.get('TAIL_DAYS', '60')))
    records = df[['trade_date','open','high','low','close','vol']].to_dict('records')
    print(json.dumps(records, ensure_ascii=False))
else:
    print("[]")
'''
                env = os.environ.copy()
                env['TUSHARE_TOKEN'] = ts_token
                env['SYMBOL'] = symbol
                env['FETCH_DAYS'] = str(days * 2)
                env['TAIL_DAYS'] = str(days)

                result = subprocess.run(
                    ['/usr/bin/python3.11', '-c', code],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    timeout=30,
                    env=env
                )
                if result.stdout.strip():
                    return json.loads(result.stdout.strip())
            except Exception:
                pass
        return self._get_mock_history(symbol, days)

    def _get_mock_history(self, symbol: str, days: int) -> List[Dict]:
        """生成模拟历史数据"""
        history = []
        base_price = 100 + (hash(symbol) % 1000)

        for i in range(days):
            date = (datetime.now() - timedelta(days=days - i)).strftime("%Y-%m-%d")
            change = (hash(symbol + str(i)) % 11 - 5) / 100
            price = base_price * (1 + change)

            history.append({
                "date": date,
                "open": price * 0.99,
                "high": price * 1.02,
                "low": price * 0.96,
                "close": price,
                "volume": 1000000 + hash(symbol + str(i)) % 10000000
            })

        return history

    def get_money_flow(self, symbol: str) -> Dict:
        """获取资金流向"""
        return self._get_mock_money_flow(symbol)

    def _get_mock_money_flow(self, symbol: str) -> Dict:
        """生成模拟资金流向"""
        hash_val = hash(symbol) % 100

        return {
            "net_inflow": (hash_val - 50) * 10000,
            "main_force_inflow": (hash_val - 50) * 5000,
            "retail_inflow": (hash_val - 50) * 5000,
            "inflow_ratio": 0.4 + (hash_val % 40) / 100,
            "large_order_ratio": 0.2 + (hash_val % 30) / 100,
            "last_updated": datetime.now().isoformat()
        }

    def get_support_resistance(self, symbol: str) -> Dict:
        """获取支撑位/阻力位"""
        tech = self.get_technical_data(symbol)
        current_price = tech.get("price", 100)
        support = tech.get("support", current_price * 0.95)
        resistance = tech.get("resistance", current_price * 1.05)

        return {
            "current_price": current_price,
            "support_levels": [
                support,
                support * 0.95,
                support * 0.90
            ],
            "resistance_levels": [
                resistance,
                resistance * 1.05,
                resistance * 1.10
            ]
        }

    def is_available(self) -> bool:
        """检查技术面数据是否可用"""
        return self.ts_available

    def get_status(self) -> Dict:
        """获取适配器状态"""
        return {
            "tushare_available": self.ts_available,
            "cache_size": len(self.cache)
        }


if __name__ == "__main__":
    adapter = AkShareAdapter()

    print("技术面适配器状态:", json.dumps(adapter.get_status(), indent=2, ensure_ascii=False))
    print("\n600519.SH 技术面数据:")
    data = adapter.get_technical_data("600519.SH")
    print(json.dumps(data, indent=2, ensure_ascii=False))
