#!/usr/bin/env python3.11
"""
Elo动态轨迹因子 (Layer 1.5)
基于学术论文 SDR-based Elo history 方法 (arXiv 2606.24171)

核心思想: 不只取当前单点Elo，而是提取过去N场比赛的Elo变化趋势
- ΔElo(trend): 斜率
- volatility(σ): 波动性
- 趋势上升+低波动 → 加分
- 趋势下降+低波动 → 扣分
- 高波动 → 不确定性标记, 不调整ELO但降低置信度
"""

import json, os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def load_elo_history():
    """从applied_results提取每队的Elo变化序列"""
    elo_path = os.path.join(DATA_DIR, "elo_ratings.json")
    with open(elo_path) as f:
        data = json.load(f)
    
    # Build per-team Elo history from applied_results
    history = {}
    for entry in data.get("applied_results", []):
        for side in ["a", "b"]:
            team = entry.get(f"team_{side}")
            new_elo = entry.get(f"elo_{side}", {}).get("new")
            if team and new_elo:
                if team not in history:
                    history[team] = []
                history[team].append(new_elo)
    
    return history


def compute_trajectory(team, elo_history, window=5):
    """
    计算Elo轨迹因子
    
    Returns:
        {
            "current_elo": float,
            "trend_elo": [recent values],
            "delta_avg": float,    # 平均变化
            "delta_trend": float,  # 趋势斜率
            "volatility": float,   # 标准差
            "adjustment": int,     # ELO调整值
            "confidence_discount": float,  # 置信度折扣
        }
    """
    values = elo_history.get(team, [])
    if len(values) < 3:
        return {"current_elo": values[-1] if values else 0, "adjustment": 0, "confidence_discount": 1.0, "note": "数据不足"}
    
    # Take last N matches
    recent = values[-window:]
    
    if len(recent) < 3:
        return {"current_elo": values[-1], "adjustment": 0, "confidence_discount": 1.0, "note": f"仅{len(recent)}场历史"}
    
    # Compute deltas
    deltas = [recent[i+1] - recent[i] for i in range(len(recent)-1)]
    
    delta_avg = sum(deltas) / len(deltas)
    delta_trend = deltas[-1]  # Most recent change direction
    
    # Volatility (std dev)
    mean = sum(deltas) / len(deltas)
    if len(deltas) > 1:
        volatility = (sum((d - mean)**2 for d in deltas) / len(deltas))**0.5
    else:
        volatility = 0
    
    # Classification
    trend_up = delta_avg > 5
    trend_down = delta_avg < -5
    low_vol = volatility < 20
    high_vol = volatility > 40
    
    if trend_up and low_vol:
        adjustment = 15
        classification = "稳步上升"
    elif trend_up and not low_vol:
        adjustment = 8
        classification = "波动上升"
    elif trend_down and low_vol:
        adjustment = -15
        classification = "持续下滑"
    elif trend_down and not low_vol:
        adjustment = -8
        classification = "波动下滑"
    else:
        adjustment = 0
        classification = "方向不明"
    
    confidence_discount = 0.85 if high_vol else 1.0
    
    return {
        "current_elo": recent[-1],
        "trend_elo": recent,
        "deltas": deltas,
        "delta_avg": round(delta_avg, 1),
        "delta_trend": round(delta_trend, 1),
        "volatility": round(volatility, 1),
        "adjustment": adjustment,
        "classification": classification,
        "confidence_discount": confidence_discount,
        "n_matches": len(recent),
    }


def get_trajectory_adjustments():
    """返回所有球队的轨迹调整值，用于预测管线"""
    history = load_elo_history()
    
    adjustments = {}
    for team in history:
        traj = compute_trajectory(team, history)
        adjustments[team] = traj
    
    return adjustments


if __name__ == "__main__":
    adjustments = get_trajectory_adjustments()
    
    # Show current QF teams
    qf_teams = ['France', 'Morocco', 'Spain', 'Belgium', 'Norway', 'England', 'Argentina', 'Switzerland']
    print("=== QF Teams Elo Trajectory ===")
    for t in qf_teams:
        if t in adjustments:
            a = adjustments[t]
            print(f"  {t}: Δavg={a['delta_avg']}, σ={a['volatility']}, "
                  f"adj={a['adjustment']:+d}, class={a['classification']}")
        else:
            print(f"  {t}: NO DATA")
