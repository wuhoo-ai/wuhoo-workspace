# Matchday 3 Motivation Patterns

> Framework for classifying team motivation in World Cup group stage final round.
> Based on historical patterns (WC1994-2022) and 48-team tournament dynamics.

## 6-Class Motivation Taxonomy

| Class | Code | ELO Adj | Definition | Typical Scenario |
|-------|------|---------|------------|-----------------|
| **铁定出线** | LOCKED_IN | -30 | Already qualified, likely to rotate | 6pts from 2MP, +3 GD gap to 3rd |
| **打平即出线** | DRAW_OK | -5 | Draw secures qualification | 4pts, 3pts gap to 3rd place |
| **需要拿分** | NEED_RESULT | +10 | Need at least a point | 3pts, within reach of 2nd |
| **背水一战** | MUST_WIN | +20 | Must win to have a chance | 3rd place, 1-2pts behind 2nd |
| **荣誉之战** | PRIDE_ONLY | -5 | Already eliminated | 0pts from 2MP, -4+ gap to 2nd |
| **头名之争** | TOP_SEED | +8 | Battling for group top spot | 1st vs 2nd within 2pts, direct matchup |

## Classification Logic (Priority Order)

1. **LOCKED_IN** — 6pts from 2MP AND gap to 3rd ≥ 4pts, OR 4+ pts AND gap to 3rd ≥ 4pts
2. **PRIDE_ONLY** — 0pts from 2MP AND gap to 2nd ≥ 4pts
3. **TOP_SEED** — 1st vs 2nd gap ≤ 2pts
4. **DRAW_OK** — Gap to 3rd ≥ 2pts (draw guarantees advancement)
5. **MUST_WIN** — Gap to 2nd ≥ 2pts (must win)
6. **NEED_RESULT** — Everything else

## Third-Place Advancement Thresholds

48-team format: 8 of 12 third-place teams advance. Opta estimates:

| Points | GD | Adv Prob |
|--------|-----|----------|
| 4+ | any | ~99% |
| 3 | +3+ | ~90% |
| 3 | 0~+2 | ~80% |
| 3 | 0 | ~70% |
| 3 | -1~-2 | ~55% |
| 3 | -3+ | ~40% |
| 2 | any | ~30% |
| 1 | any | ~10% |
| 0 | any | ~0% |

## Simultaneous Kickoff Effect (P2-deferred)

MD3 matches in the same group kick off simultaneously. Coaches monitor the other match in real time:

- If the other result favors your position → reduce urgency (DRAW_OK → near LOCKED_IN)
- If the other result hurts your position → increase urgency (NEED_RESULT → MUST_WIN)

Implementation: use pre-match odds movement as a proxy for expected simultaneity effects.

## Edge Cases

1. **K/L groups with 1MP**: Use `confidence: medium`, classification may change after MD2 completion
2. **Tied on points+GD+GF**: Use head-to-head record (FIFA tiebreaker #1) — not yet implemented in motivation logic
3. **Incomplete MD2**: Teams with MP<2 get medium confidence; reclassify after MD2 results
4. **Group E path diff**: 1st path=1643 ELO (easy) vs 2nd path=2045 ELO (hard) — massive motivation to win group at all costs

## 2026 Group-by-Group MD3 Summary

| Group | Locked | Top Seed | Draw-OK | Need Result | Must Win | Eliminated |
|-------|--------|----------|---------|-------------|----------|------------|
| A | — | Mexico | South Korea | — | Czech Rep, South Africa | — |
| B | — | Switzerland, Canada | — | — | Bosnia, Qatar | — |
| C | — | Brazil, Morocco | — | — | Scotland | Haiti |
| D | USA | — | — | Australia | Paraguay, Turkey | — |
| E | Germany | — | Ivory Coast | — | Ecuador, Curacao | — |
| F | — | Netherlands, Japan | — | — | Sweden | Tunisia |
| G | — | Egypt | — | Iran | Belgium, New Zealand | — |
| H | — | Spain | — | Uruguay | Cape Verde, Saudi Arabia | — |
| I | Norway | France | — | — | Senegal | Iraq |
| J | Argentina | — | — | Austria | Algeria, Jordan | — |
| K | — | — | — | Colombia | Portugal, DR Congo, Uzbekistan | — |
| L | — | — | — | England, Ghana | Panama, Croatia | — |
