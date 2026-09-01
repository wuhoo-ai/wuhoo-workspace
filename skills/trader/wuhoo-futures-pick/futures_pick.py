#!/usr/bin/env python3
"""
futures_pick.py — 期货品种选择脚本
Phase 1.2: 基于因子数据，输出做多/做空候选 + 仓位建议

用法:
  python3.11 futures_pick.py                           # 今天选品
  python3.11 futures_pick.py --date 2026-05-08          # 指定日期
  python3.11 futures_pick.py --top-n 3 --direction LONG  # 仅做多，Top 3
  python3.11 futures_pick.py --top-n 3 --direction both  # 做多+做空各 3

输出: ~/wuhoo-workspace/data/futures/factors/pick_result_{date}.csv
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

DATA_DIR = Path.home() / "wuhoo-workspace" / "data" / "futures"
FACTORS_DIR = DATA_DIR / "factors"
CONTRACT_INFO_PATH = DATA_DIR / "contract_info.json"


def calc_position_suggestion(
    close: float,
    lot_size: float,
    margin: float,
    volatility_20d: float,
    adx_14: float,
    account_equity: float = 10000000.0,
    risk_per_trade: float = 0.02,
    max_margin_pct: float = 0.15,
) -> dict:
    """
    计算建议仓位。

    两个约束取最小值：
    1. 风险约束: contracts = equity * risk_pct / (close * lot_size * stop_pct)
    2. 保证金约束: contracts = equity * max_margin_pct / margin
    """
    # ATR-based stop (2x daily volatility / sqrt(252))
    daily_vol = volatility_20d / np.sqrt(252) if volatility_20d > 0 else 0.01
    stop_pct = 2.0 * daily_vol
    stop_pct = max(stop_pct, 0.01)  # 最少 1% 止损

    # 风险约束手数
    risk_amount = account_equity * risk_per_trade
    point_risk = close * stop_pct * lot_size
    contracts_risk = max(1, int(risk_amount / point_risk)) if point_risk > 0 else 1

    # 保证金约束手数
    if margin > 0:
        max_margin_amount = account_equity * max_margin_pct
        contracts_margin = max(1, int(max_margin_amount / margin))
    else:
        contracts_margin = contracts_risk

    contracts = min(contracts_risk, contracts_margin)
    contracts = max(1, contracts)

    margin_used = contracts * margin
    notional_value = contracts * close * lot_size

    return {
        "contracts": contracts,
        "stop_pct": round(stop_pct * 100, 2),
        "stop_price": round(close * (1 - stop_pct), 2),
        "margin_used": round(margin_used, 0),
        "margin_pct": round(margin_used / account_equity * 100, 2),
        "notional_value": round(notional_value, 0),
        "leverage": round(notional_value / margin_used, 1) if margin_used > 0 else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="期货品种选择")
    parser.add_argument("--date", type=str, help="选品日期 (YYYY-MM-DD)")
    parser.add_argument("--top-n", type=int, default=3, help="每方向选品数 (默认 3)")
    parser.add_argument("--direction", type=str, default="both",
                        choices=["LONG", "SHORT", "both"],
                        help="选品方向")
    parser.add_argument("--min-score", type=float, default=0.45,
                        help="最低综合得分阈值 (默认 0.45)")
    parser.add_argument("--account-equity", type=float, default=10000000.0,
                        help="账户权益 (默认 10M USD)")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    factors_path = FACTORS_DIR / f"factors_{date_str}.csv"

    if not factors_path.exists():
        print(f"❌ 因子数据不存在: {factors_path}")
        print(f"   请先运行: python3.11 futures_factors.py --date {date_str}")
        sys.exit(1)

    df = pd.read_csv(factors_path)
    print(f"📊 期货选品 — {date_str}")
    print(f"   候选品种: {len(df)} | 方向: {args.direction} | Top-N: {args.top_n}")
    print()

    picks_long = []
    picks_short = []

    # LONG 候选
    if args.direction in ("LONG", "both"):
        df_long = df[df["momentum_10d"] > 0].sort_values("long_score", ascending=False)
        df_long = df_long[df_long["long_score"] >= args.min_score]

        for _, row in df_long.head(args.top_n).iterrows():
            pos = calc_position_suggestion(
                close=row["close"],
                lot_size=row["lot_size"],
                margin=row["long_margin"],
                volatility_20d=row["volatility_20d"],
                adx_14=row["adx_14"],
                account_equity=args.account_equity,
            )
            entry = {
                "code": row["code"],
                "name": row["name"],
                "direction": "LONG",
                "score": round(row["long_score"], 4),
                "close": row["close"],
                "momentum_10d": round(row["momentum_10d"], 4),
                "adx_14": round(row["adx_14"], 1),
                "volatility_20d": round(row["volatility_20d"], 4),
                **pos,
            }
            picks_long.append(entry)

    # SHORT 候选
    if args.direction in ("SHORT", "both"):
        # SHORT: 动量越小越好（越负越好）
        df_short = df.sort_values("short_score", ascending=False)
        df_short = df_short[df_short["short_score"] >= args.min_score]

        for _, row in df_short.head(args.top_n).iterrows():
            pos = calc_position_suggestion(
                close=row["close"],
                lot_size=row["lot_size"],
                margin=row["short_margin"],
                volatility_20d=row["volatility_20d"],
                adx_14=row["adx_14"],
                account_equity=args.account_equity,
            )
            entry = {
                "code": row["code"],
                "name": row["name"],
                "direction": "SHORT",
                "score": round(row["short_score"], 4),
                "close": row["close"],
                "momentum_10d": round(row["momentum_10d"], 4),
                "adx_14": round(row["adx_14"], 1),
                "volatility_20d": round(row["volatility_20d"], 4),
                **pos,
            }
            picks_short.append(entry)

    # 打印结果
    all_picks = picks_long + picks_short

    if picks_long:
        print(f"{'='*80}")
        print(f"📈 做多候选 (Long) — Top {len(picks_long)}")
        print(f"{'='*80}")
        print(f"{'代码':<18s} {'名称':<14s} {'得分':>7s} {'价格':>10s} {'手数':>4s} "
              f"{'止损%':>6s} {'止损价':>10s} {'保证金':>10s} {'保证金%':>7s} {'杠杆':>5s}")
        print("-" * 80)
        for p in picks_long:
            print(f"{p['code']:<18s} {p['name']:<14s} {p['score']:>7.4f} {p['close']:>10.1f} "
                  f"{p['contracts']:>4d} {p['stop_pct']:>5.1f}% {p['stop_price']:>10.1f} "
                  f"{p['margin_used']:>10.0f} {p['margin_pct']:>6.1f}% {p['leverage']:>5.1f}x")

    if picks_short:
        print(f"\n{'='*80}")
        print(f"📉 做空候选 (Short) — Top {len(picks_short)}")
        print(f"{'='*80}")
        print(f"{'代码':<18s} {'名称':<14s} {'得分':>7s} {'价格':>10s} {'手数':>4s} "
              f"{'止损%':>6s} {'止损价':>10s} {'保证金':>10s} {'保证金%':>7s} {'杠杆':>5s}")
        print("-" * 80)
        for p in picks_short:
            print(f"{p['code']:<18s} {p['name']:<14s} {p['score']:>7.4f} {p['close']:>10.1f} "
                  f"{p['contracts']:>4d} {p['stop_pct']:>5.1f}% {p['stop_price']:>10.1f} "
                  f"{p['margin_used']:>10.0f} {p['margin_pct']:>6.1f}% {p['leverage']:>5.1f}x")

    if not all_picks:
        print("⚠️ 无符合条件的候选（可能是全部动量偏多或得分不足）")

    # 汇总
    total_margin = sum(p["margin_used"] for p in all_picks)
    print(f"\n{'='*80}")
    print(f"📋 汇总: {len(all_picks)} 笔交易 | 总保证金: {total_margin:,.0f} "
          f"({total_margin/args.account_equity*100:.1f}% 权益)")
    if total_margin / args.account_equity > 0.60:
        print(f"⚠️ 总保证金比例 > 60%，建议减少手数或品种")

    # 保存
    if all_picks:
        df_out = pd.DataFrame(all_picks)
        output_path = FACTORS_DIR / f"pick_result_{date_str}.csv"
        df_out.to_csv(output_path, index=False)
        print(f"\n✅ 选品结果已保存: {output_path}")

    if args.json:
        print(json.dumps(all_picks, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
