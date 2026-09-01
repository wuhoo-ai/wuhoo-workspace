---
name: wuhoo-game-gates
description: "Use to check quality gates before delivery."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, quality, gates, verification, delivery]
    related_skills: [wuhoo-game-ci, wuhoo-game-scene, wuhoo-game-review, wuhoo-game-gpu]
---

# wuhoo-game-gates — 分层质量门

> 定义从编码到交付的 6 级验证。每级有明确的通过标准和失败后果。

## Gate 总览

| Gate | 名称 | 环境 | 触发 | 失败后果 |
|------|------|------|------|---------|
| 0 | 编译 | CI | 每次 push | 阻断 |
| 1 | 单元+架构测试 | CI | 每次 push | 阻断 |
| 2 | 场景完整性 | CI | 每次 push | **阻断** |
| 3 | 运行时冒烟 | GPU 节点 | 任务完成/交付前 | 阻断交付 |
| 4 | 视觉回归 | GPU 节点 | 手动/阶段完成 | 警告 |
| 5 | 导演验收 | 用户 | 阶段完成 | 决策 |

## Gate 0: 编译

- CS 编译 0 错误
- 0 警告（CS0618 等必须修复，不 suppress）
- 工具: `gh run view <id> --json jobs`

## Gate 1: 单元 + 架构测试

- EditMode 测试全绿
- 架构守护测试全绿（wuhoo-game-arch 第7节）
- 测试遵守 P04 限制（不依赖 Awake）
- 工具: CI Quality Gates job

## Gate 2: 场景完整性（阻断）

- `Tools/scene-integrity-check.py` 通过
- 所有 SceneKit 定义的 GameObject 在 .unity 中存在
- 关键组件已挂载
- 失败 = CI 红，不是警告
- 详见 wuhoo-game-scene

## Gate 3: 运行时冒烟（GPU 节点）

**PlayMode 冒烟测试清单**:
```
□ 启动 → 主菜单可见 → 新游戏 → Surface 加载
□ 摇杆可操作 → 角色移动
□ 攻击按钮 → 有伤害数字
□ 进入洞穴 → 挖矿 → 物品入包
□ 夜晚 → 敌人生成 → 炮塔射击
□ 返回菜单 → 继续游戏 → 进度恢复
□ Player.log 无 NRE / Exception
```

**执行方式**:
- GPU 节点 Unity Editor: `-batchmode -runTests -testPlatform PlayMode`
- 或 MCP 脚本化操作 + 截图
- 截图 3 张（主菜单/Surface/洞穴）附在交付消息里

## Gate 4: 视觉回归（远期）

- 固定场景截图 → 与基线 diff
- 检测 UI 布局变化、精灵缺失、颜色异常
- 当前: 手动对比截图
- 远期: 自动化 pixel diff

## Gate 5: 导演验收

**准入条件（Gate 5 前置）**:
```
□ Gate 0-3 全部通过
□ 截图 3 张已附
□ 变更摘要已写（改了什么、为什么）
□ 已知限制已列出
```

**导演只评价**:
- 玩法手感（跳跃/攻击/移动）
- 美术风格（一致性/氛围）
- 音频体验（BGM/SFX 匹配度）
- 优先级决策（下一步做什么）

**导演不需要做**:
- 检查编译是否通过
- 检查按钮是否存在
- 检查场景是否加载
- 抓 log 看 NRE

## 交付流程

```
任务完成
  → Gate 0-2 (CI 自动)
  → Gate 3 (GPU 节点 PlayMode)
  → 全过 → 发用户（附截图+摘要）
  → 不过 → agent 自己修，不发用户
```
