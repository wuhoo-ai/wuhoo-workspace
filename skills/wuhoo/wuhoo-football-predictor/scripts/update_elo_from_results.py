#!/usr/bin/env python3
"""
WC2026 ELO 结果更新 — v1.0
从 wc2026_results.json 读取比赛结果，用标准 ELO 公式更新 elo_ratings.json。

Usage:
  python3.11 scripts/update_elo_from_results.py              # 处理所有未应用的比赛
  python3.11 scripts/update_elo_from_results.py --date 2026-06-12  # 仅处理指定日期
  python3.11 scripts/update_elo_from_results.py --dry-run     # 预览，不写文件

ELO Formula:
  expected = 1 / (1 + 10^((elo_b - elo_a) / 400))
  new_elo = old_elo + K * (actual - expected)
  K = 60 (World Cup group stage weight)
"""

import sys
import os
import json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

DATA_DIR = os.path.join(PROJECT_DIR, 'data')
ELO_PATH = os.path.join(DATA_DIR, 'elo_ratings.json')
RESULTS_PATH = os.path.join(DATA_DIR, 'wc2026_results.json')

K_FACTOR = 60  # World Cup group stage weight


def load_elo():
    """Load ELO ratings with source metadata."""
    with open(ELO_PATH) as f:
        return json.load(f)


def save_elo(data):
    """Save ELO ratings."""
    with open(ELO_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_results():
    """Load match results."""
    if not os.path.exists(RESULTS_PATH):
        return {'matches': []}
    with open(RESULTS_PATH) as f:
        return json.load(f)


def expected_score(elo_a, elo_b):
    """Expected score for team A (0-1 scale)."""
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


def update_elo_from_match(team_a, team_b, score_a, score_b, elo_data, applied_matches):
    """Update ELO for one match. Returns (new_elo_a, new_elo_b, delta_a, delta_b)."""
    ratings = elo_data.get('ratings', {})
    entry_a = ratings.get(team_a, {'elo': 1700})
    entry_b = ratings.get(team_b, {'elo': 1700})
    elo_a = entry_a if isinstance(entry_a, int) else entry_a.get('elo', 1700)
    elo_b = entry_b if isinstance(entry_b, int) else entry_b.get('elo', 1700)

    # Determine actual result (1=win, 0.5=draw, 0=loss for team_a)
    if score_a > score_b:
        actual_a = 1.0
    elif score_a < score_b:
        actual_a = 0.0
    else:
        actual_a = 0.5

    expected_a = expected_score(elo_a, elo_b)
    expected_b = 1.0 - expected_a

    # Goal difference multiplier (max 2x for 4+ goal difference)
    goal_diff = abs(score_a - score_b)
    gd_multiplier = min(2.0, 1.0 + (goal_diff - 1) * 0.25) if goal_diff > 1 else 1.0

    delta_a = K_FACTOR * gd_multiplier * (actual_a - expected_a)
    delta_b = K_FACTOR * gd_multiplier * ((1.0 - actual_a) - expected_b)

    new_elo_a = elo_a + round(delta_a)
    new_elo_b = elo_b + round(delta_b)

    # Update ratings - handle both flat int and nested dict formats
    if isinstance(ratings.get(team_a), dict):
        ratings[team_a]['elo'] = new_elo_a
    else:
        ratings[team_a] = new_elo_a
    if isinstance(ratings.get(team_b), dict):
        ratings[team_b]['elo'] = new_elo_b
    else:
        ratings[team_b] = new_elo_b

    applied_matches.append({
        'team_a': team_a,
        'team_b': team_b,
        'score': f"{score_a}-{score_b}",
        'elo_a': {'old': elo_a, 'new': new_elo_a, 'delta': round(delta_a)},
        'elo_b': {'old': elo_b, 'new': new_elo_b, 'delta': round(delta_b)},
        'k_used': K_FACTOR,
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

    # Load data
    elo_data = load_elo()
    results = load_results()

    if not results.get('matches'):
        print("ℹ️ 无比赛结果数据。")
        return

    # Determine already-applied matches
    applied_set = set()
    for entry in elo_data.get('applied_results', []):
        applied_set.add((entry.get('team_a'), entry.get('team_b'), entry.get('date', '')))

    # Filter unapplied matches
    pending = []
    for r in results['matches']:
        if r.get('status') != 'completed':
            continue
        if date_filter and r.get('date_beijing') != date_filter:
            continue
        key = (r['team_a'], r['team_b'], r.get('date_beijing', ''))
        if key not in applied_set:
            pending.append(r)
        else:
            # Also check reverse
            key2 = (r['team_b'], r['team_a'], r.get('date_beijing', ''))
            if key2 not in applied_set:
                pending.append(r)

    if not pending:
        print("ℹ️ 没有新的比赛结果需要更新 ELO。")
        return

    print(f"📊 待处理: {len(pending)} 场比赛")
    if dry_run:
        print("🔍 DRY-RUN 模式 — 不写入文件")
    print()

    applied_matches = list(elo_data.get('applied_results', []))

    for r in pending:
        ta = r['team_a']
        tb = r['team_b']
        sa = r['score_a']
        sb = r['score_b']

        new_a, new_b, da, db = update_elo_from_match(
            ta, tb, sa, sb, elo_data, applied_matches
        )

        arrow_a = '⬆️' if da > 0 else '⬇️' if da < 0 else '➡️'
        arrow_b = '⬆️' if db > 0 else '⬇️' if db < 0 else '➡️'
        print(f"  {arrow_a} {ta}: {new_a - round(da)} → {new_a} ({int(da):+d})")
        print(f"  {arrow_b} {tb}: {new_b - round(db)} → {new_b} ({int(db):+d})")
        print(f"     {ta} {sa}-{sb} {tb} | K={K_FACTOR}")
        print()

    # Update metadata
    elo_data['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    elo_data['update_method'] = 'match_result'
    elo_data['applied_results'] = applied_matches

    if not dry_run:
        save_elo(elo_data)
        print(f"💾 ELO 已保存: {ELO_PATH}")
        print(f"   共更新 {len(pending)} 场比赛 | 最后更新: {elo_data['last_updated']}")
    else:
        print("🔍 DRY-RUN 完成 — 未写入文件。")


if __name__ == '__main__':
    main()
