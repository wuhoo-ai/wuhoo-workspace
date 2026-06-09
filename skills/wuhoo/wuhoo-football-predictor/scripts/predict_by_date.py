#!/usr/bin/env python3
"""
WC2026 按日期批量预测 — v1.0
按北京日期查找赛程中的所有比赛，逐场调用 predict_single_match 并输出报告。

Usage:
  python3.11 scripts/predict_by_date.py --date 2026-06-12   # 指定日期
  python3.11 scripts/predict_by_date.py --tomorrow            # 明天
  python3.11 scripts/predict_by_date.py --today               # 今天
  python3.11 scripts/predict_by_date.py --date 2026-06-12 --news  # 含情感分析

Output:
  - data/daily_predictions/YYYY-MM-DD.md  (markdown report)
  - data/daily_predictions/YYYY-MM-DD.json (JSON, per-match audit)
  - prediction_history.jsonl (appended)
"""

import sys
import os
import json
from datetime import datetime, timedelta, timezone

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, SCRIPT_DIR)

from wc2026_predict import (
    predict_single_match, _get_schedule, _save_prediction_history,
    TEAM_PROFILES
)

DATA_DIR = os.path.join(PROJECT_DIR, 'data')
PREDICTIONS_DIR = os.path.join(DATA_DIR, 'daily_predictions')
HISTORY_PATH = os.path.join(DATA_DIR, 'prediction_history.jsonl')


def format_match_report(match_info, audit):
    """Format a single match prediction as a compact WeChat-friendly message."""
    ta = audit['team_a']
    tb = audit['team_b']
    pa = TEAM_PROFILES.get(ta, {})
    pb = TEAM_PROFILES.get(tb, {})
    na = pa.get('name_cn', ta)
    nb = pb.get('name_cn', tb)
    pred = audit['prediction']
    verdict = audit['verdict']
    eff = audit['effective_elo']
    sched = audit.get('schedule', match_info)

    lines = []
    lines.append(f"⚽ {na} vs {nb}")
    lines.append(f"📅 {sched.get('date_beijing', '?')} {sched.get('time_beijing', '?')} BJT")
    lines.append(f"🏟️ {sched.get('venue', '?')} · Group {sched.get('group', '?')} MD{sched.get('matchday', '?')}")
    lines.append("")
    lines.append(f"📊 ELO: {ta} {eff['team_a']['base']}→{eff['team_a']['effective']} vs "
                 f"{tb} {eff['team_b']['base']}→{eff['team_b']['effective']}")
    lines.append(f"📈 {na}胜 {pred['team_a_win']}% | 平 {pred['draw']}% | {nb}胜 {pred['team_b_win']}%")
    lines.append(f"🎯 最可能比分: {pred['most_likely_score']} "
                 f"(xG {pred['expected_goals_a']:.2f}/{pred['expected_goals_b']:.2f})")
    lines.append(f"🧠 {verdict['result']}（置信度: {verdict['confidence']}）")

    # Key reasoning
    if audit.get('reasoning'):
        for r in audit['reasoning'][:2]:
            lines.append(f"   → {r}")

    lines.append(f"⚠️ 仅供娱乐参考 | 预测时间: {audit.get('generated', '?')[:16]}")
    return '\n'.join(lines)


def predict_by_date(date_str):
    """Predict all matches on a given Beijing date."""
    sched = _get_schedule()
    matches = [m for m in sched['matches'] if m['date_beijing'] == date_str]

    if not matches:
        print(f"✅ {date_str}: 无比赛安排")
        return [], date_str

    results = []
    for m in matches:
        print(f"🔄 预测: {m['team_a']} vs {m['team_b']} (Match #{m['match_id']})...")
        try:
            audit = predict_single_match(
                m['team_a'], m['team_b'],
                venue_name=m.get('venue'),
                enable_news=('--news' in sys.argv),
                knockout=False
            )
            audit['schedule'] = m
            _save_prediction_history(audit)
            results.append({'match': m, 'audit': audit})
            print(f"   ✅ {audit['verdict']['result']}")
        except Exception as e:
            print(f"   ❌ 预测失败: {e}")
            results.append({'match': m, 'audit': None, 'error': str(e)})

    return results, date_str


def save_reports(results, date_str):
    """Save markdown and JSON reports."""
    os.makedirs(PREDICTIONS_DIR, exist_ok=True)

    # Markdown report
    md_path = os.path.join(PREDICTIONS_DIR, f'{date_str}.md')
    lines = [
        f"# WC2026 小组赛预测 — {date_str}",
        f"",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} BJT",
        f"比赛场次: {len(results)}",
        f"",
        "---",
        "",
    ]

    for r in results:
        if r['audit']:
            msg = format_match_report(r['match'], r['audit'])
            lines.append(msg)
            lines.append("")
            lines.append("---")
            lines.append("")
        else:
            m = r['match']
            lines.append(f"## ❌ {m['team_a']} vs {m['team_b']} — 预测失败")
            lines.append(f"错误: {r.get('error', 'unknown')}")
            lines.append("")

    with open(md_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"💾 Markdown: {md_path}")

    # JSON report (serializable summary)
    json_path = os.path.join(PREDICTIONS_DIR, f'{date_str}.json')
    json_data = {
        'date_beijing': date_str,
        'generated': datetime.now().isoformat(),
        'total_matches': len(results),
        'predictions': []
    }
    for r in results:
        entry = {
            'match_id': r['match']['match_id'],
            'team_a': r['match']['team_a'],
            'team_b': r['match']['team_b'],
            'venue': r['match'].get('venue'),
            'group': r['match'].get('group'),
            'matchday': r['match'].get('matchday'),
            'time_beijing': r['match'].get('time_beijing'),
        }
        if r['audit']:
            p = r['audit']['prediction']
            v = r['audit']['verdict']
            entry['team_a_win_pct'] = p['team_a_win']
            entry['draw_pct'] = p['draw']
            entry['team_b_win_pct'] = p['team_b_win']
            entry['most_likely_score'] = p['most_likely_score']
            entry['verdict'] = v['result']
            entry['confidence'] = v['confidence']
            entry['error'] = None
        else:
            entry['error'] = r.get('error', 'unknown')
        json_data['predictions'].append(entry)

    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"💾 JSON: {json_path}")


def print_summary(results, date_str):
    """Print a terminal summary."""
    print(f"\n{'═' * 60}")
    print(f"📋 {date_str} 比赛预测汇总")
    print(f"{'═' * 60}")

    ok = sum(1 for r in results if r['audit'])
    print(f"✅ 成功: {ok}/{len(results)}")

    for r in results:
        m = r['match']
        if r['audit']:
            p = r['audit']['prediction']
            print(f"  {m['team_a']} vs {m['team_b']}: "
                  f"{p['team_a_win']}%/{p['draw']}%/{p['team_b_win']}% "
                  f"→ {r['audit']['verdict']['result']}")
        else:
            print(f"  ❌ {m['team_a']} vs {m['team_b']}: 预测失败")


def main():
    date_str = None

    if '--date' in sys.argv:
        idx = sys.argv.index('--date')
        if idx + 1 < len(sys.argv):
            date_str = sys.argv[idx + 1]
    elif '--tomorrow' in sys.argv:
        date_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    elif '--today' in sys.argv:
        date_str = datetime.now().strftime('%Y-%m-%d')

    if not date_str:
        print("Usage: python3.11 scripts/predict_by_date.py --date 2026-06-12")
        print("       python3.11 scripts/predict_by_date.py --tomorrow")
        print("       python3.11 scripts/predict_by_date.py --today [--news]")
        sys.exit(1)

    # Validate date format
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        print(f"❌ Invalid date: {date_str}. Use YYYY-MM-DD format.")
        sys.exit(1)

    print(f"🔮 WC2026 预测: {date_str}")
    print(f"📅 北京时间 (UTC+8)")
    print()

    results, _ = predict_by_date(date_str)

    if results:
        save_reports(results, date_str)
        print_summary(results, date_str)

    print(f"\n✅ 完成。")


if __name__ == '__main__':
    main()
