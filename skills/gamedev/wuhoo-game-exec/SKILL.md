---
name: wuhoo-game-exec
description: "Use to implement a code task. Executor role."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, executor, code, unity, csharp, implementation]
    related_skills: [wuhoo-game-plan, wuhoo-game-review, wuhoo-game-arch, wuhoo-game-ci]
---

# wuhoo-game-exec — 执行者角色

> 合并自: code-from-task + unity-game-patterns。
> Executor 角色：任务卡片 → 代码 + 测试 + commit。

## 触发条件

- 用户说"执行 T042"或指定一个任务卡片
- delegate_task 分派的编码子任务

## 执行流程（强制）

```
1. 加载 wuhoo-game-arch（架构契约）
2. 读取任务卡片（GDD 引用 + 验收条件）
3. 编码（遵守契约）
4. 编写 EditMode 测试（遵守 P04 限制）
5. 本地验证（编译 + 测试）
6. 运行 pre-commit-lint.sh
7. 提交 + push
8. 触发 wuhoo-game-review（独立上下文审查）
```

## 编码规则（从架构契约继承）

### 系统注册
所有游戏系统必须实现 `IGameSystem` 并通过 `GameRoot.Register<T>()` 注册。

### 事件通信
系统间通信走 `GameEventBus.Publish/Subscribe`，不直接引用其他系统。

### 命名
- 系统: `{Name}System.cs` (e.g., CombatSystem.cs)
- 测试: `{Name}Tests.cs`
- 组件: `{Name}Component.cs`
- 事件: `{Name}Event` struct

### 资源路径
- 运行时加载: `Assets/Resources/{Category}/{name}`
- 精灵: 48x48 PNG, 调色板量化
- 音频: WAV 44.1kHz mono

### 禁止
- `FindObjectOfType` → 用 `FindAnyObjectByType`
- Editor 脚本中 lambda onClick → 用运行时 MonoBehaviour
- 未缓存的 `Font.CreateDynamicFontFromOSFont` → static cache
- 跨系统直接字段引用 → 用事件或接口

## EditMode 测试规则（P04）

```
✅ 可以测:
- 纯逻辑方法（计算、状态转换）
- 静态方法
- null 安全（传 null 不崩溃）
- 默认值
- 手动调用 Init() 后的行为

❌ 不能测:
- 依赖 Awake() 初始化的字段
- 协程
- FixedUpdate 更新的物理状态
- FindObjectOfType 结果
- DontDestroyOnLoad
```

## 常用 Unity 模式

### 存档/读档
```csharp
public static void Save(string key, object data) {
    PlayerPrefs.SetString(key, JsonUtility.ToJson(data));
    PlayerPrefs.Save();
}
public static T Load<T>(string key) where T : new() {
    string json = PlayerPrefs.GetString(key, "");
    return string.IsNullOrEmpty(json) ? new T() : JsonUtility.FromJson<T>(json);
}
```

### 对象池
```csharp
private Queue<GameObject> _pool = new();
public GameObject Get() {
    if (_pool.Count > 0) { var obj = _pool.Dequeue(); obj.SetActive(true); return obj; }
    return Object.Instantiate(_prefab);
}
public void Return(GameObject obj) { obj.SetActive(false); _pool.Enqueue(obj); }
```

### Lazy Discovery（GameRoot 系统引用场景对象）
```csharp
private Volume _volume;
void Update() {
    if (_volume == null) {
        _volume = FindAnyObjectByType<Volume>();
        if (_volume == null) return;
    }
    // 正常逻辑
}
```

## 提交规范

```
feat(T042): implement IDamageable + EnemyHP
fix(T038): weapon damage calculation
test(T042): add EditMode tests for damage system
```
