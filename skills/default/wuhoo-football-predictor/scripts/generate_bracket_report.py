#!/usr/bin/env python3
"""WC2026 Bracket Report Generator — v5.9

Generates a daily markdown report of full tournament knockout simulation results.
Compatible with both bracket_simulator.py and bracket_recursive.py outputs.

Usage:
  python3.11 scripts/generate_bracket_report.py
  python3.11 scripts/generate_bracket_report.py --from-json data/bracket_recursive_results.json
"""

import sys, os, json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, 'data')

def load_team_cn_map():
    """Load simplified team name mapping from team_profiles.json."""
    with open(os.path.join(DATA_DIR, 'team_profiles.json')) as f:
        tp = json.load(f)
    cn_map = {}
    for name, info in tp.get('teams', {}).items():
        cn_map[name] = info.get('name_cn', name)
    return cn_map

def generate_markdown_report(stats, cn_map):
    """Generate a compact markdown report (WeChat-friendly).
    
    Compatible with bracket_simulator output (champion/r16/qf keys) and
    bracket_recursive output (champion_probs/advancement_probs keys).
    """
    # Compatibility: detect format and normalize
    if 'champion_probs' in stats:
        n_sims = stats['n_sims']
        champ_data = stats['champion_probs']
        adv_data = stats.get('advancement_probs', {})
        is_recursive_format = True
    else:
        n_sims = stats.get('n_sims', stats.get('total_sims', 0))
        champ_data = stats.get('champion', {})
        adv_data = {}
        is_recursive_format = False

    lines = []
    lines.append(f"# WC2026 全赛事推演报告")
    lines.append(f"")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} BJT | {n_sims} 次 Monte Carlo")
    lines.append("")
    lines.append("## 一、夺冠概率 Top 10")
    lines.append("")
    lines.append("| # | 球队 | 概率 |")
    lines.append("|---|------|------|")
    for i, (team, pct) in enumerate(list(champ_data.items())[:10]):
        cn = cn_map.get(team, team)
        bar = '█' * int(pct / 2)
        lines.append(f"| {i+1} | {cn} ({team}) | {pct:.1f}% {bar} |")

    # Stage advancement
    lines.append("")
    lines.append("## 二、各阶段晋级概率")
    lines.append("")
    if is_recursive_format:
        lines.append("| 球队 | R16→QF | →SF | →F | 夺冠 |")
        lines.append("|------|--------|-----|----|------|")
    else:
        lines.append("| 球队 | R32→R16 | →QF | →SF | →Final | 夺冠 |")
        lines.append("|------|---------|-----|-----|--------|------|")

    top_teams = list(champ_data.keys())[:15]
    for team in top_teams:
        cn = cn_map.get(team, team)
        ch = champ_data.get(team, 0)
        if is_recursive_format:
            stages = adv_data.get(team, {})
            lines.append(f"| {cn} | {stages.get('QF',0):.1f}% | {stages.get('SF',0):.1f}% | {stages.get('F',0):.1f}% | {ch:.1f}% |")
        else:
            r16 = stats.get('r16', {}).get(team, 0)
            qf = stats.get('quarterfinalist', {}).get(team, 0)
            sf = stats.get('semifinalist', {}).get(team, 0)
            fn = stats.get('finalist', {}).get(team, 0)
            lines.append(f"| {cn} | {r16:.1f}% | {qf:.1f}% | {sf:.1f}% | {fn:.1f}% | {ch:.1f}% |")

    # Dark horse alert
    lines.append("")
    lines.append("## 三、暗马预警")
    lines.append("")
    lines.append("> 暗马定义: 夺冠概率 > 3% 且 ELO 排名 > 12")
    lines.append("")

    try:
        with open(os.path.join(DATA_DIR, 'elo_ratings.json')) as f:
            elo_data = json.load(f)
        elo_rank = {}
        ratings = elo_data.get('ratings', elo_data)
        sorted_teams = sorted(ratings.items(), key=lambda x: (
            x[1].get('elo', 0) if isinstance(x[1], dict) else x[1]
        ), reverse=True)
        for rank, (team, val) in enumerate(sorted_teams, 1):
            elo_rank[team] = rank

        found = False
        for team, pct in champ_data.items():
            rank = elo_rank.get(team, 99)
            if pct > 3 and rank > 12:
                cn = cn_map.get(team, team)
                lines.append(f"- **{cn}** ({pct:.1f}%): ELO排名第{rank}")
                found = True
        if not found:
            lines.append("- 暂无符合条件的暗马")
    except Exception as e:
        lines.append(f"- (ELO数据不可用，跳过暗马分析: {e})")

    # Notes
    lines.append("")
    lines.append("## 四、说明")
    lines.append("")
    lines.append(f"- 推演基于 {n_sims} 次 Monte Carlo 模拟")
    lines.append("- 每场淘汰赛使用 v5.9 12层预测栈 + KBC淘汰赛行为校准")
    lines.append("- 加时赛/点球大战已纳入晋级概率计算")
    if n_sims <= 10:
        lines.append("- ⚠️ 10次模拟仅有方向性参考价值，冠军概率可能有 10-20% 波动")
    lines.append("- 数据时效: 基于今日赛果和ELO")

    return '\n'.join(lines)

def main():
    n_sims = 5000
    from_json = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--sims' and i + 1 < len(args):
            n_sims = int(args[i+1])
            i += 2
        elif args[i] == '--from-json' and i + 1 < len(args):
            from_json = args[i+1]
            i += 2
        else:
            i += 1

    cn_map = load_team_cn_map()

    if from_json:
        with open(from_json) as f:
            stats = json.load(f)
    else:
        # Run simulation
        from bracket_simulator import run_simulation
        stats = run_simulation(n_sims=n_sims)

    # Generate markdown
    md = generate_markdown_report(stats, cn_map)

    # Save markdown
    today = datetime.now().strftime('%Y-%m-%d')
    md_path = os.path.join(DATA_DIR, 'reports', f'bracket_report_{today}.md')
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, 'w') as f:
        f.write(md)
    print(f"✅ Markdown report saved to {md_path}")

    # Also print to stdout
    print(md)

    return md

if __name__ == '__main__':
    main()
