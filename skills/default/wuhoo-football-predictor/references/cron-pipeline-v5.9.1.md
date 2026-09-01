# Cron Pipeline v5.9.1 — Key Updates & Traps

## 5000-sim bracket_recursive (replaces 10 sims)

**Why**: 10 sims produced 10-20% statistical noise in champion probabilities.
Example: same data → 10 sims = France 70% / Argentina 30% vs 5000 sims = France 49.7% / Argentina 27.1%.

**Cron step**: `python3.11 scripts/bracket_recursive.py --sims 5000`

## Completed match pre-seeding (v5.9.1 critical fix)

`bracket_recursive.py` now pre-seeds completed match winners into the Monte Carlo loop.
Without this, teams that already won (e.g., France after beating Paraguay in R16) are invisible
to subsequent rounds → QF source resolution (`"W89 vs W90"`) fails → champion_probs is empty.

## Collect results: backtrack 2 days

`collect_results.py --check` only scans `date_beijing == today`.
If yesterday's matches weren't collected (cron failure, rate limit, ESPN not updated),
they are silently skipped the next day.

**Fix**: cron step 2 now explicitly backtracks the previous 2 days.
Check: `wc2026_schedule.json` matches where `date < today AND status != "completed"`.

## Knockout schedule sync

After adding results to `wc2026_results.json`, MUST sync to `knockout_schedule.json`:
```python
# For each completed result, find corresponding match in knockout_schedule
# and set status="completed", score_a, score_b, winner
```

`bracket_recursive.py` reads `knockout_schedule.json` for match order and completed status.
If the schedule is stale, completed matches will be re-predicted with actual outcomes
(noise) and eliminated teams may incorrectly appear in champion probabilities.

## iLink rate limiting defense

WeChat iLink adapter has a rate limit. Cron uses `deliver=local,origin` —
output is saved locally even if WeChat push fails. Manual re-delivery is possible.

Sending pattern: 1 MEDIA per 30 seconds when sending multiple PDFs.
