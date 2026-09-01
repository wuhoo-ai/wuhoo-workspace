---
name: wuhoo-game-debug
description: "Use when Unity player crashes or runtime bugs."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, unity, debug, crash, bisection, autopilot]
    related_skills: [wuhoo-game-ci, wuhoo-game-gpu]
---

# wuhoo-game-debug — 调试决策树

> 合并自: unity-crash-bisection + wuhoo-game-dev-player-crashes + wuhoo-game-dev-debug-player-crash。
> 按**症状**分类的定位流程，不是 pitfall 列表（那是 wuhoo-game-ci 的事）。

## 触发条件

- Unity player 崩溃（Editor 正常）
- 运行时 NRE / 功能不工作
- Android 闪退
- 性能问题

## 决策树 1: Player 崩溃（Editor 正常）

```
Player 崩溃
├── 崩溃发生在哪个阶段？
│   ├── 启动时（splash 之前）
│   │   → 检查 PlayerSettings / IL2CPP 配置
│   │   → 检查 Android package name (P07)
│   │   → adb logcat 抓崩溃堆栈
│   │
│   ├── 场景加载时
│   │   → 序列化问题（见下方二分法）
│   │   → 检查 .unity 文件是否有残留引用
│   │   → 检查 ScriptableObject / enum 序列化
│   │
│   └── 游戏运行中
│       → 特定操作触发？→ 定位到具体系统
│       → 随机触发？→ 内存/线程问题
│       → adb logcat / Player.log 定位
```

## 决策树 2: 运行时功能不工作（不崩溃）

```
功能不工作
├── 所有新功能都不工作？
│   → 场景过期 (P01)！检查 SceneKit vs Scene 时间戳
│
├── 单个功能不工作？
│   ├── UI 按钮无反应
│   │   → 检查 EventSystem 存在
│   │   → 检查 Canvas 有 GraphicRaycaster
│   │   → 检查按钮 onClick 是否用 lambda（P17 不序列化）
│   │   → 检查 SerializedField 引用是否 null
│   │
│   ├── 伤害/数值不生效
│   │   → 检查系统初始化顺序（GameRoot Awake 竞态 P20）
│   │   → 检查跨系统 null 链 (P26)
│   │   → EditMode 测试是否覆盖了此路径
│   │
│   ├── 音频不播放
│   │   → Resources.Load 路径 (P10)
│   │   → AudioSource 组件存在？
│   │   → AudioClip 导入设置正确？
│   │
│   └── 视觉/粒子不显示
│       → asmdef 引用 (P05)
│       → Material/Shader 兼容性
│       → Sorting Layer / Order in Layer
│
└── CI 绿但运行时坏？
    → 100% 是场景过期 (P01) 或 Resources 路径 (P10)
```

## 决策树 3: 编译/CI 失败

→ 直接查 wuhoo-game-ci skill 的 Pitfall 库。

## 二分法定位（场景级崩溃）

当崩溃与场景相关但无法定位到具体组件时：

```
Step 1: 创建最小场景（只有 Camera + Light）→ 构建 → 测试
Step 2: 如果最小场景 OK → 逐个添加原场景组件
Step 3: 每次添加后构建测试 → 定位到具体组件
Step 4: 定位到组件后 → 检查其 SerializeField / enum / 引用
```

**AutoPilot 无头冒烟**（GPU 节点）:
```csharp
[MenuItem("Hermes/AutoPilot Smoke Test")]
static void RunSmokeTest() {
    // 加载每个 BuildSettings 场景 → 等待 60 帧 → 截图 → 检查 Debug.LogError
}
```

## 已知崩溃根因（历史案例）

| 根因 | 症状 | 修复 |
|------|------|------|
| 序列化枚举 | IL2CPP 崩溃，Editor 正常 | 避免在 MonoBehaviour 中序列化 enum 数组 |
| 动态字体 atlas | 大量 DamagePopup 后崩溃 | 缓存 Font (P16) |
| 场景 YAML 残留 | 删除组件后 .unity 仍有引用 | 重新 Author 场景 |
| DontDestroyOnLoad 重复 | 第二次进入场景崩溃 | guard `if (instance == null)` |

## 调试工具清单

| 工具 | 用途 | 环境 |
|------|------|------|
| `adb logcat` | Android 崩溃堆栈 | GPU 节点 + 模拟器/真机 |
| `Player.log` | Windows 运行时日志 | GPU 节点 |
| MCP 截图 | 视觉验证 | GPU 节点 Unity Editor |
| `gh run view --log-failed` | CI 编译错误 | 云端 |
| PlayMode 测试 | 运行时行为验证 | GPU 节点 |
