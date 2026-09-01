#!/usr/bin/env python3
"""
WC2026 比赛结果采集 — v1.0
从 stdin/JSON 文件接收比赛结果，保存并交叉比对预测准确率。

Usage:
  python3.11 scripts/collect_results.py --date 2026-06-12 --results results.json
  python3.11 scripts/collect_results.py --yesterday --results results.json
  python3.11 scripts/collect_results.py --date 2026-06-12 --manual '[
    {"team_a":"Mexico","team_b":"South Africa","score_a":3,"score_b":1}
  ]'
  python3.11 scripts/collect_results.py --check   # 查看哪些日期缺结果

Input format (results.json or --manual JSON):
  [
    {"team_a": "Mexico", "team_b": "South Africa", "score_a": 3, "score_b": 1},
    ...
  ]
  Team names are fuzzy-matched against schedule canonical names.
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

from wc2026_predict import _get_schedule, _find_team_canonical, ALL_TEAMS

DATA_DIR = os.path.join(PROJECT_DIR, 'data')
RESULTS_PATH = os.path.join(DATA_DIR, 'wc2026_results.json')
ACCURACY_PATH = os.path.join(DATA_DIR, 'prediction_accuracy.json')
HISTORY_PATH = os.path.join(DATA_DIR, 'prediction_history.jsonl')

# Name mapping for common ESPN/FIFA variants
NAME_MAP = {
    'korea republic': 'South Korea',
    'korea': 'South Korea',
    'south korea': 'South Korea',
    'usa': 'United States',
    'united states of america': 'United States',
    'us': 'United States',
    'czechia': 'Czech Republic',
    'czech': 'Czech Republic',
    'bosnia': 'Bosnia and Herzegovina',
    'bih': 'Bosnia and Herzegovina',
    'bosnia-herzegovina': 'Bosnia and Herzegovina',
    "cote d'ivoire": 'Ivory Coast',
    'cote divoire': 'Ivory Coast',
    'cape verde': 'Cape Verde',
    'cabo verde': 'Cape Verde',
    'turkiye': 'Turkey',
    'dr congo': 'DR Congo',
    'congo dr': 'DR Congo',
    'democratic republic of congo': 'DR Congo',
    'curacao': 'Curacao',
    'curaçao': 'Curacao',
    'new zealand': 'New Zealand',
    'nz': 'New Zealand',
    'saudi': 'Saudi Arabia',
    'ksa': 'Saudi Arabia',
}


def canonical_team(name):
    """Resolve a team name to canonical form."""
    name_lower = name.strip().lower()
    # Check name map
    if name_lower in NAME_MAP:
        return NAME_MAP[name_lower]
    # Try fuzzy match via wc2026_predict
    result = _find_team_canonical(name, ALL_TEAMS)
    return result


def load_existing_results():
    """Load existing results file or return empty dict."""
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH) as f:
            return json.load(f)
    return {'matches': []}


def save_results(data):
    """Save results to file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RESULTS_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_prediction_history():
    """Load prediction history as list of dicts."""
    if not os.path.exists(HISTORY_PATH):
        return []
    records = []
    with open(HISTORY_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def match_prediction_to_result(result, predictions):
    """Find the prediction record matching a result."""
    ta = result['team_a']
    tb = result['team_b']
    rid = result.get('match_id')

    for p in predictions:
        # Match by match_id first (most reliable)
        sched = p.get('schedule', {})
        if rid and sched.get('match_id') == rid:
            return p
        # Match by team names
        if (p.get('team_a') == ta and p.get('team_b') == tb) or \
           (p.get('team_a') == tb and p.get('team_b') == ta):
            return p
    return None


def compute_accuracy(results_data, predictions):
    """Compute prediction accuracy from results and predictions."""
    total = 0
    correct = 0
    brier_sum = 0

    for r in results_data['matches']:
        if r.get('status') != 'completed':
            continue
        p = match_prediction_to_result(r, predictions)
        if not p:
            continue

        total += 1
        score_a = r['score_a']
        score_b = r['score_b']

        # Determine actual outcome
        if score_a > score_b:
            actual = 'home_win'
        elif score_a < score_b:
            actual = 'away_win'
        else:
            actual = 'draw'

        # Determine predicted outcome
        pred = p.get('prediction', {})
        home_pct = pred.get('team_a_win', 0) / 100
        draw_pct = pred.get('draw', 0) / 100
        away_pct = pred.get('team_b_win', 0) / 100

        # Accuracy: did we predict the right outcome?
        if actual == 'home_win' and home_pct > max(draw_pct, away_pct):
            correct += 1
        elif actual == 'away_win' and away_pct > max(home_pct, draw_pct):
            correct += 1
        elif actual == 'draw' and draw_pct > max(home_pct, away_pct):
            correct += 1

        # Brier score
        if actual == 'home_win':
            brier_sum += (1 - home_pct) ** 2 + (0 - draw_pct) ** 2 + (0 - away_pct) ** 2
        elif actual == 'away_win':
            brier_sum += (0 - home_pct) ** 2 + (0 - draw_pct) ** 2 + (1 - away_pct) ** 2
        else:
            brier_sum += (0 - home_pct) ** 2 + (1 - draw_pct) ** 2 + (0 - away_pct) ** 2

    accuracy = correct / total if total > 0 else 0
    brier = brier_sum / total if total > 0 else 0

    return {
        'total_predictions': total,
        'correct_outcomes': correct,
        'accuracy': round(accuracy, 4),
        'brier_score': round(brier, 4),
        'updated': datetime.now().isoformat(),
    }


def add_results(date_str, raw_results):
    """Add results for a date, with fuzzy team matching."""
    sched = _get_schedule()
    existing = load_existing_results()

    # Get scheduled matches for this date
    scheduled = [m for m in sched['matches'] if m['date_beijing'] == date_str]
    if not scheduled:
        print(f"⚠️ {date_str}: 赛程中无此日期的比赛")

    added = 0
    for rr in raw_results:
        ta_raw = rr.get('team_a', '')
        tb_raw = rr.get('team_b', '')
        score_a = rr.get('score_a')
        score_b = rr.get('score_b')

        if score_a is None or score_b is None:
            print(f"⚠️ 跳过 (缺比分): {ta_raw} vs {tb_raw}")
            continue

        # Resolve team names
        ta = canonical_team(ta_raw)
        tb = canonical_team(tb_raw)

        if not ta or not tb:
            print(f"⚠️ 跳过 (无法识别队名): {ta_raw} → {ta}, {tb_raw} → {tb}")
            continue

        # Find match_id from schedule
        match_id = None
        for m in scheduled:
            if (m['team_a'] == ta and m['team_b'] == tb) or \
               (m['team_a'] == tb and m['team_b'] == ta):
                match_id = m['match_id']
                break

        # Check for duplicates
        dup = False
        for existing_m in existing['matches']:
            if existing_m.get('match_id') == match_id and existing_m.get('status') == 'completed':
                dup = True
                break

        if dup:
            print(f"  ⏭️ 已有结果: {ta} vs {tb}")
            continue

        entry = {
            'match_id': match_id,
            'date_beijing': date_str,
            'team_a': ta,
            'team_b': tb,
            'score_a': int(score_a),
            'score_b': int(score_b),
            'stage': 'group_stage',
            'status': 'completed',
            'source': rr.get('source', 'manual'),
            'collected_at': datetime.now().isoformat(),
        }
        existing['matches'].append(entry)
        print(f"  ✅ {ta} {score_a}-{score_b} {tb} (Match #{match_id})")
        added += 1

    if added > 0:
        save_results(existing)
        print(f"\n💾 已保存 {added} 场比赛结果 → {RESULTS_PATH}")

        # Update accuracy
        predictions = load_prediction_history()
        acc = compute_accuracy(existing, predictions)
        with open(ACCURACY_PATH, 'w') as f:
            json.dump(acc, f, indent=2)
        print(f"📊 预测准确率: {acc['accuracy']*100:.1f}% ({acc['correct_outcomes']}/{acc['total_predictions']})")
        print(f"📊 Brier Score: {acc['brier_score']:.4f}")
    else:
        print("ℹ️ 无新结果添加")
    return added


def check_missing_dates():
    """List dates with scheduled matches that have no results."""
    sched = _get_schedule()
    existing = load_existing_results()

    # All unique dates
    all_dates = sorted(set(m['date_beijing'] for m in sched['matches']))
    completed_dates = set()
    for r in existing['matches']:
        if r.get('status') == 'completed':
            completed_dates.add(r.get('date_beijing', ''))

    today = datetime.now().strftime('%Y-%m-%d')
    print(f"📅 赛程覆盖: {all_dates[0]} ~ {all_dates[-1]} (今天: {today})")
    print()

    missing = []
    for d in all_dates:
        if d >= today:
            continue  # future matches
        if d not in completed_dates:
            ms = [m for m in sched['matches'] if m['date_beijing'] == d]
            missing.append((d, ms))

    if missing:
        print(f"⚠️ {len(missing)} 个历史日期缺结果:")
        for d, ms in missing:
            teams = ', '.join(f"{m['team_a']}vs{m['team_b']}" for m in ms)
            print(f"  {d}: {teams}")
    else:
        print("✅ 所有历史比赛结果已采集")


def main():
    date_str = None
    results_data = None

    if '--date' in sys.argv:
        idx = sys.argv.index('--date')
        if idx + 1 < len(sys.argv):
            date_str = sys.argv[idx + 1]
    elif '--yesterday' in sys.argv:
        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    elif '--check' in sys.argv:
        check_missing_dates()
        return

    # Load results from --results file or --manual JSON
    if '--results' in sys.argv:
        idx = sys.argv.index('--results')
        if idx + 1 < len(sys.argv):
            with open(sys.argv[idx + 1]) as f:
                results_data = json.load(f)
    elif '--manual' in sys.argv:
        idx = sys.argv.index('--manual')
        if idx + 1 < len(sys.argv):
            results_data = json.loads(sys.argv[idx + 1])
    else:
        # Try reading from stdin
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                results_data = json.loads(stdin_data)
        except (json.JSONDecodeError, IOError):
            pass

    if not date_str:
        print("Usage: python3.11 scripts/collect_results.py --date 2026-06-12 --results results.json")
        print("       python3.11 scripts/collect_results.py --yesterday --manual '[{...}]'")
        print("       python3.11 scripts/collect_results.py --check")
        sys.exit(1)

    if not results_data:
        print(f"⚠️ {date_str}: 未提供结果数据 (--results / --manual / stdin)")
        print("   提示: 使用 --check 查看哪些日期缺结果")
        sys.exit(0)

    if not isinstance(results_data, list):
        print("❌ 结果数据必须是 JSON 数组 [{team_a, team_b, score_a, score_b}, ...]")
        sys.exit(1)

    print(f"📥 采集比赛结果: {date_str}")
    print(f"   原始记录: {len(results_data)} 条")
    print()

    n = add_results(date_str, results_data)
    if n == 0 and results_data:
        sys.exit(2)  # signal no results added (for pipeline)
    sys.exit(0)


if __name__ == '__main__':
    main()
