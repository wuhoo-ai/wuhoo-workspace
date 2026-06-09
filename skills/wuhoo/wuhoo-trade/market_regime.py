#!/usr/bin/env python3.11
"""
市场状态判定模块 — Market Regime Detection

根据多维度市场指标判断当前市场状态，用于驱动策略选择：
- BULL_TRENDING: 强劲上涨 → 趋势动量策略
- BULL_VOLATILE: 波动上涨 → 趋势动量（减仓）
- RANGING: 震荡 → 超跌反弹策略
- BEAR_VOLATILE: 波动下跌 → 空仓/防御
- BEAR_TRENDING: 持续下跌 → 空仓

核心指标（加权投票制）:
  1. MA 位置 (30%): 价格 vs MA50/MA200 关系
  2. 市场广度 (25%): 站上均线的股票占比
  3. 趋势强度 (20%): MA50 斜率 + 连续方向
  4. 波动率 (15%): 日收益标准差 / ATR 比例
  5. 动量广度 (10%): 正20日动量股票占比

输出:
  - regime: 状态标签
  - confidence: 置信度 (0-1)
  - scores: 各维度得分明细
  - recommendation: 策略建议

用法:
  python3.11 market_regime.py --market us
  python3.11 market_regime.py --market cn --date 2026-06-06
  python3.11 market_regime.py --market all
"""

import json, sys, argparse
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

HOME = Path.home()
DATA_DIR = HOME / "wuhoo-workspace" / "data" / "stock-pick"
REGIME_DIR = HOME / "wuhoo-workspace" / "data" / "regime"

MARKET_DIRS = {
    "us": DATA_DIR / "daily_data_us",
    "hk": DATA_DIR / "daily_data_hk",
    "cn": DATA_DIR / "daily_data",
}


class Regime(str, Enum):
    BULL_TRENDING = "BULL_TRENDING"
    BULL_VOLATILE = "BULL_VOLATILE"
    RANGING = "RANGING"
    BEAR_VOLATILE = "BEAR_VOLATILE"
    BEAR_TRENDING = "BEAR_TRENDING"


STRATEGY_MAP = {
    Regime.BULL_TRENDING: "trend_momentum",
    Regime.BULL_VOLATILE: "trend_momentum_75pct",   # 减仓到 75%
    Regime.RANGING: "oversold_rebound",
    Regime.BEAR_VOLATILE: "defensive_50pct",         # 减仓到 50%
    Regime.BEAR_TRENDING: "cash_only",               # 空仓
}


def _normalize_columns(df: pd.DataFrame):
    """列名规范化，与 backtest.py/trend_momentum.py 保持一致"""
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
    return df


def load_market_data(market: str, months: int = 12, ref_date: str = None) -> pd.DataFrame:
    """加载最近 months 个月的市场数据"""
    data_dir = MARKET_DIRS[market]
    if not data_dir.exists():
        return pd.DataFrame()
    if ref_date is None:
        ref_dt = pd.Timestamp.now()
    else:
        ref_dt = pd.to_datetime(ref_date)
    start_dt = ref_dt - pd.DateOffset(months=months)

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


# ============================================================
# Dimension 1: MA Position (weight 30%)
# ============================================================
def score_ma_position(market_index_data: pd.DataFrame) -> dict:
    """
    判断价格相对 MA50 / MA200 的位置。

    返回: {"score": -2..+2, "detail": str, "ma50_pct": float, "ma200_pct": float}
      +2: price > MA50 > MA200  (golden cross, strong bull)
      +1: price > MA50 but < MA200
       0: price between MA50 and MA200
      -1: price < MA50 but > MA200
      -2: price < MA50 < MA200  (death cross, strong bear)
    """
    if market_index_data.empty or len(market_index_data) < 200:
        return {"score": 0, "detail": "insufficient data", "ma50_pct": 0, "ma200_pct": 0}

    df = market_index_data.sort_values("date")
    # 用等权平均作为市场指数的近似
    price_col = [c for c in df.columns if c.lower() in ("close", "closing_price")]
    if not price_col:
        return {"score": 0, "detail": "no price data"}
    price_col = price_col[0]

    # 构建市场指数（每日所有股票的加权平均收盘价）
    idx = df.groupby("date")[price_col].mean()
    last_price = idx.iloc[-1]

    if len(idx) >= 50:
        ma50 = idx.iloc[-50:].mean()
    else:
        ma50 = last_price

    if len(idx) >= 200:
        ma200 = idx.iloc[-200:].mean()
    else:
        ma200 = last_price

    ma50_pct = (last_price / ma50 - 1) * 100
    ma200_pct = (last_price / ma200 - 1) * 100

    above_ma50 = last_price > ma50
    above_ma200 = last_price > ma200
    golden_cross = ma50 > ma200  # MA50 在 MA200 上方

    if above_ma50 and above_ma200 and golden_cross:
        score = 2
        detail = f"强牛: price>{ma50:.1f}>{ma200:.1f}, +{ma50_pct:.1f}%/+{ma200_pct:.1f}%"
    elif above_ma50 and above_ma200:
        score = 1
        detail = f"偏牛: price>{ma50:.1f}, +{ma50_pct:.1f}%"
    elif above_ma50 and not above_ma200:
        score = 0
        detail = f"震荡: price在MA50({ma50:.1f})上方, 但低于MA200({ma200:.1f})"
    elif not above_ma50 and above_ma200:
        score = -1
        detail = f"偏熊: price<MA50({ma50:.1f}), 但 MA200 有支撑"
    else:
        score = -2
        detail = f"强熊: price<MA50<MA200, {ma50_pct:.1f}%"

    return {"score": score, "detail": detail, "ma50_pct": round(ma50_pct, 1), "ma200_pct": round(ma200_pct, 1)}


# ============================================================
# Dimension 2: Market Breadth (weight 25%)
# ============================================================
def score_breadth(market_data: pd.DataFrame) -> dict:
    """
    计算站上 MA50 / MA200 的股票占比。

    返回: {"score": -2..+2, "pct_above_ma50": float, "pct_above_ma200": float}
      +2: >70% above MA50  (broad-based rally)
      +1: 55-70%
       0: 45-55%
      -1: 30-45%
      -2: <30%  (broad-based decline)
    """
    if market_data.empty:
        return {"score": 0, "pct_above_ma50": 0, "pct_above_ma200": 0, "detail": "no data"}

    price_col = [c for c in market_data.columns if c.lower() in ("close", "closing_price")]
    if not price_col:
        return {"score": 0, "pct_above_ma50": 0, "pct_above_ma200": 0}
    price_col = price_col[0]

    codes = market_data["code"].unique()
    above_ma50 = 0
    above_ma200 = 0
    total = 0

    for code in codes:
        stock = market_data[market_data["code"] == code].sort_values("date")
        if len(stock) < 200:
            continue
        total += 1
        prices = stock[price_col]
        if prices.iloc[-1] > prices.iloc[-50:].mean():
            above_ma50 += 1
        if prices.iloc[-1] > prices.iloc[-200:].mean():
            above_ma200 += 1

    if total == 0:
        return {"score": 0, "pct_above_ma50": 0, "pct_above_ma200": 0, "detail": "no valid stocks"}

    pct50 = above_ma50 / total * 100
    pct200 = above_ma200 / total * 100

    # Score based on percentage above MA50
    if pct50 > 70:
        score = 2
    elif pct50 > 55:
        score = 1
    elif pct50 > 45:
        score = 0
    elif pct50 > 30:
        score = -1
    else:
        score = -2

    detail = f"MA50: {pct50:.0f}%, MA200: {pct200:.0f}%, n={total}"

    return {"score": score, "pct_above_ma50": round(pct50, 1), "pct_above_ma200": round(pct200, 1), "detail": detail}


# ============================================================
# Dimension 3: Trend Strength (weight 20%)
# ============================================================
def score_trend_strength(market_index_data: pd.DataFrame) -> dict:
    """
    MA50 斜率 + 连续涨/跌天数。

    返回: {"score": -2..+2, "ma50_slope_pct": float, "consecutive_days": int}
    """
    if market_index_data.empty or len(market_index_data) < 60:
        return {"score": 0, "detail": "insufficient data"}

    price_col = [c for c in market_index_data.columns if c.lower() in ("close", "closing_price")]
    if not price_col:
        return {"score": 0}
    price_col = price_col[0]

    idx = market_index_data.groupby("date")[price_col].mean()
    if len(idx) < 60:
        return {"score": 0, "detail": "insufficient data"}

    # MA50 斜率（最近10天 vs 10天前的 MA50）
    ma50_recent = idx.iloc[-10:].mean()
    ma50_prior = idx.iloc[-60:-10].mean()
    ma50_slope = (ma50_recent / ma50_prior - 1) * 100

    # 连续涨/跌天数
    daily_returns = idx.pct_change().dropna()
    last_return = daily_returns.iloc[-1]
    consecutive = 0
    for ret in reversed(daily_returns.values):
        if (last_return > 0 and ret > 0) or (last_return < 0 and ret < 0):
            consecutive += 1
        else:
            break

    # Score
    if ma50_slope > 3:
        slope_score = 2
    elif ma50_slope > 0.5:
        slope_score = 1
    elif ma50_slope > -0.5:
        slope_score = 0
    elif ma50_slope > -3:
        slope_score = -1
    else:
        slope_score = -2

    # Consecutive bonus: 超过3天连续方向+/- 1分
    if consecutive >= 5:
        if last_return > 0:
            slope_score = min(2, slope_score + 1)
        else:
            slope_score = max(-2, slope_score - 1)

    return {
        "score": slope_score,
        "ma50_slope_pct": round(ma50_slope, 2),
        "consecutive_days": consecutive,
        "consecutive_direction": "up" if last_return > 0 else "down",
        "detail": f"MA50 slope={ma50_slope:.2f}%, consecutive {consecutive}d {'↑' if last_return > 0 else '↓'}",
    }


# ============================================================
# Dimension 4: Volatility (weight 15%)
# ============================================================
def score_volatility(market_index_data: pd.DataFrame) -> dict:
    """
    波动率评估 — 年化标准差 / 近期波动率变化。

    返回: {"score": -2..+2}
      高 = -2 (恐慌), 中高 = -1, 正常 = 0, 低 = +1 (无恐慌)
    """
    if market_index_data.empty or len(market_index_data) < 60:
        return {"score": 0, "detail": "insufficient data"}

    price_col = [c for c in market_index_data.columns if c.lower() in ("close", "closing_price")]
    if not price_col:
        return {"score": 0}
    price_col = price_col[0]

    idx = market_index_data.groupby("date")[price_col].mean()
    returns = idx.pct_change().dropna()

    if len(returns) < 20:
        return {"score": 0, "detail": "insufficient returns data"}

    # 近期（20日）年化波动率
    recent_vol = returns.iloc[-20:].std() * np.sqrt(252) * 100

    # 中期（60日）年化波动率用于比较
    if len(returns) >= 60:
        mid_vol = returns.iloc[-60:].std() * np.sqrt(252) * 100
        vol_change = recent_vol / mid_vol if mid_vol > 0 else 1.0
    else:
        vol_change = 1.0

    # 根据相对波动率评分
    if vol_change > 1.5:
        score = -2  # 波动急剧放大 → 恐慌
        detail = f"VIX激增: 20d={recent_vol:.1f}%, 60d={mid_vol:.1f}% (ratio {vol_change:.1f}x)"
    elif vol_change > 1.2:
        score = -1
        detail = f"波动上升: 20d={recent_vol:.1f}% (ratio {vol_change:.1f}x)"
    elif vol_change > 0.8:
        score = 0
        detail = f"波动正常: 20d={recent_vol:.1f}%"
    else:
        score = 1
        detail = f"波动收缩: 20d={recent_vol:.1f}% (ratio {vol_change:.1f}x)"

    return {"score": score, "vol_20d_annualized": round(recent_vol, 1), "vol_ratio": round(vol_change, 2), "detail": detail}


# ============================================================
# Dimension 5: Momentum Breadth (weight 10%)
# ============================================================
def score_momentum_breadth(market_data: pd.DataFrame) -> dict:
    """
    20日正动量股票占比。

    返回: {"score": -2..+2, "pct_positive_20d": float}
    """
    if market_data.empty:
        return {"score": 0, "pct_positive_20d": 0, "detail": "no data"}

    price_col = [c for c in market_data.columns if c.lower() in ("close", "closing_price")]
    if not price_col:
        return {"score": 0, "pct_positive_20d": 0}
    price_col = price_col[0]

    codes = market_data["code"].unique()
    positive = 0
    total = 0

    for code in codes:
        stock = market_data[market_data["code"] == code].sort_values("date")
        if len(stock) < 21:
            continue
        total += 1
        if stock[price_col].iloc[-1] > stock[price_col].iloc[-21]:
            positive += 1

    if total == 0:
        return {"score": 0, "pct_positive_20d": 0, "detail": "no valid stocks"}

    pct = positive / total * 100

    if pct > 65:
        score = 2
    elif pct > 55:
        score = 1
    elif pct > 45:
        score = 0
    elif pct > 35:
        score = -1
    else:
        score = -2

    return {"score": score, "pct_positive_20d": round(pct, 1), "detail": f"20d正动量: {pct:.0f}% (n={total})"}


# ============================================================
# Regime Detector
# ============================================================
WEIGHTS = {
    "ma_position": 0.30,
    "breadth": 0.25,
    "trend_strength": 0.20,
    "volatility": 0.15,
    "momentum_breadth": 0.10,
}


def detect_regime(market: str, ref_date: str = None, data_months: int = 12) -> dict:
    """
    主函数：综合 5 个维度判断市场状态。

    返回:
      {
        "market": str,
        "ref_date": str,
        "regime": Regime,
        "confidence": float,
        "composite_score": float,
        "scores": {
          "ma_position": {...},
          "breadth": {...},
          ...
        },
        "recommendation": {
          "strategy": str,
          "position_pct": float,
          "rationale": str,
        }
      }
    """
    if ref_date is None:
        ref_date = date.today().isoformat()

    data = load_market_data(market, months=data_months, ref_date=ref_date)
    if data.empty:
        return {
            "market": market, "ref_date": ref_date,
            "regime": Regime.RANGING, "confidence": 0.0,
            "error": "No market data available",
        }

    # Pre-filter to ref_date
    ref_dt = pd.to_datetime(ref_date)
    wf_data = data[data["date"] <= ref_dt].copy()

    # Compute all dimensions
    scores = {
        "ma_position": score_ma_position(wf_data),
        "breadth": score_breadth(wf_data),
        "trend_strength": score_trend_strength(wf_data),
        "volatility": score_volatility(wf_data),
        "momentum_breadth": score_momentum_breadth(wf_data),
    }

    # Weighted composite
    composite = sum(scores[name]["score"] * weight for name, weight in WEIGHTS.items())

    # ── Breadth-mask: 当市场广度极差时，MA位置可能被少数大票拉高产生假阳性 ──
    # 2026-06-09 发现：CN MA位置+2但广度-2(仅27%站上MA50)，composite仍>0→误判BULL
    # 修复：广度得分≤-1时，composite强制cap到+0.4（最多RANGING，不能BULL）
    breadth_score = scores["breadth"]["score"]
    breadth_pct = scores["breadth"].get("pct_above_ma50", 0)
    breadth_cap_applied = False
    if breadth_score <= -1:
        # Composite capped at +0.4 → can only be RANGING or BEAR, never BULL
        composite = min(composite, 0.4)
        breadth_cap_applied = True

    # Confidence: how far from 0 (neutral)
    confidence = min(abs(composite) / 2.0, 1.0)

    # Determine regime
    vol_score = scores["volatility"]["score"]

    if composite >= 0.5:
        if vol_score <= -1:
            regime = Regime.BULL_VOLATILE
        else:
            regime = Regime.BULL_TRENDING
    elif composite <= -0.5:
        if vol_score <= -1:
            regime = Regime.BEAR_VOLATILE
        else:
            regime = Regime.BEAR_TRENDING
    else:
        regime = Regime.RANGING

    # Strategy recommendation
    strategy_rec = STRATEGY_MAP[regime]
    if regime == Regime.BULL_TRENDING:
        position_pct = 100
        rationale = "牛市趋势 → 全力做多，趋势动量策略"
    elif regime == Regime.BULL_VOLATILE:
        position_pct = 75
        rationale = "牛市中高波动 → 趋势动量但减仓至75%"
    elif regime == Regime.RANGING:
        position_pct = 80
        rationale = "震荡市 → 超跌反弹策略，低买高卖"
    elif regime == Regime.BEAR_VOLATILE:
        position_pct = 50
        rationale = "熊市高波动 → 半仓防御，避免接飞刀"
    else:
        position_pct = 0
        rationale = "熊市趋势 → 空仓避险"

    return {
        "market": market,
        "ref_date": ref_date,
        "regime": regime,
        "composite_score": round(composite, 2),
        "confidence": round(confidence, 2),
        "scores": scores,
        "recommendation": {
            "strategy": strategy_rec,
            "position_pct": position_pct,
            "rationale": rationale,
        },
    }


def detect_all_markets(ref_date: str = None) -> dict:
    """三个市场同时检测"""
    results = {}
    for market in ["us", "hk", "cn"]:
        results[market] = detect_regime(market, ref_date)
    return results


# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Market Regime Detection")
    parser.add_argument("--market", default="us", choices=["us", "hk", "cn", "all"])
    parser.add_argument("--date", default=None, help="Reference date (YYYY-MM-DD)")
    parser.add_argument("--months", type=int, default=12, help="Data months to load")
    parser.add_argument("--save", action="store_true", help="Save to JSON")
    args = parser.parse_args()

    if args.market == "all":
        results = detect_all_markets(args.date)
    else:
        results = {args.market: detect_regime(args.market, args.date, args.months)}

    for market, r in results.items():
        print(f"\n{'='*60}")
        print(f"Market Regime: {market.upper()}  |  {r.get('ref_date', '?')}")
        print(f"{'='*60}")
        print(f"  Regime:      {r['regime']}")
        print(f"  Confidence:  {r['confidence']}")
        print(f"  Composite:   {r['composite_score']}")
        print(f"  ---")
        for name, s in r.get("scores", {}).items():
            print(f"  {name:20s}: score={s['score']:+d}  |  {s.get('detail', '')}")
        print(f"  ---")
        rec = r.get("recommendation", {})
        print(f"  Strategy:    {rec.get('strategy')}")
        print(f"  Position:    {rec.get('position_pct')}%")
        print(f"  Rationale:   {rec.get('rationale')}")

    if args.save:
        REGIME_DIR.mkdir(parents=True, exist_ok=True)
        today_str = date.today().isoformat()
        path = REGIME_DIR / f"regime_{args.market}_{today_str}.json"
        with open(path, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
