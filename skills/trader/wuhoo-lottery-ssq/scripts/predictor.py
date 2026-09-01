#!/usr/bin/env python3.11
"""
双色球预测引擎

策略：
1. 频率加权法 — 基于出现频率加权随机采样
2. 遗漏回补法 — 优先选择遗漏值接近历史平均的号码
3. 统计过滤法 — 用统计条件过滤不合理组合
4. 形态匹配法 — 匹配历史高频形态

集成推荐：多策略投票，输出高共识组合
"""

import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.analysis_engine import (
    load_data,
    analyze_frequency,
    analyze_omission,
    analyze_sum,
    analyze_ac_value,
    calculate_ac_value,
    analyze_zone_distribution,
    load_stats,
    run_full_analysis,
)

# 配置目录
CONFIG_DIR = Path(__file__).parent.parent / "configs"
DEFAULT_CONFIG = CONFIG_DIR / "default_config.json"


def load_config() -> dict:
    """加载配置文件"""
    if DEFAULT_CONFIG.exists():
        with open(DEFAULT_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    return get_default_config()


def get_default_config() -> dict:
    """默认配置"""
    return {
        "strategies": {
            "frequency_weighted": {"weight": 0.30, "enabled": True},
            "omission_recovery": {"weight": 0.25, "enabled": True},
            "statistical_filter": {"weight": 0.25, "enabled": True},
            "pattern_matching": {"weight": 0.20, "enabled": True}
        },
        "constraints": {
            "sum_range": [80, 130],
            "ac_range": [4, 9],
            "max_consecutive": 2,
            "odd_even_ratios": ["3:3", "4:2", "2:4"],
            "zone_ratios": ["2:2:2", "2:3:1", "1:3:2", "3:2:1"]
        },
        "blue_ball_strategy": "weighted_omission",
        "generate_count": 5,
        "random_seed": None
    }


def set_seed(seed: int | None = None):
    """设置随机种子"""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)


# =============================================================================
# 策略 1: 频率加权法
# =============================================================================

def strategy_frequency_weighted(stats: dict, config: dict) -> list[dict]:
    """基于频率加权随机选号
    
    热号权重更高，但也保留冷号的随机性
    
    Args:
        stats: 分析结果
        config: 配置
    
    Returns:
        推荐号码列表
    """
    freq = stats.get("frequency", {})
    red_all = freq.get("red_all", {})
    blue_all = freq.get("blue_all", {})
    
    count = config.get("generate_count", 5)
    results = []
    
    for _ in range(count * 3):  # 生成更多候选，后续过滤
        # 红球加权采样
        red_numbers = list(range(1, 34))
        weights = []
        for num in red_numbers:
            key = str(num).zfill(2)
            base_rate = red_all.get(key, {}).get("rate", 3.0)
            # 加权：基础概率 + 随机扰动
            weight = base_rate + random.uniform(0, 2)
            weights.append(weight)
        
        # 归一化权重
        total = sum(weights)
        weights = [w / total for w in weights]
        
        # 采样 6 个不重复红球
        red_selected = random.choices(red_numbers, weights=weights, k=6)
        red_selected = sorted(list(set(red_selected)))
        
        # 如果不足 6 个（去重导致），补足
        while len(red_selected) < 6:
            missing = [n for n in red_numbers if n not in red_selected]
            if missing:
                red_selected.append(random.choice(missing))
                red_selected.sort()
        
        red_selected = red_selected[:6]
        
        # 蓝球加权采样
        blue_numbers = list(range(1, 17))
        blue_weights = []
        for num in blue_numbers:
            key = str(num).zfill(2)
            base_rate = blue_all.get(key, {}).get("rate", 6.25)
            weight = base_rate + random.uniform(0, 3)
            blue_weights.append(weight)
        
        total = sum(blue_weights)
        blue_weights = [w / total for w in blue_weights]
        blue_selected = random.choices(blue_numbers, weights=blue_weights, k=1)[0]
        
        results.append({
            "red": red_selected,
            "blue": blue_selected,
            "strategy": "frequency_weighted"
        })
    
    return results


# =============================================================================
# 策略 2: 遗漏回补法
# =============================================================================

def strategy_omission_recovery(stats: dict, config: dict) -> list[dict]:
    """基于遗漏值回补选号
    
    优先选择遗漏值接近历史平均的号码
    
    Args:
        stats: 分析结果
        config: 配置
    
    Returns:
        推荐号码列表
    """
    omission = stats.get("omission", {})
    red_omission = omission.get("red_omission", {})
    red_max = omission.get("red_max_omission", {})
    red_avg = omission.get("red_avg_omission", 5.5)
    
    blue_omission = omission.get("blue_omission", {})
    blue_max = omission.get("blue_max_omission", {})
    blue_avg = omission.get("blue_avg_omission", 16)
    
    count = config.get("generate_count", 5)
    results = []
    
    for _ in range(count * 3):
        # 红球：遗漏值越接近平均值，权重越高
        red_numbers = list(range(1, 34))
        weights = []
        for num in red_numbers:
            key = str(num).zfill(2)
            current = red_omission.get(key, 0)
            max_om = red_max.get(key, 30)
            
            # 权重 = 1 - |当前遗漏 - 平均遗漏| / 最大遗漏
            deviation = abs(current - red_avg) / max(max_om, 1)
            weight = max(0.1, 1 - deviation)
            weights.append(weight)
        
        total = sum(weights)
        weights = [w / total for w in weights]
        
        red_selected = random.choices(red_numbers, weights=weights, k=6)
        red_selected = sorted(list(set(red_selected)))
        
        while len(red_selected) < 6:
            missing = [n for n in red_numbers if n not in red_selected]
            if missing:
                red_selected.append(random.choice(missing))
                red_selected.sort()
        
        red_selected = red_selected[:6]
        
        # 蓝球
        blue_numbers = list(range(1, 17))
        blue_weights = []
        for num in blue_numbers:
            key = str(num).zfill(2)
            current = blue_omission.get(key, 0)
            max_om = blue_max.get(key, 50)
            
            deviation = abs(current - blue_avg) / max(max_om, 1)
            weight = max(0.1, 1 - deviation)
            blue_weights.append(weight)
        
        total = sum(blue_weights)
        blue_weights = [w / total for w in blue_weights]
        blue_selected = random.choices(blue_numbers, weights=blue_weights, k=1)[0]
        
        results.append({
            "red": red_selected,
            "blue": blue_selected,
            "strategy": "omission_recovery"
        })
    
    return results


# =============================================================================
# 策略 3: 统计过滤法
# =============================================================================

def strategy_statistical_filter(stats: dict, config: dict) -> list[dict]:
    """用统计条件过滤生成合理组合
    
    Args:
        stats: 分析结果
        config: 配置
    
    Returns:
        推荐号码列表
    """
    constraints = config.get("constraints", {})
    sum_range = constraints.get("sum_range", [80, 130])
    ac_range = constraints.get("ac_range", [4, 9])
    max_consec = constraints.get("max_consecutive", 2)
    odd_even = constraints.get("odd_even_ratios", ["3:3", "4:2", "2:4"])
    
    count = config.get("generate_count", 5)
    results = []
    max_attempts = count * 100
    
    for _ in range(max_attempts):
        if len(results) >= count * 3:
            break
        
        # 随机生成
        red_selected = sorted(random.sample(range(1, 34), 6))
        blue_selected = random.randint(1, 16)
        
        # 检查和值
        red_sum = sum(red_selected)
        if not (sum_range[0] <= red_sum <= sum_range[1]):
            continue
        
        # 检查 AC值
        ac = calculate_ac_value(red_selected)
        if not (ac_range[0] <= ac <= ac_range[1]):
            continue
        
        # 检查连号
        consec = 0
        for i in range(5):
            if red_selected[i + 1] - red_selected[i] == 1:
                consec += 1
        if consec > max_consec:
            continue
        
        # 检查奇偶比
        odd_count = sum(1 for x in red_selected if x % 2 == 1)
        even_count = 6 - odd_count
        ratio = f"{odd_count}:{even_count}"
        if ratio not in odd_even:
            continue
        
        results.append({
            "red": red_selected,
            "blue": blue_selected,
            "strategy": "statistical_filter"
        })
    
    return results


# =============================================================================
# 策略 4: 形态匹配法
# =============================================================================

def strategy_pattern_matching(stats: dict, config: dict) -> list[dict]:
    """基于历史高频形态匹配选号
    
    Args:
        stats: 分析结果
        config: 配置
    
    Returns:
        推荐号码列表
    """
    freq = stats.get("frequency", {})
    zone = stats.get("zone", {})
    red_sorted = freq.get("red_sorted_desc", [])
    
    count = config.get("generate_count", 5)
    results = []
    
    # 获取推荐三区比
    recommended_ratio = zone.get("recommended_ratio", "2:2:2")
    try:
        z1, z2, z3 = map(int, recommended_ratio.split(":"))
    except ValueError:
        z1, z2, z3 = 2, 2, 2
    
    # 分区号码
    zone1 = [n for n in range(1, 12)]
    zone2 = [n for n in range(12, 23)]
    zone3 = [n for n in range(23, 34)]
    
    for _ in range(count * 3):
        # 按推荐比例从各区选取
        r1 = random.sample(zone1, min(z1, len(zone1)))
        r2 = random.sample(zone2, min(z2, len(zone2)))
        r3 = random.sample(zone3, min(z3, len(zone3)))
        
        red_selected = sorted(r1 + r2 + r3)
        if len(red_selected) != 6:
            continue
        
        # 蓝球：优先选热号
        hot_blue = freq.get("hot_blue", [])
        if hot_blue and random.random() < 0.7:
            blue_selected = int(random.choice(hot_blue))
        else:
            blue_selected = random.randint(1, 16)
        
        results.append({
            "red": red_selected,
            "blue": blue_selected,
            "strategy": "pattern_matching"
        })
    
    return results


# =============================================================================
# 策略 5: 搏大奖策略 (胆拖+热号集中)
# =============================================================================

def strategy_big_prize(stats: dict, config: dict) -> list[dict]:
    """搏大奖策略 — 胆拖+热号集中
    
    核心思路：
    1. 选3个最热红球作为胆码（必须出现）
    2. 从热号池(10-12个)中选3个作为拖码
    3. 蓝球选最热3个
    4. 生成多注组合，提高中大奖概率
    
    Args:
        stats: 分析结果
        config: 配置
    
    Returns:
        推荐号码列表
    """
    import itertools
    
    freq = stats.get("frequency", {})
    red_all = freq.get("red_all", {})
    blue_all = freq.get("blue_all", {})
    
    count = config.get("generate_count", 5)
    
    # 获取最热红球 (前12个)
    hot_reds = sorted([
        int(k) for k, v in sorted(
            red_all.items(), 
            key=lambda x: x[1].get("rate", 0), 
            reverse=True
        )[:12]
    ])
    
    # 胆码：最热3个
    dan_ma = hot_reds[:3]
    # 拖码：剩余热号
    tuo_ma = hot_reds[3:]
    
    # 最热蓝球 (前3个)
    hot_blues = sorted([
        int(k) for k, v in sorted(
            blue_all.items(),
            key=lambda x: x[1].get("rate", 0),
            reverse=True
        )[:3]
    ])
    
    results = []
    
    # 生成胆拖组合：C(9,3) = 84种
    for combo in itertools.combinations(tuo_ma, 3):
        red_balls = sorted(dan_ma + list(combo))
        
        # 每个红球组合配3个蓝球
        for blue in hot_blues:
            results.append({
                "red": red_balls,
                "blue": blue,
                "strategy": "big_prize"
            })
            
            if len(results) >= count * 3:  # 生成足够候选
                break
        if len(results) >= count * 3:
            break
    
    # 如果不足，随机补充
    while len(results) < count * 3:
        red = sorted(random.sample(hot_reds, 6))
        blue = random.choice(hot_blues)
        results.append({
            "red": red,
            "blue": blue,
            "strategy": "big_prize"
        })
    
    return results


# =============================================================================
# 策略 6: 大遗漏反弹法
# =============================================================================

def strategy_cold_rebound(stats: dict, config: dict) -> list[dict]:
    """大遗漏反弹策略 — 追高遗漏冷号
    
    核心思路：号码不会无限遗漏，当遗漏值接近历史最大值时，
    反弹概率增加。本策略专门选取当前遗漏值最高的冷号。
    
    Args:
        stats: 分析结果
        config: 配置
    
    Returns:
        推荐号码列表
    """
    omission = stats.get("omission", {})
    red_omission = omission.get("red_omission", {})
    red_max = omission.get("red_max_omission", {})
    blue_omission = omission.get("blue_omission", {})
    
    count = config.get("generate_count", 5)
    results = []
    
    # 红球：遗漏值越高，权重越大
    red_numbers = list(range(1, 34))
    for _ in range(count * 3):
        weights = []
        for num in red_numbers:
            key = str(num).zfill(2)
            current = red_omission.get(key, 0)
            max_om = red_max.get(key, 30)
            # 权重 = 当前遗漏 / 历史最大遗漏（越接近历史极限，反弹概率越高）
            ratio = current / max(max_om, 1)
            weight = ratio ** 2  # 平方放大差异
            weights.append(max(0.05, weight))
        
        total = sum(weights)
        weights = [w / total for w in weights]
        
        red_selected = random.choices(red_numbers, weights=weights, k=6)
        red_selected = sorted(list(set(red_selected)))
        while len(red_selected) < 6:
            missing = [n for n in red_numbers if n not in red_selected]
            if missing:
                red_selected.append(random.choice(missing))
                red_selected.sort()
        red_selected = red_selected[:6]
        
        # 蓝球：确定性选最高遗漏的前几个，轮换使用
        blue_sorted = sorted(blue_omission.items(), key=lambda x: x[1], reverse=True)
        top_cold_blues = [int(k) for k, v in blue_sorted[:5]]  # 遗漏最高的5个蓝球
        idx = len(results) % len(top_cold_blues)
        blue_selected = top_cold_blues[idx]
        
        results.append({
            "red": red_selected,
            "blue": blue_selected,
            "strategy": "cold_rebound"
        })
    
    return results


# =============================================================================
# 蓝球推荐
# =============================================================================

def recommend_blue_ball(stats: dict, strategy: str = "weighted_omission") -> list[dict]:
    """蓝球推荐
    
    Args:
        stats: 分析结果
        strategy: 推荐策略
    
    Returns:
        蓝球推荐列表（按优先级排序）
    """
    freq = stats.get("frequency", {})
    omission = stats.get("omission", {})
    
    blue_all = freq.get("blue_all", {})
    blue_omission = omission.get("blue_omission", {})
    blue_avg = omission.get("blue_avg_omission", 16)
    
    recommendations = []
    
    for num in range(1, 17):
        key = str(num).zfill(2)
        rate = blue_all.get(key, {}).get("rate", 6.25)
        current_omission = blue_omission.get(key, 0)
        
        # 综合评分
        if strategy == "cold_blue":
            # 真正的高遗漏优先：遗漏值越高，评分越高
            score = (current_omission / 100) * 50 + rate * 0.5
        elif strategy == "weighted_omission" or strategy == "balanced":
            # 接近平均遗漏 + 频率加权
            score = rate * 0.5 + (1 - abs(current_omission - blue_avg) / 50) * 50
        elif strategy == "hot":
            score = rate
        else:
            score = rate * 0.5 + (1 - abs(current_omission - blue_avg) / 50) * 50
        
        recommendations.append({
            "number": num,
            "key": key,
            "score": round(score, 2),
            "rate": rate,
            "omission": current_omission
        })
    
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations[:8]


# =============================================================================
# 集成推荐
# =============================================================================

def generate_predictions(stats: dict, config: dict | None = None, count: int = 5) -> list[dict]:
    """生成集成预测结果
    
    Args:
        stats: 分析结果
        config: 配置
        count: 生成注数
    
    Returns:
        预测结果列表
    """
    if config is None:
        config = load_config()
    
    config["generate_count"] = count
    
    # 设置随机种子
    seed = config.get("random_seed")
    set_seed(seed)
    
    all_candidates = []
    strategies = config.get("strategies", {})
    
    # 运行各策略
    if strategies.get("frequency_weighted", {}).get("enabled", True):
        cands = strategy_frequency_weighted(stats, config)
        for c in cands:
            c["weight"] = strategies["frequency_weighted"]["weight"]
        all_candidates.extend(cands)
    
    if strategies.get("omission_recovery", {}).get("enabled", True):
        cands = strategy_omission_recovery(stats, config)
        for c in cands:
            c["weight"] = strategies["omission_recovery"]["weight"]
        all_candidates.extend(cands)
    
    if strategies.get("statistical_filter", {}).get("enabled", True):
        cands = strategy_statistical_filter(stats, config)
        for c in cands:
            c["weight"] = strategies["statistical_filter"]["weight"]
        all_candidates.extend(cands)
    
    if strategies.get("pattern_matching", {}).get("enabled", True):
        cands = strategy_pattern_matching(stats, config)
        for c in cands:
            c["weight"] = strategies["pattern_matching"]["weight"]
        all_candidates.extend(cands)

    if strategies.get("big_prize", {}).get("enabled", False):
        cands = strategy_big_prize(stats, config)
        for c in cands:
            c["weight"] = strategies["big_prize"]["weight"]
        all_candidates.extend(cands)

    if strategies.get("cold_rebound", {}).get("enabled", False):
        cands = strategy_cold_rebound(stats, config)
        for c in cands:
            c["weight"] = strategies["cold_rebound"]["weight"]
        all_candidates.extend(cands)
    
    # ================================================================
    # 投票与合并 (v2): 每策略贡献 top-N 候选，确保多样性
    # ================================================================
    per_strategy = {}
    for cand in all_candidates:
        strat = cand["strategy"]
        if strat not in per_strategy:
            per_strategy[strat] = []
        per_strategy[strat].append(cand)

    # 每策略内部去重后取 top-N
    strategy_top = {}
    for strat, cands in per_strategy.items():
        seen = set()
        unique_cands = []
        for c in cands:
            key = (tuple(c["red"]), c["blue"])
            if key not in seen:
                seen.add(key)
                unique_cands.append(c)
        # 每策略至少 1 个（当 count >= 策略数时）
        num_strategies = len(per_strategy)
        per_count = max(1, count // num_strategies)
        # 确保总数 >= count
        if per_count * num_strategies < count:
            per_count += 1
        strategy_top[strat] = unique_cands[:per_count]
    
    # 合并所有策略 top，去重
    combo_map = {}
    for strat, cands in strategy_top.items():
        for c in cands:
            key = (tuple(c["red"]), c["blue"])
            if key not in combo_map:
                combo_map[key] = {
                    "red": list(c["red"]),
                    "blue": c["blue"],
                    "strategies": set(),
                    "total_weight": 0,
                    "votes": 0,
                }
            combo_map[key]["strategies"].add(strat)
            combo_map[key]["total_weight"] += c.get("weight", 0.1)
            combo_map[key]["votes"] += 1
    
    # 按策略共识度排序（多策略共识优先）
    sorted_combos = sorted(
        combo_map.values(),
        key=lambda x: (len(x["strategies"]), x["total_weight"]),
        reverse=True
    )
    
    # v3: 策略多样性优先 — 每策略确保至少 1 注代表
    results = []
    used_strategies = set()
    remaining = []
    
    for combo in sorted_combos:
        combo_strats = set(combo["strategies"])
        new_strats = combo_strats - used_strategies
        if new_strats and len(results) < count:
            results.append({
                "red": list(combo["red"]),
                "blue": combo["blue"],
                "strategies": list(combo_strats),
                "total_weight": combo["total_weight"],
                "votes": combo["votes"],
            })
            used_strategies.update(combo_strats)
        else:
            remaining.append(combo)
    
    # 如不足 count，按共识度从剩余中补足
    seen_keys = {(tuple(r["red"]), r["blue"]) for r in results}
    for combo in remaining:
        if len(results) >= count:
            break
        key = (tuple(combo["red"]), combo["blue"])
        if key not in seen_keys:
            results.append({
                "red": list(combo["red"]),
                "blue": combo["blue"],
                "strategies": list(combo["strategies"]),
                "total_weight": combo["total_weight"],
                "votes": combo["votes"],
            })
            seen_keys.add(key)
    
    # 如果不足 count 注，补充随机组合
    while len(results) < count:
        red = sorted(random.sample(range(1, 34), 6))
        blue = random.randint(1, 16)
        results.append({
            "red": red,
            "blue": blue,
            "votes": 0,
            "strategies": ["random_fill"],
            "total_weight": 0.1
        })
    
    return results


def get_blue_recommendations(stats: dict, count: int = 5, strategy: str = "cold_blue") -> list[dict]:
    """获取蓝球推荐"""
    recs = recommend_blue_ball(stats, strategy=strategy)
    return recs[:count]


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="双色球预测")
    parser.add_argument("--count", type=int, default=5, help="生成注数")
    parser.add_argument("--update", action="store_true", help="先更新数据")
    parser.add_argument("--seed", type=int, help="随机种子")
    
    args = parser.parse_args()
    
    # 更新数据
    if args.update:
        from scripts.fetch_history import fetch_incremental
        fetch_incremental()
    
    # 加载数据和分析
    print("📊 加载数据...")
    df = load_data()
    print(f"  数据量: {len(df)} 期")
    
    print("📊 运行分析...")
    stats = run_full_analysis(df)
    
    if args.seed:
        config = load_config()
        config["random_seed"] = args.seed
    else:
        config = None
    
    # 生成预测
    print(f"\n🎯 生成 {args.count} 注预测...")
    predictions = generate_predictions(stats, config, count=args.count)
    
    print("\n" + "=" * 50)
    print(f"  双色球预测 — 下期推荐 ({args.count}注)")
    print("=" * 50)
    
    for i, pred in enumerate(predictions, 1):
        red_str = " ".join(str(x).zfill(2) for x in pred["red"])
        blue_str = str(pred["blue"]).zfill(2)
        strategies = ", ".join(pred["strategies"])
        print(f"  注{i}: 🔴 {red_str} | 🔵 {blue_str}")
        print(f"        策略: {strategies}")
    
    # 蓝球推荐
    print("\n🔵 蓝球推荐:")
    blue_recs = get_blue_recommendations(stats, count=5)
    for rec in blue_recs:
        print(f"  {rec['key']}: 评分 {rec['score']}, 遗漏 {rec['omission']} 期")
