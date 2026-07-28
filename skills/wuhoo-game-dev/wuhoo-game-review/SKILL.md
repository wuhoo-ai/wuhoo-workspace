---
name: wuhoo-game-review
description: "Use after task completion. Reviewer role."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, reviewer, quality, code-review, acceptance]
    related_skills: [wuhoo-game-exec, wuhoo-game-plan, wuhoo-game-gates, wuhoo-game-ci]
---

# wuhoo-game-review — 审查者角色

> 改写自: review-task。
> Reviewer 角色：独立上下文审查 diff vs GDD 验收条件。

## 触发条件

- 执行者完成一个任务后（任务粒度，非每次 commit）
- 用户要求审查

## 核心原则

**审查者必须独立上下文。** 看不到执行过程中的妥协和变通，只看：
1. 最终 diff（git diff）
2. GDD 条目的验收条件
3. 架构契约（wuhoo-game-arch）

## 审查清单

### A. 架构合规（对照 wuhoo-game-arch）
- [ ] 新系统实现 IGameSystem 接口
- [ ] 系统间通信走 GameEventBus
- [ ] 命名符合规范（{Name}System.cs 等）
- [ ] 资源在 Assets/Resources/ 下
- [ ] 无 FindObjectOfType（用 FindAnyObjectByType）
- [ ] 无 lambda onClick 在 Editor 脚本中

### B. 验收条件（对照 GDD 条目）
- [ ] 所有 acceptance 条目有对应测试
- [ ] 测试通过（EditMode 全绿）
- [ ] 编译 0 错误 0 警告

### C. 场景完整性
- [ ] 如果修改了 SceneKit/SceneAuthor → 场景是否重新 Author？
- [ ] 新增的 GameObject 是否在 .unity 中存在？
- [ ] SerializedField 引用是否非 null？

### D. 资源完整性
- [ ] Resources.Load 路径存在
- [ ] asmdef 引用完整（新 using 有对应 assembly）
- [ ] 无重复资源

### E. 测试质量
- [ ] 测试不依赖 Awake()（P04）
- [ ] 测试不依赖 FixedUpdate 状态（P25）
- [ ] 测试中跨系统引用已初始化（P26）
- [ ] 无 Dictionary 遍历中修改（P24）

### F. 回归检查
- [ ] 已有测试仍然通过
- [ ] 已有功能不受影响（对照 GDD 其他条目）

## 审查输出格式

```yaml
review:
  task_id: T042
  gdd_ref: combat-damage
  verdict: PASS | FAIL | CONDITIONAL
  issues:
    - severity: blocker | major | minor
      file: CombatSystem.cs
      line: 42
      description: "TakeDamage 未检查 IsDead"
      gdd_violation: "acceptance #2"
  notes: "整体实现符合契约，测试覆盖充分"
```

## Hermes 实现

审查通过 `delegate_task` 起独立子 agent：
```
goal: "审查 commit {sha} 的 diff，对照以下验收条件: {acceptance_list}。
       加载 wuhoo-game-arch 检查架构合规。
       输出 YAML 格式审查报告。"
context: "仓库路径: /home/admin/miners-watch, 分支: v1.1-dev"
```

子 agent 看不到执行过程，只看到 diff + 验收条件。
