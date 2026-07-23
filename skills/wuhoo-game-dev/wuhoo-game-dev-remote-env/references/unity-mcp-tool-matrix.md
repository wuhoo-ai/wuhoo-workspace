# Unity MCP (CoplayDev) 工具矩阵 — W4 spike 实测 (2026-07-18)

47 工具全清单 + v1.1 工作流映射。实测环境: mcpforunityserver 3.4.4 (FastMCP), MCPForUnity 10.1.0, Unity 6000.5.4f1, stdio over SSH。

## v1.1 工作流 → 工具映射（核心速查）

| 工作流 | 首选工具 | 备注/实测 |
|---|---|---|
| 场景 CRUD/层级查询 | `manage_scene` | get_hierarchy / get_active / get_build_settings 为只读 |
| 创建/改 GameObject | `manage_gameobject` + `manage_components` | create/modify/delete/duplicate/move_relative |
| 查找对象 | `find_gameobjects` | 按 name/tag/layer/component/path，返回 instance ID |
| **批量操作** | `batch_execute` | 多命令一次往返，场景组装必用（官方强烈推荐） |
| 跑测试 | `run_tests` → `get_test_job` | **异步 job 模式**；EditMode 136 tests 实测 2.5s；editor 无需焦点 |
| 触发编译/刷新 | `refresh_unity` | ⚠️ 只做 asset refresh；**manifest 变更后不会自动 resolve 包** → 用 `execute_code` 跑 `UnityEditor.PackageManager.Client.Resolve()` |
| 任意编辑器 C# | `execute_code` | 必带 `action:"execute"`；方法体语义，需 `return` |
| 控制台日志 | `read_console` | types 过滤 error/warning，分页 |
| 相机/截图 | `manage_camera`（Cinemachine 感知）+ `execute_code` 截图 | 无专用截图工具 |
| 构建 | `manage_build` | 触发 player build、切平台、管理 build scenes（可替代部分 GameCI 迭代） |
| 3D 建模 (T014 方案B) | `manage_probuilder` | 需 com.unity.probuilder 包（当前未装，用时 `manage_packages` install） |
| FBX 导入 (T014 方案A) | `import_model_file` | 本地 Blender 导出的 FBX/OBJ/glTF 直接导入 |
| 包管理 | `manage_packages` | query/install/remove/registry 配置 |
| C# 脚本编辑 | `script_apply_edits` > `apply_text_edits` > `create_script`/`validate_script` | 结构化编辑更安全；get_sha 校验 |
| 材质/纹理/光照 | `manage_material` / `manage_texture` / `manage_graphics` | graphics 管 volume/后处理/烘焙 |
| 动画 | `manage_animation` | animator_* 前缀控制 + AnimationClip 创建 |
| Prefab | `manage_prefabs` | create_from_gameobject 可把场景组装物固化 |
| UI Toolkit | `manage_ui` | 仅 UXML/USS；**uGUI Canvas 仍走 manage_gameobject/execute_code** |
| VFX/粒子 | `manage_vfx` | ParticleSystem/LineRenderer/TrailRenderer |
| 物理 | `manage_physics` | 碰撞矩阵/材质/查询/验证 |
| 性能 | `manage_profiler` | Profiler 会话 + 内存快照 + Frame Debugger |
| API 求证 | `unity_reflect` / `unity_docs` | 写 execute_code 前先 reflect 验证 API 存在 |
| AI 资产生成 | `generate_image` / `generate_audio` / `generate_model` / `import_model` | 需自带 fal.ai/Tripo/Meshy/Sketchfab key（未配置，暂不用） |
| 编辑器状态 | `manage_editor` | play/pause 控制 + 状态查询（PlayMode 验收入口） |
| 菜单项 | `execute_menu_item` | 按菜单路径执行 |
| 工具组开关 | `manage_tools` | list_groups；当前启用组: animation, asset_gen, core, docs, probuilder, profiling, scripting_ext, testing, ui, vfx |
| 多实例 | `set_active_instance` | 多开 Unity 时选择目标 |
| 资产操作 | `manage_asset` | import/create/modify/delete |
| ScriptableObject | `manage_scriptable_object` | SerializedObject 属性路径 |
| Shader | `manage_shader` | CRUD |
| 会话诊断 | `debug_request_context` | client/session id |

## 实测 pitfalls（v1.1 W1-W3 踩坑）

1. **`refresh_unity` ≠ 包解析**: manifest.json 变更后 refresh 返回 idle 但 packages-lock 不更新。必须 `execute_code` 跑 `UnityEditor.PackageManager.Client.Resolve()`，~30-45s 后 lock 才落盘。
2. **run_tests 异步且不需要编辑器焦点**: `editor_is_focused: false` 也能跑完，彻底解决"后台不编译"依赖用户焦点的问题（配合 refresh_unity 触发编译）。
3. **手动调试脚本** `/tmp/unity_mcp_call.py` 已改为 CoplayDev uvx 命令（原官方 relay 版本作废）。注意: python3.6 无 `text=` 参数; Windows ssh stderr 是 GBK; **必须交互式读写**（先 initialize→读响应→再 initialized+call，一次性 communicate 写完关 stdin 会拿不到响应）。
4. **CI/编辑器包解析差异**（ugui 事故, 2026-07-18): 项目 uGUI 依赖从未在 manifest 显式声明，6000.0 CI 恰好隐式带上；升 6000.5 + manifest 变更触发全量重解析后 CI 剔除孤儿 ugui → 全部 UI 脚本 CS0234。**教训: 代码直接 using 的包必须显式进 manifest**（`com.unity.ugui: 2.5.0`）。编辑器侧因 lock 里有 depth-0 残留不报错，掩盖问题。
5. Windows 远端命令别用 `tail`/`grep` 等 Unix 工具（cmd 无此命令且管道会吞 git push 输出），用 `findstr` 或把过滤放到云端本地做。
