---
name: wuhoo-game-dev-gpu-batch
description: "⚠️ FUTURE — GPU node not yet set up. This skill defines the deferred-work lifecycle for GPU-intensive tasks (HeartMuLa music generation) that should run during off-peak hours. Not used in current demo phase — all current tasks (code/pixel-art/SFX/build) execute immediately without GPU. Load for reference only until GPU hardware is provisioned."
version: 3.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, gpu, batch, off-peak, heartmula, future]
    related_skills: [wuhoo-game-dev-music-from-task, heartmula, cronjob]
---

# Wuhoo Batch Queue — 峰谷编排

> ⚠️ **状态: FUTURE — GPU 节点尚未搭建。当前 Demo 阶段不使用此 skill。**

一个 skill，统一管理需要延迟到低谷时段执行的 **GPU 密集型任务**（仅 HeartMuLa 音乐生成）。

当前 Demo 阶段所有任务直接执行，不经过此 queue：
- Code 任务: Hermes 直接写 C# → 无需 GPU
- Pixel-art: pixel-art skill → 无需 GPU
- SFX: numpy 程序化 → 无需 GPU
- BGM: 免费在线资源占位 → 无需 GPU
- Build: GameCI GitHub Actions → 无需本地 GPU

等 GPU 节点 (RTX 4070 Ti 12GB) 搭建后，HeartMuLa BGM 生成可走此 pipeline。

## 峰谷时间定义

```
北京时间 (CST, UTC+8):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  高峰 (不跑重任务):
    白天  09:00 — 18:00
    合计  9 小时 — 你在线交互, 只做设计/Review/轻量

  低谷 (批量执行窗口):
    夜间+凌晨  18:00 — 09:00
    合计  15 小时

  GPU 节点通电窗口: 02:00 — 05:00 (3h, 在低谷内)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 任务类型 (简化 — 仅 HeartMuLa)

| type | 触发条件 | 执行引擎 | 需 GPU? |
|------|---------|---------|:------:|
| `heartmula` | music-from-task BGM 生成 (HeartMuLa 路径) | HeartMuLa 3B (本地 GPU) | ✅ |

以下类型已移除此 skill（当前直接执行，不延迟）:
- ~~code-heavy~~ → Hermes 直接写 C#，不通过 delegate_task
- ~~blender~~ → Unity ProBuilder 替代
- ~~unity-build~~ → GameCI GitHub Actions
- ~~pixel-render~~ → pixel-art skill 直跑
- ~~balance-sim~~ → Python 轻量脚本直跑
- ~~ffmpeg~~ → 轻量后处理直跑

## 入队策略

```python
def should_defer(task_type):
    now = datetime.now(tz=timezone('Asia/Shanghai'))
    hour = now.hour
    is_peak = (9 <= hour < 18)

    if not is_peak:
        return False  # 低谷, 直接跑

    if task_type == 'heartmula':
        return True  # HeartMuLa 入队, 等低谷 GPU

    return False  # 其他任务 — 当前阶段不经过此 queue
```

## 队列文件 (未来启用)

```json
{
  "queue_id": "2026-XX-XX-batch-01",
  "node": {
    "host": "192.168.x.x",
    "user": "admin",
    "gpu": "RTX 4070 Ti 12GB",
    "wol_mac": "aa:bb:cc:dd:ee:ff",
    "power_window": "02:00-05:00 CST"
  },
  "tasks": [
    {
      "id": "T018_music_bgm_day",
      "type": "heartmula",
      "status": "pending",
      "spec": "BGM 白天探索 70BPM",
      "params": {
        "tags": "adventure,orchestral,70bpm,hopeful,major-key",
        "duration_sec": 120
      },
      "output": "Assets/Audio/BGM/bgm_day.mp3"
    }
  ]
}
```

## 批量执行流程 (未来)

```
CST 02:00 — cron 触发
  ├─ 02:00  读取队列, 排序
  ├─ 02:00  GPU 节点 WoL 开机, 等待就绪 (~2min)
  ├─ 02:05  HeartMuLa 生成 (串行, 避免 VRAM 争抢)
  │         每首 ~2-4min, 3 首 BGM ≈ 10min
  ├─ 02:20  scp 产物回传 + git push
  ├─ 02:25  GPU 节点关机
  ├─ 02:30  队列清理 + 归档
  └─ 02:30  WeChat 通知
```

## GPU 节点搭建清单

待办 (等硬件就绪):

1. **硬件**: NVIDIA GPU (RTX 4070 Ti 12GB 或 RTX 3060 12GB)
2. **OS**: Linux (Ubuntu 22.04+)
3. **HeartMuLa 安装**:
   ```bash
   git clone https://github.com/nous-research/heartlib
   cd heartlib && python3.10 -m venv .venv && source .venv/bin/activate
   pip install -e .
   # 下载 3B checkpoint (~5GB)
   ```
4. **WoL 配置**: 主板 BIOS 开启 Wake-on-LAN，记录 MAC 地址
5. **Hermes cron**: 创建凌晨 02:00 CST 的 cron job

## HeartMuLa 硬件要求

| GPU | 能跑吗 | 配置 |
|-----|--------|------|
| RTX 4070 Ti (12GB) | ✅ | `--version 3B --lazy_load true` (~6.2GB) |
| RTX 3060 (12GB) | ✅ | 同上 |
| RTX 4060 (8GB) | ⚠️ | 3B 勉强, 关闭其他程序 |
| 无 GPU | ❌ | 走云端备用 Suno/Udio |

## Pitfalls

1. GPU 节点不存在时不要引用此 skill
2. HeartMuLa --lazy_load 拼写 — 是 `lazy_load` 不是 `lazy-load`
3. HeartCodec 用 fp32 — 不要用 bf16, 会劣化音质
4. RTX 5080 已知不兼容 — 上游 issue 跟踪中

## Verification (未来)

- [ ] GPU 节点已搭建并可通过 SSH 访问
- [ ] HeartMuLa 3B 可正常生成 120s 音频
- [ ] WoL 开机 + SSH 等待就绪 ≤ 5min
- [ ] 凌晨 cron 按流程执行
- [ ] WeChat 通知包含成功/失败统计
