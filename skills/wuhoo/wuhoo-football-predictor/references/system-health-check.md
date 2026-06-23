# WC2026 系统健康检查清单

> 适用场景: 系统恢复后、多日未维护后、用户要求全面检查时
> 最后验证: 2026-06-22 (8项检查全部通过)

## 检查清单

### 1. Schedule ↔ Results 同步
```python
import json
with open('data/wc2026_schedule.json') as f: sched = json.load(f)
with open('data/wc2026_results.json') as f: results = json.load(f)
sched_completed = sum(1 for m in sched['matches'] if m.get('status') == 'completed')
results_count = len(results['matches'])
print(f"Schedule: {sched_completed}/72 | Results: {results_count}")
# 应相等。不等→执行同步脚本
```
**修复**: `execute_code` 脚本遍历 results 写入 schedule status/score

### 2. ELO 评分新鲜度
```bash
python3.11 -c "import json; d=json.load(open('data/elo_ratings.json')); print(d.get('last_updated','MISSING')); print('Applied:', len(d.get('applied_results',[])))"
```
**修复**: `python3.11 scripts/update_elo_from_results.py`

### 3. 伤病数据新鲜度
```bash
python3.11 -c "import json; d=json.load(open('data/injuries.json')); print('Updated:', d.get('last_updated')); print('Teams:', len(d.get('injuries',{})))"
```
**修复**: web_search ESPN 追踪器 + 逐队搜索 → 更新 injuries.json

### 4. 每日预测覆盖
检查 `data/daily_predictions/` 下 JSON 文件是否有实际预测数据（predictions > 0）

### 5. 非结构化信号缓存
检查 `data/signal_cache/` 是否有今日日期文件

### 6. 报告文件
检查 `data/reports/` 下是否有最新日期的 .md 和 .pdf

### 7. 预测准确率
```bash
python3.11 -c "import json; d=json.load(open('data/prediction_accuracy.json')); print(f'Accuracy: {d[\"accuracy\"]:.1%} | Brier: {d[\"brier_score\"]:.4f}')"
```
- 准确率 < 40% + ELO > 3天未更新 → 强相关，先刷新 ELO

### 8. Cron 作业健康
```bash
# 确认 WC2026 相关的 2 个 cron job:
# 5154715032ec: 数据刷新+结果采集 (14:30 daily)
# 86912ff0a4aa: 赛前预测报告 (15:00 daily)
# 两者都应 enabled=true, last_status=ok
```

## 审计脚本 (一键执行)

将此脚本放入 `execute_code`:
```python
import json, os
from datetime import datetime

base = '/path/to/data'

# 1. Schedule sync
with open(f'{base}/wc2026_schedule.json') as f: sched = json.load(f)
with open(f'{base}/wc2026_results.json') as f: results = json.load(f)
sc = sum(1 for m in sched['matches'] if m.get('status')=='completed')
rc = len(results['matches'])
print(f"[{'OK' if sc==rc else 'FAIL'}] Schedule: {sc}/72 vs Results: {rc}")

# 2. ELO
with open(f'{base}/elo_ratings.json') as f: elo = json.load(f)
elo_age = (datetime.now() - datetime.fromisoformat(elo.get('last_updated','2000-01-01'))).days
print(f"[{'OK' if elo_age<=1 else 'STALE'}] ELO age: {elo_age}d | Results applied: {len(elo.get('applied_results',[]))}")

# 3. Injuries
with open(f'{base}/injuries.json') as f: inj = json.load(f)
inj_age = (datetime.now() - datetime.fromisoformat(inj.get('last_updated','2000-01-01').split('+')[0])).days
print(f"[{'OK' if inj_age<=2 else 'STALE'}] Injuries age: {inj_age}d | Teams: {len(inj.get('injuries',{}))}")

# 4. Predictions
dp_dir = f'{base}/daily_predictions'
for f in sorted(os.listdir(dp_dir))[-3:]:
    with open(os.path.join(dp_dir, f)) as fp:
        d = json.load(fp)
    print(f"  {f}: {len(d.get('predictions',[]))} predictions")

# 5. Accuracy
with open(f'{base}/prediction_accuracy.json') as f: acc = json.load(f)
print(f"Accuracy: {acc['accuracy']:.1%} | Brier: {acc['brier_score']:.4f}")
```

## 已知数据陷阱

| 陷阱 | 症状 | 修复 |
|------|------|------|
| ELO 静默过期 | 预测准确率持续下降 | `update_elo_from_results.py` |
| Schedule 不同步 | completed 计数≠results 计数 | execute_code 同步脚本 |
| Injuries 静默过期 | 赛中伤病未反映 | web_search + ESPN 追踪器 |
| collect_results 裸调 | 静默 exit 1，cron 误报无新结果 | 必须带 --manual JSON |
| 两份 SKILL.md | skill_view ambiguous | 只保留 workspace 副本 |
