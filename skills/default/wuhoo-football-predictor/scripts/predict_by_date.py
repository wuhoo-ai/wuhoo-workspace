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

# v5.5: Import inference engine wrapper
try:
    from scripts.predict_v55 import predict_with_engine
    USE_INFERENCE_ENGINE = True
except ImportError:
    USE_INFERENCE_ENGINE = False

DATA_DIR = os.path.join(PROJECT_DIR, 'data')
PREDICTIONS_DIR = os.path.join(DATA_DIR, 'daily_predictions')
HISTORY_PATH = os.path.join(DATA_DIR, 'prediction_history.jsonl')
MANUAL_ADJ_PATH = os.path.join(DATA_DIR, 'manual_adjustments.json')


def _load_manual_adjustments():
    """Load Layer 6 manual ELO adjustments from data/manual_adjustments.json."""
    if not os.path.exists(MANUAL_ADJ_PATH):
        return {}
    try:
        with open(MANUAL_ADJ_PATH) as f:
            data = json.load(f)
        adj = {}
        for team, info in data.get('adjustments', {}).items():
            adj[team] = info.get('elo_adjustment', 0)
        if adj:
            print(f"📌 手动调整 (Layer 6): {len(adj)} 队 — {', '.join(f'{t}({v:+d})' for t, v in adj.items())}")
        return adj
    except Exception as e:
        print(f"⚠️ 加载手动调整失败: {e}")
        return {}


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
    
    # Also check knockout_schedule.json for knockout matches on this date
    ko_path = os.path.join(DATA_DIR, 'knockout_schedule.json')
    if os.path.exists(ko_path):
        with open(ko_path) as f:
            ko = json.load(f)
        for stage_name, stage_data in ko.get('stages', {}).items():
            for m in stage_data.get('matches', []):
                if m.get('date_beijing') == date_str and m.get('team_a') and m.get('team_b'):
                    if m.get('status') != 'completed':
                        # Add round info
                        m_copy = dict(m)
                        m_copy['round'] = stage_name
                        matches.append(m_copy)
    
    # Filter out matches with null teams (from group stage schedule remnants)
    matches = [m for m in matches if m.get('team_a') and m.get('team_b')]
    
    # v5.11.2: dedupe — wc2026_schedule.json may now carry synced knockout
    # matches (97-104), which also live in knockout_schedule.json
    seen_keys = set()
    deduped = []
    for m in matches:
        key = (m.get('match_id'), m.get('team_a'), m.get('team_b'))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(m)
    matches = deduped
    
    if not matches:
        print(f"✅ {date_str}: 无比赛安排")
        return [], date_str

    manual_adj = _load_manual_adjustments()
    
    # Load MD3 motivation data if any match is from MD3
    matchdays = {m.get('matchday') for m in matches}
    is_md3 = 3 in matchdays
    motivation_data = None
    bracket_data = None
    if is_md3:
        try:
            mot_path = os.path.join(PROJECT_DIR, 'data', 'matchday3_motivation.json')
            if os.path.exists(mot_path):
                with open(mot_path) as f:
                    motivation_data = json.load(f).get('classifications', {})
                if motivation_data:
                    print(f"   📋 加载MD3出线动机数据: {len(motivation_data)}队")
        except Exception as e:
            print(f"   ⚠️ 加载MD3动机数据失败: {e}")
        try:
            bp_path = os.path.join(PROJECT_DIR, 'data', 'bracket_paths.json')
            if os.path.exists(bp_path):
                with open(bp_path) as f:
                    bracket_data = json.load(f)
                print(f"   🗺️ 加载半区路径数据")
        except Exception as e:
            print(f"   ⚠️ 加载半区路径数据失败: {e}")

    results = []
    for m in matches:
        matchday_val = m.get('matchday')
        print(f"🔄 预测: {m['team_a']} vs {m['team_b']} (Match #{m['match_id']})...")
        try:
            # v5.5: Use inference engine wrapper when available
            if USE_INFERENCE_ENGINE:
                audit = predict_with_engine(
                    m['team_a'], m['team_b'],
                    venue_name=m.get('venue'),
                    enable_news=('--news' in sys.argv),
                    knockout=bool(m.get('round')) and str(m.get('round')) in ('R32', 'R16', 'QF', 'SF', 'F', '3rd', 'Final'),
                    match_id=m.get('match_id'),
                    manual_adjustments=manual_adj,
                    matchday=matchday_val,
                    motivation_data=motivation_data,
                    bracket_data=bracket_data,
                    rules_version="v1"
                )
            else:
                audit = predict_single_match(
                    m['team_a'], m['team_b'],
                    venue_name=m.get('venue'),
                    enable_news=('--news' in sys.argv),
                    knockout=bool(m.get('round')) and str(m.get('round')) in ('R32', 'R16', 'QF', 'SF', 'F', '3rd', 'Final'),
                    match_id=m.get('match_id'),
                    manual_adjustments=manual_adj,
                    matchday=matchday_val,
                    motivation_data=motivation_data,
                    bracket_data=bracket_data
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
        f.write('\n'.join(lines) + '\n'.join(format_objective_factors_md(results)))
    print(f"💾 Markdown: {md_path}")

    # JSON report — two keys for compatibility:
    # 'predictions' for human/WeChat (flat), 'matches' for generate_daily_report.py (full audit)
    json_path = os.path.join(PREDICTIONS_DIR, f'{date_str}.json')
    json_data = {
        'date_beijing': date_str,
        'generated': datetime.now().isoformat(),
        'total_matches': len(results),
        'predictions': [],
        'matches': []
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
            entry['expected_goals_a'] = p.get('expected_goals_a', 0)
            entry['expected_goals_b'] = p.get('expected_goals_b', 0)
            entry['scoreline_probs'] = p.get('scoreline_probs', [])
            entry['verdict'] = v['result']
            entry['confidence'] = v['confidence']
            entry['error'] = None
            # Save full audit for generate_daily_report.py compatibility
            json_data['matches'].append({
                'audit': dict(r['audit']),
                'schedule': r['match']
            })
        else:
            entry['error'] = r.get('error', 'unknown')
        json_data['predictions'].append(entry)

    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
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
    
    # v5.2: Objective factors summary
    print_objective_factors(results)


def print_objective_factors(results):
    """Print objective condition factors table (v5.2)."""
    has_factors = False
    for r in results:
        if not r['audit']:
            continue
        layers = r['audit'].get('layers', {})
        wa = layers.get('4a_weather', {})
        sd = layers.get('4b_schedule_density', {})
        wd = wa.get('weather_details', {})
        if wd.get('precip_category', 'none') != 'none' or wa.get('team_a_adj', 0) or wa.get('team_b_adj', 0) or sd.get('team_a_adj', 0) or sd.get('team_b_adj', 0):
            has_factors = True
            break
    
    if not has_factors:
        return
    
    print(f"\n{'─' * 60}")
    print(f"🌧️ 客观条件因子 (v5.2 实验性)")
    print(f"{'─' * 60}")
    print(f"{'比赛':<28} {'降水':>8} {'风力':>8} {'赛程密度':>10}")
    
    for r in results:
        if not r['audit']:
            continue
        m = r['match']
        layers = r['audit'].get('layers', {})
        wa = layers.get('4a_weather', {})
        sd = layers.get('4b_schedule_density', {})
        wd = wa.get('weather_details', {})
        
        cn_a = TEAM_PROFILES.get(m['team_a'], {}).get('name_cn', m['team_a'])
        cn_b = TEAM_PROFILES.get(m['team_b'], {}).get('name_cn', m['team_b'])
        
        precip_cat = wd.get('precip_category', 'none')
        precip_label = {'none': '无', 'light': '小雨', 'moderate': '中雨', 'heavy': '⚡暴雨'}.get(precip_cat, precip_cat)
        wind_label = wd.get('wind_category', '?')
        if wd.get('indoor', False):
            wind_label = '室内'
        
        dens_a = sd.get('team_a_adj', 0)
        dens_b = sd.get('team_b_adj', 0)
        dens_label = '均衡' if dens_a == 0 and dens_b == 0 else f"{dens_a:+d}/{dens_b:+d}"
        
        match_label = f"{cn_a}vs{cn_b}"
        print(f"{match_label:<28} {precip_label:>8} {wind_label:>8} {dens_label:>10}")
    
    print(f"⚠️ 本模块为实验性因子，权重较低 (天气5%/赛程3%)，仅供参考")
    print(f"{'─' * 60}")


def format_objective_factors_md(results):
    """Generate markdown section for objective factors (v5.2)."""
    has_factors = False
    for r in results:
        if not r['audit']:
            continue
        layers = r['audit'].get('layers', {})
        wa = layers.get('4a_weather', {})
        sd = layers.get('4b_schedule_density', {})
        wd = wa.get('weather_details', {})
        if wd.get('precip_category', 'none') != 'none' or wa.get('team_a_adj', 0) or wa.get('team_b_adj', 0) or sd.get('team_a_adj', 0) or sd.get('team_b_adj', 0):
            has_factors = True
            break
    
    if not has_factors:
        return []
    
    lines = [
        "",
        "---",
        "",
        "## 🌧️ 客观条件因子 (v5.2 实验性)",
        "",
        "| 比赛 | 降水 | 温度 | 风力 | 赛程密度 | 备注 |",
        "|------|------|------|------|----------|------|",
    ]
    
    for r in results:
        if not r['audit']:
            continue
        m = r['match']
        layers = r['audit'].get('layers', {})
        wa = layers.get('4a_weather', {})
        sd = layers.get('4b_schedule_density', {})
        wd = wa.get('weather_details', {})
        
        cn_a = TEAM_PROFILES.get(m['team_a'], {}).get('name_cn', m['team_a'])
        cn_b = TEAM_PROFILES.get(m['team_b'], {}).get('name_cn', m['team_b'])
        
        precip_cat = wd.get('precip_category', 'none')
        precip_labels = {'none': '无', 'light': '小雨', 'moderate': '中雨', 'heavy': '⚡暴雨'}
        precip_label = precip_labels.get(precip_cat, precip_cat)
        
        temp = wd.get('temp_c', '?')
        wind_label = wd.get('wind_category', '?')
        if wd.get('indoor', False):
            wind_label = '室内'
        
        dens_a = sd.get('team_a_adj', 0)
        dens_b = sd.get('team_b_adj', 0)
        dens_label = '均衡' if dens_a == 0 and dens_b == 0 else f"{dens_a:+d}/{dens_b:+d}"
        
        notes = []
        if precip_cat == 'heavy':
            notes.append("技术型队受雨影响更大")
        if abs(dens_a) >= 10 or abs(dens_b) >= 10:
            notes.append("赛程不对称")
        note_str = '; '.join(notes) if notes else '-'
        
        lines.append(f"| {cn_a}vs{cn_b} | {precip_label} | {temp}°C | {wind_label} | {dens_label} | {note_str} |")
    
    lines.append("")
    lines.append("> ⚠️ 本模块为实验性因子，权重较低 (天气5%/赛程3%)，仅供附加参考，不做方向性判断。")
    lines.append("")
    
    return lines


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
