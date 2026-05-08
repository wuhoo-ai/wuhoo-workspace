#!/usr/bin/env python3
"""
futures_diagnose.py — 期货持仓诊断 Phase 5
扫描持仓风险：保证金率、到期预警、浮亏监控

用法:
  python3.11 futures_diagnose.py              # 全市场诊断
  python3.11 futures_diagnose.py --market US  # 单市场
"""

import sys, json, time, argparse
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

DATA_DIR = Path.home() / "wuhoo-workspace" / "data" / "futures"
DIAGNOSE_DIR = DATA_DIR / "diagnose"
CONTRACT_INFO_PATH = DATA_DIR / "contract_info.json"

ACCOUNTS = {"US": 18767290, "HK": 18767297}

RISK_RULES = {
    "margin_warning": 0.50,
    "margin_critical": 0.60,
    "expiry_warning_days": 10,
    "expiry_critical_days": 5,
    "loss_warning_pct": -0.03,
    "loss_critical_pct": -0.05,
    "drawdown_warning": -0.10,
    "drawdown_critical": -0.15,
}


def diagnose():
    from futu import OpenFutureTradeContext, TrdEnv, RET_OK

    with open(CONTRACT_INFO_PATH) as f:
        contracts = json.load(f)

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = DIAGNOSE_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🩺 期货持仓诊断 — {date_str}\n")

    all_positions = []
    all_signals = []
    total_equity = 0
    total_margin = 0

    for market, acc_id in ACCOUNTS.items():
        ctx = OpenFutureTradeContext(host="127.0.0.1", port=11111)
        time.sleep(0.3)

        # 账户信息
        ret, acc_info = ctx.accinfo_query(trd_env=TrdEnv.SIMULATE, acc_id=acc_id)
        if ret != RET_OK:
            print(f"   ⚠️ {market} 账户查询失败: {acc_info}")
            ctx.close()
            continue

        row = acc_info.iloc[0]
        equity = float(row.get("total_assets", 0) or 0)
        cash = float(row.get("cash", 0) or 0)
        upl = float(row.get("unrealized_pl", 0) or 0)
        total_equity += equity

        print(f"  {market} 账户 (ID: {acc_id})")
        print(f"    权益: {equity:,.0f}  现金: {cash:,.0f}  浮盈: {upl:+,.0f}")

        # 持仓
        ret_pos, positions = ctx.position_list_query(trd_env=TrdEnv.SIMULATE, acc_id=acc_id)
        if ret_pos != RET_OK or positions.empty:
            print(f"    持仓: 无\n")
            ctx.close()
            continue

        # 计算保证金（逐品种查询）
        for _, pos in positions.iterrows():
            code = pos.get("code", "")
            qty = pos.get("qty", 0)
            cost = pos.get("cost_price", 0)
            nominal = pos.get("nominal_price", 0)
            pl = pos.get("unrealized_pl", 0)
            pl_pct = pos.get("pl_ratio", 0)

            # 获取保证金
            ret_m, margin_info = ctx.acctradinginfo_query(
                order_type=1, code=code, price=nominal,
                trd_env=TrdEnv.SIMULATE, acc_id=acc_id,
            )
            margin_used = 0
            if ret_m == RET_OK:
                margin_used = float(margin_info["long_required_im"].iloc[0] or 0)
            total_margin += margin_used

            info = contracts.get(code, {})
            name = info.get("name", code)
            lot_size = info.get("lot_size", 1)
            notional = abs(qty) * nominal * lot_size

            pos_data = {
                "code": code, "name": name, "market": market,
                "qty": int(qty), "cost": float(cost), "nominal": float(nominal),
                "pl": float(pl), "pl_pct": float(pl_pct),
                "margin": margin_used, "notional": notional,
                "leverage": round(notional / margin_used, 1) if margin_used > 0 else 0,
            }
            all_positions.append(pos_data)

            # 信号
            signals = []
            # 亏损检查
            if pl_pct <= RISK_RULES["loss_critical_pct"]:
                signals.append({"level": "critical", "type": "loss", "msg": f"浮亏{pl_pct:.1%} 达止损线"})
            elif pl_pct <= RISK_RULES["loss_warning_pct"]:
                signals.append({"level": "warning", "type": "loss", "msg": f"浮亏{pl_pct:.1%} 接近止损"})

            # 到期检查
            import re
            expiry_match = re.search(r"\((\d{4})\)", name)
            if expiry_match:
                ym = expiry_match.group(1)
                year = 2000 + int(ym[:2])
                month = int(ym[2:])
                expiry = datetime(year, month, 1) + timedelta(days=31)
                expiry = expiry.replace(day=1) - timedelta(days=1)
                days_left = (expiry - datetime.now()).days
                if days_left <= RISK_RULES["expiry_critical_days"]:
                    signals.append({"level": "critical", "type": "expiry", "msg": f"距到期{days_left}天"})
                elif days_left <= RISK_RULES["expiry_warning_days"]:
                    signals.append({"level": "warning", "type": "expiry", "msg": f"距到期{days_left}天"})

            if signals:
                all_signals.append({"code": code, "name": name, "signals": signals})

            emoji = "📈" if qty > 0 else "📉"
            sig_str = " ".join(s["msg"] for s in signals) if signals else ""
            print(f"    {emoji} {code:<16s} {name:<14s} {abs(qty):>4d}手  浮盈={pl:+,.0f} ({pl_pct:+.1%})  {sig_str}")

        ctx.close()
        print()

    # 组合级风险
    margin_pct = total_margin / total_equity * 100 if total_equity > 0 else 0
    print(f"{'='*60}")
    print(f"  总权益: {total_equity:,.0f}  总保证金: {total_margin:,.0f} ({margin_pct:.1f}%)")

    if margin_pct >= RISK_RULES["margin_critical"] * 100:
        print(f"  🔴 保证金率 {margin_pct:.1f}% ≥ {RISK_RULES['margin_critical']*100:.0f}%")
    elif margin_pct >= RISK_RULES["margin_warning"] * 100:
        print(f"  ⚠️ 保证金率 {margin_pct:.1f}% ≥ {RISK_RULES['margin_warning']*100:.0f}%")
    else:
        print(f"  ✅ 保证金安全")

    # 保存
    output = {
        "date": date_str,
        "total_equity": total_equity,
        "total_margin": total_margin,
        "margin_pct": round(margin_pct, 2),
        "positions": all_positions,
        "signals": all_signals,
    }

    with open(out_dir / "diagnose.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    # Markdown 报告
    md = [f"# 期货持仓诊断 — {date_str}",
          f"\n## 总览\n",
          f"- 总权益: {total_equity:,.0f}",
          f"- 总保证金: {total_margin:,.0f} ({margin_pct:.1f}%)",
          f"- 持仓数: {len(all_positions)}",
          f"\n## 持仓明细\n"]

    for p in all_positions:
        md.append(f"- {p['code']} {p['name']}: {p['qty']}手 @ {p['nominal']:.1f}  浮盈={p['pl']:+,.0f} ({p['pl_pct']:+.1%})")

    if all_signals:
        md.append(f"\n## ⚠️ 警告信号\n")
        for s in all_signals:
            for sig in s["signals"]:
                icon = "🔴" if sig["level"] == "critical" else "⚠️"
                md.append(f"- {icon} {s['code']} {s['name']}: {sig['msg']}")

    md.append(f"\n*报告时间: {datetime.now().isoformat()}*")
    with open(out_dir / "diagnose_report.md", "w") as f:
        f.write("\n".join(md) + "\n")

    print(f"\n✅ 诊断报告: {out_dir}/")
    print(f"   {out_dir}/diagnose.json")
    print(f"   {out_dir}/diagnose_report.md")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=str, choices=["US", "HK", "all"], default="all")
    args = parser.parse_args()

    if args.market != "all":
        global ACCOUNTS
        ACCOUNTS = {args.market: ACCOUNTS[args.market]}

    diagnose()


if __name__ == "__main__":
    main()
