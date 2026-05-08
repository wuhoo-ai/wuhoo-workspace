#!/usr/bin/env python3.11
"""美股等权调仓执行 — SIMULATE 账户
用法: python3.11 rebalance_us.py

从 portfolio.json 读取调仓方案，通过 Futu API 批量执行。
自动处理：价格精度、频率限制、限价单价格对齐。
"""
import sys, time, json
from pathlib import Path
from futu import *

HOST, PORT = '127.0.0.1', 11111
ACC_ID = 18767293  # US MARGIN SIMULATE
PORTFOLIO_PATH = Path.home() / 'wuhoo-workspace/data/us/portfolio.json'
TRD_ENV = TrdEnv.SIMULATE

def load_orders():
    with open(PORTFOLIO_PATH) as f:
        data = json.load(f)
    return data.get('orders', [])

def get_prices(codes):
    """获取当前价格（round to 2 decimals for US stocks）"""
    q = OpenQuoteContext(host=HOST, port=PORT)
    ret, snap = q.get_market_snapshot(codes)
    q.close()
    if ret != RET_OK:
        raise RuntimeError(f"Snapshot failed: {snap}")
    prices = {}
    for _, row in snap.iterrows():
        prices[row['code']] = {
            'last': round(float(row['last_price']), 2),
            'bid': round(float(row['bid_price']), 2),
            'ask': round(float(row['ask_price']), 2),
        }
    return prices

def execute_orders(orders, prices):
    trd_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host=HOST, port=PORT)
    
    sell_orders = []
    buy_orders = []
    for o in orders:
        code = o['ts_code'].replace('.US', '')  # BAC.US → US.BAC
        code = f'US.{code}'
        if code not in prices:
            print(f"  SKIP {code}: no price")
            continue
        if o['action'] == 'SELL':
            sell_orders.append((code, o))
        else:
            buy_orders.append((code, o))
    
    # SELL first (free up cash), then BUY
    all_placed = []
    failures = []
    
    for code, o in sell_orders + buy_orders:
        side = TrdSide.SELL if o['action'] == 'SELL' else TrdSide.BUY
        price_info = prices[code]
        
        # 限价对齐：卖单用 bid，买单用 ask
        if side == TrdSide.SELL:
            price = price_info['bid']
        else:
            price = price_info['ask']
        
        qty = max(1, int(o.get('target_amount', 0) / price)) if o['target_weight'] > 0 else 0
        if qty == 0:
            continue
        
        ret, data = trd_ctx.place_order(
            price=price, qty=qty, code=code,
            trd_side=side, order_type=OrderType.NORMAL,
            trd_env=TRD_ENV, acc_id=ACC_ID
        )
        if ret == RET_OK:
            all_placed.append((code, o['action'], qty, price, data['order_id'].iloc[0]))
            print(f"  {'✅' if side==TrdSide.BUY else '🔴'} {o['action']} {code} {qty} @ ${price:.2f}")
        else:
            failures.append((code, str(data)))
            print(f"  ❌ {code}: {data}")
        
        time.sleep(1.5)  # 频率限制：15次/30秒
    
    trd_ctx.close()
    return all_placed, failures

def check_pending(trd_ctx):
    """检查未成交订单，必要时撤单重下"""
    ret, data = trd_ctx.order_list_query(
        trd_env=TRD_ENV, acc_id=ACC_ID, refresh_cache=True
    )
    if ret != RET_OK:
        return []
    pending = data[data['order_status'] != 'FILLED_ALL']
    return list(pending['order_id'])

def main():
    orders = load_orders()
    if not orders:
        print("No orders to execute")
        return
    
    buys = sum(1 for o in orders if o['action'] == 'BUY')
    sells = sum(1 for o in orders if o['action'] == 'SELL')
    print(f"Orders: {buys} BUY + {sells} SELL = {len(orders)} total")
    
    codes = list(set(
        f"US.{o['ts_code'].replace('.US', '')}" for o in orders
    ))
    prices = get_prices(codes)
    print(f"Got prices for {len(prices)} stocks\n")
    
    placed, failures = execute_orders(orders, prices)
    print(f"\nPlaced: {len(placed)}, Failed: {len(failures)}")
    
    if failures:
        print("Retrying failures in 35s...")
        time.sleep(35)
        # Re-get prices and retry

if __name__ == '__main__':
    main()
