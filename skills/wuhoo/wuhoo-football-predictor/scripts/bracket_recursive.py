#!/usr/bin/env python3.11
"""
bracket_recursive.py — Recursive Single-Match Bracket Simulation
=================================================================
Replaces the monolithic bracket_simulator.py with a recursive approach:
1. For each remaining match, run full 12-layer prediction (v5.5 engine)
2. Sample winner based on predicted probabilities
3. Advance winner to next round
4. Repeat N times (Monte Carlo)
5. Aggregate advancement/champion probabilities

Key difference from bracket_simulator.py:
- Every match gets detailed 12-layer audit (not just ELO+Poisson)
- Reasoning path (v5.5 inference engine) is included
- Scoreline probabilities for every match
- Per-match detail available even for future rounds

Usage:
  python3.11 scripts/bracket_recursive.py                    # 10 sims (default)
  python3.11 scripts/bracket_recursive.py --sims 50          # Custom sims
  python3.11 scripts/bracket_recursive.py --from-round R16   # Start from R16
"""

import json, os, sys, random, math
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
sys.path.insert(0, BASE_DIR)

from scripts.predict_v510 import predict_with_engine_v510 as predict_with_engine


def load_knockout_schedule():
    """Load knockout schedule with filled teams."""
    with open(os.path.join(DATA_DIR, "knockout_schedule.json")) as f:
        return json.load(f)


def get_match_order(ko):
    """Get ordered list of ALL knockout matches (including future rounds with null teams).
    Returns list of (match_dict, round_name) sorted by match_id.
    Only includes uncompleted matches.
    """
    stages_order = ["R32", "R16", "QF", "SF", "3rd", "F"]
    matches = []
    for stage in stages_order:
        if stage not in ko.get("stages", {}):
            continue
        for m in ko["stages"][stage]["matches"]:
            if m.get("status") == "completed":
                continue
            # Include matches even if teams are null (will resolve from winners)
            matches.append((m, stage))
    matches.sort(key=lambda x: x[0]["match_id"])
    return matches


def predict_match(team_a, team_b, match_id, knockout_round, knockout=True):
    """Run full 12-layer prediction with v5.5 engine.
    Returns detailed audit dict.
    """
    try:
        result = predict_with_engine(
            team_a, team_b,
            match_id=match_id,
            knockout=knockout,
            enable_news=True,
            rules_version="v3"
        )
        return result
    except Exception as e:
        print(f"  [WARN] predict_with_engine failed for {team_a} vs {team_b}: {e}")
        # Fallback to basic predict_single_match
        from wc2026_predict import predict_single_match
        return predict_single_match(team_a, team_b, match_id=match_id, knockout=knockout)


def sample_winner(prediction, knockout=True):
    """Sample a winner based on predicted probabilities.
    For knockout: if draw, do coin flip (50/50).
    Returns winning team name.
    """
    p = prediction.get("prediction", prediction)
    p_a = (p.get("team_a_win") or 33) / 100.0
    p_draw = (p.get("draw") or 33) / 100.0
    p_b = (p.get("team_b_win") or 33) / 100.0

    if knockout:
        # In knockout, draws resolved by extra time → 50/50
        # Scale win probabilities excluding draw
        total = p_a + p_b
        if total > 0:
            p_a = p_a / total
            p_b = p_b / total
        else:
            p_a = p_b = 0.5

    r = random.random()
    if r < p_a:
        return prediction["team_a"]
    elif r < p_a + p_draw and not knockout:
        return "draw"
    else:
        return prediction["team_b"]


def extract_scoreline_probs(pred):
    """Extract scoreline probabilities from v5.5 prediction output."""
    # v5.5 predict_with_engine already has scoreline_probs in prediction
    p = pred.get("prediction", {})
    sc = p.get("scoreline_probs", [])
    if sc:
        return sc  # Already in correct format [{score, prob_pct}, ...]
    # Fallback: expected goals
    eg_a = p.get("expected_goals_a", 1.4)
    eg_b = p.get("expected_goals_b", 1.0)
    return [{"score": f"{round(eg_a)}-{round(eg_b)}", "prob_pct": None, "note": "expected"}]


def extract_reasoning_path(prediction):
    """Extract v5.5 reasoning path."""
    audit = prediction.get("audit", prediction)
    return audit.get("inference_trace", audit.get("reasoning_path", None))


def run_bracket_simulation(n_sims=10):
    """Main recursive bracket simulation."""
    print(f"\n{'='*60}")
    print(f"BRACKET RECURSIVE SIMULATION — {n_sims} Monte Carlo runs")
    print(f"{'='*60}\n")

    ko = load_knockout_schedule()
    remaining_matches = get_match_order(ko)
    
    if not remaining_matches:
        print("No remaining matches to simulate!")
        return None

    print(f"Remaining matches: {len(remaining_matches)}")
    for m, stage in remaining_matches:
        print(f"  M{m['match_id']} ({stage}): {m.get('team_a','?')} vs {m.get('team_b','?')} [{m.get('date_beijing','?')}]")

    # === Phase 1: Detailed predictions for known teams (deterministic) ===
    print(f"\n--- Phase 1: Running detailed predictions ---")
    match_details = {}
    for m, stage in remaining_matches:
        mid = m["match_id"]
        ta, tb = m.get("team_a"), m.get("team_b")
        
        # Skip future rounds where teams are not yet known
        if ta is None or tb is None:
            match_details[mid] = {
                "match_id": mid,
                "round": stage,
                "date": m.get("date_beijing", ""),
                "team_a": None,
                "team_b": None,
                "venue": m.get("venue", ""),
                "source": m.get("source", ""),
                "prediction": {"team_a_win_pct": None, "draw_pct": None, "team_b_win_pct": None},
                "scoreline_probs": [],
                "reasoning_path": None,
                "most_likely": None,
                "verdict": {},
                "pending": True
            }
            continue
        
        pred = predict_match(ta, tb, mid, stage, knockout=True)
        pdata = pred.get("prediction", {})
        eff = pred.get("effective_elo", {})
        match_details[mid] = {
            "match_id": mid,
            "round": stage,
            "date": m.get("date_beijing", ""),
            "team_a": ta,
            "team_b": tb,
            "venue": m.get("venue", ""),
            "prediction": {
                "team_a_win_pct": pdata.get("team_a_win", None),
                "draw_pct": pdata.get("draw", None),
                "team_b_win_pct": pdata.get("team_b_win", None),
                "expected_goals_a": pdata.get("expected_goals_a", None),
                "expected_goals_b": pdata.get("expected_goals_b", None),
            },
            "effective_elo": {
                "team_a": eff.get("team_a", {}),
                "team_b": eff.get("team_b", {}),
                "diff": eff.get("diff", None),
            },
            "scoreline_probs": extract_scoreline_probs(pred),
            "reasoning_path": pred.get("reasoning_path", None),
            "most_likely": pdata.get("most_likely_score", ""),
            "verdict": pred.get("verdict", {}),
        }
        # Print quick verdict
        p = pred.get("prediction", {})
        pa, pd, pb = p.get("team_a_win", 0), p.get("draw", 0), p.get("team_b_win", 0)
        print(f"→ {ta} {pa:.0f}% / Draw {pd:.0f}% / {tb} {pb:.0f}%")
    
    # === Phase 1b: Most likely bracket path (deterministic) ===
    print(f"\n--- Phase 1b: Most likely path ---")
    
    # Load completed matches to seed winners/losers for source resolution
    ko_completed_matches = {}
    for stage in ["R32", "R16", "QF", "SF", "3rd", "F"]:
        if stage not in ko.get("stages", {}):
            continue
        for m in ko["stages"][stage]["matches"]:
            if m.get("status") == "completed" and m.get("winner"):
                ko_completed_matches[m["match_id"]] = {
                    "winner": m["winner"],
                    "stage": stage,
                }
    
    mlp_winners = {}  # match_id → winner (highest probability)
    mlp_losers = {}
    
    # Pre-seed completed match winners for source resolution
    for mid, cm in ko_completed_matches.items():
        for stage in ["R32", "R16", "QF", "SF", "3rd", "F"]:
            if stage not in ko.get("stages", {}):
                continue
            for m in ko["stages"][stage]["matches"]:
                if m["match_id"] == mid:
                    ta, tb = m.get("team_a"), m.get("team_b")
                    if ta and tb:
                        mlp_winners[mid] = cm["winner"]
                        mlp_losers[mid] = tb if cm["winner"] == ta else ta
                    break
            if mid in mlp_winners:
                break
    
    for m, stage in remaining_matches:
        mid = m["match_id"]
        ta = m.get("team_a")
        tb = m.get("team_b")
        
        # Resolve future round teams from mlp winners
        if ta is None or tb is None:
            src = m.get("source", "")
            if "W" in src and "vs" in src:
                parts = src.split(" vs ")
                try:
                    w1_id = int(parts[0].replace("W", "").strip())
                    w2_id = int(parts[1].replace("W", "").strip())
                    ta = mlp_winners.get(w1_id)
                    tb = mlp_winners.get(w2_id)
                except ValueError:
                    pass
            if "L" in src and "vs" in src:
                parts = src.split(" vs ")
                try:
                    l1_id = int(parts[0].replace("L", "").strip())
                    l2_id = int(parts[1].replace("L", "").strip())
                    ta = mlp_losers.get(l1_id)
                    tb = mlp_losers.get(l2_id)
                except ValueError:
                    pass
        
        if ta is None or tb is None:
            continue
        
        # For R16, use pre-computed prediction; for future rounds, predict now
        if mid in match_details and not match_details[mid].get("pending"):
            md = match_details[mid]
            pa = md["prediction"]["team_a_win_pct"]
            pb = md["prediction"]["team_b_win_pct"]
            pd_val = md["prediction"]["draw_pct"]
        else:
            pred = predict_match(ta, tb, mid, stage, knockout=True)
            pdata = pred.get("prediction", {})
            eff = pred.get("effective_elo", {})
            pa = pdata.get("team_a_win", 50)
            pd_val = pdata.get("draw", 0)
            pb = pdata.get("team_b_win", 50)
            match_details[mid] = {
                "match_id": mid, "round": stage,
                "date": m.get("date_beijing", ""),
                "team_a": ta, "team_b": tb,
                "venue": m.get("venue", ""),
                "prediction": {
                    "team_a_win_pct": pa, "draw_pct": pd_val, "team_b_win_pct": pb,
                    "expected_goals_a": pdata.get("expected_goals_a"),
                    "expected_goals_b": pdata.get("expected_goals_b"),
                },
                "effective_elo": {
                    "team_a": eff.get("team_a", {}),
                    "team_b": eff.get("team_b", {}),
                    "diff": eff.get("diff"),
                },
                "scoreline_probs": extract_scoreline_probs(pred),
                "most_likely": pdata.get("most_likely_score", ""),
                "verdict": pred.get("verdict", {}),
                "pending": False,
            }
        
        # Determine winner: highest probability (excluding draw for knockout)
        if pa > pb:
            mlp_winners[mid] = ta
            mlp_losers[mid] = tb
        else:
            mlp_winners[mid] = tb
            mlp_losers[mid] = ta
        
        print(f"  M{mid} ({stage}): {ta} {pa:.0f}% vs {tb} {pb:.0f}% → {mlp_winners[mid]} 晋级")
    
    # === Phase 2: Monte Carlo simulation ===
    print(f"\n--- Phase 2: Running {n_sims} Monte Carlo simulations ---")
    print(f"  Pre-seeded winners from {len(ko_completed_matches)} completed matches")
    
    # Track results
    advancement = defaultdict(lambda: defaultdict(int))
    champion_count = Counter()
    path_counter = Counter()  # bracket path hash → count
    
    for sim in range(n_sims):
        # Seed winners/losers from completed matches at start of each sim
        winners = {}
        losers = {}
        for mid, cm in ko_completed_matches.items():
            # Find team_a/team_b from knockout_schedule
            team_a = team_b = None
            for stage in ["R32", "R16", "QF", "SF", "3rd", "F"]:
                if stage not in ko.get("stages", {}):
                    continue
                for m in ko["stages"][stage]["matches"]:
                    if m["match_id"] == mid:
                        team_a = m.get("team_a")
                        team_b = m.get("team_b")
                        break
                if team_a:
                    break
            if team_a and team_b:
                winners[mid] = cm["winner"]
                losers[mid] = team_b if cm["winner"] == team_a else team_a
                # Track advancement for completed match winner
                advancement[cm["winner"]][cm["stage"]] += 1
        
        for m, stage in remaining_matches:
            mid = m["match_id"]
            
            # Resolve teams
            ta = m.get("team_a")
            tb = m.get("team_b")
            
            # Parse source for future rounds ("W89 vs W90" → lookup winners)
            if ta is None or tb is None:
                src = m.get("source", "")
                if "W" in src and "vs" in src:
                    parts = src.split(" vs ")
                    w1_str = parts[0].replace("W", "").strip()
                    w2_str = parts[1].replace("W", "").strip()
                    try:
                        w1_id = int(w1_str)
                        w2_id = int(w2_str)
                        ta = winners.get(w1_id)
                        tb = winners.get(w2_id)
                    except ValueError:
                        pass
                # Also handle loser source ("L101 vs L102" for 3rd place)
                if "L" in src and "vs" in src:
                    parts = src.split(" vs ")
                    l1_str = parts[0].replace("L", "").strip()
                    l2_str = parts[1].replace("L", "").strip()
                    try:
                        l1_id = int(l1_str)
                        l2_id = int(l2_str)
                        # For 3rd place: the LOSERS of semi-finals
                        ta = losers.get(l1_id)
                        tb = losers.get(l2_id)
                    except ValueError:
                        pass
            
            if ta is None or tb is None:
                continue
            
            # Use match_details from Phase 1b for sampling probabilities
            md = match_details.get(mid, {})
            pa = md.get("prediction", {}).get("team_a_win_pct") or 50
            pd_val = md.get("prediction", {}).get("draw_pct") or 33
            pb = md.get("prediction", {}).get("team_b_win_pct") or 50
            
            # Sample winner
            pred_for_sample = {
                "team_a": ta,
                "team_b": tb,
                "prediction": {"team_a_win": pa, "draw": pd_val, "team_b_win": pb}
            }
            winner = sample_winner(pred_for_sample, knockout=True)
            winners[mid] = winner
            loser = tb if winner == ta else ta
            losers[mid] = loser
            
            # Track advancement
            advancement[winner][stage] += 1
        # Track champion
        final_matches = [m for m, s in remaining_matches if s == "F"]
        if final_matches:
            final_winner = winners.get(final_matches[0]["match_id"])
            if final_winner:
                champion_count[final_winner] += 1
        
        # Track bracket path
        path = {"R16": {}, "QF": {}, "SF": {}, "3rd": {}, "F": {}}
        for m, stage in remaining_matches:
            mid = m["match_id"]
            w = winners.get(mid)
            if w:
                stage_k = stage if stage in path else "F"
                path[stage_k][str(mid)] = w
        path_key = json.dumps(path, sort_keys=True, ensure_ascii=False)
        path_counter[path_key] += 1
        
        if sim % max(1, n_sims // 5) == 0 or sim == n_sims - 1:
            print(f"  Sim {sim+1}/{n_sims} complete", end="\r")
    
    print(f"\n  All {n_sims} simulations complete.")
    
    # === Phase 3: Aggregate results ===
    print(f"\n--- Phase 3: Aggregating results ---")
    
    # Calculate advancement probabilities
    adv_probs = {}
    for team, rounds in advancement.items():
        adv_probs[team] = {
            r: count / n_sims * 100
            for r, count in rounds.items()
        }
    
    # Champion probabilities
    champ_probs = {
        team: count / n_sims * 100
        for team, count in champion_count.most_common()
    }
    
    # Sort by champion probability
    sorted_champs = sorted(champ_probs.items(), key=lambda x: -x[1])
    
    print("\n=== CHAMPION PROBABILITIES ===")
    for i, (team, prob) in enumerate(sorted_champs[:10]):
        bar = "█" * int(prob / 2)
        print(f"  {i+1:2d}. {team:25s} {prob:5.1f}% {bar}")
    
    # Build output
    output = {
        "n_sims": n_sims,
        "generated": datetime.now().isoformat(),
        "total_remaining_matches": len(remaining_matches),
        "match_details": {str(k): v for k, v in match_details.items()},
        "advancement_probs": adv_probs,
        "champion_probs": champ_probs,
        "top_bracket_paths": [
            {"count": c, "path": json.loads(p)}
            for p, c in path_counter.most_common(3)
        ],
    }
    
    # Save
    out_path = os.path.join(DATA_DIR, "bracket_recursive_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved: {out_path}")
    
    # Save summary
    summary_path = os.path.join(DATA_DIR, "reports", f"bracket_recursive_{datetime.now().strftime('%Y%m%d_%H%M')}.md")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    
    with open(summary_path, "w") as f:
        f.write(f"# WC2026 Bracket Recursive Simulation\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')} CST\n")
        f.write(f"**Simulations**: {n_sims}\n")
        f.write(f"**Remaining matches**: {len(remaining_matches)}\n\n")
        f.write(f"## Champion Probabilities\n\n")
        for i, (team, prob) in enumerate(sorted_champs[:16]):
            f.write(f"| {i+1} | {team} | {prob:.1f}% |\n")
        f.write(f"\n## Match Details\n\n")
        for mid, detail in sorted(match_details.items()):
            f.write(f"### M{mid}: {detail['team_a']} vs {detail['team_b']} ({detail['round']})\n")
            f.write(f"- Date: {detail['date']}\n")
            f.write(f"- Venue: {detail['venue']}\n")
            p = detail['prediction']
            pa = p.get('team_a_win_pct')
            pb = p.get('team_b_win_pct')
            pd_val = p.get('draw_pct')
            if pa is not None and pb is not None:
                f.write(f"- Prediction: {detail['team_a']} {pa:.0f}% / Draw {pd_val:.0f}% / {detail['team_b']} {pb:.0f}%\n")
            else:
                f.write(f"- Prediction: pending (teams TBD)\n")
            if detail.get('most_likely'):
                f.write(f"- Most likely score: {detail['most_likely']}\n")
            if detail.get('scoreline_probs'):
                f.write(f"- Scoreline probs: {', '.join(s['score'] for s in detail['scoreline_probs'][:3])}\n")
            f.write("\n")
    
    print(f"Saved summary: {summary_path}")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Recursive bracket simulation")
    parser.add_argument("--sims", type=int, default=10, help="Number of Monte Carlo simulations")
    parser.add_argument("--from-round", type=str, default=None, help="Start from this round (R16, QF, SF)")
    args = parser.parse_args()
    
    random.seed(42)  # Reproducible
    run_bracket_simulation(n_sims=args.sims)
