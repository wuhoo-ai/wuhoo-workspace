#!/usr/bin/env python3.11
"""调试 Futu K-line 数据获取"""
import os
import sys

# 加载环境变量
env_file = os.path.expanduser('~/.openclaw/.env')
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

from futu import OpenQuoteContext, KLType, AuType

symbol = "HK.00700"  # 腾讯

print(f"连接 OpenD: 127.0.0.1:11111")
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

print(f"\n1. 测试 get_stock_quote('{symbol}'):")
ret, data = quote_ctx.get_stock_quote([symbol])
print(f"   ret={ret}, type(data)={type(data)}")
if ret == 0 and data is not None:
    print(f"   列名: {list(data.columns)}")
    print(f"   数据:\n{data}")
else:
    print(f"   data={data}")

print(f"\n2. 测试 get_cur_kline('{symbol}', 120, K_DAY, QFQ):")
ret, data, page_key = quote_ctx.get_cur_kline(symbol, 120, KLType.K_DAY, AuType.QFQ)
print(f"   ret={ret}, page_req_key={page_key}")
print(f"   type(data)={type(data)}")
if data is not None:
    print(f"   行数: {len(data)}")
    print(f"   列名: {list(data.columns)}")
    if len(data) > 0:
        print(f"   最近 5 条 K 线:")
        print(data.tail(5).to_string())
    else:
        print("   数据为空")
else:
    print("   data 为 None")

quote_ctx.close()
print("\n连接已关闭")
