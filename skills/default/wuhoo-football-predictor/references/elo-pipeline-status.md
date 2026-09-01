# ELO Data Pipeline Status (v2.3)

## Current State (2026-05-21)

### Source
- **Primary**: international-football.net (structured HTML table, mirrors eloratings.net)
- **Secondary**: eloratings.net web_search snippets (for cross-validation)
- **Tertiary**: Hardcoded STATIC_ELO fallback in fetch_elo.py (64 teams, updated 2026-05-21)

### Pipeline Architecture (fetch_elo.py v2.0)

```
fetch_elo.py
├── Tier 1: HTTP fetch international-football.net
│   └── curl with rate-limit awareness (429 → skip to Tier 3)
├── Tier 2: Merge with existing elo_ratings.json (preserve manual curation)
├── Tier 3: STATIC_ELO fallback (64 teams, updated via --update-static)
└── Output: elo_ratings.json (same format, backwards compatible)
```

### Key Improvements vs v2.2
| Item | Old | New |
|------|-----|-----|
| Data source | clubelo.com (dead) | international-football.net + eloratings.net |
| Teams | 55 | 64 |
| Auto-update | ❌ curl dead API | ✅ multi-source cascade |
| Agent-assisted update | ❌ manual | ✅ --update-static via stdin |
| Name normalization | ❌ raw keys | ✅ TEAM_ALIASES dict |
| Duplicate detection | ❌ | ✅ canonical name dedup |
| Diff support | ❌ | ✅ --diff flag |

### Data Quality
- 48/48 WC teams covered ✅
- 64 teams total (16 non-Q: Italy, Chile, Wales, Peru, etc.)
- Source: international-football.net + eloratings.net (2026-05-21)
- All team names normalized to canonical form (e.g., "United States" not "USA")

### Key ELO Changes vs v2.2 (May 1 data)
| Team | Old | New | Δ |
|------|-----|-----|---|
| Norway | 1760 | 1912 | +152 |
| Paraguay | 1755 | 1833 | +78 |
| Ecuador | 1865 | 1933 | +68 |
| United States | 1920 | 1721 | -199 |
| Belgium | 1982 | 1866 | -116 |
| Morocco | 1933 | 1821 | -112 |
| Italy | 1968 | 1856 | -112 |
| Qatar | 1705 | 1427 | -278 |
| Ghana | 1795 | 1505 | -290 |

### Agent Update Procedure
```bash
# Agent fetches latest data via web_extract, then pipes to script:
python3.11 scripts/fetch_elo.py --update-static <<'EOF'
{"Spain": 2165, "Argentina": 2113, ...}
EOF
```
