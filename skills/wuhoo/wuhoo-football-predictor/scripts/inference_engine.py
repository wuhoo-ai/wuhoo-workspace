#!/usr/bin/env python3.11
"""
Inference Engine — Rule-based reasoning for football prediction
v1.0 — WC2026 v5.5

Replaces naive additive ELO stacking with rule-driven inference.
Supports: confidence scaling, interaction constraints, sigmoid saturation.

Architecture:
  Context → Evidence → Rules Engine → effective_elo_delta + trace
"""

import json, os, math, sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

# === Sigmoid Saturation ===
def sigmoid_saturation(x: float, midpoint: float = 40, steepness: float = 0.08, 
                       max_output: float = 50) -> float:
    """
    Sigmoid saturation function.
    - x=0   → ~0
    - x=20  → ~3 (linear region)
    - x=40  → ~20 (inflection point)
    - x=60  → ~38 (approaching saturation)
    - x=100 → ~48 (asymptotic to max_output)
    """
    if x <= 0:
        return 0.0
    offset = max_output / (1 + math.exp(-steepness * (0 - midpoint)))
    return max_output / (1 + math.exp(-steepness * (x - midpoint))) - offset


# === Confidence Scaling ===
CONFIDENCE_FACTOR = {
    "high": 1.0,
    "medium": 0.7,
    "low": 0.4,
}


def freshness_factor(age_hours: float) -> float:
    """Compute confidence decay based on data age."""
    if age_hours < 6:
        return 1.0
    elif age_hours < 12:
        return 0.9
    elif age_hours < 24:
        return 0.7
    elif age_hours < 72:
        return 0.5
    else:
        return 0.3


# === Condition Evaluator ===
def evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
    """
    Evaluate a rule condition against context dict.
    
    Supports simple patterns:
      - "team.X == 'VALUE'" → context['X'] == 'VALUE'
      - "team.X == True" → context['X'] == True  
      - "team.X > N" → context['X'] > N
      - "A AND B" → evaluate(A) and evaluate(B)
    """
    if not condition or condition.strip() == "":
        return True
    
    condition = condition.strip()
    
    try:
        # Handle AND
        if ' AND ' in condition:
            parts = condition.split(' AND ')
            return all(evaluate_condition(p.strip(), context) for p in parts)
        
        # Handle OR
        if ' OR ' in condition:
            parts = condition.split(' OR ')
            return any(evaluate_condition(p.strip(), context) for p in parts)
        
        # Handle team.X == 'VALUE' or team.X == True
        import re
        
        # Pattern: team.X == 'VALUE'
        m = re.match(r"team\.(\w+)\s*==\s*'([^']*)'", condition)
        if m:
            key, val = m.group(1), m.group(2)
            return str(context.get(key, '')) == val
        
        # Pattern: team.X == True / False
        m = re.match(r"team\.(\w+)\s*==\s*(True|False)", condition)
        if m:
            key, val = m.group(1), m.group(2)
            return bool(context.get(key, False)) == (val == 'True')
        
        # Pattern: team.X != 'VALUE'
        m = re.match(r"team\.(\w+)\s*!=\s*'([^']*)'", condition)
        if m:
            key, val = m.group(1), m.group(2)
            return str(context.get(key, '')) != val
        
        # Pattern: team.X > N
        m = re.match(r"team\.(\w+)\s*>\s*([\d.]+)", condition)
        if m:
            key, val = m.group(1), float(m.group(2))
            return float(context.get(key, 0)) > val
        
        # Pattern: team.X < N
        m = re.match(r"team\.(\w+)\s*<\s*([\d.]+)", condition)
        if m:
            key, val = m.group(1), float(m.group(2))
            return float(context.get(key, 0)) < val
        
        # Fallback: direct key lookup
        if condition in context:
            return bool(context[condition])
        
        # Try simple eval as last resort
        safe_dict = {"context": context, "True": True, "False": False}
        return bool(eval(condition, {"__builtins__": {}}, safe_dict))
        
    except Exception:
        return False


# === Rule Engine ===
class InferenceEngine:
    """
    Rule-driven inference engine for football match prediction.
    
    Usage:
        engine = InferenceEngine("configs/rules_v1.json")
        result = engine.reason(team_context, opponent_context)
        # result.delta: ELO adjustment
        # result.trace: full reasoning trace
    """
    
    def __init__(self, rules_path: str = None):
        self.rules = []
        self.interactions = []
        self.confidence_factors = CONFIDENCE_FACTOR
        self.saturation_params = {"midpoint": 40, "steepness": 0.08, "max_output": 50}
        
        if rules_path and os.path.exists(rules_path):
            self.load_rules(rules_path)
    
    def load_rules(self, path: str):
        """Load rules and interactions from JSON config."""
        with open(path) as f:
            config = json.load(f)
        
        self.rules = config.get("rules", [])
        self.interactions = config.get("interactions", [])
        
        if "confidence_factors" in config:
            self.confidence_factors = config["confidence_factors"]
        if "saturation" in config:
            self.saturation_params = config["saturation"]
        
        # Sort rules by priority
        self.rules.sort(key=lambda r: r.get("priority", 50))
    
    def reason(self, team_ctx: Dict[str, Any], opponent_ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run inference for one team.
        
        Args:
            team_ctx: Context dict for the team
            opponent_ctx: Context dict for the opponent
        
        Returns:
            {
                "delta": float,          # Final ELO adjustment
                "trace": List[dict],     # Full reasoning trace
                "saturated": bool,       # Whether saturation was applied
                "raw_sum": float,        # Sum before saturation
            }
        """
        trace = []
        adjustments = []
        
        # Merge contexts for condition evaluation
        eval_ctx = dict(team_ctx)
        for k, v in opponent_ctx.items():
            eval_ctx[f"opp_{k}"] = v
        
        # Phase 1: Evaluate all rules
        for rule in self.rules:
            activation = rule.get("activation", {})
            condition = activation.get("condition", "")
            
            if not evaluate_condition(condition, eval_ctx):
                continue
            
            # Rule fires — execute action
            action = rule.get("action", {})
            action_type = action.get("type", "elo_adjust")
            
            base_value = action.get("base_value", 0)
            
            # Resolve template values from context
            if isinstance(base_value, str) and base_value.startswith("{{") and base_value.endswith("}}"):
                key = base_value[2:-2].strip()
                base_value = eval_ctx.get(key, 0)
            
            confidence = activation.get("confidence", "high")
            # Resolve confidence template
            if isinstance(confidence, str) and confidence.startswith("{{") and confidence.endswith("}}"):
                key = confidence[2:-2].strip()
                confidence = eval_ctx.get(key, "medium")
            conf_factor = self.confidence_factors.get(confidence, 1.0)
            
            adjusted_value = base_value * conf_factor
            
            trace_entry = {
                "rule_id": rule.get("id", "?"),
                "rule_name": rule.get("name", "?"),
                "priority": rule.get("priority", 50),
                "condition": condition,
                "evaluated": True,
                "action_type": action_type,
                "base_value": base_value,
                "confidence": confidence,
                "confidence_factor": conf_factor,
                "preliminary_value": round(adjusted_value, 1),
                "interactions_applied": [],
                "final_value": round(adjusted_value, 1),
                "evidence": activation.get("evidence", rule.get("description", "")),
            }
            trace.append(trace_entry)
        
        # Phase 2: Apply interaction constraints
        self._apply_interactions(trace, eval_ctx)
        
        # Phase 3: Compute raw sum
        positive_sum = sum(t["final_value"] for t in trace if t["final_value"] > 0)
        negative_sum = sum(t["final_value"] for t in trace if t["final_value"] < 0)
        raw_sum = positive_sum + negative_sum
        
        # Phase 4: Apply saturation
        saturated = False
        if positive_sum > self.saturation_params.get("midpoint", 40) * 0.75:
            saturated_positive = sigmoid_saturation(
                positive_sum,
                self.saturation_params.get("midpoint", 40),
                self.saturation_params.get("steepness", 0.08),
                self.saturation_params.get("max_output", 50)
            )
            # Scale positive adjustments proportionally
            if positive_sum > 0:
                scale = saturated_positive / positive_sum
                for t in trace:
                    if t["final_value"] > 0:
                        t["final_value"] = round(t["final_value"] * scale, 1)
                        if "interactions_applied" not in t:
                            t["interactions_applied"] = []
                        t["interactions_applied"].append({
                            "type": "saturation",
                            "scale": round(scale, 3),
                            "reason": f"正面累计饱和: {positive_sum:.1f}→{saturated_positive:.1f}"
                        })
            saturated = True
        
        # Recompute final delta
        delta = sum(t["final_value"] for t in trace)
        
        return {
            "delta": round(delta),
            "trace": trace,
            "saturated": saturated,
            "raw_sum": round(raw_sum, 1),
            "positive_before_saturation": round(positive_sum, 1),
        }
    
    def _apply_interactions(self, trace: List[dict], context: Dict[str, Any]):
        """
        Apply interaction constraints to trace entries.
        
        Interactions can:
        - Dampen (multiply by coefficient < 1)
        - Amplify (multiply by coefficient > 1)
        - Penalize (subtract value)
        """
        for interaction in self.interactions:
            when_conditions = interaction.get("when", [])
            target_rule = interaction.get("target", "")
            
            # Check if all conditions are met
            conditions_met = True
            for cond in when_conditions:
                # Check if any trace entry has this condition type in its rule
                found = False
                for t in trace:
                    if cond in t.get("rule_name", "") or cond in t.get("rule_id", ""):
                        found = True
                        break
                # Also check context
                if not found and cond in context:
                    found = True
                if not found:
                    conditions_met = False
                    break
            
            if not conditions_met:
                continue
            
            # Find target rule in trace and apply effect
            effect = interaction.get("effect", "multiply")
            coefficient = interaction.get("coefficient", 1.0)
            
            for t in trace:
                if target_rule in t.get("rule_id", "") or target_rule in t.get("rule_name", ""):
                    if effect == "multiply":
                        t["final_value"] = round(t["final_value"] * coefficient, 1)
                    elif effect == "subtract":
                        t["final_value"] = round(t["final_value"] - coefficient, 1)
                    
                    t.setdefault("interactions_applied", []).append({
                        "interaction_id": interaction.get("id", "?"),
                        "effect": effect,
                        "coefficient": coefficient,
                        "reason": interaction.get("reason", ""),
                    })
    
    def format_trace(self, team_name: str, result: Dict[str, Any]) -> str:
        """Format inference trace as human-readable text for reports."""
        lines = []
        lines.append(f"\n{team_name} ({result['delta']:+d} ELO):")
        
        for t in result["trace"]:
            conf_str = f"conf={t['confidence']}×{t['confidence_factor']}"
            lines.append(f"  📋 {t['rule_name']}({t['base_value']:+d}, {conf_str}) → {t['preliminary_value']:+.1f}")
            
            if t.get("interactions_applied"):
                for ia in t["interactions_applied"]:
                    if ia.get("type") == "saturation":
                        lines.append(f"     ⚡ 饱和: ×{ia['scale']} → {t['final_value']:+.1f}")
                    else:
                        lines.append(f"     ├ 交互: {ia.get('reason','?')} → {t['final_value']:+.1f}")
            
            if t.get("evidence"):
                lines.append(f"     └ 证据: {t['evidence'][:80]}")
        
        if result["saturated"]:
            lines.append(f"  ⚡ 饱和: 正面累计={result['positive_before_saturation']:.0f} → sigmoid → {result['delta']:+d}")
        
        lines.append(f"  {'─'*40}")
        lines.append(f"  净调整: {result['delta']:+d} ELO")
        
        return "\n".join(lines)


# === Standalone test ===
if __name__ == "__main__":
    print("=== Inference Engine Test ===\n")
    
    # Test condition evaluator
    ctx = {"classification": "MUST_WIN", "third_place_prob": 0.35, "points": 3}
    print("Condition tests:")
    cond1 = "team.classification == 'MUST_WIN'"
    cond3 = "team.classification == 'MUST_WIN' AND team.third_place_prob > 0.7"
    print("  MUST_WIN: {}".format(evaluate_condition(cond1, ctx)))
    print("  third_place > 0.7: {}".format(evaluate_condition('team.third_place_prob > 0.7', ctx)))
    print("  AND: {}".format(evaluate_condition(cond3, ctx)))
    
    # Test sigmoid
    print("\nSigmoid saturation tests:")
    for x in [0, 10, 20, 30, 40, 50, 60, 80, 100]:
        print(f"  sigmoid({x}) = {sigmoid_saturation(x):.1f}")
    
    print("\n✅ Engine tests passed")
