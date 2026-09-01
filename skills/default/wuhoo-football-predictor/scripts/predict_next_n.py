#!/usr/bin/env python3
"""
WC2026 未来N场预测 — v2.0
查找赛程中即将开始的比赛（默认4场），逐场预测并输出中文报告。
v2.0: 直接调用 predict_single_match() 获取结构化数据，保存完整预测到 JSON。

Usage:
  python3.11 scripts/predict_next_n.py           # 未来4场
  python3.11 scripts/predict_next_n.py --n 6     # 未来6场
  python3.11 scripts/predict_next_n.py --news    # 含新闻情感分析
  python3.11 scripts/predict_next_n.py --all-today-remaining  # 今天剩余比赛

Output: 终端中文报告 + data/daily_predictions/YYYY-MM-DD.json (含完整预测数据)
"""

import sys
import os
import json
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

from wc2026_predict import predict_single_match, print_match_prediction, TEAM_PROFILES as _TP
TEAM_PROFILES = _TP


def cn(name):
    """Get Chinese team name, fallback to English."""
    return TEAM_PROFILES.get(name, {}).get('name_cn', name)


def get_schedule():
    """Load schedule, return sorted by date_beijing + time_beijing."""
    sched_path = os.path.join(PROJECT_DIR, 'data', 'wc2026_schedule.json')
    with open(sched_path) as f:
        sched = json.load(f)
    matches = sched['matches']
    matches.sort(key=lambda m: (m['date_beijing'], m['time_beijing']))
    return matches


def get_next_n_matches(n, today_remaining=False):
    """Get the next N upcoming matches from now."""
    now_bjt = datetime.now(timezone(timedelta(hours=8)))
    now_str = now_bjt.strftime('%H:%M')
    today_str = now_bjt.strftime('%Y-%m-%d')

    all_matches = get_schedule()

    if today_remaining:
        upcoming = [
            m for m in all_matches
            if m['date_beijing'] == today_str and m['time_beijing'] > now_str
        ]
        return upcoming

    start_idx = None
    for i, m in enumerate(all_matches):
        dt = (m['date_beijing'], m['time_beijing'])
        now_dt = (today_str, now_str)
        if dt > now_dt:
            start_idx = i
            break

    if start_idx is None:
        return []

    return all_matches[start_idx:start_idx + n]


def main():
    n = 4
    today_remaining = False

    if '--n' in sys.argv:
        idx = sys.argv.index('--n')
        if idx + 1 < len(sys.argv):
            n = int(sys.argv[idx + 1])

    if '--all-today-remaining' in sys.argv:
        today_remaining = True
        n = 20

    matches = get_next_n_matches(n, today_remaining)

    if not matches:
        print("✅ 没有即将到来的比赛需要预测。")
        return

    enable_news = '--news' in sys.argv

    print(f"🔮 WC2026 未来 {len(matches)} 场预测")
    print(f"📅 北京时间 (UTC+8)")
    if enable_news:
        print(f"📰 已启用新闻情感分析")
    print(f"={'═' * 40}")

    all_audits = []  # v2.0: collect structured audit dicts

    for i, m in enumerate(matches, 1):
        team_a = m['team_a']
        team_b = m['team_b']
        venue = m.get('venue', None)
        matchday = m.get('matchday', '?')
        group = m.get('group', '?')

        print(f"\n{'─' * 40}")
        print(f"  #{i}/{len(matches)}  {m['date_beijing']} {m['time_beijing']} | Group {group} MD{matchday}")
        print(f"  ⚽ {cn(team_a)} vs {cn(team_b)} @ {venue}")
        print(f"{'─' * 40}")

        # v2.0: call predict_single_match directly for structured data
        try:
            audit = predict_single_match(team_a, team_b, venue_name=venue,
                                         enable_news=enable_news)
            all_audits.append({
                'match_id': m.get('match_id', f"{team_a}_vs_{team_b}"),
                'schedule': {
                    'date_beijing': m['date_beijing'],
                    'time_beijing': m.get('time_beijing', ''),
                    'group': group,
                    'matchday': matchday,
                    'venue': venue,
                },
                'audit': audit,
            })
            print_match_prediction(audit)
        except Exception as e:
            print(f"  ⚠️ 预测失败: {e}")
            all_audits.append({
                'match_id': m.get('match_id', f"{team_a}_vs_{team_b}"),
                'schedule': {
                    'date_beijing': m['date_beijing'],
                    'time_beijing': m.get('time_beijing', ''),
                    'group': group,
                    'matchday': matchday,
                    'venue': venue,
                },
                'error': str(e),
            })

    print(f"\n{'═' * 40}")
    print(f"✅ 完成 {len(matches)} 场预测")
    print(f"⚠️ 预测仅供娱乐参考。足球比赛具有高度不确定性。")

    # --- v2.0: 保存完整预测数据到 daily_predictions/ ---
    today_str = datetime.now().strftime('%Y-%m-%d')
    pred_dir = os.path.join(PROJECT_DIR, 'data', 'daily_predictions')
    os.makedirs(pred_dir, exist_ok=True)

    predictions_data = {
        'date_beijing': today_str,
        'generated': datetime.now().isoformat(),
        'total_matches': len(matches),
        'news_enabled': enable_news,
        'predictions': [],
        'matches': all_audits,  # raw audit for debugging
    }
    
    # Build flattened predictions with scoreline_probs
    for audit_entry in all_audits:
        audit = audit_entry.get('audit', {})
        sched = audit_entry.get('schedule', {})
        pred = audit.get('prediction', {})
        flat = {
            'match_id': audit_entry.get('match_id', '?'),
            'team_a': audit.get('team_a', '?'),
            'team_b': audit.get('team_b', '?'),
            'venue': audit.get('venue', ''),
            'group': sched.get('group', None),
            'matchday': sched.get('matchday', None),
            'time_beijing': sched.get('time_beijing', ''),
            'team_a_win_pct': pred.get('team_a_win', 0),
            'draw_pct': pred.get('draw', 0),
            'team_b_win_pct': pred.get('team_b_win', 0),
            'most_likely_score': pred.get('most_likely_score', '?'),
            'expected_goals_a': pred.get('expected_goals_a', 0),
            'expected_goals_b': pred.get('expected_goals_b', 0),
            'scoreline_probs': pred.get('scoreline_probs', []),  # v5.7: Poisson score distribution
            'verdict': audit.get('verdict', {}).get('result', '?') if isinstance(audit.get('verdict'), dict) else str(audit.get('verdict', '?')),
            'confidence': audit.get('verdict', {}).get('confidence', 'low') if isinstance(audit.get('verdict'), dict) else 'low',
            'error': audit_entry.get('error', None),
        }
        predictions_data['predictions'].append(flat)

    pred_path = os.path.join(pred_dir, f'{today_str}.json')
    with open(pred_path, 'w') as f:
        json.dump(predictions_data, f, indent=2, ensure_ascii=False)
    print(f"💾 预测已保存: {pred_path}")

    # --- 体彩串关方案 ---
    if '--no-lottery' not in sys.argv:
        print(f"\n{'═' * 60}")
        print(f"🎲 生成体彩串关方案中...")
        print(f"{'═' * 60}")
        try:
            import subprocess
            lottery_cmd = f"{sys.executable} {SCRIPT_DIR}/lottery_parlay.py --matches {len(matches)}"
            if '--news' in sys.argv:
                lottery_cmd += " --news"
            else:
                lottery_cmd += " --no-news"
            result = subprocess.run(lottery_cmd, shell=True, cwd=PROJECT_DIR,
                                    capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(f"⚠️ 串关生成失败: {result.stderr[:200]}")
        except Exception as e:
            print(f"⚠️ 串关生成异常: {e}")


if __name__ == '__main__':
    main()
