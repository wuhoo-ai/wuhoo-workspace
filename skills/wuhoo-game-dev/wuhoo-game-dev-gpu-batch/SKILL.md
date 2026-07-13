---
name: wuhoo-game-dev-gpu-batch
description: "Use when a task needs GPU (HeartMuLa/Unity/Blender) OR is token-heavy (bulk coding via delegate_task) and should defer to off-peak hours for cost optimization. Daytime peak (CST 09-12,14-18): enqueue only, no heavy work. Off-peak (CST 00-09,12-14,18-24): cron-driven batch execution at low token pricing + GPU node on-hours. Manages the full deferred-work lifecycle."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, gpu, batch, off-peak, cost-optimization, heartmula, unity-build, coding, cron]
    related_skills: [wuhoo-game-dev-code-from-task, wuhoo-game-dev-daily-build, wuhoo-game-dev-music-from-task, wuhoo-game-dev-sprite-from-task, heartmula, delegate_task, cronjob]
---

# Wuhoo Batch Queue — 峰谷编排

一个 skill，统一管理所有应延迟到低谷时段执行的「重任务」：
**GPU 密集型** (HeartMuLa/Unity/Blender) + **Token 密集型** (批量编码)。

## 峰谷时间定义

```
北京时间 (CST, UTC+8):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  高峰 (不跑重任务):
    上午  09:00 — 12:00
    下午  14:00 — 18:00
    合计  7 小时 — 你在线交互, 只做设计/Review/轻量

  低谷 (批量执行窗口):
    凌晨  00:00 — 09:00   ← 主力窗口
    午休  12:00 — 14:00
    夜间  18:00 — 24:00
    合计  17 小时

  GPU 节点通电窗口: 02:00 — 05:00 (3h, 在低谷内)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 任务类型 (扩展)

| type | 何时入队 | 执行引擎 | 预估 Token | 需 GPU? | 优先级 |
|------|---------|---------|-----------|---------|--------|
| `heartmula` | 日间 music-from-task | HeartMuLa 3B | 0 | ✅ | 1 |
| `unity-build` | 日间 daily-build | Unity CLI | 0 | ❌(但需Windows) | 2 |
| `blender` | 日间 sprite-from-task | Blender headless | 0 | ⚠️ | 1 |
| `code-heavy` | **日间 code-from-task** | **delegate_task** | **高 (30K-100K)** | ❌ | 1 |
| `test-suite` | 日间 code-from-task | Unity Test Runner | 低 | ❌ | 2 |
| `balance-sim` | 日间 balance-validate | Python Monte Carlo | 中 | ❌ | 2 |
| `pixel-render` | 日间 sprite-from-task | pixel-art skill | 低 | ❌ | 1 |
| `ffmpeg` | 日间 audio post | ffmpeg | 0 | ❌ | 3 |

## 入队策略：日间不跑重活

日间 Hermes 检测到当前是高峰时段 + 任务符合入队条件时 → 入队而非直接执行：

```python
def should_defer(task_type, params):
    now = datetime.now(tz=timezone('Asia/Shanghai'))
    hour = now.hour
    
    # 判断是否高峰
    is_peak = (9 <= hour < 12) or (14 <= hour < 18)
    if not is_peak:
        return False  # 低谷时段, 直接跑
    
    # 高峰时段, 只跑轻量任务
    heavy_types = {'heartmula', 'unity-build', 'blender', 'code-heavy', 'balance-sim'}
    if task_type in heavy_types:
        return True  # 入队, 等低谷
    
    # 代码任务 — 按预估 token 量判断
    if task_type == 'code' and params.get('estimated_tokens', 0) > 10000:
        return True
    
    return False  # 轻量任务, 直接跑
```

**日间不影响的工作**（直接执行，不入队）：
- gdd-to-tasks（编排，低 token）
- review-task（审查，中 token 但需要你即时反馈）
- 轻量 code-from-task（<10K token，如修一个 bug 或小 function）
- sprite-from-task 的 spec 编写（入队的是 pixel-render 阶段）
- music-from-task 的 lyrics/tags 编写（入队的是 HeartMuLa 生成阶段）

## 队列文件 (扩展)

```json
{
  "queue_id": "2026-07-14-batch-01",
  "created": "2026-07-13T23:00:00+08:00",
  "node": {
    "host": "192.168.x.x",
    "user": "admin",
    "gpu": "RTX 4070 Ti 12GB",
    "wol_mac": "aa:bb:cc:dd:ee:ff",
    "power_window": "02:00-05:00 CST"
  },
  "tasks": [
    {
      "id": "T003_code",
      "type": "code-heavy",
      "status": "pending",
      "priority": 1,
      "spec": "实现采矿系统 MiningSystem.cs",
      "params": {
        "task_json_path": "tasks.json#T003",
        "estimated_tokens": 50000,
        "delegate_model": "deepseek-v4-pro"
      },
      "output": ["Scripts/Systems/MiningSystem.cs", "Scripts/Data/MineralData.cs"],
      "depends_on": ["T001", "T002"]
    },
    {
      "id": "T017_music_bgm_day",
      "type": "heartmula",
      "status": "pending",
      "priority": 2,
      "spec": "BGM 白天探索 70BPM",
      "params": {
        "tags": "adventure,orchestral,70bpm,hopeful,major-key",
        "duration_sec": 120,
        "lyrics_file": "lyrics_instrumental.txt"
      },
      "output": "Assets/Audio/BGM/bgm_day.mp3",
      "depends_on": []
    }
  ]
}
```

## Phase 2: 批量执行 (低谷 cron)

### 执行窗口

```
CST 02:00 — cron 触发
  │
  ├─ 02:00  读取队列, 排序
  ├─ 02:00  GPU 节点 WoL 开机, 等待就绪
  │
  ├─ 02:05  Phase A: code-heavy 任务 (云上 delegate_task)
  │         5-10 个并行, 每个 30K-100K token
  │         利用低谷 DeepSeek 价格 (~50% off)
  │         耗时: ~20-40 min
  │
  ├─ 02:45  Phase B: GPU 任务 (SSH 到 4070 Ti)
  │         heartmula → blender → unity-build
  │         串行 (避免 VRAM/CPU 争抢)
  │         耗时: ~30-60 min
  │
  ├─ 03:45  Phase C: 轻量后处理 (云上)
  │         pixel-render / ffmpeg / balance-sim
  │         耗时: ~5-10 min
  │
  ├─ 04:00  scp 产物回传 + git push
  ├─ 04:10  GPU 节点关机
  ├─ 04:15  队列清理 + 归档
  └─ 04:20  WeChat 通知
```

### Phase A: Code-Heavy 批量编码

```python
# 低谷时段, 对每个 code-heavy task 派发 delegate_task
for task in get_pending('code-heavy'):
    task_spec = load_task_json(task['params']['task_json_path'])
    
    delegate_task(
        goal=task_spec['spec'],
        context=f"""
        Task: {task['id']}
        Spec: {task_spec['spec']}
        Params: {json.dumps(task_spec.get('params', {}))}
        Output files: {task_spec['output']}
        Test criteria: {task_spec['test']}
        Existing codebase: see repo at /mnt/shared/unity-project
        """,
        role='leaf'
    )
    # delegate_task 是异步的, 派完继续下一个
    # 所有 coding agent 并行工作
```

**并发控制**: 单次最多 3 个 code-heavy 并行（Hermes 默认限制），串行依赖的 task 按 depends_on 排序。

### Phase B: GPU 任务

（与 v1.0 相同，HeartMuLa → Unity → Blender）

### Step 5 (更新): 通知

```
🤖 Off-Peak Batch #03 完成  |  02:00-04:15 CST

📝 Code (低谷 token):
  ✅ T003_code  MiningSystem.cs         (52K token, 18min)
  ✅ T004_code  InventorySystem.cs      (38K token, 12min)
  ✅ T005_code  ShopSystem.cs           (45K token, 15min)
  ❌ T008_code  EnemyAI.cs              (OOM — context too large)

🎵 Audio (GPU):
  ✅ T017_music_bgm_day     (2m34s, 3.2MB)
  ✅ T017_music_bgm_night   (1m58s, 2.8MB)

🏗️ Build (GPU):
  ✅ T020_build_win         (8m15s, 45MB)
  ✅ T020_build_android     (6m42s, 38MB)

💰 预估节省: ~120K token × 低谷价 ≈ 节省 40-50%
🔌 GPU 节点已关机  |  📦 产物已推送
```

## Cron 配置 (更新)

```bash
# 主批次: 每天 CST 02:00 (UTC 18:00)
hermes cron create '0 18 * * *' \
  --name 'off-peak-batch' \
  --prompt '加载 wuhoo-game-dev-gpu-batch skill。按 Phase A→B→C 顺序执行所有 pending 队列任务。Phase A: delegate_task 并行跑 code-heavy 任务。Phase B: SSH GPU 节点执行 heartmula/unity/blender。Phase C: 云上跑 pixel-render/ffmpeg。完成后回传产物、关机 GPU 节点、清理队列、WeChat 通知。' \
  --skills 'wuhoo-game-dev-gpu-batch' \
  --deliver 'wechat' \
  --enabled_toolsets 'terminal,file,web,delegation'

# 午休补充批次: 每天 CST 12:30 (UTC 04:30) — 只跑 code-heavy, 不开 GPU 节点
hermes cron create '30 4 * * *' \
  --name 'lunch-batch' \
  --prompt '加载 wuhoo-game-dev-gpu-batch skill。只执行 code-heavy 类型的 pending 任务 (delegate_task), 不启动 GPU 节点。完成后 WeChat 通知。' \
  --skills 'wuhoo-game-dev-gpu-batch' \
  --deliver 'wechat' \
  --enabled_toolsets 'terminal,file,delegation'
```

## 日间 code-from-task 变更

日间 code-from-task skill 在高峰时段遇到重任务时：

```
if is_peak_hours() and estimated_tokens > 10000:
    → 不入队: 不执行
    → 写入 gpu-queue.json (type=code-heavy)
    → 回复用户: "T003 已入队, 凌晨低谷批量编码, 明早可 Review"
else:
    → 正常执行 (轻量 fix/小 function)
```

## 成本模型

```
假设一天的工作量:
  10 个 code-heavy task × 50K token = 500K token

高峰全部执行:
  500K × DeepSeek v4-pro 高峰价 ≈ $X

低谷全部执行:
  500K × DeepSeek v4-pro 低谷价 ≈ $X × 0.5 ≈ 节省 50%
  + GPU 电费 3h ≈ ¥1

  月度节省: 可估算为原来的 40-60%
```

## Pitfalls

1. code-heavy 并发超限 — Hermes 默认 max 3 并行 delegate_task → 串行依赖的按序, 独立的并行
2. 编码任务 OOM — 上下文窗口溢出 (代码库太大) → 拆分为更小的 sub-task
3. 低谷时段编码 Agent 出错无人看管 → 失败 task 保留在队列, 次日白天人工 Review 后决定重跑或手动修
4. 日间立刻需要的 task 被误入队 → code-from-task 加 `--now` flag 跳过峰谷检测, 强制立即执行
5. GPU 节点没开机时 code-heavy 也要等? → 不, code-heavy 在云上跑, 不进 GPU 节点。只有 heartmula/unity/blender 等 GPU 节点

## Verification

- [ ] 当前时间正确判断高峰/低谷
- [ ] 高峰时段 code-heavy/heartmula/unity-build 入队而非执行
- [ ] 低谷 cron 按 Phase A→B→C 顺序执行
- [ ] code-heavy 结果已 commit 到 repo
- [ ] GPU 产物已回传
- [ ] GPU 节点已关机
- [ ] WeChat 通知包含成功/失败统计 + 节省估算
