#!/usr/bin/env python3.11
"""
蒙特卡洛回测模块

用历史数据验证策略表现：
- 滚动窗口回测
- 多策略对比
- ROI 统计
"""

import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.analysis_engine import (
    load_data,
    analyze_frequency,
    analyze_omission,
    run_full_analysis,
    calculate_ac_value,
)
from scripts.predictor import (
    strategy_frequency_weighted,
    strategy_omission_recovery,
    strategy_statistical_filter,
    strategy_pattern_matching,
    strategy_big_prize,
    generate_predictions,
    get_default_config,
)

# 奖级奖金（固定部分，浮动奖按平均值估算）
PRIZE_STRUCTURE = {
    1: {"match": "6+1", "amount": 5_000_000, "desc": "一等奖"},  # 浮动，估算
    2: {"match": "6+0", "amount": 150_000, "desc": "二等奖"},
    3: {"match": "5+1", "amount": 3_000, "desc": "三等奖"},
    4: {"match": "5+0/4+1", "amount": 200, "desc": "四等奖"},
    5: {"match": "4+0/3+1", "amount": 10, "desc": "五等奖"},
    6: {"match": "2+1/1+1/0+1", "amount": 5, "desc": "六等奖"},
}


def check_prize(red_balls: list[int], blue_ball: int, 
                draw_red: list[int], draw_blue: int) -> tuple[int, int]:
    """检查中奖情况
    
    Args:
        red_balls: 预测红球
        blue_ball: 预测蓝球
        draw_red: 开奖红球
        draw_blue: 开奖蓝球
    
    Returns:
        (奖级, 奖金), 未中奖返回 (0, 0)
    """
    red_match = len(set(red_balls) & set(draw_red))
    blue_match = 1 if blue_ball == draw_blue else 0
    
    if red_match == 6 and blue_match == 1:
        return (1, PRIZE_STRUCTURE[1]["amount"])
    elif red_match == 6:
        return (2, PRIZE_STRUCTURE[2]["amount"])
    elif red_match == 5 and blue_match == 1:
        return (3, PRIZE_STRUCTURE[3]["amount"])
    elif (red_match == 5 and blue_match == 0) or (red_match == 4 and blue_match == 1):
        return (4, PRIZE_STRUCTURE[4]["amount"])
    elif (red_match == 4 and blue_match == 0) or (red_match == 3 and blue_match == 1):
        return (5, PRIZE_STRUCTURE[5]["amount"])
    elif (red_match == 2 and blue_match == 1) or \
         (red_match == 1 and blue_match == 1) or \
         (red_match == 0 and blue_match == 1):
        return (6, PRIZE_STRUCTURE[6]["amount"])
    
    return (0, 0)


def _compute_window_stats(df: pd.DataFrame, window_size: int = 100,
                          periods: int = 100) -> list[dict | None]:
    """预计算所有回测窗口的分析结果（跨策略共享）
    
    Args:
        df: 全量历史数据
        window_size: 回看窗口大小
        periods: 回测期数
    
    Returns:
        列表，索引对应 df 中的位置，值为 stats dict 或 None
    """
    total_periods = len(df)
    start_idx = total_periods - periods - window_size
    if start_idx < 0:
        start_idx = 0
    
    cache: list[tuple[int, dict | None]] = []
    
    for i in range(start_idx, total_periods - 1):
        window_df = df.iloc[max(0, i - window_size):i].copy()
        if len(window_df) < 50:
            cache.append((i, None))
            continue
        try:
            stats = run_full_analysis(window_df, save=False, verbose=False)
            cache.append((i, stats))
        except Exception:
            cache.append((i, None))
    
    return cache


def backtest_strategy(stats_cache: list[tuple[int, dict | None]], 
                      df: pd.DataFrame, strategy_name: str,
                      predict_count: int = 5,
                      periods: int = 100,
                      random_seed: int | None = None) -> dict:
    """回测单个策略（使用预计算的 stats 缓存）
    
    Args:
        stats_cache: 预计算的分析结果缓存
        df: 历史数据
        strategy_name: 策略名称
        predict_count: 每期预测注数
        periods: 回测期数
        random_seed: 随机种子
    
    Returns:
        回测结果
    """
    if random_seed is not None:
        random.seed(random_seed)
        np.random.seed(random_seed)
    
    results = {
        "strategy": strategy_name,
        "periods": 0,
        "total_cost": 0,
        "total_prize": 0,
        "wins": defaultdict(int),
        "win_details": []
    }
    
    # 将 cache 转为 dict 以便快速查找
    stats_map: dict[int, dict | None] = dict(stats_cache)
    
    for idx, stats in stats_cache:
        if results["periods"] >= periods:
            break
        
        if stats is None:
            continue
        
        # 根据策略生成预测
        config = get_default_config()
        config["generate_count"] = predict_count
        config["random_seed"] = random_seed + idx if random_seed else None
        
        if strategy_name == "frequency_weighted":
            predictions = strategy_frequency_weighted(stats, config)
        elif strategy_name == "omission_recovery":
            predictions = strategy_omission_recovery(stats, config)
        elif strategy_name == "statistical_filter":
            predictions = strategy_statistical_filter(stats, config)
        elif strategy_name == "pattern_matching":
            predictions = strategy_pattern_matching(stats, config)
        elif strategy_name == "big_prize":
            predictions = strategy_big_prize(stats, config)
        elif strategy_name == "integrated":
            predictions = generate_predictions(stats, config, count=predict_count)
        elif strategy_name == "random":
            # 纯随机基准
            predictions = []
            for _ in range(predict_count):
                predictions.append({
                    "red": sorted(random.sample(range(1, 34), 6)),
                    "blue": random.randint(1, 16),
                    "strategy": "random"
                })
        else:
            continue
        
        predictions = predictions[:predict_count]
        
        # 获取实际开奖结果
        actual_draw = df.iloc[idx + 1]
        draw_red = [actual_draw[f"红{j}"] for j in range(1, 7)]
        draw_blue = actual_draw["蓝球"]
        
        # 检查每注中奖情况
        cost = predict_count * 2  # 每注 2 元
        prize = 0
        
        for pred in predictions:
            prize_level, prize_amount = check_prize(
                pred["red"], pred["blue"], draw_red, draw_blue
            )
            prize += prize_amount
            if prize_level > 0:
                results["wins"][prize_level] += 1
                results["win_details"].append({
                    "period": actual_draw["期号"],
                    "level": prize_level,
                    "amount": prize_amount,
                    "predicted": pred["red"],
                    "actual": draw_red,
                    "blue_pred": pred["blue"],
                    "blue_actual": draw_blue
                })
        
        results["periods"] += 1
        results["total_cost"] += cost
        results["total_prize"] += prize
    
    # 计算 ROI
    results["roi"] = round((results["total_prize"] - results["total_cost"]) / results["total_cost"] * 100, 2) if results["total_cost"] > 0 else 0
    results["win_rate"] = round(sum(results["wins"].values()) / results["periods"] * 100, 2) if results["periods"] > 0 else 0
    results["avg_cost_per_period"] = round(results["total_cost"] / results["periods"], 2) if results["periods"] > 0 else 0
    results["avg_prize_per_period"] = round(results["total_prize"] / results["periods"], 2) if results["periods"] > 0 else 0
    
    return results


def run_comparison(df: pd.DataFrame, periods: int = 100, 
                   predict_count: int = 5) -> list[dict]:
    """多策略对比回测（预计算分析结果，跨策略共享）
    
    Args:
        df: 历史数据
        periods: 回测期数
        predict_count: 每期预测注数
    
    Returns:
        各策略回测结果
    """
    strategies = [
        "random",
        "frequency_weighted",
        "omission_recovery",
        "statistical_filter",
        "pattern_matching",
        "integrated",
        "big_prize"
    ]
    
    # 预计算所有窗口的分析结果（只算一次）
    print("  📊 预计算分析窗口...")
    stats_cache = _compute_window_stats(df, window_size=100, periods=periods)
    print(f"  ✅ 已预计算 {len(stats_cache)} 个窗口")
    
    results = []
    
    for strategy in strategies:
        print(f"  🔄 回测策略: {strategy}...")
        result = backtest_strategy(
            stats_cache, df, strategy,
            predict_count=predict_count,
            periods=periods,
            random_seed=42
        )
        results.append(result)
    
    return results


def monte_carlo_simulation(df: pd.DataFrame, simulations: int = 1000,
                           predict_count: int = 5) -> dict:
    """蒙特卡洛模拟
    
    随机模拟多次购买，统计长期表现
    
    Args:
        df: 历史数据（用于获取开奖分布）
        simulations: 模拟次数
        predict_count: 每次模拟购买注数
    
    Returns:
        模拟结果
    """
    # 从历史数据中提取开奖分布
    reds = []
    blues = []
    for _, row in df.iterrows():
        reds.append([row[f"红{i}"] for i in range(1, 7)])
        blues.append(row["蓝球"])
    
    total_cost = 0
    total_prize = 0
    win_counts = defaultdict(int)
    roi_list = []
    
    for sim in range(simulations):
        # 随机选一注（模拟随机购买）
        pred_red = sorted(random.sample(range(1, 34), 6))
        pred_blue = random.randint(1, 16)
        
        # 随机选一期开奖结果
        idx = random.randint(0, len(reds) - 1)
        draw_red = reds[idx]
        draw_blue = blues[idx]
        
        cost = predict_count * 2
        prize = 0
        
        for _ in range(predict_count):
            # 每次模拟生成不同的随机号码
            sim_red = sorted(random.sample(range(1, 34), 6))
            sim_blue = random.randint(1, 16)
            
            level, amount = check_prize(sim_red, sim_blue, draw_red, draw_blue)
            prize += amount
            if level > 0:
                win_counts[level] += 1
        
        total_cost += cost
        total_prize += prize
        roi_list.append((prize - cost) / cost * 100 if cost > 0 else 0)
    
    return {
        "simulations": simulations,
        "predict_per_sim": predict_count,
        "total_cost": total_cost,
        "total_prize": total_prize,
        "roi": round((total_prize - total_cost) / total_cost * 100, 2) if total_cost > 0 else 0,
        "wins": dict(win_counts),
        "win_rate": round(sum(win_counts.values()) / (simulations * predict_count) * 100, 2),
        "avg_roi": round(np.mean(roi_list), 2),
        "std_roi": round(np.std(roi_list), 2),
        "max_roi": round(max(roi_list), 2),
        "min_roi": round(min(roi_list), 2),
    }


def print_backtest_report(results: list[dict]):
    """打印回测报告"""
    print("\n" + "=" * 60)
    print("  📊 策略回测对比报告")
    print("=" * 60)
    
    print(f"\n{'策略':<20} {'期数':>6} {'总投入':>10} {'总奖金':>10} {'ROI':>8} {'中奖率':>8}")
    print("-" * 60)
    
    for r in results:
        strategy_name = r["strategy"]
        name_map = {
            "random": "随机基准",
            "frequency_weighted": "频率加权",
            "omission_recovery": "遗漏回补",
            "statistical_filter": "统计过滤",
            "pattern_matching": "形态匹配",
            "integrated": "集成推荐",
            "big_prize": "搏大奖(胆拖)"
        }
        name = name_map.get(strategy_name, strategy_name)
        
        print(f"{name:<20} {r['periods']:>6} {r['total_cost']:>10.0f} {r['total_prize']:>10.0f} "
              f"{r['roi']:>7.2f}% {r['win_rate']:>7.2f}%")
    
    print("\n" + "-" * 60)
    print("⚠️  注意: 所有策略期望值均为负，历史表现不代表未来")
    print("   彩票为负期望值游戏，请理性购买")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="双色球策略回测")
    parser.add_argument("--periods", type=int, default=100, help="回测期数")
    parser.add_argument("--monte-carlo", type=int, default=0, help="蒙特卡洛模拟次数")
    parser.add_argument("--count", type=int, default=5, help="每期预测注数")
    
    args = parser.parse_args()
    
    print("📊 加载数据...")
    df = load_data()
    print(f"  数据量: {len(df)} 期")
    
    if args.monte_carlo > 0:
        print(f"\n🎲 蒙特卡洛模拟 ({args.monte_carlo} 次)...")
        mc_result = monte_carlo_simulation(df, simulations=args.monte_carlo, predict_count=args.count)
        print(f"\n  模拟次数: {mc_result['simulations']}")
        print(f"  平均 ROI: {mc_result['avg_roi']:.2f}%")
        print(f"  ROI 标准差: {mc_result['std_roi']:.2f}%")
        print(f"  最大 ROI: {mc_result['max_roi']:.2f}%")
        print(f"  最小 ROI: {mc_result['min_roi']:.2f}%")
        print(f"  总体 ROI: {mc_result['roi']:.2f}%")
    else:
        print(f"\n🔄 策略回测 ({args.periods} 期)...")
        results = run_comparison(df, periods=args.periods, predict_count=args.count)
        print_backtest_report(results)
