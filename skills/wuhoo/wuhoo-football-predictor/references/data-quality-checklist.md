# Data Quality Checklist — Knockout Match Entry

Every time knockout match results are entered into `wc2026_results.json`, run this checklist.

## Required Fields Per Match

| Field | Required? | Example | Notes |
|-------|-----------|---------|-------|
| `match_id` | ✅ | `86` | Must match knockout_schedule |
| `date` | ✅ | `"2026-07-04"` | ISO format |
| `date_beijing` | ✅ | `"2026-07-04"` | Same as date for knockout (already BJT) |
| `team_a` | ✅ | `"Argentina"` | Canonical name from team_profiles.json |
| `team_b` | ✅ | `"Cape Verde"` | Canonical name |
| `score_a` | ✅ | `3` | Integer, 90-min or AET score |
| `score_b` | ✅ | `2` | Integer |
| `status` | ✅ | `"completed"` | MUST be "completed" or ELO update skips |
| `winner` | ✅ | `"Argentina"` | Knockout MUST have winner |
| `round` | ✅ | `"R32"` | One of R32/R16/QF/SF/F/3rd |
| `penalties` | ⚠️ | `"3-4"` | Required if score_a == score_b (PK win) |
| `aet` | ⚠️ | `true` | Required if match went to extra time |

## Verification Command

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-football-predictor
python3.11 -c "
import json
r = json.load(open('data/wc2026_results.json'))
matches = r.get('matches', r)
ko = [m for m in matches if m.get('match_id',0) >= 73]
for m in sorted(ko, key=lambda x: x['match_id']):
    issues = []
    if not m.get('date_beijing'): issues.append('date_beijing')
    if m.get('score_a') == m.get('score_b') and m.get('winner') and not m.get('penalties'):
        issues.append('penalties')
    if m.get('aet') and m.get('score_a') == m.get('score_b') and not m.get('penalties'):
        pass  # AET + draw = PK already flagged
    if m.get('status') == 'completed' and not m.get('winner'):
        issues.append('winner')
    if issues:
        print(f'M{m[\"match_id\"]}: MISSING {issues}')
    else:
        print(f'M{m[\"match_id\"]}: OK')
"
```

## Known Historical Issues

| Date | Issue | Impact |
|------|-------|--------|
| 7/04 | M80-M88 missing `date_beijing` | Tournament form showed empty dates for 9 matches |
| 7/04 | M74/M75 missing `penalties` | PK resolution not documented |
| 7/04 | M73/M80-M85 missing `winner` | R16 slot filling failed for 7 matches |
| 6/28 | M67-M72 missing `status:'completed'` | ELO update silently skipped |
