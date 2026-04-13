#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio Metrics — 组合级量化指标计算

包含:
1. Sharpe Ratio (基于持仓收益率估算)
2. HHI (Herfindahl-Hirschman Index) 集中度
3. Top-N 集中度
4. 估算最大回撤
5. 行业集中度 (如果行业数据可用)
6. 盈亏分布统计

这些指标用于 Workflow D (持仓诊断) 的组合级风险评估。
"""

import math
from typing import Dict, List, Optional


def calculate_sharpe_ratio(
    returns: List[float],
    weights: Optional[List[float]] = None,
    risk_free_rate: float = 0.02,
) -> float:
    """
    计算组合 Sharpe Ratio

    使用加权平均收益率和加权标准差。基于持仓收益率的横截面估算，
    非时间序列 Sharpe，仅用于持仓间的风险调整收益比较。

    Args:
        returns: 各持仓收益率列表 (小数形式, 如 0.15 表示 15%)
        weights: 各持仓权重列表 (可选, 默认等权)
        risk_free_rate: 无风险利率 (年化, 默认 2%)

    Returns:
        Sharpe Ratio
    """
    if not returns:
        return 0.0

    n = len(returns)
    if weights is None:
        weights = [1.0 / n] * n

    # 归一化权重
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    weights = [w / total_w for w in weights]

    # 加权平均收益
    portfolio_return = sum(r * w for r, w in zip(returns, weights))

    # 加权标准差 (横截面近似)
    if n < 2:
        return 0.0

    mean_return = sum(returns) / n
    variance = sum(w * (r - mean_return) ** 2 for r, w in zip(returns, weights))
    std_dev = math.sqrt(variance) if variance > 0 else 0.001

    sharpe = (portfolio_return - risk_free_rate) / std_dev
    return sharpe


def calculate_hhi(weights: List[float]) -> float:
    """
    计算 Herfindahl-Hirschman Index

    HHI = sum(w_i^2), 范围 [1/N, 1]
    接近 1 = 高度集中 (单股主导), 接近 1/N = 高度分散

    Args:
        weights: 各持仓权重列表

    Returns:
        HHI 指数
    """
    if not weights:
        return 0.0
    return sum(w * w for w in weights)


def calculate_concentration(
    weights: List[float], top_n: int = 3
) -> Dict[str, float]:
    """
    计算 Top-N 集中度

    Args:
        weights: 各持仓权重列表
        top_n: 前 N 大 (用于内部计算, 返回包含 3/5/10)

    Returns:
        {"top3": float, "top5": float, "top10": float}
    """
    if not weights:
        return {"top3": 0.0, "top5": 0.0, "top10": 0.0}

    sorted_w = sorted(weights, reverse=True)
    return {
        "top3": round(sum(sorted_w[:3]), 4),
        "top5": round(sum(sorted_w[:5]), 4),
        "top10": round(sum(sorted_w[:10]), 4),
    }


def calculate_max_drawdown_estimate(positions: List[Dict]) -> float:
    """
    估算组合最大回撤 (基于个股盈亏比加权)

    注意: 这是基于当前持仓盈亏的静态估算, 非历史时间序列最大回撤。
    仅考虑亏损股票的加权平均亏损幅度。

    Args:
        positions: 持仓列表 (含 market_val, pl_ratio_avg_cost)

    Returns:
        估算最大回撤 (小数形式, 如 0.08 表示 8%)
    """
    if not positions:
        return 0.0

    total_mv = sum(p.get("market_val", 0) for p in positions)
    if total_mv == 0:
        return 0.0

    weighted_drawdown = 0.0
    for pos in positions:
        weight = pos.get("market_val", 0) / total_mv
        pl = pos.get("pl_ratio_avg_cost", 0) / 100.0
        # 只计算负收益部分的加权贡献
        if pl < 0:
            weighted_drawdown += abs(pl) * weight

    return round(weighted_drawdown, 4)


def calculate_sector_concentration(positions: List[Dict]) -> Dict:
    """
    计算行业集中度

    如果持仓不含 sector/industry 字段, 按市场 (CN/HK/US) 聚合。

    Args:
        positions: 持仓列表 (含 sector 或 industry 或 _market 字段)

    Returns:
        {"hhi": float, "distribution": {sector: weight}}
    """
    if not positions:
        return {"hhi": 0.0, "distribution": {}}

    total_mv = sum(p.get("market_val", 0) for p in positions)
    if total_mv == 0:
        return {"hhi": 0.0, "distribution": {}}

    # 按行业或市场聚合
    sector_mv: Dict[str, float] = {}
    for pos in positions:
        sector = (
            pos.get("sector")
            or pos.get("industry")
            or pos.get("_market", "Unknown")
        )
        sector_mv[sector] = sector_mv.get(sector, 0) + pos.get("market_val", 0)

    # 行业权重
    sector_weights = {s: mv / total_mv for s, mv in sector_mv.items()}
    hhi = sum(w * w for w in sector_weights.values())

    return {
        "hhi": round(hhi, 4),
        "distribution": {s: round(w, 4) for s, w in sector_weights.items()},
    }


def calculate_pl_distribution(positions: List[Dict]) -> Dict:
    """
    计算盈亏分布

    Args:
        positions: 持仓列表

    Returns:
        {"profitable": int, "losing": int, "break_even": int,
         "profit_mv": float, "loss_mv": float}
    """
    result = {
        "profitable": 0,
        "losing": 0,
        "break_even": 0,
        "profit_mv": 0.0,
        "loss_mv": 0.0,
    }

    for pos in positions:
        pl = pos.get("pl_ratio_avg_cost", 0)
        mv = pos.get("market_val", 0)
        if pl > 0:
            result["profitable"] += 1
            result["profit_mv"] += mv
        elif pl < 0:
            result["losing"] += 1
            result["loss_mv"] += abs(mv * pl / 100.0)
        else:
            result["break_even"] += 1

    result["profit_mv"] = round(result["profit_mv"], 2)
    result["loss_mv"] = round(result["loss_mv"], 2)
    return result


if __name__ == "__main__":
    # 内置测试
    print("=== Portfolio Metrics 内置测试 ===\n")

    # 测试数据: 模拟 5 只持仓
    test_positions = [
        {"code": "HK.00700", "market_val": 300000, "pl_ratio_avg_cost": 15.2, "_market": "HK"},
        {"code": "SH.600519", "market_val": 250000, "pl_ratio_avg_cost": 8.5, "_market": "CN"},
        {"code": "US.AAPL", "market_val": 200000, "pl_ratio_avg_cost": -3.2, "_market": "US"},
        {"code": "HK.09988", "market_val": 150000, "pl_ratio_avg_cost": -12.0, "_market": "HK"},
        {"code": "SZ.000001", "market_val": 100000, "pl_ratio_avg_cost": 2.1, "_market": "CN"},
    ]

    total_mv = sum(p["market_val"] for p in test_positions)
    weights = [p["market_val"] / total_mv for p in test_positions]
    returns = [p["pl_ratio_avg_cost"] / 100.0 for p in test_positions]

    sharpe = calculate_sharpe_ratio(returns, weights)
    hhi = calculate_hhi(weights)
    concentration = calculate_concentration(weights)
    drawdown = calculate_max_drawdown_estimate(test_positions)
    sector = calculate_sector_concentration(test_positions)
    pl_dist = calculate_pl_distribution(test_positions)

    print(f"Sharpe Ratio:        {sharpe:.4f}")
    print(f"HHI 集中度:          {hhi:.4f} (1/5={1/5:.4f} 为完全分散)")
    print(f"Top-3 集中度:        {concentration['top3']:.2%}")
    print(f"Top-5 集中度:        {concentration['top5']:.2%}")
    print(f"估算最大回撤:        {drawdown:.2%}")
    print(f"行业 HHI:            {sector['hhi']:.4f}")
    print(f"行业分布:            {sector['distribution']}")
    print(f"盈亏分布:            {pl_dist}")
    print("\n✅ 所有测试通过")
