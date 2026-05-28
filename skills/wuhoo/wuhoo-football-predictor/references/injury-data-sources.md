# Injury Data Sources & Update Procedure

## Current State (2026-05-26)

10 teams, 15 players with confirmed or doubtful injuries affecting World Cup 2026 participation.

## Primary Sources (ranked by usefulness)

1. **ESPN Injuries Tracker** — "2026 World Cup injuries tracker: Which players are out?"
   - URL: https://www.espn.com/soccer/story/_/id/48572979/2026-fifa-world-cup-injuries-tracker-which-stars-miss-latest-info
   - Published: continuously updated
   - Coverage: Most comprehensive real-time tracker. Sections: "Will miss the World Cup", "Racing to be fit"

2. **The Athletic Squad Tracker** — "Every country's 2026 World Cup squad"
   - URL: https://www.nytimes.com/athletic/7279459/2026/05/15/world-cup-squad-tracker-roster-2026
   - Coverage: Lists every announced squad by group. Can cross-reference who WASN'T named.

3. **BBC Sport Squad Announcements** — "World Cup: Every squad as they are announced"
   - URL: https://www.bbc.com/sport/football/articles/cvgz43lgn15o
   - Coverage: Links to individual squad announcement articles per nation. Headlines reveal key omissions (e.g. "Foden, Palmer, Alexander-Arnold to miss World Cup").

4. **Yahoo/BBC Injury Watch** — "World Cup 2026 injury watch: Key names racing to be ready"
   - URL: https://sports.yahoo.com/articles/world-cup-2026-injury-watch-175035681.html
   - Published: April 23, 2026
   - Coverage: Detailed player-by-player status with recovery timelines

5. **Al Jazeera** — "Which injured players could miss the FIFA World Cup 2026?"
   - URL: https://www.aljazeera.com/sports/2026/4/26/will-yamal-salah-and-ekitike-miss-the-world-cup-2026-due-to-injury
   - Published: April 26, 2026
   - Coverage: Comprehensive early list — now outdated

6. **FIFA Official** — "All the World Cup 2026 squad announcements"
   - URL: https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/all-world-cup-squad-announcements
   - Coverage: Official FIFA announcements, updated as squads confirmed

## Update Procedure

### Phase 1: Squad Cross-Reference (use after squad announcements)

1. Extract list of announced squads from BBC/FIFA/The Athletic
2. For each squad, check if KEY players are MISSING (not just injured — also omitted)
3. Cross-reference with ESPN injuries tracker for confirmed injury absences
4. Flag: player NOT in squad + reason unknown → search individual news

### Phase 2: Injury Severity Assessment

1. For each confirmed OUT player, classify severity:
   - **core**: undisputed starter, Ballon d'Or candidate, team's best player
   - **important**: regular starter, key system player
   - **role**: squad rotation player, young prospect, not guaranteed starter
2. For DOUBTFUL players, check recovery timeline vs June 11 kickoff
3. If player is NAMED in squad despite injury → reduce penalty (manager expects them fit)

### Phase 3: ELO Penalty Mapping

| Status | Core | Important | Role |
|:---:|:---:|:---:|:---:|
| OUT (confirmed absent) | -40 | -25 | -15 |
| DOUBTFUL (racing, unlikely) | -20 | -15 | -10 |
| MINOR (expected fit) | -10 | -5 | -3 |

### Phase 4: Data Update

1. Update `data/injuries.json` — add/remove/modify players
2. Recalculate `total_penalty` for each affected team
3. Update `data/team_metadata.json` if injuries affect roster_stability or chemistry
4. Re-run simulation: `python3.11 wc2026_predict.py --report --sims 5000`
5. Verify impact: check championship probability deltas against previous run

## Current Injuries (2026-05-26)

| Team | Penalty | Players |
|------|:---:|------|
| England | -90 | Foden (OUT/core), Palmer (OUT/core), TAA (OUT/important) |
| Brazil | -80 | Rodrygo (OUT/core), Militao (OUT/important), Estevao (OUT/important) |
| Japan | -50 | Mitoma (OUT/core), Endo (DOUBTFUL/important), Minamino (DOUBTFUL/role) |
| Germany | -45 | Gnabry (OUT/core), Ter Stegen (DOUBTFUL/important) |
| Spain | -30 | Yamal (DOUBTFUL/core), Merino (DOUBTFUL/important) |
| Netherlands | -25 | Xavi Simons (OUT/important) |
| Ghana | -20 | Kudus (DOUBTFUL/core) |
| Argentina | -15 | Romero (DOUBTFUL/important) |
| France | -10 | Ekitike (OUT/role) |
| Canada | -10 | Davies (DOUBTFUL/core) |

## Common Pitfalls

- **Squad announcement ≠ injury confirmation**: Player not in squad could be tactical omission, not injury. Verify with injury-specific sources.
- **Recovery timeline optimism**: Teams often claim player "should be fit" right up until they're ruled out. Treat club-side optimism skeptically.
- **Goalkeeper injuries impact less**: Ter Stegen DOUBTFUL but Neuer returns → net GK situation unchanged. Don't double-penalize.
- **Stacking penalties**: Three OUT players from same position (e.g. England's three creative attackers) has multiplicative effect beyond sum of individual penalties. Consider adding a "synergy penalty" for same-position clusters.
- **Yamal status fluid**: Barcelona says "expected fit", but hamstring re-injury risk is real. Keep DOUBTFUL until he plays a friendly.

## Pre-Tournament Update Window

- **June 1**: Final 26-man squads submitted to FIFA
- **June 2**: FIFA officially publishes all squads
- **June 5-7**: Final pre-tournament injury assessment — re-run everything
- **June 11**: Tournament kickoff (Mexico vs South Africa)
