# 数据完整性审计脚本模板

每次修改 `wc2026_results.json` 后必须执行。

```python
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

base = "/home/admin/wuhoo-workspace/skills/wuhoo/wuhoo-football-predictor/data"

with open(f"{base}/wc2026_schedule.json") as f:
    sched = json.load(f)['matches']
with open(f"{base}/wc2026_results.json") as f:
    results = json.load(f)['matches']

beijing_tz = timezone(timedelta(hours=8))
now = datetime.now(beijing_tz)
today = now.strftime('%Y-%m-%d')
result_by_id = {r['match_id']: r for r in results}

# === 1. 历史遗漏检查 ===
print("🔍 1) 历史遗漏")
missing = [m for m in sched 
           if m.get('date_beijing','') < today 
           and m['match_id'] not in result_by_id]
for m in missing:
    print(f"  ❌ #{m['match_id']} {m['team_a']} vs {m['team_b']} @ {m.get('date_beijing')}")
print(f"  {'✅ 无遗漏' if not missing else f'⚠️ {len(missing)}场遗漏'}")

# === 2. 今日赛程检查 ===
print(f"\n🔍 2) 今日 ({today})")
for m in sched:
    if m.get('date_beijing') != today: continue
    mid = m['match_id']
    time_str = m.get('time_beijing', '00:00')
    match_dt = datetime.strptime(f"{today} {time_str}", '%Y-%m-%d %H:%M').replace(tzinfo=beijing_tz)
    if mid in result_by_id:
        r = result_by_id[mid]
        print(f"  ✅ #{mid} {r['team_a']} {r['score_a']}-{r['score_b']} {r['team_b']}")
    elif match_dt + timedelta(hours=3) < now:
        print(f"  ⚠️ #{mid} {m['team_a']} vs {m['team_b']} — 应已完赛未采集")
    else:
        print(f"  ⏳ #{mid} {m['team_a']} vs {m['team_b']} — 尚未完赛")

# === 3. 一致性检查 ===
print(f"\n🔍 3) 一致性")
issues = []
for r in results:
    sm = next((m for m in sched if m['match_id'] == r['match_id']), None)
    if not sm:
        issues.append(f"#{r['match_id']}: 赛程中无此比赛")
        continue
    if r['team_a'] != sm['team_a'] or r['team_b'] != sm['team_b']:
        issues.append(f"#{r['match_id']}: team名不匹配")
    if r.get('date_beijing') != sm.get('date_beijing'):
        issues.append(f"#{r['match_id']}: 日期不匹配")
for i in issues: print(f"  ❌ {i}")
if not issues: print("  ✅ 全部一致")

# === 4. 重复检查 ===
print(f"\n🔍 4) 重复")
ids = [r['match_id'] for r in results]
dupes = {mid for mid in ids if ids.count(mid) > 1}
for d in dupes:
    entries = [r for r in results if r['match_id'] == d]
    print(f"  ❌ #{d} 出现{ids.count(d)}次")
if not dupes: print("  ✅ 无重复")

# === 5. 按日统计 ===
print(f"\n🔍 5) 按日统计")
by_date = defaultdict(lambda: {'sched': 0, 'result': 0})
for m in sched: by_date[m.get('date_beijing','?')]['sched'] += 1
for r in results: by_date[r.get('date_beijing','?')]['result'] += 1
for date in sorted(by_date.keys()):
    d = by_date[date]
    status = '✅' if d['result'] >= d['sched'] or date >= today else f'❌({d[\"sched\"]-d[\"result\"]}场漏)'
    print(f"  {status} {date}: 赛程{d['sched']}场 已采{d['result']}场")
```

## 比分交叉验证

审计通过后，额外抽检 3-5 场比分：
```python
# 用 web_search 验证
web_search("<Team_A> <Team_B> World Cup 2026 <date> final score")
```
用户纠正的比分无条件信任，立即更新。
