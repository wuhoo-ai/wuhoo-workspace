---
name: wuhoo-game-dev-code-from-task
description: "Use when you need to implement a single code task from tasks.json for a Unity URP game. Input: one task object with spec+params+output. Output: C# scripts written to the specified paths, Unity Test Framework tests, and a self-review report. Load wuhoo-game-dev-review-task after implementation for quality gate."
version: 1.1.0
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

### Step 2: 实现

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

### Step 3: 写测试

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

### Step 4: Self-Review

实现完成后做自检：

```
□ 编译通过 (0 errors)
□ 所有 output 路径的文件已创建/修改
□ 测试覆盖了 spec 中描述的核心行为
□ 无硬编码魔法数字 (用 params 传入或 const)
□ 处理了边界条件 (0值/空值/极限值)
□ 代码 ≤ 200 行 (如果超过, 考虑是否需要拆分)
```

### Step 5: 输出报告

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
5. EditMode 测试 [SerializeField] 陷阱: Unity Test Framework 运行时会重置所有 SerializeField 字段为 0/null。用 public Init() 方法显式注入依赖，Awake() 中 guard 防御性赋值。
6. 跨 asmdef 测试: 测试 asmdef 不能引用 Assembly-CSharp。创建独立的游戏逻辑 asmdef (如 MinersWatch.Game)，测试 asmdef 引用它。
7. PlayMode 在 headless CI 崩溃: GameCI Linux runner 无 Input System 运行时。核心逻辑放 EditMode 纯 C# 测试，PlayMode 仅本地验证用。
8. .meta 文件 GUID: 手动编辑后必须是 32 位 hex。损坏的 GUID 导致编译错误 "guid"。
9. 重复方法: CI 合并冲突常导致重复方法 (如 OnTriggerExit2D 出现两次)。提交前 grep 检查。
10. Destroy() in EditMode 崩溃: Unity Test Framework 中必须用 DestroyImmediate。用 #if UNITY_EDITOR 宏区分运行时和编辑器模式。

## Verification

- [ ] C# 脚本位于正确的 output 路径
- [ ] 测试位于 `Assets/Tests/EditMode/` 或 `Assets/Tests/PlayMode/`
- [ ] 所有测试在本地通过
- [ ] Self-Review 清单全部勾选
