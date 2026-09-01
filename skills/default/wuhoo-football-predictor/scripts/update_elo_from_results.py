#!/usr/bin/env python3
"""
WC2026 ELO 结果更新 — v5.6
从 wc2026_results.json 读取比赛结果，用标准 ELO 公式更新 elo_ratings.json。

v5.6 新增: MD3 锁定出线球队非对称 ELO 调整
  - 锁定队赢球 → 全额 K=60（轮换都能赢=板凳深度强）
  - 锁定队平/输 → K=30（轮换导致，不反映真实实力）

Usage:
  python3.11 scripts/update_elo_from_results.py
  python3.11 scripts/update_elo_from_results.py --dry-run

ELO Formula:
  expected = 1 / (1 + 10^((elo_b - elo_a) / 400))
  new_elo = old_elo + K * (actual - expected)
"""

import sys, os, json
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

DATA_DIR = os.path.join(PROJECT_DIR, 'data')
ELO_PATH = os.path.join(DATA_DIR, 'elo_ratings.json')
RESULTS_PATH = os.path.join(DATA_DIR, 'wc2026_results.json')
SCHEDULE_PATH = os.path.join(DATA_DIR, 'wc2026_schedule.json')

K_FACTOR = 60
K_LOCKED_LOSE = 30  # 锁定队平/输: 降权
K_LOCKED_WIN = 60    # 锁定队赢球: 全额（轮换还能赢=实力更强）


def compute_pre_md3_locked_teams():
    if not os.path.exists(SCHEDULE_PATH) or not os.path.exists(RESULTS_PATH):
        return set()
    with open(SCHEDULE_PATH) as f:
        schedule = json.load(f)
    with open(RESULTS_PATH) as f:
        results = json.load(f)
    groups = defaultdict(lambda: defaultdict(lambda: {'pts': 0, 'gf': 0, 'ga': 0}))
    sched_map = {m['match_id']: m for m in schedule['matches']}
    result_map = {m['match_id']: m for m in results['matches']}
    for mid, m in sched_map.items():
        if mid not in result_map or m.get('matchday', 0) >= 3:
            continue
        group = m.get('group', '')
        if not group:
            continue
        r = result_map[mid]
        a, b = m['team_a'], m['team_b']
        sa, sb = r.get('score_a', 0) or 0, r.get('score_b', 0) or 0
        if sa > sb:
            groups[group][a]['pts'] += 3
        elif sb > sa:
            groups[group][b]['pts'] += 3
        else:
            groups[group][a]['pts'] += 1
            groups[group][b]['pts'] += 1
        groups[group][a]['gf'] += sa; groups[group][a]['ga'] += sb
        groups[group][b]['gf'] += sb; groups[group][b]['ga'] += sa
    locked = set()
    for grp in groups.values():
        st = sorted(grp.items(), key=lambda x: (-x[1]['pts'], -(x[1]['gf']-x[1]['ga'])))
        if len(st) < 3:
            continue
        third = st[2]
        for team, stats in st[:2]:
            pts_lead = stats['pts'] - third[1]['pts']
            gd = stats['gf'] - stats['ga']
            if pts_lead > 3 or (pts_lead == 3 and gd > 5):
                locked.add(team)
    return locked


def load_elo():
    with open(ELO_PATH) as f:
        return json.load(f)


def save_elo(data):
    with open(ELO_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_results():
    if not os.path.exists(RESULTS_PATH):
        return {'matches': []}
    with open(RESULTS_PATH) as f:
        return json.load(f)


def expected_score(elo_a, elo_b):
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


def update_elo_from_match(team_a, team_b, score_a, score_b, elo_data, applied_matches,
                          locked_teams=None, matchday=None):
    if locked_teams is None:
        locked_teams = set()
    ratings = elo_data.get('ratings', {})
    entry_a = ratings.get(team_a, {'elo': 1700})
    entry_b = ratings.get(team_b, {'elo': 1700})
    elo_a = entry_a if isinstance(entry_a, int) else entry_a.get('elo', 1700)
    elo_b = entry_b if isinstance(entry_b, int) else entry_b.get('elo', 1700)

    if score_a > score_b:
        actual_a = 1.0
    elif score_a < score_b:
        actual_a = 0.0
    else:
        actual_a = 0.5

    expected_a = expected_score(elo_a, elo_b)
    expected_b = 1.0 - expected_a
    goal_diff = abs(score_a - score_b)
    gd_multiplier = min(2.0, 1.0 + (goal_diff - 1) * 0.25) if goal_diff > 1 else 1.0

    # v5.6: Asymmetric K for locked teams in MD3
    # Win with reserves → full K. Draw/lose with reserves → reduced K.
    a_locked = team_a in locked_teams and matchday == 3
    b_locked = team_b in locked_teams and matchday == 3
    a_won = score_a > score_b
    b_won = score_a < score_b

    if a_locked:
        k_a = K_LOCKED_WIN if a_won else K_LOCKED_LOSE
    else:
        k_a = K_FACTOR

    if b_locked:
        k_b = K_LOCKED_WIN if b_won else K_LOCKED_LOSE
    else:
        k_b = K_FACTOR

    delta_a = k_a * gd_multiplier * (actual_a - expected_a)
    delta_b = k_b * gd_multiplier * ((1.0 - actual_a) - expected_b)

    new_elo_a = elo_a + round(delta_a)
    new_elo_b = elo_b + round(delta_b)

    if isinstance(ratings.get(team_a), dict):
        ratings[team_a]['elo'] = new_elo_a
    else:
        ratings[team_a] = new_elo_a
    if isinstance(ratings.get(team_b), dict):
        ratings[team_b]['elo'] = new_elo_b
    else:
        ratings[team_b] = new_elo_b

    applied_matches.append({
        'team_a': team_a, 'team_b': team_b,
        'score': f"{score_a}-{score_b}",
        'elo_a': {'old': elo_a, 'new': new_elo_a, 'delta': round(delta_a)},
        'elo_b': {'old': elo_b, 'new': new_elo_b, 'delta': round(delta_b)},
        'k_a': k_a, 'k_b': k_b,
        'gd_multiplier': round(gd_multiplier, 2),
    })
    return new_elo_a, new_elo_b, delta_a, delta_b


def main():
    dry_run = '--dry-run' in sys.argv
    date_filter = None
    if '--date' in sys.argv:
        idx = sys.argv.index('--date')
        if idx + 1 < len(sys.argv):
            date_filter = sys.argv[idx + 1]

    elo_data = load_elo()
    results = load_results()
    if not results.get('matches'):
        print("ℹ️ 无比赛结果数据。")
        return

    applied_set = set()
    for entry in elo_data.get('applied_results', []):
        # Check by team pair + score (most robust dedup key)
        key1 = (entry.get('team_a'), entry.get('team_b'), entry.get('score', ''))
        key2 = (entry.get('team_b'), entry.get('team_a'), entry.get('score', ''))
        applied_set.add(key1)
        applied_set.add(key2)
        # Also check by team pair + date (legacy)
        if entry.get('date'):
            applied_set.add((entry.get('team_a'), entry.get('team_b'), entry.get('date', '')))

    pending = []
    for r in results['matches']:
        if r.get('status') != 'completed':
            continue
        if date_filter and r.get('date_beijing') != date_filter:
            continue
        score = f"{r.get('score_a','?')}-{r.get('score_b','?')}"
        key_score = (r['team_a'], r['team_b'], score)
        key_date = (r['team_a'], r['team_b'], r.get('date_beijing', ''))
        key_date_rev = (r['team_b'], r['team_a'], r.get('date_beijing', ''))
        if key_score not in applied_set and key_date not in applied_set and key_date_rev not in applied_set:
            pending.append(r)

    if not pending:
        print("ℹ️ 没有新的比赛结果需要更新 ELO。")
        return

    locked_teams = compute_pre_md3_locked_teams()

    print(f"📊 待处理: {len(pending)} 场比赛")
    if locked_teams:
        print(f"🔒 锁定出线: {', '.join(sorted(locked_teams))}")
        print(f"   赢球→K={K_LOCKED_WIN} | 平/输→K={K_LOCKED_LOSE}")
    if dry_run:
        print("🔍 DRY-RUN 模式")
    print()

    applied_matches = list(elo_data.get('applied_results', []))
    sched_map = {}
    if os.path.exists(SCHEDULE_PATH):
        with open(SCHEDULE_PATH) as f:
            sched_map = {m['match_id']: m.get('matchday') for m in json.load(f)['matches']}

    for r in pending:
        ta, tb = r['team_a'], r['team_b']
        sa, sb = r['score_a'], r['score_b']
        md = sched_map.get(r.get('match_id'))

        new_a, new_b, da, db = update_elo_from_match(
            ta, tb, sa, sb, elo_data, applied_matches,
            locked_teams=locked_teams, matchday=md
        )

        a_win = sa > sb
        b_win = sa < sb
        k_a = K_LOCKED_WIN if (ta in locked_teams and md == 3 and a_win) else \
              K_LOCKED_LOSE if (ta in locked_teams and md == 3) else K_FACTOR
        k_b = K_LOCKED_WIN if (tb in locked_teams and md == 3 and b_win) else \
              K_LOCKED_LOSE if (tb in locked_teams and md == 3) else K_FACTOR

        tag_a = ' [🔒赢]' if k_a == K_LOCKED_WIN and ta in locked_teams else \
                ' [🔒↓]' if k_a < K_FACTOR else ''
        tag_b = ' [🔒赢]' if k_b == K_LOCKED_WIN and tb in locked_teams else \
                ' [🔒↓]' if k_b < K_FACTOR else ''

        old_a = new_a - round(da); old_b = new_b - round(db)
        arrow_a = '⬆️' if da > 0 else '⬇️' if da < 0 else '➡️'
        arrow_b = '⬆️' if db > 0 else '⬇️' if db < 0 else '➡️'
        print(f"  {arrow_a} {ta}{tag_a}: {old_a} → {new_a} ({int(da):+d})")
        print(f"  {arrow_b} {tb}{tag_b}: {old_b} → {new_b} ({int(db):+d})")
        print(f"     {ta} {sa}-{sb} {tb} | K_a={k_a} K_b={k_b}")
        print()

    elo_data['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    elo_data['update_method'] = 'match_result_v56'
    elo_data['applied_results'] = applied_matches

    if not dry_run:
        save_elo(elo_data)
        print(f"💾 ELO 已保存 | {len(pending)} 场比赛")
    else:
        print("🔍 DRY-RUN 完成")


if __name__ == '__main__':
    main()
