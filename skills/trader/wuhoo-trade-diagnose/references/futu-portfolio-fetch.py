#!/usr/bin/env python3.11
"""
可复用的 Futu OpenD 美股持仓获取脚本模板。
用法: python3.11 futu-portfolio-fetch.py [--acc-id 18767293]

已知限制:
- US 模拟账户 (18767293) 的 accinfo_query 返回全零
- Futu API 返回的字段可能为 'N/A' 字符串，必须用 safe_float 处理
- 持仓获取用 OpenSecTradeContext.position_list_query（非 OpenQuoteContext）
"""
from futu import *
import json, sys

def safe_float(val, default=0.0):
    """Convert Futu value to float, handling N/A strings and None."""
    if val is None:
        return default
    if isinstance(val, str) and val.strip().upper() == 'N/A':
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# Config
ACC_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 18767293
TRD_MARKET = TrdMarket.US
TRD_ENV = TrdEnv.SIMULATE

# Step 1: Get positions (uses OpenSecTradeContext)
trd_ctx = OpenSecTradeContext(
    filter_trdmarket=TRD_MARKET,
    host='127.0.0.1', port=11111,
    security_firm=SecurityFirm.FUTUSECURITIES
)

ret, data = trd_ctx.position_list_query(
    trd_env=TRD_ENV, acc_id=ACC_ID, refresh_cache=True
)

if ret != RET_OK:
    print(json.dumps({"error": str(data)}))
    trd_ctx.close()
    sys.exit(1)

positions = []
for _, row in data.iterrows():
    positions.append({
        'code': row['code'],
        'name': row.get('stock_name', ''),
        'qty': int(row['qty']),
        'cost_price': safe_float(row.get('cost_price')),
        'current_price': safe_float(row.get('nominal_price')),
        'market_val': safe_float(row.get('market_val')),
        'pl_ratio': safe_float(row.get('pl_ratio')),
        'pl_val': safe_float(row.get('pl_val')),
        'unrealized_pl': safe_float(row.get('unrealized_pl')),
        'today_pl_val': safe_float(row.get('today_pl_val')),
    })

total_mv = sum(p['market_val'] for p in positions)

# Step 2: Get account info (⚠️ returns zero for US SIMULATE 18767293)
ret2, acc_data = trd_ctx.accinfo_query(
    trd_env=TRD_ENV, acc_id=ACC_ID, refresh_cache=True
)
account_info = {}
if ret2 == RET_OK:
    account_info = {
        'total_assets': safe_float(acc_data.get('total_assets')),
        'cash': safe_float(acc_data.get('cash')),
        'market_val': safe_float(acc_data.get('market_val')),
        'power': safe_float(acc_data.get('power')),
    }

result = {
    'account_info': account_info,
    'positions': sorted(positions, key=lambda x: x['market_val'], reverse=True),
    'total_positions': len(positions),
    'total_market_val': total_mv,
}

print(json.dumps(result, indent=2, ensure_ascii=False))
trd_ctx.close()
