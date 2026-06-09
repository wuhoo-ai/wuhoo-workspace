#!/usr/bin/env python3
"""
WC2026 赛前 1h 提醒 — v1.0
查找即将在 60-90 分钟内开始的比赛，匹配已有预测并生成提醒消息。

Usage:
  python3.11 scripts/match_reminder.py                  # 默认: 60-90min 窗口
  python3.11 scripts/match_reminder.py --window 45      # 自定义窗口（分钟）
  python3.11 scripts/match_reminder.py --all             # 显示今天所有比赛时间
"""

import sys
import os
import json
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, SCRIPT_DIR)

from wc2026_predict import (
    _get_schedule, predict_single_match, _save_prediction_history,
    TEAM_PROFILES
)

DATA_DIR = os.path.join(PROJECT_DIR, 'data')
HISTORY_PATH = os.path.join(DATA_DIR, 'prediction_history.jsonl')

# Beijing timezone (UTC+8)
BJT = timezone(timedelta(hours=8))

WINDOW_MIN = 60   # minutes before match
WINDOW_MAX = 90   # max minutes before match


def parse_match_time(m):
    """Parse match Beijing time into a datetime object."""
    date_str = m['date_beijing']
    time_str = m['time_beijing']
    dt_str = f"{date_str} {time_str}:00"
    naive = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    return naive.replace(tzinfo=BJT)


def load_prediction_history():
    """Load prediction history keyed by match_id."""
    if not os.path.exists(HISTORY_PATH):
        return {}
    records = {}
    with open(HISTORY_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    mid = r.get('schedule', {}).get('match_id')
                    if mid:
                        # Keep the latest prediction
                        if mid not in records or r.get('timestamp', '') > records[mid].get('timestamp', ''):
                            records[mid] = r
                except json.JSONDecodeError:
                    pass
    return records


def format_reminder(match_info, prediction):
    """Format a WeChat-friendly reminder message."""
    ta = match_info['team_a']
    tb = match_info['team_b']
    pa = TEAM_PROFILES.get(ta, {})
    pb = TEAM_PROFILES.get(tb, {})
    na = pa.get('name_cn', ta)
    nb = pb.get('name_cn', tb)

    lines = []
    lines.append(f"⏰ 比赛即将开始！")
    lines.append(f"⚽ {na} vs {nb}")
    lines.append(f"📅 {match_info['date_beijing']} {match_info['time_beijing']} BJT")
    lines.append(f"🏟️ {match_info.get('venue', '?')} · "
                 f"Group {match_info['group']} · MD{match_info['matchday']}")

    if prediction:
        p = prediction.get('prediction', {})
        v = prediction.get('verdict', {})
        # verdict can be str or dict depending on source
        if isinstance(v, dict):
            verdict_str = v.get('result', str(v))
        else:
            verdict_str = str(v) if v else '?'
        lines.append("")
        lines.append(f"📈 {na}胜 {p.get('team_a_win', '?')}% | "
                     f"平 {p.get('draw', '?')}% | "
                     f"{nb}胜 {p.get('team_b_win', '?')}%")
        lines.append(f"🎯 最可能比分: {p.get('most_likely_score', '?')}")
        lines.append(f"🧠 {verdict_str}")
    else:
        lines.append("")
        lines.append("⚠️ 无预测记录，请查看上一期预测报告")

    lines.append(f"⚠️ 仅供娱乐参考")
    return '\n'.join(lines)


def find_upcoming_matches(window_min=WINDOW_MIN, window_max=WINDOW_MAX):
    """Find matches starting within the window (minutes from now)."""
    now = datetime.now(BJT)
    sched = _get_schedule()

    upcoming = []
    for m in sched['matches']:
        match_time = parse_match_time(m)
        diff_min = (match_time - now).total_seconds() / 60

        if window_min <= diff_min <= window_max:
            upcoming.append((m, diff_min))
        elif 0 <= diff_min < window_min:
            upcoming.append((m, diff_min))

    # Sort by proximity
    upcoming.sort(key=lambda x: x[1])
    return upcoming


def list_today_matches():
    """List all matches for today (Beijing time)."""
    now = datetime.now(BJT)
    today_str = now.strftime('%Y-%m-%d')
    sched = _get_schedule()

    matches = [m for m in sched['matches'] if m['date_beijing'] == today_str]
    if not matches:
        print(f"📅 {today_str}: 今日无比赛")
        return

    print(f"📅 {today_str} 比赛安排 (北京时间):")
    print()
    for m in matches:
        mt = parse_match_time(m)
        diff_min = (mt - now).total_seconds() / 60
        if diff_min < 0:
            status = "✅ 已结束"
        elif diff_min < 60:
            status = f"🔴 {int(diff_min)}分钟后"
        else:
            hours = int(diff_min / 60)
            mins = int(diff_min % 60)
            status = f"⏳ {hours}h{mins}min后"
        print(f"  {m['time_beijing']}  {m['team_a']} vs {m['team_b']}  [{status}]")
        print(f"       Group {m['group']} MD{m['matchday']} · {m.get('venue', '?')}")


def main():
    if '--all' in sys.argv or '--today' in sys.argv:
        list_today_matches()
        return

    window_min = WINDOW_MIN
    window_max = WINDOW_MAX
    if '--window' in sys.argv:
        idx = sys.argv.index('--window')
        if idx + 1 < len(sys.argv):
            w = int(sys.argv[idx + 1])
            window_min = max(10, w - 15)
            window_max = w + 15

    predictions = load_prediction_history()
    upcoming = find_upcoming_matches(window_min, window_max)

    if not upcoming:
        # Silent exit — no matches coming up
        print(f"ℹ️ 未来 {window_max} 分钟内无比赛")
        return

    print(f"🔔 赛前提醒 — {datetime.now(BJT).strftime('%H:%M')} BJT")
    print(f"   窗口: {window_min}-{window_max} 分钟")
    print()

    for match_info, diff_min in upcoming:
        mid = match_info['match_id']
        pred = predictions.get(mid)

        if not pred:
            # No existing prediction — run one now
            try:
                audit = predict_single_match(
                    match_info['team_a'], match_info['team_b'],
                    venue_name=match_info.get('venue'),
                    enable_news=False, knockout=False
                )
                audit['schedule'] = match_info
                _save_prediction_history(audit)
                pred = audit
            except Exception as e:
                print(f"  ⚠️ 预测失败: {match_info['team_a']} vs {match_info['team_b']}: {e}")
                continue

        msg = format_reminder(match_info, pred)
        print(msg)
        print()
        print("---")
        print()

    print(f"✅ 共 {len(upcoming)} 场即将开始的比赛")


if __name__ == '__main__':
    main()
