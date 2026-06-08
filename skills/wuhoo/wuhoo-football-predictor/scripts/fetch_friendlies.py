#!/usr/bin/env python3
"""
热身赛数据采集脚本 v1.0 — 支持手动输入 + URL 抓取辅助

世界杯前（6.11开幕）每天都有多场热身赛。此脚本提供：
1. --add: 手动添加单场比赛
2. --batch: 从 JSON 批量导入
3. --list: 列出已采集的比赛
4. --pending: 显示待确认结果的比赛
5. --compute-form: 基于热身赛结果计算近期状态调整值

Usage:
  python3.11 scripts/fetch_friendlies.py --add '{"team_a":"France","team_b":"Ivory Coast","score_a":1,"score_b":2,"date":"2026-06-04"}'
  python3.11 scripts/fetch_friendlies.py --list
  python3.11 scripts/fetch_friendlies.py --pending
  python3.11 scripts/fetch_friendlies.py --compute-form
"""

import json
import sys
import os
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).parent.parent / 'data'
FRIENDLY_FILE = DATA_DIR / 'friendly_matches.json'
ELO_FILE = DATA_DIR / 'elo_ratings.json'

# ─── ELO expected win probability ───
def elo_expected(elo_a: int, elo_b: int, home_adv: int = 60) -> float:
    """Expected win probability for team_a (0-1 scale)"""
    diff = elo_a - elo_b + home_adv
    return 1.0 / (1.0 + 10 ** (-diff / 400))

# ─── Result to adjustment mapping ───
def result_to_adjustment(expected_win: float, actual_diff: int, is_home: bool) -> dict:
    """
    Convert a friendly match result into an ELO adjustment.
    
    actual_diff > 0: team_a won
    actual_diff == 0: draw
    actual_diff < 0: team_a lost
    
    Adjustment scale:
      - Expected win + won:  0 to +10 (good, as expected)
      - Expected win + lost: -20 to -40 (major upset)
      - Expected loss + won: +20 to +40 (major positive surprise)
      - Expected loss + lost: -10 to 0 (bad, as expected)
      - Draw (expected win): -10 to -15 (disappointing)
      - Draw (expected loss): +10 to +15 (creditable)
    """
    if actual_diff > 0:
        won = True
    elif actual_diff == 0:
        won = None  # draw
    else:
        won = False
    
    goal_diff = abs(actual_diff)
    
    # Base: how surprising was the result?
    if won is True:
        surprise = 1.0 - expected_win  # 0 if expected to win, 1 if expected to lose
        base = int(round(surprise * 40))
        # Bonus for big wins
        if goal_diff >= 3:
            base = min(base + 10, 40)
        elif goal_diff >= 2:
            base = min(base + 5, 35)
    elif won is False:
        surprise = expected_win  # 1 if expected to win, 0 if expected to lose
        base = int(round(-surprise * 40))
        # Penalty for big losses
        if goal_diff >= 3:
            base = max(base - 10, -40)
        elif goal_diff >= 2:
            base = max(base - 5, -35)
    else:  # draw
        if expected_win > 0.5:
            base = int(round(-(expected_win - 0.5) * 30))  # disappointing draw
        else:
            base = int(round((0.5 - expected_win) * 30))   # creditable draw
    
    return {
        'elo_adjustment': base,
        'expected_win_prob': round(expected_win, 3),
        'surprise_factor': round(abs(base) / 40, 3)
    }


def load_elo() -> Dict[str, int]:
    """Load ELO ratings for adjustment calculation"""
    if not ELO_FILE.exists():
        return {}
    with open(ELO_FILE) as f:
        data = json.load(f)
    return {team: info['elo'] for team, info in data.get('ratings', {}).items()}


def load_friendlies() -> dict:
    """Load friendly matches data"""
    if not FRIENDLY_FILE.exists():
        return {"matches": []}
    with open(FRIENDLY_FILE) as f:
        return json.load(f)


def save_friendlies(data: dict):
    """Save friendly matches data"""
    data['last_update'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
    with open(FRIENDLY_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def compute_form_adjustments(elo: dict, matches: list, 
                              window_days: int = 21,
                              weight_decay: float = 0.9) -> dict:
    """
    Compute per-team recent form adjustments from friendly matches.
    
    Returns:
      {team_name: {'adjustment': int, 'matches_played': int, 'details': [...]}}
    
    Weight decay: matches older than 7 days are weighted less.
    Final adjustment = Σ(per_match_adj × weight) / Σ(weight)
    """
    now = datetime.now(timezone.utc)
    team_stats = {}
    
    for m in matches:
        if m.get('score_a') is None or m.get('score_b') is None:
            continue  # skip TBD matches
        
        team_a = m['team_a']
        team_b = m['team_b']
        score_a = m['score_a']
        score_b = m['score_b']
        is_neutral = m.get('neutral', True)
        
        elo_a = elo.get(team_a, 1700)
        elo_b = elo.get(team_b, 1700)
        
        home_adv = 0 if is_neutral else 60
        expected_a = elo_expected(elo_a, elo_b, home_adv)
        actual_diff_a = score_a - score_b
        
        # Time decay weight
        try:
            match_date = datetime.fromisoformat(m['date'])
            days_ago = (now - match_date).days
        except:
            days_ago = 7
        weight = weight_decay ** (days_ago / 7)
        
        # Compute adjustment for team A
        adj_a = result_to_adjustment(expected_a, actual_diff_a, not is_neutral)
        # Compute adjustment for team B (mirror)
        expected_b = 1.0 - expected_a
        adj_b = result_to_adjustment(expected_b, -actual_diff_a, is_neutral)
        
        for team, adj, score_for, score_against, opp, date in [
            (team_a, adj_a, score_a, score_b, team_b, m['date']),
            (team_b, adj_b, score_b, score_a, team_a, m['date']),
        ]:
            if team not in team_stats:
                team_stats[team] = {'weighted_sum': 0.0, 'weight_sum': 0.0, 
                                     'matches': [], 'raw_adjustments': []}
            
            team_stats[team]['weighted_sum'] += adj['elo_adjustment'] * weight
            team_stats[team]['weight_sum'] += weight
            team_stats[team]['raw_adjustments'].append(adj['elo_adjustment'])
            team_stats[team]['matches'].append({
                'date': date,
                'opponent': opp,
                'score': f"{score_for}-{score_against}",
                'adj': adj['elo_adjustment'],
                'weight': round(weight, 3)
            })
    
    result = {}
    for team, stats in team_stats.items():
        if stats['weight_sum'] > 0:
            raw_avg = sum(stats['raw_adjustments']) / len(stats['raw_adjustments'])
            weighted_avg = stats['weighted_sum'] / stats['weight_sum']
            # Blend raw and weighted (avoid over-weighting single recent match)
            final = int(round(0.7 * weighted_avg + 0.3 * raw_avg))
            result[team] = {
                'adjustment': final,
                'matches_played': len(stats['matches']),
                'details': sorted(stats['matches'], key=lambda x: x['date'], reverse=True)
            }
    
    return result


def cmd_add(args: List[str]):
    """Add a match from JSON string or interactively"""
    data = load_friendlies()
    
    if not args:
        print("Usage: fetch_friendlies.py --add '<json_match>'", file=sys.stderr)
        print('Example: {"team_a":"France","team_b":"Ivory Coast","score_a":1,"score_b":2,"date":"2026-06-04"}', file=sys.stderr)
        return 1
    
    try:
        match = json.loads(' '.join(args))
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}", file=sys.stderr)
        return 1
    
    required = ['team_a', 'team_b', 'date']
    for field in required:
        if field not in match:
            print(f"Missing required field: {field}", file=sys.stderr)
            return 1
    
    # Set defaults
    match.setdefault('score_a', None)
    match.setdefault('score_b', None)
    match.setdefault('neutral', True)
    match.setdefault('notes', '')
    match.setdefault('source', 'manual')
    
    data['matches'].append(match)
    save_friendlies(data)
    
    score_str = f"{match['score_a']}-{match['score_b']}" if match['score_a'] is not None else "TBD"
    print(f"✅ Added: {match['team_a']} {score_str} {match['team_b']} ({match['date']})")
    return 0


def cmd_list():
    """List all recorded matches"""
    data = load_friendlies()
    matches = data['matches']
    
    print(f"📋 {len(matches)} friendly matches recorded")
    print(f"🕐 Last update: {data.get('last_update', 'unknown')}")
    print()
    
    # Sort by date desc
    for m in sorted(matches, key=lambda x: x['date'], reverse=True):
        score = f"{m.get('score_a', '?')}-{m.get('score_b', '?')}" if m.get('score_a') is not None else "TBD"
        venue = m.get('venue', '')
        print(f"  {m['date']}  {m['team_a']} {score:>5} {m['team_b']:20s}  {venue}")
    return 0


def cmd_pending():
    """Show matches with TBD results"""
    data = load_friendlies()
    pending = [m for m in data['matches'] if m.get('score_a') is None]
    
    if not pending:
        print("✅ No pending matches — all results confirmed.")
        return 0
    
    print(f"⚠️ {len(pending)} matches with TBD results:")
    for m in sorted(pending, key=lambda x: x['date'], reverse=True):
        print(f"  {m['date']}  {m['team_a']} vs {m['team_b']}  ({m.get('venue', 'TBD')})")
    return len(pending)


def cmd_compute_form():
    """Compute recent form adjustments from friendly matches"""
    elo = load_elo()
    data = load_friendlies()
    matches = [m for m in data['matches'] if m.get('score_a') is not None]
    
    if not matches:
        print("⚠️ No completed matches to compute form from.")
        return 1
    
    print(f"📊 Computing form from {len(matches)} completed matches")
    print(f"📅 Match window: {data.get('match_window_days', 21)} days")
    print()
    
    form = compute_form_adjustments(elo, matches, 
                                     window_days=data.get('match_window_days', 21),
                                     weight_decay=data.get('weight_decay', 0.9))
    
    # Sort by |adjustment| desc
    sorted_teams = sorted(form.items(), key=lambda x: abs(x[1]['adjustment']), reverse=True)
    
    print(f"{'Team':20s} {'Adj':>5} {'#M':>3}  {'Recent Results'}")
    print("-" * 70)
    for team, stats in sorted_teams:
        adj = stats['adjustment']
        n = stats['matches_played']
        results = ', '.join(f"{d['opponent']}({d['score']})" for d in stats['details'][:3])
        flag = '🟢' if adj > 5 else '🔴' if adj < -5 else '⚪'
        print(f"{flag} {team:18s} {adj:+4d}  {n:>2}  {results}")
    
    print()
    print(f"🏆 Top positive: {max(form.items(), key=lambda x: x[1]['adjustment'])}")
    print(f"📉 Top negative: {min(form.items(), key=lambda x: x[1]['adjustment'])}")
    
    # Output JSON for integration
    output = {
        'computed_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00'),
        'teams': {team: stats['adjustment'] for team, stats in form.items()}
    }
    out_path = DATA_DIR / 'friendly_form_adjustments.json'
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n💾 Saved adjustments to {out_path}")
    
    return 0


def main():
    if '--add' in sys.argv:
        idx = sys.argv.index('--add')
        return cmd_add(sys.argv[idx+1:])
    elif '--list' in sys.argv:
        return cmd_list()
    elif '--pending' in sys.argv:
        return cmd_pending()
    elif '--compute-form' in sys.argv:
        return cmd_compute_form()
    else:
        print(__doc__)
        return 0


if __name__ == '__main__':
    sys.exit(main())
