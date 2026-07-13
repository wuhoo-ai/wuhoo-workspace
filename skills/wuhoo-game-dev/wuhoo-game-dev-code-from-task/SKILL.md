---
name: wuhoo-game-dev-code-from-task
description: "Use when you need to implement a single code task from tasks.json for a Unity URP game. Input: one task object with spec+params+output. Output: C# scripts written to the specified paths, Unity Test Framework tests, and a self-review report. Load wuhoo-game-dev-review-task after implementation for quality gate."
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, code, unity, csharp, implementation]
    related_skills: [wuhoo-game-dev-gdd-to-tasks, wuhoo-game-dev-review-task, Claude Code]
---

# Wuhoo Code From Task

单个 code task → C# 脚本 + Unity Test Framework 测试 + Self-Review。

## When to Use

- 用户分配了 type=code 的 task
- 需要实现具体的 Unity C# 游戏逻辑
- 已有 Unity 项目骨架 (T001 完成)

## Workflow

### Step 1: 读取上下文

```
1. 从 tasks.json 读取当前 task 的 spec + params + output + test
2. 检查 depends_on: 依赖的 task 是否已完成?
3. 读取现有项目代码了解架构
```

### Step 2: 峰谷检查

```python
# 高峰时段 + 预估 token > 10K → 入队延迟到低谷执行
guard_result = peak_hour_guard(
    task_type='code-heavy',
    task_id=task['id'],
    task_context={'spec': task['spec'], 'params': task['params'], 'output': task['output']},
    estimated_tokens=estimate_tokens(task['spec'])
)
if guard_result == 'deferred':
    print(f'⏳ {task["id"]} 已入队, 凌晨低谷批量编码')
    return  # 不入队: 不执行, 等 off-peak batch
```

> 紧急覆盖: 用户说 "现在跑" / "--now" → 跳过 guard, 直接执行

### Step 3: 实现

确定：
- 要创建/修改哪些文件 (以 output 字段为准)
- 需要引入哪些 Unity 命名空间
- 是否涉及 MonoBehaviour / ScriptableObject / 纯 C# 类
- 如何与已有系统交互

### Step 3: 实现

遵循 Unity + wuhoo 编码规范：

```csharp
// 命名空间: Game.[系统名]
namespace Game.Mining
{
    // [RequireComponent] 声明依赖
    [RequireComponent(typeof(PlayerController))]
    public class MiningSystem : MonoBehaviour
    {
        // [SerializeField] 可配置参数, 对应 task.params
        [Header("体力消耗")]
        [SerializeField] private float stoneStamina = 1f;
        [SerializeField] private float ironStamina = 2f;
        [SerializeField] private float goldStamina = 5f;

        // 私有引用用 [SerializeField] 暴露在 Inspector
        [SerializeField] private InventorySystem inventory;

        // 公共 API
        public bool TryMine(MineralType type, out MineralData mineral)
        {
            // ...
        }
    }
}
```

编码规范：
- 类名 PascalCase, 方法名 PascalCase, 变量名 camelCase
- `[SerializeField]` 私有字段 (不用 public)
- 每个方法 ≤ 30 行
- 使用 `Debug.Assert` 做运行时检查
- ScriptableObject 用于数据定义 (矿物/武器/敌人属性)

### Step 4: 写测试

```csharp
// Assets/Tests/EditMode/MiningSystemTests.cs
using NUnit.Framework;
using Game.Mining;

public class MiningSystemTests
{
    [Test]
    public void TryMine_Iron_ConsumesTwoStamina()
    {
        var player = CreateTestPlayer(stamina: 100);
        var system = new MiningSystem();

        system.TryMine(MineralType.Iron, out var mineral);

        Assert.AreEqual(98, player.Stamina);
        Assert.AreEqual(MineralType.Iron, mineral.Type);
    }

    [Test]
    public void TryMine_NoStamina_ReturnsFalse()
    {
        var player = CreateTestPlayer(stamina: 0);

        var result = new MiningSystem().TryMine(MineralType.Stone, out _);

        Assert.IsFalse(result);
    }
}
```

测试规范：
- EditMode 测试纯逻辑 (不依赖场景/MonoBehaviour, 速度快)
- PlayMode 测试涉及场景/GameObject 的行为
- 一个测试一个断言意图 (可以用多个 Assert 但语义统一)
- 测试命名: MethodName_Scenario_ExpectedBehavior

### Step 5: Self-Review

实现完成后做自检：

```
□ 编译通过 (0 errors)
□ 所有 output 路径的文件已创建/修改
□ 测试覆盖了 spec 中描述的核心行为
□ 无硬编码魔法数字 (用 params 传入或 const)
□ 处理了边界条件 (0值/空值/极限值)
□ 代码 ≤ 200 行 (如果超过, 考虑是否需要拆分)
```

### Step 6: 输出报告

```markdown
## Task {id} 完成报告

**状态**: ✅ / ❌
**文件**: 
  - 创建: Scripts/Systems/MiningSystem.cs (85 lines)
  - 创建: Assets/Tests/EditMode/MiningSystemTests.cs (40 lines)
**测试**: 5/5 passed
**Self-Review**: ✅ 全部通过
**注意事项**: 体力系统依赖 PlayerController, 确保 T002 先完成
```

## 工具调用策略

优先使用 Hermes 原生工具：
- `write_file` — 创建新 C# 脚本
- `patch` — 修改已有脚本
- `terminal` — 运行 `dotnet test` 或 Unity Test Runner CLI

如果 Unity MCP 已安装，可以：
- 通过 MCP 创建 GameObject/Component
- 通过 MCP 运行 PlayMode 测试

## Pitfalls

1. MonoBehaviour 测试陷阱: EditMode 测试不能 `new GameObject()`, 用纯 C# 类测试逻辑
2. 忘记 `[System.Serializable]` — 需要序列化的数据类必须标记
3. URP 特定: 不要用 `Camera.main` (URP 中使用 `Camera.main` 仍有效但性能差), 考虑缓存引用
4. 坐标系统: URP 2D 使用像素坐标, 3D 使用世界坐标, 混合时要小心 Cinemachine 配置

## Verification

- [ ] C# 脚本位于正确的 output 路径
- [ ] 测试位于 `Assets/Tests/EditMode/` 或 `Assets/Tests/PlayMode/`
- [ ] 所有测试在本地通过
- [ ] Self-Review 清单全部勾选
