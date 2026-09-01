# v5.5 推理数据合并流程

## 问题

v5.5推理引擎（`predict_v55.py`）产出的JSON（`_v55.json`）与标准预测管线（`predict_by_date.py`）产出的JSON（`YYYY-MM-DD.json`）**结构不同**：

| 字段 | 标准JSON | v55 JSON |
|------|----------|----------|
| 顶层键 | `date_beijing`, `predictions`, `matches` | `date`, `engine`, `rules_version`, `matches` |
| 匹配详情 | `matches[].audit.layers` | `matches[].inference_trace` |
| 推理路径 | 无 | `matches[].reasoning_path` |
| 引擎标记 | 无 | `matches[].effective_elo.engine_delta_a/b` |

`generate_daily_report.py` 只读标准JSON（路径: `daily_predictions/{date}.json`），不查v55 JSON。**不合并的话报告中无v5.5推理路径**。

## 合并脚本

```python
import json
from pathlib import Path

DATE = '2026-06-25'
DATA_DIR = Path('data/daily_predictions')

with open(DATA_DIR / f'{DATE}.json') as f:
    std = json.load(f)
with open(DATA_DIR / f'{DATE}_v55.json') as f:
    v55 = json.load(f)

# 按 (team_a, team_b) 建v55查找表
v55_lookup = {(m['team_a'], m['team_b']): m for m in v55['matches']}

for m in std['matches']:
    ta = m['audit']['team_a']
    tb = m['audit']['team_b']
    vm = v55_lookup.get((ta, tb))
    if not vm:
        continue
    m['audit']['inference_engine'] = True
    m['audit']['reasoning_path'] = vm.get('reasoning_path', '')
    m['audit']['inference_trace'] = vm.get('inference_trace', {})
    # engine_delta在effective_elo顶层（不在team_a/team_b子对象内）
    veff = vm.get('effective_elo', {})
    m['audit']['effective_elo']['engine_delta_a'] = veff.get('engine_delta_a', 0)
    m['audit']['effective_elo']['engine_delta_b'] = veff.get('engine_delta_b', 0)

# 备份原文件后覆盖
import shutil
shutil.copy(DATA_DIR / f'{DATE}.json', DATA_DIR / f'{DATE}_std_backup.json')
with open(DATA_DIR / f'{DATE}.json', 'w') as f:
    json.dump(std, f, ensure_ascii=False, indent=2)
```

## 验证

```python
first = std['matches'][0]
assert first['audit']['inference_engine'] == True
assert len(first['audit']['reasoning_path']) > 100
assert 'engine_delta_a' in first['audit']['effective_elo']
```

## 生成报告

```bash
cd ~/wuhoo-workspace/skills/default/wuhoo-football-predictor
python3.11 scripts/generate_daily_report.py --date 2026-06-25 --json-only
```

## 常见错误

1. **engine_delta=0**: `engine_delta_a/b` 在v55的 `effective_elo` 顶层（不在`team_a`子对象内），直接写 `veff['team_a']['engine_delta']` 会报错或取0
2. **JSON被覆盖**: `generate_daily_report.py` 默认读 `{date}.json`，如果同时存在 `_merged.json`，需手动指定或覆盖标准文件
3. **文件大小暴增**: 合并后JSON从~39KB→~78KB（+inference_trace明细），报告PDF从107KB→154KB（+推理路径+规则明细表），可能触发微信100KB大小限制。解决方案: 拆分PDF或精简规则明细（只保留推理路径文字，去掉表格）
