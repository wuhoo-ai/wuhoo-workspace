# 遗漏赛果恢复工作流

**触发**: 推演报告/预测与实际比赛结果不符，怀疑赛果漏采。

## 案例 (2026-07-05)

Cron 14:30 运行时 `collect_results.py --check` 仅检查当日 (7/5) 预约比赛，遗漏了 7/4 已完赛但未录入的 2 场 R16 比赛：
- Canada 0-3 Morocco
- Paraguay 0-1 France

wc2026_results.json 仅有 88 场，缺少这两场。导致 bracket_recursive 推演基于过期 EL0 数据运行。

## 诊断步骤

```bash
cd /home/admin/wuhoo-workspace/skills/default/wuhoo-football-predictor

# 1. 检查 schedule 中 date < today 但不在 results 中的比赛
python3.11 -c "
import json, datetime
today = datetime.date.today()
with open('data/wc2026_results.json') as f:
    results = json.load(f)['matches']
with open('data/knockout_schedule.json') as f:
    ko = json.load(f).get('matches', [])
with open('data/wc2026_schedule.json') as f:
    sched = json.load(f).get('matches', [])

result_ids = {m['match_id'] for m in results}
all_sched = sched + ko
missed = [m for m in all_sched 
          if m.get('date_beijing','') < today.isoformat() 
          and m['match_id'] not in result_ids
          and m.get('team_a') and m.get('team_b')]
for m in missed:
    print(f\"MISSED: ID:{m['match_id']} {m['date_beijing']} {m.get('team_a')} vs {m.get('team_b')}\")
"
```

## 恢复步骤

### 1. 从 web_search 获取赛果

```
web_search("TeamA TeamB World Cup 2026 score result July XX")
```

验证至少 2 个独立来源（ESPN + 其他媒体）。

### 2. 手动录入到 wc2026_results.json

```python
# 用 execute_code 追加赛果，确保字段完整
# 必填: match_id, date_beijing, date, team_a, team_b, score_a, score_b
# 淘汰赛必填: stage="round_of_16", round="R16", status="completed", winner="<胜者>"
# 不要遗漏: collected_at 时间戳, source="manual"
```

### 3. 更新 ELO

```bash
python3.11 scripts/update_elo_from_results.py
```

### 4. 重新推演

```bash
python3.11 scripts/bracket_recursive.py --sims 10
python3.11 scripts/generate_bracket_pdf.py --from-json data/bracket_recursive_results.json
```

### 5. 重新生成单场 PDF（如需要）

```bash
python3.11 scripts/generate_single_match_pdf.py --date 2026-07-06 --all
```

### 6. 审计确认

用 execute_code 运行 5 维检查确认数据完整性。

## 根因与预防

**根因**: `collect_results.py --check` 仅检查当前日期。前一天比赛若未被 cron/手动采集，第二天不会自动追溯。

**预防措施**:
1. Cron 第 2 步采集赛果时应回溯前 2 天（不只是当天）
2. 数据保鲜检查应报告「schedule 中 date < today 但不在 results 中的比赛数」
3. bracket_recursive 运行前应验证所有已完赛 round 的比赛都已录入
