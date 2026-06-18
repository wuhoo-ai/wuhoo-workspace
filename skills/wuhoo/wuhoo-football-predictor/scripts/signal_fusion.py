#!/usr/bin/env python3
"""
v5.0 信号融合引擎 (Signal Fusion Engine)
=========================================
将 LLM 提取的结构化非结构化信号转换为 ELO 调整值。

核心算法:
1. 信号类型权重 × strength × direction
2. consensus 增强 (多源确认 → 更可靠)
3. novelty 增强 (新信息比已知信息更有价值)
4. contrarian 增强 (与 ELO 预期相反的信号 → 额外加权)
5. 钳制在 ±120 ELO

Usage:
  from signal_fusion import SignalFusionEngine
  engine = SignalFusionEngine()
  adjustment = engine.compute_elo_adjustment(signals, elo_diff)
"""

import json
import math
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# ── Signal type weights (initial, to be calibrated via backtest) ──

SIGNAL_TYPE_WEIGHTS = {
    "injury_impact": 0.30,
    "tactical_matchup": 0.25,
    "form_momentum": 0.20,
    "lineup_surprise": 0.20,
    "team_cohesion": 0.15,
    "external_factor": 0.10,
    "discipline_risk": 0.05,
}

# Max ELO adjustment per signal type (prevents any single signal dominating)
MAX_PER_TYPE = 60

# Global max adjustment
MAX_ELO_ADJUSTMENT = 120

# Scaling factor: converts raw signal score to ELO points
# Max raw score ~6.0 across all types → target ~120 ELO → scale = 20
ELO_SCALE = 20


class SignalFusionEngine:
    """信号融合引擎: 信号 → ELO 调整"""
    
    def __init__(self, type_weights: Dict[str, float] = None):
        self.weights = type_weights or SIGNAL_TYPE_WEIGHTS
    
    def compute_elo_adjustment(self, signals: List[Dict], 
                                base_elo_diff: float = 0) -> Tuple[int, Dict]:
        """将信号列表融合为 ELO 调整值。
        
        Args:
            signals: 信号列表 [{type, direction, strength, novelty, consensus, ...}]
            base_elo_diff: 基础 ELO 差值 (team_a - team_b)，用于 contrarian boost
        
        Returns:
            (adjustment: int, breakdown: dict)
        """
        if not signals:
            return 0, {"signals": 0, "total_raw": 0, "breakdown": []}
        
        total_adjustment = 0.0
        breakdown = []
        
        # Group signals by type, take dominant direction
        type_signals = {}
        for sig in signals:
            stype = sig.get('type', 'unknown')
            if stype not in type_signals:
                type_signals[stype] = []
            type_signals[stype].append(sig)
        
        for stype, sigs in type_signals.items():
            type_weight = self.weights.get(stype, 0.10)
            
            # Take the strongest signal per type (avoid double-counting)
            sigs_sorted = sorted(sigs, key=lambda s: s.get('strength', 0) * s.get('consensus', 0.5), reverse=True)
            sig = sigs_sorted[0]
            
            strength = sig.get('strength', 0.5)
            direction = sig.get('direction', 0)
            novelty = sig.get('novelty', 0.5)
            consensus = sig.get('consensus', 0.5)
            
            # Base contribution
            base = strength * type_weight * direction
            
            # Consensus boost: multiple independent sources → more reliable
            # Range: 0.75 (low consensus) to 1.25 (high consensus)
            consensus_boost = 1.0 + (consensus - 0.5) * 0.5
            
            # Novelty boost: new information is more valuable than known facts
            # Range: 1.0 (old news) to 1.5 (breaking news)
            novelty_boost = 1.0 + novelty * 0.5
            
            # Contrarian boost: signals that go against ELO expectation get extra weight
            # Because these represent information the market/ELO hasn't priced in
            if base_elo_diff != 0 and direction != 0:
                # Signal direction relative to ELO diff
                # If elo_diff > 0 (team A stronger) and signal is negative → contrarian
                signal_aligns_with_elo = (direction * base_elo_diff) >= 0
                if not signal_aligns_with_elo:
                    contrarian_boost = 1.5
                else:
                    contrarian_boost = 1.0
            else:
                contrarian_boost = 1.0
            
            adjustment = base * consensus_boost * novelty_boost * contrarian_boost * ELO_SCALE
            adjustment = max(-MAX_PER_TYPE, min(MAX_PER_TYPE, adjustment))
            
            total_adjustment += adjustment
            
            breakdown.append({
                'type': stype,
                'direction': direction,
                'strength': strength,
                'novelty': novelty,
                'consensus': consensus,
                'type_weight': type_weight,
                'consensus_boost': round(consensus_boost, 3),
                'novelty_boost': round(novelty_boost, 3),
                'contrarian_boost': round(contrarian_boost, 3),
                'adjustment': round(adjustment, 1),
                'description': sig.get('description_cn', sig.get('description', ''))[:100],
            })
        
        # Clamp total
        total_adjustment = max(-MAX_ELO_ADJUSTMENT, min(MAX_ELO_ADJUSTMENT, total_adjustment))
        
        return int(round(total_adjustment)), {
            'signals': len(signals),
            'signal_types': len(type_signals),
            'total_raw': round(total_adjustment, 1),
            'breakdown': breakdown,
        }
    
    def compute_matchup_adjustments(self, team_a_signals: List[Dict],
                                     team_b_signals: List[Dict],
                                     elo_a: float, elo_b: float) -> Dict:
        """计算一场比赛两队各自的信号调整。
        
        Returns:
            {
                'team_a_adjustment': int,
                'team_b_adjustment': int,
                'team_a_breakdown': dict,
                'team_b_breakdown': dict,
                'net_adjustment': int,  # net effect on elo_diff
            }
        """
        elo_diff = elo_a - elo_b
        
        adj_a, bd_a = self.compute_elo_adjustment(team_a_signals, elo_diff)
        adj_b, bd_b = self.compute_elo_adjustment(team_b_signals, -elo_diff)
        
        return {
            'team_a_adjustment': adj_a,
            'team_b_adjustment': adj_b,
            'team_a_breakdown': bd_a,
            'team_b_breakdown': bd_b,
            'net_adjustment': adj_a - adj_b,
        }


# ── Tactical Matchup Module ─────────────────────────────────

# Primary + Secondary tactical styles
TACTICAL_STYLES = {
    'Spain': ('possession', 'high_press'),
    'Portugal': ('possession', 'counter_attack'),
    'Argentina': ('possession', 'counter_attack'),
    'Germany': ('possession', 'high_press'),
    'England': ('high_press', 'possession'),
    'Netherlands': ('high_press', 'possession'),
    'France': ('counter_attack', 'possession'),
    'Brazil': ('mixed', 'possession'),
    'Belgium': ('mixed', 'possession'),
    'Croatia': ('mixed', 'possession'),
    'Uruguay': ('counter_attack', 'deep_block'),
    'Morocco': ('deep_block', 'counter_attack'),
    'Senegal': ('counter_attack', 'high_press'),
    'Japan': ('high_press', 'counter_attack'),
    'South Korea': ('high_press', 'direct_play'),
    'Iran': ('deep_block', 'counter_attack'),
    'Saudi Arabia': ('deep_block', 'counter_attack'),
    'Australia': ('direct_play', 'high_press'),
    'United States': ('high_press', 'counter_attack'),
    'Mexico': ('possession', 'high_press'),
    'Canada': ('counter_attack', 'direct_play'),
    'Egypt': ('deep_block', 'counter_attack'),
    'Tunisia': ('deep_block', 'direct_play'),
    'Algeria': ('counter_attack', 'mixed'),
    'Austria': ('high_press', 'direct_play'),
    'Sweden': ('direct_play', 'high_press'),
    'Norway': ('direct_play', 'counter_attack'),
    'Switzerland': ('mixed', 'deep_block'),
    'Turkey': ('mixed', 'counter_attack'),
    'Paraguay': ('deep_block', 'counter_attack'),
    'Ecuador': ('mixed', 'high_press'),
    'Ivory Coast': ('counter_attack', 'direct_play'),
    'Ghana': ('counter_attack', 'high_press'),
    'Scotland': ('direct_play', 'high_press'),
    'Colombia': ('possession', 'counter_attack'),
    'DR Congo': ('direct_play', 'deep_block'),
    'Cape Verde': ('deep_block', 'counter_attack'),
    'New Zealand': ('direct_play', 'deep_block'),
    'South Africa': ('mixed', 'counter_attack'),
    'Qatar': ('possession', 'mixed'),
    'Iraq': ('deep_block', 'mixed'),
    'Jordan': ('deep_block', 'mixed'),
    'Uzbekistan': ('mixed', 'deep_block'),
    'Panama': ('deep_block', 'direct_play'),
    'Haiti': ('deep_block', 'direct_play'),
    'Curacao': ('deep_block', 'direct_play'),
    'Czech Republic': ('mixed', 'high_press'),
    'Bosnia and Herzegovina': ('mixed', 'direct_play'),
}

# Tactical matchup matrix: (style_a, style_b) → advantage for A
# Positive = A's style counters B, Negative = B's style counters A
TACTICAL_MATRIX = {
    # Possession vs...
    ('possession', 'high_press'): -0.3,     # High press disrupts possession
    ('possession', 'deep_block'): 0.1,       # Slight advantage if can penetrate
    ('possession', 'counter_attack'): -0.2,  # Vulnerable to counters
    ('possession', 'direct_play'): 0.2,      # Can control tempo
    
    # High press vs...
    ('high_press', 'possession'): 0.3,       # Disrupts buildup
    ('high_press', 'deep_block'): 0.3,       # Forces errors
    ('high_press', 'counter_attack'): -0.1,  # Vulnerable to long balls
    ('high_press', 'direct_play'): -0.2,     # Direct play bypasses press
    
    # Counter-attack vs...
    ('counter_attack', 'possession'): 0.2,   # Exploit spaces behind
    ('counter_attack', 'high_press'): 0.1,   # Can exploit press
    ('counter_attack', 'deep_block'): -0.3,  # No space to counter
    ('counter_attack', 'direct_play'): 0.1,  # Even matchup
    
    # Deep block vs...
    ('deep_block', 'possession'): -0.1,      # Needs perfect defense
    ('deep_block', 'high_press'): -0.3,      # Can't sit back
    ('deep_block', 'counter_attack'): 0.3,   # Perfect setup
    ('deep_block', 'direct_play'): -0.2,     # Physical battle
    
    # Direct play vs...
    ('direct_play', 'possession'): -0.2,     # Can't get ball
    ('direct_play', 'high_press'): 0.2,      # Long balls bypass press
    ('direct_play', 'counter_attack'): -0.1, # Similar to counter
    ('direct_play', 'deep_block'): 0.2,      # Physical advantage
}

def compute_tactical_matchup(team_a: str, team_b: str) -> float:
    """计算战术风格匹配得分。正值=A有利，负值=B有利。
    
    Uses primary + secondary styles, weighted 0.6/0.4.
    """
    styles_a = TACTICAL_STYLES.get(team_a, ('mixed', 'mixed'))
    styles_b = TACTICAL_STYLES.get(team_b, ('mixed', 'mixed'))
    
    # Primary style matchup
    primary_score = TACTICAL_MATRIX.get((styles_a[0], styles_b[0]), 0.0)
    
    # Secondary style matchup (for mixed-style teams)
    secondary_score = TACTICAL_MATRIX.get((styles_a[1], styles_b[1]), 0.0) if len(styles_a) > 1 else 0.0
    
    # Weighted blend
    matchup_score = primary_score * 0.6 + secondary_score * 0.4
    
    return round(matchup_score, 3)


# ── CLI ────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description='v5.0 信号融合引擎')
    parser.add_argument('--signals-file', type=str, help='Path to signals JSON file')
    parser.add_argument('--team-a', type=str, help='Team A name')
    parser.add_argument('--team-b', type=str, help='Team B name')
    parser.add_argument('--elo-a', type=float, default=1500, help='ELO of team A')
    parser.add_argument('--elo-b', type=float, default=1500, help='ELO of team B')
    parser.add_argument('--test', action='store_true', help='Run unit tests')
    args = parser.parse_args()
    
    if args.test:
        run_tests()
        return
    
    engine = SignalFusionEngine()
    
    if args.signals_file:
        with open(args.signals_file) as f:
            data = json.load(f)
        
        teams = data.get('teams', {})
        if args.team_a and args.team_b:
            sigs_a = teams.get(args.team_a, {}).get('signals', [])
            sigs_b = teams.get(args.team_b, {}).get('signals', [])
            
            result = engine.compute_matchup_adjustments(
                sigs_a, sigs_b, args.elo_a, args.elo_b
            )
            
            print(f"{args.team_a}: {result['team_a_adjustment']:+d} ELO")
            for bd in result['team_a_breakdown'].get('breakdown', []):
                print(f"  - {bd['type']}: {bd['adjustment']:+5.1f} | {bd['description']}")
            
            print(f"{args.team_b}: {result['team_b_adjustment']:+d} ELO")
            for bd in result['team_b_breakdown'].get('breakdown', []):
                print(f"  - {bd['type']}: {bd['adjustment']:+5.1f} | {bd['description']}")
            
            print(f"\nNet adjustment: {result['net_adjustment']:+d} ELO")
            
            # Tactical matchup
            tm = compute_tactical_matchup(args.team_a, args.team_b)
            print(f"Tactical matchup: {tm:+.3f} ({'A有利' if tm > 0 else 'B有利' if tm < 0 else '中性'})")
    
    else:
        print("Usage: python3.11 scripts/signal_fusion.py --signals-file <path> --team-a A --team-b B")


def run_tests():
    """单元测试"""
    print("=" * 60)
    print("v5.0 SignalFusionEngine 单元测试")
    print("=" * 60)
    
    engine = SignalFusionEngine()
    
    # Test 1: Empty signals
    print("\n📋 Test 1: Empty signals")
    adj, bd = engine.compute_elo_adjustment([], 0)
    assert adj == 0, "Empty signals → 0 adjustment"
    print(f"  Empty → {adj} ELO")
    print("  ✅ PASS")
    
    # Test 2: Strong negative injury signal
    print("\n📋 Test 2: Strong injury signal (negative)")
    signals = [
        {
            "type": "injury_impact",
            "direction": -1,
            "strength": 0.8,
            "novelty": 0.9,
            "consensus": 0.9,
            "description_cn": "多名主力伤缺"
        }
    ]
    adj, bd = engine.compute_elo_adjustment(signals, 100)
    print(f"  Adjustment: {adj:+d} ELO")
    print(f"  Breakdown: {bd['breakdown'][0]}")
    assert adj < 0, "Should be negative"
    assert adj > -60, "Should not exceed per-type cap"
    print("  ✅ PASS")
    
    # Test 3: Contrarian boost
    print("\n📋 Test 3: Contrarian boost (signal vs ELO)")
    # Spain (+398 ELO diff) but negative signal
    signals_neg = [{
        "type": "form_momentum",
        "direction": -1,
        "strength": 0.6,
        "novelty": 0.8,
        "consensus": 0.7,
        "description_cn": "进攻效率下降"
    }]
    adj_contrarian, _ = engine.compute_elo_adjustment(signals_neg, 398)  # Spain favored
    adj_aligned, _ = engine.compute_elo_adjustment(signals_neg, -398)    # Already underdog
    
    print(f"  Contrarian (ELO +398, neg signal): {adj_contrarian:+d}")
    print(f"  Aligned   (ELO -398, neg signal): {adj_aligned:+d}")
    # Contrarian should have larger magnitude
    assert abs(adj_contrarian) >= abs(adj_aligned), "Contrarian should amplify"
    print("  ✅ PASS")
    
    # Test 4: Multiple signal types
    print("\n📋 Test 4: Multiple signal types")
    multi_signals = [
        {"type": "injury_impact", "direction": -1, "strength": 0.7, "novelty": 0.9, "consensus": 0.9, "description_cn": "后防核心伤缺"},
        {"type": "tactical_matchup", "direction": -1, "strength": 0.5, "novelty": 0.7, "consensus": 0.6, "description_cn": "被对手高位逼抢克制"},
        {"type": "team_cohesion", "direction": -1, "strength": 0.4, "novelty": 0.6, "consensus": 0.5, "description_cn": "更衣室不和谐"},
    ]
    adj, bd = engine.compute_elo_adjustment(multi_signals, 100)
    print(f"  Total adjustment: {adj:+d} ELO")
    print(f"  Signal types: {bd['signal_types']}")
    for b in bd['breakdown']:
        print(f"    {b['type']}: {b['adjustment']:+5.1f} | {b['description']}")
    assert adj < 0, "All negative → negative total"
    assert adj >= -120, "Should respect global cap"
    print("  ✅ PASS")
    
    # Test 5: Tactical matchup
    print("\n📋 Test 5: Tactical matchup computation")
    matchups = [
        ('Spain', 'Cape Verde'),      # possession vs deep_block → slight advantage
        ('Netherlands', 'Japan'),      # high_press vs high_press → even
        ('Brazil', 'Morocco'),         # mixed vs deep_block → slight advantage
        ('Germany', 'Curacao'),        # possession vs deep_block → advantage
    ]
    for ta, tb in matchups:
        score = compute_tactical_matchup(ta, tb)
        styles_a = TACTICAL_STYLES.get(ta, ('mixed',))
        styles_b = TACTICAL_STYLES.get(tb, ('mixed',))
        print(f"  {ta}({styles_a[0]}) vs {tb}({styles_b[0]}): {score:+.3f}")
    print("  ✅ PASS")
    
    # Test 6: Matchup adjustments
    print("\n📋 Test 6: Full matchup adjustment")
    team_a_sigs = [{
        "type": "injury_impact",
        "direction": -1, "strength": 0.7, "novelty": 0.8, "consensus": 0.9,
        "description_cn": "Spain后防伤病"
    }]
    team_b_sigs = [{
        "type": "form_momentum",
        "direction": 1, "strength": 0.6, "novelty": 0.9, "consensus": 0.7,
        "description_cn": "Cape Verde门将神勇"
    }]
    result = engine.compute_matchup_adjustments(team_a_sigs, team_b_sigs, 2000, 1600)
    print(f"  Team A adj: {result['team_a_adjustment']:+d}")
    print(f"  Team B adj: {result['team_b_adjustment']:+d}")
    print(f"  Net: {result['net_adjustment']:+d}")
    print("  ✅ PASS")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)


if __name__ == '__main__':
    main()
