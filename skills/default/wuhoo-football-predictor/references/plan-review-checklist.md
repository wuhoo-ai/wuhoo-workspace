# Plan Review Checklist (v2.1 Enhancement Session)

Methodology used to review the 2026-05-02 plan for `wc2026_predict.py --report` enhancement. Reusable for future prediction system plans.

## Review Dimensions

### 1. Data Schema Integrity
- Does every new file have a defined schema?
- Are key-value lookups guaranteed to work? (e.g., team name matching between GROUPS, ELO, profiles)
- Run cross-reference: `set(GROUPS_teams) - set(ELO_teams)` and `set(GROUPS_teams) - set(profile_teams)`

### 2. Decision Logic Completeness
- Are ALL edge cases covered in judgment rules?
- For `analyze_group()`: tested 12 groups with computed ELO gaps — found 4 of 6 rules were missing
- Test rules against actual data before implementing

### 3. Output Format Specification
- Is the output format defined in detail? (Markdown structure, table columns, bracket tree format)
- "Bracket visualization" without format spec is a gap — need both table + tree representation
- Third-place teams (T1-T8) need resolution to actual team names

### 4. Statistical Soundness
- "Expected path" from single MC sim is biased — use probability-weighted most-frequent per-slot instead
- Probability-weighted paths may have self-consistency issues (same team in multiple slots)
- Document the trade-off explicitly

### 5. Data Validation Before Runtime
- Add `validate_data()` that runs before main logic
- Checks: team↔ELO, team↔profile, venue name resolution
- Fail fast with clear error messages

### 6. Unstructured Data Reproducibility
- `analyze_group()` narrative is rule-based (deterministic), not LLM-generated
- Good: reproducible. Limitation: no real-world context (injuries, form, etc.)
- Document the limitation in the report itself

## Gaps Found (2026-05-02 Session)

| # | Gap | Severity | Fix |
|---|-----|----------|-----|
| 1 | team_profiles.json no schema | Critical | Defined JSON schema with 7 fields |
| 2 | analyze_group() only 1 of 6 rules | High | Added 5 more rules with thresholds |
| 3 | Bracket format undefined | High | Table + venue icons (🏔️🔥) |
| 4 | Single-sim bias | Medium | Probability-weighted per-slot |
| 5 | No pre-run data validation | Medium | Added validate_data() |
| 6 | Unstructured judgment reproducibility | Low | Documented in report disclaimer |

## Runtime Bugs Discovered

### R32 Pair Tracking
- **Symptom**: Bracket shows "韩国 vs ..." with missing opponent
- **Root Cause**: `r32_slot_team[slot_id][team]` tracked individual teams, not pairs
- **Fix**: `r32_slot_pair[slot_id][(t1, t2)]` — track full pair tuple. Same for R16/QF/SF/Final
- **Bonus Bug**: `final_slot_winner[1][(t1, t2)]` mixed tuple keys with string keys in same dict → separated `final_pair_count`

### Expected Score vs Winner Mismatch
- **Symptom**: `expected_score(t1, winner)` computed t1 vs winner (same side!)
- **Root Cause**: Using winner as opponent when pair was unknown
- **Fix**: Once pairs tracked, use `expected_score(t1, t2, ...)` with actual pair
