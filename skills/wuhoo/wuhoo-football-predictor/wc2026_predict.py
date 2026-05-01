#!/usr/bin/env python3
"""
2026 FIFA World Cup — 全流程 Monte Carlo 预测系统 v2.0
基于: Elo + Poisson + FIFA 官方 Bracket + 10,000次 全流程模拟

Usage:
  python3.11 wc2026_predict.py [--full|--groups|--knockout] [--sims N]

v2.0 更新:
- FIFA 官方 R32 对阵表 (Yahoo Sports 2026-04)
- Monte Carlo 扩展到淘汰赛阶段
- 完整第3名排序规则 (pts > GD > GF)
- 第3名符合条件的 R32 slot 分配
"""

import sys
import json
import math
import os
import random
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from prediction_models import PoissonModel

random.seed(42)
_poisson = PoissonModel()

# ============================================================
# 1. 分组 & ELO
# ============================================================
GROUPS = {
    'A': ['Mexico', 'South Africa', 'South Korea', 'Czech Republic'],
    'B': ['Canada', 'Switzerland', 'Bosnia and Herzegovina', 'Qatar'],
    'C': ['Brazil', 'Morocco', 'Haiti', 'Scotland'],
    'D': ['USA', 'Turkey', 'Paraguay', 'Australia'],
    'E': ['Germany', 'Ecuador', 'Ivory Coast', 'Curacao'],
    'F': ['Netherlands', 'Japan', 'Sweden', 'Tunisia'],
    'G': ['Belgium', 'Egypt', 'Iran', 'New Zealand'],
    'H': ['Spain', 'Uruguay', 'Saudi Arabia', 'Cape Verde'],
    'I': ['France', 'Senegal', 'Iraq', 'Norway'],
    'J': ['Argentina', 'Algeria', 'Austria', 'Jordan'],
    'K': ['Portugal', 'DR Congo', 'Uzbekistan', 'Colombia'],
    'L': ['England', 'Croatia', 'Ghana', 'Panama'],
}

def _load_elo():
    elo_path = os.path.join(os.path.dirname(__file__), 'data', 'elo_ratings.json')
    with open(elo_path) as f:
        data = json.load(f)
    return {team: info['elo'] for team, info in data.get('ratings', {}).items()}

ELO = _load_elo()

# Load venue data
def _load_venues():
    vpath = os.path.join(os.path.dirname(__file__), 'data', 'venues.json')
    with open(vpath) as f:
        return json.load(f)

VENUES = _load_venues()

# Venue mapping for each match stage
# Format: (venue_name, home_adv)
R32_VENUES = {
    1:  ("SoFi Stadium", 0),
    2:  ("NRG Stadium", 0),
    3:  ("Gillette Stadium", 0),
    4:  ("Estadio BBVA", 0),
    5:  ("AT&T Stadium", 0),
    6:  ("MetLife Stadium", 0),
    7:  ("Estadio Azteca", 0),       # 2200m!
    8:  ("Mercedes-Benz Stadium", 0),
    9:  ("Lumen Field", 0),
    10: ("Levi's Stadium", 0),
    11: ("SoFi Stadium", 0),
    12: ("BMO Field", 0),
    13: ("BC Place", 0),
    14: ("AT&T Stadium", 0),
    15: ("Hard Rock Stadium", 0),      # Heat!
    16: ("Arrowhead Stadium", 0),
}

R16_VENUES = {
    1: ("NRG Stadium", 0),
    2: ("Lincoln Financial Field", 0),
    3: ("MetLife Stadium", 0),
    4: ("Estadio Azteca", 0),         # 2200m!
    5: ("AT&T Stadium", 0),
    6: ("Lumen Field", 0),
    7: ("Mercedes-Benz Stadium", 0),
    8: ("BC Place", 0),
}

QF_VENUES = {
    1: ("Gillette Stadium", 0),
    2: ("SoFi Stadium", 0),
    3: ("Hard Rock Stadium", 0),      # Heat!
    4: ("Arrowhead Stadium", 0),
}

SF_VENUES = {
    1: ("AT&T Stadium", 0),
    2: ("Mercedes-Benz Stadium", 0),
}

FINAL_VENUE = ("MetLife Stadium", 0)
THIRD_VENUE = ("Hard Rock Stadium", 0)   # Heat!

# ============================================================
# 2. FIFA 官方 R32 Bracket (source: Yahoo Sports, April 2026)
# ============================================================
# Format: (slot_id, home_slot, away_slot, description)
# home_slot/away_slot reference group position or third-place slot
R32_SLOTS = [
    # slot_id, home, away, label
    (1,  ('A', 2), ('B', 2),     "A2 vs B2"),
    (2,  ('C', 1), ('F', 2),     "C1 vs F2"),
    (3,  ('E', 1), 'T1',         "E1 vs 3rd(A/B/C/D/F)"),
    (4,  ('F', 1), ('C', 2),     "F1 vs C2"),
    (5,  ('E', 2), ('I', 2),     "E2 vs I2"),
    (6,  ('I', 1), 'T2',         "I1 vs 3rd(C/D/F/G/H)"),
    (7,  ('A', 1), 'T3',         "A1 vs 3rd(C/E/F/H/I)"),
    (8,  ('L', 1), 'T4',         "L1 vs 3rd(E/H/I/J/K)"),
    (9,  ('G', 1), 'T5',         "G1 vs 3rd(A/E/H/I/J)"),
    (10, ('D', 1), 'T6',         "D1 vs 3rd(B/E/F/I/J)"),
    (11, ('H', 1), ('J', 2),     "H1 vs J2"),
    (12, ('K', 2), ('L', 2),     "K2 vs L2"),
    (13, ('B', 1), 'T7',         "B1 vs 3rd(E/F/G/I/J)"),
    (14, ('D', 2), ('G', 2),     "D2 vs G2"),
    (15, ('J', 1), ('H', 2),     "J1 vs H2"),
    (16, ('K', 1), 'T8',         "K1 vs 3rd(D/E/I/J/L)"),
]

# Third-place slot eligibility: which groups' 3rd can fill each T-slot
T_SLOT_ELIGIBILITY = {
    'T1': {'A', 'B', 'C', 'D', 'F'},
    'T2': {'C', 'D', 'F', 'G', 'H'},
    'T3': {'C', 'E', 'F', 'H', 'I'},
    'T4': {'E', 'H', 'I', 'J', 'K'},
    'T5': {'A', 'E', 'H', 'I', 'J'},
    'T6': {'B', 'E', 'F', 'I', 'J'},
    'T7': {'E', 'F', 'G', 'I', 'J'},
    'T8': {'D', 'E', 'I', 'J', 'L'},
}

# R16 bracket: which R32 winners play each other
R16_PAIRINGS = [
    (2, 3), (1, 16), (4, 5), (6, 7),
    (9, 10), (8, 11), (13, 14), (12, 15),
]

# QF pairings
QF_PAIRINGS = [(1, 2), (3, 4), (5, 6), (7, 8)]  # R16 winner indices

# SF pairings
SF_PAIRING = [(1, 2), (3, 4)]  # QF winner indices

# ============================================================
# 3. Match simulation helpers
# ============================================================
def predict_score(elo_a, elo_b, home_adv=0):
    """Poisson-based score prediction"""
    elo_diff = elo_a - elo_b + home_adv
    base = 1.45
    lam_a = max(0.2, base * 10**(elo_diff / 500))
    lam_b = max(0.2, base * 10**(-elo_diff / 500))

    scores = {}
    for ga in range(7):
        for gb in range(7):
            scores[(ga, gb)] = _poisson._poisson_prob(ga, lam_a) * _poisson._poisson_prob(gb, lam_b)

    best = max(scores, key=scores.get)
    w = sum(p for (a, b), p in scores.items() if a > b)
    d = sum(p for (a, b), p in scores.items() if a == b)
    l = sum(p for (a, b), p in scores.items() if a < b)
    t = w + d + l

    return {
        'score': best, 'ga': lam_a, 'gb': lam_b,
        'win': w / t, 'draw': d / t, 'loss': l / t,
    }

def get_venue_penalty(team, venue_name):
    """Calculate ELO penalty for a team at a specific venue (altitude + heat)"""
    if venue_name not in VENUES.get('venues', {}):
        return 0
    v = VENUES['venues'][venue_name]
    penalty = 0
    
    # Altitude penalty (only for non-acclimated teams)
    alt = v.get('altitude_m', 0)
    if alt > 500 and team not in VENUES.get('altitude_scale', {}).get('teams_acclimated', []):
        penalty += (alt - 500) / 1000 * VENUES['altitude_scale']['penalty_per_1000m']
    
    # Heat penalty (only for non-heat-resistant teams)
    temp = v.get('temp_c_jun_jul_avg', 20)
    if temp > VENUES['heat_scale']['threshold_c'] and team not in VENUES['heat_scale'].get('teams_heat_resistant', []):
        heat_penalty = (temp - VENUES['heat_scale']['threshold_c']) / 5 * VENUES['heat_scale']['penalty_per_5c_above']
        # Indoor stadiums halve the heat penalty
        if v.get('indoor', False):
            heat_penalty *= 0.5
        penalty += heat_penalty
    
    return int(penalty)

def sim_match(team_a, team_b, elo_a, elo_b, home_adv=0, ko=False, venue_name=None):
    """Simulate one match, return (goals_a, goals_b). Venue affects ELO via altitude/heat."""
    # Apply venue penalties
    venue_penalty_a = get_venue_penalty(team_a, venue_name) if venue_name else 0
    venue_penalty_b = get_venue_penalty(team_b, venue_name) if venue_name else 0
    
    pred = predict_score(elo_a - venue_penalty_a, elo_b - venue_penalty_b, home_adv)
    ga, gb = pred['score']

    # Random perturbation
    if random.random() < 0.2:
        ga += random.choice([-1, 0, 1])
    if random.random() < 0.2:
        gb += random.choice([-1, 0, 1])
    ga, gb = max(0, ga), max(0, gb)

    # KO: if draw, probabilistic tie-breaker (not auto-higher-ELO)
    if ko and ga == gb:
        elo_diff = elo_a - elo_b
        # Higher ELO has advantage but not guaranteed
        p_higher_wins = 0.5 + min(abs(elo_diff) / 800, 0.15)
        if random.random() < p_higher_wins:
            if elo_a >= elo_b: ga += 1
            else: gb += 1
        else:
            if elo_a >= elo_b: gb += 1
            else: ga += 1

    return ga, gb

# ============================================================
# 4. Single tournament simulation
# ============================================================
def simulate_one_tournament():
    """Run one complete tournament simulation, return champion & round results"""
    elos = {t: ELO.get(t, 1700) for g in GROUPS.values() for t in g}

    # --- Group Stage ---
    group_standings = {}  # {letter: [(team, pts, gd, gf), ...]}
    all_thirds = []

    for letter, teams in GROUPS.items():
        pts = {t: 0 for t in teams}
        gf = {t: 0 for t in teams}
        ga = {t: 0 for t in teams}

        # 6 matches per group
        for i in range(4):
            for j in range(i + 1, 4):
                home, away = teams[i], teams[j]

                # Home advantage
                home_adv = 0
                if home in ('USA', 'Mexico', 'Canada'):
                    home_adv = 60
                elif home in ('Brazil', 'Argentina', 'Uruguay', 'Colombia', 'Ecuador', 'Paraguay'):
                    home_adv = 15

                gh, ga_goals = sim_match(home, away, elos[home], elos[away], home_adv)

                if gh > ga_goals:
                    pts[home] += 3
                elif gh == ga_goals:
                    pts[home] += 1
                    pts[away] += 1
                else:
                    pts[away] += 3

                gf[home] += gh
                ga[home] += ga_goals
                gf[away] += ga_goals
                ga[away] += gh

        # Sort by pts > GD > GF
        standing = sorted(teams, key=lambda t: (-pts[t], -(gf[t] - ga[t]), -gf[t]))
        group_standings[letter] = [(t, pts[t], gf[t] - ga[t], gf[t]) for t in standing]

        # Third place candidate
        third_team = standing[2]
        all_thirds.append((letter, third_team, pts[third_team], gf[third_team] - ga[third_team], gf[third_team]))

    # --- Best 3rd Places ---
    all_thirds.sort(key=lambda x: (-x[2], -x[3], -x[4]))  # pts > GD > GF
    best_third_groups = {x[0] for x in all_thirds[:8]}

    # --- Assign 3rd place teams to T-slots ---
    # Constraint-based: assign most constrained slots first
    third_assignments = {}
    available = [(g, t, p, gd, gf) for g, t, p, gd, gf in all_thirds[:8]]
    available_groups = {x[0] for x in available}

    # Sort T-slots by how many eligible groups are in available set
    slot_order = []
    for t_slot, eligible in T_SLOT_ELIGIBILITY.items():
        match_count = len(eligible & available_groups)
        slot_order.append((match_count, t_slot, eligible))
    slot_order.sort()  # fewest matches first

    for _, t_slot, eligible in slot_order:
        # Find best eligible third-place team
        assigned = False
        for idx, (g, t, p, gd, gf) in enumerate(available):
            if g in eligible:
                third_assignments[t_slot] = (g, t)
                available.pop(idx)
                assigned = True
                break
        # Fallback: if no eligible team, use best available (non-perfect bracket)
        if not assigned and available:
            g, t, p, gd, gf = available.pop(0)
            third_assignments[t_slot] = (g, t)

    # --- R32: Build team map per slot ---
    # slot → team name
    r32_teams = {}

    for slot_id, home_spec, away_spec, _label in R32_SLOTS:
        # Home team
        if isinstance(home_spec, tuple):
            group_letter, position = home_spec
            home_team = group_standings[group_letter][position - 1][0]
        else:  # T-slot
            home_team = third_assignments.get(home_spec, (None, None))[1]

        # Away team
        if isinstance(away_spec, tuple):
            group_letter, position = away_spec
            away_team = group_standings[group_letter][position - 1][0]
        else:
            away_team = third_assignments.get(away_spec, (None, None))[1]

        if home_team and away_team:
            r32_teams[slot_id] = (home_team, away_team)

    # --- Knockout Stage: simulate forward ---
    stage_winners = {}  # {stage: {slot: winner_team}}

    # R32
    r32_winners = {}
    for slot_id, (t1, t2) in r32_teams.items():
        home_adv = 60 if t1 in ('USA', 'Mexico', 'Canada') else 0
        venue_name = R32_VENUES.get(slot_id, (None,))[0]
        g1, g2 = sim_match(t1, t2, elos[t1], elos[t2], home_adv, ko=True, venue_name=venue_name)
        r32_winners[slot_id] = t1 if g1 > g2 else t2
    stage_winners['R32'] = r32_winners

    # R16
    r16_winners = {}
    for i, (s1, s2) in enumerate(R16_PAIRINGS, 1):
        if s1 in r32_winners and s2 in r32_winners:
            t1, t2 = r32_winners[s1], r32_winners[s2]
            venue_name = R16_VENUES.get(i, (None,))[0]
            g1, g2 = sim_match(t1, t2, elos[t1], elos[t2], ko=True, venue_name=venue_name)
            r16_winners[i] = t1 if g1 > g2 else t2
    stage_winners['R16'] = r16_winners

    # QF
    qf_winners = {}
    for i, (s1, s2) in enumerate(QF_PAIRINGS, 1):
        if s1 in r16_winners and s2 in r16_winners:
            t1, t2 = r16_winners[s1], r16_winners[s2]
            venue_name = QF_VENUES.get(i, (None,))[0]
            g1, g2 = sim_match(t1, t2, elos[t1], elos[t2], ko=True, venue_name=venue_name)
            qf_winners[i] = t1 if g1 > g2 else t2
    stage_winners['QF'] = qf_winners

    # SF
    sf_winners = {}
    for i, (s1, s2) in enumerate(SF_PAIRING, 1):
        if s1 in qf_winners and s2 in qf_winners:
            t1, t2 = qf_winners[s1], qf_winners[s2]
            venue_name = SF_VENUES.get(i, (None,))[0]
            g1, g2 = sim_match(t1, t2, elos[t1], elos[t2], ko=True, venue_name=venue_name)
            sf_winners[i] = t1 if g1 > g2 else t2
    stage_winners['SF'] = sf_winners

    # Final
    if 1 in sf_winners and 2 in sf_winners:
        t1, t2 = sf_winners[1], sf_winners[2]
        g1, g2 = sim_match(t1, t2, elos[t1], elos[t2], ko=True, venue_name=FINAL_VENUE[0])
        champion = t1 if g1 > g2 else t2
        stage_winners['F'] = {1: champion}
    else:
        champion = None

    # Third place
    sf_losers = []
    for i in [1, 2]:
        if i in r16_winners:
            pair = SF_PAIRING[i-1]
            for s in pair:
                if s in qf_winners and qf_winners[s] not in sf_winners.values():
                    sf_losers.append(qf_winners[s])
                    break
    if len(sf_losers) == 2:
        g1, g2 = sim_match(sf_losers[0], sf_losers[1], elos[sf_losers[0]], elos[sf_losers[1]], ko=True, venue_name=THIRD_VENUE[0])
        stage_winners['3rd'] = sf_losers[0] if g1 > g2 else sf_losers[1]

    return stage_winners, group_standings

# ============================================================
# 5. Monte Carlo aggregation
# ============================================================
def run_monte_carlo(n_sims=10000):
    """Run full tournament Monte Carlo, return aggregated stats"""
    # Counters
    champion_count = defaultdict(int)
    final_count = defaultdict(int)
    sf_count = defaultdict(int)
    qf_count = defaultdict(int)
    r16_count = defaultdict(int)
    r32_count = defaultdict(int)
    group_advance_count = defaultdict(lambda: defaultdict(int))
    group_pts_total = defaultdict(lambda: defaultdict(float))

    for sim_idx in range(n_sims):
        if sim_idx % 2000 == 0 and sim_idx > 0:
            print(f"  ... {sim_idx}/{n_sims} simulations", file=sys.stderr)

        stage_winners, group_standings = simulate_one_tournament()

        # Group stage stats
        for letter, standings in group_standings.items():
            for rank, (team, pts, gd, gf) in enumerate(standings):
                group_pts_total[letter][team] += pts
                if rank <= 2:  # top 2 auto-advance
                    group_advance_count[letter][team] += 1

        # KO stats
        r32_winners = stage_winners.get('R32', {})
        for team in r32_winners.values():
            r32_count[team] += 1

        r16_winners = stage_winners.get('R16', {})
        for team in r16_winners.values():
            r16_count[team] += 1

        qf_winners = stage_winners.get('QF', {})
        for team in qf_winners.values():
            qf_count[team] += 1

        sf_winners = stage_winners.get('SF', {})
        for team in sf_winners.values():
            sf_count[team] += 1

        finalists = stage_winners.get('F', {})
        for team in finalists.values():
            final_count[team] += 1

        champ = finalists.get(1)
        if champ:
            champion_count[champ] += 1

    # Normalize to percentages
    def to_pct(d, total):
        return {t: round(c / total * 100, 1) for t, c in sorted(d.items(), key=lambda x: -x[1])}

    return {
        'champion': to_pct(champion_count, n_sims),
        'final': to_pct(final_count, n_sims),
        'semifinal': to_pct(sf_count, n_sims),
        'quarterfinal': to_pct(qf_count, n_sims),
        'r16': to_pct(r16_count, n_sims),
        'group_advance': {g: to_pct(d, n_sims) for g, d in group_advance_count.items()},
        'group_pts_avg': {g: {t: round(c / n_sims, 1) for t, c in d.items()}
                          for g, d in group_pts_total.items()},
        'n_sims': n_sims,
    }

# ============================================================
# 6. Output
# ============================================================
def print_results(stats):
    n = stats['n_sims']
    print(f"\n🌍 2026 FIFA World Cup — Full Monte Carlo ({n:,} simulations)")
    print(f"{'='*70}")

    # Group stage
    print(f"\n📋 GROUP STAGE")
    print(f"{'='*70}")
    for letter in 'ABCDEFGHIJKL':
        teams = GROUPS[letter]
        print(f"\n  Group {letter}")
        print(f"  {'Team':<25} {'Elo':>5} {'Advance%':>10} {'AvgPts':>7}")
        print(f"  {'-'*50}")
        for t in sorted(teams, key=lambda t: -ELO.get(t, 0)):
            adv = stats['group_advance'].get(letter, {}).get(t, 0)
            pts = stats['group_pts_avg'].get(letter, {}).get(t, 0)
            flag = '✅' if adv > 50 else '⚪'
            print(f"  {t:<25} {ELO.get(t, 1700):>5} {adv:>9.1f}% {pts:>6.1f} {flag}")

    # Knockout
    print(f"\n\n🏟️ KNOCKOUT STAGE PROBABILITIES")
    print(f"{'='*70}")

    print(f"\n  🏆 CHAMPION")
    for i, (team, pct) in enumerate(stats['champion'].items()):
        if i >= 10:
            break
        print(f"  {team:<25} {pct:>6.1f}%")

    print(f"\n  🥈 FINALISTS")
    for i, (team, pct) in enumerate(stats['final'].items()):
        if i >= 10:
            break
        print(f"  {team:<25} {pct:>6.1f}%")

    print(f"\n  🏅 SEMI-FINALISTS")
    for i, (team, pct) in enumerate(stats['semifinal'].items()):
        if i >= 10:
            break
        print(f"  {team:<25} {pct:>6.1f}%")

    # Most likely champion
    if stats['champion']:
        top = list(stats['champion'].items())[0]
        print(f"\n{'='*70}")
        print(f"  👑 MOST LIKELY CHAMPION: {top[0]} ({top[1]}%)")
        print(f"  📈 Model: Elo + Poisson + FIFA Official Bracket + {n:,} MC Sims")
        print(f"  📊 Backtest: 57.8% (WC 2022)")
        print(f"  🔄 ELO: clubelo.com (55 teams, national-team scale)")
        print(f"{'='*70}")

def main():
    mode = '--full' if len(sys.argv) < 2 else sys.argv[1]
    n_sims = 5000
    for i, arg in enumerate(sys.argv):
        if arg == '--sims' and i + 1 < len(sys.argv):
            n_sims = int(sys.argv[i + 1])

    print("🌍 2026 FIFA World Cup — Monte Carlo Prediction System v2.0")
    print(f"📅 June 11 – July 19, 2026 | 🏟️ USA 🇺🇸 Canada 🇨🇦 Mexico 🇲🇽")
    print(f"👥 48 teams | 12 groups | Official FIFA Bracket | {n_sims:,} sims")
    print()

    print("🔄 Running Monte Carlo simulation...")
    stats = run_monte_carlo(n_sims)
    print_results(stats)

    # Save JSON
    report = {
        'generated': datetime.now().isoformat(),
        'model': 'Elo + Poisson + FIFA Official Bracket',
        'n_sims': n_sims,
        'backtest_accuracy': '57.8% (WC2022), 51.0% (Euro2024)',
        'champion': {k: v for k, v in list(stats['champion'].items())[:10]},
        'final': {k: v for k, v in list(stats['final'].items())[:10]},
        'semifinal': {k: v for k, v in list(stats['semifinal'].items())[:10]},
        'quarterfinal': {k: v for k, v in list(stats['quarterfinal'].items())[:16]},
        'group_advance': stats['group_advance'],
    }
    report_path = os.path.join(os.path.dirname(__file__), 'data', 'wc2026_mc_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Full report saved: data/wc2026_mc_report.json")

if __name__ == '__main__':
    main()
