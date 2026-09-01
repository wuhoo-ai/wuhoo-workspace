#!/usr/bin/env python3
"""
WC2026 每日管线编排脚本 — v1.0
按时间段编排数据刷新、结果采集、赛前预测全流程。

Usage:
  python3.11 scripts/daily_pipeline.py            # 自动检测（按当前时间）
  python3.11 scripts/daily_pipeline.py --morning  # 08:00 数据刷新模式
  python3.11 scripts/daily_pipeline.py --evening  # 17:00 赛前预测模式
  python3.11 scripts/daily_pipeline.py --test     # 测试模式（dry-run）
"""

import sys
import os
import json
import subprocess
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

BJT = timezone(timedelta(hours=8))
PYTHON = 'python3.11'

# Tournament date range (Beijing)
TOURNAMENT_START = '2026-06-11'  # first cron run (evening before MD1)
GROUP_STAGE_END = '2026-06-28'   # last match day
POST_END = '2026-06-29'          # last morning run


def run_cmd(cmd, desc):
    """Run a command and print status."""
    print(f"  ▶ {desc}...")
    result = subprocess.run(cmd, shell=True, cwd=PROJECT_DIR,
                            capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        # Print first few lines as summary
        for line in lines[:5]:
            print(f"    {line}")
        if len(lines) > 5:
            print(f"    ... ({len(lines)} lines total)")
        return True
    else:
        print(f"  ⚠️ 失败 (exit {result.returncode})")
        if result.stderr.strip():
            for line in result.stderr.strip().split('\n')[:3]:
                print(f"    {line}")
        return False


def is_in_range(date_str, start, end):
    """Check if date is in [start, end]."""
    return start <= date_str <= end


def pipeline_morning(date_str):
    """08:00 Morning pipeline: data refresh + results collection."""
    print(f"🌅 Morning Pipeline — {date_str}")
    print("═" * 50)
    print()

    # 1. Pre-match refresh
    print("📊 Step 1: 数据新鲜度检查")
    run_cmd(f"{PYTHON} scripts/pre_match_refresh.py", "pre_match_refresh")
    print()

    # 2. ELO update attempt
    print("📊 Step 2: ELO 数据更新")
    run_cmd(f"{PYTHON} scripts/fetch_elo.py --diff", "fetch_elo")
    print()

    # 3. Friendly form update
    print("📊 Step 3: 热身赛状态更新")
    run_cmd(f"{PYTHON} scripts/fetch_friendlies.py --compute-form", "friendly form")
    print()

    # 4. Collect yesterday's results
    yesterday = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    if yesterday >= '2026-06-12':
        print(f"📊 Step 4: 采集 {yesterday} 比赛结果")
        print("  ℹ️ 请用 web_search 查找昨日比赛结果，传入 --manual JSON")
        print(f"  示例: python3.11 scripts/collect_results.py --date {yesterday} --manual '[...]'")
        print("  ⚠️ 此步骤需在 cron prompt 中由 Agent 执行 web_search")
    else:
        print(f"📊 Step 4: {yesterday} — 赛程未开始，跳过")
    print()

    # 5. ELO update from results (if results exist)
    results_path = os.path.join(PROJECT_DIR, 'data', 'wc2026_results.json')
    if os.path.exists(results_path):
        print("📊 Step 5: ELO 结果更新")
        run_cmd(f"{PYTHON} scripts/update_elo_from_results.py", "update_elo")
    else:
        print("📊 Step 5: 无比赛结果，跳过 ELO 更新")
    print()

    # 6. Summary
    print("═" * 50)
    print("✅ Morning pipeline 完成")


def pipeline_evening(date_str):
    """17:00 Evening pipeline: predict tomorrow's matches."""
    tomorrow = (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"🌇 Evening Pipeline — {date_str}")
    print(f"   预测日期: {tomorrow}")
    print("═" * 50)
    print()

    if tomorrow > GROUP_STAGE_END:
        print(f"✅ {tomorrow} 已超出小组赛范围，无需预测")
        print("   小组赛: 6/12 ~ 6/28")
        return

    # 1. Predict tomorrow's matches
    print(f"🔮 Step 1: 预测 {tomorrow} 比赛")
    success = run_cmd(f"{PYTHON} scripts/predict_by_date.py --date {tomorrow}", "predict_by_date")
    print()

    if not success:
        print("⚠️ 预测失败，管线终止")
        return

    # 2. Read predictions for WeChat delivery
    predictions_dir = os.path.join(PROJECT_DIR, 'data', 'daily_predictions')
    json_path = os.path.join(predictions_dir, f'{tomorrow}.json')
    if os.path.exists(json_path):
        with open(json_path) as f:
            data = json.load(f)

        print(f"📋 Step 2: 生成微信推送 ({data['total_matches']} 场比赛)")
        print()
        for p in data['predictions']:
            if p.get('error'):
                print(f"  ❌ {p['team_a']} vs {p['team_b']}: 预测失败")
            else:
                team_cn_a = p.get('team_cn_a', p['team_a'])
                team_cn_b = p.get('team_cn_b', p['team_b'])
                print(f"  ⚽ {team_cn_a} vs {team_cn_b}")
                print(f"     {p['team_a']}胜 {p['team_a_win_pct']}% / "
                      f"平 {p['draw_pct']}% / "
                      f"{p['team_b']}胜 {p['team_b_win_pct']}%")
                print(f"     最可能比分: {p['most_likely_score']}")
                print(f"     判定: {p['verdict']} (置信度: {p['confidence']})")
                print()
                print("---")

    print()
    print("═" * 50)
    print("✅ Evening pipeline 完成")
    print()
    print("📱 Cron job 将读取以上输出，为每场比赛发送一条微信消息。")


def main():
    mode = None
    if '--morning' in sys.argv:
        mode = 'morning'
    elif '--evening' in sys.argv:
        mode = 'evening'
    elif '--test' in sys.argv:
        mode = 'evening'  # test runs evening by default
    else:
        # Auto-detect: use current BJT hour
        now = datetime.now(BJT)
        if now.hour < 12:
            mode = 'morning'
        else:
            mode = 'evening'

    today = datetime.now(BJT).strftime('%Y-%m-%d')

    if '--date' in sys.argv:
        idx = sys.argv.index('--date')
        if idx + 1 < len(sys.argv):
            today = sys.argv[idx + 1]

    # Date range check
    if mode == 'evening' and today < TOURNAMENT_START:
        print(f"ℹ️ {today}: 赛程未开始（首场预测: {TOURNAMENT_START} 晚间）")
        return
    if mode == 'evening' and today > GROUP_STAGE_END:
        print(f"ℹ️ {today}: 小组赛已结束（{GROUP_STAGE_END}）")
        return
    if mode == 'morning' and today < '2026-06-12':
        print(f"ℹ️ {today}: 首场比赛尚未开始（6/12）")
        return
    if mode == 'morning' and today > POST_END:
        print(f"ℹ️ {today}: 小组赛后续处理已完成")
        return

    if mode == 'morning':
        pipeline_morning(today)
    else:
        pipeline_evening(today)


if __name__ == '__main__':
    main()
