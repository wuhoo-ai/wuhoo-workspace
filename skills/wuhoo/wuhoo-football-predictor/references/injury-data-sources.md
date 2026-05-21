# Injury Data Sources & Update Procedure

## Current State (2026-05-21)

7 teams, 11 players with confirmed or doubtful injuries affecting World Cup 2026 participation.

## Primary Sources

1. **Al Jazeera** — "Which injured players could miss the FIFA World Cup 2026?"
   - URL: https://www.aljazeera.com/sports/2026/4/26/will-yamal-salah-and-ekitike-miss-the-world-cup-2026-due-to-injury
   - Published: April 26, 2026
   - Coverage: Comprehensive list of all major injuries

2. **BBC Sport** — "World Cup 2026 injury watch"
   - URL: https://www.bbc.com/sport/football/articles/c87wzlpd5l7o
   - Published: May 2026
   - Coverage: Yamal, Ter Stegen, Romero focus

## Update Procedure

1. Run web_search: "2026 World Cup injury players missing squad June 2026"
2. Extract confirmed OUT and DOUBTFUL players
3. Map to ELO penalty using the scale:
   - OUT core: -40, OUT important: -25, OUT role: -15
   - DOUBTFUL core: -20, DOUBTFUL important: -15, DOUBTFUL role: -10
4. Update `data/injuries.json` with new players
5. Update `total_penalty` for each affected team
6. Re-run simulation to verify impact

## Current Injuries (2026-05-21)

| Team | Penalty | Players |
|------|:---:|------|
| Brazil | -60 | Rodrygo (OUT), Militao (OUT), Estevao (DOUBTFUL) |
| Germany | -35 | Ter Stegen (DOUBTFUL), Gnabry (DOUBTFUL) |
| Netherlands | -25 | Xavi Simons (OUT, ACL) |
| Japan | -25 | Endo (DOUBTFUL), Minamino (DOUBTFUL) |
| Spain | -15 | Lamine Yamal (DOUBTFUL, hamstring) |
| France | -10 | Hugo Ekitike (OUT, Achilles) |
| Egypt | -10 | Mohamed Salah (DOUBTFUL, expected fit) |

## Pre-Tournament Update Window

World Cup starts June 11, 2026. Final squad lists should be announced ~June 1.
Re-run full injury assessment on June 5-7 to capture final pre-tournament state.