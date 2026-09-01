#!/usr/bin/env python3.11
"""
⚽ WC2026 足球数据保鲜检查 — 检查所有预测管线数据源的新鲜度。
集成在每日 14:30 cron (WC2026 数据刷新+结果采集) 中运行。

用法:
  python3.11 check_football_freshness.py           # Markdown 报告
  python3.11 check_football_freshness.py --json    # JSON 输出
  python3.11 check_football_freshness.py --quiet   # 仅输出有问题的项
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import OrderedDict

SKILL_DIR = Path.home() / 'wuhoo-workspace' / 'skills' / 'wuhoo' / 'wuhoo-football-predictor'
DATA_DIR = SKILL_DIR / 'data'
NOW = datetime.now()

# ============================================================
# 保鲜阈值 (warn_days, crit_days, 描述)
# ============================================================
THRESHOLDS = OrderedDict([
    # 核心实时数据 — 每天应更新
    ('elo_ratings.json',              (1, 3,  'ELO 评分',           'fetch_elo.py')),
    ('wc2026_results.json',           (1, 3,  '比赛结果',           'collect_results.py')),
    ('injuries.json',                 (2, 5,  '伤停数据',           '手动维护 / injury data sources')),
    ('prediction_accuracy.json',      (3, 7,  '预测准确率',         'daily_pipeline.py 自动更新')),
    
    # 赛程与热身赛 — 赛事期间每日更新
    ('wc2026_schedule.json',          (3, 7,  '赛程表',             '重新 fetch 赛程数据')),
    ('friendly_matches.json',         (5, 10, '热身赛数据',         'fetch_friendlies.py')),
    ('friendly_form_adjustments.json',(5, 10, '热身赛形态修正',     'fetch_friendlies.py 后自动生成')),
    
    # 球队元数据 — 赛事期间低频更新
    ('team_metadata.json',            (14, 30, '球队元数据',         '重新 fetch 球队数据')),
    ('team_profiles.json',            (14, 30, '球队档案',           '重新生成球队档案')),
    
    # 基础设施 — 赛事全程不变
    ('venues.json',                   (30, 60, '场馆数据',          '重新 fetch 场馆数据')),
    ('group_venues.json',             (30, 60, '小组场馆映射',      '重新生成场馆映射')),
    
    # 赛程 — 小组赛后基本不变 (但应随赛果更新)
    ('wc2026_schedule.json',          (5, 14, '赛程表',             '重新 fetch 赛程数据')),
])


def check_file(path: Path, warn_d: int, crit_d: int, desc: str) -> dict:
    """检查单个文件保鲜度"""
    if not path.exists():
        return {'status': 'missing', 'days_old': None, 'desc': desc, 'warn': warn_d, 'crit': crit_d}
    
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    days_old = (NOW - mtime).days
    hours_old = round((NOW - mtime).total_seconds() / 3600, 1)
    
    if days_old >= crit_d:
        level = 'critical'
    elif days_old >= warn_d:
        level = 'warning'
    else:
        level = 'ok'
    
    return {
        'status': 'ok',
        'level': level,
        'days_old': days_old,
        'hours_old': hours_old,
        'mtime': mtime.isoformat(),
        'size_kb': round(path.stat().st_size / 1024, 1),
        'desc': desc,
        'warn': warn_d,
        'crit': crit_d,
    }


def check_daily_predictions() -> dict:
    """检查每日预测输出"""
    pred_dir = DATA_DIR / 'daily_predictions'
    if not pred_dir.exists():
        return {'status': 'missing', 'files': []}
    
    files = sorted(pred_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return {'status': 'empty', 'files': []}
    
    latest = files[0]
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    days_old = (NOW - mtime).days
    
    return {
        'status': 'ok',
        'days_old': days_old,
        'latest_file': latest.name,
        'latest_mtime': mtime.isoformat(),
        'total_files': len(files),
        'level': 'warning' if days_old > 2 else 'ok',
    }


def run_all_checks():
    checks = OrderedDict()
    
    for fname, (warn_d, crit_d, desc, fix_cmd) in THRESHOLDS.items():
        path = DATA_DIR / fname
        result = check_file(path, warn_d, crit_d, desc)
        result['fix_cmd'] = fix_cmd
        checks[fname] = result
    
    # Daily predictions
    checks['daily_predictions'] = check_daily_predictions()
    
    # ELO ratings internal data quality
    elo_path = DATA_DIR / 'elo_ratings.json'
    if elo_path.exists():
        try:
            elo_data = json.loads(elo_path.read_text())
            checks['elo_ratings.json']['team_count'] = len(elo_data) if isinstance(elo_data, dict) else len(elo_data)
        except Exception:
            pass
    
    return checks


def freshness_icon(level):
    return {'ok': '✅', 'warning': '🟡', 'critical': '🔴'}.get(level, '❓')


def generate_markdown(checks):
    lines = []
    lines.append(f"## ⚽ WC2026 数据保鲜检查")
    lines.append(f"**时间**: {NOW.strftime('%Y-%m-%d %H:%M')} (UTC+8)")
    lines.append("")
    
    criticals = [(k, v) for k, v in checks.items() if v.get('level') == 'critical']
    warnings  = [(k, v) for k, v in checks.items() if v.get('level') == 'warning']
    
    if criticals:
        lines.append(f"### 🔴 严重过期 ({len(criticals)} 项)")
        for name, r in criticals:
            desc = r.get('desc', name)
            fix = r.get('fix_cmd', '')
            lines.append(f"- **{desc}** (`{name}`): {r['days_old']} 天未更新 → `{fix}`")
        lines.append("")
    
    if warnings:
        lines.append(f"### 🟡 接近过期 ({len(warnings)} 项)")
        for name, r in warnings:
            desc = r.get('desc', name)
            lines.append(f"- **{desc}** (`{name}`): {r['days_old']} 天未更新")
        lines.append("")
    
    lines.append("| 数据文件 | 状态 | 天数 | 大小 | 阈值 |")
    lines.append("|----------|------|------|------|------|")
    
    for fname, r in checks.items():
        if fname == 'daily_predictions':
            icon = freshness_icon(r.get('level', 'ok'))
            days = r.get('days_old', '?')
            lines.append(f"| 每日预测输出 | {icon} | {days}d | {r.get('total_files', 0)} 文件 | — |")
            continue
        
        icon = freshness_icon(r.get('level', 'ok'))
        days = r.get('days_old', 'N/A')
        size = f"{r.get('size_kb', 0)} KB"
        thresh = f"{r.get('warn', '?')}/{r.get('crit', '?')}d"
        desc = r.get('desc', fname)
        lines.append(f"| {desc} | {icon} | {days}d | {size} | {thresh} |")
    
    if not criticals and not warnings:
        lines.append("")
        lines.append("✅ **所有足球数据保鲜正常**")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='WC2026 足球数据保鲜检查')
    parser.add_argument('--json', action='store_true', help='JSON 输出')
    parser.add_argument('--quiet', action='store_true', help='仅输出有问题的项')
    args = parser.parse_args()
    
    checks = run_all_checks()
    
    if args.json:
        clean = {}
        for k, v in checks.items():
            clean[k] = {kk: vv for kk, vv in v.items() if kk != 'fix_cmd'}
        print(json.dumps(clean, indent=2, ensure_ascii=False, default=str))
        return
    
    report = generate_markdown(checks)
    
    if args.quiet:
        criticals = [(k, v) for k, v in checks.items() if v.get('level') == 'critical']
        warnings  = [(k, v) for k, v in checks.items() if v.get('level') == 'warning']
        if not criticals and not warnings:
            print("✅ Football data all fresh")
            return
        for line in report.split('\n'):
            if any(line.startswith(p) for p in ['### 🔴', '### 🟡', '- **']):
                print(line)
    else:
        print(report)


if __name__ == '__main__':
    main()
