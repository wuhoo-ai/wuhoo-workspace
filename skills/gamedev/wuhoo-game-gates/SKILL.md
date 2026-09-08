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
>
> 2026-09-03 路线升级(决策117-121): B' 大块铰链试点的动画验收复用复合帧差画像
> (`frame_diff.py` + `frame_profile.py`); battle v2.1/idle 执行卡冻结, 不设新交付门。
> 2026-09-08 决策122: 验收指标改整图口径——**去切块完整性检查**(asset_check 只查整图+头层元数据),
> 保留 frame_diff/frame_profile 复合帧差体系, 新增**表演参数达标+观感闸**(1帧试看+5秒视频, 导演裁决)。

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

## 整图表演试点验收（2026-09-08 决策122 起）

- 资产门: `asset_check.py` 只查整图母版+头层的元数据(命名/尺寸/alpha/透明底)——**不再查切块完整性/连通域件数/连接孔**(分件生产已废止; 部件质量门 --quality-gate 仅历史批次)。
- 表演门(新增): puppet.json performance 字段齐全(channels/layers/emotions)且可被整图表演器解释; 头层枢轴合理。
- 动画门: `frame_diff.py` + `frame_profile.py` 复合判定（loop_gap < 0.3、std ≥ 0.35、停息占比 15–25%）——frame_diff 体系保留不变。
- 观感闸(视觉闸1/2): 渲 1 帧试看 → 渲 5 秒短视频 → 用户裁决(导演门), 不要求用户逐帧排查。

〔历史〕B' 大块铰链试点验收(2026-09-03): 资产门查 10-14 主身大块/垂直度/接缝遮挡/覆盖层——随决策122 废止。

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
