#!/usr/bin/env python3
"""
futures_risk_manager.py — 期货风控模块
Phase 4.1: 保证金检查、止损计算、到期预警、总敞口监控

用法:
  python3.11 futures_risk_manager.py --check                              # 检查当前持仓风险
  python3.11 futures_risk_manager.py --validate-order --code US.MESmain   # 验证新订单风控
      --direction LONG --contracts 10 --price 5865.0
"""

import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

DATA_DIR = Path.home() / "wuhoo-workspace" / "data" / "futures"
AUDIT_LOG = Path.home() / ".futures_trade_audit.jsonl"

# ============================================================
# 风控规则
# ============================================================
RISK_RULES = {
    "single_position_max_margin_pct": 0.20,   # 单品种保证金 ≤ 20% 权益
    "total_margin_max_pct": 0.60,             # 总保证金 ≤ 60% 权益
    "single_trade_max_loss_pct": 0.02,        # 单笔最大亏损 ≤ 2% 权益
    "max_drawdown_pct": 0.15,                 # 最大回撤 ≤ 15%
    "expiry_warning_days": 5,                 # 到期前 N 天预警
    "correlated_group_max_margin_pct": 0.30,  # 同类品种总保证金 ≤ 30%
    "min_adx_for_trade": 10,                  # 最低 ADX（趋势不明朗不交易）
}

# 品种关联分组
CORRELATED_GROUPS = {
    "美股指数": ["US.MESmain", "US.MNQmain"],
    "贵金属": ["US.MGCmain", "US.SImain"],
    "港股指数": ["HK.MHImain", "HK.MCHmain", "HK.HTImain"],
}


def load_contract_info():
    with open(DATA_DIR / "contract_info.json") as f:
        return json.load(f)


def audit_log(entry: dict):
    """追加审计日志"""
    entry["ts"] = datetime.now().isoformat()
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def check_single_position_margin(margin_used: float, equity: float) -> dict:
    """单品种保证金检查"""
    pct = margin_used / equity if equity > 0 else 1.0
    limit = RISK_RULES["single_position_max_margin_pct"]
    return {
        "rule": "single_position_margin",
        "pct": round(pct * 100, 2),
        "limit_pct": round(limit * 100, 1),
        "pass": pct <= limit,
        "msg": f"{pct*100:.1f}% {'≤' if pct <= limit else '>'} {limit*100:.0f}%",
    }


def check_total_margin(total_margin: float, equity: float) -> dict:
    """总保证金检查"""
    pct = total_margin / equity if equity > 0 else 1.0
    limit = RISK_RULES["total_margin_max_pct"]
    return {
        "rule": "total_margin",
        "pct": round(pct * 100, 2),
        "limit_pct": round(limit * 100, 1),
        "pass": pct <= limit,
        "msg": f"{pct*100:.1f}% {'≤' if pct <= limit else '>'} {limit*100:.0f}%",
    }


def check_single_trade_loss(close: float, stop_price: float, contracts: int,
                            lot_size: float, equity: float) -> dict:
    """单笔亏损检查"""
    loss_per_contract = abs(close - stop_price) * lot_size
    total_loss = loss_per_contract * contracts
    pct = total_loss / equity if equity > 0 else 1.0
    limit = RISK_RULES["single_trade_max_loss_pct"]
    return {
        "rule": "single_trade_loss",
        "loss_amount": round(total_loss, 0),
        "loss_pct": round(pct * 100, 2),
        "limit_pct": round(limit * 100, 1),
        "pass": pct <= limit,
        "msg": f"${total_loss:,.0f} ({pct*100:.2f}%) {'≤' if pct <= limit else '>'} {limit*100:.0f}%",
    }


def check_correlated_group(margin_used: float, equity: float, group_name: str,
                           group_members: list, positions: dict) -> dict:
    """同类品种关联检查"""
    group_margin = sum(
        positions.get(m, {}).get("margin_used", 0) for m in group_members
    )
    pct = group_margin / equity if equity > 0 else 0
    limit = RISK_RULES["correlated_group_max_margin_pct"]
    return {
        "rule": f"correlated_group_{group_name}",
        "pct": round(pct * 100, 2),
        "limit_pct": round(limit * 100, 1),
        "pass": pct <= limit,
        "msg": f"{group_name} {pct*100:.1f}% {'≤' if pct <= limit else '>'} {limit*100:.0f}%",
    }


def check_adx(adx_value: float) -> dict:
    """ADX 趋势检查"""
    limit = RISK_RULES["min_adx_for_trade"]
    return {
        "rule": "min_adx",
        "value": round(adx_value, 1),
        "limit": limit,
        "pass": adx_value >= limit,
        "msg": f"ADX={adx_value:.1f} {'≥' if adx_value >= limit else '<'} {limit}",
    }


def check_expiry(code: str) -> dict:
    """合约到期检查（从合约名称提取到期月）"""
    info = load_contract_info().get(code, {})
    name = info.get("name", code)

    # 从代码名称提取到期月（如 "2605" = 2026-05, "2606" = 2026-06）
    # 对 Futu 主连代码，名称中包含如 "主连 (2605)" 的信息
    import re
    match = re.search(r"\((\d{4})\)", name)
    if not match:
        # 从 get_stock_basicinfo 返回的 name 提取
        # 格式如 "小恒指期货主连 (2605)"
        return {"rule": "expiry", "pass": True, "msg": "无法解析到期日，跳过"}

    expiry_str = match.group(1)  # "2605"
    year = 2000 + int(expiry_str[:2])
    month = int(expiry_str[2:])
    expiry_date = datetime(year, month, 1) + timedelta(days=31)
    expiry_date = expiry_date.replace(day=1) - timedelta(days=1)  # 当月最后一天

    days_left = (expiry_date - datetime.now()).days
    warning_days = RISK_RULES["expiry_warning_days"]

    if days_left < 0:
        return {"rule": "expiry", "pass": False, "days_left": days_left,
                "msg": f"🔴 已过期 ({expiry_date.strftime('%Y-%m')})", "expiry": expiry_date.strftime("%Y-%m")}
    elif days_left <= warning_days:
        return {"rule": "expiry", "pass": False, "days_left": days_left,
                "msg": f"🔴 即将到期 {days_left} 天 ({expiry_date.strftime('%Y-%m')})",
                "expiry": expiry_date.strftime("%Y-%m")}
    else:
        return {"rule": "expiry", "pass": True, "days_left": days_left,
                "msg": f"✅ 距到期 {days_left} 天 ({expiry_date.strftime('%Y-%m')})",
                "expiry": expiry_date.strftime("%Y-%m")}


def validate_order(
    code: str,
    direction: str,
    contracts: int,
    price: float,
    stop_price: float,
    adx_14: float,
    equity: float,
    existing_positions: dict = None,
) -> dict:
    """
    验证新订单是否通过全部风控检查。
    返回: {"all_pass": bool, "checks": [...], "blocked_by": [...]}
    """
    if existing_positions is None:
        existing_positions = {}

    info = load_contract_info().get(code, {})
    lot_size = info.get("lot_size", 1)
    margin_key = "long_margin" if direction == "LONG" else "short_margin"
    margin_per_contract = info.get(margin_key, 0)

    total_margin_new = contracts * margin_per_contract
    existing_total_margin = sum(p.get("margin_used", 0) for p in existing_positions.values())

    checks = []

    # 1. ADX 检查
    checks.append(check_adx(adx_14))

    # 2. 到期检查
    checks.append(check_expiry(code))

    # 3. 单笔亏损检查
    checks.append(check_single_trade_loss(price, stop_price, contracts, lot_size, equity))

    # 4. 单品种保证金
    existing_code_margin = existing_positions.get(code, {}).get("margin_used", 0)
    checks.append(check_single_position_margin(
        existing_code_margin + total_margin_new, equity
    ))

    # 5. 总保证金
    checks.append(check_total_margin(
        existing_total_margin + total_margin_new, equity
    ))

    # 6. 关联品种检查
    for group_name, members in CORRELATED_GROUPS.items():
        if code in members:
            # 模拟新持仓后的组内保证金
            simulated_positions = {**existing_positions}
            simulated_positions[code] = simulated_positions.get(code, {})
            simulated_positions[code]["margin_used"] = (
                simulated_positions[code].get("margin_used", 0) + total_margin_new
            )
            checks.append(check_correlated_group(
                total_margin_new, equity, group_name, members, simulated_positions
            ))
            break

    blocked_by = [c for c in checks if not c["pass"]]
    all_pass = len(blocked_by) == 0

    result = {
        "all_pass": all_pass,
        "checks": checks,
        "blocked_by": [c["rule"] for c in blocked_by],
        "total_margin_new": round(total_margin_new, 0),
        "total_margin_after": round(existing_total_margin + total_margin_new, 0),
        "total_margin_pct_after": round((existing_total_margin + total_margin_new) / equity * 100, 2),
    }

    audit_log({
        "action": "RISK_CHECK",
        "code": code,
        "direction": direction,
        "contracts": contracts,
        "price": price,
        "all_pass": all_pass,
        "blocked_by": result["blocked_by"],
    })

    return result


def print_check_result(result: dict):
    """格式化打印风控结果"""
    for check in result["checks"]:
        icon = "✅" if check["pass"] else "❌"
        print(f"   {icon} {check['rule']:<25s} {check['msg']}")

    print(f"\n   {'✅ 全部通过' if result['all_pass'] else '❌ 被阻断: ' + ', '.join(result['blocked_by'])}")
    print(f"   新保证金: {result['total_margin_new']:,.0f} | "
          f"总保证金: {result['total_margin_after']:,.0f} "
          f"({result['total_margin_pct_after']:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="期货风控模块")
    sub = parser.add_subparsers(dest="cmd")

    # check 子命令
    p_check = sub.add_parser("check", help="检查当前持仓风险")
    p_check.add_argument("--account-id", type=int, default=18767290)

    # validate-order 子命令
    p_val = sub.add_parser("validate-order", help="验证新订单")
    p_val.add_argument("--code", type=str, required=True)
    p_val.add_argument("--direction", type=str, required=True, choices=["LONG", "SHORT"])
    p_val.add_argument("--contracts", type=int, required=True)
    p_val.add_argument("--price", type=float, required=True)
    p_val.add_argument("--stop-price", type=float, required=True)
    p_val.add_argument("--adx", type=float, default=10)
    p_val.add_argument("--equity", type=float, default=10000000.0)

    args = parser.parse_args()

    if args.cmd == "validate-order":
        print(f"🔍 风控验证: {args.code} {args.direction} {args.contracts}手 @ {args.price}")
        print()
        result = validate_order(
            code=args.code,
            direction=args.direction,
            contracts=args.contracts,
            price=args.price,
            stop_price=args.stop_price,
            adx_14=args.adx,
            equity=args.equity,
        )
        print_check_result(result)
    elif args.cmd == "check":
        print("⚠️ 实时持仓检查需要连接 OpenD，请使用 futures_trade.py --check")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
