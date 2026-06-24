# Inference Engine Patterns — v5.5

> Techniques learned during the v5.5 rule engine build. Reference for future extension.

## Wrapper Pattern (Zero-Invasion Integration)

**Problem**: Adding conditional code paths to `predict_single_match` would require re-indenting 300+ lines of existing layer stacking code.

**Solution**: `predict_v55.py` wraps the existing function. Engine computes ELO deltas, injects them as `manual_adjustments`, and the existing pipeline runs unchanged.

```python
# DO: wrap, don't modify
engine_deltas = engine.reason(ctx_a, ctx_b)
result = predict_single_match(..., manual_adjustments=engine_deltas)
result['inference_trace'] = ...  # inject trace after

# DON'T: modify predict_single_match internals
```

## Regex Condition Evaluation (Safe eval Alternative)

**Problem**: Using Python `eval()` on rule conditions is fragile and insecure.

**Solution**: `evaluate_condition()` uses `re.match` patterns:

```python
# Supported patterns:
m = re.match(r"team\.(\w+)\s*==\s*'([^']*)'", condition)  # string equality
m = re.match(r"team\.(\w+)\s*==\s*(True|False)", condition)  # boolean
m = re.match(r"team\.(\w+)\s*>\s*([\d.]+)", condition)       # numeric gt
m = re.match(r"team\.(\w+)\s*!=\s*'([^']*)'", condition)     # not-equal
# AND/OR handled by recursive split
```

**Extending**: Add new `re.match` patterns for new comparison types.

## Template Resolution (`{{key}}`)

**Problem**: Rule `base_value` depends on dynamic context (e.g., `motivation_elo` varies per team).

**Solution**: Template strings `"{{key}}"` resolve to `context[key]` at rule evaluation time:

```json
{
  "action": {
    "base_value": "{{motivation_elo}}"
  }
}
```

Silent fallback to 0 if key missing.

## Sigmoid Saturation

Prevents unbounded positive ELO accumulation:

```python
def sigmoid_saturation(x, midpoint=40, steepness=0.08, max_output=50):
    offset = max_output / (1 + exp(-steepness * (0 - midpoint)))
    return max_output / (1 + exp(-steepness * (x - midpoint))) - offset
```

- x=20 → ~3 (linear region, no saturation)
- x=40 → ~20 (inflection — growth slows)
- x=80 → ~46 (near asymptote)
- x=∞ → ~50 (hard cap)

## Deterministic Tournament Form

**Problem**: `random.gauss(0, 60)` returns different values each call — non-reproducible.

**Solution**: Hash team name for deterministic seed:
```python
seed = sum(ord(c) * (i + 1) for i, c in enumerate(team))
rng = random.Random(seed + 2026)
return int(rng.gauss(0, 30))  # Reduced from 60
```

## Confidence × Freshness Decay

Two-stage scaling applied to every rule:
1. Confidence: `high=1.0, medium=0.7, low=0.4`
2. Freshness: `<6h=1.0, 6-12h=0.9, 12-24h=0.7, 24-72h=0.5, >72h=0.3`

`adjusted_value = base_value × conf_factor` then interactions may further modify.
