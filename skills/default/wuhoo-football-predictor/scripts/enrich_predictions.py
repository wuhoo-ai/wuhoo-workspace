#!/usr/bin/env python3.11
"""
enrich_predictions.py — 为 daily JSON 注入分模型预测 + ELO 轨迹

问题：predict_by_date.py 的 daily JSON 只存 ensemble 值，缺少：
  - Poisson 分模型（从 expected_goals 独立计算）
  - Logit 分模型（ordered_logit 查表）
  - ELO 轨迹（elo_trajectory）

用法：
  python3.11 scripts/enrich_predictions.py --date 2026-07-15
  python3.11 scripts/enrich_predictions.py --all       # enrich 所有 daily JSON
  python3.11 scripts/enrich_predictions.py --latest    # 仅最新一份

也可作为模块导入：
  from scripts.enrich_predictions import enrich_match, enrich_daily_json
"""

import json, math, os, sys, argparse
from datetime import datetime

WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(WORKDIR, "data")
DAILY_DIR = os.path.join(DATA, "daily_predictions")

sys.path.insert(0, os.path.join(WORKDIR, "scripts"))
from ordered_logit import predict_outcome as ol_predict
from elo_trajectory import get_trajectory_adjustments


def poisson_split(xg_a, xg_b, max_goals=7):
    """从预期进球独立计算 Poisson 胜平负概率（0-7×0-7 全矩阵）"""
    p_w = p_d = p_l = 0.0
    for ga in range(0, max_goals + 1):
        for gb in range(0, max_goals + 1):
            prob_a = (xg_a ** ga * math.exp(-xg_a) / math.factorial(ga)) if xg_a > 0 else (1.0 if ga == 0 else 0)
            prob_b = (xg_b ** gb * math.exp(-xg_b) / math.factorial(gb)) if xg_b > 0 else (1.0 if gb == 0 else 0)
            prob = prob_a * prob_b
            if ga > gb:
                p_w += prob
            elif ga == gb:
                p_d += prob
            else:
                p_l += prob
    total = p_w + p_d + p_l
    if total > 0:
        return round(p_w / total * 100), round(p_d / total * 100), round(p_l / total * 100)
    return 33, 34, 33


def enrich_match(audit, elo_ratings, trajectory_data, is_knockout=True):
    """
    为单场比赛的 audit 注入 sub_models + e_data.trajectory。

    Args:
        audit: match audit dict (from daily JSON)
        elo_ratings: {team_name: elo_value} dict
        trajectory_data: {team_name: trajectory_dict} from get_trajectory_adjustments()
        is_knockout: 是否淘汰赛（影响 Logit 查表选择）
    Returns:
        audit (mutated in-place, also returned)
    """
    pred = audit.get('prediction', {})
    ta = audit.get('team_a', '')
    tb = audit.get('team_b', '')
    if not ta or not tb:
        return audit

    # ── Poisson split ──
    xga = float(pred.get('expected_goals_a', 1.0))
    xgb = float(pred.get('expected_goals_b', 1.0))
    pw, pd_, pl = poisson_split(xga, xgb)

    # ── Logit split ──
    elo_a = elo_ratings.get(ta, 1500)
    elo_b = elo_ratings.get(tb, 1500)
    elo_diff = elo_a - elo_b
    lw_raw, ld_raw, ll_raw = ol_predict(elo_diff, knockout=is_knockout)
    lw, ld, ll = round(lw_raw * 100), round(ld_raw * 100), round(ll_raw * 100)

    # ── Sub-models ──
    audit['sub_models'] = {
        'ensemble': {
            'team_a_win': pred.get('team_a_win', 0),
            'draw': pred.get('draw', 0),
            'team_b_win': pred.get('team_b_win', 0),
        },
        'poisson': {'team_a_win': pw, 'draw': pd_, 'team_b_win': pl},
        'logit': {'team_a_win': lw, 'draw': ld, 'team_b_win': ll},
        'expected_goals': {'a': xga, 'b': xgb},
    }

    # ── ELO trajectory ──
    t_a = trajectory_data.get(ta, {})
    t_b = trajectory_data.get(tb, {})
    if t_a or t_b:
        audit['e_data'] = {'trajectory': {ta: dict(t_a), tb: dict(t_b)}}

    return audit


def enrich_daily_json(date_str, elo_ratings=None, trajectory_data=None):
    """
    Enrich a daily predictions JSON file.

    Args:
        date_str: 'YYYY-MM-DD' date string
        elo_ratings: pre-loaded ELO dict (loads from file if None)
        trajectory_data: pre-loaded trajectory dict (loads from file if None)
    Returns:
        dict with keys: file_path, matches_enriched, sub_models_added
    """
    fpath = os.path.join(DAILY_DIR, f'{date_str}.json')
    if not os.path.exists(fpath):
        return {'error': f'File not found: {fpath}'}

    # Load data
    if elo_ratings is None:
        elo_path = os.path.join(DATA, 'elo_ratings.json')
        elo_ratings = json.load(open(elo_path))
    if isinstance(elo_ratings, dict) and 'ratings' in elo_ratings:
        elo_ratings = {k: v.get('elo', v) if isinstance(v, dict) else v
                       for k, v in elo_ratings['ratings'].items()}

    if trajectory_data is None:
        trajectory_data = get_trajectory_adjustments()

    daily = json.load(open(fpath))
    matches = daily.get('matches', daily.get('predictions', []))
    enriched = 0
    has_sub_models = 0

    for m in matches:
        audit = m.get('audit', {})
        if audit.get('sub_models'):
            has_sub_models += 1
            continue

        # Determine if knockout from schedule data
        is_ko = True  # default to knockout for safety
        sched = m.get('schedule', {})
        rnd = sched.get('round', audit.get('round', ''))
        if rnd and 'Group' in str(rnd):
            is_ko = False

        enrich_match(audit, elo_ratings, trajectory_data, is_knockout=is_ko)
        enriched += 1

    json.dump(daily, open(fpath, 'w'), indent=2, ensure_ascii=False)

    result = {
        'file_path': fpath,
        'total_matches': len(matches),
        'already_had_sub_models': has_sub_models,
        'newly_enriched': enriched,
    }
    if enriched > 0:
        # Print summary
        for m in matches:
            audit = m.get('audit', {})
            sm = audit.get('sub_models', {})
            if sm:
                poi = sm.get('poisson', {})
                log = sm.get('logit', {})
                print(f"  {audit.get('team_a','?')} vs {audit.get('team_b','?')}: "
                      f"Poisson={poi.get('team_a_win','?')}/{poi.get('draw','?')}/{poi.get('team_b_win','?')} "
                      f"Logit={log.get('team_a_win','?')}/{log.get('draw','?')}/{log.get('team_b_win','?')}")

    return result


def enrich_all(elo_ratings=None, trajectory_data=None):
    """Enrich all daily prediction JSONs that lack sub_models."""
    if not os.path.isdir(DAILY_DIR):
        return {'error': f'Daily dir not found: {DAILY_DIR}'}

    if elo_ratings is None:
        elo_path = os.path.join(DATA, 'elo_ratings.json')
        elo_ratings = json.load(open(elo_path))
    if isinstance(elo_ratings, dict) and 'ratings' in elo_ratings:
        elo_ratings = {k: v.get('elo', v) if isinstance(v, dict) else v
                       for k, v in elo_ratings['ratings'].items()}

    if trajectory_data is None:
        trajectory_data = get_trajectory_adjustments()

    results = []
    for fname in sorted(os.listdir(DAILY_DIR)):
        if not fname.endswith('.json'):
            continue
        date_str = fname.replace('.json', '')
        # Only process date-format files (skip special ones like 2026-07-08_qf.json)
        if not date_str[:4].isdigit():
            continue
        r = enrich_daily_json(date_str, elo_ratings, trajectory_data)
        results.append(r)

    total_enriched = sum(r.get('newly_enriched', 0) for r in results)
    print(f"\nAll done: {total_enriched} matches enriched across {len(results)} files")
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enrich daily predictions with sub-models + ELO trajectory')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--date', type=str, help='Enrich specific date (YYYY-MM-DD)')
    group.add_argument('--all', action='store_true', help='Enrich all daily JSONs')
    group.add_argument('--latest', action='store_true', help='Enrich only the most recent daily JSON')

    args = parser.parse_args()

    if args.all:
        enrich_all()
    elif args.latest:
        files = sorted([f for f in os.listdir(DAILY_DIR) if f.endswith('.json') and f[:4].isdigit()])
        if files:
            latest = files[-1].replace('.json', '')
            print(f"Enriching latest: {latest}")
            enrich_daily_json(latest)
        else:
            print("No daily JSONs found")
    elif args.date:
        enrich_daily_json(args.date)
