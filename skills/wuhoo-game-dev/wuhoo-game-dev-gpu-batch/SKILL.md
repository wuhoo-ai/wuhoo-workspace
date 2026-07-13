---
name: wuhoo-game-dev-gpu-batch
description: "Use when a task needs GPU (HeartMuLa music gen, Unity build, Blender render, sprite-to-pixel conversion) and the GPU node is offline or in batch mode. Daytime: append tasks to gpu-queue.json. Nighttime (cron 02:00 CST): SSH to 4070 Ti, execute all queued tasks in batch, fetch artifacts back, shutdown node, notify via WeChat. Manages the full GPU batch lifecycle."
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, gpu, batch, heartmula, unity-build, blender, cron]
    related_skills: [wuhoo-game-dev-daily-build, wuhoo-game-dev-music-from-task, wuhoo-game-dev-sprite-from-task, heartmula, cronjob]
---

# Wuhoo GPU Batch

GPU 任务队列管理 + 凌晨批量执行。一个 skill，两阶段：白天入队，凌晨跑批。

## 架构

```
白天 (云 Hermes)                      凌晨 2:00 CST (cron触发)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
日间 Agent 产出 spec/代码  ✅          1. SSH 到 GPU 节点
GPU 依赖任务 → 入队 queue  ⏳          2. 按 task.type 批量执行:
  - HeartMuLa BGM/SFX                        heartmula → 音乐生成
  - Unity Win+Android build                  unity → 多平台构建
  - Blender 3D 渲染                          blender → 模型导出
  - pixel-art 渲染                           pixel → spritesheet
  - ffmpeg 音视频后处理                       ffmpeg → 格式转换
                                       3. scp 产物回云存储
                                       4. 关机 GPU 节点
                                       5. WeChat 通知结果
```

## When to Use

- 日间 task 执行时检测到需要 GPU → 入队而非直接执行
- 凌晨 cron 触发 → 执行队列中所有 pending 任务
- 用户说：跑 GPU 批处理、检查 GPU 队列、GPU 节点状态

## 队列文件: ~/.hermes/gpu-queue.json

```json
{
  "queue_id": "2026-07-14-batch-01",
  "created": "2026-07-13T23:00:00+08:00",
  "node": {
    "host": "192.168.x.x",
    "user": "admin",
    "gpu": "RTX 4070 Ti 12GB",
    "wol_mac": "aa:bb:cc:dd:ee:ff"
  },
  "tasks": [
    {
      "id": "T017_music_bgm_day",
      "type": "heartmula",
      "status": "pending",
      "priority": 1,
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

## Phase 1: 入队 (日间)

日间 Hermes 执行 task 时，遇到 GPU 依赖调用入队函数：

```python
def enqueue_gpu_task(task_id, task_type, spec, params, output_path):
    queue = read_queue()
    # 防重复: 同一 task_id + pending → 跳过
    existing = [t for t in queue['tasks'] if t['id'] == task_id and t['status'] == 'pending']
    if existing:
        return f"Task {task_id} already queued, skipping"
    queue['tasks'].append({
        'id': task_id, 'type': task_type, 'status': 'pending',
        'priority': params.get('priority', 1),
        'spec': spec, 'params': params, 'output': output_path,
        'depends_on': params.get('depends_on', [])
    })
    write_queue(queue)
    return f"Queued: {task_id} ({task_type}) for GPU batch"
```

## Phase 2: 批量执行 (凌晨 cron)

### Step 1: 唤醒/检查 GPU 节点

```bash
# WoL 开机 (如果需要)
wakeonlan aa:bb:cc:dd:ee:ff
# 等待启动 + SSH 就绪 (最多 2 分钟)
for i in {1..12}; do
  ssh -o ConnectTimeout=5 admin@$GPU_HOST 'echo OK' 2>/dev/null && break
  sleep 10
done
```

### Step 2: 读取队列, 按优先级排序

```bash
cat ~/.hermes/gpu-queue.json | python3 -c "
import json, sys
q = json.load(sys.stdin)
pending = [t for t in q['tasks'] if t['status'] == 'pending']
pending.sort(key=lambda t: t['priority'])
print(f'{len(pending)} tasks to execute')
"
```

### Step 3: 按类型执行

```bash
# HeartMuLa 音乐 (优先级 1 — 先跑, GPU 独占)
for task_id in $(pending_by_type 'heartmula'); do
    params=$(task_param $task_id)
    ssh admin@$GPU_HOST "
        cd ~/heartlib && .venv/bin/activate
        python run_music_generation.py \
            --model_path=./ckpt --version=3B \
            --tags=<(echo '$tags') \
            --lyrics=./lyrics_instrumental.txt \
            --save_path=output/$task_id.mp3 \
            --lazy_load true --max_audio_length_ms $duration_ms
    "
    mark_complete $task_id
done

# Unity 构建 (优先级 2 — HeartMuLa 完成后跑)
for task_id in $(pending_by_type 'unity-build'); do
    target=$(task_param $task_id 'target')
    ssh admin@$GPU_HOST "
        '/mnt/c/Program Files/Unity/Hub/Editor/6000.x/Editor/Unity.exe' \
            -batchmode -nographics -quit \
            -projectPath /mnt/repo/unity-project \
            -buildTarget $target \
            -executeMethod BuildScript.PerformBuild \
            -logFile build_$task_id.log
    "
    mark_complete $task_id
done

# Blender 渲染 (优先级 1 — 和 HeartMuLa 可并行? 不, HeartMuLa 占了 GPU)
for task_id in $(pending_by_type 'blender'); do
    blend=$(task_param $task_id 'blend_file')
    script=$(task_param $task_id 'script')
    ssh admin@$GPU_HOST "blender '$blend' --background --python '$script'"
    mark_complete $task_id
done
```

### Step 4: 回传产物

```bash
scp -r admin@$GPU_HOST:output/* /mnt/shared/Assets/Audio/
scp -r admin@$GPU_HOST:build/* /mnt/shared/build/
scp -r admin@$GPU_HOST:heartlib/output/* /mnt/shared/Assets/Audio/BGM/

# 提交到 Git LFS
cd /mnt/shared && git add -A && git commit -m "gpu-batch: $(date +%Y-%m-%d)" && git push
```

### Step 5: 关机 + 通知

```bash
ssh admin@$GPU_HOST "sudo shutdown -h +1"
```

通知模板：

```
🤖 GPU Batch #03 完成  |  02:00-03:42 CST
11/12 ✅  |  1 ❌ (Boss sprite VRAM OOM)
产物已推送 Git LFS  |  🔌 GPU 节点已关机
```

### Step 6: 队列清理

```bash
python3 -c "
import json, shutil
from datetime import datetime
q = json.load(open('gpu-queue.json'))
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy('gpu-queue.json', f'gpu-queue-archive/{ts}.json')
# 保留 failed + pending, 移除 completed
q['tasks'] = [t for t in q['tasks'] if t['status'] in ('pending','failed')]
q['queue_id'] = f'batch-{ts}'
json.dump(q, open('gpu-queue.json','w'), indent=2)
"
```

## Cron 配置

```bash
hermes cron create '0 18 * * *' \
  --name 'gpu-nightly-batch' \
  --prompt '加载 wuhoo-game-dev-gpu-batch skill, 读取 gpu-queue.json, SSH 到 GPU 节点执行所有 pending 任务, 回传产物, 关机, WeChat 通知' \
  --skills 'wuhoo-game-dev-gpu-batch' \
  --deliver 'wechat' \
  --enabled_toolsets 'terminal,file,web'
```

> UTC 18:00 = CST 02:00

## GPU 任务类型速查

| type | 引擎 | 预估耗时 | 优先级 | 独占 GPU? |
|------|------|---------|--------|----------|
| `heartmula` | HeartMuLa 3B | 2-4 min/首 | 1 | ✅ 是 |
| `unity-build` | Unity CLI | 6-15 min/平台 | 2 | ❌ 否 |
| `blender` | Blender headless | 2-5 min/场景 | 1 | ⚠️ 视场景而定 |
| `pixel-render` | pixel-art skill | 30s-2 min | 1 | ❌ 否 |
| `ffmpeg` | ffmpeg | <30s | 3 | ❌ 否 |

**执行顺序**: 按 priority 分组, 同 priority 串行 (避免 VRAM 争抢), 不同 priority 按序执行。

## 日间其他 skill 的集成点

其他 wuhoo-game-dev skill 需要在执行前加判断：

```
if task_needs_gpu() and gpu_node_is_offline():
    enqueue_to_gpu_batch(task)
    task.status = "queued_for_gpu"
    return  # 不阻塞, 等凌晨批处理
```

影响范围: music-from-task (HeartMuLa), sprite-from-task (pixel render), daily-build (Unity build)。后续逐个 patch。

## Pitfalls

1. 队列重复入队 — 同一 task_id + pending → 跳过
2. SSH 超时 — GPU 节点未唤醒 → 重试 12 次 × 10s, 仍失败则跳过所有 GPU 任务
3. HeartMuLa OOM — 其他进程占 VRAM → HeartMuLa 优先跑, 独占 GPU
4. Unity license 过期 — 构建静默失败 → Step 1 先验证: `ssh admin@$GPU_HOST "ls 'C:/ProgramData/Unity/' "`
5. scp 大文件超时 — 产物 > 100MB → 分片或 rsync
6. 忘记关机 — 脚本 crash → `trap 'ssh admin@$GPU_HOST "sudo shutdown -h +5"' EXIT`

## Verification

- [ ] gpu-queue.json 格式正确
- [ ] SSH 可达, GPU 可见 (`nvidia-smi`)
- [ ] 每种 pending task type 至少执行了一个
- [ ] 产物已回传且文件非空
- [ ] GPU 节点已关机
- [ ] WeChat 通知已送达
