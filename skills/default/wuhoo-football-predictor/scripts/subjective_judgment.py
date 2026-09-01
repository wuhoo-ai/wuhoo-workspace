#!/usr/bin/env python3.11
"""
subjective_judgment.py — 纯 web 驱动的独立主观判断

完全独立于预测管线：不读取 ELO、injuries.json、team_tactics.json 或任何管线脚本。
仅基于 web_fetch/web_search 获取的最新资讯做独立判断。

用法:
  # 模式 1: agent 收集 web 数据后，传入结构化结果
  python3.11 scripts/subjective_judgment.py --team-a France --team-b Spain --date 2026-07-15 \
    --verdict draw --confidence medium --score "1-1" \
    --reasoning "法国中场控制力强但西班牙传控可抵消..." \
    --factors "Mbappé状态成疑" "Rodri复出" "交手3次平局" \
    --source "The Athletic|https://...|France's attacking..." \
    --source "ESPN|https://...|Rodri return..."

  # 模式 2: 从 JSON 文件加载
  python3.11 scripts/subjective_judgment.py --from-json /tmp/judgment_input.json

  # 模式 3: 查看已有判断
  python3.11 scripts/subjective_judgment.py --show --team-a France --team-b Spain --date 2026-07-15

输出: data/subjective/{date}_{TeamA}_vs_{TeamB}.json
"""
import json, os, sys, argparse
from datetime import datetime

WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(WORKDIR, "data")
SUBJ_DIR = os.path.join(DATA, "subjective")
os.makedirs(SUBJ_DIR, exist_ok=True)


def save_judgment(team_a, team_b, date, verdict, confidence='medium',
                  predicted_score='', reasoning='', key_factors=None,
                  sources=None, model_prediction=None):
    """
    Save a subjective judgment to JSON.

    Args:
        team_a, team_b: team names (English)
        date: match date YYYY-MM-DD
        verdict: 'team_a_win' | 'draw' | 'team_b_win'
        confidence: 'high' | 'medium' | 'low'
        predicted_score: e.g. '1-1' or ''
        reasoning: 1-2 sentence summary
        key_factors: list of bullet points
        sources: list of {title, url, site} dicts
        model_prediction: optional string like "France 胜 (62%)" for divergence
    """
    # Compute divergence
    divergence = 'none'
    model_says = ''
    subjective_says = ''
    if model_prediction:
        # Team name CN mapping for comparison
        TEAM_CN_SUBJ = {
            'France': '法国', 'Spain': '西班牙', 'England': '英格兰', 'Argentina': '阿根廷',
            'Germany': '德国', 'Brazil': '巴西', 'Netherlands': '荷兰', 'Portugal': '葡萄牙',
            'Belgium': '比利时', 'Morocco': '摩洛哥', 'Norway': '挪威', 'Switzerland': '瑞士',
        }
        verdict_cn = {'team_a_win': f'{team_a} 胜', 'draw': '平局', 'team_b_win': f'{team_b} 胜'}
        subj_en = verdict_cn.get(verdict, verdict)
        # Translate to CN for comparison
        for en, cn_name in TEAM_CN_SUBJ.items():
            subj_en = subj_en.replace(en, cn_name)
        model_dir = model_prediction.split('(')[0].strip() if '(' in model_prediction else model_prediction
        if subj_en != model_dir:
            divergence = 'significant'
        else:
            divergence = 'consistent'
        model_says = model_prediction
        subjective_says = subj_en

    judgment = {
        'team_a': team_a,
        'team_b': team_b,
        'date': date,
        'generated': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        'verdict': verdict,
        'confidence': confidence,
        'predicted_score': predicted_score,
        'reasoning': reasoning,
        'key_factors': key_factors or [],
        'divergence_from_model': {
            'model_says': model_says,
            'subjective_says': subjective_says,
            'divergence': divergence,
        },
        'sources': sources or [],
    }

    fname = f'{date}_{team_a}_vs_{team_b}.json'
    fpath = os.path.join(SUBJ_DIR, fname)
    json.dump(judgment, open(fpath, 'w'), indent=2, ensure_ascii=False)
    print(f'Saved: {fpath}')
    return fpath


def load_judgment(team_a, team_b, date):
    """Load existing subjective judgment. Returns None if not found."""
    fname = f'{date}_{team_a}_vs_{team_b}.json'
    fpath = os.path.join(SUBJ_DIR, fname)
    if os.path.exists(fpath):
        return json.load(open(fpath))
    # Try reversed order
    fname_rev = f'{date}_{team_b}_vs_{team_a}.json'
    fpath_rev = os.path.join(SUBJ_DIR, fname_rev)
    if os.path.exists(fpath_rev):
        return json.load(open(fpath_rev))
    return None


def list_judgments():
    """List all saved subjective judgments."""
    if not os.path.isdir(SUBJ_DIR):
        return []
    return sorted([f for f in os.listdir(SUBJ_DIR) if f.endswith('.json')])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='主观判断生成器 — 纯 web 驱动')
    parser.add_argument('--team-a', type=str, help='主队英文名')
    parser.add_argument('--team-b', type=str, help='客队英文名')
    parser.add_argument('--date', type=str, help='比赛日期 YYYY-MM-DD')
    parser.add_argument('--verdict', type=str, choices=['team_a_win', 'draw', 'team_b_win'],
                        help='判定方向')
    parser.add_argument('--confidence', type=str, default='medium',
                        choices=['high', 'medium', 'low'])
    parser.add_argument('--score', type=str, default='', help='预期比分 e.g. 1-1')
    parser.add_argument('--reasoning', type=str, default='', help='推理概述')
    parser.add_argument('--factors', type=str, nargs='*', default=[],
                        help='关键因素列表')
    parser.add_argument('--source', type=str, nargs='*', action='append', default=[],
                        help='来源: site|url|title')
    parser.add_argument('--model-prediction', type=str, default='',
                        help='管线预测结果，用于计算分歧 e.g. "France 胜 (62%)"')
    parser.add_argument('--from-json', type=str, help='从 JSON 文件加载判断数据')
    parser.add_argument('--show', action='store_true', help='显示已有判断')
    parser.add_argument('--list', action='store_true', help='列出所有判断')

    args = parser.parse_args()

    if args.list:
        files = list_judgments()
        if files:
            print(f'{len(files)} judgment(s):')
            for f in files:
                print(f'  {f}')
        else:
            print('No judgments found.')
        sys.exit(0)

    if args.show:
        if not args.team_a or not args.team_b or not args.date:
            print("--show requires --team-a, --team-b, --date")
            sys.exit(1)
        j = load_judgment(args.team_a, args.team_b, args.date)
        if j:
            print(json.dumps(j, indent=2, ensure_ascii=False))
        else:
            print(f'No judgment for {args.team_a} vs {args.team_b} on {args.date}')
        sys.exit(0)

    if args.from_json:
        data = json.load(open(args.from_json))
        save_judgment(
            team_a=data['team_a'], team_b=data['team_b'], date=data['date'],
            verdict=data['verdict'], confidence=data.get('confidence', 'medium'),
            predicted_score=data.get('predicted_score', ''),
            reasoning=data.get('reasoning', ''),
            key_factors=data.get('key_factors', []),
            sources=data.get('sources', []),
            model_prediction=data.get('model_prediction', ''),
        )
        sys.exit(0)

    if args.verdict:
        if not args.team_a or not args.team_b or not args.date:
            print("--team-a, --team-b, --date are required")
            sys.exit(1)
        sources = []
        for s_list in args.source:
            for s in s_list:
                parts = s.split('|', 2)
                if len(parts) >= 3:
                    sources.append({'site': parts[0], 'url': parts[1], 'title': parts[2]})
        save_judgment(
            team_a=args.team_a, team_b=args.team_b, date=args.date,
            verdict=args.verdict, confidence=args.confidence,
            predicted_score=args.score, reasoning=args.reasoning,
            key_factors=args.factors, sources=sources,
            model_prediction=args.model_prediction,
        )
    else:
        parser.print_help()
