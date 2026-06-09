#!/usr/bin/env python3.11
"""
PnL Tracker — 每日组合净值快照与绩效指标计算

功能:
1. snapshot — 连接 Futu OpenD，对所有账户持仓+现金做快照，追加到时序 JSON
2. metrics — 从时序快照计算 Sharpe/Max DD/Calmar/Win Rate + Benchmark 对比
3. benchmark — 获取基准指数数据(SPY/HSI/沪深300)用于对比

输出:
- ~/wuhoo-workspace/data/pnl/snapshots.jsonl  — 每日快照（JSONL 格式）
- ~/wuhoo-workspace/data/pnl/metrics_report.json — 最新绩效报告

用法:
  python3.11 pnl_tracker.py snapshot          # 当日快照
  python3.11 pnl_tracker.py metrics           # 计算绩效指标
  python3.11 pnl_tracker.py full              # 快照 + 指标
"""

import json, os, sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from futu import (
    OpenSecTradeContext, OpenQuoteContext,
    TrdMarket, TrdEnv, RET_OK
)

HOME = Path.home()
DATA_DIR = HOME / "wuhoo-workspace" / "data" / "pnl"
SNAPSHOTS_FILE = DATA_DIR / "snapshots.jsonl"
METRICS_FILE = DATA_DIR / "metrics_report.json"

# Futu 模拟账户配置（与 wuhoo-trade skill 一致）
ACCOUNTS = {
    "US": {"acc_id": 18767293, "market": TrdMarket.US, "env": TrdEnv.SIMULATE, "name": "US Stocks"},
    "HK": {"acc_id": 18767294, "market": TrdMarket.HK, "env": TrdEnv.SIMULATE, "name": "HK Stocks"},
    "CN": {"acc_id": 18767295, "market": TrdMarket.CN, "env": TrdEnv.SIMULATE, "name": "CN Stocks"},
}

# Benchmark tickers
BENCHMARKS = {
    "SPY": "US",
    "HSI": "HK",   # ^HSI via yfinance
    "ASHR": "CN",  # A股替代 (沪深300 ETF)
}


def safe_float(v, default=0.0):
    """Futu API 可能返回 'N/A' 字符串"""
    if v is None or v == "N/A" or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def fetch_snapshot() -> dict:
    """获取所有账户的当前持仓+现金快照"""
    result = {
        "date": date.today().isoformat(),
        "timestamp": datetime.now().isoformat(),
        "accounts": {},
        "total_equity": 0.0,
        "total_cash": 0.0,
        "total_market_value": 0.0,
        "total_unrealized_pl": 0.0,
    }

    for market, cfg in ACCOUNTS.items():
        try:
            trd_ctx = OpenSecTradeContext(
                host="127.0.0.1", port=11111,
                filter_trdmarket=cfg["market"]
            )

            # 查持仓
            ret, positions = trd_ctx.position_list_query(
                trd_env=cfg["env"], acc_id=cfg["acc_id"],
                refresh_cache=True
            )
            pos_list = []
            market_value = 0.0
            unrealized_pl = 0.0

            if ret == RET_OK and len(positions) > 0:
                for _, row in positions.iterrows():
                    code = row.get("code", "")
                    qty = safe_float(row.get("qty", 0))
                    cost = safe_float(row.get("cost_price", 0))
                    price = safe_float(row.get("price", 0))
                    mv = qty * price
                    pl_val = safe_float(row.get("unrealized_pl", 0))
                    pl_pct = safe_float(row.get("pl_ratio", 0))  # may be percentage or decimal

                    market_value += mv
                    unrealized_pl += pl_val
                    pos_list.append({
                        "code": code,
                        "qty": qty,
                        "cost_price": cost,
                        "market_price": price,
                        "market_value": round(mv, 2),
                        "unrealized_pl": round(pl_val, 2),
                        "unrealized_pl_pct": round(pl_pct, 4),
                    })

            # 查账户现金
            try:
                ret_acc, accinfo = trd_ctx.accinfo_query(
                    trd_env=cfg["env"], acc_id=cfg["acc_id"],
                    refresh_cache=True
                )
            except Exception:
                accinfo = None
                ret_acc = None

            cash = 0.0
            total_assets = 0.0
            if ret_acc == RET_OK and accinfo is not None and len(accinfo) > 0:
                cash = safe_float(accinfo.iloc[0].get("cash", 0))
                total_assets = safe_float(accinfo.iloc[0].get("total_assets", 0))

            # US 模拟账户 accinfo_query 可能返回全零 → 用持仓市值估算
            if total_assets == 0 and market_value > 0:
                total_assets = market_value + cash

            account_snapshot = {
                "name": cfg["name"],
                "acc_id": cfg["acc_id"],
                "cash": round(cash, 2),
                "total_assets": round(total_assets, 2),
                "market_value": round(market_value, 2),
                "unrealized_pl": round(unrealized_pl, 2),
                "position_count": len(pos_list),
                "positions": pos_list,
            }
            result["accounts"][market] = account_snapshot

            result["total_cash"] += cash
            result["total_market_value"] += market_value
            result["total_unrealized_pl"] += unrealized_pl
            result["total_equity"] += total_assets if total_assets > 0 else (cash + market_value)

            trd_ctx.close()

        except Exception as e:
            result["accounts"][market] = {
                "name": cfg["name"],
                "acc_id": cfg["acc_id"],
                "error": str(e),
                "cash": 0, "total_assets": 0, "market_value": 0,
                "unrealized_pl": 0, "position_count": 0, "positions": [],
            }

    result["total_equity"] = round(result["total_equity"], 2)
    result["total_cash"] = round(result["total_cash"], 2)
    result["total_market_value"] = round(result["total_market_value"], 2)
    result["total_unrealized_pl"] = round(result["total_unrealized_pl"], 2)

    return result


def save_snapshot(snapshot: dict) -> Path:
    """追加快照到 JSONL 文件"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SNAPSHOTS_FILE, "a") as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
    return SNAPSHOTS_FILE


def load_snapshots() -> pd.DataFrame:
    """加载所有历史快照为 DataFrame"""
    if not SNAPSHOTS_FILE.exists():
        return pd.DataFrame()

    records = []
    with open(SNAPSHOTS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    df = pd.DataFrame(records)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    return df


def get_benchmark_data() -> dict:
    """获取基准指数数据"""
    import yfinance as yf

    result = {}
    yf_symbols = {"SPY": "SPY", "HSI": "^HSI", "ASHR": "ASHR"}

    for name, ticker in yf_symbols.items():
        try:
            data = yf.download(ticker, period="1y", progress=False)
            if not data.empty:
                closes = data["Close"].values.flatten()
                result[name] = {
                    "latest": round(float(closes[-1]), 2),
                    "start": round(float(closes[0]), 2),
                    "return_1y": round(float((closes[-1] / closes[0] - 1) * 100), 2),
                    "dates": len(closes),
                }
        except Exception as e:
            result[name] = {"error": str(e)}

    return result


def calculate_metrics() -> dict:
    """从历史快照计算绩效指标"""
    df = load_snapshots()
    if df.empty:
        return {"error": "No snapshot data found", "snapshot_count": 0}

    equities = df["total_equity"].values

    # 日收益率
    daily_returns = np.diff(equities) / equities[:-1]
    daily_returns = daily_returns[~np.isnan(daily_returns)]
    daily_returns = daily_returns[~np.isinf(daily_returns)]

    if len(daily_returns) < 5:
        return {
            "error": f"Need at least 5 data points, have {len(daily_returns) + 1}",
            "snapshot_count": len(df),
        }

    # 无风险利率（年化 3%）
    rf_annual = 0.03
    rf_daily = (1 + rf_annual) ** (1 / 252) - 1

    # Sharpe Ratio (年化)
    excess_returns = daily_returns - rf_daily
    sharpe = np.sqrt(252) * np.mean(excess_returns) / np.std(daily_returns) if np.std(daily_returns) > 0 else 0

    # Max Drawdown
    peak = np.maximum.accumulate(equities)
    drawdowns = (equities - peak) / peak
    max_dd = float(np.min(drawdowns))

    # Calmar Ratio
    total_return = (equities[-1] / equities[0] - 1)
    calmar = total_return / abs(max_dd) if max_dd < 0 else float("inf")

    # Win Rate
    wins = np.sum(daily_returns > 0)
    total = len(daily_returns)
    win_rate = wins / total if total > 0 else 0

    # 总收益
    total_return_pct = round(total_return * 100, 2)

    # 基准对比
    benchmarks = get_benchmark_data()

    # 日数
    n_days = len(df)
    start_date = df["date"].iloc[0].strftime("%Y-%m-%d")
    end_date = df["date"].iloc[-1].strftime("%Y-%m-%d")

    report = {
        "generated_at": datetime.now().isoformat(),
        "period": {"start": start_date, "end": end_date, "trading_days": n_days},
        "current_equity": round(float(equities[-1]), 2),
        "total_return_pct": total_return_pct,
        "annualized_return_pct": round(float(((1 + total_return) ** (252 / n_days) - 1) * 100), 2) if n_days > 0 else 0,
        "sharpe_ratio": round(float(sharpe), 3),
        "max_drawdown_pct": round(float(max_dd * 100), 2),
        "calmar_ratio": round(float(calmar), 3) if calmar != float("inf") else None,
        "win_rate_pct": round(float(win_rate * 100), 1),
        "avg_daily_return_pct": round(float(np.mean(daily_returns) * 100), 4),
        "volatility_annual_pct": round(float(np.std(daily_returns) * np.sqrt(252) * 100), 2),
        "benchmarks": benchmarks,
        "account_breakdown": {},
    }

    # 最后一份快照的账户明细
    if len(df) > 0:
        last_row = df.iloc[-1]
        for market in ["US", "HK", "CN"]:
            if market in last_row.get("accounts", {}):
                acc = last_row["accounts"][market]
                report["account_breakdown"][market] = {
                    "equity": acc.get("total_assets", 0),
                    "cash": acc.get("cash", 0),
                    "positions": acc.get("position_count", 0),
                    "unrealized_pl": acc.get("unrealized_pl", 0),
                }

    return report


def cmd_snapshot():
    """执行快照"""
    snap = fetch_snapshot()
    path = save_snapshot(snap)
    print(f"Snapshot saved: {path}")
    print(f"Date: {snap['date']}")
    print(f"Total Equity: ${snap['total_equity']:,.2f}")
    print(f"Total Cash: ${snap['total_cash']:,.2f}")
    print(f"Market Value: ${snap['total_market_value']:,.2f}")
    print(f"Unrealized P&L: ${snap['total_unrealized_pl']:,.2f}")
    for market, acc in snap["accounts"].items():
        if acc.get("error"):
            print(f"  {market}: ERROR — {acc['error']}")
        else:
            print(f"  {market}: equity=${acc['total_assets']:,.2f}, cash=${acc['cash']:,.2f}, {acc['position_count']} positions, P&L=${acc['unrealized_pl']:,.2f}")


def cmd_metrics():
    """计算并保存绩效指标"""
    report = calculate_metrics()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(METRICS_FILE, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Metrics report saved: {METRICS_FILE}")
    if "error" in report:
        print(f"⚠️  {report['error']}")
        return

    print(f"\n=== Performance Report ===")
    print(f"Period: {report['period']['start']} → {report['period']['end']} ({report['period']['trading_days']} days)")
    print(f"Current Equity: ${report['current_equity']:,.2f}")
    print(f"Total Return: {report['total_return_pct']}%")
    print(f"Ann. Return: {report['annualized_return_pct']}%")
    print(f"Sharpe Ratio: {report['sharpe_ratio']}")
    print(f"Max Drawdown: {report['max_drawdown_pct']}%")
    print(f"Calmar Ratio: {report['calmar_ratio']}")
    print(f"Win Rate: {report['win_rate_pct']}%")
    print(f"Volatility (ann): {report['volatility_annual_pct']}%")

    print(f"\n=== Benchmarks (1Y) ===")
    for name, bm in report.get("benchmarks", {}).items():
        if "error" in bm:
            print(f"  {name}: ERROR — {bm['error']}")
        else:
            print(f"  {name}: ${bm['latest']}, 1Y return {bm['return_1y']}%")


def cmd_full():
    """快照 + 指标"""
    cmd_snapshot()
    print()
    cmd_metrics()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "full"
    if cmd == "snapshot":
        cmd_snapshot()
    elif cmd == "metrics":
        cmd_metrics()
    elif cmd == "full":
        cmd_full()
    else:
        print(f"Usage: python3.11 pnl_tracker.py [snapshot|metrics|full]")
        sys.exit(1)
