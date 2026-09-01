#!/usr/bin/env python3
"""
futures_trade.py — 期货交易执行引擎
Phase 4.2: OpenFutureTradeContext 交易 + 持仓查询 + 调仓

用法:
  # 查询持仓
  python3.11 futures_trade.py --check

  # 基于选品结果生成调仓计划（dry-run）
  python3.11 futures_trade.py --rebalance --date 2026-05-08 --dry-run

  # 执行调仓（需确认）
  python3.11 futures_trade.py --rebalance --date 2026-05-08

  # 手动下单
  python3.11 futures_trade.py --order --code US.MESmain --direction LONG \\
      --contracts 5 --price 5865.0

数据源: Futu OpenD OpenFutureTradeContext
审计日志: ~/.futures_trade_audit.jsonl
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd

DATA_DIR = Path.home() / "wuhoo-workspace" / "data" / "futures"
FACTORS_DIR = DATA_DIR / "factors"
AUDIT_LOG = Path.home() / ".futures_trade_audit.jsonl"

# ============================================================
# 账户配置
# ============================================================
ACCOUNTS = {
    "US": 18767290,
    "HK": 18767297,
}


def load_contract_info():
    with open(DATA_DIR / "contract_info.json") as f:
        return json.load(f)


def audit_log(entry: dict):
    entry["ts"] = datetime.now().isoformat()
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_futu_contexts():
    """创建 US 和 HK 期货交易上下文"""
    from futu import OpenFutureTradeContext
    ctx_us = OpenFutureTradeContext(host="127.0.0.1", port=11111)
    time.sleep(0.3)
    ctx_hk = OpenFutureTradeContext(host="127.0.0.1", port=11111)
    time.sleep(0.3)
    return ctx_us, ctx_hk


def query_positions(ctx, acc_id: int, trd_env) -> pd.DataFrame:
    """查询期货持仓"""
    from futu import RET_OK
    ret, data = ctx.position_list_query(trd_env=trd_env, acc_id=acc_id)
    if ret != RET_OK:
        print(f"   ⚠️ 持仓查询失败: {data}")
        return pd.DataFrame()
    if data.empty:
        return pd.DataFrame()
    return data


def query_account(ctx, acc_id: int, trd_env) -> dict:
    """查询账户资金"""
    from futu import RET_OK
    ret, data = ctx.accinfo_query(trd_env=trd_env, acc_id=acc_id)
    if ret != RET_OK:
        return {"total_assets": 10000000.0, "cash": 10000000.0}
    row = data.iloc[0]
    return {
        "total_assets": float(row.get("total_assets", 0) or 0),
        "cash": float(row.get("cash", 0) or 0),
        "market_val": float(row.get("market_val", 0) or 0),
        "unrealized_pl": float(row.get("unrealized_pl", 0) or 0),
    }


def place_futures_order(ctx, code: str, direction: str, contracts: int,
                        price: float, acc_id: int, trd_env, dry_run: bool = False) -> dict:
    """下期货单"""
    from futu import TrdSide, OrderType, RET_OK

    side = TrdSide.BUY if direction == "LONG" else TrdSide.SELL
    order_type = OrderType.NORMAL  # 限价单

    entry = {
        "action": "ORDER",
        "code": code,
        "direction": direction,
        "contracts": contracts,
        "price": price,
        "acc_id": acc_id,
        "dry_run": dry_run,
    }

    if dry_run:
        entry["status"] = "DRY_RUN"
        audit_log(entry)
        return entry

    ret, data = ctx.place_order(
        price=price,
        qty=contracts,
        code=code,
        trd_side=side,
        order_type=order_type,
        trd_env=trd_env,
        acc_id=acc_id,
    )

    if ret == RET_OK:
        order_id = data.get("order_id", [None])[0] if hasattr(data, "get") else str(data)
        entry["status"] = "SUCCESS"
        entry["order_id"] = str(order_id)
        print(f"   ✅ 下单成功: {code} {direction} {contracts}手 @ {price} — 订单号 {order_id}")
    else:
        entry["status"] = "FAILED"
        entry["error"] = str(data)
        print(f"   ❌ 下单失败: {code} {direction} {contracts}手 — {data}")

    audit_log(entry)
    return entry


def close_position(ctx, code: str, acc_id: int, trd_env, dry_run: bool = False) -> dict:
    """平仓（市价反向单）"""
    from futu import TrdSide, OrderType, RET_OK

    # 先查当前持仓方向
    pos_data = query_positions(ctx, acc_id, trd_env)
    if pos_data.empty:
        return {"status": "SKIP", "msg": "无持仓"}

    matching = pos_data[pos_data["code"] == code]
    if matching.empty:
        return {"status": "SKIP", "msg": f"无 {code} 持仓"}

    row = matching.iloc[0]
    qty = int(row.get("qty", 0))
    if qty <= 0:
        return {"status": "SKIP", "msg": "持仓为 0"}

    # 市价反向平仓
    side = TrdSide.SELL if qty > 0 else TrdSide.BUY

    if dry_run:
        entry = {"action": "CLOSE", "code": code, "qty": abs(qty), "dry_run": True}
        audit_log(entry)
        print(f"   [DRY-RUN] 平仓 {code} {abs(qty)}手")
        return entry

    ret, data = ctx.place_order(
        price=0,  # 市价
        qty=abs(qty),
        code=code,
        trd_side=side,
        order_type=OrderType.MARKET,
        trd_env=trd_env,
        acc_id=acc_id,
    )

    entry = {"action": "CLOSE", "code": code, "qty": abs(qty)}
    if ret == RET_OK:
        entry["status"] = "SUCCESS"
        print(f"   ✅ 平仓成功: {code} {abs(qty)}手")
    else:
        entry["status"] = "FAILED"
        entry["error"] = str(data)
        print(f"   ❌ 平仓失败: {code} — {data}")

    audit_log(entry)
    return entry


def cmd_check():
    """查询所有期货账户持仓"""
    from futu import TrdEnv

    ctx_us, ctx_hk = get_futu_contexts()
    contracts = load_contract_info()

    try:
        print("📊 期货持仓查询\n")
        total_equity = 0
        total_margin = 0

        for market, acc_id in ACCOUNTS.items():
            print(f"{'='*60}")
            print(f"  {market} 期货账户 (ID: {acc_id})")

            # 账户信息
            ctx = ctx_us if market == "US" else ctx_hk
            acc_info = query_account(ctx, acc_id, TrdEnv.SIMULATE)
            print(f"  总资产: {acc_info['total_assets']:,.0f}  "
                  f"现金: {acc_info['cash']:,.0f}  "
                  f"市值: {acc_info['market_val']:,.0f}  "
                  f"浮盈: {acc_info['unrealized_pl']:,.0f}")

            total_equity += acc_info["total_assets"]

            # 持仓
            positions = query_positions(ctx, acc_id, TrdEnv.SIMULATE)
            if positions.empty:
                print(f"  持仓: 无")
                continue

            print(f"  持仓 {len(positions)} 笔:")
            for _, row in positions.iterrows():
                code = row.get("code", "?")
                qty = row.get("qty", 0)
                cost = row.get("cost_price", 0)
                nominal = row.get("nominal_price", 0)
                pl = row.get("unrealized_pl", 0)
                pl_pct = row.get("pl_ratio", 0)
                name = contracts.get(code, {}).get("name", "")
                emoji = "📈" if qty > 0 else "📉"
                print(f"  {emoji} {code:<18s} {name:<14s} {abs(qty):>4d}手  "
                      f"成本={cost:>10.1f} 现价={nominal:>10.1f}  "
                      f"浮盈={pl:>+10,.0f} ({pl_pct:>+.1f}%)")

        print(f"\n{'='*60}")
        print(f"  总权益: {total_equity:,.0f}")

    finally:
        ctx_us.close()
        ctx_hk.close()


def cmd_rebalance(date_str: str, dry_run: bool = True):
    """基于选品结果生成并执行调仓计划"""
    from futu import TrdEnv

    pick_path = FACTORS_DIR / f"pick_result_{date_str}.csv"
    if not pick_path.exists():
        print(f"❌ 选品结果不存在: {pick_path}")
        print(f"   请先运行: python3.11 futures_pick.py --date {date_str}")
        sys.exit(1)

    picks = pd.read_csv(pick_path)
    if picks.empty:
        print("⚠️ 选品结果为空，无需调仓")
        return

    ctx_us, ctx_hk = get_futu_contexts()
    contracts = load_contract_info()

    try:
        print(f"🔄 期货调仓计划 — {date_str}")
        print(f"   {'[DRY-RUN] 模拟模式' if dry_run else '⚠️ 实盘模式'}")
        print(f"   选品: {len(picks)} 个候选")
        print()

        # 扫描所有持仓
        all_positions = {}
        for market, acc_id in ACCOUNTS.items():
            ctx = ctx_us if market == "US" else ctx_hk
            pos = query_positions(ctx, acc_id, TrdEnv.SIMULATE)
            if not pos.empty:
                for _, row in pos.iterrows():
                    code = row.get("code", "")
                    all_positions[code] = {
                        "qty": row.get("qty", 0),
                        "market": market,
                        "acc_id": acc_id,
                    }

        # 目标持仓
        target_codes = set(picks["code"].tolist())

        # 需要平仓的：当前持仓但不在目标列表
        to_close = [c for c in all_positions if c not in target_codes]
        # 需要开仓的：目标列表但不在当前持仓
        to_open = [c for c in target_codes if c not in all_positions]
        # 持仓调整的：都在但仓位不同（MVP 先跳过）

        print(f"📋 调仓计划:")
        print(f"   当前持仓: {len(all_positions)} 个品种")
        print(f"            {list(all_positions.keys()) if all_positions else '无'}")
        print(f"   目标持仓: {len(target_codes)} 个品种")
        print(f"            {list(target_codes)}")
        print()

        if to_close:
            print(f"🔴 平仓 ({len(to_close)} 个):")
            for code in to_close:
                pos = all_positions[code]
                ctx = ctx_us if pos["market"] == "US" else ctx_hk
                close_position(ctx, code, pos["acc_id"], TrdEnv.SIMULATE, dry_run)

        if to_open:
            print(f"\n🟢 开仓 ({len(to_open)} 个):")
            for code in to_open:
                pick_row = picks[picks["code"] == code].iloc[0]
                info = contracts.get(code, {})
                market = info.get("market", "US")
                ctx = ctx_us if market == "US" else ctx_hk
                acc_id = ACCOUNTS[market]

                # 获取限价（当前价格 ± 0.1% 滑点）
                direction = pick_row["direction"]
                price = pick_row["close"]
                contracts_qty = int(pick_row["contracts"])
                slippage = 0.001  # 0.1%

                if direction == "LONG":
                    limit_price = round(price * (1 + slippage), 2)
                else:
                    limit_price = round(price * (1 - slippage), 2)

                print(f"   {pick_row['code']} {direction} {contracts_qty}手 @ {limit_price:.1f}"
                      f" (现价={price:.1f})")

                place_futures_order(
                    ctx, code, direction, contracts_qty, limit_price,
                    acc_id, TrdEnv.SIMULATE, dry_run
                )

        if not to_close and not to_open:
            print("✅ 持仓已与目标一致，无需调整")

    finally:
        ctx_us.close()
        ctx_hk.close()


def cmd_order(code: str, direction: str, contracts_qty: int, price: float, dry_run: bool):
    """手动下单"""
    from futu import TrdEnv

    info = load_contract_info().get(code, {})
    market = info.get("market", "US")
    acc_id = ACCOUNTS[market]

    ctx_us, ctx_hk = get_futu_contexts()
    ctx = ctx_us if market == "US" else ctx_hk

    try:
        print(f"📝 手动下单: {code} {direction} {contracts_qty}手 @ {price}")
        print(f"   账户: {acc_id} ({market})  |  {'DRY-RUN' if dry_run else '实盘'}")
        print()

        result = place_futures_order(
            ctx, code, direction, contracts_qty, price,
            acc_id, TrdEnv.SIMULATE, dry_run
        )
        print(f"\n结果: {json.dumps(result, indent=2, ensure_ascii=False, default=str)}")
    finally:
        ctx_us.close()
        ctx_hk.close()


def main():
    parser = argparse.ArgumentParser(description="期货交易执行引擎")
    sub = parser.add_subparsers(dest="cmd")

    # check 子命令
    sub.add_parser("check", help="查询所有期货账户持仓")

    # rebalance 子命令
    p_reb = sub.add_parser("rebalance", help="基于选品结果调仓")
    p_reb.add_argument("--date", type=str, required=True)
    p_reb.add_argument("--dry-run", action="store_true", default=True,
                       help="模拟模式 (默认开启)")
    p_reb.add_argument("--execute", action="store_true",
                       help="实际执行 (覆盖 dry-run)")

    # order 子命令
    p_ord = sub.add_parser("order", help="手动下单")
    p_ord.add_argument("--code", type=str, required=True)
    p_ord.add_argument("--direction", type=str, required=True, choices=["LONG", "SHORT"])
    p_ord.add_argument("--contracts", type=int, required=True)
    p_ord.add_argument("--price", type=float, required=True)
    p_ord.add_argument("--dry-run", action="store_true", default=True)
    p_ord.add_argument("--execute", action="store_true")

    args = parser.parse_args()

    if args.cmd == "check":
        cmd_check()
    elif args.cmd == "rebalance":
        dry_run = not args.execute
        cmd_rebalance(args.date, dry_run)
    elif args.cmd == "order":
        dry_run = not args.execute
        cmd_order(args.code, args.direction, args.contracts, args.price, dry_run)
    else:
        parser.print_help()
        print("\n快捷用法:")
        print("  查询持仓:  python3.11 futures_trade.py check")
        print("  模拟调仓:  python3.11 futures_trade.py rebalance --date 2026-05-08")
        print("  实盘调仓:  python3.11 futures_trade.py rebalance --date 2026-05-08 --execute")


if __name__ == "__main__":
    main()
