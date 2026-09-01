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

## Pitfalls (v5.5 Implementation)

### 1. Git checkout wipes unsaved changes
**Symptom**: Used `git checkout wc2026_predict.py` to revert a corrupted patch. This reverted ALL v5.4 changes (QMF/BPP/KBC) that had been added earlier but not committed.
**Lesson**: Commit intermediate work BEFORE attempting complex file edits. `git stash` is safer than `git checkout` for temporary reverts.

### 2. Patch tool escaping corrupts files
**Symptom**: `patch` tool in mode='replace' with `\\n` sequences in old_string/new_string inserted literal backslash-n characters instead of newlines. File became syntactically broken.
**Lesson**: For multi-line insertions or complex edits, use `execute_code` with Python string manipulation instead of the `patch` tool. The `patch` tool is reliable for single-line replacements only.

### 3. Python 3.6 f-string backslash limitation
**Symptom**: `f"... {evaluate_condition(\"team.classification == 'MUST_WIN'\", ctx)}"` caused SyntaxError — f-strings in Python 3.6 cannot contain backslashes.
**Fix**: Extract complex expressions to variables, use `.format()` for strings with quotes:
```python
# WRONG (Python 3.6):
print(f"Result: {func(\"arg\")}")
# RIGHT:
val = func("arg")
print("Result: {}".format(val))
```

### 4. Sigmoid midpoint too low
**Symptom**: Saturation triggered at `positive_sum > 30` (midpoint 40 × 0.75), causing even modest adjustments (+13.6 ELO) to get compressed by ×0.512. This was because the saturation condition checked `positive_sum > midpoint * 0.75` but then applied the scale to ALL positive entries regardless.
**Fix**: Recalibrate midpoint to 50-60 and ensure saturation only fires when `positive_sum` genuinely exceeds the threshold by a meaningful margin (> midpoint × 1.0, not 0.75).

### 5. Tournament form randomness
**Symptom**: `random.gauss(0, 60)` produced wildly different values per call (-71 in one run, +18 in another for the same team). Non-reproducible predictions.
**Fix**: Hash team name for deterministic seed. Also reduced stddev from 60 to 30 to prevent extreme values dominating.

### 6. wrapper vs inline integration tradeoff
**Decision**: Used wrapper pattern (predict_v55.py) over inline modification of predict_single_match. 
**Tradeoff**: Wrapper is safer (zero risk of breaking existing pipeline) but creates two code paths. If engine becomes the primary path, consolidate into predict_single_match. For now, wrapper is correct for a new feature under validation.
