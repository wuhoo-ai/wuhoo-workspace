#!/usr/bin/env python3.11
"""
多策略回测模块 — 4 种新策略的 walk-forward 回测

策略清单:
  1. dual_momentum     — 双动量 (12月相对动量 + SMA200绝对过滤)
  2. bollinger_reversal — 布林带均值回归 (触及下轨 + RSI<30)
  3. smallcap_reversal  — 小市值反转 (最小市值30% + 5日最大跌幅)
  4. hk_large_momentum  — 港股大盘动量 (Top 30市值 + 10日正动量)

用法:
  python3.11 strategies.py --strategy dual_momentum --market us --months 12
  python3.11 strategies.py --strategy bollinger_reversal --market cn --months 12
  python3.11 strategies.py --strategy smallcap_reversal --market cn --months 12
  python3.11 strategies.py --strategy hk_large_momentum --market hk --months 12
  python3.11 strategies.py --strategy all --market all --months 12
"""

import json, sys, argparse, os
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import (
    load_market_data, compute_forward_returns,
    MARKET_DIRS, PNL_DIR,
)

HOME = Path.home()
DATA_DIR = HOME / "wuhoo-workspace" / "data" / "stock-pick"

# ═══════════════════════════════════════════════════════════════
# 通用工具
# ═══════════════════════════════════════════════════════════════

def _price_col(data):
    for c in ["close", "Close", "closing_price"]:
        if c in data.columns:
            return c
    return None

def _vol_col(data):
    for c in ["volume", "Volume", "vol"]:
        if c in data.columns:
            return c
    return None

def _get_stock_series(data, code, pc):
    """获取单只股票的收盘价序列"""
    s = data[data["code"] == code].sort_values("date")
    if len(s) < 60:
        return None
    return s[pc].values

def _load_hk_market_cap():
    """加载港股总市值 (HKD)"""
    cap_file = DATA_DIR / "stock_info_hk_top500.csv"
    if not cap_file.exists():
        return {}
    df = pd.read_csv(cap_file)
    caps = {}
    for _, row in df.iterrows():
        caps[row.get("code", row.get("ts_code", ""))] = float(row.get("total_market_val", 0))
    return caps

def _avg_volume_proxy(data, pc, vc):
    """用平均成交额 (price × volume) 作为市值代理"""
    proxies = {}
    for code in data["code"].unique():
        s = data[data["code"] == code]
        if len(s) >= 20:
            avg_val = (s[pc].iloc[-20:] * s[vc].iloc[-20:]).mean() if vc else s[pc].iloc[-20:].mean() * 1e6
        else:
            avg_val = 0
        proxies[code] = avg_val
    return proxies


# ═══════════════════════════════════════════════════════════════
# Strategy 1: Dual Momentum
# ═══════════════════════════════════════════════════════════════

def dual_momentum_select(data, top_n=10):
    """
    双动量选股:
    1. 相对动量: 过去12个月收益排名前 30%
    2. 绝对动量过滤: 价格必须 > SMA(200)
    3. 按相对动量降序取 Top N
    """
    pc = _price_col(data)
    if not pc:
        return pd.DataFrame()

    codes = data["code"].unique()
    scores = []

    for code in codes:
        closes = _get_stock_series(data, code, pc)
        if closes is None or len(closes) < 252:
            continue

        # 12-month relative momentum
        mom_12m = (closes[-1] / closes[-252] - 1) * 100 if len(closes) >= 252 else 0

        # Absolute momentum: SMA(200)
        if len(closes) >= 200:
            sma200 = np.mean(closes[-200:])
            above_sma = closes[-1] > sma200
        else:
            above_sma = False

        if above_sma:  # 绝对动量过滤
            scores.append({
                "code": code,
                "momentum_12m": round(mom_12m, 2),
                "last_price": round(closes[-1], 2),
            })

    if not scores:
        return pd.DataFrame()

    df = pd.DataFrame(scores)
    # 相对动量前 30% (至少 30 只)
    cutoff_idx = max(int(len(df) * 0.3), min(30, len(df)))
    df = df.nlargest(cutoff_idx, "momentum_12m")

    return df.nlargest(min(top_n, len(df)), "momentum_12m")


# ═══════════════════════════════════════════════════════════════
# Strategy 2: Bollinger Mean Reversion
# ═══════════════════════════════════════════════════════════════

def _rsi(closes, period=14):
    """计算 RSI"""
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def bollinger_reversal_select(data, top_n=10):
    """
    布林带均值回归:
    1. 价格触及或跌破布林下轨 (2σ)
    2. RSI(14) < 30 确认超卖
    3. 按 (下轨偏离度) 升序 → 跌越深越优先
    """
    pc = _price_col(data)
    if not pc:
        return pd.DataFrame()

    codes = data["code"].unique()
    candidates = []

    for code in codes:
        closes = _get_stock_series(data, code, pc)
        if closes is None or len(closes) < 30:
            continue

        # Bollinger Bands (20日, 2σ)
        window = 20
        if len(closes) < window:
            continue
        recent = closes[-window:]
        sma = np.mean(recent)
        std = np.std(recent)
        lower_band = sma - 2 * std
        current = closes[-1]

        # Condition: price at or below lower band
        touch_lower = current <= lower_band

        # RSI < 30
        rsi_val = 50.0  # default
        if len(closes) >= 14:
            rsi_val = _rsi(closes)
            oversold = rsi_val < 30
        else:
            oversold = False

        if touch_lower and oversold:
            # Deviation from lower band (negative = below band)
            deviation = (current - lower_band) / sma * 100
            candidates.append({
                "code": code,
                "last_price": round(current, 2),
                "lower_band": round(lower_band, 2),
                "deviation_pct": round(deviation, 2),
                "rsi": round(rsi_val, 1),
            })

    if not candidates:
        return pd.DataFrame()

    df = pd.DataFrame(candidates)
    # 偏离度越小（越低于下轨）越好
    return df.nsmallest(min(top_n, len(df)), "deviation_pct")


# ═══════════════════════════════════════════════════════════════
# Strategy 3: Small-cap Reversal (CN)
# ═══════════════════════════════════════════════════════════════

def smallcap_reversal_select(data, top_n=10):
    """
    小市值反转:
    1. 用平均成交额作为市值代理 → 筛选最小 30%
    2. 5日动量升序 → 跌最狠的优先
    3. 取 Top N
    """
    pc = _price_col(data)
    vc = _vol_col(data)
    if not pc:
        return pd.DataFrame()

    # 市值代理
    cap_proxy = _avg_volume_proxy(data, pc, vc)
    if not cap_proxy:
        return pd.DataFrame()

    cutoff = np.percentile(list(cap_proxy.values()), 30)
    small_caps = {k: v for k, v in cap_proxy.items() if v <= cutoff and v > 0}

    codes = data["code"].unique()
    scores = []

    for code in codes:
        if code not in small_caps:
            continue
        closes = _get_stock_series(data, code, pc)
        if closes is None or len(closes) < 10:
            continue

        # 5日动量
        mom_5d = (closes[-1] / closes[-6] - 1) * 100 if len(closes) >= 6 else 0

        scores.append({
            "code": code,
            "momentum_5d": round(mom_5d, 2),
            "last_price": round(closes[-1], 2),
            "cap_proxy": round(cap_proxy[code], 0),
        })

    if not scores:
        return pd.DataFrame()

    df = pd.DataFrame(scores)
    # 按动量升序 = 跌最狠的在前
    return df.nsmallest(min(top_n, len(df)), "momentum_5d")


# ═══════════════════════════════════════════════════════════════
# Strategy 4: HK Large-cap Head Momentum
# ═══════════════════════════════════════════════════════════════

def hk_large_momentum_select(data, top_n=10, top_mcap=30):
    """
    港股大盘头部动量:
    1. 从 stock_info_hk_top500.csv 加载市值
    2. 按总市值排序取 Top N (默认30)
    3. 在这些头部股中筛 10日动量 > 0
    4. 按 10日动量降序选股
    """
    pc = _price_col(data)
    if not pc:
        return pd.DataFrame()

    caps = _load_hk_market_cap()
    if not caps:
        print("  ⚠️  No HK market cap data, using volume proxy")
        vc = _vol_col(data)
        caps = _avg_volume_proxy(data, pc, vc)

    # Filter to data codes that have market cap
    data_codes = set(data["code"].unique())
    eligible = [(code, cap) for code, cap in caps.items() if code in data_codes and cap > 0]
    eligible.sort(key=lambda x: x[1], reverse=True)
    large_caps = set(code for code, _ in eligible[:top_mcap])

    scores = []
    for code in large_caps:
        closes = _get_stock_series(data, code, pc)
        if closes is None or len(closes) < 15:
            continue

        # 10日动量
        mom_10d = (closes[-1] / closes[-11] - 1) * 100 if len(closes) >= 11 else 0

        # 仅选正动量
        if mom_10d > 0:
            scores.append({
                "code": code,
                "momentum_10d": round(mom_10d, 2),
                "last_price": round(closes[-1], 2),
            })

    if not scores:
        return pd.DataFrame()

    df = pd.DataFrame(scores)
    return df.nlargest(min(top_n, len(df)), "momentum_10d")


# ═══════════════════════════════════════════════════════════════
# Backtest Runner
# ═══════════════════════════════════════════════════════════════

STRATEGIES = {
    "dual_momentum": {
        "fn": dual_momentum_select,
        "name": "Dual Momentum (12M relative + SMA200)",
        "description": "12个月相对动量排名前30% + 绝对动量过滤(价>SMA200)",
    },
    "bollinger_reversal": {
        "fn": bollinger_reversal_select,
        "name": "Bollinger Mean Reversion",
        "description": "触及布林下轨(2σ) + RSI<30 超卖反弹",
    },
    "smallcap_reversal": {
        "fn": smallcap_reversal_select,
        "name": "Small-cap Reversal",
        "description": "最小市值30% + 5日最大跌幅反转",
    },
    "hk_large_momentum": {
        "fn": hk_large_momentum_select,
        "name": "HK Large-cap Momentum",
        "description": "港股Top 30市值 + 10日正动量",
    },
}


def run_strategy_backtest(
    strategy: str,
    market: str = "us",
    months: int = 12,
    top_n: int = 10,
    hold_days: int = 20,
    data_months: int = 18,
) -> dict:
    """通用策略回测框架"""
    strat_info = STRATEGIES[strategy]
    select_fn = strat_info["fn"]

    print(f"\n{'='*70}")
    print(f"Strategy: {strat_info['name']} | {market.upper()} | {months}m | Top {top_n} | Hold {hold_days}d")
    print(f"{'='*70}")

    today = date.today()
    test_dates = []
    for i in range(months, 0, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        test_dates.append(date(y, m, min(15, 28)))

    all_data = load_market_data(market, months + data_months, today.isoformat())
    if all_data.empty:
        return {"error": "No market data", "market": market}
    n_stocks = all_data["code"].nunique()
    print(f"Loaded {len(all_data)} rows, {n_stocks} stocks")

    monthly_results = []
    all_returns = []

    for ref_date in test_dates:
        ref_str = ref_date.isoformat()
        wf_data = all_data[all_data["date"] <= pd.to_datetime(ref_str)].copy()

        if len(wf_data) < 1000:
            continue

        selected = select_fn(wf_data, top_n)
        if selected.empty or len(selected) < 3:
            continue

        codes = selected["code"].tolist()
        fwd = compute_forward_returns(all_data, codes, ref_str, hold_days)

        result = {
            "ref_date": ref_str,
            "n_selected": len(codes),
            "avg_return": fwd["avg_return"],
            "win_rate": fwd["win_rate"],
            "returns": fwd["returns"],
        }
        monthly_results.append(result)
        all_returns.append(fwd["avg_return"])

        print(f"  [{ref_str}] Return: {fwd['avg_return']:+.2f}% | "
              f"Win: {fwd['win_rate']:.0f}% | "
              f"Stocks: {codes[:3]}...")

    if not all_returns:
        return {"error": "No valid results", "market": market}

    valid = all_returns
    avg_m = np.mean(valid)
    win_m = sum(1 for r in valid if r > 0)
    best = max(valid)
    worst = min(valid)
    std_r = np.std(valid)
    sharpe = avg_m / std_r if std_r > 0 else 0
    cum_ret = np.prod([1 + r/100 for r in valid]) - 1

    # Equity curve
    equity = 100.0
    equity_curve = []
    for r in valid:
        equity *= (1 + r / 100)
        equity_curve.append(round(equity, 2))

    summary = {
        "strategy": strategy,
        "market": market,
        "parameters": {"top_n": top_n, "hold_days": hold_days, "months": len(valid)},
        "results": {
            "monthly_avg_return_pct": round(float(avg_m), 2),
            "monthly_win_rate_pct": round(win_m / len(valid) * 100, 1),
            "best_month_pct": round(float(best), 2),
            "worst_month_pct": round(float(worst), 2),
            "std_monthly_pct": round(float(std_r), 2),
            "sharpe_monthly": round(float(sharpe), 3),
            "total_cumulative_return_pct": round(float(cum_ret) * 100, 2),
        },
        "equity_curve": equity_curve,
        "monthly_details": monthly_results,
    }

    print(f"\n  Avg Monthly: {avg_m:+.2f}% | Win: {win_m}/{len(valid)} "
          f"({win_m/len(valid)*100:.0f}%) | Sharpe: {sharpe:.3f} | "
          f"Cumulative: {cum_ret*100:+.2f}%")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Multi-strategy backtest suite")
    parser.add_argument("--strategy", default="dual_momentum",
                        choices=list(STRATEGIES.keys()) + ["all"])
    parser.add_argument("--market", default="us", choices=["us", "hk", "cn", "all"])
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--hold-days", type=int, default=20)
    parser.add_argument("--data-months", type=int, default=18)
    args = parser.parse_args()

    strategies = list(STRATEGIES.keys()) if args.strategy == "all" else [args.strategy]
    markets = ["us", "hk", "cn"] if args.market == "all" else [args.market]

    # Smart defaults: some strategies only make sense for specific markets
    strategy_market_map = {
        "dual_momentum": ["us"],
        "bollinger_reversal": ["us", "cn"],
        "smallcap_reversal": ["cn"],
        "hk_large_momentum": ["hk"],
    }

    all_results = {}
    for strat in strategies:
        # If user passed --market all, restrict to applicable markets
        if args.market == "all":
            applicable = strategy_market_map.get(strat, ["us", "hk", "cn"])
            applicable = [m for m in applicable if m in markets]
        else:
            applicable = markets

        for mkt in applicable:
            key = f"{mkt}_{strat}"
            result = run_strategy_backtest(
                strategy=strat, market=mkt, months=args.months,
                top_n=args.top_n, hold_days=args.hold_days,
                data_months=args.data_months,
            )
            all_results[key] = result

    # Save
    PNL_DIR.mkdir(parents=True, exist_ok=True)
    ts = date.today().isoformat()
    output_path = PNL_DIR / f"strategies_{args.strategy}_{args.market}_{ts}.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()
