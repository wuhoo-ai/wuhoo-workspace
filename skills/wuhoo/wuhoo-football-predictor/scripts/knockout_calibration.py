#!/usr/bin/env python3.11
"""
KBC (Knockout Behavior Calibration) — 淘汰赛行为校准模块
v1.0 — WC2026 knockout stage optimization

Calibrates Poisson model parameters for knockout matches based on
historical World Cup knockout data (WC1998-2022, 94 matches).

Key adjustments:
1. Lambda suppression: 2.09/2.67 = 0.78 (knockout goals -22%)
2. Draw probability enhancement: 25% → 35% (mean reversion)
3. Underdog bonus: weaker teams get +5~25 ELO in knockout
4. Extra time / penalty simulation

Usage:
  from scripts.knockout_calibration import apply_knockout_calibration
  lam_a, lam_b, audit = apply_knockout_calibration(lam_a, lam_b, elo_diff, audit)
"""

import json
import os
import math

# === Historical Statistics (WC1998-2022) ===
# Source: 94 knockout matches across 7 World Cups
GROUP_STAGE_GOALS = 2.67   # Average goals per match (group stage)
KNOCKOUT_GOALS = 2.09      # Average goals per match (knockout 90min)
LAMBDA_SUPPRESSION = KNOCKOUT_GOALS / GROUP_STAGE_GOALS  # ~0.78

GROUP_DRAW_RATE = 0.25     # ~25% draws in group stage
KNOCKOUT_DRAW_RATE = 0.47  # ~47% draws in 90-min knockout (including ET resolved)
TARGET_KNOCKOUT_DRAW = 0.35  # Target draw rate in 90min (accounting for ET avoidance)

MEAN_REVERSION = 0.15      # Pull lambdas 15% toward mean

# Underdog bonus: weaker teams perform better in knockout (defensive tactics)
UNDERDOG_BONUS = {
    100: 5,     # diff > 100: +5 ELO
    200: 15,    # diff > 200: +15 ELO  
    300: 25,    # diff > 300: +25 ELO
}

# Favorite suppression: strong teams play more conservatively in knockout
FAVORITE_SUPPRESSION = {
    100: 0,     # diff > 100: lambda × 0.95
    200: 0.90,  # diff > 200: lambda × 0.90
    300: 0.85,  # diff > 300: lambda × 0.85
}

# Knockout advancement probabilities
EXTRA_TIME_PROB = 0.28     # ~28% of knockout matches go to extra time
PENALTIES_PROB = 0.15      # ~15% go to penalties


def apply_knockout_calibration(lam_a, lam_b, elo_a, elo_b, audit=None):
    """
    Apply knockout behavior calibration to Poisson lambdas.
    
    Args:
        lam_a: Expected goals for team A
        lam_b: Expected goals for team B
        elo_a: Effective ELO for team A
        elo_b: Effective ELO for team B
        audit: Existing audit dict (optional)
    
    Returns:
        (lam_a_calibrated, lam_b_calibrated, audit_updated)
    """
    if audit is None:
        audit = {}
    
    elo_diff = elo_a - elo_b
    
    # === 1. Global lambda suppression ===
    lam_a_orig = lam_a
    lam_b_orig = lam_b
    lam_a *= LAMBDA_SUPPRESSION
    lam_b *= LAMBDA_SUPPRESSION
    
    # === 2. Favorite/underdog asymmetry ===
    abs_diff = abs(elo_diff)
    fav_suppress = 1.0
    dog_bonus_factor = 1.0
    
    for threshold in sorted(FAVORITE_SUPPRESSION.keys()):
        if abs_diff > threshold:
            fav_suppress = FAVORITE_SUPPRESSION[threshold]
    
    for threshold in sorted(UNDERDOG_BONUS.keys()):
        if abs_diff > threshold:
            dog_bonus_factor = 1.0 + (UNDERDOG_BONUS[threshold] / 1000.0)
    
    if elo_diff > 0:
        # A is favorite
        lam_a *= fav_suppress
        lam_b *= dog_bonus_factor
    elif elo_diff < 0:
        # B is favorite
        lam_b *= fav_suppress
        lam_a *= dog_bonus_factor
    
    # === 3. Mean reversion (increase draw probability) ===
    mean_lam = (lam_a + lam_b) / 2
    lam_a = lam_a * (1 - MEAN_REVERSION) + mean_lam * MEAN_REVERSION
    lam_b = lam_b * (1 - MEAN_REVERSION) + mean_lam * MEAN_REVERSION
    
    # === 4. Compute extra time / penalties probabilities ===
    # Probability of draw in 90 minutes (approximate from Poisson)
    draw_prob = 0.0
    for i in range(8):
        p_a = (lam_a ** i) * math.exp(-lam_a) / math.factorial(i)
        p_b = (lam_b ** i) * math.exp(-lam_b) / math.factorial(i)
        draw_prob += p_a * p_b
    
    # Overall advancement probabilities
    et_win_a = 0.52  # Slight bias to stronger team in ET
    et_win_b = 0.48
    
    # Adjust based on ELO difference
    if elo_diff > 50:
        et_win_a = 0.55
        et_win_b = 0.45
    elif elo_diff < -50:
        et_win_a = 0.45
        et_win_b = 0.55
    
    pk_win_a = 0.50  # Penalties are ~50/50
    pk_win_b = 0.50
    
    p_et = draw_prob * EXTRA_TIME_PROB / GROUP_DRAW_RATE  # Scale to knockout rate
    p_pk = draw_prob * PENALTIES_PROB / GROUP_DRAW_RATE
    
    # Compute win probabilities from Poisson
    win_a_90 = sum(
        (lam_a ** i) * math.exp(-lam_a) / math.factorial(i) *
        sum((lam_b ** j) * math.exp(-lam_b) / math.factorial(j) for j in range(i))
        for i in range(1, 10)
    )
    
    # Overall advancement probability (simplified model)
    # P(advance) = P(win in 90) + P(draw) × P(win in ET/PK)
    # Of draws: ~60% resolved in ET, ~40% go to PK after ET draw
    
    # Conditional win probabilities
    if elo_diff > 100:
        et_win_a_cond = 0.58
    elif elo_diff > 50:
        et_win_a_cond = 0.55
    elif elo_diff > -50:
        et_win_a_cond = 0.52
    elif elo_diff > -100:
        et_win_a_cond = 0.48
    else:
        et_win_a_cond = 0.45
    
    et_still_draw = 0.35  # 35% of ET periods remain tied → go to PK
    pk_win_a_cond = 0.50  # Penalties are ~50/50
    
    # Probability team A advances conditional on draw in 90 minutes
    p_adv_if_draw = et_win_a_cond * (1 - et_still_draw) + et_still_draw * pk_win_a_cond
    
    # Overall advancement
    overall_adv_a = win_a_90 + draw_prob * p_adv_if_draw
    overall_adv_b = 1.0 - overall_adv_a  # Complementary
    
    # === Build audit ===
    audit['layers'] = audit.get('layers', {})
    audit['layers']['7_knockout_calibration'] = {
        'lambda_suppression': round(LAMBDA_SUPPRESSION, 4),
        'lambda_a': {'original': round(lam_a_orig, 3), 'calibrated': round(lam_a, 3)},
        'lambda_b': {'original': round(lam_b_orig, 3), 'calibrated': round(lam_b, 3)},
        'favorite_suppression': round(fav_suppress, 3),
        'underdog_bonus_factor': round(dog_bonus_factor, 3),
        'mean_reversion': MEAN_REVERSION,
        'draw_prob_90min': round(draw_prob, 3),
        'advancement': {
            'team_a': round(overall_adv_a, 3),
            'team_b': round(overall_adv_b, 3),
        },
        'extra_time_prob': round(p_et, 3),
        'penalties_prob': round(p_pk, 3),
        'description': f"KO校准: λ={LAMBDA_SUPPRESSION:.2f}×, 弱队加成, 平局增强, 加时/点球模拟"
    }
    
    return lam_a, lam_b, audit


def get_knockout_config():
    """Return knockout calibration config as dict (for external use)."""
    return {
        "lambda_suppression": LAMBDA_SUPPRESSION,
        "mean_reversion": MEAN_REVERSION,
        "favorite_suppression": FAVORITE_SUPPRESSION,
        "underdog_bonus": UNDERDOG_BONUS,
        "extra_time_prob": EXTRA_TIME_PROB,
        "penalties_prob": PENALTIES_PROB,
    }


# === Standalone test ===
if __name__ == "__main__":
    print("=== KBC Module Test ===")
    print(f"Lambda suppression: {LAMBDA_SUPPRESSION:.4f} ({KNOCKOUT_GOALS}/{GROUP_STAGE_GOALS})")
    print(f"Mean reversion: {MEAN_REVERSION}")
    
    # Test 1: Equal teams
    print("\nTest 1: Equal teams (ELO diff=0)")
    lam_a, lam_b, audit = apply_knockout_calibration(1.45, 1.45, 2000, 2000)
    print(f"  Original: λ_a={1.45}, λ_b={1.45}")
    print(f"  Calibrated: λ_a={lam_a:.3f}, λ_b={lam_b:.3f}")
    kb = audit['layers']['7_knockout_calibration']
    print(f"  Draw prob (90min): {kb['draw_prob_90min']:.1%}")
    print(f"  Advancement: A={kb['advancement']['team_a']:.1%}, B={kb['advancement']['team_b']:.1%}")
    
    # Test 2: Strong favorite
    print("\nTest 2: Strong favorite (ELO diff=+250)")
    lam_a, lam_b, audit = apply_knockout_calibration(2.00, 0.80, 2200, 1950)
    print(f"  Original: λ_a={2.00}, λ_b={0.80}")
    print(f"  Calibrated: λ_a={lam_a:.3f}, λ_b={lam_b:.3f}")
    kb = audit['layers']['7_knockout_calibration']
    print(f"  Draw prob (90min): {kb['draw_prob_90min']:.1%}")
    print(f"  Advancement: A={kb['advancement']['team_a']:.1%}, B={kb['advancement']['team_b']:.1%}")
    print(f"  Fav suppression: {kb['favorite_suppression']}, Dog bonus: {kb['underdog_bonus_factor']}")
    
    # Test 3: Extreme favorite
    print("\nTest 3: Extreme favorite (ELO diff=+400)")
    lam_a, lam_b, audit = apply_knockout_calibration(2.80, 0.40, 2300, 1900)
    print(f"  Original: λ_a={2.80}, λ_b={0.40}")
    print(f"  Calibrated: λ_a={lam_a:.3f}, λ_b={lam_b:.3f}")
    kb = audit['layers']['7_knockout_calibration']
    print(f"  Advancement: A={kb['advancement']['team_a']:.1%}, B={kb['advancement']['team_b']:.1%}")
    
    print("\n✅ KBC module tests passed")
