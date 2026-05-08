#!/usr/bin/env python3
"""
futures_factors.py — 期货品种因子计算引擎
Phase 1.1: 计算 7 个品种的技术因子，输出因子表 + 排名

因子:
  momentum_10d    — 10 日价格动量（做多选正，做空选负）
  momentum_20d    — 20 日价格动量（辅助趋势判断）
  volatility_20d  — 20 日年化波动率（越高越有机会）
  adx_14          — ADX 趋势强度（越高趋势越明确）
  volume_ratio    — 5 日均量 / 20 日均量（放量信号）
  ma20_deviation  — 价格偏离 MA20 程度（不过度追高/杀跌）
  sharpe_20d      — 20 日夏普比率（风险调整收益）

用法:
  python3.11 futures_factors.py                     # 计算全部品种
  python3.11 futures_factors.py --date 2026-05-08   # 指定日期

输出: ~/wuhoo-workspace/data/futures/factors/factors_{date}.csv
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

DATA_DIR = Path.home() / "wuhoo-workspace" / "data" / "futures"
KLINES_DIR = DATA_DIR / "daily_kline"
FACTORS_DIR = DATA_DIR / "factors"
CONTRACT_INFO_PATH = DATA_DIR / "contract_info.json"


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """手动计算 ADX（替代 talib）"""
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    n = len(df)

    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        # True Range
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        # Directional Movement
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move
        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move

    # Wilder smoothing (EMA with alpha = 1/period)
    alpha = 1.0 / period
    tr_smooth = np.zeros(n)
    plus_dm_smooth = np.zeros(n)
    minus_dm_smooth = np.zeros(n)

    # Initialize with simple average of first 'period' values
    tr_smooth[period] = tr[1 : period + 1].mean()
    plus_dm_smooth[period] = plus_dm[1 : period + 1].mean()
    minus_dm_smooth[period] = minus_dm[1 : period + 1].mean()

    for i in range(period + 1, n):
        tr_smooth[i] = tr_smooth[i - 1] * (1 - alpha) + tr[i] * alpha
        plus_dm_smooth[i] = plus_dm_smooth[i - 1] * (1 - alpha) + plus_dm[i] * alpha
        minus_dm_smooth[i] = minus_dm_smooth[i - 1] * (1 - alpha) + minus_dm[i] * alpha

    # +DI, -DI, DX, ADX
    plus_di = np.full(n, np.nan)
    minus_di = np.full(n, np.nan)
    dx = np.full(n, np.nan)
    adx = np.full(n, np.nan)

    adx_smooth = np.full(n, np.nan)

    for i in range(period, n):
        if tr_smooth[i] > 0:
            plus_di[i] = 100.0 * plus_dm_smooth[i] / tr_smooth[i]
            minus_di[i] = 100.0 * minus_dm_smooth[i] / tr_smooth[i]
            di_sum = plus_di[i] + minus_di[i]
            if di_sum > 0:
                dx[i] = 100.0 * abs(plus_di[i] - minus_di[i]) / di_sum

    # ADX = smoothed DX
    if n > period:
        adx_smooth[2 * period] = np.nanmean(dx[period : 2 * period])
        for i in range(2 * period + 1, n):
            if not np.isnan(dx[i]):
                adx_smooth[i] = adx_smooth[i - 1] * (1 - alpha) + dx[i] * alpha

    return pd.Series(adx_smooth, index=df.index)


def compute_factors(df: pd.DataFrame) -> dict:
    """计算单品种全部因子"""
    if len(df) < 30:
        return {}

    close = df["close"].values
    volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))

    # 日收益率
    returns = np.diff(close) / close[:-1]
    returns_full = np.concatenate([[0], returns])

    factors = {}

    # 10 日动量
    if len(close) >= 11:
        factors["momentum_10d"] = (close[-1] - close[-11]) / close[-11]

    # 20 日动量
    if len(close) >= 21:
        factors["momentum_20d"] = (close[-1] - close[-21]) / close[-21]

    # 20 日年化波动率
    if len(returns) >= 20:
        factors["volatility_20d"] = np.std(returns[-20:]) * np.sqrt(252)

    # 60 日年化波动率
    if len(returns) >= 60:
        factors["volatility_60d"] = np.std(returns[-60:]) * np.sqrt(252)

    # ADX (14)
    if len(df) >= 40:
        adx = compute_adx(df, period=14)
        factors["adx_14"] = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else np.nan

    # 成交量比
    if len(volume) >= 20:
        vol_5d = np.mean(volume[-5:])
        vol_20d = np.mean(volume[-20:])
        factors["volume_ratio"] = vol_5d / vol_20d if vol_20d > 0 else 1.0

    # MA20 偏离
    if len(close) >= 20:
        ma20 = np.mean(close[-20:])
        factors["ma20_deviation"] = (close[-1] - ma20) / ma20

    # 20 日夏普比率
    if len(returns) >= 20 and np.std(returns[-20:]) > 0:
        factors["sharpe_20d"] = np.mean(returns[-20:]) / np.std(returns[-20:]) * np.sqrt(252)

    # 当前价格
    factors["close"] = close[-1]

    return factors


def compute_composite_score(factors: dict, direction: str = "LONG") -> float:
    """
    计算综合得分。各因子先归一化再加权。

    LONG 优选: 正动量 + 强趋势(ADX) + 适中波动 + 放量 + 未过度偏离MA
    SHORT 优选: 负动量 + 强趋势(ADX) + 适中波动 + 放量 + 未过度偏离MA

    ADX 的"趋势质量"和动量的"方向"是核心：
    - 动量决定方向（LONG 需正，SHORT 需负）
    - ADX 决定趋势可信度（越高权重越大）
    """
    weights = {
        "momentum_direction": 0.30,   # 动量方向
        "adx_14": 0.30,               # 趋势强度
        "volatility_20d": 0.15,       # 波动率（适中最好，过高扣分）
        "volume_ratio": 0.15,          # 量比（放量积极）
        "ma20_deviation": 0.10,        # MA偏离（越小越好）
    }

    raw = {}

    # 1. 动量方向分
    mom = factors.get("momentum_10d", 0)
    if pd.isna(mom):
        mom = 0
    if direction == "SHORT":
        mom = -mom
    # 动量分 = sigmoid 映射到 0-1，中心在 0
    raw["momentum_direction"] = 1.0 / (1.0 + np.exp(-mom * 50))  # steep sigmoid

    # 2. ADX: 0-100 范围，直接归一化
    adx = factors.get("adx_14", 0)
    if pd.isna(adx):
        adx = 0
    raw["adx_14"] = adx / 100.0  # 0-1

    # 3. 波动率：用高斯函数，最优区间在 15%-30% 年化
    vol = factors.get("volatility_20d", 0.20)
    if pd.isna(vol):
        vol = 0.20
    # 最优 0.22，sigma=0.15 → 0.10-0.35 都还行
    raw["volatility_20d"] = np.exp(-((vol - 0.22) ** 2) / (2 * 0.15**2))

    # 4. 成交量比：>1.0 好，上限 3.0
    vr = factors.get("volume_ratio", 1.0)
    if pd.isna(vr):
        vr = 1.0
    raw["volume_ratio"] = min(max(vr, 0.3), 5.0) / 5.0  # 归一化到 0-1

    # 5. MA偏离绝对值：越小越好
    dev = factors.get("ma20_deviation", 0)
    if pd.isna(dev):
        dev = 0
    raw["ma20_deviation"] = 1.0 / (1.0 + abs(dev) * 20)  # 偏离 5% → 0.5

    score = sum(raw[k] * weights[k] for k in weights)
    return score


def main():
    parser = argparse.ArgumentParser(description="期货因子计算引擎")
    parser.add_argument("--date", type=str, help="计算日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    # 加载合约信息
    with open(CONTRACT_INFO_PATH) as f:
        contracts = json.load(f)

    print(f"📊 期货因子计算 — {date_str}")
    print(f"   品种数: {len(contracts)}")
    print()

    results = []

    for code, info in contracts.items():
        market = info["market"]
        kline_path = KLINES_DIR / market / f"{code}.csv"

        if not kline_path.exists():
            print(f"   ⚠️ {code} — 无日线数据，跳过")
            continue

        df = pd.read_csv(kline_path)
        factors = compute_factors(df)

        if not factors:
            print(f"   ⚠️ {code} — 数据不足，跳过")
            continue

        # 计算多空得分
        long_score = compute_composite_score(factors, "LONG")
        short_score = compute_composite_score(factors, "SHORT")

        result = {
            "code": code,
            "name": info["name"],
            "market": market,
            "category": info.get("category", ""),
            "close": factors["close"],
            "lot_size": info["lot_size"],
            "long_margin": info.get("long_margin", 0),
            "short_margin": info.get("short_margin", 0),
            "margin_currency": info.get("margin_currency", "USD"),
            "date": date_str,
            # 因子
            "momentum_10d": factors.get("momentum_10d", np.nan),
            "momentum_20d": factors.get("momentum_20d", np.nan),
            "volatility_20d": factors.get("volatility_20d", np.nan),
            "volatility_60d": factors.get("volatility_60d", np.nan),
            "adx_14": factors.get("adx_14", np.nan),
            "volume_ratio": factors.get("volume_ratio", np.nan),
            "ma20_deviation": factors.get("ma20_deviation", np.nan),
            "sharpe_20d": factors.get("sharpe_20d", np.nan),
            # 得分
            "long_score": round(long_score, 6),
            "short_score": round(short_score, 6),
        }
        results.append(result)

        direction = "📈" if factors.get("momentum_10d", 0) > 0 else "📉"
        print(f"   {direction} {code:16s} ({info['name']:12s})  "
              f"动量={factors.get('momentum_10d', 0):+.3f}  "
              f"波动={factors.get('volatility_20d', 0):.3f}  "
              f"ADX={factors.get('adx_14', 0):.1f}  "
              f"long={long_score:+.4f}  short={short_score:+.4f}")

    # 排序 + 输出
    df_result = pd.DataFrame(results)

    # LONG 排名
    df_long = df_result.sort_values("long_score", ascending=False)
    print(f"\n{'='*60}")
    print(f"📈 做多排名 (Long)")
    print(f"{'='*60}")
    for _, row in df_long.iterrows():
        print(f"   {row['code']:16s}  {row['name']:12s}  score={row['long_score']:+.4f}  "
              f"动量={row['momentum_10d']:+.3f}  ￥{row['close']:.1f}")

    # SHORT 排名
    df_short = df_result.sort_values("short_score", ascending=False)
    print(f"\n{'='*60}")
    print(f"📉 做空排名 (Short)")
    print(f"{'='*60}")
    for _, row in df_short.iterrows():
        print(f"   {row['code']:16s}  {row['name']:12s}  score={row['short_score']:+.4f}  "
              f"动量={row['momentum_10d']:+.3f}  ￥{row['close']:.1f}")

    # 保存
    FACTORS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = FACTORS_DIR / f"factors_{date_str}.csv"
    df_result.to_csv(output_path, index=False)
    print(f"\n✅ 因子数据已保存: {output_path}")

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
