#!/usr/bin/env python3.11
"""
v5.10 预测wrapper — 淘汰赛增强版
===================================
集成: Elo轨迹因子 + 有序Logit + 淘汰赛lambda校准 + Phase-aware规则引擎

与v5.5对比新增:
  Layer 1.5: Elo Trajectory (轨迹趋势/波动)
  Ordered Logit: 补充Poisson概率 (50/50加权平均)
  KO Lambda: 淘汰赛lambda校准 (0.78x + 平局增强)
  Rules v3: Phase-aware rules (6条新KO规则 + 自动禁用小组赛MOT规则)
"""
import json, os, sys, math
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
sys.path.insert(0, BASE_DIR)

from scripts.elo_trajectory import get_trajectory_adjustments
from scripts.ordered_logit import predict_outcome as ordered_logit_predict

_trajectory_cache = None

def _get_trajectory():
    global _trajectory_cache
    if _trajectory_cache is None:
        _trajectory_cache = get_trajectory_adjustments()
    return _trajectory_cache


def compute_knockout_poisson_calibration(lambda_a, lambda_b, elo_diff):
    """淘汰赛Poisson lambda校准 — 基于WC1998-2022 94场历史数据"""
    ka = kb = 0.78
    if abs(elo_diff) < 100:
        ka *= 0.92
        kb *= 0.92
    return lambda_a * ka, lambda_b * kb


def predict_with_engine_v510(team_a, team_b, match_id=None, knockout=True,
                              enable_news=True, rules_version="v3"):
    """v5.10 增强预测"""
    
    trajectory = _get_trajectory()
    traj_a = trajectory.get(team_a, {"adjustment": 0, "classification": "none", "volatility": 0,
                                      "delta_avg": 0})
    traj_b = trajectory.get(team_b, {"adjustment": 0, "classification": "none", "volatility": 0,
                                      "delta_avg": 0})
    
    from scripts.predict_v55 import predict_with_engine as predict_v55
    v55_result = predict_v55(
        team_a, team_b,
        match_id=match_id,
        knockout=knockout,
        enable_news=enable_news,
        rules_version=rules_version
    )
    
    pdata = v55_result.get("prediction", {})
    eff = v55_result.get("effective_elo", {})
    audit = v55_result.get("audit", {})
    
    # KO lambda calibration
    ko_calibrated = False
    if knockout:
        eg_a = pdata.get("expected_goals_a", 1.4)
        eg_b = pdata.get("expected_goals_b", 1.0)
        elo_diff = eff.get("diff", 0)
        cal_eg_a, cal_eg_b = compute_knockout_poisson_calibration(eg_a, eg_b, elo_diff)
        
        scores = []
        for i in range(8):
            for j in range(8):
                pi = (math.exp(-cal_eg_a) * cal_eg_a**i / math.factorial(i)) if cal_eg_a > 0 else (1.0 if i == 0 else 0)
                pj = (math.exp(-cal_eg_b) * cal_eg_b**j / math.factorial(j)) if cal_eg_b > 0 else (1.0 if j == 0 else 0)
                prob = pi * pj
                if prob > 0.002:
                    scores.append({"score": f"{i}-{j}", "prob_pct": round(prob * 100, 1)})
        scores.sort(key=lambda x: -x["prob_pct"])
        pdata["scoreline_probs"] = scores[:5]
        pdata["expected_goals_a_calibrated"] = round(cal_eg_a, 2)
        pdata["expected_goals_b_calibrated"] = round(cal_eg_b, 2)
        pdata["ko_lambda_suppression"] = 0.78
        ko_calibrated = True
    
    # Ordered Logit ensemble
    elo_diff_eff = eff.get("diff", 0)
    ol_w, ol_d, ol_l = ordered_logit_predict(elo_diff_eff, knockout=knockout)
    
    poisson_w = pdata.get("team_a_win", 50) / 100.0
    poisson_d = pdata.get("draw", 33) / 100.0
    poisson_l = pdata.get("team_b_win", 50) / 100.0
    
    ensemble_w = round((poisson_w + ol_w) / 2 * 100)
    ensemble_d = round((poisson_d + ol_d) / 2 * 100)
    ensemble_l = round((poisson_l + ol_l) / 2 * 100)
    
    result = {
        "team_a": team_a, "team_b": team_b, "match_id": match_id,
        "knockout": knockout, "model_version": "v5.10",
        "prediction": {
            "team_a_win_pct": ensemble_w, "draw_pct": ensemble_d,
            "team_b_win_pct": ensemble_l,
            "team_a_win_poisson": round(poisson_w * 100),
            "draw_poisson": round(poisson_d * 100),
            "team_b_win_poisson": round(poisson_l * 100),
            "team_a_win_logit": round(ol_w * 100),
            "draw_logit": round(ol_d * 100),
            "team_b_win_logit": round(ol_l * 100),
            "team_a_win": ensemble_w, "draw": ensemble_d, "team_b_win": ensemble_l,
            "expected_goals_a": pdata.get("expected_goals_a"),
            "expected_goals_b": pdata.get("expected_goals_b"),
            "expected_goals_a_calibrated": pdata.get("expected_goals_a_calibrated"),
            "expected_goals_b_calibrated": pdata.get("expected_goals_b_calibrated"),
            "scoreline_probs": pdata.get("scoreline_probs", []),
            "most_likely_score": pdata.get("most_likely_score", ""),
            "ko_lambda_calibrated": ko_calibrated,
        },
        "effective_elo": eff,
        "elo_trajectory": {team_a: traj_a, team_b: traj_b},
        "reasoning_path": v55_result.get("reasoning_path"),
        "inference_trace": audit.get("inference_trace"),
        "verdict": v55_result.get("verdict", {}),
    }
    
    return result


if __name__ == "__main__":
    print("=== v5.10 QF Predictions ===")
    qf_matches = [
        ("France", "Morocco"), ("Spain", "Belgium"),
        ("Norway", "England"), ("Argentina", "Switzerland"),
    ]
    for ta, tb in qf_matches:
        print(f"\n--- {ta} vs {tb} ---")
        r = predict_with_engine_v510(ta, tb, knockout=True, rules_version="v3")
        p = r["prediction"]
        tr = r["elo_trajectory"]
        print(f"  Ensemble: {ta} {p['team_a_win_pct']}% / Draw {p['draw_pct']}% / {tb} {p['team_b_win_pct']}%")
        print(f"  Poisson:  {ta} {p['team_a_win_poisson']}% / Draw {p['draw_poisson']}% / {tb} {p['team_b_win_poisson']}%")
        print(f"  Logit:    {ta} {p['team_a_win_logit']}% / Draw {p['draw_logit']}% / {tb} {p['team_b_win_logit']}%")
        taj = tr.get(ta, {})
        tbj = tr.get(tb, {})
        print(f"  Trajectory: {ta}={taj.get('classification','?')}(Δavg={taj.get('delta_avg',0)}) "
              f"{tb}={tbj.get('classification','?')}(Δavg={tbj.get('delta_avg',0)})")
        if p.get("scoreline_probs"):
            sp = p["scoreline_probs"][:3]
            strs = [f"{s['score']}({s['prob_pct']}%)" for s in sp]
            print(f"  Top scores: {', '.join(strs)}")
        if p.get("expected_goals_a_calibrated"):
            print(f"  Calibrated xG: {ta} {p['expected_goals_a_calibrated']} - {p['expected_goals_b_calibrated']} {tb}")
