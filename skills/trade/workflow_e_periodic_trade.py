#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow E — 周期平权调仓

策略：选股后按总价平权买入 Top 10，下次选股时卖出旧持仓，产出 P&L 报告。

逻辑:
1. 读取最新选股结果 CSV（result_cn_*.csv）获取 Top 10
2. 查询 OpenD 当前总资产 → 计算每只目标金额 = 总资产 × 9%
3. 卖出不在新选股列表中的持仓
4. 买入选股列表中的股票（市价单）
5. 输出操作日志 JSON

用法:
    python workflow_e_periodic_trade.py --dry-run          # 仅输出计划，不下单
    python workflow_e_periodic_trade.py --trd-env SIMULATE # 模拟盘执行
    python workflow_e_periodic_trade.py --trd-env REAL     # 实盘执行（需确认）
    python workflow_e_periodic_trade.py --pick-date 20260419
"""

import os
import sys
import json
import csv
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================
# 路径配置
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from path_config import (
        TRADE_DIR, FUTU_API_SCRIPTS, PICK_RESULT_DIR,
        DAILY_DATA_DIR, ENV_FILE, ACCOUNT_IDS
    )
except ImportError:
    from pathlib import Path
    HOME = Path.home()
    TRADE_DIR = HOME / 'wuhoo-agents' / 'trade'
    FUTU_API_SCRIPTS = HOME / 'wuhoo-skills' / 'futu-api' / 'scripts'
    PICK_RESULT_DIR = HOME / '.hermes' / 'data' / 'stock-pick' / 'factors'
    DAILY_DATA_DIR = HOME / '.hermes' / 'data' / 'stock-pick' / 'daily_data'
    ENV_FILE = HOME / '.hermes' / '.env'
    ACCOUNT_IDS = {'CN': 18767295, 'HK': 18767294, 'US': 18767299}

# ============================================================
# 环境变量加载
# ============================================================
if ENV_FILE.exists():
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value

# ============================================================
# 下单频率限制
# ============================================================
ORDER_RATE_LIMIT = 14  # 每 30 秒最多 15 次，留 1 笔余量

_order_counter = 0

def _rate_limited_place_order(**kwargs):
    """节流下单，避免触发 OpenD 频率限制"""
    global _order_counter
    if _order_counter > 0 and _order_counter % ORDER_RATE_LIMIT == 0:
        print(f"    [限频] 已提交 {_order_counter} 笔，等待 3 秒...")
        time.sleep(3)
    _order_counter += 1
    return place_order(**kwargs)

# ============================================================
# 市场代码转换
# ============================================================
def code_to_futu(code: str, market: str) -> str:
    """将选股结果代码转为 Futu 格式"""
    code = code.strip()
    # 已经是 Futu 格式
    if '.' in code:
        # ts_code 格式: 002354.SZ -> SZ.002354
        if code.split('.')[1] in ('SH', 'SZ'):
            parts = code.split('.')
            return f"{parts[1]}.{parts[0]}"
        return code  # 已经是 Futu 格式
    # 裸代码
    if market == 'HK':
        if code.startswith('0'):
            return f"HK.{code}"
        return f"HK.{code.zfill(5)}"
    elif market == 'US':
        return f"US.{code}"
    else:  # A 股 — 裸代码无法转换
        return code


def futu_to_code(futu_code: str) -> str:
    """将 Futu 代码转为裸代码"""
    if '.' in futu_code:
        return futu_code.split('.', 1)[1]
    return futu_code


# ============================================================
# 选股结果读取
# ============================================================
def load_pick_result(pick_date: Optional[str] = None, market: str = 'CN') -> Tuple[List[Dict], str]:
    """
    读取最新选股结果 CSV，支持多市场

    Args:
        pick_date: 选股日期 YYYYMMDD，None 则取最新
        market: CN / HK / US

    Returns:
        (top10_list, source_file_path)
    """
    if not PICK_RESULT_DIR.exists():
        print(f"[Workflow E] 选股结果目录不存在: {PICK_RESULT_DIR}")
        return [], ""

    # 支持多市场: result_cn_*, result_hk_*, result_us_*
    market_prefix = market.lower()
    pattern = f"result_{market_prefix}_{pick_date}.csv" if pick_date else f"result_{market_prefix}_*.csv"
    csv_files = list(PICK_RESULT_DIR.glob(pattern))

    if not csv_files:
        # 如果指定日期没找到，尝试找最新的该市场文件
        if pick_date:
            print(f"[Workflow E] 未找到指定日期的结果，使用最新文件")
        csv_files = sorted(PICK_RESULT_DIR.glob(f"result_{market_prefix}_*.csv"))

    if not csv_files:
        print(f"[Workflow E] 未找到 {market} 市场选股结果文件 (pattern: {pattern})")
        return [], ""

    latest_csv = csv_files[-1]  # 取最新
    print(f"[Workflow E] 读取选股结果: {latest_csv.name}")

    top10 = []
    with open(latest_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 10:
                break
            code = row.get('ts_code', row.get('代码', row.get('code', ''))).strip()
            name = row.get('name', row.get('名称', ''))
            # 排序依据：momentum_10d（越低越好）
            score = float(row.get('momentum_10d', row.get('总分', row.get('score', 0))))
            # 推断市场
            if code.startswith('US.'):
                market = 'US'
            elif code.startswith('HK.'):
                market = 'HK'
            else:
                market = 'CN'
            top10.append({
                'code': code,
                'name': name,
                'score': score,
                'market': market,
                'futu_code': code_to_futu(code, market),
            })

    print(f"[Workflow E] 选股 Top 10:")
    for s in top10:
        print(f"  {s['futu_code']} {s['name']} (score={s['score']:.2f})")

    return top10, str(latest_csv)


# ============================================================
# OpenD 持仓查询
# ============================================================
def get_opend_portfolio(market: str = 'CN', account_id: Optional[int] = None) -> Dict:
    """通过 futu-api get_portfolio.py 查询 OpenD 持仓和资金"""
    acc_id = account_id or ACCOUNT_IDS.get(market, 18767295)

    script = FUTU_API_SCRIPTS / 'trade' / 'get_portfolio.py'
    cmd = [
        sys.executable, str(script),
        '--market', market,
        '--acc-id', str(acc_id),
        '--json',
    ]

    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode == 0 and result.stdout.strip():
        stdout = result.stdout.strip()
        start = stdout.find('{')
        if start >= 0:
            depth = 0
            end = -1
            for i in range(start, len(stdout)):
                if stdout[i] == '{':
                    depth += 1
                elif stdout[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > start:
                return json.loads(stdout[start:end])

    return {'error': result.stderr.strip() or result.stdout.strip() or 'no output', 'positions': [], 'funds': {}}


def _get_lot_sizes(codes: List[str]) -> Dict[str, int]:
    """获取港股每手股数"""
    lot_sizes = {}
    try:
        from futu import OpenQuoteContext, RET_OK
        host = os.environ.get('FUTU_HOST', '127.0.0.1')
        port = int(os.environ.get('FUTU_PORT', 11111))
        ctx = OpenQuoteContext(host=host, port=port)
        ret, data = ctx.get_market_snapshot(codes)
        if ret == RET_OK and data is not None:
            for _, row in data.iterrows():
                code = row.get('code', '')
                lot_size = row.get('lot_size', 100)
                if code:
                    lot_sizes[code] = int(lot_size) if lot_size else 100
        ctx.close()
    except Exception:
        pass
    return lot_sizes


def _calc_buy_qty(target_amount: float, price: float, futu_code: str, market: str, lot_sizes: Dict[str, int]) -> int:
    """计算买入数量，考虑各市场的每手股数"""
    qty = int(target_amount / price)
    if market == 'HK':
        # 港股：按每手股数取整
        lot_size = lot_sizes.get(futu_code, 100)
        qty = (qty // lot_size) * lot_size
    elif market == 'CN':
        # A 股：100 股整数倍
        qty = (qty // 100) * 100
    elif market == 'US':
        # 美股：1 股即可
        pass
    return qty


def get_stock_prices(codes: List[str]) -> Dict[str, float]:
    """
    通过 Futu OpenAPI 获取股票实时价格
    降级：如果 OpenD 不可用，从本地日线数据获取最新收盘价

    Args:
        codes: Futu 格式代码列表

    Returns:
        {code: last_price}
    """
    prices = {}
    try:
        from futu import OpenQuoteContext, SubType
        host = os.environ.get('FUTU_HOST', '127.0.0.1')
        port = int(os.environ.get('FUTU_PORT', 11111))
        ctx = OpenQuoteContext(host=host, port=port)

        # 订阅实时报价
        ret, _ = ctx.subscribe(codes, [SubType.QUOTE])
        if ret == 0:
            ret, data = ctx.get_market_snapshot(codes)
            if ret == 0 and len(data) > 0:
                for _, row in data.iterrows():
                    code = row.get('code', '')
                    last_price = row.get('last_price', 0)
                    if code and last_price:
                        full_code = _normalize_futu_code(code)
                        prices[full_code] = float(last_price)
        ctx.close()
        if prices:
            return prices
    except Exception:
        pass

    # 降级：从本地日线数据获取最新收盘价
    print(f"  ⚠️  OpenD 不可用，使用最新收盘价作为估算")
    prices = _get_latest_close_prices(codes)
    return prices


def _normalize_futu_code(code: str) -> str:
    """将裸代码转为 Futu 格式"""
    if '.' in code:
        return code
    if code.startswith('6'):
        return f"SH.{code}"
    return f"SZ.{code}"


def _get_latest_close_prices(codes: List[str]) -> Dict[str, float]:
    """从本地日线数据获取最新收盘价"""
    prices = {}
    remaining_codes = []

    for code in codes:
        if '.' in code:
            parts = code.split('.', 1)
            ts_code = f"{parts[1]}.{parts[0]}"
        else:
            ts_code = code
        remaining_codes.append((code, ts_code))

    # 先从本地 A 股数据查找
    daily_file = DAILY_DATA_DIR / '2026' / '202604.csv'
    if daily_file.exists():
        import pandas as pd
        df = pd.read_csv(daily_file)
        latest_date = df['trade_date'].max()
        latest_df = df[df['trade_date'] == latest_date]

        new_remaining = []
        for code, ts_code in remaining_codes:
            match = latest_df[latest_df['ts_code'] == ts_code]
            if not match.empty:
                prices[code] = float(match.iloc[0]['close'])
            else:
                new_remaining.append((code, ts_code))
        remaining_codes = new_remaining

    # 本地数据找不到的，尝试 yfinance
    if remaining_codes:
        print(f"  本地数据未找到 {len(remaining_codes)} 只股票，尝试 yfinance 获取...")
        try:
            import yfinance as yf
            for code, ts_code in remaining_codes:
                try:
                    ticker = yf.Ticker(ts_code)
                    hist = ticker.history(period="5d")
                    if hist is not None and not hist.empty:
                        prices[code] = float(hist['Close'].iloc[-1])
                except Exception:
                    pass
        except ImportError:
            pass

    return prices


def get_all_positions() -> Tuple[Dict, Dict]:
    """
    获取所有市场的持仓和资金

    Returns:
        (positions_dict, funds_dict)
        positions_dict: {futu_code: {qty, market_val, avg_cost, ...}}
        funds_dict: {market: {total_assets, cash, ...}}
    """
    all_positions = {}
    all_funds = {}

    for market in ['CN', 'HK', 'US']:
        print(f"  查询 {market} 市场持仓...")
        data = get_opend_portfolio(market)
        if data.get('positions') is not None:
            for pos in data['positions']:
                code = pos.get('code', '')
                all_positions[code] = pos
            print(f"    {len(data['positions'])} 只持仓")
        if data.get('funds'):
            all_funds[market] = data['funds']
            print(f"    总资产: {data['funds'].get('total_assets', 0):,.2f}, "
                  f"现金: {data['funds'].get('cash', 0):,.2f}")

    return all_positions, all_funds


# ============================================================
# 交易执行
# ============================================================
def place_order(futu_code: str, action: str, price: float, qty: int,
                trd_env: str = 'SIMULATE', dry_run: bool = False) -> Dict:
    """
    下单

    Args:
        futu_code: Futu 格式代码 (如 SH.600519)
        action: BUY / SELL
        price: 价格（市价单传 0，会自动使用 MARKET 订单类型）
        qty: 数量
        trd_env: SIMULATE / REAL
        dry_run: 仅模拟，不实际下单

    Returns:
        下单结果
    """
    if dry_run:
        return {'status': 'dry_run', 'code': futu_code, 'action': action, 'price': price, 'qty': qty}

    script = FUTU_API_SCRIPTS / 'trade' / 'place_order.py'

    # 确定 market
    market_prefix = futu_code.split('.')[0] if '.' in futu_code else 'SH'
    market_map = {'SH': 'CN', 'SZ': 'CN', 'HK': 'HK', 'US': 'US'}
    market = market_map.get(market_prefix, 'CN')

    acc_id = ACCOUNT_IDS.get(market, 18767295)

    # 市价单使用 MARKET 订单类型
    is_market_order = (price == 0)
    cmd = [
        sys.executable, str(script),
        '--code', futu_code,
        '--side', action,
        '--quantity', str(qty),
        '--trd-env', trd_env,
        '--acc-id', str(acc_id),
        '--json',
    ]
    if is_market_order:
        cmd.extend(['--order-type', 'MARKET'])
    else:
        cmd.extend(['--price', str(price)])

    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode == 0 and result.stdout.strip():
        stdout = result.stdout.strip()
        start = stdout.find('{')
        if start >= 0:
            depth = 0
            end = -1
            for i in range(start, len(stdout)):
                if stdout[i] == '{':
                    depth += 1
                elif stdout[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > start:
                return json.loads(stdout[start:end])

    return {'status': 'error', 'error': result.stderr.strip() or result.stdout.strip()}


# ============================================================
# P&L 报告
# ============================================================
def generate_pnl_report(sell_orders: List[Dict], buy_orders: List[Dict],
                        total_assets: float, pick_source: str,
                        trd_env: str, output_dir: Path) -> str:
    """生成周期 P&L 报告"""
    sell_total = sum(o.get('expected_value', 0) for o in sell_orders)
    buy_total = sum(o.get('expected_value', 0) for o in buy_orders)

    report = {
        "workflow": "E",
        "strategy": "周期平权 Top 10",
        "generated_at": datetime.now().isoformat(),
        "trd_env": trd_env,
        "pick_source": pick_source,
        "summary": {
            "total_assets_before": round(total_assets, 2),
            "target_per_stock_pct": 0.09,
            "target_cash_pct": 0.10,
            "sell_count": len(sell_orders),
            "buy_count": len(buy_orders),
            "estimated_sell_value": round(sell_total, 2),
            "estimated_buy_value": round(buy_total, 2),
        },
        "sell_orders": sell_orders,
        "buy_orders": buy_orders,
    }

    report_path = output_dir / "pnl_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return str(report_path)


# ============================================================
# 主流程
# ============================================================
def run_workflow_e(pick_date: Optional[str] = None, trd_env: str = 'SIMULATE',
                   dry_run: bool = False, market: str = 'CN') -> Dict:
    """
    执行周期平权调仓

    Args:
        pick_date: 选股日期 YYYYMMDD
        trd_env: SIMULATE / REAL
        dry_run: 仅输出计划
        market: CN / HK / US

    Returns:
        执行结果
    """
    print("=" * 60)
    print("Workflow E — 周期平权调仓")
    print(f"市场: {market}")
    print(f"选股日期: {pick_date or '最新'}")
    print(f"交易环境: {trd_env}")
    print(f"Dry Run: {dry_run}")
    print("=" * 60)

    # 重置限频计数器
    global _order_counter
    _order_counter = 0

    # 输出目录
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = TRADE_DIR / "data" / "workflow_e" / today
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Step 1: 读取选股结果 ----
    print("\n[Step 1] 读取选股结果...")
    top10, pick_source = load_pick_result(pick_date, market=market)
    if not top10:
        print("[Workflow E] 无选股结果，终止")
        return {'error': 'no_pick_result'}

    target_codes = {s['futu_code'] for s in top10}
    # 确定调仓范围：只处理选股结果涉及的市场
    pick_markets = set(s['market'] for s in top10)

    # ---- Step 2: 查询 CN 账户总资产（仅选股涉及的市场） ----
    print("\n[Step 2] 查询账户资产...")

    # 资金隔离：只查询选股结果涉及的市场
    cn_total = 0.0
    cn_positions = {}
    cn_funds = {}

    for market in pick_markets:
        print(f"  查询 {market} 市场...")
        data = get_opend_portfolio(market)
        if data.get('funds'):
            cn_funds[market] = data['funds']
            market_total = data['funds'].get('total_assets', 0)
            cn_total += market_total
            print(f"    总资产: {market_total:,.2f}")
        if data.get('positions'):
            for pos in data['positions']:
                code = pos.get('code', '')
                cn_positions[code] = pos

    if cn_total == 0:
        cn_total = 1_000_000  # 默认 100 万
        print(f"  ⚠️  未能获取总资产，使用默认值 {cn_total:,.0f}")
    else:
        print(f"  ✅ 可用总资产: {cn_total:,.2f}")

    target_per_stock = cn_total * 0.09  # 每只 9%
    print(f"  每只目标金额: {target_per_stock:,.2f} (9%)")
    print(f"  保留现金: {cn_total * 0.10:,.2f} (10%)")

    # 只考虑当前市场的持仓
    sell_positions = {}
    for code, pos in cn_positions.items():
        if pos.get('qty', 0) > 0:  # 只考虑有实际持仓的股票
            sell_positions[code] = pos

    # ---- Step 3: 生成卖出计划 ----
    # 策略：卖出所有现有持仓，释放资金后重新等权买入 Top 10
    # 原因：资金隔离下，CN 账户资金有限，需要先卖后买才能实现真正的等权配置
    print("\n[Step 3] 生成卖出计划（卖出所有现有持仓，释放资金重新等权配置）...")
    sell_orders = []
    for code, pos in sell_positions.items():
        qty = pos.get('qty', 0)
        if qty <= 0:
            continue
        price = pos.get('nominal_price', pos.get('last_price', 0))
        expected_value = price * qty
        in_target = " (在目标列表中，将重新买入)" if code in target_codes else ""
        sell_orders.append({
            'code': code,
            'name': pos.get('name', ''),
            'qty': qty,
            'price': round(price, 3),
            'expected_value': round(expected_value, 2),
            'current_pl': pos.get('pl_ratio_avg_cost', 0),
            'in_target': code in target_codes,
        })
        print(f"  卖出 {code} {pos.get('name', '')} x{qty} @ {price:.3f} "
              f"(市值 {expected_value:,.2f}, 盈亏 {pos.get('pl_ratio_avg_cost', 0):.1f}%){in_target}")

    if not sell_orders:
        print("  无需要卖出的持仓")

    # 计算卖出后的可用资金
    estimated_sell_value = sum(o['expected_value'] for o in sell_orders)
    current_cash = cn_funds.get('CN', {}).get('cash', 0) if cn_funds else 0
    available_after_sell = current_cash + estimated_sell_value
    print(f"  预计卖出金额: {estimated_sell_value:,.2f}")
    print(f"  卖出后可用资金: {available_after_sell:,.2f}")

    # ---- Step 4: 生成买入计划 ----
    print("\n[Step 4] 生成买入计划（等权买入 Top 10）...")

    # 获取所有目标股票的价格
    all_target_codes = [s['futu_code'] for s in top10]
    print(f"  获取 {len(all_target_codes)} 只目标股票价格...")
    live_prices = get_stock_prices(all_target_codes)
    if live_prices:
        print(f"  ✅ 获取到 {len(live_prices)} 只股票价格")
    else:
        print(f"  ⚠️  未能获取价格，使用估算值")

    # 获取港股每手股数
    hk_codes = [c for c in all_target_codes if c.startswith('HK.')]
    lot_sizes = _get_lot_sizes(hk_codes) if hk_codes else {}
    if lot_sizes:
        print(f"  港股每手股数: {lot_sizes}")

    buy_orders = []
    for stock in top10:
        futu_code = stock['futu_code']

        # 使用实时价格计算数量
        price = live_prices.get(futu_code, 0)
        if price > 0:
            qty = _calc_buy_qty(target_per_stock, price, futu_code, stock['market'], lot_sizes)
            if qty > 0:
                print(f"  买入 {futu_code} {stock['name']} x{qty} @ {price:.3f} (目标金额 {target_per_stock:,.2f})")
                buy_orders.append({
                    'code': futu_code,
                    'name': stock['name'],
                    'action': 'BUY',
                    'qty': qty,
                    'price': round(price, 3),
                    'expected_value': round(qty * price, 2),
                })
            else:
                print(f"  ⚠️  {futu_code} 价格过高，计算数量为 0，跳过")
        else:
            print(f"  ⚠️  {futu_code} 无价格参考，跳过")

    if not buy_orders:
        print("  无需要买入的股票")

    # ---- Step 5: 执行交易 ----
    print(f"\n[Step 5] 执行交易 (dry_run={dry_run})...")
    executed_sells = []
    executed_buys = []

    for order in sell_orders:
        print(f"  卖出 {order['code']} x{order['qty']}...")
        qty = int(order['qty'])
        result = _rate_limited_place_order(
            futu_code=order['code'],
            action='SELL',
            price=0,  # 市价单
            qty=qty,
            trd_env=trd_env,
            dry_run=dry_run,
        )
        order['execution'] = result
        executed_sells.append(order)
        status = result.get('status', 'unknown')
        print(f"    结果: {status}")

    for order in buy_orders:
        qty = order.get('qty', 0)
        if qty <= 0:
            print(f"  ⚠️  {order['code']} 数量为 0，跳过")
            continue

        print(f"  买入 {order['code']} x{qty}...")
        result = _rate_limited_place_order(
            futu_code=order['code'],
            action='BUY',
            price=0,
            qty=qty,
            trd_env=trd_env,
            dry_run=dry_run,
        )
        order['execution'] = result
        executed_buys.append(order)
        status = result.get('status', 'unknown')
        print(f"    结果: {status}")

    # ---- Step 6: 生成 P&L 报告 ----
    print("\n[Step 6] 生成 P&L 报告...")
    report_path = generate_pnl_report(
        sell_orders=executed_sells,
        buy_orders=executed_buys,
        total_assets=cn_total,
        pick_source=pick_source,
        trd_env=trd_env,
        output_dir=output_dir,
    )
    print(f"  P&L 报告: {report_path}")

    # ---- 汇总 ----
    plan_path = output_dir / "trade_plan.json"
    plan = {
        'workflow': 'E',
        'generated_at': datetime.now().isoformat(),
        'pick_date': pick_date or 'latest',
        'trd_env': trd_env,
        'dry_run': dry_run,
        'total_assets': round(cn_total, 2),
        'target_per_stock': round(target_per_stock, 2),
        'sell_orders': executed_sells,
        'buy_orders': executed_buys,
        'report_path': report_path,
    }
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Workflow E 完成")
    print(f"卖出: {len(executed_sells)} 笔, 买入: {len(executed_buys)} 笔")
    print(f"输出目录: {output_dir}")
    print(f"{'=' * 60}")

    return plan


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Workflow E — 周期平权调仓")
    parser.add_argument('--market', type=str, default='CN',
                        choices=['CN', 'HK', 'US'],
                        help='市场 (默认: CN)')
    parser.add_argument('--pick-date', type=str, default=None,
                        help='选股日期 YYYYMMDD (默认: 最新)')
    parser.add_argument('--trd-env', type=str, default='SIMULATE',
                        choices=['SIMULATE', 'REAL'],
                        help='交易环境 (默认: SIMULATE)')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅输出计划，不实际下单')

    args = parser.parse_args()

    if args.trd_env == 'REAL' and not args.dry_run:
        confirm = input("⚠️  实盘交易确认！输入 YES 继续: ")
        if confirm != 'YES':
            print("已取消")
            sys.exit(0)

    result = run_workflow_e(
        pick_date=args.pick_date,
        trd_env=args.trd_env,
        dry_run=args.dry_run,
        market=args.market,
    )

    if args.dry_run:
        print("\n=== DRY RUN 结果 ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
