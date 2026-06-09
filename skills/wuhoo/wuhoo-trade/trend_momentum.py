#!/usr/bin/env python3.11
"""
趋势动量策略 — 与超跌反弹互补的选股模块

策略逻辑:
  相反于超跌反弹（买跌最狠的），趋势动量买涨最多的：
  1. 筛选过去 N 日表现最强的股票（动量因子）
  2. 辅以成交量确认（放量上涨）
  3. 高 Beta 保证弹性
  4. 相对强度排序

适用市场环境:
  - BULL: 趋势动量在牛市中跑赢超跌反弹
  - RANGING: 两者均可
  - BEAR: 趋势动量容易追高被套，应降仓或切换

因子:
  1. momentum_10d — 10日动量，越高越好
  2. momentum_20d — 20日动量，越高越好 (P50)
  3. momentum_60d — 60日动量，越高越好 (P30)
  4. volume_ratio_5d20d — 短期/中期成交量比 > 1.0 (确认放量)
  5. beta_20d — 高 Beta (P20, 硬地板 1.0)
  6. relative_strength — 相对基准强度，越高越好

排序: momentum_10d 降序（涨最多的在前）

用法:
  python3.11 trend_momentum.py --market us --months 12
  python3.11 trend_momentum.py --market all --months 12
"""

import json, sys, argparse
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HOME = Path.home()
DATA_DIR = HOME / "wuhoo-workspace" / "data" / "stock-pick"
PNL_DIR = HOME / "wuhoo-workspace" / "data" / "pnl"

MARKET_DIRS = {
    "us": DATA_DIR / "daily_data_us",
    "hk": DATA_DIR / "daily_data_hk",
    "cn": DATA_DIR / "daily_data",
}

MOMENTUM_FACTORS = ["momentum_10d", "momentum_20d", "momentum_60d",
                    "volume_ratio", "beta_20d", "relative_strength"]


def _normalize_columns(df: pd.DataFrame):
    """从 backtest.py 复用的列名规范化（保持一致性）"""
    for src in ["trade_date", "time_key", "Date"]:
        if src in df.columns:
            df = df.rename(columns={src: "date"})
            break
    if "date" not in df.columns:
        return None
    df = df.dropna(subset=["date"])
    if df.empty:
        return None
    try:
        if pd.api.types.is_integer_dtype(df["date"]) or pd.api.types.is_float_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
        else:
            df["date"] = pd.to_datetime(df["date"], format="mixed")
    except Exception:
        try:
            df["date"] = pd.to_datetime(df["date"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2})")[0])
        except Exception:
            try:
                df["date"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
            except Exception:
                return None
    for src in ["ts_code"]:
        if src in df.columns:
            df = df.rename(columns={src: "code"})
            break
    if "code" not in df.columns:
        return None
    for src in ["Close"]:
        if src in df.columns:
            df = df.rename(columns={src: "close"})
            break
    if "close" not in df.columns:
        return None
    for src in ["Volume"]:
        if src in df.columns and "volume" not in df.columns:
            df = df.rename(columns={src: "volume"})
    return df


def load_market_data(market: str, months_back: int, ref_date: str) -> pd.DataFrame:
    """加载 ref_date 之前 months_back 个月的日线数据"""
    data_dir = MARKET_DIRS[market]
    if not data_dir.exists():
        return pd.DataFrame()
    ref_dt = pd.to_datetime(ref_date)
    start_dt = ref_dt - pd.DateOffset(months=months_back)
    all_data = []
    for year_dir in sorted(data_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        for csv_file in sorted(year_dir.glob("*.csv")):
            try:
                month_str = csv_file.stem
                month_dt = pd.to_datetime(month_str, format="%Y%m")
                if month_dt <= ref_dt and month_dt >= start_dt.replace(day=1):
                    df = pd.read_csv(csv_file)
                    df = _normalize_columns(df)
                    if df is not None and not df.empty:
                        all_data.append(df)
            except Exception:
                continue
    if not all_data:
        return pd.DataFrame()
    return pd.concat(all_data, ignore_index=True)


def compute_momentum_factors(market_data: pd.DataFrame) -> pd.DataFrame:
    """
    计算趋势动量策略所需因子。

    与超跌反弹的因子相同但排序和阈值方向相反：
    - momentum 越高越好（而非越低越好）
    - volume_ratio 确认放量（而非缩量）
    - beta 仍要求高 Beta
    """
    if market_data.empty:
        return pd.DataFrame()

    codes = market_data["code"].unique()
    results = []

    price_cols = [c for c in market_data.columns if c.lower() in ("close", "closing_price")]
    if not price_cols:
        return pd.DataFrame()
    price_col = price_cols[0]

    vol_cols = [c for c in market_data.columns if c.lower() in ("volume", "vol")]
    vol_col = vol_cols[0] if vol_cols else None

    # 基准（等权平均）
    daily_close = market_data.groupby("date")[price_col].mean().sort_index()
    benchmark_returns = daily_close.pct_change().dropna()

    for code in codes:
        try:
            stock_data = market_data[market_data["code"] == code].sort_values("date")
            if len(stock_data) < 252:
                continue

            closes = stock_data[price_col].values

            # 动量因子
            if len(closes) >= 11:
                momentum_10d = (closes[-1] / closes[-11] - 1) * 100
            else:
                momentum_10d = 0

            if len(closes) >= 21:
                momentum_20d = (closes[-1] / closes[-21] - 1) * 100
            else:
                momentum_20d = 0

            if len(closes) >= 61:
                momentum_60d = (closes[-1] / closes[-61] - 1) * 100
            else:
                momentum_60d = 0

            # 成交量比率（短期放量确认）
            if vol_col and len(stock_data) >= 20:
                avg_vol_5d = np.mean(stock_data[vol_col].values[-5:]) if len(stock_data) >= 5 else 1
                avg_vol_20d = np.mean(stock_data[vol_col].values[-20:])
                volume_ratio = avg_vol_5d / avg_vol_20d if avg_vol_20d > 0 else 1.0
            else:
                volume_ratio = 1.0

            # 20日 Beta
            returns = np.diff(closes) / closes[:-1]
            if len(returns) >= 20:
                stock_ret_20 = returns[-20:]
                bm_ret_20 = benchmark_returns.iloc[-20:]
                if len(bm_ret_20) >= 20 and np.std(bm_ret_20) > 0:
                    beta_20d = np.cov(stock_ret_20, bm_ret_20)[0, 1] / np.var(bm_ret_20)
                else:
                    beta_20d = 1.0
            else:
                beta_20d = 1.0

            # 相对强度（相对基准的超额收益）
            if len(returns) >= 20:
                stock_cum = np.prod(1 + returns[-20:]) - 1
                bm_cum = np.prod(1 + benchmark_returns.iloc[-20:].values[:len(returns[-20:])]) - 1
                relative_strength = (stock_cum - bm_cum) * 100
            else:
                relative_strength = 0

            results.append({
                "code": code,
                "momentum_10d": momentum_10d,
                "momentum_20d": momentum_20d,
                "momentum_60d": momentum_60d,
                "volume_ratio": volume_ratio,
                "beta_20d": beta_20d,
                "relative_strength": relative_strength,
                "last_price": closes[-1],
            })
        except Exception:
            continue

    return pd.DataFrame(results)


def select_momentum_stocks(factors_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    趋势动量选股逻辑:
    1. momentum_10d > 0（必须处于上升趋势）
    2. momentum_60d > P50（中期趋势向好）
    3. volume_ratio > 0.8（避免缩量）
    4. beta_20d > max(P20, 1.0)（高弹性）
    5. 按 momentum_10d 降序排序 → 取 Top N
    """
    if factors_df.empty or len(factors_df) < top_n:
        return factors_df

    df = factors_df.copy()

    # 硬性约束：10日动量必须为正
    df = df[df["momentum_10d"] > 0]
    if len(df) < top_n:
        # 牛市末期可能没有正动量股票，放宽条件
        df = factors_df.copy()

    if len(df) < top_n:
        return df.nlargest(top_n, "momentum_10d")

    # 分位阈值（与超跌反弹相反的方向）
    p50_mom60 = df["momentum_60d"].quantile(0.50)
    p20_beta = df["beta_20d"].quantile(0.20)

    # 应用筛选
    filtered = df[
        (df["momentum_60d"] >= p50_mom60) &
        (df["volume_ratio"] >= 0.8) &
        (df["beta_20d"] >= max(p20_beta, 1.0))
    ]

    if len(filtered) < top_n:
        # 放宽：只保留 momentum_10d > 0 + volume
        filtered = df[
            (df["momentum_10d"] > 0) &
            (df["volume_ratio"] >= 0.6)
        ]

    if len(filtered) < top_n:
        filtered = df

    # 按 momentum_10d 降序（涨最多的在前）
    result = filtered.nlargest(top_n, "momentum_10d")
    return result


def compute_forward_returns(market_data, selected_codes, ref_date, hold_days=20):
    """计算入选股票的前向收益。复用 backtest.py 逻辑。"""
    ref_dt = pd.to_datetime(ref_date)
    end_dt = ref_dt + pd.DateOffset(days=hold_days + 5)

    price_col = [c for c in market_data.columns if c.lower() in ("close", "closing_price")]
    if not price_col:
        return {"avg_return": 0, "win_rate": 0, "returns": {}, "n_valid": 0}
    price_col = price_col[0]

    returns = {}
    for code in selected_codes:
        try:
            stock_data = market_data[
                (market_data["code"] == code) &
                (market_data["date"] >= ref_dt) &
                (market_data["date"] <= end_dt)
            ].sort_values("date")

            if len(stock_data) < 2:
                returns[code] = None
                continue

            entry_price = stock_data[price_col].iloc[0]
            future = stock_data[stock_data["date"] > ref_dt + pd.DateOffset(days=hold_days - 3)]
            exit_price = future[price_col].iloc[0] if len(future) > 0 else stock_data[price_col].iloc[-1]

            ret = (exit_price / entry_price - 1) * 100
            returns[code] = round(float(ret), 2)
        except Exception:
            returns[code] = None

    valid_returns = [r for r in returns.values() if r is not None]
    avg_return = np.mean(valid_returns) if valid_returns else 0
    winners = sum(1 for r in valid_returns if r > 0)

    return {
        "avg_return": round(float(avg_return), 2),
        "win_rate": round(winners / len(valid_returns) * 100, 1) if valid_returns else 0,
        "returns": returns,
        "n_valid": len(valid_returns),
        "n_total": len(selected_codes),
    }


def run_momentum_backtest(market="us", months=12, top_n=10, hold_days=20, data_months=18):
    """执行趋势动量策略的 walk-forward 回测"""
    print(f"\n{'='*60}")
    print(f"Trend Momentum Backtest: {market.upper()} | {months}m | Top {top_n} | Hold {hold_days}d")
    print(f"{'='*60}")

    today = date.today()
    test_dates = []
    for i in range(months, 0, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        test_dates.append(date(year, month, min(15, 28)))

    print(f"Test dates: {[d.isoformat() for d in test_dates]}")

    all_data = load_market_data(market, months + data_months, today.isoformat())
    if all_data.empty:
        return {"error": "No market data", "market": market}

    print(f"Loaded {len(all_data)} rows, {all_data['code'].nunique()} stocks")

    monthly_results = []
    all_returns = []

    for ref_date in test_dates:
        ref_str = ref_date.isoformat()
        print(f"\n--- {ref_str} ---")

        wf_data = all_data[all_data["date"] <= pd.to_datetime(ref_str)].copy()
        if len(wf_data) < 1000:
            print(f"  ⚠️  Insufficient data ({len(wf_data)} rows), skipping")
            continue

        factors = compute_momentum_factors(wf_data)
        if factors.empty or len(factors) < top_n:
            print(f"  ⚠️  Only {len(factors)} stocks, skipping")
            continue

        selected = select_momentum_stocks(factors, top_n)
        selected_codes = selected["code"].tolist()
        print(f"  Selected: {selected_codes[:5]}...")
        if len(selected) > 0:
            avg_mom10 = selected["momentum_10d"].mean()
            print(f"  Avg Mom10: {avg_mom10:.1f}% | Avg Mom60: {selected['momentum_60d'].mean():.1f}%")

        fwd = compute_forward_returns(all_data, selected_codes, ref_str, hold_days)
        monthly_results.append({
            "ref_date": ref_str,
            "n_stocks_filtered": len(factors),
            "n_selected": len(selected_codes),
            "avg_return": fwd["avg_return"],
            "win_rate": fwd["win_rate"],
            "returns": fwd["returns"],
        })
        all_returns.append(fwd["avg_return"])
        print(f"  Return: {fwd['avg_return']}% | Win: {fwd['win_rate']}% | Valid: {fwd['n_valid']}/{fwd['n_total']}")

    if not all_returns:
        return {"error": "No valid results", "market": market}

    valid_returns = [r for r in all_returns if r is not None]
    avg_monthly = np.mean(valid_returns)
    win_months = sum(1 for r in valid_returns if r > 0)
    std_returns = np.std(valid_returns)
    sharpe = avg_monthly / std_returns if std_returns > 0 else 0

    # Equity curve
    equity = 100.0
    equity_curve = []
    for r in valid_returns:
        equity *= (1 + r / 100)
        equity_curve.append(round(equity, 2))

    summary = {
        "market": market,
        "strategy": "trend_momentum",
        "parameters": {"top_n": top_n, "hold_days": hold_days, "months_tested": len(valid_returns)},
        "results": {
            "monthly_avg_return_pct": round(float(avg_monthly), 2),
            "monthly_win_rate_pct": round(win_months / len(valid_returns) * 100, 1),
            "best_month_pct": round(float(max(valid_returns)), 2),
            "worst_month_pct": round(float(min(valid_returns)), 2),
            "std_monthly_pct": round(float(std_returns), 2),
            "sharpe_monthly": round(float(sharpe), 3),
            "total_cumulative_return_pct": round(float(np.prod([1 + r/100 for r in valid_returns]) - 1) * 100, 2),
        },
        "monthly_details": monthly_results,
        "equity_curve": equity_curve,
    }

    print(f"\n{'='*60}")
    print(f"SUMMARY: Trend Momentum — {market.upper()}")
    print(f"{'='*60}")
    print(f"Avg Monthly: {avg_monthly:.2f}% | Win: {win_months}/{len(valid_returns)} ({win_months/len(valid_returns)*100:.1f}%)")
    print(f"Best: {max(valid_returns):.2f}% | Worst: {min(valid_returns):.2f}%")
    print(f"Sharpe: {sharpe:.3f} | Cumulative: {summary['results']['total_cumulative_return_pct']:.2f}%")
    print(f"Equity: {equity_curve}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Trend Momentum Backtest")
    parser.add_argument("--market", default="us", choices=["us", "hk", "cn", "all"])
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--hold-days", type=int, default=20)
    parser.add_argument("--output", type=str, default=None, help="JSON output path")
    args = parser.parse_args()

    markets = ["us", "hk", "cn"] if args.market == "all" else [args.market]
    all_results = {}

    for mkt in markets:
        result = run_momentum_backtest(
            market=mkt, months=args.months, top_n=args.top_n,
            hold_days=args.hold_days
        )
        all_results[mkt] = result

    # Compare with contrarian results if available
    PNL_DIR.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()
    output_path = args.output or str(PNL_DIR / f"backtest_momentum_{args.market}_{today_str}.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nSaved: {output_path}")

    # Quick comparison
    if args.market != "all":
        print(f"\n{'='*60}")
        print(f"STRATEGY COMPARISON QUICK REFERENCE")
        print(f"{'='*60}")
        for mkt in markets:
            r = all_results.get(mkt, {}).get("results", {})
            print(f"{mkt.upper()} Momentum: Sharpe={r.get('sharpe_monthly','N/A')}, "
                  f"CumReturn={r.get('total_cumulative_return_pct','N/A')}%, "
                  f"WinRate={r.get('monthly_win_rate_pct','N/A')}%")


if __name__ == "__main__":
    main()
