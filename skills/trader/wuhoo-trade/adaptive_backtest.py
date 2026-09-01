#!/usr/bin/env python3.11
"""
自适应组合回测 — Adaptive Strategy Backtest

在每个回测期初，用当时可得的数据检测市场状态，自动选择对应策略。
对比自适应组合 vs 单一策略（超跌反弹 / 趋势动量）。

策略路由表:
  BULL_TRENDING  → trend_momentum (100%)
  BULL_VOLATILE  → trend_momentum (75%)
  RANGING        → oversold_rebound (80%)
  BEAR_VOLATILE  → defensive_50pct  (50%)
  BEAR_TRENDING  → cash_only (0%)

用法:
  python3.11 adaptive_backtest.py --market us --months 12
  python3.11 adaptive_backtest.py --market all --months 12
"""

import json, sys, argparse, os
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Import existing modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from market_regime import detect_regime, Regime, STRATEGY_MAP
from backtest import (
    load_market_data, compute_factors, select_stocks, compute_forward_returns,
    MARKET_DIRS, PNL_DIR,
)
from trend_momentum import (
    compute_momentum_factors, select_momentum_stocks,
)

HOME = Path.home()
DATA_DIR = HOME / "wuhoo-workspace" / "data" / "stock-pick"

# ────────────────────────────────────────────────────────────
# Position sizing by regime
# ────────────────────────────────────────────────────────────
REGIME_WEIGHT = {
    Regime.BULL_TRENDING: 1.00,
    Regime.BULL_VOLATILE: 0.75,
    Regime.RANGING: 0.80,
    Regime.BEAR_VOLATILE: 0.50,
    Regime.BEAR_TRENDING: 0.00,
}


def run_adaptive_backtest(
    market: str = "us",
    months: int = 12,
    top_n: int = 10,
    hold_days: int = 20,
    data_months: int = 18,
    regime_data_months: int = 12,
) -> dict:
    """
    自适应组合回测：每月检测市场状态 → 选择策略 → 计算收益。

    与单策略回测完全相同的 walk-forward 框架，
    区别在于每月选股前先调用 detect_regime。
    """
    print(f"\n{'='*70}")
    print(f"Adaptive Backtest: {market.upper()} | {months} months | Top {top_n} | Hold {hold_days}d")
    print(f"{'='*70}")

    # 生成测试日期（每月 15 日）
    today = date.today()
    test_dates = []
    for i in range(months, 0, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        test_dates.append(date(y, m, min(15, 28)))

    print(f"Test dates: {[d.isoformat() for d in test_dates]}")

    # 预加载全部数据
    all_data = load_market_data(market, months + data_months, today.isoformat())
    if all_data.empty:
        return {"error": "No market data", "market": market}
    print(f"Loaded {len(all_data)} rows, {all_data['code'].nunique()} stocks")

    monthly_results = []
    all_returns = []
    regime_history = []

    for ref_date in test_dates:
        ref_str = ref_date.isoformat()
        # Walk-forward: 只用 ref_date 之前的数据
        wf_data = all_data[all_data["date"] <= pd.to_datetime(ref_str)].copy()

        if len(wf_data) < 1000:
            print(f"  [{ref_str}] ⚠️  Insufficient data, skipping")
            continue

        # ── Step 1: 检测市场状态 ──
        regime_result = detect_regime(market, ref_date=ref_str, data_months=regime_data_months)
        regime = regime_result.get("regime", Regime.RANGING)
        composite = regime_result.get("composite_score", 0)
        confidence = regime_result.get("confidence", 0)

        # ── Step 2: 根据状态选择策略 ──
        if regime == Regime.BEAR_TRENDING:
            # 空仓月 — 收益为 0
            monthly_results.append({
                "ref_date": ref_str,
                "regime": str(regime),
                "composite": composite,
                "confidence": confidence,
                "strategy": "cash_only",
                "weight": 0.0,
                "n_selected": 0,
                "avg_return": 0.0,
                "win_rate": 0,
                "returns": {},
            })
            all_returns.append(0.0)
            regime_history.append(str(regime))
            print(f"  [{ref_str}] {regime} (comp={composite:+.2f}) → CASH_ONLY | Return: 0.00%")
            continue

        elif regime in (Regime.BULL_TRENDING, Regime.BULL_VOLATILE):
            # 趋势动量策略
            strategy_name = "trend_momentum"
            factors = compute_momentum_factors(wf_data)
            if factors.empty or len(factors) < top_n:
                print(f"  [{ref_str}] {regime} → momentum factors insufficient ({len(factors)} stocks), skipping")
                continue
            selected = select_momentum_stocks(factors, top_n)
            selected_codes = selected["code"].tolist()

        else:
            # RANGING / BEAR_VOLATILE → 超跌反弹
            strategy_name = "oversold_rebound"
            if regime == Regime.BEAR_VOLATILE:
                strategy_name = "defensive_50pct"
            factors = compute_factors(wf_data, market)
            if factors.empty or len(factors) < top_n:
                print(f"  [{ref_str}] {regime} → contrarian factors insufficient ({len(factors)} stocks), skipping")
                continue
            sel = select_stocks(factors, top_n)
            selected_codes = sel["code"].tolist()

        # ── Step 3: 计算前向收益 ──
        fwd = compute_forward_returns(all_data, selected_codes, ref_str, hold_days)

        # ── Step 4: 应用仓位权重 ──
        weight = REGIME_WEIGHT.get(regime, 0.80)
        weighted_return = fwd["avg_return"] * weight

        result = {
            "ref_date": ref_str,
            "regime": str(regime),
            "composite": composite,
            "confidence": confidence,
            "strategy": strategy_name,
            "weight": weight,
            "n_selected": len(selected_codes),
            "raw_avg_return": fwd["avg_return"],
            "avg_return": round(weighted_return, 2),
            "win_rate": fwd["win_rate"],
            "returns": fwd["returns"],
        }
        monthly_results.append(result)
        all_returns.append(weighted_return)
        regime_history.append(str(regime))

        print(f"  [{ref_str}] {regime} (comp={composite:+.2f}, conf={confidence:.2f}) "
              f"→ {strategy_name} (wt={weight:.0%}) | "
              f"Raw: {fwd['avg_return']:+.2f}% → Wtd: {weighted_return:+.2f}% | "
              f"Win: {fwd['win_rate']:.0f}% | "
              f"Stocks: {selected_codes[:3]}...")

    # ── 汇总统计 ──
    if not all_returns:
        return {"error": "No valid backtest results", "market": market}

    valid_returns = all_returns
    avg_monthly = np.mean(valid_returns)
    win_months = sum(1 for r in valid_returns if r > 0)
    best = max(valid_returns)
    worst = min(valid_returns)
    std_returns = np.std(valid_returns)
    sharpe_monthly = avg_monthly / std_returns if std_returns > 0 else 0

    # Equity curve
    equity = 100.0
    equity_curve = []
    for r in valid_returns:
        equity *= (1 + r / 100)
        equity_curve.append(round(equity, 2))

    # Regime distribution
    from collections import Counter
    regime_dist = dict(Counter(regime_history))

    summary = {
        "market": market,
        "strategy": "adaptive",
        "parameters": {
            "top_n": top_n,
            "hold_days": hold_days,
            "months_tested": len(valid_returns),
            "data_months": data_months,
            "regime_data_months": regime_data_months,
        },
        "results": {
            "monthly_avg_return_pct": round(float(avg_monthly), 2),
            "monthly_win_rate_pct": round(win_months / len(valid_returns) * 100, 1),
            "best_month_pct": round(float(best), 2),
            "worst_month_pct": round(float(worst), 2),
            "std_monthly_pct": round(float(std_returns), 2),
            "sharpe_monthly": round(float(sharpe_monthly), 3),
            "total_cumulative_return_pct": round(
                float(np.prod([1 + r / 100 for r in valid_returns]) - 1) * 100, 2
            ),
        },
        "regime_distribution": regime_dist,
        "equity_curve": equity_curve,
        "monthly_details": monthly_results,
    }

    print(f"\n{'='*70}")
    print(f"ADAPTIVE SUMMARY: {market.upper()}")
    print(f"{'='*70}")
    print(f"Periods: {len(valid_returns)} months")
    print(f"Avg Monthly Return: {avg_monthly:.2f}%")
    print(f"Win Rate: {win_months}/{len(valid_returns)} ({win_months/len(valid_returns)*100:.1f}%)")
    print(f"Best Month: {best:.2f}%")
    print(f"Worst Month: {worst:.2f}%")
    print(f"Sharpe (monthly): {sharpe_monthly:.3f}")
    print(f"Cumulative Return: {summary['results']['total_cumulative_return_pct']:.2f}%")
    print(f"Regime Distribution: {regime_dist}")
    print(f"Equity Curve: {equity_curve}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Adaptive strategy backtest")
    parser.add_argument("--market", default="us", choices=["us", "hk", "cn", "all"])
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--hold-days", type=int, default=20)
    parser.add_argument("--data-months", type=int, default=18)
    parser.add_argument("--regime-data-months", type=int, default=12,
                        help="Months of data for regime detection")
    args = parser.parse_args()

    markets = ["us", "hk", "cn"] if args.market == "all" else [args.market]

    all_results = {}
    for mkt in markets:
        result = run_adaptive_backtest(
            market=mkt, months=args.months, top_n=args.top_n,
            hold_days=args.hold_days, data_months=args.data_months,
            regime_data_months=args.regime_data_months,
        )
        all_results[mkt] = result

    # Save
    PNL_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PNL_DIR / f"backtest_adaptive_{args.market}_{date.today().isoformat()}.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()
