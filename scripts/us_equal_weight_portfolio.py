#!/usr/bin/env python3
"""
美股等权持仓策略管理

策略说明:
- 持仓范围: stock_pick.py 选股脚本当天选出的结果
- 权重分配: 每只股票等权重 (1/N)
- 再平衡: 每次选股结果更新后自动再平衡
- 调仓规则: 对比当前持仓与最新选股结果，生成调仓订单

数据源:
- 选股结果: ~/.hermes/data/stock-pick/factors/result_us_YYYYMMDD.csv
- 持仓记录: ~/wuhoo-workspace/data/us/portfolio.json

用法:
  python3.11 scripts/us_equal_weight_portfolio.py show      # 查看当前持仓
  python3.11 scripts/us_equal_weight_portfolio.py rebalance # 执行再平衡
  python3.11 scripts/us_equal_weight_portfolio.py check     # 检查是否需要再平衡
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import glob

import pandas as pd
import numpy as np

# 配置路径
DATA_DIR = Path.home() / 'wuhoo-workspace' / 'data' / 'us'
PORTFOLIO_FILE = DATA_DIR / 'portfolio.json'
FACTORS_DIR = Path.home() / '.hermes' / 'data' / 'stock-pick' / 'factors'

# 策略参数
CASH_RATIO = 0.02  # 2% 现金储备
REBALANCE_THRESHOLD = 0.05  # 5% 偏离阈值


def get_latest_stock_pick_result():
    """获取最新的选股结果"""
    # 查找 result_us_*.csv 文件
    pattern = str(FACTORS_DIR / "result_us_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        print("❌ 未找到选股结果文件")
        return None
    
    # 按文件名排序 (日期最新的)
    latest_file = sorted(files)[-1]
    
    # 解析日期
    filename = Path(latest_file).stem
    date_str = filename.replace("result_us_", "")
    
    df = pd.read_csv(latest_file)
    print(f"📊 加载选股结果: {latest_file}")
    print(f"   日期: {date_str}, 股票数: {len(df)}")
    
    return df


def load_portfolio():
    """加载当前持仓"""
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return None


def save_portfolio(portfolio):
    """保存持仓"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)
    print(f"✅ 持仓已保存: {PORTFOLIO_FILE}")


def show_portfolio():
    """展示当前持仓"""
    portfolio = load_portfolio()
    
    if not portfolio:
        print("📝 当前无持仓记录")
        return
    
    print("\n" + "=" * 80)
    print(f"=== 美股等权持仓 ===")
    print(f"创建日期: {portfolio.get('created_date', 'N/A')}")
    print(f"最后更新: {portfolio.get('last_updated', 'N/A')}")
    print(f"股票数量: {len(portfolio.get('positions', []))}")
    print("=" * 80)
    
    if 'positions' in portfolio:
        print(f"\n{'代码':<12} {'名称':<30} {'权重':<8} {'状态':<10}")
        print("-" * 80)
        for pos in portfolio['positions']:
            print(f"{pos['ts_code']:<12} {pos.get('name', 'N/A'):<30} {pos['weight']:.2%} {pos.get('status', 'active'):<10}")
    
    print("\n")


def rebalance():
    """执行再平衡 - 基于最新选股结果"""
    # 获取最新选股结果
    stock_pick_result = get_latest_stock_pick_result()
    
    if stock_pick_result is None or stock_pick_result.empty:
        print("❌ 无选股结果，无法再平衡")
        return
    
    # 加载当前持仓
    old_portfolio = load_portfolio()
    old_positions = {}
    if old_portfolio and 'positions' in old_portfolio:
        for pos in old_portfolio['positions']:
            old_positions[pos['ts_code']] = pos
    
    # 计算等权权重
    n_stocks = len(stock_pick_result)
    target_weight = (1 - CASH_RATIO) / n_stocks
    
    # 生成新持仓
    new_positions = []
    for _, row in stock_pick_result.iterrows():
        new_positions.append({
            'ts_code': row['ts_code'],
            'name': row.get('name', 'N/A'),
            'weight': target_weight,
            'status': 'active',
            'factors': {
                'residual_vol': float(row.get('residual_vol', 0)),
                'momentum_5d': float(row.get('momentum_5d', 0)),
                'momentum_10d': float(row.get('momentum_10d', 0)),
                'beta_20d': float(row.get('beta_20d', 0))
            }
        })
    
    # 生成调仓订单
    orders = []
    new_stock_codes = set(row['ts_code'] for _, row in stock_pick_result.iterrows())
    old_stock_codes = set(old_positions.keys())
    
    # 需要买入的 (新选中的股票)
    for code in new_stock_codes:
        if code not in old_stock_codes:
            stock_info = stock_pick_result[stock_pick_result['ts_code'] == code].iloc[0]
            orders.append({
                'action': 'BUY',
                'ts_code': code,
                'name': stock_info.get('name', 'N/A'),
                'target_weight': target_weight,
                'reason': '新入选'
            })
    
    # 需要卖出的 (不再选中的股票)
    for code in old_stock_codes:
        if code not in new_stock_codes:
            orders.append({
                'action': 'SELL',
                'ts_code': code,
                'name': old_positions[code].get('name', 'N/A'),
                'target_weight': 0,
                'reason': '未入选'
            })
    
    # 权重调整的 (已持仓但权重变化)
    for pos in new_positions:
        if pos['ts_code'] in old_positions:
            old_weight = old_positions[pos['ts_code']]['weight']
            if abs(pos['weight'] - old_weight) > 0.01:  # 1% 以上变化
                orders.append({
                    'action': 'ADJUST',
                    'ts_code': pos['ts_code'],
                    'name': pos['name'],
                    'old_weight': old_weight,
                    'new_weight': pos['weight'],
                    'reason': f'权重调整 {old_weight:.2%} → {pos["weight"]:.2%}'
                })
    
    # 保存新持仓
    today = datetime.now().strftime('%Y-%m-%d')
    portfolio = {
        'created_date': old_portfolio.get('created_date', today) if old_portfolio else today,
        'last_updated': today,
        'source_file': str(FACTORS_DIR / f"result_us_{today.replace('-', '')}.csv"),
        'n_stocks': n_stocks,
        'target_weight': target_weight,
        'cash_ratio': CASH_RATIO,
        'positions': new_positions,
        'orders': orders
    }
    
    save_portfolio(portfolio)
    
    # 打印调仓订单
    print("\n" + "=" * 80)
    print(f"=== 调仓订单 ===")
    print(f"买入: {sum(1 for o in orders if o['action'] == 'BUY')} 笔")
    print(f"卖出: {sum(1 for o in orders if o['action'] == 'SELL')} 笔")
    print(f"调整: {sum(1 for o in orders if o['action'] == 'ADJUST')} 笔")
    print("=" * 80)
    
    if orders:
        print(f"\n{'操作':<8} {'代码':<12} {'名称':<25} {'详情':<40}")
        print("-" * 80)
        for order in orders:
            if order['action'] == 'BUY':
                detail = f"买入 {order['target_weight']:.2%}"
            elif order['action'] == 'SELL':
                detail = "清仓"
            else:
                detail = order.get('reason', '')
            print(f"{order['action']:<8} {order['ts_code']:<12} {order.get('name', 'N/A'):<25} {detail:<40}")
    
    print("\n")
    return portfolio


def check():
    """检查是否需要再平衡"""
    stock_pick_result = get_latest_stock_pick_result()
    
    if stock_pick_result is None:
        print("❌ 无选股结果")
        return False
    
    portfolio = load_portfolio()
    
    if not portfolio:
        print("📝 无持仓，需要建仓")
        return True
    
    # 检查选股日期是否更新
    last_updated = portfolio.get('last_updated', '')
    pick_date = str(stock_pick_result.iloc[0].get('date', ''))
    
    # 检查股票池是否变化
    current_codes = set(pos['ts_code'] for pos in portfolio.get('positions', []))
    new_codes = set(stock_pick_result['ts_code'])
    
    changed = current_codes != new_codes
    
    if changed:
        added = new_codes - current_codes
        removed = current_codes - new_codes
        print(f"⚠️  股票池变化: +{len(added)} / -{len(removed)}")
        if added:
            print(f"   新增: {', '.join(list(added)[:5])}{'...' if len(added) > 5 else ''}")
        if removed:
            print(f"   移除: {', '.join(list(removed)[:5])}{'...' if len(removed) > 5 else ''}")
        return True
    else:
        print("✅ 股票池未变化，无需再平衡")
        return False


def main():
    parser = argparse.ArgumentParser(description='美股等权持仓策略管理')
    parser.add_argument('action', choices=['show', 'rebalance', 'check'],
                        help='操作类型')
    
    args = parser.parse_args()
    
    if args.action == 'show':
        show_portfolio()
    elif args.action == 'rebalance':
        rebalance()
    elif args.action == 'check':
        needs_rebalance = check()
        sys.exit(0 if needs_rebalance else 1)


if __name__ == '__main__':
    main()
