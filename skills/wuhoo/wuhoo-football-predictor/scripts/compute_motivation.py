#!/usr/bin/env python3.11
"""
QMF (Qualification Motivation Factor) — 小组赛末轮出线动机自动分类
v1.0 — WC2026 Matchday 3 optimization

Computes motivation classification for all 48 teams based on:
- Current group standings (points, GD, GF)
- Remaining matches (opponent strength)
- 3rd place qualification probability

Output: data/matchday3_motivation.json

Usage:
  python3.11 scripts/compute_motivation.py --all-groups
  python3.11 scripts/compute_motivation.py --group B
  python3.11 scripts/compute_motivation.py --all-groups --output data/motivation.json
"""

import json
import os
import sys
import argparse
from collections import defaultdict
from datetime import datetime, timezone, timedelta

# === Configuration ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ELO adjustment by classification
MOTIVATION_ELO = {
    "LOCKED_IN": -30,       # Already qualified, likely to rotate
    "DRAW_OK": -5,           # Draw secures qualification
    "NEED_RESULT": 10,       # Need at least a point
    "MUST_WIN": 20,          # Must win to have a chance
    "PRIDE_ONLY": -5,        # Eliminated, playing for pride
    "TOP_SEED": 8,           # Battling for group top spot
}

# Classification descriptions
CLASSIFICATION_DESC = {
    "LOCKED_IN": "已锁定出线，大概率轮换主力",
    "DRAW_OK": "打平即出线，保守策略",
    "NEED_RESULT": "需要至少1分，稍有紧迫感",
    "MUST_WIN": "必须赢球，背水一战",
    "PRIDE_ONLY": "已淘汰，为荣誉而战",
    "TOP_SEED": "争夺小组第一，为淘汰赛有利位置",
}

# Third-place advancement probability estimates (based on Opta data)
# Key insight: 8 of 12 third-place teams advance
THIRD_PLACE_ODDS = {
    # (points, gd_range): probability_of_advancing
    (4, 99): 0.99,    # 4+ points almost always qualifies
    (3, 3): 0.90,     # 3pts + GD >= 3
    (3, 1): 0.80,     # 3pts + GD 0~2
    (3, 0): 0.70,     # 3pts + GD 0
    (3, -1): 0.55,    # 3pts + GD -1~
    (3, -3): 0.40,    # 3pts + GD -2~-3
    (3, -99): 0.25,   # 3pts + GD worse
    (2, 99): 0.30,    # 2pts
    (1, 99): 0.10,    # 1pt
    (0, 99): 0.0,     # 0pts
}

def load_json(filename):
    """Load JSON data file."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"ERROR: {filename} not found at {path}", file=sys.stderr)
        return None
    with open(path) as f:
        return json.load(f)

def get_third_place_probability(points, gd):
    """Estimate probability of advancing as 3rd place."""
    for (pts_thresh, gd_thresh), prob in sorted(THIRD_PLACE_ODDS.items(), 
                                                  key=lambda x: (-x[0][0], -x[0][1])):
        if points >= pts_thresh and gd >= gd_thresh:
            return prob
    return 0.0

def compute_group_standings(schedule, elo):
    """Compute group standings from completed matches."""
    groups = defaultdict(lambda: defaultdict(lambda: {"pts": 0, "gf": 0, "ga": 0, "mp": 0}))
    group_remaining = defaultdict(list)
    group_completed = defaultdict(list)
    
    for m in schedule.get("matches", []):
        g = m.get("group", "?")
        if g == "?":
            continue
        
        if m.get("status") == "completed":
            group_completed[g].append(m)
            ta, tb = m["team_a"], m["team_b"]
            sa, sb = m.get("score_a"), m.get("score_b")
            if sa is None or sb is None:
                continue
            sa, sb = int(sa), int(sb)
            
            groups[g][ta]["mp"] += 1
            groups[g][tb]["mp"] += 1
            groups[g][ta]["gf"] += sa
            groups[g][ta]["ga"] += sb
            groups[g][tb]["gf"] += sb
            groups[g][tb]["ga"] += sa
            
            if sa > sb:
                groups[g][ta]["pts"] += 3
            elif sb > sa:
                groups[g][tb]["pts"] += 3
            else:
                groups[g][ta]["pts"] += 1
                groups[g][tb]["pts"] += 1
        else:
            group_remaining[g].append(m)
    
    # Get ELO ratings
    ratings = elo.get("ratings", {})
    
    # Build standings with ELO
    standings = {}
    for g in groups:
        team_list = []
        for team, stats in groups[g].items():
            elo_val = ratings.get(team, {}).get("elo", 1500) if isinstance(ratings.get(team), dict) else ratings.get(team, 1500)
            team_list.append({
                "team": team,
                "elo": elo_val,
                "pts": stats["pts"],
                "mp": stats["mp"],
                "gf": stats["gf"],
                "ga": stats["ga"],
                "gd": stats["gf"] - stats["ga"],
            })
        
        # Sort: pts desc, gd desc, gf desc
        team_list.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"], -x["elo"]))
        standings[g] = team_list
    
    return standings, group_remaining


def classify_team(team_data, group_standings, group_remaining_matches, all_standings):
    """
    Classify a team's motivation based on group position and scenarios.
    
    Returns: (classification, elo_adjustment, reasoning, confidence)
    """
    team_name = team_data["team"]
    pts = team_data["pts"]
    mp = team_data["mp"]
    gd = team_data["gd"]
    gf = team_data["gf"]
    pos = team_data.get("position", 1)
    
    total_teams = len(group_standings)
    
    # Find the team's remaining match
    remaining_match = None
    for m in group_remaining_matches:
        if m["team_a"] == team_name or m["team_b"] == team_name:
            remaining_match = m
            break
    
    if mp < 2:
        # Incomplete matchday (K/L groups): lower confidence
        confidence = "medium"
    else:
        confidence = "high"
    
    # === Classification logic ===
    
    # 1. Already qualified scenarios
    if pos == 1:
        if pts >= 6:
            # 6pts from 2MP = securely qualified
            # Check if top spot is locked
            if len(group_standings) >= 2:
                second = group_standings[1]
                if second["mp"] >= 2 and pts - second["pts"] >= 4:
                    return ("LOCKED_IN", MOTIVATION_ELO["LOCKED_IN"],
                            f"已锁定{get_group_name(team_data)}第一，大概率轮换主力", confidence)
                elif second["mp"] >= 2 and pts - second["pts"] >= 3 and gd > second["gd"] + 3:
                    return ("LOCKED_IN", MOTIVATION_ELO["LOCKED_IN"],
                            f"基本锁定{get_group_name(team_data)}第一(GD优势)，可能轮换", confidence)
            
            # Still needs a result to secure top
            return ("TOP_SEED", MOTIVATION_ELO["TOP_SEED"],
                    f"已锁定出线，但仍需确保小组第一", confidence)
        
        if pts >= 4 and len(group_standings) >= 3:
            third = group_standings[2]
            if third["mp"] >= 2 and pts - third["pts"] >= 4:
                return ("LOCKED_IN", MOTIVATION_ELO["LOCKED_IN"],
                        f"已锁定小组前二，确保出线", confidence)
    
    if pos == 2:
        if pts >= 4 and len(group_standings) >= 3:
            third = group_standings[2]
            if third["mp"] >= 2 and pts - third["pts"] >= 4:
                return ("LOCKED_IN", MOTIVATION_ELO["LOCKED_IN"],
                        f"已锁定小组前二，确保出线", confidence)
    
    # 2. TOP_SEED / head-of-group battles
    # Check if team is within striking distance of 1st or defending 1st
    if pos == 1:
        if len(group_standings) >= 2:
            second = group_standings[1]
            if second["mp"] >= 2 and pts - second["pts"] <= 2:
                return ("TOP_SEED", MOTIVATION_ELO["TOP_SEED"],
                        f"争夺小组第一(领先第二仅{pts - second['pts']}分)", confidence)
    
    if pos == 2:
        first = group_standings[0]
        if first["mp"] >= 2 and pts - first["pts"] >= -2:
            return ("TOP_SEED", MOTIVATION_ELO["TOP_SEED"],
                    f"争夺小组第一(落后第一{first['pts'] - pts}分)", confidence)
    
    # 3. Draw-OK scenarios
    if pos == 1 and pts >= 4:
        if len(group_standings) >= 3:
            third = group_standings[2]
            if third["mp"] >= 2 and pts - third["pts"] >= 3:
                return ("DRAW_OK", MOTIVATION_ELO["DRAW_OK"],
                        f"打平即确保出线(领先第三{pts - third['pts']}分)", confidence)
    
    if pos == 2:
        if len(group_standings) >= 3:
            third = group_standings[2]
            first = group_standings[0]
            if third["mp"] >= 2 and pts - third["pts"] >= 2:
                # Can we catch first?
                if first["mp"] >= 2 and pts - first["pts"] >= -2 and remaining_match:
                    # Within range of first - this is a TOP_SEED battle
                    opponent = remaining_match["team_b"] if remaining_match["team_a"] == team_name else remaining_match["team_a"]
                    if opponent == first["team"]:
                        return ("TOP_SEED", MOTIVATION_ELO["TOP_SEED"],
                                f"直接对决争小组第一(落后{first['pts'] - pts}分)", confidence)
                
                return ("DRAW_OK", MOTIVATION_ELO["DRAW_OK"],
                        f"打平即确保前二出线(领先第三{pts - third['pts']}分)", confidence)
    
    # 3. Must-win scenarios
    if pos == 3:
        second = group_standings[1]
        if second["mp"] >= 2 and pts - second["pts"] >= -3:
            return ("MUST_WIN", MOTIVATION_ELO["MUST_WIN"],
                    f"必须赢球争夺出线权(落后第二{second['pts'] - pts}分)", confidence)
    
    if pos == 4 and pts <= 1:
        # Check if eliminated
        second = group_standings[1]
        if second["mp"] >= 2 and pts - second["pts"] <= -4:
            return ("PRIDE_ONLY", MOTIVATION_ELO["PRIDE_ONLY"],
                    f"已提前淘汰(落后第二{second['pts'] - pts}分)", confidence)
        else:
            return ("MUST_WIN", MOTIVATION_ELO["MUST_WIN"],
                    f"必须赢球且依赖其他结果", confidence)
    
    # 4. Need-result scenarios  
    if pos == 3:
        # Check third-place advancement chances
        tp_prob = get_third_place_probability(pts, gd)
        if tp_prob >= 0.7:
            return ("DRAW_OK", MOTIVATION_ELO["DRAW_OK"],
                    f"第三名晋级概率~{tp_prob*100:.0f}%，打平大概率晋级", confidence)
        elif tp_prob >= 0.4:
            return ("NEED_RESULT", MOTIVATION_ELO["NEED_RESULT"],
                    f"第三名晋级概率~{tp_prob*100:.0f}%，需要至少1分", confidence)
        else:
            return ("MUST_WIN", MOTIVATION_ELO["MUST_WIN"],
                    f"第三名晋级概率~{tp_prob*100:.0f}%，必须赢球", confidence)
    
    # 5. Eliminated
    if pos == 4 and pts == 0 and mp >= 2:
        return ("PRIDE_ONLY", MOTIVATION_ELO["PRIDE_ONLY"],
                f"已提前淘汰(0分垫底)", confidence)
    
    # Fallback
    if pts >= 4:
        return ("DRAW_OK", MOTIVATION_ELO["DRAW_OK"],
                f"积分优势，打平大概率出线", "medium")
    elif pts >= 2:
        return ("NEED_RESULT", MOTIVATION_ELO["NEED_RESULT"],
                f"需要至少1分确保出线机会", "medium")
    else:
        return ("MUST_WIN", MOTIVATION_ELO["MUST_WIN"],
                f"积分落后，必须赢球", "medium")


def get_group_name(team_data):
    """Extract group name from context (set externally)."""
    return team_data.get("_group", "?")


def compute_all_motivation(schedule, elo, target_groups=None):
    """Compute motivation for all groups."""
    standings, remaining = compute_group_standings(schedule, elo)
    
    results = {}
    for g in sorted(standings.keys()):
        if target_groups and g not in target_groups:
            continue
        
        group_teams = standings[g]
        group_rem = remaining.get(g, [])
        
        for i, team_data in enumerate(group_teams):
            team_data["position"] = i + 1
            team_data["_group"] = g
            
            classification, elo_adj, reason, conf = classify_team(
                team_data, group_teams, group_rem, standings
            )
            
            # Build scenarios list
            scenarios = []
            if classification == "LOCKED_IN":
                scenarios.append("已出线")
            if classification == "TOP_SEED":
                scenarios.append("争头名")
            if classification == "MUST_WIN":
                scenarios.append("必须赢球")
            if classification == "DRAW_OK":
                scenarios.append("打平即出线")
            if team_data["position"] == 3 and team_data["mp"] >= 2:
                tp_prob = get_third_place_probability(team_data["pts"], team_data["gd"])
                scenarios.append(f"第三名晋级概率~{tp_prob*100:.0f}%")
            
            results[team_data["team"]] = {
                "classification": classification,
                "elo_adjustment": elo_adj,
                "reason": reason,
                "confidence": conf,
                "points": team_data["pts"],
                "group_position": team_data["position"],
                "group": g,
                "mp": team_data["mp"],
                "gd": team_data["gd"],
                "scenarios": scenarios,
            }
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Compute MD3 motivation factors")
    parser.add_argument("--all-groups", action="store_true", help="Process all groups")
    parser.add_argument("--group", type=str, help="Process specific group (A-L)")
    parser.add_argument("--output", type=str, default="data/matchday3_motivation.json",
                        help="Output file path (relative to skill root)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    if not args.all_groups and not args.group:
        print("ERROR: Specify --all-groups or --group X", file=sys.stderr)
        sys.exit(1)
    
    # Load data
    schedule = load_json("wc2026_schedule.json")
    elo = load_json("elo_ratings.json")
    
    if schedule is None or elo is None:
        sys.exit(1)
    
    # Determine target groups
    target_groups = None
    if args.group:
        target_groups = {args.group.upper()}
    
    # Compute
    motivation = compute_all_motivation(schedule, elo, target_groups)
    
    # Build output
    output = {
        "generated": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "teams": len(motivation),
        "classifications": motivation,
        "classification_summary": {},
        "notes": [
            "Classification key: LOCKED_IN=已锁定出线, DRAW_OK=打平即出线, NEED_RESULT=需要拿分, MUST_WIN=必须赢球, PRIDE_ONLY=已淘汰, TOP_SEED=争头名",
            "ELO adjustments are applied as direct deltas to effective ELO before Poisson calculation",
            "Third-place advancement probabilities based on Opta estimates for 48-team format",
            "Confidence: high=2MP complete, medium=<2MP (K/L groups not yet complete)",
        ]
    }
    
    # Summary
    summary = defaultdict(int)
    for team, data in motivation.items():
        summary[data["classification"]] += 1
        if args.verbose:
            print(f"  {team} [{data['group']}]: {data['classification']} ({data['elo_adjustment']:+d} ELO) - {data['reason']}")
    
    output["classification_summary"] = dict(summary)
    
    # Save
    output_path = os.path.join(BASE_DIR, args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Motivation computed for {len(motivation)} teams")
    print(f"   Saved to: {output_path}")
    print(f"   Summary: {dict(summary)}")


if __name__ == "__main__":
    main()
