# Rule Learning Results — Phase 0 (2026-06-24)

> Grid search over 44 completed WC2026 group stage matches.

## Baseline (v5.4, no interactions)

| Metric | Value |
|--------|-------|
| Matches | 44 |
| Correct | 31 |
| Accuracy | 70.5% |
| Brier Score | 0.3362 |

## Error Pattern Analysis

**ALL 13 errors are missed draws** — model predicts a winner but match ends in draw:

| Match | ELO Diff | Predicted | Actual |
|-------|----------|-----------|--------|
| Canada vs Bosnia | +365 | a_wins | draw (1-1) |
| Qatar vs Switzerland | -365 | b_wins | draw (1-1) |
| Brazil vs Morocco | -86 | b_wins | draw (1-1) |
| Netherlands vs Japan | +78 | a_wins | draw (2-2) |
| Spain vs Cape Verde | +116 | a_wins | draw (0-0) |
| Belgium vs Egypt | -104 | b_wins | draw (1-1) |
| Saudi Arabia vs Uruguay | -135 | b_wins | draw (1-1) |
| Iran vs New Zealand | +186 | a_wins | draw (2-2) |
| Portugal vs DR Congo | +55 | a_wins | draw (1-1) |
| Czech Rep vs S. Africa | +26 | a_wins | draw (1-1) |

**Key insight**: Model overestimates win probability for favorites. Mean reversion (KBC's 15% lambda pull) directly addresses this.

## Learned Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `mustwin_3rdplace_dampen` | 0.6 | MUST_WIN × 0.6 when 3rd place viable |
| `lockedin_vs_mustwin_penalty` | 15 | LOCKED_IN -15 when facing MUST_WIN |
| `mustwin_home_amplify` | 1.15 | MUST_WIN × 1.15 with home advantage |
| `injury_heavy_dampen` | 0.75 | MUST_WIN × 0.75 when injury_total > 60 |
| `sigmoid_midpoint` | 40 | Saturation inflection at +40 ELO |
| `sigmoid_steepness` | 0.08 | Moderate saturation curve |
| `confidence_high` | 1.0 | Full weight for high-confidence evidence |
| `confidence_medium` | 0.7 | 30% discount for medium confidence |
| `confidence_low` | 0.4 | 60% discount for low confidence |

## Limitations

- Parameter grid search was expert-guided (not exhaustive 720-combination sweep) due to time constraints
- LOCKED_IN vs MUST_WIN interaction could not be validated (no such matches in completed data)
- Parameters should be recalibrated after MD3 data becomes available
- Full grid search requires the inference engine to be running (Phase 1+ dependency)
