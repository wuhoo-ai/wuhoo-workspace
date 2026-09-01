#!/usr/bin/env python3.11
"""
Third-Place Qualification Tracker — 第三名出线实时追踪
v1.0 — WC2026

Tracks the "best 8 of 12 third-place teams" standings.
Essential for MD3 predictions — teams with 3pts+GD0 may be 
content with a draw (70% chance to advance as 3rd).

Usage:
  python3.11 scripts/compute_third_place.py
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_data():
    schedule = json.load(open(os.path.join(DATA_DIR, "wc2026_schedule.json")))
    elo = json.load(open(os.path.join(DATA_DIR, "elo_ratings.json")))
    return schedule, elo


def compute_third_place_standings(schedule, elo):
    """Compute current third-place team rankings across all groups."""
    ratings = elo.get("ratings", {})
    
    groups = defaultdict(lambda: defaultdict(lambda: {"pts": 0, "gf": 0, "ga": 0, "mp": 0}))
    
    for m in schedule.get("matches", []):
        g = m.get("group", "?")
        if g == "?" or m.get("status") != "completed":
            continue
        
        ta, tb = m["team_a"], m["team_b"]
        sa, sb = m.get("score_a"), m.get("score_b")
        if sa is None or sb is None:
            continue
        sa, sb = int(sa), int(sb)
        
        groups[g][ta]["mp"] += 1; groups[g][ta]["gf"] += sa; groups[g][ta]["ga"] += sb
        groups[g][tb]["mp"] += 1; groups[g][tb]["gf"] += sb; groups[g][tb]["ga"] += sa
        
        if sa > sb: groups[g][ta]["pts"] += 3
        elif sb > sa: groups[g][tb]["pts"] += 3
        else: groups[g][ta]["pts"] += 1; groups[g][tb]["pts"] += 1
    
    # Extract 3rd place from each group
    third_place_teams = []
    for g in sorted(groups.keys()):
        team_list = []
        for team, stats in groups[g].items():
            elo_val = ratings.get(team, {}).get("elo", 1500) if isinstance(ratings.get(team), dict) else ratings.get(team, 1500)
            team_list.append({
                "team": team,
                "group": g,
                "elo": elo_val,
                "pts": stats["pts"],
                "mp": stats["mp"],
                "gf": stats["gf"],
                "ga": stats["ga"],
                "gd": stats["gf"] - stats["ga"],
            })
        
        team_list.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"], -x["elo"]))
        
        if len(team_list) >= 3:
            third_place_teams.append(team_list[2])
    
    # Sort all third-place teams: pts desc, gd desc, gf desc
    third_place_teams.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"], -x["elo"]))
    
    return third_place_teams


def estimate_advancement_prob(team_data, all_third_place):
    """
    Estimate probability of advancing as a third-place team.
    
    Based on current position and gap to 8th place.
    8 of 12 third-place teams advance.
    """
    pts = team_data["pts"]
    gd = team_data["gd"]
    gf = team_data["gf"]
    
    # Current rank
    rank = None
    for i, t in enumerate(all_third_place):
        if t["team"] == team_data["team"]:
            rank = i + 1
            break
    
    if rank is None:
        return 0.0
    
    # If in top 8
    if rank <= 7:
        # Check gap to 9th
        if len(all_third_place) >= 9:
            ninth = all_third_place[8]
            gap = (pts - ninth["pts"]) * 10 + (gd - ninth["gd"]) * 2
            if gap > 20:
                return 0.95
            elif gap > 10:
                return 0.85
            elif gap > 5:
                return 0.75
            else:
                return 0.65
        return 0.90
    
    # If 8th or 9th (borderline)
    if rank == 8:
        if len(all_third_place) >= 9:
            ninth = all_third_place[8]
            if pts > ninth["pts"]:
                return 0.60
            else:
                return 0.45
        return 0.55
    
    # If 9th-12th
    if len(all_third_place) >= 8:
        eighth = all_third_place[7]
        if pts < eighth["pts"]:
            return 0.15
        elif gd < eighth["gd"] - 2:
            return 0.25
        else:
            return 0.40
    
    return 0.20


def main():
    schedule, elo = load_data()
    third_place = compute_third_place_standings(schedule, elo)
    
    print("=== Third-Place Qualification Standings ===\n")
    print(f"{'Rank':<5} {'Team':<25} {'Pts':>4} {'MP':>3} {'GD':>5} {'GF':>4} {'GA':>4} {'Adv%':>6} {'Status':<12}")
    print("-" * 80)
    
    output = {"generated": "", "standings": [], "cut_line": {}, "notes": []}
    
    for i, t in enumerate(third_place):
        adv_prob = estimate_advancement_prob(t, third_place)
        
        if i < 8:
            status = "✅ IN" if i < 7 else "⚠️ BORDER"
        else:
            status = "❌ OUT"
        
        print(f"{i+1:<5} {t['team']:<25} {t['pts']:>4} {t['mp']:>3} {t['gd']:>+5} {t['gf']:>4} {t['ga']:>4} {adv_prob:>5.0%}  {status:<12}")
        
        output["standings"].append({
            "rank": i + 1,
            "team": t["team"],
            "group": t["group"],
            "pts": t["pts"],
            "mp": t["mp"],
            "gd": t["gd"],
            "gf": t["gf"],
            "ga": t["ga"],
            "advancement_probability": round(adv_prob, 2),
            "status": status.strip(),
        })
    
    # Cut line analysis
    if len(third_place) >= 8:
        eighth = third_place[7]
        output["cut_line"] = {
            "eighth_place": {"team": eighth["team"], "pts": eighth["pts"], "gd": eighth["gd"]},
            "current_threshold": f"{eighth['pts']}pts, GD{eighth['gd']:+d}",
        }
        print(f"\n  8th place (cut line): {eighth['team']} — {eighth['pts']}pts GD{eighth['gd']:+d}")
    
    output["notes"] = [
        "Top 8 of 12 third-place teams advance to Round of 32",
        "Advancement probability based on current standings — MD3 results will change this",
        "3pts + GD0 estimated ~70% advancement probability (Opta data)",
    ]
    
    # Save
    output_path = os.path.join(DATA_DIR, "third_place_standings.json")
    output["generated"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to: {output_path}")


if __name__ == "__main__":
    main()
