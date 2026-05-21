# ELO Data Pipeline Status (v2.2)

## Current State (2026-05-21)

### Source
- **Primary**: eloratings.net (2100-scale national team ELO)
- **Secondary** (fallback): clubelo.com (API dead since ~2026-05)

### Top 5 Confirmations (2026-05-20)
From web_search snippet of eloratings.net main page:
1. Spain 2165
2. Argentina 2113
3. France 2082
4. England 2020
5. Brazil 1984

### Key Changes vs v2.1 (2026-05-01 data)
| Team | Old | New | Δ |
|------|-----|-----|---|
| Spain | 2013 | 2165 | +152 |
| Argentina | 2114 | 2113 | -1 |
| France | 2075 | 2082 | +7 |
| Brazil | 2061 | 1984 | -77 |
| Netherlands | 1985 | 1961 | -24 |
| Uruguay | 1963 | 1892 | -71 |
| Ecuador | 1865 | 1933 | +68 |

### Data Quality
- 48/48 WC teams covered ✅
- 55 teams total (7 non-qualified: Italy, Denmark, etc.)
- 9 teams confirmed from live source
- 46 teams carried forward from 2026-05-01 with tier adjustments
- South Africa added manually (ELO 1720)

### Pipeline Issues
1. **clubelo.com API**: `http://api.clubelo.com/` returns empty → API likely decomissioned
2. **eloratings.net JS**: Site is JS-rendered, web_extract/curl returns empty body. Only web_search snippets reveal data.
3. **fetch_elo.py**: Still points to clubelo.com, falls back to hardcoded data from 2026-04-23

### Recommended Fix
Rewrite `scripts/fetch_elo.py` to:
1. Try eloratings.net via headless browser or proxy
2. Fall back to a maintained static JSON
3. Add web_search-based extraction as last resort
