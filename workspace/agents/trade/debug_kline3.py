#!/usr/bin/env python3.11
"""调试 K-line 返回值"""
import os

env_file = os.path.expanduser('~/.openclaw/.env')
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

from futu import OpenQuoteContext, KLType, AuType, SubType

symbol = "HK.00700"
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

# 先订阅 K 线数据
print(f"1. 订阅 {symbol} K_Day 数据...")
ret, data = quote_ctx.subscribe(symbol, [SubType.K_DAY])
print(f"   subscribe ret={ret}, data={data}")

# 获取 K-line
print(f"\n2. 获取 cur_kline:")
result = quote_ctx.get_cur_kline(symbol, 120, KLType.K_DAY, AuType.QFQ)
print(f"   result type: {type(result)}, len: {len(result)}")
ret_val = result[0]
data_val = result[1]
print(f"   ret={ret_val}")
print(f"   data type: {type(data_val)}")
print(f"   data: {data_val}")

# 如果 ret=0 且是 DataFrame
if ret_val == 0 and hasattr(data_val, 'columns'):
    print(f"   行数: {len(data_val)}")
    print(f"   列名: {list(data_val.columns)}")
    if len(data_val) > 0:
        print(f"   最近 3 条:")
        print(data_val.tail(3).to_string())

quote_ctx.close()
print("\n完成")
