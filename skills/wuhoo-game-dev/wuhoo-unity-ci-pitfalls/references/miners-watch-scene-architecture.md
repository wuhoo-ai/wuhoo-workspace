# 矿工守夜场景创作架构

## 两种场景构建机制

| 场景 | 构建方式 | 触发时机 | 自动化？ |
|------|---------|---------|---------|
| MainMenu | `MainMenuBuilder` (`IProcessSceneWithReport`) | 每次 Build 时 | ✅ 自动 |
| Surface | `SurfaceSceneAuthor` (`[MenuItem]`) | 手动菜单 | ❌ 手动 |
| ShallowCave | `CaveSceneAuthor` (`[MenuItem]`) | 手动菜单 | ❌ 手动 |
| MidCave | `CaveSceneAuthor` (`[MenuItem]`) | 手动菜单 | ❌ 手动 |
| DeepCave | `CaveSceneAuthor` (`[MenuItem]`) | 手动菜单 | ❌ 手动 |

## 核心问题

`SceneKit.cs` 是共享的 UI 构建工具箱，被所有 SceneAuthor 使用。当 SceneKit.cs 修改后（如添加 AttackButton、调整摇杆位置），MainMenu 会自动更新（Build 时回调），但 Surface/Caves 不会——它们是上次手动运行时的静态快照。

## 快速诊断流程

```bash
# 1. 场景最后创作时间
git log --oneline -1 -- Assets/Scenes/Surface.unity
git log --oneline -1 -- Assets/Scenes/ShallowCave.unity

# 2. SceneKit 最后修改时间
git log --oneline -- Assets/Editor/SceneAuthoring/SceneKit.cs

# 3. 如果 SceneKit 的修改在场景创作之后 → 场景过期

# 4. 验证特定组件是否存在
grep -c "ComponentName" Assets/Scenes/Surface.unity
```

## 正确的工作流

修改 SceneKit.cs 或任何 *SceneAuthor.cs 后：
1. Unity Editor → `Hermes → Author Surface Scene`
2. Unity Editor → `Hermes → Author Shallow Cave Scene`
3. Unity Editor → `Hermes → Author Mid Cave Scene`
4. Unity Editor → `Hermes → Author Deep Cave Scene`
5. `git add Assets/Scenes/*.unity && git commit -m "chore: re-author all scenes after SceneKit changes"`
6. `git push` → CI 自动构建

## 实战案例

2026-07-22: v1.2 提交了 AttackButton 到 SceneKit.BuildTouchControls，但场景未重创。
用户安装最新 APK 后报告"v1.1/v1.2 所有新功能都没生效"。
grep 确认 Surface.unity 中 AttackBtn 出现 0 次。
修复：重创所有场景 + 提交。
