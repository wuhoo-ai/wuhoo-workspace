---
name: wuhoo-game-scene
description: "Use for scene authoring and integrity checks."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, scene, unity, authoring, integrity, yaml]
    related_skills: [wuhoo-game-ci, wuhoo-game-gpu, wuhoo-game-gates]
---

# wuhoo-game-scene — 场景管线

> 新建。解决矿工守夜最大痛点：场景过期导致功能消失。

## 触发条件

- 修改了 SceneKit.cs 或 *SceneAuthor.cs
- 场景完整性检查失败
- 需要重新 Author 场景

## 当前架构

```
MainMenu.unity     → MainMenuBuilder (IProcessSceneWithReport) → 自动 ✅
Surface.unity      → SurfaceSceneAuthor ([MenuItem])           → 手动 ❌
ShallowCave.unity  → CaveSceneAuthor ([MenuItem])              → 手动 ❌
MidCave.unity      → CaveSceneAuthor ([MenuItem])              → 手动 ❌
DeepCave.unity     → CaveSceneAuthor ([MenuItem])              → 手动 ❌
```

## 场景新鲜度规则

**任何修改 SceneKit.cs 或 *SceneAuthor.cs 的任务，最后一步必须是：**
1. GPU 节点重新 Author 所有受影响场景
2. Commit + push .unity 文件
3. CI 场景完整性检查通过

## 场景完整性检查 (Tools/scene-integrity-check.py)

解析 .unity YAML（纯文本），检查：
1. SceneKit 中 BuildXXX() 创建的所有 GameObject 名称是否存在
2. 关键组件是否挂载（PlayerController, TouchControls 等）
3. 关键 SerializedField 引用是否非 null

```python
# 伪代码
scene_yaml = open("Assets/Scenes/Surface.unity").read()
required_objects = extract_from_scenekit("SurfaceSceneAuthor.cs")
for obj_name in required_objects:
    assert obj_name in scene_yaml, f"MISSING: {obj_name}"
```

## CI 集成 (Gate 2)

```yaml
scene-integrity:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: python3 Tools/scene-integrity-check.py
```

失败 = 阻断 CI（不是警告）。

## 长期方案：迁移到 IProcessSceneWithReport

将 SurfaceSceneAuthor / CaveSceneAuthor 从 MenuItem 迁移到 IProcessSceneWithReport，
实现 CI 构建时自动 Author（像 MainMenuBuilder 一样）。

**前置验证**（GPU 节点）：
- 确认 CI docker 环境下 Editor 脚本可正常执行
- 确认 SerializedObject 绑定在 batchmode 下工作
- 确认幂等性（重复构建不重复创建）

## 场景 Author 操作手册（GPU 节点）

```bash
# 通过 MCP 执行
execute_menu_item "Hermes/Author Surface Scene"
execute_menu_item "Hermes/Author Shallow Cave Scene"
execute_menu_item "Hermes/Author Mid Cave Scene"
execute_menu_item "Hermes/Author Deep Cave Scene"

# 然后
git add Assets/Scenes/
git commit -m "scene: re-author all scenes after SceneKit update"
git push origin v1.1-dev
```
