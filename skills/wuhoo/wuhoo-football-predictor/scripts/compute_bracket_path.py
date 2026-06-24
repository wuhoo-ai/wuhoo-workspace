#!/usr/bin/env python3.11
"""
BPP (Bracket Path Preference) — 淘汰赛半区路径难度分析
v1.0 — WC2026

Computes knockout bracket path difficulty for each group position,
enabling "strategic positioning" adjustments in MD3.

Based on: references/bracket-2026.md (R32 matchups)
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# === R32 Bracket: (Group Winner/2nd → opponent) ===
# Format: {group: {position: [(opponent_group, opponent_position), ...]}}
# "3rd" means third-place team from eligible groups

R32_BRACKET = {
    "A": {
        1: [("3rd", "C/E/F/H/I")],     # Mexico → 3rd place
        2: [("B", 2)],                    # → B2 (runner-up)
    },
    "B": {
        1: [("3rd", "E/F/G/I/J")],      # → 3rd place
        2: [("A", 2)],                    # → A2
    },
    "C": {
        1: [("F", 2)],                   # → F2
        2: [("F", 1)],                   # → F1
    },
    "D": {
        1: [("3rd", "B/E/F/I/J")],      # USA → 3rd place
        2: [("G", 2)],                   # → G2
    },
    "E": {
        1: [("3rd", "A/B/C/D/F")],      # Germany → 3rd place
        2: [("I", 2)],                   # → I2
    },
    "F": {
        1: [("C", 2)],                   # → C2
        2: [("C", 1)],                   # → C1
    },
    "G": {
        1: [("3rd", "A/E/H/I/J")],      # → 3rd place
        2: [("D", 2)],                   # → D2
    },
    "H": {
        1: [("J", 2)],                   # → J2
        2: [("J", 1)],                   # → J1
    },
    "I": {
        1: [("3rd", "C/D/F/G/H")],      # France → 3rd place
        2: [("E", 2)],                   # → E2
    },
    "J": {
        1: [("H", 2)],                   # Argentina → H2
        2: [("H", 1)],                   # → H1
    },
    "K": {
        1: [("3rd", "D/E/I/J/L")],      # → 3rd place
        2: [("L", 2)],                   # → L2
    },
    "L": {
        1: [("3rd", "E/H/I/J/K")],      # England → 3rd place
        2: [("K", 2)],                   # → K2
    },
}

# R16 pairings (winner of R32 slot X vs winner of R32 slot Y)
R16_PAIRINGS = [
    (73, 74),   # A2-B2 winner vs E1-3rd winner
    (76, 77),   # C1-F2 winner vs I1-3rd winner
    (78, 79),   # E2-I2 winner vs A1-3rd winner
    (75, 82),   # F1-C2 winner vs G1-3rd winner
    (81, 80),   # D1-3rd winner vs L1-3rd winner
    (84, 83),   # H1-J2 winner vs K2-L2 winner
    (85, 88),   # B1-3rd winner vs D2-G2 winner
    (86, 87),   # J1-H2 winner vs K1-3rd winner
]

# QF pairings: R16 slots paired
QF_PAIRINGS = [
    ((73, 74), (76, 77)),
    ((78, 79), (75, 82)),
    ((81, 80), (84, 83)),
    ((85, 88), (86, 87)),
]

# SF pairings: QF groups
SF_PAIRINGS = [
    (0, 1),  # QF 0-1
    (2, 3),  # QF 2-3
]


def load_data():
    """Load required data files."""
    elo_path = os.path.join(DATA_DIR, "elo_ratings.json")
    schedule_path = os.path.join(DATA_DIR, "wc2026_schedule.json")
    
    elo = json.load(open(elo_path))
    schedule = json.load(open(schedule_path))
    
    ratings = elo.get("ratings", {})
    
    # Compute current group standings to predict likely qualifiers
    from collections import defaultdict
    groups = defaultdict(list)
    for m in schedule.get("matches", []):
        g = m.get("group", "?")
        if g == "?" or m.get("status") != "completed":
            continue
        groups[g].append(m)
    
    # Current standings
    group_standings = {}
    for g, matches in groups.items():
        teams = defaultdict(lambda: {"pts": 0, "gf": 0, "ga": 0, "elo": 1500})
        for m in matches:
            ta, tb = m["team_a"], m["team_b"]
            sa, sb = m.get("score_a"), m.get("score_b")
            if sa is None or sb is None:
                continue
            sa, sb = int(sa), int(sb)
            teams[ta]["gf"] += sa; teams[ta]["ga"] += sb
            teams[tb]["gf"] += sb; teams[tb]["ga"] += sa
            if sa > sb: teams[ta]["pts"] += 3
            elif sb > sa: teams[tb]["pts"] += 3
            else: teams[ta]["pts"] += 1; teams[tb]["pts"] += 1
        
        for t in teams:
            r = ratings.get(t, {})
            teams[t]["elo"] = r.get("elo", 1500) if isinstance(r, dict) else r
        
        sorted_teams = sorted(teams.items(), 
                             key=lambda x: (-x[1]["pts"], -(x[1]["gf"]-x[1]["ga"]), -x[1]["gf"]))
        group_standings[g] = [(t, s) for t, s in sorted_teams]
    
    return ratings, group_standings


def get_likely_opponent(group, position, group_standings, ratings):
    """
    Estimate ELO of likely opponent for a given group position.
    
    For fixed matchups (e.g., 1C vs 2F): return the projected opponent ELO
    For 3rd-place slots: return average ELO of eligible 3rd-place teams
    """
    bracket = R32_BRACKET.get(group, {}).get(position, [])
    if not bracket:
        return 1500
    
    opp_group, opp_pos = bracket[0]
    
    if opp_group == "3rd":
        # Third-place slot — compute average ELO of eligible 3rd place teams
        eligible_groups = opp_pos.split("/")
        eligible_elos = []
        for eg in eligible_groups:
            if eg in group_standings and len(group_standings[eg]) >= 3:
                third_team, third_stats = group_standings[eg][2]
                elo_val = third_stats.get("elo", 1500)
                eligible_elos.append(elo_val)
        
        if eligible_elos:
            return sum(eligible_elos) / len(eligible_elos)
        return 1500
    
    # Fixed opponent
    if opp_group in group_standings:
        idx = opp_pos - 1  # 0-indexed
        if idx < len(group_standings[opp_group]):
            opp_team, opp_stats = group_standings[opp_group][idx]
            return opp_stats.get("elo", 1500)
    
    return 1500


def compute_path_difficulty(group, position, group_standings, ratings):
    """
    Compute cumulative path difficulty for a group position.
    
    Returns: {
        "r32_opponent_elo": float,
        "path_elo": float (cumulative),
        "difficulty": "easy"|"normal"|"hard",
        "opponent_description": str,
    }
    """
    # R32 opponent ELO
    r32_elo = get_likely_opponent(group, position, group_standings, ratings)
    
    # R16 estimate: average of possible next-round opponents
    # This is a rough estimate based on bracket structure
    r16_elo = r32_elo  # placeholder — simplified
    
    # Cumulative path difficulty
    # Higher = harder path
    path_elo = r32_elo
    
    # Difficulty classification
    if path_elo < 1750:
        difficulty = "easy"
    elif path_elo < 1900:
        difficulty = "normal"
    else:
        difficulty = "hard"
    
    # Build opponent description
    bracket = R32_BRACKET.get(group, {}).get(position, [])
    if bracket:
        opp_group, opp_pos = bracket[0]
        if opp_group == "3rd":
            desc = f"第三名球队({opp_pos})"
        else:
            desc = f"G{opp_group}-{opp_pos}"
    else:
        desc = "未知"
    
    return {
        "r32_opponent_elo": round(r32_elo),
        "path_elo": round(path_elo),
        "difficulty": difficulty,
        "opponent_description": desc,
    }


def compute_all_paths(group_standings, ratings):
    """Compute bracket path difficulty for all group positions."""
    results = {}
    
    for group in sorted(group_standings.keys()):
        for position in [1, 2]:
            key = f"{group}_{position}"
            results[key] = compute_path_difficulty(group, position, group_standings, ratings)
    
    return results


def compute_bpp_adjustment(group, team_position, group_standings, ratings):
    """
    Compute BPP ELO adjustment for a specific team.
    
    If path as group winner is significantly harder than as runner-up 
    (or vice versa), teams may have "strategic" motivation.
    
    Returns: (elo_adjustment, reason)
    """
    path_1st = compute_path_difficulty(group, 1, group_standings, ratings)
    path_2nd = compute_path_difficulty(group, 2, group_standings, ratings)
    
    diff = path_1st["path_elo"] - path_2nd["path_elo"]
    
    if team_position == 1:
        # Currently in 1st — if 2nd path is easier, may reduce motivation
        if diff > 100:
            return (-10, f"小组第二条路径更容易(低{diff} ELO)，可能策略性留力")
        elif diff > 50:
            return (-5, f"小组第二条路径略容易(低{diff} ELO)")
        else:
            return (0, f"小组第一路径更优或相当(差{abs(diff)} ELO)")
    else:
        # Currently in 2nd — if 1st path is much better, extra motivation
        if diff < -100:
            return (10, f"小组第一路径显著更好(高{abs(diff)} ELO)，抢头名动机强")
        elif diff < -50:
            return (5, f"小组第一路径略好(高{abs(diff)} ELO)")
        else:
            return (0, f"两条路径相当(差{abs(diff)} ELO)")


def main():
    print("=== BPP: Bracket Path Preference Analysis ===\n")
    
    ratings, group_standings = load_data()
    
    # Compute all paths
    paths = compute_all_paths(group_standings, ratings)
    
    print(f"{'Group-Pos':<10} {'R32 Opp':>8} {'Diff':>8} {'Description':<30}")
    print("-" * 60)
    
    output = {"generated": "", "paths": {}, "pairwise_comparison": {}}
    
    for key in sorted(paths.keys()):
        p = paths[key]
        group, pos = key.split("_")
        print(f"{key:<10} {p['r32_opponent_elo']:>8} {p['difficulty']:>8} {p['opponent_description']:<30}")
        output["paths"][key] = p
    
    # Pairwise comparison
    print("\n=== Strategic Implications ===\n")
    for group in sorted(group_standings.keys()):
        adj_1st = compute_bpp_adjustment(group, 1, group_standings, ratings)
        adj_2nd = compute_bpp_adjustment(group, 2, group_standings, ratings)
        
        path_1st = paths.get(f"{group}_1", {})
        path_2nd = paths.get(f"{group}_2", {})
        
        diff = path_1st.get("path_elo", 0) - path_2nd.get("path_elo", 0)
        signal = "⚠️" if abs(diff) > 100 else "  " if abs(diff) > 50 else "✅"
        
        print(f"  {signal} Group {group}: 1st path={path_1st.get('path_elo','?')} vs 2nd path={path_2nd.get('path_elo','?')} (diff={diff:+d})")
        print(f"     1st team BPP: {adj_1st[0]:+d} ELO — {adj_1st[1]}")
        print(f"     2nd team BPP: {adj_2nd[0]:+d} ELO — {adj_2nd[1]}")
        
        output["pairwise_comparison"][group] = {
            "path_diff": diff,
            "adjustment_1st": adj_1st[0],
            "adjustment_2nd": adj_2nd[0],
            "reason_1st": adj_1st[1],
            "reason_2nd": adj_2nd[1],
        }
    
    # Save
    output_path = os.path.join(DATA_DIR, "bracket_paths.json")
    from datetime import datetime, timezone, timedelta
    output["generated"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ BPP analysis saved to: {output_path}")


if __name__ == "__main__":
    main()
