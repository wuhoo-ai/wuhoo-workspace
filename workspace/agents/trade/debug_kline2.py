#!/usr/bin/env python3.11
"""调试 Futu K-line — 修复订阅和 API 返回值"""
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

# 先订阅 Basic 数据
print(f"1. 订阅 {symbol} Basic 数据...")
ret, data = quote_ctx.subscribe(symbol, [SubType.QUOTE])
print(f"   subscribe ret={ret}, data={data}")

# 再获取实时报价
print(f"\n2. 获取 stock_quote:")
ret, data = quote_ctx.get_stock_quote([symbol])
print(f"   ret={ret}")
if ret == 0 and data is not None:
    print(f"   列名: {list(data.columns)}")
    print(data.to_string())
else:
    print(f"   data={data}")

# 获取 K-line
print(f"\n3. 获取 cur_kline (120 根日 K):")
result = quote_ctx.get_cur_kline(symbol, 120, KLType.K_DAY, AuType.QFQ)
print(f"   返回值数量: {len(result)}")
print(f"   返回值类型: {[type(x) for x in result]}")

if len(result) == 2:
    ret, data = result
    page_key = None
elif len(result) == 3:
    ret, data, page_key = result

print(f"   ret={ret}, page_key={page_key}")
if data is not None:
    print(f"   行数: {len(data)}")
    print(f"   列名: {list(data.columns)}")
    if len(data) > 0:
        print(f"   最近 5 条:")
        print(data.tail(5).to_string())

quote_ctx.close()
print("\n完成")
