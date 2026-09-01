# World Cup 2026 — Pre-Tournament Data Refresh Checklist

## When to Run

- After major squad announcements (teams confirmed)
- After significant injury news (new OUT/DOUBTFUL players)
- After ELO ratings update from international-football.net
- Weekly during the month before tournament (May 11–June 11)

## Step-by-Step Workflow

### Step 1: Scan Current State

```bash
# Check ELO freshness
python3.11 scripts/fetch_elo.py --source

# Check data coverage
python3.11 -c "
import json
from wc2026_predict import ALL_TEAMS, ELO, INJURIES, META_ADJUSTMENTS

# ELO coverage
missing_elo = [t for t in ALL_TEAMS if t not in ELO]
print(f'ELO: {len(ALL_TEAMS) - len(missing_elo)}/48 teams covered' +
      (f' — MISSING: {missing_elo}' if missing_elo else ' ✅'))

# Injuries
with open('data/injuries.json') as f:
    inj = json.load(f)
inj_teams = len(inj.get('injuries', {}))
print(f'Injuries: {inj_teams} teams affected')

# Metadata
with open('data/team_metadata.json') as f:
    meta = json.load(f)
meta_teams = len(meta.get('teams', {}))
print(f'Metadata: {meta_teams}/48 teams')
"
```

### Step 2: Collect Latest Injury News

1. web_search: "2026 World Cup injury players OUT squad <today's date>"
2. web_extract ESPN Injuries Tracker: https://www.espn.com/soccer/story/_/id/48572979
3. web_extract The Athletic Squad Tracker: https://www.nytimes.com/athletic/7279459
4. Cross-reference BBC squad announcements: https://www.bbc.com/sport/football/articles/cvgz43lgn15o

### Step 3: Update injuries.json

For each new/updated injury:
- Determine severity: core/important/role
- Determine status: OUT/DOUBTFUL/MINOR
- Map to ELO penalty per the penalty scale
- Recalculate `total_penalty` for affected teams
- Remove players confirmed FIT and in squad (e.g. Salah May 26)

### Step 4: Update team_metadata.json

When rosters are confirmed/updated:
- Adjust `roster_stability` if key players IN or OUT
- Adjust `recent_form_consistency` if team form changed
- Add new teams not yet covered (target: eventually all 48)

### Step 5: Check ELO Freshness

```bash
# Check eloratings.net for latest
python3.11 scripts/fetch_elo.py --diff
```

ELO data is considered fresh if within 7 days. Static fallback is used when HTTP fetch fails (429 rate limit).

### Step 6: Verify Data Integrity

```bash
python3.11 -c "
from wc2026_predict import ALL_TEAMS, ELO, INJURIES, META_ADJUSTMENTS

print('=== Integrity Checks ===')

# 1. All WC teams have ELO
missing = [t for t in ALL_TEAMS if t not in ELO]
assert not missing, f'MISSING ELO: {missing}'
print('✅ All 48 teams have ELO')

# 2. Injury targets exist in ALL_TEAMS
for team in INJURIES:
    assert team in ALL_TEAMS, f'UNKNOWN injury team: {team}'
print(f'✅ All {len(INJURIES)} injury teams in ALL_TEAMS')

# 3. Show adjusted ELO rankings
all_teams_sorted = sorted(ALL_TEAMS, key=lambda t:
    ELO.get(t, 1700) + META_ADJUSTMENTS.get(t, 0) + INJURIES.get(t, 0), reverse=True)
print('\\nTop 10 Adjusted ELO:')
for i, t in enumerate(all_teams_sorted[:10], 1):
    adj = ELO.get(t,1700) + META_ADJUSTMENTS.get(t,0) + INJURIES.get(t,0)
    print(f'  {i}. {t}: {adj} (raw={ELO.get(t,1700)}, meta={META_ADJUSTMENTS.get(t,0):+d}, inj={INJURIES.get(t,0):+d})')
"
```

### Step 7: Run Full Simulation

```bash
python3.11 wc2026_predict.py --report --sims 5000
```

### Step 8: Verify Simulation Output

1. Check championship probability deltas vs previous run
2. Verify no team has 0% or 100% that shouldn't
3. Check group-stage advancement rates make sense
4. Look for unexpected anomalies (e.g. England 0.2% post-injury update → verify logic)

### Step 9: Run Tests

```bash
python3.11 -m pytest tests/ -v --tb=short
```

Known failing tests (May 26): 7 tests — see SKILL.md "Known Limitations" for details.

## Common Pitfalls

- **Name mismatch**: Use `wc2026_predict.py` GROUPS dict names, not Wikipedia names. "Czech Republic" not "Czechia", "Bosnia and Herzegovina" not "Bosnia-Herzegovina".
- **execute_code quirk**: `hermes_tools.read_file()` returns dict in execute_code, not string. Use `terminal()` for data scanning scripts.
- **team_profiles structure**: `_load_profiles()` returns `data['teams']` (inner dict). Direct JSON read gives root object with `_meta`, `teams` keys — so `len(data)` looks like 2, not 48.
- **Order of adjustments**: ELO + elo_adjustments + injury_adjustments + META_ADJUSTMENTS + tournament_form. Order doesn't affect result but matters for debugging.
