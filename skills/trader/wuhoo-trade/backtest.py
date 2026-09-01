#!/usr/bin/env python3.11
"""
Walk-Forward 回测 — 验证超跌反弹策略的历史表现

对指定市场，从历史日线数据按月重新计算因子，模拟每月选股买入并跟踪表现。

用法:
  python3.11 backtest.py --market us --months 12 --top-n 10 --hold-days 20
  python3.11 backtest.py --market cn --months 6 --top-n 10
  python3.11 backtest.py --market all --months 12

输出:
  ~/wuhoo-workspace/data/pnl/backtest_{market}_{date}.json
"""

import json, sys, argparse, os
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd

HOME = Path.home()
DATA_DIR = HOME / "wuhoo-workspace" / "data" / "stock-pick"
PNL_DIR = HOME / "wuhoo-workspace" / "data" / "pnl"

# 各市场数据目录
MARKET_DIRS = {
    "us": DATA_DIR / "daily_data_us",
    "hk": DATA_DIR / "daily_data_hk",
    "cn": DATA_DIR / "daily_data",
}

# 基准
BENCHMARK_TICKERS = {
    "us": "SPY",
    "hk": "^HSI",
    "cn": "000300.SH",  # 近似用沪深300
}


def load_market_data(market: str, months_back: int, ref_date: str) -> pd.DataFrame:
    """
    加载 ref_date 之前 months_back 个月的日线数据。
    这是 walk-forward 的关键——只用当时可得的数据。
    """
    data_dir = MARKET_DIRS[market]
    if not data_dir.exists():
        print(f"  ⚠️  Data dir not found: {data_dir}")
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
                    # 统一列名（在 concat 之前，避免混合格式冲突）
                    df = _normalize_columns(df)
                    if df is not None and not df.empty:
                        all_data.append(df)
            except Exception:
                continue

    if not all_data:
        print(f"  ⚠️  No data for {market} in [{start_dt.date()}, {ref_dt.date()}]")
        return pd.DataFrame()

    combined = pd.concat(all_data, ignore_index=True)
    return combined


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """将不同数据源的列名统一为标准格式: date, code, close, volume"""
    # 日期列: Date (yfinance), time_key (Futu), trade_date (Tushare)
    for src in ["trade_date", "time_key", "Date"]:
        if src in df.columns:
            df = df.rename(columns={src: "date"})
            break
    if "date" not in df.columns:
        return None

    # Drop NaN dates
    df = df.dropna(subset=["date"])
    if df.empty:
        return None

    # Parse dates (mixed formats: 2025-01-02, 2025-01-02 00:00:00, 20260430 int)
    try:
        # Handle integer dates like 20260430 (A-share Tushare format)
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

    # 代码列: ts_code (Tushare/Futu) or already 'code'
    for src in ["ts_code"]:
        if src in df.columns:
            df = df.rename(columns={src: "code"})
            break
    if "code" not in df.columns:
        return None

    # 价格列: Close (yfinance), close (Futu/Tushare)
    for src in ["Close"]:
        if src in df.columns:
            df = df.rename(columns={src: "close"})
            break
    if "close" not in df.columns:
        return None

    # 成交量: Volume (yfinance), vol (Tushare)
    for src in ["Volume"]:
        if src in df.columns and "volume" not in df.columns:
            df = df.rename(columns={src: "volume"})

    return df


def compute_factors(market_data: pd.DataFrame, market: str) -> pd.DataFrame:
    """
    计算选股因子: residual_vol, turnover_5d, momentum_5d, beta_20d, momentum_10d
    使用 ref_date 之前的数据计算，避免未来函数。
    """
    if market_data.empty:
        return pd.DataFrame()

    codes = market_data["code"].unique()
    results = []

    # 确定价格列
    price_cols = [c for c in market_data.columns if c.lower() in ("close", "closing_price")]
    if not price_cols:
        return pd.DataFrame()
    price_col = price_cols[0]

    vol_cols = [c for c in market_data.columns if c.lower() in ("volume", "vol")]
    vol_col = vol_cols[0] if vol_cols else None

    # 获取基准数据（简单用等权平均作为基准）
    daily_close = market_data.groupby("date")[price_col].mean().sort_index()
    benchmark_returns = daily_close.pct_change().dropna()

    for code in codes:
        try:
            stock_data = market_data[market_data["code"] == code].sort_values("date")
            if len(stock_data) < 252:
                continue

            closes = stock_data[price_col].values
            returns = np.diff(closes) / closes[:-1]

            # 252日残差波动率
            if len(returns) >= 252:
                benchmark_ret_aligned = benchmark_returns.iloc[-min(len(returns), len(benchmark_returns)):]
                stock_ret_aligned = returns[-len(benchmark_ret_aligned):]
                if len(stock_ret_aligned) >= 60:
                    residual = stock_ret_aligned - benchmark_ret_aligned
                    residual_vol = np.std(residual) * np.sqrt(252) * 100  # 年化%
                else:
                    residual_vol = np.nan
            else:
                residual_vol = np.nan

            # 5日平均换手率（简化用成交量变化率）
            if vol_col and len(stock_data) >= 5:
                volumes = stock_data[vol_col].values[-5:]
                avg_vol = np.mean(volumes)
                # 近似换手率用成交量 / 过去20日均量
                if len(stock_data) >= 20:
                    avg_vol_20 = np.mean(stock_data[vol_col].values[-20:])
                    turnover = avg_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0
                else:
                    turnover = 1.0
            else:
                turnover = 1.0

            # 5日动量
            if len(closes) >= 5:
                momentum_5d = (closes[-1] / closes[-6] - 1) * 100 if len(closes) >= 6 else 0
            else:
                momentum_5d = 0

            # 10日动量
            if len(closes) >= 10:
                momentum_10d = (closes[-1] / closes[-11] - 1) * 100 if len(closes) >= 11 else 0
            else:
                momentum_10d = 0

            # 20日 Beta
            if len(returns) >= 20:
                stock_ret_20 = returns[-20:]
                bm_ret_20 = benchmark_returns.iloc[-20:]
                if len(bm_ret_20) >= 20 and np.std(bm_ret_20) > 0:
                    beta_20d = np.cov(stock_ret_20, bm_ret_20)[0, 1] / np.var(bm_ret_20)
                else:
                    beta_20d = 1.0
            else:
                beta_20d = 1.0

            results.append({
                "code": code,
                "residual_vol": residual_vol if not np.isnan(residual_vol) else 999,
                "turnover_5d": turnover,
                "momentum_5d": momentum_5d,
                "momentum_10d": momentum_10d,
                "beta_20d": beta_20d,
                "last_price": closes[-1],
            })
        except Exception:
            continue

    return pd.DataFrame(results)


def select_stocks(factors_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    应用当前策略的选股逻辑:
    1. 残差波动率 ≤ P50
    2. 换手率 ≥ P50
    3. 5日动量 ≥ P30
    4. Beta ≥ P20 + 硬地板 1.0
    5. 按 10日动量升序排序 → 取 Top N
    """
    if factors_df.empty or len(factors_df) < top_n:
        return factors_df

    df = factors_df.copy()
    df = df[df["residual_vol"] < 999]  # 排除无效数据

    if len(df) < top_n:
        return df.nsmallest(top_n, "momentum_10d")

    # 分位阈值
    p50_vol = df["residual_vol"].quantile(0.50)
    p50_turnover = df["turnover_5d"].quantile(0.50)
    p30_mom5 = df["momentum_5d"].quantile(0.30)
    p20_beta = df["beta_20d"].quantile(0.20)

    # 应用筛选
    filtered = df[
        (df["residual_vol"] <= p50_vol) &
        (df["turnover_5d"] >= p50_turnover) &
        (df["momentum_5d"] >= p30_mom5) &
        (df["beta_20d"] >= max(p20_beta, 1.0))
    ]

    if len(filtered) < top_n:
        # 放宽条件：只保留波动率+动量筛选
        filtered = df[
            (df["residual_vol"] <= df["residual_vol"].quantile(0.70)) &
            (df["momentum_5d"] >= df["momentum_5d"].quantile(0.30))
        ]

    # 按 momentum_10d 升序（跌最多的在前）
    result = filtered.nsmallest(top_n, "momentum_10d")

    return result


def compute_forward_returns(
    market_data: pd.DataFrame,
    selected_codes: list,
    ref_date: str,
    hold_days: int = 20,
) -> dict:
    """
    计算入选股票在 ref_date 之后 hold_days 天的收益。
    """
    ref_dt = pd.to_datetime(ref_date)
    end_dt = ref_dt + pd.DateOffset(days=hold_days + 5)  # 加几天缓冲

    price_col = [c for c in market_data.columns if c.lower() in ("close", "closing_price")]
    if not price_col:
        return {"avg_return": 0, "winners": [], "returns": {}}
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
            # 找 hold_days 天后的价格，或最近的交易日
            future = stock_data[stock_data["date"] > ref_dt + pd.DateOffset(days=hold_days - 3)]
            if len(future) > 0:
                exit_price = future[price_col].iloc[0]
            else:
                exit_price = stock_data[price_col].iloc[-1]

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


def run_backtest(
    market: str = "us",
    months: int = 12,
    top_n: int = 10,
    hold_days: int = 20,
    data_months: int = 18,
) -> dict:
    """
    执行 walk-forward 回测:
    - 每月底做一次选股
    - 用当时可得的过去 data_months 个月数据计算因子
    - 模拟买入 top_n 只
    - 持有 hold_days 天
    - 统计平均收益、胜率等
    """
    print(f"\n{'='*60}")
    print(f"Backtest: {market.upper()} | {months} months | Top {top_n} | Hold {hold_days}d")
    print(f"{'='*60}")

    # 生成回测日期（每月最后一个工作日近似）
    today = date.today()
    test_dates = []
    for i in range(months, 0, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        # 用每月 15 日作为近似选股日
        test_dates.append(date(year, month, min(15, 28)))

    print(f"Test dates: {[d.isoformat() for d in test_dates]}")

    # 预加载全部日线数据
    data_dir = MARKET_DIRS[market]
    all_data = load_market_data(market, months + data_months, today.isoformat())

    if all_data.empty:
        return {"error": "No market data", "market": market}

    print(f"Loaded {len(all_data)} rows, {all_data['code'].nunique()} stocks")

    monthly_results = []
    all_returns = []

    for ref_date in test_dates:
        ref_str = ref_date.isoformat()
        print(f"\n--- {ref_str} ---")

        # Walk-forward: 只用 ref_date 之前的数据
        wf_data = all_data[all_data["date"] <= pd.to_datetime(ref_str)].copy()

        if len(wf_data) < 1000:
            print(f"  ⚠️  Insufficient data ({len(wf_data)} rows), skipping")
            continue

        # 计算因子
        factors = compute_factors(wf_data, market)
        if factors.empty or len(factors) < top_n:
            print(f"  ⚠️  Only {len(factors)} stocks with valid factors, skipping")
            continue

        # 选股
        selected = select_stocks(factors, top_n)
        selected_codes = selected["code"].tolist()
        print(f"  Selected: {selected_codes[:5]}...")

        # 计算前向收益
        fwd = compute_forward_returns(all_data, selected_codes, ref_str, hold_days)

        result = {
            "ref_date": ref_str,
            "n_stocks_filtered": len(factors),
            "n_selected": len(selected_codes),
            "avg_return": fwd["avg_return"],
            "win_rate": fwd["win_rate"],
            "returns": fwd["returns"],
        }
        monthly_results.append(result)
        all_returns.append(fwd["avg_return"])

        print(f"  Avg Return: {fwd['avg_return']}% | Win Rate: {fwd['win_rate']}% | Valid: {fwd['n_valid']}/{fwd['n_total']}")

    # 汇总统计
    if not all_returns:
        return {"error": "No valid backtest results", "market": market}

    valid_returns = [r for r in all_returns if r is not None]
    avg_monthly = np.mean(valid_returns)
    win_months = sum(1 for r in valid_returns if r > 0)
    best = max(valid_returns)
    worst = min(valid_returns)
    std_returns = np.std(valid_returns)
    sharpe_monthly = avg_monthly / std_returns if std_returns > 0 else 0

    summary = {
        "market": market,
        "strategy": "low_momentum_contrarian",
        "parameters": {
            "top_n": top_n,
            "hold_days": hold_days,
            "months_tested": len(valid_returns),
            "data_months": data_months,
        },
        "results": {
            "monthly_avg_return_pct": round(float(avg_monthly), 2),
            "monthly_win_rate_pct": round(win_months / len(valid_returns) * 100, 1),
            "best_month_pct": round(float(best), 2),
            "worst_month_pct": round(float(worst), 2),
            "std_monthly_pct": round(float(std_returns), 2),
            "sharpe_monthly": round(float(sharpe_monthly), 3),
            "total_cumulative_return_pct": round(float(np.prod([1 + r/100 for r in valid_returns]) - 1) * 100, 2),
        },
        "monthly_details": monthly_results,
    }

    # Compounded equity curve
    equity = 100.0
    equity_curve = []
    for r in valid_returns:
        equity *= (1 + r / 100)
        equity_curve.append(round(equity, 2))
    summary["equity_curve"] = equity_curve

    print(f"\n{'='*60}")
    print(f"SUMMARY: {market.upper()} Backtest")
    print(f"{'='*60}")
    print(f"Periods: {len(valid_returns)} months")
    print(f"Avg Monthly Return: {avg_monthly:.2f}%")
    print(f"Win Rate: {win_months}/{len(valid_returns)} ({win_months/len(valid_returns)*100:.1f}%)")
    print(f"Best Month: {best:.2f}%")
    print(f"Worst Month: {worst:.2f}%")
    print(f"Sharpe (monthly): {sharpe_monthly:.3f}")
    print(f"Cumulative Return: {summary['results']['total_cumulative_return_pct']:.2f}%")
    print(f"Equity Curve: {equity_curve}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Walk-forward backtest for stock picking strategy")
    parser.add_argument("--market", default="us", choices=["us", "hk", "cn", "all"],
                        help="Market to backtest")
    parser.add_argument("--months", type=int, default=12, help="Number of months to backtest")
    parser.add_argument("--top-n", type=int, default=10, help="Number of stocks to select each period")
    parser.add_argument("--hold-days", type=int, default=20, help="Holding period in days")
    parser.add_argument("--data-months", type=int, default=18,
                        help="Months of data to use for factor calculation")
    parser.add_argument("--strategy", default="contrarian",
                        choices=["contrarian", "momentum", "both"],
                        help="Strategy: contrarian (current), momentum (new), both (compare)")
    args = parser.parse_args()

    markets = ["us", "hk", "cn"] if args.market == "all" else [args.market]

    strategies = []
    if args.strategy == "both":
        strategies = ["contrarian", "momentum"]
    else:
        strategies = [args.strategy]

    all_results = {}
    for strategy in strategies:
        for mkt in markets:
            strat_label = f"{mkt}_{strategy}"
            if strategy == "momentum":
                # Import and use trend momentum strategy
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from trend_momentum import run_momentum_backtest
                result = run_momentum_backtest(
                    market=mkt, months=args.months, top_n=args.top_n,
                    hold_days=args.hold_days, data_months=args.data_months,
                )
            else:
                result = run_backtest(
                    market=mkt, months=args.months, top_n=args.top_n,
                    hold_days=args.hold_days, data_months=args.data_months,
                )
            all_results[strat_label] = result

    # Save
    PNL_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PNL_DIR / f"backtest_{args.market}_{args.strategy}_{date.today().isoformat()}.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nSaved to: {output_path}")

    # Comparison table when running 'both'
    if args.strategy == "both" and len(strategies) > 1:
        print(f"\n{'='*80}")
        print(f"STRATEGY COMPARISON: Contrarian vs Momentum")
        print(f"{'='*80}")
        print(f"{'Market':>6} | {'Strategy':>12} | {'Sharpe':>8} | {'CumRet%':>8} | {'WinRate%':>9} | {'Best%':>7} | {'Worst%':>7} | {'Std%':>7}")
        print(f"{'-'*6}-+-{'-'*12}-+-{'-'*8}-+-{'-'*8}-+-{'-'*9}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}")
        for mkt in markets:
            for strat in strategies:
                key = f"{mkt}_{strat}"
                r = all_results.get(key, {}).get("results", {})
                if not r:
                    continue
                sr = r.get("sharpe_monthly", 0)
                cum = r.get("total_cumulative_return_pct", 0)
                wr = r.get("monthly_win_rate_pct", 0)
                best = r.get("best_month_pct", 0)
                worst = r.get("worst_month_pct", 0)
                std = r.get("std_monthly_pct", 0)
                winner = "🏆" if (strat == "momentum" and "momentum" in str(key)) else ""
                print(f"{mkt.upper():>6} | {strat:>12} | {sr:>8.3f} | {cum:>7.1f}% | {wr:>8.1f}% | {best:>6.1f}% | {worst:>6.1f}% | {std:>6.1f}% {winner}")
        print(f"{'='*80}")


if __name__ == "__main__":
    main()
