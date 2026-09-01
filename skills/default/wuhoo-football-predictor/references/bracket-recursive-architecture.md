# bracket_recursive.py Architecture & Pitfalls

> Created 2026-07-04 during WC2026 R16 system overhaul

## Three-Phase Pipeline

1. **Phase 1**: Deterministic 12-layer predictions for R16 matches (teams known)
2. **Phase 1b**: Most likely bracket path — resolve QF/SF/F teams deterministically using highest-probability winners, predict each match with full v5.5 stack via `predict_with_engine()`
3. **Phase 2**: Monte Carlo simulation (N sims) — sample winners from Phase 1 probabilities, propagate through bracket, track advancement/champion/top paths

## Critical Pitfalls

### 1. Do NOT Let Monte Carlo Overwrite Match Details

The match_details shown in reports MUST come from Phase 1b (deterministic most-likely path), NOT from random Monte Carlo sampling. With only 10 sims, sampling noise produces absurd results (e.g., Mexico beating Argentina in one sim causing "France vs Mexico" Final when the most likely is "France vs Argentina").

**Fix**: Phase 1b populates match_details for ALL rounds deterministically. Phase 2 reads match_details for sampling probabilities only, never writes back.

### 2. advancement Tracking Was Lost

During refactoring, `advancement[winner][stage] += 1` line was accidentally removed from the Phase 2 inner loop. This line must be placed right after `winners[mid] = winner` INSIDE the match loop.

### 3. Losers Tracking for 3rd Place

The 3rd place match source is "L101 vs L102" (losers of semi-finals). Track both `winners` and `losers` dicts per sim. Initialize `losers = {}` alongside `winners = {}`. Use `losers.get(mid)` for the 3rd place match, NOT `winners.get(mid)`.

### 4. Data Structure Compatibility with v5.5

`predict_with_engine()` returns a flat structure (NOT wrapped in `audit`):
- `prediction.scoreline_probs` — already formatted [{score, prob_pct}, ...]
- `effective_elo.team_a.effective` — nested dict with base, effective, adjustments
- `reasoning_path` — at top level

Do NOT use `pred.get("audit", {}).get("effective_elo", {})` — this returns empty dict.

### 5. get_match_order Must Include All Rounds

Future rounds (QF/SF/F/3rd) have `team_a: null, team_b: null` in knockout_schedule.json. `get_match_order()` must include these pending matches so Phase 1b and Phase 2 can resolve teams from winners/losers.

### 6. winners.get Typo

Original code had `winners.get(w1_id, winners.get(w1_id))` (double fallback). Fixed to `winners.get(w1_id)`.
