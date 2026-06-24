#!/usr/bin/env python3.11
"""
predict_v55.py — v5.5 Inference Engine Wrapper
================================================
Wraps wc2026_predict.predict_single_match with the v5.5 rule engine.
Zero modification to the existing prediction pipeline.

Usage:
  from scripts.predict_v55 import predict_with_engine
  result = predict_with_engine('Brazil', 'Scotland', matchday=3)

The wrapper:
1. Runs InferenceEngine to compute ELO deltas
2. Passes deltas as manual_adjustments to predict_single_match
3. Injects inference trace into the audit output
"""

import json, os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from wc2026_predict import predict_single_match
from scripts.data_provider import DataProvider
from scripts.inference_engine import InferenceEngine


def predict_with_engine(team_a, team_b, venue_name=None, enable_news=False,
                        manual_adjustments=None, knockout=False, match_id=None,
                        matchday=None, rules_version="v1"):
    """
    Predict a single match using the v5.5 rule inference engine.
    
    Uses the engine to compute ELO adjustments, then delegates to
    predict_single_match for Poisson + verdict.
    
    Args:
        Same as predict_single_match, plus:
        rules_version: "v1" or "v2" for A/B testing
    
    Returns:
        dict with full audit trail including inference trace
    """
    if manual_adjustments is None:
        manual_adjustments = {}
    
    # Load rules
    rules_path = os.path.join(BASE_DIR, 'configs', f'rules_{rules_version}.json')
    if not os.path.exists(rules_path):
        # Fallback to original prediction
        return predict_single_match(
            team_a, team_b, venue_name=venue_name, enable_news=enable_news,
            manual_adjustments=manual_adjustments, knockout=knockout,
            match_id=match_id, matchday=matchday
        )
    
    # Initialize engine
    dp = DataProvider()
    engine = InferenceEngine(rules_path)
    
    # Build contexts
    ctx_a = dp.build_context(team_a, team_b, matchday=matchday, match_id=match_id)
    ctx_b = dp.build_context(team_b, team_a, matchday=matchday, match_id=match_id)
    
    # Inject computed values into context
    try:
        from wc2026_predict import compute_meta_adjustment
        meta_a, _ = compute_meta_adjustment(team_a)
        meta_b, _ = compute_meta_adjustment(team_b)
        ctx_a['coach_meta_adjustment'] = meta_a
        ctx_b['coach_meta_adjustment'] = meta_b
    except Exception:
        ctx_a['coach_meta_adjustment'] = 0
        ctx_b['coach_meta_adjustment'] = 0
    
    ctx_a['friendly_form'] = dp.get_friendly_form(team_a)
    ctx_b['friendly_form'] = dp.get_friendly_form(team_b)
    ctx_a['tournament_form'] = dp.get_tournament_form(team_a)
    ctx_b['tournament_form'] = dp.get_tournament_form(team_b)
    ctx_a['manual_adjustment'] = manual_adjustments.get(team_a, 0)
    ctx_b['manual_adjustment'] = manual_adjustments.get(team_b, 0)
    ctx_a['venue_adjustment'] = 0
    ctx_a['weather_adjustment'] = 0
    ctx_a['density_adjustment'] = 0
    ctx_a['bpp_adjustment'] = 0
    ctx_b['venue_adjustment'] = 0
    ctx_b['weather_adjustment'] = 0
    ctx_b['density_adjustment'] = 0
    ctx_b['bpp_adjustment'] = 0
    
    # Run inference
    result_a = engine.reason(ctx_a, ctx_b)
    result_b = engine.reason(ctx_b, ctx_a)
    
    delta_a = result_a['delta']
    delta_b = result_b['delta']
    
    # Pass engine deltas as manual adjustments to existing pipeline
    # This adds engine-computed deltas on top of base ELO
    engine_adjustments = dict(manual_adjustments)
    engine_adjustments[team_a] = engine_adjustments.get(team_a, 0) + delta_a
    engine_adjustments[team_b] = engine_adjustments.get(team_b, 0) + delta_b
    
    # Run standard prediction with engine deltas baked in
    result = predict_single_match(
        team_a, team_b,
        venue_name=venue_name,
        enable_news=enable_news,
        manual_adjustments=engine_adjustments,
        knockout=knockout,
        match_id=match_id,
        matchday=matchday
    )
    
    # Inject engine trace into result
    result['inference_engine'] = True
    result['inference_engine_version'] = rules_version
    result['inference_trace'] = {
        'team_a': {
            'delta': delta_a,
            'raw_sum': result_a['raw_sum'],
            'saturated': result_a['saturated'],
            'trace': result_a['trace'],
        },
        'team_b': {
            'delta': delta_b,
            'raw_sum': result_b['raw_sum'],
            'saturated': result_b['saturated'],
            'trace': result_b['trace'],
        },
    }
    
    # Format reasoning path
    result['reasoning_path'] = (
        engine.format_trace(team_a, result_a) + '\n' +
        engine.format_trace(team_b, result_b)
    )
    
    # Add engine contribution to effective ELO
    if 'effective_elo' in result:
        result['effective_elo']['engine_delta_a'] = delta_a
        result['effective_elo']['engine_delta_b'] = delta_b
    
    return result


def predict_batch_with_engine(date_str, rules_version="v1"):
    """
    Predict all matches on a given date using the inference engine.
    
    Args:
        date_str: Beijing date string (e.g., '2026-06-25')
        rules_version: "v1" or "v2"
    
    Returns:
        list of (match_info, audit) tuples
    """
    from wc2026_predict import _get_schedule, _save_prediction_history
    
    sched = _get_schedule()
    matches = [m for m in sched['matches'] if m['date_beijing'] == date_str]
    
    if not matches:
        print(f"✅ {date_str}: 无比赛安排")
        return [], date_str
    
    # Load manual adjustments
    manual_adj = {}
    try:
        madj_path = os.path.join(BASE_DIR, 'data', 'manual_adjustments.json')
        if os.path.exists(madj_path):
            with open(madj_path) as f:
                madj_data = json.load(f)
            for team, adj in madj_data.get('adjustments', {}).items():
                manual_adj[team] = adj.get('elo_adjustment', 0)
            if manual_adj:
                teams_str = ', '.join(f'{t}({v:+d})' for t, v in manual_adj.items())
                print(f"📌 手动调整 (Layer 6): {len(manual_adj)} 队 — {teams_str}")
    except Exception:
        pass
    
    results = []
    for m in matches:
        matchday_val = m.get('matchday')
        print(f"🔄 预测: {m['team_a']} vs {m['team_b']} (Match #{m['match_id']})...")
        try:
            audit = predict_with_engine(
                m['team_a'], m['team_b'],
                venue_name=m.get('venue'),
                knockout=False,
                match_id=m.get('match_id'),
                matchday=matchday_val,
                manual_adjustments=manual_adj,
                rules_version=rules_version
            )
            audit['schedule'] = m
            _save_prediction_history(audit)
            results.append({'match': m, 'audit': audit})
            print(f"   ✅ {audit['verdict']['result']}")
        except Exception as e:
            print(f"   ❌ 预测失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({'match': m, 'audit': None, 'error': str(e)})
    
    return results, date_str


# === Standalone test ===
if __name__ == "__main__":
    print("=== predict_v55.py Test ===\n")
    
    # Test single match
    result = predict_with_engine('Brazil', 'Scotland', matchday=3)
    print(f"Engine used: {result.get('inference_engine', False)}")
    print(f"Delta A: {result.get('inference_trace', {}).get('team_a', {}).get('delta', '?')}")
    print(f"Delta B: {result.get('inference_trace', {}).get('team_b', {}).get('delta', '?')}")
    print(f"Verdict: {result['verdict']['result']}")
    print(f"Reasoning path length: {len(result.get('reasoning_path', ''))} chars\n")
    
    # Print reasoning path
    print("--- REASONING PATH ---")
    print(result.get('reasoning_path', 'N/A')[:800])
    
    print("\n✅ Test passed")
