---
name: wuhoo-game-dev-gdd-to-tasks
description: "Use when you have a GDD.md and need to decompose it into atomic tasks ready for Agent dispatch. Reads game design document, analyzes dependencies, assigns Agent targets (code/art/audio/test), and outputs tasks.json. This is the orchestrator skill for the wuhoo-game-dev pipeline."
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, planning, gdd, task-decomposition, orchestrator]
    related_skills: [wuhoo-game-dev-code-from-task, wuhoo-game-dev-sprite-from-task, wuhoo-game-dev-music-from-task, wuhoo-game-dev-review-task, wuhoo-game-dev-balance-validate, wuhoo-game-dev-daily-build, plan]
---

# Wuhoo GDD → Tasks Orchestrator

读取 GDD.md → 分析系统/依赖 → 拆解原子任务 → 分配 Agent → 输出 tasks.json。

## When to Use

- 用户说：拆解这个 GDD、生成任务列表、分解成 task
- 用户说：为这个游戏生成开发计划
- 热身项目或正式项目的规划阶段
- tasks.json 过期需要重新生成

## Workflow

### Step 1: 读取 GDD

使用 `read_file` 读取 GDD.md。关注：
- Chapter 2: 核心 Loop (理解玩法流程)
- Chapter 3: 系统设计 (每个系统 = 一组 task)
- Chapter 4: 内容规格 (CSV/表格 → 数值 task)
- Chapter 5: 美术规格 (资产清单 → art task)
- Chapter 6: 技术规格 (引擎/管线 → infra task)

### Step 2: 生成任务列表

对每个系统做原子化拆解。一个 task 的粒度标准：
- 1 个文件 (或 2-3 个紧密耦合的文件)
- 1 个可验证的结果
- 1 种类型 (code / art / audio / test / infra)

### Step 3: 分析依赖

```
T003 采矿系统 → depends_on: T001 (项目初始化), T002 (玩家控制器)
T011 角色 sprite → depends_on: [] (独立, 无代码依赖)
T019 测试 → depends_on: T003, T004, T005 (依赖相关系统先完成)
```

### Step 4: 分配 Agent

| type | delegate_to | 说明 |
|------|------------|------|
| `code` | `coding-agent` | 通过 Claude Code harness 执行 |
| `art` | `pixel-art-agent` | 使用 pixel-art skill |
| `audio` | `music-agent` | 使用 songwriting/heartmula skill |
| `test` | `coding-agent` | 写 Unity Test Framework 用例 |
| `infra` | `coding-agent` | CI/CD 配置、Git 设置 |

### Step 5: 输出 tasks.json

格式：

```json
{
  "project": "矿工守夜",
  "engine": "Unity 6 + URP",
  "generated": "2026-07-13T00:00:00Z",
  "tasks": [
    {
      "id": "T001",
      "system": "基础设施",
      "type": "infra",
      "priority": "P0",
      "spec": "创建 Unity URP 项目, 配置 Git LFS, 初始化 GameCI workflow",
      "params": {},
      "output": [
        "Assets/",
        ".github/workflows/build.yml",
        ".gitattributes"
      ],
      "test": "GitHub Actions 首次构建成功",
      "depends_on": [],
      "delegate_to": "coding-agent"
    },
    {
      "id": "T003",
      "system": "采矿系统",
      "type": "code",
      "priority": "P0",
      "spec": "实现采矿: 玩家按下交互键 → 检测前方矿物碰撞体 → 播放采矿动画 → 消耗体力 → 矿物加入背包",
      "params": {
        "体力消耗": "按矿物硬度 1/2/5/10/20",
        "矿物价值": "石$5/铁$15/金$40/水晶$100/黑曜石$300"
      },
      "output": [
        "Scripts/Systems/MiningSystem.cs",
        "Scripts/Data/MineralData.cs"
      ],
      "test": "EditMode: 挖铁矿物体力减少 2, 背包增加 1 铁。PlayMode: 按 E 键对着铁矿 → 动画播放 → 体力条减少",
      "depends_on": ["T001", "T002"],
      "delegate_to": "coding-agent"
    }
  ]
}
```

### Step 6: 保存 + 展示摘要

保存到 `GDD 同级目录/tasks.json`。然后展示摘要：

```
生成 {N} 个任务:
  代码: {code_count} | 美术: {art_count} | 音频: {audio_count} | 测试: {test_count} | 基础设施: {infra_count}
  P0 (阻塞): {p0_count} | P1: {p1_count} | P2: {p2_count}
  关键路径: T001 → T002 → T003 → ...
```

## Priority 定义

| Priority | 含义 | 示例 |
|----------|------|------|
| P0 | 阻塞后续任务, 必须最先完成 | 项目初始化, 玩家控制器, 核心循环 |
| P1 | 独立可并行, 但影响可玩性 | UI, 音效, 存档 |
| P2 | 锦上添花, 可后期 | Boss 动画, 额外音效变体 |

## Pitfalls

1. 不要把 "实现整个战斗系统" 当成一个 task — 拆成移动/攻击/伤害/死亡 4 个
2. 依赖关系不要过度串联 — art task 通常无代码依赖, 可以并行
3. 不要忘记 test task — 每个核心系统至少 1 个 EditMode 测试
4. params 必须是数值 (字符串/数字), 不要放自然语言描述
5. 输出 tasks.json 前验证 JSON 有效性

## Verification

- [ ] tasks.json 是有效的 JSON
- [ ] 每个 task 都有 id, type, spec, output, test, depends_on, delegate_to
- [ ] 依赖图中没有循环引用
- [ ] P0 任务中至少有一个是完全独立的 (无 depends_on)
