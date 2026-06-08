#!/usr/bin/env python3
"""
2026 FIFA World Cup — 全流程 Monte Carlo 预测系统 v2.3
基于: Elo + Poisson + FIFA 官方 Bracket + 2,000次 全流程模拟

Usage:
  python3.11 wc2026_predict.py [--full|--groups|--knockout|--report] [--sims N] [--news]

v2.3 更新:
- ELO 采集管线完全重写 (fetch_elo.py v2.0): 多源级联 + 64 队完整覆盖
- 锦标赛级形态因子: 每队抽取持久 N(0,60) form boost, 模拟"状态火热的黑马"
- 冷门模型: 上界 18%→22%, 每场 N(0,25) 抖动, 比分扰动 30%→40%
- 队名标准化: USA→United States, 全量 TEAM_ALIASES 映射
- ELO 数据源: international-football.net (结构化 HTML, 非 JS 渲染)

v2.2 更新:
- ELO 数据刷新到 2026-05-20 (eloratings.net)
- 动态冷门模型：ELO 差相关冷门概率 (max 18% for equal teams, min 2%)
- ELO 比赛级抖动：每场模拟前对 ELO 添加 N(0,35) 高斯噪声
- 比分扰动增强：20% → 30%
- --news 模式：集成 wuhoo-news-rss 新闻情感分析

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
# v2.2: News sentiment integration (RSS only)
try:
    from sentiment_analyzer import SentimentAnalyzer, RSSConnector
    _sentiment_available = True
except Exception:
    _sentiment_available = False

random.seed(42)
_poisson = PoissonModel()

# v2.3: Tournament-level form — each team draws a persistent form boost/slump
# for the entire tournament. This creates correlated outcomes and prevents
# top-team dominance by allowing any team to have a "hot tournament."
TOURNAMENT_FORM_SIGMA = 60  # std dev of persistent tournament ELO adjustment
# v2.2: ELO jitter — reduced in v2.3 since tournament form handles big swings
ELO_JITTER_SIGMA = 25  # std dev of per-match ELO perturbation (v2.2: 35 → v2.3: 25)
# v2.2: Dynamic upset probability — replaces flat 3% with ELO-difference-based formula
# Higher upset chance for close matches, lower for blowouts
def _upset_prob(elo_diff):
    """Dynamic upset probability based on absolute ELO difference."""
    return max(0.02, 0.22 - 0.0003 * abs(elo_diff))  # v2.2: 0.18 → v2.3: 0.22

# ============================================================
# 1. 分组 & ELO
# ============================================================
GROUPS = {
    'A': ['Mexico', 'South Africa', 'South Korea', 'Czech Republic'],
    'B': ['Canada', 'Switzerland', 'Bosnia and Herzegovina', 'Qatar'],
    'C': ['Brazil', 'Morocco', 'Haiti', 'Scotland'],
    'D': ['United States', 'Turkey', 'Paraguay', 'Australia'],
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

def _load_group_venues():
    gv_path = os.path.join(os.path.dirname(__file__), 'data', 'group_venues.json')
    with open(gv_path) as f:
        return json.load(f)['groups']

GROUP_VENUES = _load_group_venues()

def _load_profiles():
    ppath = os.path.join(os.path.dirname(__file__), 'data', 'team_profiles.json')
    with open(ppath) as f:
        return json.load(f)['teams']

TEAM_PROFILES = _load_profiles()

# ============================================================
# 1b. Injuries (v2.3)
# ============================================================
def _load_injuries():
    """Load injury data. Returns {team: total_penalty} dict."""
    ipath = os.path.join(os.path.dirname(__file__), 'data', 'injuries.json')
    try:
        with open(ipath) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {team: info['total_penalty'] for team, info in data.get('injuries', {}).items()}

INJURIES = _load_injuries()

# ============================================================
# 1c. Team Metadata (v2.3) — Coach + Roster + Chemistry
# ============================================================
def _load_team_metadata():
    """Load team metadata. Returns {team: metadata} dict."""
    mpath = os.path.join(os.path.dirname(__file__), 'data', 'team_metadata.json')
    try:
        with open(mpath) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data.get('teams', {})

TEAM_META = _load_team_metadata()

RESULT_POINTS = {
    'champion': 25, 'finalist': 15, 'semifinalist': 10,
    'quarterfinalist': 5, 'round16': 2, 'none': 0
}

def compute_meta_adjustment(team):
    """Compute ELO adjustment from coaching + roster + chemistry factors.
    Returns (adjustment, breakdown_dict) or (0, None) if no data."""
    meta = TEAM_META.get(team)
    if not meta:
        return 0, None
    coach = meta.get('coach_wc_experience', 0) * 8
    result = RESULT_POINTS.get(meta.get('coach_best_result', 'none'), 0)
    stability = (meta.get('roster_stability', 0.5) - 0.5) * 40
    chemistry = (meta.get('recent_form_consistency', 0.5) - 0.5) * 30
    total = int(round(coach + result + stability + chemistry))
    return total, {'coach': coach, 'result': result, 'stability': stability, 'chemistry': chemistry}

META_ADJUSTMENTS = {}
for team in ALL_TEAMS:
    adj, _ = compute_meta_adjustment(team)
    if adj != 0:
        META_ADJUSTMENTS[team] = adj

# ============================================================
# 1d. Friendly Match Form (v3.1) — Recent warm-up match results
# ============================================================
def _load_friendly_form():
    """Load friendly match form adjustments.
    Returns {team: adjustment} dict computed from recent friendly matches."""
    fpath = os.path.join(os.path.dirname(__file__), 'data', 'friendly_form_adjustments.json')
    try:
        with open(fpath) as f:
            data = json.load(f)
        return data.get('teams', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

FRIENDLY_FORM = _load_friendly_form()

# ============================================================
# 1e. News Sentiment (v3.2 — RSS single channel)
# ============================================================
def load_news_sentiment(enable_news=False):
    """Load news sentiment scores and convert to ELO adjustments.
    Returns dict: team_name -> elo_adjustment (int).
    
    v3.2: Removed hard cutoff when news_items is empty. Always runs proxy sentiment
    strategy even with sparse/no data — returns neutral (zero) adjustments gracefully
    rather than bailing out. Two-tier window: 14 days → 30 day fallback.
    """
    if not enable_news or not _sentiment_available:
        return {}

    try:
        connector = RSSConnector()
        if not connector.db_path or not connector.db_path.exists():
            print("📰 News sentiment skipped: news-rss DB not found", file=sys.stderr)
            return {}

        analyzer = SentimentAnalyzer()
        all_teams_list = list(ALL_TEAMS)

        # Tiered window: start with 14 days, fall back to 30 days if empty
        news_items = connector.fetch_football_news(all_teams_list, days_back=14)

        if not news_items:
            news_items = connector.fetch_football_news(all_teams_list, days_back=30)

        if news_items:
            sentiment_scores = analyzer.analyze_news_batch(news_items)
            n_articles = len(news_items)
            print(f"📰 RSS sentiment: {n_articles} articles loaded from DB", file=sys.stderr)
        else:
            sentiment_scores = {}
            print("📰 RSS sentiment: no football articles in DB (30-day window), "
                  "all teams → neutral", file=sys.stderr)

        # Convert sentiment to ELO adjustment (scale: ±40 max)
        elo_adj = {}
        teams_with_news = 0
        teams_with_proxy = 0
        for team in ALL_TEAMS:
            proxy_score = analyzer.get_proxy_sentiment(team, sentiment_scores)
            if proxy_score != 0 and team.lower() not in sentiment_scores:
                sentiment_scores[team.lower()] = proxy_score
                teams_with_proxy += 1
            impact = analyzer.get_sentiment_impact(team, sentiment_scores)
            adj = int(round(impact * 250))  # -0.15*250=-37, 0.05*250=12
            if adj != 0:
                elo_adj[team] = adj
                teams_with_news += 1

        direct_count = teams_with_news - teams_with_proxy
        if teams_with_news > 0:
            print(f"📰 News sentiment loaded: {direct_count} direct + {teams_with_proxy} proxy = "
                  f"{teams_with_news}/{len(ALL_TEAMS)} teams "
                  f"(range: {min(elo_adj.values())} to {max(elo_adj.values())} ELO)",
                  file=sys.stderr)
        else:
            print(f"📰 News sentiment: all 48 teams neutral (no actionable signals)",
                  file=sys.stderr)
        return elo_adj
    except Exception as e:
        print(f"📰 News sentiment unavailable: {e}", file=sys.stderr)
        return {}

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

    # v2.2: Validate group stage venues
    for letter in 'ABCDEFGHIJKL':
        if letter not in GROUP_VENUES:
            errors.append(f"Group {letter} missing from group_venues.json")
        else:
            gv = GROUP_VENUES[letter]
            for md, vname in enumerate(gv.get('venues', [])):
                if vname not in all_venue_names:
                    errors.append(f"Group {letter} MD{md+1} venue '{vname}' not in venues.json")

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
    """Simulate one match, return (goals_a, goals_b).
    v2.2: ELO jitter per match + increased score perturbation."""
    venue_penalty_a = get_venue_penalty(team_a, venue_name) if venue_name else 0
    venue_penalty_b = get_venue_penalty(team_b, venue_name) if venue_name else 0

    # v2.2: Apply ELO jitter to simulate match-day form fluctuation
    jitter_a = random.gauss(0, ELO_JITTER_SIGMA)
    jitter_b = random.gauss(0, ELO_JITTER_SIGMA)

    pred = predict_score(
        elo_a - venue_penalty_a + jitter_a,
        elo_b - venue_penalty_b + jitter_b,
        home_adv)
    ga, gb = pred['score']

    # v2.3: Score perturbation (30% → 40%) to add more variance
    if random.random() < 0.4:
        ga += random.choice([-1, 0, 1])
    if random.random() < 0.4:
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
def simulate_one_tournament(elo_adjustments=None):
    """Run one complete tournament simulation, return champion & round results.
    Also returns `r32_teams` dict for bracket tracking.
    v2.2: elo_adjustments applies news sentiment adjustments per team.
    v2.3: tournament_form adds persistent team-level random boost/slump.
    """
    if elo_adjustments is None:
        elo_adjustments = {}

    # v2.3: Apply injury penalties (loaded from injuries.json)
    injury_adjustments = {}
    if INJURIES:
        for team, penalty in INJURIES.items():
            injury_adjustments[team] = penalty

    # v2.3: Tournament-level form — each team gets a persistent random boost
    # that applies to ALL matches in this simulation. A team with +80 form
    # is effectively 80 ELO points stronger for the entire tournament.
    all_team_names = [t for g in GROUPS.values() for t in g]
    tournament_form = {t: random.gauss(0, TOURNAMENT_FORM_SIGMA) for t in all_team_names}

    elos = {t: ELO.get(t, 1700) + elo_adjustments.get(t, 0) + injury_adjustments.get(t, 0)
             + META_ADJUSTMENTS.get(t, 0) + FRIENDLY_FORM.get(t, 0) + tournament_form.get(t, 0)
            for g in GROUPS.values() for t in g}

    # --- Group Stage ---
    group_standings = {}
    all_thirds = []

    for letter, teams in GROUPS.items():
        pts = {t: 0 for t in teams}
        gf = {t: 0 for t in teams}
        ga = {t: 0 for t in teams}

        # v2.2: Get group stage venues for this group
        gv = GROUP_VENUES.get(letter, {})
        group_venue_list = gv.get('venues', [None, None, None])

        for i in range(4):
            for j in range(i + 1, 4):
                home, away = teams[i], teams[j]
                home_adv = 0
                if home in ('United States', 'Mexico', 'Canada'):
                    home_adv = 60
                elif home in ('Brazil', 'Argentina', 'Uruguay', 'Colombia', 'Ecuador', 'Paraguay'):
                    home_adv = 15

                # v2.2: Determine matchday for venue lookup
                # MD1: (0,1) (2,3) | MD2: (0,2) (1,3) | MD3: (0,3) (1,2)
                if (i == 0 and j == 1) or (i == 2 and j == 3):
                    md = 0
                elif (i == 0 and j == 2) or (i == 1 and j == 3):
                    md = 1
                else:
                    md = 2
                venue_name = group_venue_list[md] if md < len(group_venue_list) else None

                gh, ga_goals = sim_match(home, away, elos[home], elos[away], home_adv,
                                         venue_name=venue_name)

                # v2.2: Dynamic upset factor — higher chance for close teams
                elo_diff = elos[home] - elos[away]
                upset_chance = _upset_prob(elo_diff)
                if random.random() < upset_chance:
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
        home_adv = 60 if t1 in ('United States', 'Mexico', 'Canada') else 0
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
    sf_losers_list = []  # v2.2: track all 4 SF participants
    for i, (s1, s2) in enumerate(SF_PAIRING, 1):
        if s1 in qf_winners and s2 in qf_winners:
            t1, t2 = qf_winners[s1], qf_winners[s2]
            venue_name = SF_VENUES.get(i, (None,))[0]
            g1, g2 = sim_match(t1, t2, elos[t1], elos[t2], ko=True, venue_name=venue_name)
            winner = t1 if g1 > g2 else t2
            loser = t2 if g1 > g2 else t1
            sf_winners[i] = winner
            sf_losers_list.append(loser)
    stage_winners['SF'] = sf_winners
    stage_winners['SF_all'] = list(sf_winners.values()) + sf_losers_list  # all 4 SF teams

    # Final
    if 1 in sf_winners and 2 in sf_winners:
        t1, t2 = sf_winners[1], sf_winners[2]
        g1, g2 = sim_match(t1, t2, elos[t1], elos[t2], ko=True, venue_name=FINAL_VENUE[0])
        champion = t1 if g1 > g2 else t2
        runner_up = t2 if g1 > g2 else t1
        stage_winners['F'] = {1: champion, 2: runner_up}
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
def run_monte_carlo(n_sims=10000, elo_adjustments=None):
    """Run full tournament Monte Carlo, return aggregated stats + expected bracket data.
    v2.2: elo_adjustments applies per-team news sentiment ELO adjustments.
    """
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

        stage_winners, group_standings, r32_teams = simulate_one_tournament(elo_adjustments)

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

        # v2.2: Count all 4 SF participants (SF_all includes both winners and losers)
        sf_winners = stage_winners.get('SF', {})
        sf_all = stage_winners.get('SF_all', [])
        for team in sf_all:
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
    host_adv = any(t in ('United States', 'Mexico', 'Canada') for t in teams)
    if host_adv:
        host_names = [t for t in teams if t in ('United States', 'Mexico', 'Canada')]
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
def generate_report(stats, expected_bracket, elo_adjustments=None):
    """Generate comprehensive Chinese Markdown report.
    v2.2: elo_adjustments for news sentiment display.
    """
    if elo_adjustments is None:
        elo_adjustments = {}
    n = stats['n_sims']
    lines = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    lines.append(f"# 🌍 2026 FIFA 世界杯预测报告")
    lines.append(f"")
    lines.append(f"**生成时间**: {now} | **模拟次数**: {n:,} | **模型**: Elo + Poisson + FIFA Bracket v2.3")
    lines.append(f"**数据来源**: international-football.net + eloratings.net (2026-05-21) | **回测**: WC2022 57.8%")
    lines.append(f"")
    lines.append(f"> ⚠️ v2.3 新增: 伤病(7队/11名球员), 教练因子(20队), 锦标赛形态因子 N(0,60). 预测仅供娱乐参考。")
    if elo_adjustments:
        lines.append(f"> 📰 已集成新闻情感分析：{len(elo_adjustments)} 支球队有情感调整 (±{max(abs(v) for v in elo_adjustments.values())} ELO)")
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
    lines.append(f"### 🏆 冠军概率 ASCII 柱状图")
    lines.append(f"```")
    champion_sorted = sorted(stats['champion'].items(), key=lambda x: -x[1])[:12]
    max_pct = max(pct for _, pct in champion_sorted)
    bar_width = 30
    for team, pct in champion_sorted:
        bar_len = int(pct / max_pct * bar_width)
        bar = '█' * bar_len
        name_cn = TEAM_PROFILES.get(team, {}).get('name_cn', team)
        lines.append(f"  {name_cn:<10} {bar} {pct:.1f}%")
    lines.append(f"```")
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
        lines.append(f"⚠️ 无法构建最可能路径——模拟数据不足。请增加模拟次数或检查数据文件。")
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

        home_adv = 60 if t1 in ('United States', 'Mexico', 'Canada') else 0
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


    # ===== Section 4.5: 冷门风险指数 v2.3 =====
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"## 四.五、冷门风险指数 🎲")
    lines.append(f"")
    lines.append(f"> 淘汰赛中弱队胜率 >25% 的高风险场次。ELO 差距越小、概率越接近，冷门风险越大。")
    lines.append(f"")

    upset_rounds = []
    for slot_id in range(1, 17):
        pair = expected_bracket.get('r32_pairs', {}).get(slot_id)
        if not pair:
            continue
        t1, t2 = pair
        e1, e2 = ELO.get(t1, 1700), ELO.get(t2, 1700)
        diff = abs(e1 - e2)
        pred = predict_score(e1, e2)
        favorite_win = max(pred['win'], pred['loss'])
        underdog_win = 1 - favorite_win if abs(pred['win'] - pred['loss']) > 0.001 else 0.5
        if underdog_win > 0.25:
            upset_rounds.append(('R32', slot_id, t1, t2, diff, underdog_win))

    if upset_rounds:
        lines.append(f"| 轮次 | Slot | 对阵 | ELO 差 | 弱队胜率 | 风险 |")
        lines.append(f"|------|------|------|--------|----------|------|")
        for round_name, slot, t1, t2, diff, uw in sorted(upset_rounds, key=lambda x: -x[5]):
            risk = '🔴 高' if uw > 0.40 else '🟡 中' if uw > 0.33 else '🟢 低'
            n1 = TEAM_PROFILES.get(t1, {}).get('name_cn', t1)
            n2 = TEAM_PROFILES.get(t2, {}).get('name_cn', t2)
            lines.append(f"| {round_name} | {slot} | {n1} vs {n2} | {diff} | {uw*100:.0f}% | {risk} |")
    else:
        lines.append(f"⚠️ 无显著冷门风险场次（所有淘汰赛对阵中弱队胜率均 ≤25%）")
    lines.append(f"")
    # ===== Section 5: 关于本预测 =====
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"## 五、关于本预测")
    lines.append(f"")
    lines.append(f"- **模型**: Elo 评分（2100-scale）+ Poisson 进球分布 + FIFA 官方淘汰赛对阵表")
    lines.append(f"- **模拟**: {n:,} 次 Monte Carlo 全流程模拟")
    lines.append(f"- **集成功能 v2.3**: 伤病(INJURIES), 教练/磨合(META), 锦标赛形态 N(0,60), 同洲代理新闻情感，建模海拔（Azteca 2200m）和高温（Miami, Dallas 等）对非适应球队的惩罚")
    lines.append(f"- **平局处理**: KO 阶段概率化打破（非确定性强队胜），ELO 差 0 → 50:50")
    lines.append(f"- **冷门模型 v2.3**: 动态冷门上界 22% + 每场 N(0,25) 抖动 + 40% 比分扰动 + 锦标赛形态 N(0,60)")
    lines.append(f"- **新闻情感 v2.3**: {'已启用 (' + str(len(elo_adjustments)) + ' 支球队有调整)' if elo_adjustments else '未启用（--news 参数可选）'}")
    lines.append(f"- **已知局限**: ELO 为 2026-05-21 静态数据；小组赛 venue 建模已启用；伤病/教练数据需手动维护")
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
        print(f"  🔄 ELO: international-football.net (64 teams, 2100-scale)")
        print(f"{'='*70}")


# ============================================================
# 11. Single Match Prediction (v3.0)
# ============================================================

def _load_schedule():
    """Load WC2026 match schedule."""
    spath = os.path.join(os.path.dirname(__file__), 'data', 'wc2026_schedule.json')
    try:
        with open(spath) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'matches': []}

SCHEDULE = None

def _get_schedule():
    global SCHEDULE
    if SCHEDULE is None:
        SCHEDULE = _load_schedule()
    return SCHEDULE

def _find_team_canonical(name, all_teams=None):
    """Fuzzy match a team name to canonical GROUPS name. Case-insensitive."""
    if all_teams is None:
        all_teams = ALL_TEAMS
    name_lower = name.strip().lower()
    # Direct match
    for t in all_teams:
        if t.lower() == name_lower:
            return t
    # Partial match
    for t in all_teams:
        if name_lower in t.lower() or t.lower() in name_lower:
            return t
    # Common aliases
    aliases = {
        'usa': 'United States', 'us': 'United States',
        'south korea': 'South Korea', 'korea': 'South Korea',
        'bosnia': 'Bosnia and Herzegovina', 'bih': 'Bosnia and Herzegovina',
        'czechia': 'Czech Republic', 'czech': 'Czech Republic',
        'cote d\'ivoire': 'Ivory Coast',
        'cape verde': 'Cape Verde',
        'turkiye': 'Turkey',
        'dr congo': 'DR Congo', 'congo': 'DR Congo',
        'curacao': 'Curacao', 'curaçao': 'Curacao',
    }
    if name_lower in aliases:
        return aliases[name_lower]
    return None

def predict_single_match(team_a, team_b, venue_name=None, enable_news=False,
                         manual_adjustments=None, knockout=False):
    """Predict a single match with full audit trail.

    Args:
        team_a, team_b: canonical team names
        venue_name: stadium name (from venues.json) or None to skip venue effects
        enable_news: if True, load RSS news sentiment
        manual_adjustments: dict of team->elo_adjustment for manual overrides
        knockout: if True, resolve draws via probabilistic tiebreaker

    Returns:
        dict with full audit trail and prediction results
    """
    if manual_adjustments is None:
        manual_adjustments = {}

    audit = {
        'team_a': team_a,
        'team_b': team_b,
        'venue': venue_name,
        'generated': datetime.now().isoformat(),
        'layers': {},
    }

    # --- Layer 1: Base ELO ---
    elo_a = ELO.get(team_a, 1700)
    elo_b = ELO.get(team_b, 1700)
    elo_diff_raw = elo_a - elo_b
    base_win = 1 / (1 + 10 ** (-elo_diff_raw / 400))
    audit['layers']['1_elo_base'] = {
        'team_a_elo': elo_a,
        'team_b_elo': elo_b,
        'elo_diff': elo_diff_raw,
        'base_win_prob': round(base_win * 100, 1),
        'description': f"{team_a} {elo_a} vs {team_b} {elo_b}, Δ={elo_diff_raw:+d}"
    }

    effective_a = elo_a
    effective_b = elo_b

    # --- Layer 2: Injuries ---
    inj_a = INJURIES.get(team_a, 0)
    inj_b = INJURIES.get(team_b, 0)
    inj_details_a = []
    inj_details_b = []

    # Load full injury details
    ipath = os.path.join(os.path.dirname(__file__), 'data', 'injuries.json')
    try:
        with open(ipath) as f:
            inj_full = json.load(f).get('injuries', {})
    except Exception:
        inj_full = {}

    for team, details_key in [(team_a, 'a'), (team_b, 'b')]:
        if team in inj_full:
            for p in inj_full[team].get('players', []):
                detail = f"  {p['name']} ({p['position']}): {p['status']} — {p['injury']} [{p['elo_penalty']:+d}]"
                if details_key == 'a':
                    inj_details_a.append(detail)
                else:
                    inj_details_b.append(detail)

    effective_a += inj_a
    effective_b += inj_b
    audit['layers']['2_injuries'] = {
        'team_a_penalty': inj_a,
        'team_b_penalty': inj_b,
        'team_a_details': inj_details_a,
        'team_b_details': inj_details_b,
        'description': f"{team_a}: {inj_a:+d} | {team_b}: {inj_b:+d}" if inj_a or inj_b else "No injuries"
    }

    # --- Layer 3: Coach / Roster / Chemistry ---
    meta_a, breakdown_a = compute_meta_adjustment(team_a)
    meta_b, breakdown_b = compute_meta_adjustment(team_b)
    effective_a += meta_a
    effective_b += meta_b
    audit['layers']['3_coach_meta'] = {
        'team_a_adjustment': meta_a,
        'team_b_adjustment': meta_b,
        'team_a_breakdown': breakdown_a,
        'team_b_breakdown': breakdown_b,
        'description': f"{team_a}: {meta_a:+d} (coach+stability+chemistry) | {team_b}: {meta_b:+d}"
    }

    # --- Layer 4: Venue Effects ---
    venue_penalty_a = 0
    venue_penalty_b = 0
    venue_details = {}
    home_adv = 0

    # Host nation home advantage
    if team_a in ('United States', 'Mexico', 'Canada'):
        home_adv = 60
    elif team_a in ('Brazil', 'Argentina', 'Uruguay', 'Colombia', 'Ecuador', 'Paraguay'):
        home_adv = 15

    if venue_name:
        venue_penalty_a = get_venue_penalty(team_a, venue_name)
        venue_penalty_b = get_venue_penalty(team_b, venue_name)
        if venue_name in VENUES.get('venues', {}):
            v = VENUES['venues'][venue_name]
            venue_details = {
                'city': v.get('city', '?'),
                'altitude_m': v.get('altitude_m', 0),
                'temp_c': v.get('temp_c_jun_jul_avg', '?'),
                'indoor': v.get('indoor', False),
                'climate_note': v.get('climate_note', ''),
            }

    effective_a += home_adv - venue_penalty_a
    effective_b -= venue_penalty_b
    audit['layers']['4_venue'] = {
        'home_advantage': home_adv,
        'team_a_venue_penalty': venue_penalty_a,
        'team_b_venue_penalty': venue_penalty_b,
        'venue_details': venue_details,
        'description': f"Home adv {home_adv:+d}, venue penalties: {team_a} {venue_penalty_a:+d} / {team_b} {venue_penalty_b:+d}"
    }

    # --- Layer 4.5: Friendly Match Form (v3.1) ---
    friendly_a = FRIENDLY_FORM.get(team_a, 0)
    friendly_b = FRIENDLY_FORM.get(team_b, 0)
    effective_a += friendly_a
    effective_b += friendly_b
    audit['layers']['4.5_friendly_form'] = {
        'team_a_adj': friendly_a,
        'team_b_adj': friendly_b,
        'description': f"{team_a}: {friendly_a:+d} (warm-up form) | {team_b}: {friendly_b:+d}" if friendly_a or friendly_b else "No recent friendlies data"
    }

    # --- Layer 5: News Sentiment (optional) ---
    news_adj = {}
    if enable_news:
        sentiment = load_news_sentiment(True)
        for t in [team_a, team_b]:
            if t in sentiment:
                news_adj[t] = sentiment[t]
                if t == team_a:
                    effective_a += sentiment[t]
                else:
                    effective_b += sentiment[t]
    audit['layers']['5_news_sentiment'] = {
        'enabled': enable_news,
        'team_a_adj': news_adj.get(team_a, 0),
        'team_b_adj': news_adj.get(team_b, 0),
        'description': f"{team_a}: {news_adj.get(team_a, 0):+d} | {team_b}: {news_adj.get(team_b, 0):+d}" if news_adj else "Not enabled"
    }

    # --- Layer 6: Manual Adjustments ---
    manual_a = manual_adjustments.get(team_a, 0)
    manual_b = manual_adjustments.get(team_b, 0)
    effective_a += manual_a
    effective_b += manual_b
    audit['layers']['6_manual'] = {
        'team_a_adj': manual_a,
        'team_b_adj': manual_b,
        'description': f"{team_a}: {manual_a:+d} | {team_b}: {manual_b:+d}" if manual_a or manual_b else "None"
    }

    # --- Final Effective ELO ---
    effective_diff = effective_a - effective_b
    audit['effective_elo'] = {
        'team_a': {'base': elo_a, 'effective': effective_a, 'adjustments': effective_a - elo_a},
        'team_b': {'base': elo_b, 'effective': effective_b, 'adjustments': effective_b - elo_b},
        'diff': effective_diff,
    }

    # --- Poisson Prediction ---
    pred = predict_score(effective_a, effective_b, 0)  # home_adv already in effective
    audit['prediction'] = {
        'model': 'Poisson (Elo-based lambda)',
        'team_a_win': round(pred['win'] * 100, 1),
        'draw': round(pred['draw'] * 100, 1),
        'team_b_win': round(pred['loss'] * 100, 1),
        'most_likely_score': f"{pred['score'][0]}-{pred['score'][1]}",
        'expected_goals_a': round(pred['ga'], 2),
        'expected_goals_b': round(pred['gb'], 2),
    }

    # --- KO Tiebreaker (if applicable) ---
    if knockout and pred['score'][0] == pred['score'][1]:
        elo_diff_abs = abs(effective_diff)
        p_higher = 0.5 + min(elo_diff_abs / 800, 0.15)
        higher_elo_team = team_a if effective_a >= effective_b else team_b
        audit['prediction']['knockout_note'] = (
            f"Expected draw in 90 min. KO tiebreaker: {higher_elo_team} "
            f"has {p_higher*100:.0f}% chance to advance (ELO-based)"
        )

    # --- Verdict ---
    win_a = audit['prediction']['team_a_win']
    draw_p = audit['prediction']['draw']
    win_b = audit['prediction']['team_b_win']

    if win_a >= 60:
        verdict = f"{team_a} 胜（高置信度）"
        confidence = 'high'
    elif win_a >= 50:
        verdict = f"{team_a} 胜（中置信度）"
        confidence = 'medium'
    elif draw_p >= 35:
        verdict = "平局（高概率）"
        confidence = 'medium'
    elif win_b >= 50:
        verdict = f"{team_b} 胜（中置信度）"
        confidence = 'medium'
    elif win_b >= 60:
        verdict = f"{team_b} 胜（高置信度）"
        confidence = 'high'
    else:
        verdict = "势均力敌（低置信度）"
        confidence = 'low'

    audit['verdict'] = {'result': verdict, 'confidence': confidence}

    # --- Reasoning ---
    reasons = []
    abs_diff = abs(elo_diff_raw)
    if abs_diff > 300:
        reasons.append(f"ELO 绝对优势 {abs_diff} 分，实力差距明显")
    elif abs_diff > 100:
        reasons.append(f"ELO 优势 {abs_diff} 分，有明确的实力差距")
    else:
        reasons.append(f"ELO 接近（差 {abs_diff} 分），实力相当")

    if inj_a != 0 or inj_b != 0:
        reasons.append(f"伤病影响：{team_a} {inj_a:+d} / {team_b} {inj_b:+d} ELO")

    if venue_penalty_a != 0 or venue_penalty_b != 0:
        if venue_name:
            alt = venue_details.get('altitude_m', 0)
            if alt > 1000:
                reasons.append(f"{venue_name} 海拔 {alt}m，非适应球队受显著影响")

    if abs(effective_diff - elo_diff_raw) > 30:
        reasons.append(f"多层调整后有效 ELO 差 {effective_diff:+d}（原始 {elo_diff_raw:+d}）")

    audit['reasoning'] = reasons

    return audit


def print_match_prediction(audit, team_profiles=None):
    """Print a formatted single match prediction."""
    if team_profiles is None:
        team_profiles = TEAM_PROFILES

    ta = audit['team_a']
    tb = audit['team_b']
    pa = team_profiles.get(ta, {})
    pb = team_profiles.get(tb, {})
    na = pa.get('name_cn', ta)
    nb = pb.get('name_cn', tb)

    elo_eff = audit['effective_elo']
    pred = audit['prediction']
    venue = audit['venue']
    layers = audit['layers']

    print("═" * 65)
    print("🏆 WC2026 单场预测 · v3.0")
    print("═" * 65)

    if venue:
        vd = layers['4_venue']['venue_details']
        alt_flag = " ⛰️" if vd.get('altitude_m', 0) > 1000 else ""
        heat_flag = " 🔥" if vd.get('temp_c', 20) > 30 else ""
        print(f"🏟️ {venue}{alt_flag}{heat_flag} ({vd.get('city', '?')}, {vd.get('altitude_m', 0)}m)")
    print(f"⚽ {na} ({ta}) vs {nb} ({tb})")
    print()

    # ELO comparison table
    print("─" * 65)
    print("📊 ELO 基础对比")
    print("─" * 65)
    l1 = layers['1_elo_base']
    print(f"  {ta:<28} {l1['team_a_elo']:>5}")
    print(f"  {tb:<28} {l1['team_b_elo']:>5}")
    print(f"  {'ELO 差':<28} {l1['elo_diff']:>+5d}  →  基础胜率 {l1['base_win_prob']}%")
    print()

    # Injuries
    print("─" * 65)
    print("🏥 伤病调整")
    print("─" * 65)
    l2 = layers['2_injuries']
    if l2['team_a_details'] or l2['team_b_details']:
        for d in l2['team_a_details']:
            print(d)
        for d in l2['team_b_details']:
            print(d)
        print(f"  伤病调整: {ta} {l2['team_a_penalty']:+d} / {tb} {l2['team_b_penalty']:+d}")
    else:
        print("  无伤病")
    print()

    # Coach/Meta
    print("─" * 65)
    print("👔 教练/磨合调整")
    print("─" * 65)
    l3 = layers['3_coach_meta']
    bda = l3.get('team_a_breakdown')
    bdb = l3.get('team_b_breakdown')
    if bda:
        print(f"  {ta}: 教练经验 +{bda['coach']:.0f}, 最佳战绩 +{bda['result']:.0f}, "
              f"阵容稳定 {bda['stability']:+.0f}, 化学反应 {bda['chemistry']:+.0f} → {l3['team_a_adjustment']:+d}")
    else:
        print(f"  {ta}: 无元数据 → 0")
    if bdb:
        print(f"  {tb}: 教练经验 +{bdb['coach']:.0f}, 最佳战绩 +{bdb['result']:.0f}, "
              f"阵容稳定 {bdb['stability']:+.0f}, 化学反应 {bdb['chemistry']:+.0f} → {l3['team_b_adjustment']:+d}")
    else:
        print(f"  {tb}: 无元数据 → 0")
    print()

    # Venue
    if venue:
        print("─" * 65)
        print("🏟️ Venue 影响")
        print("─" * 65)
        l4 = layers['4_venue']
        vd = l4['venue_details']
        print(f"  {venue} | {vd.get('city', '?')} | {vd.get('altitude_m', 0)}m | "
              f"{vd.get('temp_c', '?')}°C | {'室内' if vd.get('indoor') else '室外'}")
        print(f"  主场优势: {l4['home_advantage']:+d} ({ta})" if l4['home_advantage'] else f"  主场优势: 无")
        print(f"  {ta}: venue 惩罚 {-l4['team_a_venue_penalty']:+d}")
        print(f"  {tb}: venue 惩罚 {-l4['team_b_venue_penalty']:+d}")
        print()

    # News
    l5 = layers['5_news_sentiment']
    if l5['enabled'] and (l5['team_a_adj'] or l5['team_b_adj']):
        print("─" * 65)
        print("📰 新闻情感")
        print("─" * 65)
        print(f"  {ta}: {l5['team_a_adj']:+d}")
        print(f"  {tb}: {l5['team_b_adj']:+d}")
        print()

    # Manual
    l6 = layers['6_manual']
    if l6['team_a_adj'] or l6['team_b_adj']:
        print("─" * 65)
        print("✋ 手动调整")
        print("─" * 65)
        print(f"  {ta}: {l6['team_a_adj']:+d}")
        print(f"  {tb}: {l6['team_b_adj']:+d}")
        print()

    # Effective ELO
    print("─" * 65)
    print("🎯 综合 ELO")
    print("─" * 65)
    adj_a = elo_eff['team_a']['adjustments']
    adj_b = elo_eff['team_b']['adjustments']
    print(f"  {ta}: {elo_eff['team_a']['base']} → {elo_eff['team_a']['effective']} "
          f"({adj_a:+d} 调整)")
    print(f"  {tb}: {elo_eff['team_b']['base']} → {elo_eff['team_b']['effective']} "
          f"({adj_b:+d} 调整)")
    print(f"  有效 ELO 差: {elo_eff['diff']:+d}")
    print()

    # Prediction
    print("─" * 65)
    print("📈 Poisson 90 分钟预测")
    print("─" * 65)
    bar_w = 20
    win_a_bar = int(pred['team_a_win'] / 100 * bar_w)
    draw_bar = int(pred['draw'] / 100 * bar_w)
    win_b_bar = int(pred['team_b_win'] / 100 * bar_w)
    print(f"  {na} 胜:  {pred['team_a_win']:5.1f}% {'█' * win_a_bar}")
    print(f"  平局:    {pred['draw']:5.1f}% {'█' * draw_bar}")
    print(f"  {nb} 胜:  {pred['team_b_win']:5.1f}% {'█' * win_b_bar}")
    print(f"  最可能比分: {pred['most_likely_score']} "
          f"(xG: {ta} {pred['expected_goals_a']:.2f} / {tb} {pred['expected_goals_b']:.2f})")
    if 'knockout_note' in pred:
        print(f"  ⚠️ {pred['knockout_note']}")
    print()

    # Verdict
    print("─" * 65)
    print("🧠 综合判定")
    print("─" * 65)
    v = audit['verdict']
    print(f"  预测: {v['result']}")
    print(f"  置信度: {v['confidence']}")
    print(f"  理由:")
    for i, r in enumerate(audit['reasoning'], 1):
        print(f"    {i}. {r}")

    print()
    print("⚠️ 预测仅供娱乐参考。足球比赛具有高度不确定性。")
    print("═" * 65)


# ============================================================
# 12. Main
# ============================================================
def main():
    mode = sys.argv[1] if len(sys.argv) >= 2 else '--full'
    enable_news = '--news' in sys.argv
    n_sims = 5000
    for i, arg in enumerate(sys.argv):
        if arg == '--sims' and i + 1 < len(sys.argv):
            n_sims = int(sys.argv[i + 1])

    # --- v3.0: Single match prediction modes ---
    if mode == '--match':
        # --match "TeamA" "TeamB" [--venue "VenueName"] [--news] [--adj "Team:+N"]
        team_args = []
        venue_arg = None
        manual_adj = {}
        output_file = None
        for i, arg in enumerate(sys.argv):
            if i == 0:
                continue  # skip script name
            if arg == '--match':
                continue
            elif arg == '--venue' and i + 1 < len(sys.argv):
                venue_arg = sys.argv[i + 1]
            elif arg == '--adj' and i + 1 < len(sys.argv):
                parts = sys.argv[i + 1].split(':')
                if len(parts) == 2:
                    team = _find_team_canonical(parts[0])
                    if team:
                        manual_adj[team] = int(parts[1])
            elif arg == '-o' and i + 1 < len(sys.argv):
                output_file = sys.argv[i + 1]
            elif arg == '--ko':
                pass
            elif arg.startswith('-'):
                continue
            else:
                team_args.append(arg)

        if len(team_args) < 2:
            print("Usage: python3.11 wc2026_predict.py --match \"TeamA\" \"TeamB\" [--venue name] [--news] [--adj \"Team:+N\"] [--ko]")
            sys.exit(1)

        team_a = _find_team_canonical(team_args[0])
        team_b = _find_team_canonical(team_args[1])

        if not team_a:
            print(f"❌ Unknown team: '{team_args[0]}'. Use canonical name (e.g. 'South Korea', 'United States').")
            sys.exit(1)
        if not team_b:
            print(f"❌ Unknown team: '{team_args[1]}'.")
            sys.exit(1)

        ko = '--ko' in sys.argv
        audit = predict_single_match(team_a, team_b, venue_name=venue_arg,
                                     enable_news=enable_news, manual_adjustments=manual_adj,
                                     knockout=ko)
        print_match_prediction(audit)

        # Save JSON if -o specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(audit, f, indent=2, ensure_ascii=False, default=str)
            print(f"💾 JSON audit saved: {output_file}")

        # Save to prediction history
        _save_prediction_history(audit)
        return

    elif mode == '--match-id':
        # --match-id N
        match_id = None
        venue_arg = None
        manual_adj = {}
        for i, arg in enumerate(sys.argv):
            if i == 0:
                continue  # skip script name
            if arg == '--match-id' and i + 1 < len(sys.argv):
                match_id = int(sys.argv[i + 1])
            elif arg == '--venue' and i + 1 < len(sys.argv):
                venue_arg = sys.argv[i + 1]
            elif arg == '--adj' and i + 1 < len(sys.argv):
                parts = sys.argv[i + 1].split(':')
                if len(parts) == 2:
                    team = _find_team_canonical(parts[0])
                    if team:
                        manual_adj[team] = int(parts[1])

        if not match_id:
            print("Usage: python3.11 wc2026_predict.py --match-id N")
            sys.exit(1)

        sched = _get_schedule()
        match_info = None
        for m in sched['matches']:
            if m['match_id'] == match_id:
                match_info = m
                break

        if not match_info:
            print(f"❌ Match #{match_id} not found in schedule.")
            sys.exit(1)

        team_a = match_info['team_a']
        team_b = match_info['team_b']
        venue_name = venue_arg or match_info.get('venue')
        ko = '--ko' in sys.argv

        # Print match context
        print(f"📅 {match_info['date_beijing']} {match_info['time_beijing']} CST | "
              f"Group {match_info['group']} · MD{match_info['matchday']}")
        print(f"⚽ {match_info['team_a']} vs {match_info['team_b']}")
        print()

        audit = predict_single_match(team_a, team_b, venue_name=venue_name,
                                     enable_news=enable_news, manual_adjustments=manual_adj,
                                     knockout=ko)
        # Attach schedule info
        audit['schedule'] = match_info
        print_match_prediction(audit)

        output_file = None
        for i, arg in enumerate(sys.argv):
            if arg == '-o' and i + 1 < len(sys.argv):
                output_file = sys.argv[i + 1]
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(audit, f, indent=2, ensure_ascii=False, default=str)
            print(f"💾 JSON audit saved: {output_file}")

        _save_prediction_history(audit)
        return

    elif mode == '--group':
        # --group A --matchday 1
        group = None
        matchday = None
        for i, arg in enumerate(sys.argv):
            if i == 0:
                continue
            if arg == '--group' and i + 1 < len(sys.argv):
                group = sys.argv[i + 1].upper()
            elif arg == '--matchday' and i + 1 < len(sys.argv):
                matchday = int(sys.argv[i + 1])

        if not group or not matchday:
            print("Usage: python3.11 wc2026_predict.py --group A --matchday 1 [--news]")
            sys.exit(1)

        sched = _get_schedule()
        matches = [m for m in sched['matches']
                   if m['group'] == group and m['matchday'] == matchday]

        if not matches:
            print(f"❌ No matches found for Group {group} MD{matchday}")
            sys.exit(1)

        print(f"🏆 Group {group} · Matchday {matchday} · {len(matches)} matches")
        print(f"📅 {matches[0]['date_beijing']}")
        print()

        for m in matches:
            audit = predict_single_match(m['team_a'], m['team_b'],
                                         venue_name=m.get('venue'),
                                         enable_news=enable_news)
            audit['schedule'] = m
            print_match_prediction(audit)
            _save_prediction_history(audit)
            print()
        return

    # --- Original modes ---
    if not validate_data():
        sys.exit(1)

    # v2.2: Load news sentiment if --news flag enabled
    elo_adj = load_news_sentiment(enable_news)

    print("🌍 2026 FIFA World Cup — Monte Carlo Prediction System v3.0")
    print(f"📅 June 11 – July 19, 2026 | 🏟️ USA 🇺🇸 Canada 🇨🇦 Mexico 🇲🇽")
    print(f"👥 48 teams | 12 groups | Official FIFA Bracket | {n_sims:,} sims")
    if elo_adj:
        teams_adj = len(elo_adj)
        print(f"📰 News sentiment enabled: {teams_adj} teams with ELO adjustments")
    print()

    if mode == '--report':
        # Report mode: run MC + generate markdown report
        print("🔄 Running Monte Carlo simulation...")
        stats, expected_bracket = run_monte_carlo(n_sims, elo_adj)

        print("📝 Generating report...")
        report = generate_report(stats, expected_bracket, elo_adj)

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
            'model': 'Elo + Poisson + FIFA Official Bracket v3.0',
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
        stats, _ = run_monte_carlo(n_sims, elo_adj)
        print_results(stats)

    else:
        # --full or --knockout
        print("🔄 Running Monte Carlo simulation...")
        stats, _ = run_monte_carlo(n_sims, elo_adj)
        print_results(stats)

        # Save JSON
        report_data = {
            'generated': datetime.now().isoformat(),
            'model': 'Elo + Poisson + FIFA Official Bracket v3.0',
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


def _save_prediction_history(audit):
    """Append prediction result to history file."""
    hist_path = os.path.join(os.path.dirname(__file__), 'data', 'prediction_history.jsonl')
    record = {
        'timestamp': audit.get('generated', datetime.now().isoformat()),
        'team_a': audit['team_a'],
        'team_b': audit['team_b'],
        'venue': audit.get('venue'),
        'schedule': audit.get('schedule', {}),
        'verdict': audit['verdict']['result'],
        'confidence': audit['verdict']['confidence'],
        'prediction': audit['prediction'],
        'effective_elo': audit['effective_elo'],
    }
    try:
        with open(hist_path, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception:
        pass


if __name__ == '__main__':
    main()
