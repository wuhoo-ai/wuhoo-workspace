---
name: wuhoo-game-plan
description: "Use to decompose GDD into tasks. Planner role."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, planner, gdd, task-decomposition, dag]
    related_skills: [wuhoo-game-exec, wuhoo-game-review, wuhoo-game-arch, wuhoo-game-gates]
---

# wuhoo-game-plan — 规划者角色

> 合并自: gdd-to-tasks + software-development/game-dev。
> Planner 角色：GDD → 原子任务 → 依赖 DAG → 变更影响分析。

## 触发条件

- 用户说"规划 v1.x"或 /plan
- GDD 变更后需要重新拆分任务
- 需要评估功能完成度

## 1. GDD 三层结构

| 层 | 内容 | 粒度 | 性质 |
|----|------|------|------|
| **Layer A** | 接口/事件/命名/资源格式 | 接口级 | "法律"，改走变更流程 |
| **Layer B** | 行为 + 验收条件 | 验收级 | "合同"，导演改时更新 |
| **Layer C** | 实现建议 | 参考级 | "建议"，可不遵守 |

Layer A 在 `wuhoo-game-arch` skill 中维护。
Layer B 在 `Docs/GDD/*.md` 中维护（YAML frontmatter）。

## 2. GDD 条目格式

```yaml
---
id: combat-damage
title: 伤害结算
status: IMPLEMENTED  # TODO|IN_PROGRESS|IMPLEMENTED|VERIFIED|SHIPPED|CHANGED
priority: P0
depends_on: [weapon-system, enemy-hp]
blocks: [damage-popup, screen-shake]
---

## Spec (Layer B)

### 接口
见 Docs/Architecture/IDamageable.cs

### 行为
- Melee damage = weapon.baseDamage + upgrade.bonusDamage
- Critical: 10% chance, 2x multiplier

### 验收条件
- [ ] EditMode: TakeDamage(10) → HP == MaxHP - 10
- [ ] EditMode: IsDead when HP <= 0
- [ ] Scene: DamagePopup prefab in Resources/
- [ ] Runtime: Attack → enemy HP decreases → popup visible

### 已知 Pitfall
- Font 缓存 (P16)
- EditMode Awake 限制 (P04)
```

## 3. 任务分解规则

### 原子任务标准
- 预估 ≤ 2h
- 产出可独立验证（编译通过 + 测试通过）
- 有明确的 GDD 条目引用
- 有验收条件（从 GDD 继承）

### 任务卡片格式

```yaml
task_id: T042
gdd_ref: combat-damage
title: "实现 IDamageable + EnemyHP"
estimate: 1.5h
depends_on: [T038]
blocks: [T045]
acceptance:
  - "EditMode: TakeDamage reduces HP"
  - "EditMode: IsDead when HP <= 0"
  - "编译 0 错误 0 警告"
```

### 依赖 DAG
- depends_on 形成有向无环图
- 执行顺序 = 拓扑排序
- 无依赖的任务可并行（delegate_task 最多 3 并行）

## 4. GDD 变更管理

```
导演: "加连击系统"
  ↓
Step 1: 更新 GDD 条目状态 → CHANGED
Step 2: 影响分析（扫描引用代码 + 测试）
Step 3: 已有产物合规检查
Step 4: 生成增量任务卡片
Step 5: 执行 → 审查 → 验收
```

**规则**:
- 每次变更记录原因（导演原话）
- 变更后验收条件包含"已有功能不回归"
- 一个 sprint 内变更 ≤ 3 次（提醒）

## 5. 完成度报告

扫描 `Docs/GDD/*.md`，按状态统计:
```
TODO: 3 | IN_PROGRESS: 1 | IMPLEMENTED: 5 | VERIFIED: 2 | SHIPPED: 0
完成度: 7/11 (64%)
```

## 6. 人类决策点（Agent 不越界）

| 决策 | 人类 | Agent 不做 |
|------|------|-----------|
| 核心循环手感 | ✅ | 不调物理参数 |
| 美术风格 | ✅ | 不选最终资产 |
| 优先级排序 | ✅ | 不调 P0-P5 |
| 发布时机 | ✅ | 不自动 Release |
| 设计变更 | ✅ | 不扩展 GDD 范围 |
