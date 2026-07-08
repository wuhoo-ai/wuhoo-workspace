#!/usr/bin/env python3
"""WC2026 Knockout Seed Module — v1.0

Reads group stage results, determines R32 seedings, fills knockout_schedule.json.
Only needed once after group stage completes. Subsequent days use filled schedule.

Usage:
  python3.11 scripts/seed_knockout.py
  python3.11 scripts/seed_knockout.py --dry-run
"""

import json, os, sys
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, 'data')

# --- Name aliases mapping (FIFA → our standard names) ---
TEAM_ALIASES = {
    'Cabo Verde': 'Cape Verde',
    'Côte d\'Ivoire': 'Ivory Coast',
    'Congo DR': 'DR Congo',
    'USA': 'United States',
    'Korea Republic': 'South Korea',
    'Czechia': 'Czech Republic',
}

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def compute_group_standings(results_file, schedule_file):
    """Compute final group standings from completed results."""
    from datetime import date
    
    results = load_json(results_file)
    schedule = load_json(schedule_file)
    
    # Build group table
    groups = defaultdict(lambda: defaultdict(lambda: {'pts': 0, 'gf': 0, 'ga': 0, 'gd': 0}))
    
    # Find all completed group stage matches
    sched_map = {m['match_id']: m for m in schedule['matches']}
    
    for m in results['matches']:
        mid = m['match_id']
        if mid > 72:  # Only group stage
            continue
        sched = sched_map.get(mid, {})
        group = sched.get('group', '')
        if not group:
            continue
        
        team_a = m.get('team_a', '')
        team_b = m.get('team_b', '')
        score_a = m.get('score_a', 0) or 0
        score_b = m.get('score_b', 0) or 0
        
        # Points
        if score_a > score_b:
            groups[group][team_a]['pts'] += 3
        elif score_b > score_a:
            groups[group][team_b]['pts'] += 3
        else:
            groups[group][team_a]['pts'] += 1
            groups[group][team_b]['pts'] += 1
        
        # Goal stats
        groups[group][team_a]['gf'] += score_a
        groups[group][team_a]['ga'] += score_b
        groups[group][team_b]['gf'] += score_b
        groups[group][team_b]['ga'] += score_a
    
    # Compute GD and sort
    standings = {}
    for group, teams in groups.items():
        for team, stats in teams.items():
            stats['gd'] = stats['gf'] - stats['ga']
        
        sorted_teams = sorted(teams.items(), 
            key=lambda x: (-x[1]['pts'], -x[1]['gd'], -x[1]['gf']))
        
        standings[group] = [(t, s) for t, s in sorted_teams]
    
    return standings

def get_r32_seedings(standings):
    """Map group standings to R32 bracket slots per FIFA bracket rules.
    
    Based on bracket-2026.md slot mapping:
      1: A2 vs B2
      2: C1 vs F2
      3: E1 vs 3rd(A/B/C/D/F)
      4: F1 vs C2
      5: E2 vs I2
      6: I1 vs 3rd(C/D/F/G/H)
      7: A1 vs 3rd(C/E/F/H/I)
      8: L1 vs 3rd(E/H/I/J/K)
      9: G1 vs 3rd(A/E/H/I/J)
     10: D1 vs 3rd(B/E/F/I/J)
     11: H1 vs J2
     12: K2 vs L2
     13: B1 vs 3rd(E/F/G/I/J)
     14: D2 vs G2
     15: J1 vs H2
     16: K1 vs 3rd(D/E/I/J/L)
    """
    # Extract teams by position
    winners = {g: standings[g][0][0] for g in sorted(standings.keys())}
    runners_up = {g: standings[g][1][0] for g in sorted(standings.keys())}
    thirds = []
    for g in sorted(standings.keys()):
        if len(standings[g]) > 2:
            team, stats = standings[g][2]
            thirds.append({'group': g, 'team': team, 'pts': stats['pts'], 'gd': stats['gd']})
    
    # Sort thirds by pts, gd (best 8 advance)
    thirds.sort(key=lambda x: (-x['pts'], -x['gd']))
    advancing_thirds = thirds[:8]
    advancing_third_teams = {t['team']: t for t in advancing_thirds}
    
    win_str = ', '.join('{}:{}'.format(g, t) for g, t in sorted(winners.items()))
    ru_str = ', '.join('{}:{}'.format(g, t) for g, t in sorted(runners_up.items()))
    th_str = ', '.join('{}({},{})'.format(t['team'], t['group'], t['pts']) for t in advancing_thirds)
    print(f"Group Winners (12): {win_str}")
    print(f"Runners-up (12): {ru_str}")
    print(f"Advancing 3rd-place (8): {th_str}")
    
    # R32 slot assignments (from bracket-2026.md)
    slot_map = {
        1: ('A2', 'B2'),
        2: ('C1', 'F2'),
        3: ('E1', '3rd(A,B,C,D,F)'),
        4: ('F1', 'C2'),
        5: ('E2', 'I2'),
        6: ('I1', '3rd(C,D,F,G,H)'),
        7: ('A1', '3rd(C,E,F,H,I)'),
        8: ('L1', '3rd(E,H,I,J,K)'),
        9: ('G1', '3rd(A,E,H,I,J)'),
        10: ('D1', '3rd(B,E,F,I,J)'),
        11: ('H1', 'J2'),
        12: ('K2', 'L2'),
        13: ('B1', '3rd(E,F,G,I,J)'),
        14: ('D2', 'G2'),
        15: ('J1', 'H2'),
        16: ('K1', '3rd(D,E,I,J,L)'),
    }
    
    def resolve_team(slot_expr, used_teams):
        """Resolve a slot expression to actual team name."""
        if slot_expr.startswith('3rd('):
            # Parse eligible groups
            groups_str = slot_expr[4:-1]
            eligible_groups = [g.strip() for g in groups_str.split(',')]
            # Find best eligible 3rd-place team that hasn't been used yet
            for t in advancing_thirds:
                if t['group'] in eligible_groups and t['team'] not in used_teams:
                    used_teams.add(t['team'])
                    return t['team']
            # Fallback: use best available unused 3rd-place team
            for t in advancing_thirds:
                if t['team'] not in used_teams:
                    used_teams.add(t['team'])
                    return t['team']
            return None
        else:
            group, pos = slot_expr[0], slot_expr[1]
            if pos == '1':
                return winners.get(group)
            elif pos == '2':
                return runners_up.get(group)
        return None
    
    # Resolve all slots (process 3rd-place slots from most constrained first)
    used_third_teams = set()
    
    # Sort slots by constraint (fewer eligible groups = more constrained)
    third_slots = []
    direct_slots = []
    for slot_id, (team_a_expr, team_b_expr) in slot_map.items():
        if team_a_expr.startswith('3rd('):
            third_slots.append((slot_id, 'a', team_a_expr, team_b_expr))
        elif team_b_expr.startswith('3rd('):
            third_slots.append((slot_id, 'b', team_a_expr, team_b_expr))
        else:
            direct_slots.append((slot_id, team_a_expr, team_b_expr))
    
    # Sort third-place slots by number of eligible groups (ascending = most constrained first)
    third_slots.sort(key=lambda x: len(x[2 if x[1]=='a' else 3][4:-1].split(',')))
    
    seedings = {}
    
    # First assign direct slots
    for slot_id, team_a_expr, team_b_expr in direct_slots:
        team_a = resolve_team(team_a_expr, set())
        team_b = resolve_team(team_b_expr, set())
        seedings[slot_id] = {'team_a': team_a, 'team_b': team_b, 'slot_a': team_a_expr, 'slot_b': team_b_expr}
    
    # Then assign third-place slots
    for slot_id, pos, team_a_expr, team_b_expr in third_slots:
        team_a = resolve_team(team_a_expr, used_third_teams)
        team_b = resolve_team(team_b_expr, used_third_teams)
        seedings[slot_id] = {'team_a': team_a, 'team_b': team_b, 'slot_a': team_a_expr, 'slot_b': team_b_expr}
    
    return seedings, winners, runners_up, advancing_thirds


def fill_knockout_schedule(knockout_schedule_path, seedings):
    """Fill team names into knockout_schedule.json based on seedings."""
    schedule = load_json(knockout_schedule_path)
    
    r32_matches = schedule['stages']['R32']['matches']
    for match in r32_matches:
        slot = match.get('slot')
        if slot and slot in seedings:
            match['team_a'] = seedings[slot]['team_a']
            match['team_b'] = seedings[slot]['team_b']
    
    schedule['_seeded'] = True
    schedule['_seeded_at'] = __import__('datetime').datetime.now().isoformat()
    
    return schedule


def main():
    dry_run = '--dry-run' in sys.argv
    
    results_file = os.path.join(DATA_DIR, 'wc2026_results.json')
    schedule_file = os.path.join(DATA_DIR, 'wc2026_schedule.json')
    knockout_file = os.path.join(DATA_DIR, 'knockout_schedule.json')
    
    # 1. Compute standings
    print("=== WC2026 Knockout Seeding ===\n")
    standings = compute_group_standings(results_file, schedule_file)
    
    print("Group Standings:")
    for g in sorted(standings.keys()):
        teams = standings[g]
        print(f"  Group {g}: ", end="")
        for i, (team, stats) in enumerate(teams):
            print(f"{'🥇' if i==0 else '🥈' if i==1 else '  '} {team}({stats['pts']}pts, GD{stats['gd']:+d})", end="  ")
        print()
    
    # 2. Get seedings
    print()
    seedings, winners, runners_up, thirds = get_r32_seedings(standings)
    
    # 3. Show R32 bracket
    print(f"\n=== R32 Bracket ===")
    schedule = load_json(knockout_file)
    r32_matches = schedule['stages']['R32']['matches']
    
    for match in sorted(r32_matches, key=lambda m: m['match_id']):
        slot = match.get('slot')
        team_a = seedings.get(slot, {}).get('team_a', match.get('team_a'))
        team_b = seedings.get(slot, {}).get('team_b', match.get('team_b'))
        print(f"  M{match['match_id']} [{match['date_beijing']}] {team_a} vs {team_b} @ {match['venue_city']}")
    
    # 4. Save filled schedule (only if not already FIFA-official)
    if not dry_run:
        existing_source = schedule.get('_source', '')
        if 'FIFA' in existing_source:
            print(f"\n⏭️ 跳过写回 — 已包含 FIFA 官方对阵 (source={existing_source})")
        else:
            filled = fill_knockout_schedule(knockout_file, seedings)
            save_json(knockout_file, filled)
            print(f"\n✅ Saved seeded knockout schedule to {knockout_file}")
    else:
        print(f"\n🔍 Dry run — no files modified")
    
    # 5. Save seedings data for bracket simulator
    seed_data = {
        'generated': __import__('datetime').datetime.now().isoformat(),
        'winners': winners,
        'runners_up': runners_up,
        'advancing_thirds': [{'team': t['team'], 'group': t['group'], 'pts': t['pts'], 'gd': t['gd']} for t in thirds],
        'seedings': seedings,
    }
    
    seed_path = os.path.join(DATA_DIR, 'knockout_seedings.json')
    if not dry_run:
        save_json(seed_path, seed_data)
        print(f"✅ Saved seedings data to {seed_path}")
    
    return standings, seedings


if __name__ == '__main__':
    main()
