#!/usr/bin/env python3
"""
WC2026 预测前数据刷新检查 — v3.0
检查所有数据文件的新鲜度和完整性，在预测前自动运行。

Usage:
  python3.11 scripts/pre_match_refresh.py              # 检查并报告
  python3.11 scripts/pre_match_refresh.py --refresh    # 尝试自动刷新
"""

import sys
import os
import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'

FILES = {
    'elo': DATA_DIR / 'elo_ratings.json',
    'injuries': DATA_DIR / 'injuries.json',
    'metadata': DATA_DIR / 'team_metadata.json',
    'profiles': DATA_DIR / 'team_profiles.json',
    'schedule': DATA_DIR / 'wc2026_schedule.json',
    'venues': DATA_DIR / 'venues.json',
    'group_venues': DATA_DIR / 'group_venues.json',
    'friendlies': DATA_DIR / 'friendly_matches.json',
    'friendly_form': DATA_DIR / 'friendly_form_adjustments.json',
}

EXPECTED_GROUPS = {
    'A': 4, 'B': 4, 'C': 4, 'D': 4, 'E': 4, 'F': 4,
    'G': 4, 'H': 4, 'I': 4, 'J': 4, 'K': 4, 'L': 4,
}


def check_file_age(path, max_days=7):
    """Check if file is within max_days old."""
    if not path.exists():
        return False, "NOT FOUND", None
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    age_days = (datetime.now() - mtime).days
    if age_days > max_days:
        return False, f"STALE ({age_days}d old)", mtime.strftime('%Y-%m-%d')
    return True, f"OK ({age_days}d ago)", mtime.strftime('%Y-%m-%d')


def main():
    refresh = '--refresh' in sys.argv
    all_ok = True
    issues = []

    print("═" * 60)
    print("🔍 WC2026 预测数据刷新检查 v3.0")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 60)

    # 1. ELO
    print("\n📊 ELO 数据")
    path = FILES['elo']
    ok, status, date = check_file_age(path, max_days=14)
    icon = '✅' if ok else '⚠️'
    print(f"  {icon} {status} ({date})")
    if path.exists():
        with open(path) as f:
            elo = json.load(f)
        wc_teams = set()
        for g in EXPECTED_GROUPS:
            pass  # we'll check from schedule
        n_teams = len(elo.get('ratings', {}))
        print(f"     {n_teams} teams, source: {elo.get('source', '?')}")
        if n_teams < 48:
            print(f"  ⚠️ Only {n_teams} teams — need at least 48 for WC")
        if not ok:
            issues.append(f"ELO data {status} — run: python3.11 scripts/fetch_elo.py --output=data/elo_ratings.json")
    else:
        issues.append("ELO data missing!")

    # 2. Injuries
    print("\n🏥 伤病数据")
    path = FILES['injuries']
    ok, status, date = check_file_age(path, max_days=14)
    icon = '✅' if ok else '⚠️'
    print(f"  {icon} {status} ({date})")
    if path.exists():
        with open(path) as f:
            inj = json.load(f)
        n_teams = len(inj.get('injuries', {}))
        doubtful = 0
        for t, info in inj.get('injuries', {}).items():
            for p in info.get('players', []):
                if p.get('status') == 'DOUBTFUL':
                    doubtful += 1
        print(f"     {n_teams} teams with injuries, {doubtful} DOUBTFUL")
        if doubtful > 0:
            print(f"  ⚠️ {doubtful} DOUBTFUL players — check ESPN for squad confirmations")
            issues.append(f"伤病数据 {status} — 请查看 ESPN injuries tracker 确认 DOUBTFUL 球员状态")

    # 3. Team metadata
    print("\n👔 教练/磨合元数据")
    path = FILES['metadata']
    ok, status, date = check_file_age(path, max_days=14)
    icon = '✅' if ok else '⚠️'
    print(f"  {icon} {status} ({date})")
    if path.exists():
        with open(path) as f:
            meta = json.load(f)
        n_teams = len(meta.get('teams', {}))
        print(f"     {n_teams}/48 teams")
        if n_teams < 48:
            missing = 48 - n_teams
            print(f"  ⚠️ {missing} teams missing metadata")
            issues.append(f"元数据 {status} — {missing} 队缺失，影响教练/磨合因子")

    # 4. Schedule
    print("\n📅 赛程数据")
    path = FILES['schedule']
    ok, status, date = check_file_age(path, max_days=365)  # schedule doesn't change
    icon = '✅' if ok else '❌'
    print(f"  {icon} {status} ({date})")
    if path.exists():
        with open(path) as f:
            sched = json.load(f)
        n_matches = len(sched.get('matches', []))
        print(f"     {n_matches} matches")
        if n_matches != 72:
            print(f"  ❌ Expected 72 matches, got {n_matches}")
            issues.append(f"赛程 {status} — 比赛数 {n_matches} ≠ 72")
    else:
        issues.append("赛程文件缺失！无法按赛程查找比赛。")

    # 5. Cross-validation: schedule teams vs ELO
    print("\n🔗 交叉验证")
    if FILES['schedule'].exists() and FILES['elo'].exists():
        with open(FILES['schedule']) as f:
            sched = json.load(f)
        with open(FILES['elo']) as f:
            elo = json.load(f)

        schedule_teams = set()
        for m in sched.get('matches', []):
            schedule_teams.add(m['team_a'])
            schedule_teams.add(m['team_b'])

        elo_teams = set(elo.get('ratings', {}).keys())
        missing_elo = schedule_teams - elo_teams
        if missing_elo:
            print(f"  ❌ {len(missing_elo)} teams in schedule missing ELO: {missing_elo}")
            issues.append(f"交叉验证失败: {len(missing_elo)} 队缺 ELO")
        else:
            print(f"  ✅ All {len(schedule_teams)} schedule teams have ELO data")

        # Check metadata coverage
        if FILES['metadata'].exists():
            with open(FILES['metadata']) as f:
                meta = json.load(f)
            meta_teams = set(meta.get('teams', {}).keys())
            missing_meta = schedule_teams - meta_teams
            if missing_meta:
                print(f"  ⚠️ {len(missing_meta)} teams missing metadata: {sorted(missing_meta)}")
            else:
                print(f"  ✅ All {len(schedule_teams)} teams have metadata")

    # 6. Prediction history
    hist_path = DATA_DIR / 'prediction_history.jsonl'
    if hist_path.exists():
        n_lines = sum(1 for _ in open(hist_path))
        print(f"\n📝 预测历史: {n_lines} 条记录")

    # 7. Friendly matches (v3.1)
    print("\n⚽ 热身赛数据 (v3.1)")
    path = FILES['friendlies']
    ok, status, date = check_file_age(path, max_days=2)  # daily updates expected
    icon = '✅' if ok else '⚠️'
    print(f"  {icon} {status} ({date})")
    if path.exists():
        with open(path) as f:
            friendlies = json.load(f)
        matches = friendlies.get('matches', [])
        completed = sum(1 for m in matches if m.get('score_a') is not None)
        pending = len(matches) - completed
        print(f"     {len(matches)} matches, {completed} completed, {pending} TBD")
        if pending > 0:
            print(f"  ⚠️ {pending} matches with TBD results — check FIFA/ESPN")
            issues.append(f"热身赛 {status} — {pending}场比赛结果未确认")
    else:
        issues.append("热身赛数据缺失！请运行: python3.11 scripts/fetch_friendlies.py")

    # 7b. Friendly form adjustments
    form_path = FILES['friendly_form']
    if form_path.exists():
        with open(form_path) as f:
            form = json.load(f)
        n_teams = len(form.get('teams', {}))
        print(f"     Form adjustments: {n_teams} teams")
        # Show top/bottom adjustments
        teams = form.get('teams', {})
        if teams:
            top_pos = max(teams.items(), key=lambda x: x[1])
            top_neg = min(teams.items(), key=lambda x: x[1])
            print(f"     🟢 Best form: {top_pos[0]} ({top_pos[1]:+d})")
            print(f"     🔴 Worst form: {top_neg[0]} ({top_neg[1]:+d})")
    else:
        print(f"  ⚠️ Form adjustments not computed — run: python3.11 scripts/fetch_friendlies.py --compute-form")

    # Summary
    print("\n" + "═" * 60)
    if issues:
        print(f"⚠️ {len(issues)} 个问题需要处理:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("✅ 所有数据就绪，可以运行预测。")

    # Data freshness summary
    print("\n📊 数据新鲜度总览:")
    for name, path in FILES.items():
        if path.exists():
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age = (datetime.now() - mtime).days
            flag = '🟢' if age < 7 else '🟡' if age < 14 else '🔴'
            print(f"  {flag} {name:<15} {mtime.strftime('%Y-%m-%d')} ({age}d ago)")

    print("═" * 60)

    return 0 if not issues else len(issues)


if __name__ == '__main__':
    sys.exit(main())
