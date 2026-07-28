---
name: wuhoo-game-arch
description: "Use before any code task. Architecture contract."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, architecture, contract, interface, naming]
    related_skills: [wuhoo-game-exec, wuhoo-game-review, wuhoo-game-plan]
---

# wuhoo-game-arch — 架构契约 (Layer A)

> 所有任务执行前**强制加载**的约束。这是"法律"，不是"建议"。
> 对应仓库 `Docs/Architecture/` 目录和 `Assets/Scripts/Interfaces/`。

## 1. 系统注册

所有游戏系统必须实现 `IGameSystem`：
```csharp
public interface IGameSystem {
    void Init(GameRoot root);
    void Tick(float dt);
    void Reset();
}
```
通过 `GameRoot.Register<T>()` 注册。不允许系统自行 FindObjectOfType 获取其他系统。

## 2. 事件总线

系统间通信走 `GameEventBus`：
```csharp
// 发布
GameEventBus.Publish(new DamageEvent { Target = enemy, Amount = 10, Type = DamageType.Melee });

// 订阅
GameEventBus.Subscribe<DamageEvent>(e => { /* 处理 */ });
```

### 已定义事件
| 事件 | 字段 | 发布者 | 订阅者 |
|------|------|--------|--------|
| DamageEvent | Target, Amount, Type, Source | WeaponSystem | EnemyHP, DamagePopup, ScreenShake |
| DeathEvent | Entity, Killer | EnemyHP | WaveManager, AchievementSystem |
| MineEvent | OreType, Amount, Position | MiningSystem | InventorySystem, ParticleEffects |
| BuildEvent | BuildingType, Position | BuildSystem | SceneKit |
| DayNightEvent | Phase, Time | DayNightCycle | WaveManager, DayNightPostProcess |

## 3. 核心接口

```csharp
// IDamageable.cs
public interface IDamageable {
    int CurrentHP { get; }
    int MaxHP { get; }
    bool IsDead { get; }
    void TakeDamage(int amount, DamageType type, Vector2 source);
}

// IInteractable.cs
public interface IInteractable {
    string InteractPrompt { get; }
    void Interact(PlayerController player);
}

// ISaveable.cs
public interface ISaveable {
    string SaveKey { get; }
    object GetSaveData();
    void LoadSaveData(object data);
}
```

## 4. 命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 系统 | `{Name}System.cs` | CombatSystem.cs |
| 组件 | `{Name}Component.cs` | EnemyHPComponent.cs |
| 测试 | `{Name}Tests.cs` | CombatSystemTests.cs |
| 事件 | `{Name}Event` | DamageEvent |
| 接口 | `I{Name}` | IDamageable |
| 枚举 | `{Name}Type` / `{Name}Level` | DamageType, DepthLevel |

## 5. 资源规范

| 类型 | 路径 | 格式 |
|------|------|------|
| 运行时加载 | `Assets/Resources/{Category}/{name}` | — |
| 精灵 | `Assets/Art/Sprites/{Category}/` | 48x48 PNG, 32色调色板 |
| 音频 | `Assets/Resources/Audio/{BGM\|SFX}/` | WAV 44.1kHz mono |
| 场景 | `Assets/Scenes/{Name}.unity` | — |
| 字体 | `Resources.GetBuiltinResource<Font>("Arial.ttf")` | batchmode 唯一 |

## 6. 禁止清单

| 禁止 | 替代 | 原因 |
|------|------|------|
| `FindObjectOfType<T>()` | `FindAnyObjectByType<T>()` | Unity 6 CS0618 |
| Editor 脚本 lambda onClick | 运行时 MonoBehaviour Awake() | 不序列化 (P17) |
| 未缓存 Font.Create | `static Font _cached` | 内存泄漏 (P16) |
| 跨系统直接字段引用 | 事件总线 / 接口 | 耦合 |
| `Assets/Audio/` 运行时加载 | `Assets/Resources/Audio/` | Resources.Load 限制 (P10) |
| 手动 new 系统实例 | GameRoot.Register<T>() | 生命周期管理 |

## 7. 架构守护测试

`Assets/Tests/Architecture/ArchitectureTests.cs`:
```csharp
[Test] public void AllSystemsImplementIGameSystem() { ... }
[Test] public void NoFindObjectOfTypeInScripts() { ... }
[Test] public void AllEventsAreStructs() { ... }
[Test] public void ResourcesPathsExist() { ... }
```

这些测试在 CI Gate 1 运行，违反架构规则 = CI 红。
