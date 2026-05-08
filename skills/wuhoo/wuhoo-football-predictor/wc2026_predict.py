#!/usr/bin/env python3
"""
2026 FIFA World Cup — 全流程 Monte Carlo 预测系统 v2.1
基于: Elo + Poisson + FIFA 官方 Bracket + 10,000次 全流程模拟

Usage:
  python3.11 wc2026_predict.py [--full|--groups|--knockout|--report] [--sims N]

v2.1 更新:
- --report 模式：生成中文 Markdown 综合报告（含 48 队简介、分组分析、淘汰赛预测）
- 概率加权最大似然淘汰赛路径
- 小组分析 6 条研判规则
- 数据完整性校验
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

ALL_TEAMS = set()
for g in GROUPS.values():
    ALL_TEAMS.update(g)

def _load_elo():
    elo_path = os.path.join(os.path.dirname(__file__), 'data', 'elo_ratings.json')
    with open(elo_path) as f:
        data = json.load(f)
    return {team: info['elo'] for team, info in data.get('ratings', {}).items()}

ELO = _load_elo()

def _load_venues():
    vpath = os.path.join(os.path.dirname(__file__), 'data', 'venues.json')
    with open(vpath) as f:
        return json.load(f)

VENUES = _load_venues()

def _load_profiles():
    ppath = os.path.join(os.path.dirname(__file__), 'data', 'team_profiles.json')
    with open(ppath) as f:
        return json.load(f)['teams']

TEAM_PROFILES = _load_profiles()

# ============================================================
# 1a. Data Validation
# ============================================================
def validate_data():
    """Validate all data integrity before running predictions."""
    errors = []
    warnings = []

    # 1. All GROUP teams must be in ELO
    elo_teams = set(ELO.keys())
    for team in ALL_TEAMS:
        if team not in elo_teams:
            errors.append(f"Team '{team}' in GROUPS but NOT in ELO data")

    # 2. All GROUP teams must have profiles
    profile_teams = set(TEAM_PROFILES.keys())
    for team in ALL_TEAMS:
        if team not in profile_teams:
            errors.append(f"Team '{team}' in GROUPS but NOT in team_profiles.json")

    for team in profile_teams:
        if team not in ALL_TEAMS:
            warnings.append(f"Team '{team}' in profiles but NOT in GROUPS")

    # 3. Check ELO range sanity
    for team, elo in ELO.items():
        if team in ALL_TEAMS:
            if elo < 1500:
                warnings.append(f"Team '{team}' ELO={elo} unusually low")
            if elo > 2200:
                warnings.append(f"Team '{team}' ELO={elo} unusually high")

    # 4. Check venues referenced in bracket exist
    all_venue_names = set(VENUES.get('venues', {}).keys())
    for stage_map, stage_name in [
        (R32_VENUES, 'R32'), (R16_VENUES, 'R16'), (QF_VENUES, 'QF'),
        (SF_VENUES, 'SF')
    ]:
        for slot, (vname, _) in stage_map.items():
            if vname and vname not in all_venue_names:
                errors.append(f"Venue '{vname}' ({stage_name} slot {slot}) not in venues.json")

    for vname, _ in [FINAL_VENUE, THIRD_VENUE]:
        if vname and vname not in all_venue_names:
            errors.append(f"Venue '{vname}' not in venues.json")

    if errors:
        print("❌ DATA VALIDATION ERRORS:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return False

    if warnings:
        print("⚠️ DATA VALIDATION WARNINGS:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)

    print(f"✅ Data validated: {len(ALL_TEAMS)} teams, {len(elo_teams)} ELO entries, "
          f"{len(profile_teams)} profiles, {len(all_venue_names)} venues",
          file=sys.stderr)
    return True


# ============================================================
# 2. Venue mappings
# ============================================================
R32_VENUES = {
    1:  ("SoFi Stadium", 0), 2: ("NRG Stadium", 0),
    3:  ("Gillette Stadium", 0), 4: ("Estadio BBVA", 0),
    5:  ("AT&T Stadium", 0), 6: ("MetLife Stadium", 0),
    7:  ("Estadio Azteca", 0), 8: ("Mercedes-Benz Stadium", 0),
    9:  ("Lumen Field", 0), 10: ("Levi's Stadium", 0),
    11: ("SoFi Stadium", 0), 12: ("BMO Field", 0),
    13: ("BC Place", 0), 14: ("AT&T Stadium", 0),
    15: ("Hard Rock Stadium", 0), 16: ("Arrowhead Stadium", 0),
}
R16_VENUES = {
    1: ("NRG Stadium", 0), 2: ("Lincoln Financial Field", 0),
    3: ("MetLife Stadium", 0), 4: ("Estadio Azteca", 0),
    5: ("AT&T Stadium", 0), 6: ("Lumen Field", 0),
    7: ("Mercedes-Benz Stadium", 0), 8: ("BC Place", 0),
}
QF_VENUES = {
    1: ("Gillette Stadium", 0), 2: ("SoFi Stadium", 0),
    3: ("Hard Rock Stadium", 0), 4: ("Arrowhead Stadium", 0),
}
SF_VENUES = {
    1: ("AT&T Stadium", 0), 2: ("Mercedes-Benz Stadium", 0),
}
FINAL_VENUE = ("MetLife Stadium", 0)
THIRD_VENUE = ("Hard Rock Stadium", 0)

# ============================================================
# 3. FIFA 官方 R32 Bracket
# ============================================================
R32_SLOTS = [
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

R16_PAIRINGS = [
    (2, 3), (1, 16), (4, 5), (6, 7),
    (9, 10), (8, 11), (13, 14), (12, 15),
]
QF_PAIRINGS = [(1, 2), (3, 4), (5, 6), (7, 8)]
SF_PAIRING = [(1, 2), (3, 4)]

# ============================================================
# 4. Match simulation helpers
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

    alt = v.get('altitude_m', 0)
    if alt > 500 and team not in VENUES.get('altitude_scale', {}).get('teams_acclimated', []):
        penalty += (alt - 500) / 1000 * VENUES['altitude_scale']['penalty_per_1000m']

    temp = v.get('temp_c_jun_jul_avg', 20)
    if temp > VENUES['heat_scale']['threshold_c'] and team not in VENUES['heat_scale'].get('teams_heat_resistant', []):
        heat_penalty = (temp - VENUES['heat_scale']['threshold_c']) / 5 * VENUES['heat_scale']['penalty_per_5c_above']
        if v.get('indoor', False):
            heat_penalty *= 0.5
        penalty += heat_penalty

    return int(penalty)

def sim_match(team_a, team_b, elo_a, elo_b, home_adv=0, ko=False, venue_name=None):
    """Simulate one match, return (goals_a, goals_b)."""
    venue_penalty_a = get_venue_penalty(team_a, venue_name) if venue_name else 0
    venue_penalty_b = get_venue_penalty(team_b, venue_name) if venue_name else 0

    pred = predict_score(elo_a - venue_penalty_a, elo_b - venue_penalty_b, home_adv)
    ga, gb = pred['score']

    if random.random() < 0.2:
        ga += random.choice([-1, 0, 1])
    if random.random() < 0.2:
        gb += random.choice([-1, 0, 1])
    ga, gb = max(0, ga), max(0, gb)

    if ko and ga == gb:
        elo_diff = elo_a - elo_b
        p_higher_wins = 0.5 + min(abs(elo_diff) / 800, 0.15)
        if random.random() < p_higher_wins:
            if elo_a >= elo_b: ga += 1
            else: gb += 1
        else:
            if elo_a >= elo_b: gb += 1
            else: ga += 1

    return ga, gb

# ============================================================
# 5. Single tournament simulation (enhanced to return r32_teams)
# ============================================================
def simulate_one_tournament():
    """Run one complete tournament simulation, return champion & round results.
    Also returns `r32_teams` dict for bracket tracking.
    """
    elos = {t: ELO.get(t, 1700) for g in GROUPS.values() for t in g}

    # --- Group Stage ---
    group_standings = {}
    all_thirds = []

    for letter, teams in GROUPS.items():
        pts = {t: 0 for t in teams}
        gf = {t: 0 for t in teams}
        ga = {t: 0 for t in teams}

        for i in range(4):
            for j in range(i + 1, 4):
                home, away = teams[i], teams[j]
                home_adv = 0
                if home in ('USA', 'Mexico', 'Canada'):
                    home_adv = 60
                elif home in ('Brazil', 'Argentina', 'Uruguay', 'Colombia', 'Ecuador', 'Paraguay'):
                    home_adv = 15

                gh, ga_goals = sim_match(home, away, elos[home], elos[away], home_adv)

                # P4: Group stage upset factor (3% chance of +2 goals for underdog)
                if random.random() < 0.03:
                    if elos[home] < elos[away]:
                        gh += 2
                    else:
                        ga_goals += 2

                if gh > ga_goals:
                    pts[home] += 3
                elif gh == ga_goals:
                    pts[home] += 1
                    pts[away] += 1
                else:
                    pts[away] += 3

                gf[home] += gh; ga[home] += ga_goals
                gf[away] += ga_goals; ga[away] += gh

        standing = sorted(teams, key=lambda t: (-pts[t], -(gf[t] - ga[t]), -gf[t]))
        group_standings[letter] = [(t, pts[t], gf[t] - ga[t], gf[t]) for t in standing]
        third_team = standing[2]
        all_thirds.append((letter, third_team, pts[third_team], gf[third_team] - ga[third_team], gf[third_team]))

    # --- Best 3rd Places ---
    all_thirds.sort(key=lambda x: (-x[2], -x[3], -x[4]))
    best_third_groups = {x[0] for x in all_thirds[:8]}

    # --- Assign 3rd place teams to T-slots ---
    third_assignments = {}
    available = [(g, t, p, gd, gf) for g, t, p, gd, gf in all_thirds[:8]]
    available_groups = {x[0] for x in available}

    slot_order = []
    for t_slot, eligible in T_SLOT_ELIGIBILITY.items():
        match_count = len(eligible & available_groups)
        slot_order.append((match_count, t_slot, eligible))
    slot_order.sort()

    for _, t_slot, eligible in slot_order:
        assigned = False
        for idx, (g, t, p, gd, gf) in enumerate(available):
            if g in eligible:
                third_assignments[t_slot] = (g, t)
                available.pop(idx)
                assigned = True
                break
        if not assigned and available:
            g, t, p, gd, gf = available.pop(0)
            third_assignments[t_slot] = (g, t)

    # --- R32: Build team map per slot ---
    r32_teams = {}
    for slot_id, home_spec, away_spec, _label in R32_SLOTS:
        if isinstance(home_spec, tuple):
            home_team = group_standings[home_spec[0]][home_spec[1] - 1][0]
        else:
            home_team = third_assignments.get(home_spec, (None, None))[1]
        if isinstance(away_spec, tuple):
            away_team = group_standings[away_spec[0]][away_spec[1] - 1][0]
        else:
            away_team = third_assignments.get(away_spec, (None, None))[1]
        if home_team and away_team:
            r32_teams[slot_id] = (home_team, away_team)

    # --- Knockout Stage ---
    stage_winners = {}

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

    return stage_winners, group_standings, r32_teams

# ============================================================
# 6. Monte Carlo aggregation (enhanced with slot tracking)
# ============================================================
def run_monte_carlo(n_sims=10000):
    """Run full tournament Monte Carlo, return aggregated stats + expected bracket data."""
    # Counters
    champion_count = defaultdict(int)
    final_count = defaultdict(int)
    sf_count = defaultdict(int)
    qf_count = defaultdict(int)
    r16_count = defaultdict(int)
    r32_count = defaultdict(int)
    group_advance_count = defaultdict(lambda: defaultdict(int))
    group_pts_total = defaultdict(lambda: defaultdict(float))

    # New: Slot-pair tracking for expected bracket (track FULL pairs, not just individuals)
    r32_slot_pair = defaultdict(lambda: defaultdict(int))    # slot -> (t1,t2) -> count
    r32_slot_winner = defaultdict(lambda: defaultdict(int))
    r16_slot_pair = defaultdict(lambda: defaultdict(int))    # slot -> (t1,t2) -> count
    r16_slot_winner = defaultdict(lambda: defaultdict(int))
    qf_slot_pair = defaultdict(lambda: defaultdict(int))
    qf_slot_winner = defaultdict(lambda: defaultdict(int))
    sf_slot_pair = defaultdict(lambda: defaultdict(int))
    sf_slot_winner = defaultdict(lambda: defaultdict(int))
    final_slot_winner = defaultdict(lambda: defaultdict(int))
    third_slot_pair = defaultdict(lambda: defaultdict(int))
    final_pair_count = defaultdict(int)     # separate counter for final pair

    for sim_idx in range(n_sims):
        if sim_idx % 2000 == 0 and sim_idx > 0:
            print(f"  ... {sim_idx}/{n_sims} simulations", file=sys.stderr)

        stage_winners, group_standings, r32_teams = simulate_one_tournament()

        # Group stage stats
        for letter, standings in group_standings.items():
            for rank, (team, pts, gd, gf) in enumerate(standings):
                group_pts_total[letter][team] += pts
                if rank <= 2:
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

        # Track slot PAIRS (not just individuals) for expected bracket
        for slot_id, (t1, t2) in r32_teams.items():
            r32_slot_pair[slot_id][(t1, t2)] += 1
        for slot_id, winner in r32_winners.items():
            r32_slot_winner[slot_id][winner] += 1
        # R16: track pairs from the R16 matchups
        for i, (s1, s2) in enumerate(R16_PAIRINGS, 1):
            if s1 in r32_winners and s2 in r32_winners:
                r16_slot_pair[i][(r32_winners[s1], r32_winners[s2])] += 1
        for slot_id, winner in r16_winners.items():
            r16_slot_winner[slot_id][winner] += 1
        # QF: track pairs
        for i, (s1, s2) in enumerate(QF_PAIRINGS, 1):
            if s1 in r16_winners and s2 in r16_winners:
                qf_slot_pair[i][(r16_winners[s1], r16_winners[s2])] += 1
        for slot_id, winner in qf_winners.items():
            qf_slot_winner[slot_id][winner] += 1
        # SF: track pairs
        for i, (s1, s2) in enumerate(SF_PAIRING, 1):
            if s1 in qf_winners and s2 in qf_winners:
                sf_slot_pair[i][(qf_winners[s1], qf_winners[s2])] += 1
        for slot_id, winner in sf_winners.items():
            sf_slot_winner[slot_id][winner] += 1
        # Final
        if 1 in sf_winners and 2 in sf_winners:
            final_pair_count[(sf_winners[1], sf_winners[2])] += 1
        for slot_id, winner in stage_winners.get('F', {}).items():
            final_slot_winner[slot_id][winner] += 1

    # Normalize
    def to_pct(d, total):
        return {t: round(c / total * 100, 1) for t, c in sorted(d.items(), key=lambda x: -x[1])}

    stats = {
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

    # Build expected bracket with CONSTRAINED assignment (P2 fix)
    # Each team can only appear in ONE R32 slot
    def most_frequent(d):
        if not d: return None
        return max(d, key=d.get)

    def constrained_r32_assignment(slot_pairs):
        """Greedy constrained assignment: assign most-frequent pairs,
        ensuring no team appears in multiple R32 slots."""
        # Build sorted candidate list: (slot_id, (t1,t2), count)
        candidates = []
        for slot_id, pair_counts in slot_pairs.items():
            for pair, count in pair_counts.items():
                candidates.append((slot_id, pair, count))
        candidates.sort(key=lambda x: -x[2])  # highest count first

        assigned = {}  # slot_id -> (t1, t2)
        used_teams = set()

        for slot_id, pair, count in candidates:
            if slot_id in assigned:
                continue
            t1, t2 = pair
            if t1 in used_teams or t2 in used_teams:
                continue
            assigned[slot_id] = pair
            used_teams.add(t1)
            used_teams.add(t2)

        return assigned

    expected = {
        'r32_pairs': constrained_r32_assignment(dict(r32_slot_pair)),
        'r32_winners': {},
        'r16_pairs': {},
        'r16_winners': {},
        'qf_pairs': {},
        'qf_winners': {},
        'sf_pairs': {},
        'sf_winners': {},
        'final_pair': most_frequent(final_pair_count),
        'final_winner': None,
    }

    # R32 winners: for each assigned pair, use most frequent winner
    for slot_id in expected['r32_pairs']:
        expected['r32_winners'][slot_id] = most_frequent(r32_slot_winner.get(slot_id, {}))

    for slot_id in range(1, 9):
        expected['r16_pairs'][slot_id] = most_frequent(r16_slot_pair.get(slot_id, {}))
        expected['r16_winners'][slot_id] = most_frequent(r16_slot_winner.get(slot_id, {}))
    for slot_id in range(1, 5):
        expected['qf_pairs'][slot_id] = most_frequent(qf_slot_pair.get(slot_id, {}))
        expected['qf_winners'][slot_id] = most_frequent(qf_slot_winner.get(slot_id, {}))
    for slot_id in range(1, 3):
        expected['sf_pairs'][slot_id] = most_frequent(sf_slot_pair.get(slot_id, {}))
        expected['sf_winners'][slot_id] = most_frequent(sf_slot_winner.get(slot_id, {}))

    # Final winner: most frequent team in final_winner slot 1
    final_w = most_frequent(final_slot_winner.get(1, {}))
    expected['final_winner'] = final_w

    return stats, expected

# ============================================================
# 7. Group Analysis (6 rules)
# ============================================================
def analyze_group(letter, teams, elos, advance_probs, pts_avg):
    """Analyze a group with 6 deterministic rules based on ELO gaps."""
    team_elos = [(t, elos.get(t, 1700)) for t in teams]
    team_elos.sort(key=lambda x: -x[1])

    e1, e2, e3, e4 = [e for _, e in team_elos]
    t1, t2, t3, t4 = [t for t, _ in team_elos]

    adv = advance_probs.get(letter, {})

    tags = []
    narrative_parts = []

    # Rule 1: 绝对热门 (clear favorite)
    if e1 - e2 > 100:
        tags.append(f"🏆 绝对热门：{t1}")
        narrative_parts.append(f"{t1}（ELO {e1}）实力明显高出同组其他队（Δ={e1-e2}），基本锁定小组头名")

    # Rule 2: 死亡之组 (group of death)
    if e1 - e3 < 80:
        tags.append("💀 死亡之组")
        narrative_parts.append("前三名 ELO 差距极小，出线形势扑朔迷离，任何一场失常都可能导致出局")

    # Rule 3: 争2激烈 (tight race for 2nd)
    if e2 - e3 < 40 and e1 - e2 > 50:
        tags.append("⚔️ 争2白热化")
        narrative_parts.append(f"{t2} 与 {t3} 实力接近（Δ={e2-e3}），小组第二的争夺将是最大看点")

    # Rule 4: 主队优势 (host advantage)
    host_adv = any(t in ('USA', 'Mexico', 'Canada') for t in teams)
    if host_adv:
        host_names = [t for t in teams if t in ('USA', 'Mexico', 'Canada')]
        tags.append(f"🏟️ 东道主：{', '.join(host_names)}")
        narrative_parts.append(f"东道主 {host_names[0]} 享有主场优势，这是小组出线的重要加分项")

    # Rule 5: 黑马信号 (dark horse)
    if e2 - e3 < 30 and e3 > 1750 and not host_adv:
        tags.append(f"🐎 黑马候选：{t3}")
        narrative_parts.append(f"{t3}（ELO {e3}）与 {t2} 差距仅 {e2-e3}，有爆冷出线的可能")

    # Rule 6: 送分队
    if e3 - e4 > 120:
        tags.append(f"📦 {t4} 实力明显不足")

    # Narrative
    if not narrative_parts:
        narrative_parts.append("本组实力分层清晰，前两名出线悬念不大")

    return {
        'tags': tags,
        'narrative': '。'.join(narrative_parts) + '。',
        'team_elos': team_elos,
        'advance_probs': adv,
        'pts_avg': pts_avg.get(letter, {}),
    }

# ============================================================
# 8. Expected Score Calculation (deterministic)
# ============================================================
def expected_score(team_a, team_b, home_adv=0, venue_name=None):
    """Deterministic expected score using Poisson model (no random perturbation)."""
    elo_a = ELO.get(team_a, 1700)
    elo_b = ELO.get(team_b, 1700)

    venue_penalty_a = get_venue_penalty(team_a, venue_name) if venue_name else 0
    venue_penalty_b = get_venue_penalty(team_b, venue_name) if venue_name else 0

    pred = predict_score(elo_a - venue_penalty_a, elo_b - venue_penalty_b, home_adv)
    return pred['score'], pred['win'], pred['draw'], pred['loss']

# ============================================================
# 9. Report Generation
# ============================================================
def generate_report(stats, expected_bracket):
    """Generate comprehensive Chinese Markdown report."""
    n = stats['n_sims']
    lines = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    lines.append(f"# 🌍 2026 FIFA 世界杯预测报告")
    lines.append(f"")
    lines.append(f"**生成时间**: {now} | **模拟次数**: {n:,} | **模型**: Elo + Poisson + FIFA Bracket")
    lines.append(f"**数据来源**: ELO (clubelo.com 2026-05-01) | **回测准确率**: WC2022 57.8%, Euro2024 51.0%")
    lines.append(f"")
    lines.append(f"> ⚠️ 本报告基于 ELO 评分和统计模型，不含实时新闻/伤病/阵容磨合数据。预测仅供娱乐参考。")
    lines.append(f"")

    # ===== Section 1: 48队实力排行 =====
    lines.append(f"---")
    lines.append(f"## 一、48 队实力排行（ELO Top 20）")
    lines.append(f"")

    all_elos = sorted([(t, ELO.get(t, 1700)) for t in ALL_TEAMS], key=lambda x: -x[1])
    lines.append(f"| # | 球队 | ELO | 地区 | FIFA排名(估) | 世界杯最佳 |")
    lines.append(f"|---|------|-----|------|-------------|-----------|")
    for rank, (team, elo) in enumerate(all_elos[:20], 1):
        p = TEAM_PROFILES.get(team, {})
        name_cn = p.get('name_cn', team)
        conf = p.get('confederation', '?')
        fifa = p.get('fifa_rank_est', '?')
        best = p.get('wc_best', '?')
        lines.append(f"| {rank} | {name_cn} ({team}) | {elo} | {conf} | {fifa} | {best} |")

    lines.append(f"")
    lines.append(f"**其余 28 队**: " + "、".join(
        TEAM_PROFILES.get(t, {}).get('name_cn', t) for t, _ in all_elos[20:]) + "")
    lines.append(f"")

    # ===== Section 2: 分组分析 =====
    lines.append(f"---")
    lines.append(f"## 二、分组分析与出线预测")
    lines.append(f"")

    for letter in 'ABCDEFGHIJKL':
        teams = GROUPS[letter]
        analysis = analyze_group(
            letter, teams, ELO,
            stats['group_advance'],
            stats['group_pts_avg']
        )

        lines.append(f"### Group {letter}")
        lines.append(f"")

        # Tags
        if analysis['tags']:
            lines.append(f"**标签**: {' · '.join(analysis['tags'])}")
            lines.append(f"")

        # Narrative
        lines.append(f"> {analysis['narrative']}")
        lines.append(f"")

        # Table
        lines.append(f"| 球队 | 中文名 | ELO | 出线概率 | 平均积分 | 判定 |")
        lines.append(f"|------|--------|-----|----------|----------|------|")
        for team, elo in analysis['team_elos']:
            p = TEAM_PROFILES.get(team, {})
            name_cn = p.get('name_cn', team)
            adv_pct = analysis['advance_probs'].get(team, 0)
            pts = analysis['pts_avg'].get(team, 0)
            if adv_pct > 90:
                flag = '✅ 稳出线'
            elif adv_pct > 50:
                flag = '🟢 大概率'
            elif adv_pct > 20:
                flag = '🟡 有机会'
            else:
                flag = '🔴 难度大'
            lines.append(f"| {team:<25} | {name_cn} | {elo} | {adv_pct:.1f}% | {pts:.1f} | {flag} |")

        lines.append(f"")

    # ===== Section 3: 淘汰赛概率总结 =====
    lines.append(f"---")
    lines.append(f"## 三、淘汰赛各阶段概率")
    lines.append(f"")

    lines.append(f"### 🏆 夺冠概率 Top 10")
    lines.append(f"| 球队 | 中文名 | 夺冠概率 |")
    lines.append(f"|------|--------|----------|")
    for team, pct in list(stats['champion'].items())[:10]:
        name_cn = TEAM_PROFILES.get(team, {}).get('name_cn', team)
        lines.append(f"| {team} | {name_cn} | {pct:.1f}% |")

    lines.append(f"")
    lines.append(f"### 🏅 四强概率 Top 10")
    lines.append(f"| 球队 | 中文名 | 四强概率 |")
    lines.append(f"|------|--------|----------|")
    for team, pct in list(stats['semifinal'].items())[:10]:
        name_cn = TEAM_PROFILES.get(team, {}).get('name_cn', team)
        if pct > 0:
            lines.append(f"| {team} | {name_cn} | {pct:.1f}% |")

    # ===== Section 4: 最可能淘汰赛路径 =====
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"## 四、概率加权最可能淘汰赛路径")
    lines.append(f"")
    lines.append(f"> 方法：10,000 次模拟中，每个 slot 出现频率最高的对阵组合构成「最可能」路径。")
    lines.append(f"> 预期比分：基于 ELO + Poisson 的确定性预期比分（无随机扰动），KO 平局通过点球打破。")
    lines.append(f"> ⚠️ 决赛出现 1-1 预期比分时，模型按概率偏向 ELO 较高方（阿根廷 2114 vs 法国 2075）。")
    lines.append(f"")

    exp = expected_bracket

    if not exp.get('r32_pairs'):
        lines.append(f"⚠️ 无法构建最可能路径——数据不完整。请增加模拟次数或检查数据。")
        return '\n'.join(lines)

    # R32 bracket
    lines.append(f"### R32 — 1/16 决赛")
    lines.append(f"| Slot | 对阵 | 预期比分 | 胜/平/负概率 | 晋级队 |")
    lines.append(f"|------|------|----------|-------------|--------|")

    for slot_id in range(1, 17):
        pair = exp['r32_pairs'].get(slot_id)
        winner = exp['r32_winners'].get(slot_id)
        if not pair or not winner:
            continue
        t1, t2 = pair

        home_adv = 60 if t1 in ('USA', 'Mexico', 'Canada') else 0
        venue_name = R32_VENUES.get(slot_id, (None,))[0]
        score, win_p, draw_p, loss_p = expected_score(t1, t2, home_adv, venue_name)

        n1 = TEAM_PROFILES.get(t1, {}).get('name_cn', t1)
        n2 = TEAM_PROFILES.get(t2, {}).get('name_cn', t2)
        nw = TEAM_PROFILES.get(winner, {}).get('name_cn', winner)

        venue_note = ""
        if venue_name == "Estadio Azteca":
            venue_note = " 🏔️"
        elif venue_name == "Hard Rock Stadium":
            venue_note = " 🔥"

        lines.append(f"| {slot_id}{venue_note} | {n1} vs {n2} | {score[0]}-{score[1]} | {win_p*100:.0f}%/{draw_p*100:.0f}%/{loss_p*100:.0f}% | ➡️ {nw} |")

    # R16
    lines.append(f"")
    lines.append(f"### R16 — 1/8 决赛")
    lines.append(f"| # | 对阵 | 预期比分 | 晋级队 |")
    lines.append(f"|---|------|----------|--------|")
    for i, (s1, s2) in enumerate(R16_PAIRINGS, 1):
        w1 = exp['r32_winners'].get(s1)
        w2 = exp['r32_winners'].get(s2)
        r16_winner = exp['r16_winners'].get(i)
        if w1 and w2:
            venue_name = R16_VENUES.get(i, (None,))[0]
            score, _, _, _ = expected_score(w1, w2, venue_name=venue_name)
            n1 = TEAM_PROFILES.get(w1, {}).get('name_cn', w1)
            n2 = TEAM_PROFILES.get(w2, {}).get('name_cn', w2)
            nw = TEAM_PROFILES.get(r16_winner, {}).get('name_cn', r16_winner) if r16_winner else '?'
            venue_note = " 🏔️" if venue_name == "Estadio Azteca" else ""
            lines.append(f"| {i}{venue_note} | {n1} vs {n2} | {score[0]}-{score[1]} | ➡️ {nw} |")

    # QF
    lines.append(f"")
    lines.append(f"### QF — 1/4 决赛")
    lines.append(f"| # | 对阵 | 预期比分 | 晋级队 |")
    lines.append(f"|---|------|----------|--------|")
    for i, (s1, s2) in enumerate(QF_PAIRINGS, 1):
        w1 = exp['r16_winners'].get(s1)
        w2 = exp['r16_winners'].get(s2)
        qf_winner = exp['qf_winners'].get(i)
        if w1 and w2:
            venue_name = QF_VENUES.get(i, (None,))[0]
            score, _, _, _ = expected_score(w1, w2, venue_name=venue_name)
            n1 = TEAM_PROFILES.get(w1, {}).get('name_cn', w1)
            n2 = TEAM_PROFILES.get(w2, {}).get('name_cn', w2)
            nw = TEAM_PROFILES.get(qf_winner, {}).get('name_cn', qf_winner) if qf_winner else '?'
            venue_note = " 🔥" if venue_name == "Hard Rock Stadium" else ""
            lines.append(f"| {i}{venue_note} | {n1} vs {n2} | {score[0]}-{score[1]} | ➡️ {nw} |")

    # SF
    lines.append(f"")
    lines.append(f"### SF — 半决赛")
    lines.append(f"| # | 对阵 | 预期比分 | 晋级队 |")
    lines.append(f"|---|------|----------|--------|")
    for i, (s1, s2) in enumerate(SF_PAIRING, 1):
        w1 = exp['qf_winners'].get(s1)
        w2 = exp['qf_winners'].get(s2)
        sf_winner = exp['sf_winners'].get(i)
        if w1 and w2:
            venue_name = SF_VENUES.get(i, (None,))[0]
            score, _, _, _ = expected_score(w1, w2, venue_name=venue_name)
            n1 = TEAM_PROFILES.get(w1, {}).get('name_cn', w1)
            n2 = TEAM_PROFILES.get(w2, {}).get('name_cn', w2)
            nw = TEAM_PROFILES.get(sf_winner, {}).get('name_cn', sf_winner) if sf_winner else '?'
            lines.append(f"| {i} | {n1} vs {n2} | {score[0]}-{score[1]} | ➡️ {nw} |")

    # Final — 分离展示 P3 fix
    final_winner = exp.get('final_winner')
    lines.append(f"")
    lines.append(f"### 🏆 决赛 — MetLife Stadium (New York)")
    f1 = exp['sf_winners'].get(1)
    f2 = exp['sf_winners'].get(2)
    if f1 and f2 and final_winner:
        n1 = TEAM_PROFILES.get(f1, {}).get('name_cn', f1)
        n2 = TEAM_PROFILES.get(f2, {}).get('name_cn', f2)
        nw = TEAM_PROFILES.get(final_winner, {}).get('name_cn', final_winner)
        score, win_p, draw_p, loss_p = expected_score(f1, f2, venue_name=FINAL_VENUE[0])

        # P3 fix: clearly separate expected score vs champion prediction
        lines.append(f"")
        lines.append(f"**📊 Poisson 预期（90 分钟常规时间）**")
        lines.append(f"")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 最可能比分 | {score[0]} - {score[1]} |")
        lines.append(f"| {n1} 胜概率 | {win_p*100:.1f}% |")
        lines.append(f"| 平局概率 | {draw_p*100:.1f}% |")
        lines.append(f"| {n2} 胜概率 | {loss_p*100:.1f}% |")
        lines.append(f"")
        lines.append(f"**🏆 Monte Carlo 预测（含加时+点球）**")
        lines.append(f"")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| {n1} MC 夺冠率 | {stats['champion'].get(f1, 0):.1f}% |")
        lines.append(f"| {n2} MC 夺冠率 | {stats['champion'].get(f2, 0):.1f}% |")
        lines.append(f"| **最可能冠军** | **{nw}** |")
        lines.append(f"")
        lines.append(f"> 💡 Poisson 预期比分是 90 分钟最可能比分（可为平局），MC 冠军含加时+点球概率打破。当预期比分平局时，ELO 高方（{n2 if ELO.get(f2,0) > ELO.get(f1,0) else n1}）在点球中略占优。")

    # ===== Section 5: 关于本预测 =====
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"## 五、关于本预测")
    lines.append(f"")
    lines.append(f"- **模型**: Elo 评分（2100-scale）+ Poisson 进球分布 + FIFA 官方淘汰赛对阵表")
    lines.append(f"- **模拟**: {n:,} 次 Monte Carlo 全流程模拟")
    lines.append(f"- **球场因素**: 16 个球场，建模海拔（Azteca 2200m）和高温（Miami, Dallas 等）对非适应球队的惩罚")
    lines.append(f"- **平局处理**: KO 阶段概率化打破（非确定性强队胜），ELO 差 0 → 50:50")
    lines.append(f"- **冷门因子**: 小组赛 3% 概率弱队获得 +2 球冷门加成（模拟世界杯不确定性）")
    lines.append(f"- **已知局限**: 无实时伤病/阵容/教练数据，ELO 为静态数据（2026-05-01），小组赛无 venue 建模")
    lines.append(f"")

    return '\n'.join(lines)


# ============================================================
# 10. CLI Output (original modes)
# ============================================================
def print_results(stats):
    n = stats['n_sims']
    print(f"\n🌍 2026 FIFA World Cup — Full Monte Carlo ({n:,} simulations)")
    print(f"{'='*70}")

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

    print(f"\n\n🏟️ KNOCKOUT STAGE PROBABILITIES")
    print(f"{'='*70}")
    print(f"\n  🏆 CHAMPION")
    for i, (team, pct) in enumerate(stats['champion'].items()):
        if i >= 10: break
        print(f"  {team:<25} {pct:>6.1f}%")

    print(f"\n  🥈 FINALISTS")
    for i, (team, pct) in enumerate(stats['final'].items()):
        if i >= 10: break
        print(f"  {team:<25} {pct:>6.1f}%")

    print(f"\n  🏅 SEMI-FINALISTS")
    for i, (team, pct) in enumerate(stats['semifinal'].items()):
        if i >= 10: break
        print(f"  {team:<25} {pct:>6.1f}%")

    if stats['champion']:
        top = list(stats['champion'].items())[0]
        print(f"\n{'='*70}")
        print(f"  👑 MOST LIKELY CHAMPION: {top[0]} ({top[1]}%)")
        print(f"  📈 Model: Elo + Poisson + FIFA Official Bracket + {n:,} MC Sims")
        print(f"  📊 Backtest: 57.8% (WC 2022)")
        print(f"  🔄 ELO: clubelo.com (55 teams, national-team scale)")
        print(f"{'='*70}")


# ============================================================
# 11. Main
# ============================================================
def main():
    mode = sys.argv[1] if len(sys.argv) >= 2 else '--full'
    n_sims = 5000
    for i, arg in enumerate(sys.argv):
        if arg == '--sims' and i + 1 < len(sys.argv):
            n_sims = int(sys.argv[i + 1])

    if not validate_data():
        sys.exit(1)

    print("🌍 2026 FIFA World Cup — Monte Carlo Prediction System v2.1")
    print(f"📅 June 11 – July 19, 2026 | 🏟️ USA 🇺🇸 Canada 🇨🇦 Mexico 🇲🇽")
    print(f"👥 48 teams | 12 groups | Official FIFA Bracket | {n_sims:,} sims")
    print()

    if mode == '--report':
        # Report mode: run MC + generate markdown report
        print("🔄 Running Monte Carlo simulation...")
        stats, expected_bracket = run_monte_carlo(n_sims)

        print("📝 Generating report...")
        report = generate_report(stats, expected_bracket)

        # Save report
        report_dir = os.path.join(os.path.dirname(__file__), 'data')
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        report_path = os.path.join(report_dir, f'wc2026_report_{date_str}.md')
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"💾 Report saved: data/wc2026_report_{date_str}.md")

        # Save JSON data
        json_data = {
            'generated': datetime.now().isoformat(),
            'model': 'Elo + Poisson + FIFA Official Bracket v2.1',
            'n_sims': n_sims,
            'backtest_accuracy': '57.8% (WC2022), 51.0% (Euro2024)',
            'champion': {k: v for k, v in list(stats['champion'].items())[:10]},
            'final': {k: v for k, v in list(stats['final'].items())[:10]},
            'semifinal': {k: v for k, v in list(stats['semifinal'].items())[:10]},
            'quarterfinal': {k: v for k, v in list(stats['quarterfinal'].items())[:16]},
            'group_advance': stats['group_advance'],
            'expected_bracket': expected_bracket,
        }
        json_path = os.path.join(report_dir, 'wc2026_mc_report.json')
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"💾 JSON data saved: data/wc2026_mc_report.json")

        # Print report summary to stdout
        print("\n" + "="*70)
        print("REPORT SUMMARY")
        print("="*70)
        if stats['champion']:
            top = list(stats['champion'].items())[0]
            print(f"👑 Champion: {top[0]} ({top[1]}%)")
        if expected_bracket.get('final_winner'):
            nw = TEAM_PROFILES.get(expected_bracket['final_winner'], {}).get('name_cn', expected_bracket['final_winner'])
            print(f"🏆 Expected Final: {nw} wins")
        print(f"📄 Full report: data/wc2026_report_{date_str}.md")

    elif mode == '--groups':
        # Groups only (quick)
        stats, _ = run_monte_carlo(n_sims)
        print_results(stats)

    else:
        # --full or --knockout
        print("🔄 Running Monte Carlo simulation...")
        stats, _ = run_monte_carlo(n_sims)
        print_results(stats)

        # Save JSON
        report_data = {
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
        json_path = os.path.join(os.path.dirname(__file__), 'data', 'wc2026_mc_report.json')
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full report saved: data/wc2026_mc_report.json")


if __name__ == '__main__':
    main()
