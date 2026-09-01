# Inference Engine Architecture

## Overview

The v5.5 rule inference engine replaces naive additive ELO stacking with a 3-layer reasoning architecture:

```
Context (积分/伤病/动机/天气) → Evidence (带confidence) → Rules Engine → effective_elo_delta
```

## Key Components

### 1. InferenceEngine (`scripts/inference_engine.py`)

Core loop:
1. Load rules from `configs/rules_v1.json` (sorted by priority)
2. For each rule: evaluate `activation.condition` against team context
3. If condition met: execute `action` (ELO adjust with confidence scaling)
4. After all rules: apply interaction constraints (dampen/amplify/penalize)
5. Apply sigmoid saturation if positive sum > midpoint × 0.75
6. Output delta + full trace

### 2. DataProvider (`scripts/data_provider.py`)

Unified data access with freshness tracking:
- ELO, injuries, team profiles: from JSON files
- Motivation: from `matchday3_motivation.json` (computed by `compute_motivation.py`)
- Third-place: from `third_place_standings.json` (computed by `compute_third_place.py`)
- Bracket paths: from `bracket_paths.json` (computed by `compute_bracket_path.py`)

### 3. predict_v55.py (wrapper)

Zero-intrusion wrapper over `wc2026_predict.py`:
1. Build team contexts via DataProvider
2. Run InferenceEngine → get ELO deltas
3. Pass deltas as `manual_adjustments` to `predict_single_match`
4. Inject `inference_trace` and `reasoning_path` into audit output

## Rule Format

```json
{
  "id": "MOT_002",
  "name": "出线动机 — MUST_WIN",
  "priority": 15,
  "activation": {
    "condition": "team.classification == 'MUST_WIN'",
    "confidence": "{{motivation_confidence}}",
    "evidence": "QMF自动分类"
  },
  "action": {
    "type": "elo_adjust",
    "base_value": "{{motivation_elo}}"
  }
}
```

Template values `{{key}}` are resolved from team context at runtime.

## Interaction Constraints

4 predefined interactions in `rules_v1.json`:
- INT_001: MUST_WIN × THIRD_PLACE_VIABLE → ×0.6 dampen
- INT_002: LOCKED_IN × OPPONENT_MUST_WIN → -15 penalty
- INT_003: MUST_WIN × HOME_ADVANTAGE → ×1.15 amplify
- INT_004: INJURY_HEAVY × MUST_WIN → ×0.75 dampen

## Confidence Scaling

| Level | Factor |
|-------|--------|
| high | 1.0 |
| medium | 0.7 |
| low | 0.4 |

Applied automatically to each rule's base_value before interaction processing.

## Sigmoid Saturation

```
sigmoid(x) = 50 / (1 + exp(-0.08 × (x - 40))) - offset
```

Prevents unbounded accumulation of positive ELO adjustments.
Default midpoint=40, steepness=0.08, max_output=50.
