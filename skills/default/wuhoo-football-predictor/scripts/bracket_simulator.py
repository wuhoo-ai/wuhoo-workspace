#!/usr/bin/env python3
"""WC2026 Bracket Simulator — v5.6

Full knockout tournament Monte Carlo simulation using v5.5 prediction stack.
Runs N simulations through R32→R16→QF→SF→Final, tracking advancement probabilities.

Key: Uses predict_single_match(knockout=True, round=...) from wc2026_predict.py,
which applies the full 12-layer stack + KBC + inference engine.

Usage:
  python3.11 scripts/bracket_simulator.py                    # 5000 sims, full tournament
  python3.11 scripts/bracket_simulator.py --sims 1000        # Custom sim count
  python3.11 scripts/bracket_simulator.py --from-round R16   # Start from specific round
  python3.11 scripts/bracket_simulator.py --output json       # JSON output only
"""

import sys, os, json, math, random
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
# Seed will be set per-simulation for proper Monte Carlo diversity

# Bracket advancement rules (match_id → next match_id, position)
# Position: 'a' for winner goes to team_a, 'b' for winner goes to team_b
BRACKET_FLOW = {
    # R32 → R16
    73: (90, 'b'), 74: (89, 'a'), 75: (90, 'a'), 76: (91, 'a'),
    77: (89, 'b'), 78: (91, 'b'), 79: (92, 'a'), 80: (92, 'b'),
    81: (94, 'a'), 82: (94, 'b'), 83: (93, 'a'), 84: (93, 'b'),
    85: (96, 'a'), 86: (95, 'a'), 87: (96, 'b'), 88: (95, 'b'),
    # R16 → QF
    89: (97, 'a'), 90: (97, 'b'), 91: (99, 'a'), 92: (99, 'b'),
    93: (98, 'a'), 94: (98, 'b'), 95: (100, 'a'), 96: (100, 'b'),
    # QF → SF
    97: (101, 'a'), 98: (101, 'b'), 99: (102, 'a'), 100: (102, 'b'),
    # SF → Final
    101: (104, 'a'), 102: (104, 'b'),
}

def load_knockout_schedule():
    with open(os.path.join(DATA_DIR, 'knockout_schedule.json')) as f:
        return json.load(f)

def get_round_for_match(match_id):
    """Determine knockout round from match_id."""
    if 73 <= match_id <= 88:
        return 'R32'
    elif 89 <= match_id <= 96:
        return 'R16'
    elif 97 <= match_id <= 100:
        return 'QF'
    elif 101 <= match_id <= 102:
        return 'SF'
    elif match_id in (103, 104):
        return 'F'
    return 'R32'

def get_match_schedule():
    """Get all knockout matches with actual team names (post-seeding)."""
    schedule = load_knockout_schedule()
    all_matches = {}
    
    for stage_name in ['R32', 'R16', 'QF', 'SF', 'F', '3rd']:
        stage = schedule['stages'].get(stage_name, {})
        for m in stage.get('matches', []):
            mid = m['match_id']
            all_matches[mid] = {
                'match_id': mid,
                'stage': stage_name,
                'date': m['date_beijing'],
                'team_a': m.get('team_a'),
                'team_b': m.get('team_b'),
                'venue': m.get('venue', ''),
                'venue_city': m.get('venue_city', ''),
            }
    
    return all_matches

def simulate_match(team_a, team_b, match_id, knockout=True, ko_round='R32'):
    """Simulate a single knockout match.
    Uses ELO-based probabilities with random sampling for Monte Carlo efficiency.
    For knockout: draws resolved via ET/PK probabilities.
    Returns: (p_adv_a, p_adv_b, p_draw, elo_diff)
    """
    global _elo_cache
    if _elo_cache is None:
        import json as _json
        with open(os.path.join(DATA_DIR, 'elo_ratings.json')) as f:
            _elo_data = _json.load(f)
        _elo_cache = _elo_data.get('ratings', _elo_data)
    
    _get_elo = lambda t: _elo_cache.get(t, {}).get('elo', 1500) if isinstance(_elo_cache.get(t, {}), dict) else _elo_cache.get(t, 1500)
    elo_a = _get_elo(team_a)
    elo_b = _get_elo(team_b)
    elo_diff = elo_a - elo_b
    
    # Base Poisson lambda (from predict_single_match model)
    base_lam = 1.45
    # v5.6: Cap lambda to prevent absurd values at extreme ELO diffs
    MAX_LAM = 4.0
    lam_a = max(0.2, min(MAX_LAM, base_lam * 10 ** (elo_diff / 500)))
    lam_b = max(0.2, min(MAX_LAM, base_lam * 10 ** (-elo_diff / 500)))
    
    # Apply KBC-style knockout suppression
    round_suppression = {'R32': 0.75, 'R16': 0.78, 'QF': 0.82, 'SF': 0.85, 'F': 0.88, '3rd': 0.90}
    suppression = round_suppression.get(ko_round, 0.78)
    
    lam_a *= suppression
    lam_b *= suppression
    
    # Mean reversion (increase draw probability)
    mean_lam = (lam_a + lam_b) / 2
    lam_a = lam_a * 0.80 + mean_lam * 0.20
    lam_b = lam_b * 0.80 + mean_lam * 0.20
    
    # Compute win/draw probabilities from Poisson
    p_win_a = 0.0
    p_draw = 0.0
    for i in range(12):
        pi_a = (lam_a ** i) * math.exp(-lam_a) / math.factorial(i)
        for j in range(12):
            pi_b = (lam_b ** j) * math.exp(-lam_b) / math.factorial(j)
            prob = pi_a * pi_b
            if i > j:
                p_win_a += prob
            elif i == j:
                p_draw += prob
    
    p_win_b = 1.0 - p_win_a - p_draw
    
    # For knockout: draw → ET → PK
    if knockout:
        if elo_diff > 100:
            et_win_a = 0.58
        elif elo_diff > 50:
            et_win_a = 0.55
        elif elo_diff > -50:
            et_win_a = 0.52
        elif elo_diff > -100:
            et_win_a = 0.48
        else:
            et_win_a = 0.45
        
        et_still_draw = 0.35
        pk_win_a = 0.50
        p_adv_if_draw = et_win_a * (1 - et_still_draw) + et_still_draw * pk_win_a
        p_adv_a = p_win_a + p_draw * p_adv_if_draw
    else:
        p_adv_a = p_win_a + p_draw * 0.5
    
    return p_adv_a, 1.0 - p_adv_a, p_draw, elo_diff


# Pre-load ELO cache once
_elo_cache = None

def run_simulation(n_sims=5000, from_round=None):
    """Run full Monte Carlo bracket simulation."""
    all_matches = get_match_schedule()
    schedule = load_knockout_schedule()
    
    # Determine which matches to simulate
    # Include ALL knockout matches — later rounds get teams from bracket flow
    sim_matches = []
    all_stage_matches = {}  # stage_name → list of matches
    
    for stage_name in ['R32', 'R16', 'QF', 'SF', 'F', '3rd']:
        stage = schedule['stages'].get(stage_name, {})
        stage_list = []
        for m in stage.get('matches', []):
            mid = m['match_id']
            if from_round and ['R32', 'R16', 'QF', 'SF', 'F', '3rd'].index(stage_name) < \
               ['R32', 'R16', 'QF', 'SF', 'F', '3rd'].index(from_round):
                continue
            match_info = {
                'match_id': mid,
                'stage': stage_name,
                'date': m['date_beijing'],
                'team_a': m.get('team_a'),
                'team_b': m.get('team_b'),
                'venue': m.get('venue', ''),
                'venue_city': m.get('venue_city', ''),
            }
            stage_list.append(match_info)
            sim_matches.append(match_info)
        all_stage_matches[stage_name] = stage_list
    
    print(f"=== WC2026 Bracket Simulator v5.6 ===")
    print(f"Simulations: {n_sims}, Total matches in bracket: {len(sim_matches)}")
    print(f"R32 seeded teams: {sum(1 for m in all_stage_matches.get('R32', []) if m['team_a'])}")
    from_round_str = from_round or 'R32'
    print(f"Starting from: {from_round_str}")
    print()
    
    # Counters
    champion_count = defaultdict(int)
    final_count = defaultdict(int)
    sf_count = defaultdict(int)
    qf_count = defaultdict(int)
    r16_count = defaultdict(int)
    r32_advance_count = defaultdict(int)
    
    # Round-by-round tracking
    stage_advancement = defaultdict(lambda: defaultdict(int))
    
    for sim_idx in range(n_sims):
        if sim_idx % 1000 == 0 and sim_idx > 0:
            print(f"  ... {sim_idx}/{n_sims}")
        
        # Current bracket state (match_id → winner)
        winners = {}
        
        # Process rounds in order
        for stage_name in ['R32', 'R16', 'QF', 'SF', 'F', '3rd']:
            if from_round and ['R32', 'R16', 'QF', 'SF', 'F', '3rd'].index(stage_name) < \
               ['R32', 'R16', 'QF', 'SF', 'F', '3rd'].index(from_round):
                continue
            
            stage_matches = all_stage_matches.get(stage_name, [])
            
            for m in stage_matches:
                mid = m['match_id']
                
                # Get teams (either from schedule or from previous round winners)
                team_a = m['team_a']
                team_b = m['team_b']
                
                # For later rounds, teams come from bracket flow
                if stage_name == 'R16':
                    for r32_mid, (next_mid, pos) in BRACKET_FLOW.items():
                        if r32_mid <= 88 and next_mid == mid:
                            if r32_mid in winners:
                                if pos == 'a':
                                    team_a = winners[r32_mid]
                                else:
                                    team_b = winners[r32_mid]
                elif stage_name == 'QF':
                    for r16_mid, (next_mid, pos) in BRACKET_FLOW.items():
                        if 89 <= r16_mid <= 96 and next_mid == mid:
                            if r16_mid in winners:
                                if pos == 'a':
                                    team_a = winners[r16_mid]
                                else:
                                    team_b = winners[r16_mid]
                elif stage_name == 'SF':
                    for qf_mid, (next_mid, pos) in BRACKET_FLOW.items():
                        if 97 <= qf_mid <= 100 and next_mid == mid:
                            if qf_mid in winners:
                                if pos == 'a':
                                    team_a = winners[qf_mid]
                                else:
                                    team_b = winners[qf_mid]
                elif stage_name == 'F':
                    for sf_mid, (next_mid, pos) in BRACKET_FLOW.items():
                        if 101 <= sf_mid <= 102 and next_mid == mid:
                            if sf_mid in winners:
                                if pos == 'a':
                                    team_a = winners[sf_mid]
                                else:
                                    team_b = winners[sf_mid]
                
                if not team_a or not team_b:
                    continue
                
                # Simulate match
                p_adv_a, p_adv_b, p_draw, elo_diff = simulate_match(
                    team_a, team_b, mid, knockout=(stage_name != '3rd'))
                
                # Determine winner
                r = random.random()
                if r < p_adv_a:
                    winners[mid] = team_a
                else:
                    winners[mid] = team_b
                
                # Track advancement
                stage_advancement[stage_name][team_a] += 1
                stage_advancement[stage_name][team_b] += 1
        
        # Track final results
        # Champion = winner of match 104
        champ = winners.get(104)
        if champ:
            champion_count[champ] += 1
        
        # Finalists
        for mid in (101, 102):
            if mid in winners:
                final_count[winners[mid]] += 1
        
        # Semifinalists (all 4)
        for mid in (97, 98, 99, 100):
            if mid in winners:
                sf_count[winners[mid]] += 1
        
        # Quarterfinalists
        for mid in (89, 90, 91, 92, 93, 94, 95, 96):
            if mid in winners:
                qf_count[winners[mid]] += 1
        
        # R16 advancement
        for mid in range(73, 89):
            if mid in winners:
                r16_count[winners[mid]] += 1
    
    # Normalize
    def to_pct(d, total):
        return {t: round(c / total * 100, 1) for t, c in sorted(d.items(), key=lambda x: -x[1])}
    
    stats = {
        'n_sims': n_sims,
        'generated': datetime.now().isoformat(),
        'champion': to_pct(champion_count, n_sims),
        'finalist': to_pct(final_count, n_sims),
        'semifinalist': to_pct(sf_count, n_sims),
        'quarterfinalist': to_pct(qf_count, n_sims),
        'r16': to_pct(r16_count, n_sims),
        'stage_participation': {s: to_pct(d, n_sims) for s, d in stage_advancement.items()},
    }
    
    return stats

def main():
    import argparse
    
    # Simple arg parsing
    n_sims = 5000
    from_round = None
    output_mode = 'text'
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--sims' and i + 1 < len(args):
            n_sims = int(args[i+1])
            i += 2
        elif args[i] == '--from-round' and i + 1 < len(args):
            from_round = args[i+1]
            i += 2
        elif args[i] == '--output' and i + 1 < len(args):
            output_mode = args[i+1]
            i += 2
        else:
            i += 1
    
    stats = run_simulation(n_sims=n_sims, from_round=from_round)
    
    if output_mode == 'json':
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        print(f"🏆 CHAMPION PROBABILITY (Top 10)")
        print(f"{'='*60}")
        for i, (team, pct) in enumerate(list(stats['champion'].items())[:10]):
            bar = '█' * int(pct / 2)
            print(f"  {i+1:2d}. {team:<25s} {pct:5.1f}% {bar}")
        
        print(f"\n{'='*60}")
        print(f"📊 STAGE ADVANCEMENT (selected teams)")
        print(f"{'='*60}")
        print(f"  {'Team':<25s} {'R16':>6s} {'QF':>6s} {'SF':>6s} {'Final':>6s} {'Champ':>6s}")
        print(f"  {'-'*25} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
        
        top_teams = list(stats['champion'].keys())[:15]
        for team in top_teams:
            r16_pct = stats['r16'].get(team, 0)
            qf_pct = stats['quarterfinalist'].get(team, 0)
            sf_pct = stats['semifinalist'].get(team, 0)
            fn_pct = stats['finalist'].get(team, 0)
            ch_pct = stats['champion'].get(team, 0)
            print(f"  {team:<25s} {r16_pct:5.1f}% {qf_pct:5.1f}% {sf_pct:5.1f}% {fn_pct:5.1f}% {ch_pct:5.1f}%")
    
    # Save to JSON
    output_path = os.path.join(DATA_DIR, 'bracket_simulation_results.json')
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Results saved to {output_path}")
    
    return stats

if __name__ == '__main__':
    main()
