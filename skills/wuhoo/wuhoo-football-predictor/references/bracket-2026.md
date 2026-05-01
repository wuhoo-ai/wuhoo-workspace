# WC2026 Bracket, Calibration & Venue Reference

> Condensed technical reference for future sessions. Source: Yahoo Sports schedule, FIFA regulations, Wikipedia.

## Official R32 Bracket (16 matches)

```
Slot Home                 Away                  Venue
 1   A2 (runner-up)       B2 (runner-up)        SoFi Stadium (LA)
 2   C1 (winner)          F2 (runner-up)        NRG Stadium (Houston)
 3   E1 (winner)          3rd(A/B/C/D/F)        Gillette Stadium (Boston)
 4   F1 (winner)          C2 (runner-up)        Estadio BBVA (Monterrey)
 5   E2 (runner-up)       I2 (runner-up)        AT&T Stadium (Dallas)
 6   I1 (winner)          3rd(C/D/F/G/H)        MetLife Stadium (NY)
 7   A1 (winner)          3rd(C/E/F/H/I)        Estadio Azteca (2200m!)
 8   L1 (winner)          3rd(E/H/I/J/K)        Mercedes-Benz Stadium (Atlanta)
 9   G1 (winner)          3rd(A/E/H/I/J)        Lumen Field (Seattle)
10   D1 (winner)          3rd(B/E/F/I/J)        Levi's Stadium (SF)
11   H1 (winner)          J2 (runner-up)        SoFi Stadium (LA)
12   K2 (runner-up)       L2 (runner-up)        BMO Field (Toronto)
13   B1 (winner)          3rd(E/F/G/I/J)        BC Place (Vancouver)
14   D2 (runner-up)       G2 (runner-up)        AT&T Stadium (Dallas)
15   J1 (winner)          H2 (runner-up)        Hard Rock Stadium (Miami, heat!)
16   K1 (winner)          3rd(D/E/I/J/L)        Arrowhead Stadium (Kansas City)
```

## R16 → QF → SF → Final Pairings

```
R16: (2v3), (1v16), (4v5), (6v7), (9v10), (8v11), (13v14), (12v15)
 QF: R16(1v2), R16(3v4), R16(5v6), R16(7v8)
 SF: QF(1v2), QF(3v4)
Final: SF winners
 3rd: SF losers
```

## Third-Place Assignment Algorithm

### Problem
FIFA publishes a 495-entry lookup table mapping which 8 groups' 3rd-place teams go to which R32 slots. Hardcoding all 495 is impractical. The official rule: 3rd-place teams always face group winners, never other 3rd-place or runners-up; no same-group rematch in R32.

### Our Constraint-Based Solution
1. Each T-slot has eligible groups (`T_SLOT_ELIGIBILITY` in code)
2. Sort T-slots by `len(eligible_groups ∩ available_groups)` ascending — most constrained first
3. For each T-slot in order, assign the highest-ranked eligible 3rd-place team
4. **Fallback**: if no eligible team remains for a slot, use best available (any group) — bracket is approximate but simulation continues

### Pitfall Encountered
Greedy assignment in T1→T8 order caused slot 13 to consistently fail (needs E/F/G/I/J, but those groups' 3rd teams were often already assigned to earlier slots). Fix: sort by constraint count first.

## KO Tie-Breaker Calibration

### Problem (v1)
Original code: `if draw: higher_ELO += 1`. This made Argentina (highest ELO) win EVERY close match → 87.8% champion probability. Unrealistic.

### Fix (v2)
Probabilistic tie-breaker:
```
p_higher_wins = 0.5 + min(abs(elo_diff) / 800, 0.15)
```
- Two equal-ELO teams: 50/50 on draws
- Argentina (2114) vs France (2075), diff=39: p = 0.549
- Result: Argentina 87.8% → 54.8% champion probability

## ELO Scale
- **2100-scale** (national-team only, clubelo.com). Argentina=2114, France=2075.
- **Do NOT use 1859-scale** (club-level, includes clubs) — that's the old `elo_ratings.json` from `fetch_data.py._get_default_elo()`.
- Backtest verified: WC2022 57.8% with 2100-scale (up from 56.2% with 1859-scale).

## Poisson Lambda Calibration
```
base = 1.45
lam_a = max(0.2, base * 10^(elo_diff / 500))
```
- Tuned for 2100-scale ELO. Average goals ~1.35 per team in WC2022.
- `base=1.45` gives lam=1.45 when elo_diff=0 (two equal teams).

## High-Altitude Venues
| Venue | Altitude | ELO Penalty (non-acclimated) |
|-------|----------|------------------------------|
| Estadio Azteca (Mexico City) | 2200m | -68 |
| Estadio Akron (Guadalajara) | 1566m | -43 |
| Estadio BBVA (Monterrey) | 537m | -2 |

Acclimated teams: Mexico, Ecuador, Colombia (high-altitude home nations).

## Heat Venues
| Venue | June/July Avg | Penalty (non-resistant, outdoor) |
|-------|---------------|----------------------------------|
| Hard Rock (Miami) | 32°C | -8 |
| Arrowhead (Kansas City) | 31°C | -6 |
| NRG (Houston) | 34°C | -6 (indoor, halved) |
| AT&T (Dallas) | 35°C | -7 (indoor, halved) |

Heat-resistant: South American, African, Middle Eastern, Australian teams.

## Cron Job
- `WC2026 ELO Weekly Update` — runs every Monday 00:00 SGT
- Executes: `python3.11 scripts/fetch_elo.py --output=data/elo_ratings.json`
- Job ID: `f5b003eee5fc`
