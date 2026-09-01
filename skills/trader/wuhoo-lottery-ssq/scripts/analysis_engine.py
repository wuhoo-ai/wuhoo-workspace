#!/usr/bin/env python3.11
"""
双色球统计分析引擎

分析维度：
1. 频率分析 (热号/温号/冷号)
2. 遗漏分析 (当前遗漏 + 历史最大遗漏)
3. 区间分布 (三区比)
4. 奇偶比
5. 和值分析
6. AC值 (号码复杂度)
7. 连号分析
8. 重号分析 (上期重复)
9. 蓝球专项分析
10. 历史同期对比
"""

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

# 数据目录
DATA_DIR = Path(__file__).parent.parent / "data"
STATS_FILE = DATA_DIR / "ssq_stats.json"


def load_data() -> pd.DataFrame:
    """加载历史开奖数据"""
    history_file = DATA_DIR / "ssq_history.csv"
    if not history_file.exists():
        raise FileNotFoundError(f"数据文件不存在: {history_file}")
    
    df = pd.read_csv(history_file, dtype={"期号": str})
    df = df.sort_values("期号").reset_index(drop=True)
    return df


def get_red_balls(df: pd.DataFrame) -> list[list[int]]:
    """提取所有期次的红球组合"""
    cols = [f"红{i}" for i in range(1, 7)]
    return df[cols].values.tolist()


def get_blue_balls(df: pd.DataFrame) -> list[int]:
    """提取所有期次的蓝球"""
    return df["蓝球"].tolist()


# =============================================================================
# 1. 频率分析
# =============================================================================

def analyze_frequency(df: pd.DataFrame, recent_n: int | None = None) -> dict:
    """红球和蓝球频率分析
    
    Args:
        df: 历史数据
        recent_n: 仅分析最近 N 期，None 表示全量
    
    Returns:
        频率统计结果
    """
    if recent_n:
        df = df.tail(recent_n)
    
    reds = get_red_balls(df)
    blues = get_blue_balls(df)
    
    # 红球频率
    red_counter = Counter()
    for draw in reds:
        red_counter.update(draw)
    
    # 蓝球频率
    blue_counter = Counter(blues)
    
    # 红球统计
    red_stats = {}
    for num in range(1, 34):
        count = red_counter.get(num, 0)
        red_stats[str(num).zfill(2)] = {
            "count": count,
            "rate": round(count / len(df) * 100, 2) if len(df) > 0 else 0
        }
    
    # 蓝球统计
    blue_stats = {}
    for num in range(1, 17):
        count = blue_counter.get(num, 0)
        blue_stats[str(num).zfill(2)] = {
            "count": count,
            "rate": round(count / len(df) * 100, 2) if len(df) > 0 else 0
        }
    
    # 排序
    red_sorted = sorted(red_stats.items(), key=lambda x: x[1]["count"], reverse=True)
    blue_sorted = sorted(blue_stats.items(), key=lambda x: x[1]["count"], reverse=True)
    
    # 热号 (Top 10) / 冷号 (Bottom 10)
    hot_red = [x[0] for x in red_sorted[:10]]
    cold_red = [x[0] for x in red_sorted[-10:]]
    hot_blue = [x[0] for x in blue_sorted[:5]]
    cold_blue = [x[0] for x in blue_sorted[-5:]]
    
    return {
        "red_all": red_stats,
        "blue_all": blue_stats,
        "hot_red": hot_red,
        "cold_red": cold_red,
        "hot_blue": hot_blue,
        "cold_blue": cold_blue,
        "red_sorted_desc": [x[0] for x in red_sorted],
        "blue_sorted_desc": [x[0] for x in blue_sorted],
        "total_draws": len(df),
        "period": f"最近{recent_n}期" if recent_n else "全量"
    }


# =============================================================================
# 2. 遗漏分析
# =============================================================================

def analyze_omission(df: pd.DataFrame) -> dict:
    """号码遗漏分析
    
    Args:
        df: 历史数据（按期号升序）
    
    Returns:
        遗漏统计结果
    """
    reds = get_red_balls(df)
    blues = get_blue_balls(df)
    total = len(df)
    
    # 红球遗漏
    red_omission = {}
    red_max_omission = {}
    red_last_seen = {}
    
    for num in range(1, 34):
        current_omission = 0
        max_omission = 0
        last_seen_idx = -1
        temp_omission = 0
        
        for i in range(total - 1, -1, -1):
            if num in reds[i]:
                if temp_omission > max_omission:
                    max_omission = temp_omission
                temp_omission = 0
                if last_seen_idx == -1:
                    current_omission = total - 1 - i
                    red_last_seen[num] = df.iloc[i]["期号"]
            else:
                temp_omission += 1
        
        # 如果从未出现（理论上不会）
        if temp_omission > max_omission:
            max_omission = temp_omission
        if num not in red_last_seen:
            current_omission = total
        
        red_omission[str(num).zfill(2)] = current_omission
        red_max_omission[str(num).zfill(2)] = max_omission
    
    # 蓝球遗漏
    blue_omission = {}
    blue_max_omission = {}
    blue_last_seen = {}
    
    for num in range(1, 17):
        current_omission = 0
        max_omission = 0
        temp_omission = 0
        
        for i in range(total - 1, -1, -1):
            if blues[i] == num:
                if temp_omission > max_omission:
                    max_omission = temp_omission
                temp_omission = 0
                if num not in blue_last_seen:
                    current_omission = total - 1 - i
                    blue_last_seen[num] = df.iloc[i]["期号"]
            else:
                temp_omission += 1
        
        if temp_omission > max_omission:
            max_omission = temp_omission
        if num not in blue_last_seen:
            current_omission = total
        
        blue_omission[str(num).zfill(2)] = current_omission
        blue_max_omission[str(num).zfill(2)] = max_omission
    
    # 高遗漏号码（当前遗漏 > 历史平均遗漏）
    red_avg_omission = sum(red_omission.values()) / 33
    blue_avg_omission = sum(blue_omission.values()) / 16
    
    high_omission_red = [k for k, v in red_omission.items() if v > red_avg_omission]
    high_omission_blue = [k for k, v in blue_omission.items() if v > blue_avg_omission]
    
    return {
        "red_omission": red_omission,
        "red_max_omission": red_max_omission,
        "blue_omission": blue_omission,
        "blue_max_omission": blue_max_omission,
        "red_avg_omission": round(red_avg_omission, 1),
        "blue_avg_omission": round(blue_avg_omission, 1),
        "high_omission_red": sorted(high_omission_red),
        "high_omission_blue": sorted(high_omission_blue),
    }


# =============================================================================
# 3. 区间分布 (三区比)
# =============================================================================

def analyze_zone_distribution(df: pd.DataFrame) -> dict:
    """三区分布分析
    
    一区: 1-11, 二区: 12-22, 三区: 23-33
    
    Args:
        df: 历史数据
    
    Returns:
        区间分布统计
    """
    reds = get_red_balls(df)
    
    zone_counts = {"一区(1-11)": 0, "二区(12-22)": 0, "三区(23-33)": 0}
    zone_ratios = Counter()
    
    for draw in reds:
        zone1 = sum(1 for x in draw if x <= 11)
        zone2 = sum(1 for x in draw if 12 <= x <= 22)
        zone3 = sum(1 for x in draw if x >= 23)
        
        zone_counts["一区(1-11)"] += zone1
        zone_counts["二区(12-22)"] += zone2
        zone_counts["三区(23-33)"] += zone3
        
        zone_ratios[f"{zone1}:{zone2}:{zone3}"] += 1
    
    total = len(df) * 6
    zone_pct = {k: round(v / total * 100, 1) for k, v in zone_counts.items()}
    
    # 最常见的三区比
    common_ratios = zone_ratios.most_common(10)
    
    return {
        "zone_counts": zone_counts,
        "zone_pct": zone_pct,
        "common_ratios": [{"ratio": r, "count": c, "rate": round(c/len(df)*100, 1)} 
                          for r, c in common_ratios],
        "recommended_ratio": common_ratios[0][0] if common_ratios else "2:2:2"
    }


# =============================================================================
# 4. 奇偶比
# =============================================================================

def analyze_odd_even(df: pd.DataFrame) -> dict:
    """奇偶比分析
    
    Args:
        df: 历史数据
    
    Returns:
        奇偶比统计
    """
    reds = get_red_balls(df)
    odd_even_ratios = Counter()
    
    for draw in reds:
        odd_count = sum(1 for x in draw if x % 2 == 1)
        even_count = 6 - odd_count
        odd_even_ratios[f"{odd_count}:{even_count}"] += 1
    
    common = odd_even_ratios.most_common()
    
    return {
        "ratios": [{"ratio": r, "count": c, "rate": round(c/len(df)*100, 1)} 
                   for r, c in common],
        "recommended": common[0][0] if common else "3:3"
    }


# =============================================================================
# 5. 和值分析
# =============================================================================

def analyze_sum(df: pd.DataFrame) -> dict:
    """红球和值分析
    
    Args:
        df: 历史数据
    
    Returns:
        和值统计
    """
    reds = get_red_balls(df)
    sums = [sum(draw) for draw in reds]
    
    sum_series = pd.Series(sums)
    
    # 和值分布区间
    bins = list(range(60, 181, 10))
    hist = pd.cut(sum_series, bins=bins).value_counts().sort_index()
    
    sum_distribution = []
    for interval, count in hist.items():
        sum_distribution.append({
            "range": str(interval),
            "count": int(count),
            "rate": round(count / len(df) * 100, 1)
        })
    
    # 推荐和值区间（覆盖 70% 数据的区间）
    sorted_intervals = sorted(sum_distribution, key=lambda x: x["count"], reverse=True)
    cumulative = 0
    recommended_ranges = []
    for item in sorted_intervals:
        cumulative += item["rate"]
        recommended_ranges.append(item["range"])
        if cumulative >= 70:
            break
    
    return {
        "mean": round(sum_series.mean(), 1),
        "median": int(sum_series.median()),
        "std": round(sum_series.std(), 1),
        "min": int(sum_series.min()),
        "max": int(sum_series.max()),
        "distribution": sum_distribution,
        "recommended_range": f"{min(sums)}-{max(sums)}",
        "common_ranges": recommended_ranges[:3]
    }


# =============================================================================
# 6. AC值分析
# =============================================================================

def calculate_ac_value(balls: list[int]) -> int:
    """计算 AC值 (数字复杂度指标)
    
    AC = 不同差值数量 - (号码数量 - 1)
    双色球 AC 值范围: 0-10，常见值 4-9
    
    Args:
        balls: 6个红球
    
    Returns:
        AC值
    """
    diffs = set()
    for i in range(len(balls)):
        for j in range(i + 1, len(balls)):
            diffs.add(abs(balls[i] - balls[j]))
    
    return len(diffs) - (len(balls) - 1)


def analyze_ac_value(df: pd.DataFrame) -> dict:
    """AC值分布分析
    
    Args:
        df: 历史数据
    
    Returns:
        AC值统计
    """
    reds = get_red_balls(df)
    ac_values = [calculate_ac_value(draw) for draw in reds]
    
    ac_counter = Counter(ac_values)
    ac_dist = [{"ac": ac, "count": c, "rate": round(c/len(df)*100, 1)} 
               for ac, c in sorted(ac_counter.items())]
    
    ac_series = pd.Series(ac_values)
    
    return {
        "mean": round(ac_series.mean(), 2),
        "median": int(ac_series.median()),
        "mode": ac_series.mode().tolist(),
        "distribution": ac_dist,
        "recommended_range": f"{int(ac_series.quantile(0.1))}-{int(ac_series.quantile(0.9))}"
    }


# =============================================================================
# 7. 连号分析
# =============================================================================

def analyze_consecutive(df: pd.DataFrame) -> dict:
    """连号分析
    
    Args:
        df: 历史数据
    
    Returns:
        连号统计
    """
    reds = get_red_balls(df)
    
    consecutive_counts = Counter()
    has_consecutive = 0
    
    for draw in reds:
        sorted_draw = sorted(draw)
        consec = 0
        for i in range(len(sorted_draw) - 1):
            if sorted_draw[i + 1] - sorted_draw[i] == 1:
                consec += 1
        
        if consec > 0:
            has_consecutive += 1
        consecutive_counts[str(consec)] += 1
    
    dist = [{"count": int(k), "occurrences": v, "rate": round(v/len(df)*100, 1)} 
            for k, v in sorted(consecutive_counts.items(), key=lambda x: int(x[0]))]
    
    return {
        "has_consecutive_rate": round(has_consecutive / len(df) * 100, 1),
        "distribution": dist,
        "recommended": "建议包含 0-1 组连号"
    }


# =============================================================================
# 8. 重号分析
# =============================================================================

def analyze_repeat(df: pd.DataFrame) -> dict:
    """重号分析（相邻期次重复号码）
    
    Args:
        df: 历史数据
    
    Returns:
        重号统计
    """
    reds = get_red_balls(df)
    repeat_counts = Counter()
    
    for i in range(1, len(reds)):
        common = len(set(reds[i]) & set(reds[i - 1]))
        repeat_counts[str(common)] += 1
    
    dist = [{"count": int(k), "occurrences": v, "rate": round(v/(len(df)-1)*100, 1)} 
            for k, v in sorted(repeat_counts.items(), key=lambda x: int(x[0]))]
    
    return {
        "distribution": dist,
        "recommended": "通常 1-2 个重号"
    }


# =============================================================================
# 9. 蓝球专项分析
# =============================================================================

def analyze_blue_ball(df: pd.DataFrame) -> dict:
    """蓝球专项分析
    
    Args:
        df: 历史数据
    
    Returns:
        蓝球分析结果
    """
    blues = get_blue_balls(df)
    
    # 奇偶
    odd_count = sum(1 for b in blues if b % 2 == 1)
    even_count = len(blues) - odd_count
    
    # 大小 (1-8 小，9-16 大)
    small_count = sum(1 for b in blues if b <= 8)
    big_count = len(blues) - small_count
    
    # 012路 (除3余数)
    route_counts = Counter(b % 3 for b in blues)
    
    # 遗漏
    omission = analyze_omission(df)
    
    return {
        "odd_rate": round(odd_count / len(blues) * 100, 1),
        "even_rate": round(even_count / len(blues) * 100, 1),
        "small_rate": round(small_count / len(blues) * 100, 1),
        "big_rate": round(big_count / len(blues) * 100, 1),
        "route_distribution": {str(k): v for k, v in sorted(route_counts.items())},
        "current_omission": omission["blue_omission"],
        "high_omission": omission["high_omission_blue"]
    }


# =============================================================================
# 10. 历史同期对比
# =============================================================================

def analyze_same_period(df: pd.DataFrame) -> dict:
    """历史同期对比（同月同日）
    
    Args:
        df: 历史数据
    
    Returns:
        同期统计
    """
    from datetime import datetime
    
    today = datetime.now()
    target_month = today.month
    target_day = today.day
    
    # 筛选同月同日的数据
    same_period = df[df["日期"].apply(
        lambda x: datetime.strptime(str(x), "%Y-%m-%d").month == target_month and 
                  datetime.strptime(str(x), "%Y-%m-%d").day == target_day
        if pd.notna(x) else False
    )]
    
    if len(same_period) < 3:
        # 放宽到同月
        same_month = df[df["日期"].apply(
            lambda x: datetime.strptime(str(x), "%Y-%m-%d").month == target_month
            if pd.notna(x) else False
        )]
        
        if len(same_month) < 3:
            return {"available": False, "message": "同期数据不足"}
        
        same_period = same_month
    
    reds = get_red_balls(same_period)
    blues = get_blue_balls(same_period)
    
    red_counter = Counter()
    for draw in reds:
        red_counter.update(draw)
    
    blue_counter = Counter(blues)
    
    hot_red = [str(k).zfill(2) for k, _ in red_counter.most_common(6)]
    hot_blue = [str(k).zfill(2) for k, _ in blue_counter.most_common(3)]
    
    return {
        "available": True,
        "total_draws": len(same_period),
        "period_type": "同月" if len(same_period) > 10 else "同月同日",
        "hot_red": hot_red,
        "hot_blue": hot_blue,
        "red_frequency": {str(k).zfill(2): v for k, v in red_counter.most_common()}
    }


# =============================================================================
# 统一分析入口
# =============================================================================

def run_full_analysis(df: pd.DataFrame, save: bool = True, verbose: bool = True) -> dict:
    """运行完整分析
    
    Args:
        df: 历史数据
        save: 是否保存结果到文件
        verbose: 是否打印进度消息（回测时应设为 False）
    
    Returns:
        完整分析结果
    """
    if verbose:
        print("📊 开始分析历史数据...")
    
    results = {
        "total_draws": len(df),
        "date_range": f"{df.iloc[0]['期号']} ~ {df.iloc[-1]['期号']}",
        "frequency": analyze_frequency(df),
        "frequency_recent_50": analyze_frequency(df, recent_n=50),
        "omission": analyze_omission(df),
        "zone": analyze_zone_distribution(df),
        "odd_even": analyze_odd_even(df),
        "sum": analyze_sum(df),
        "ac_value": analyze_ac_value(df),
        "consecutive": analyze_consecutive(df),
        "repeat": analyze_repeat(df),
        "blue_ball": analyze_blue_ball(df),
        "same_period": analyze_same_period(df),
    }
    
    if save:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"✅ 分析结果已保存: {STATS_FILE}")
    
    return results


def load_stats() -> dict | None:
    """加载缓存的分析结果"""
    if STATS_FILE.exists():
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


if __name__ == "__main__":
    df = load_data()
    print(f"加载数据: {len(df)} 期")
    run_full_analysis(df)
