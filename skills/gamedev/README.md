# wuhoo-game-dev Skill 索引

> 17 个 skill，统一 wuhoo-game-* 命名。2026-07-28 整合完成，2026-08-03 新增 voice，2026-08-20 新增 Unity 参考工程系列 4 个。

## 生产流程（从上到下）

| # | Skill | 职责 | 触发 |
|---|-------|------|------|
| 1 | `wuhoo-game-arch` | 架构契约 (接口/事件/命名/资源) | 任何代码任务前 |
| 2 | `wuhoo-game-gates` | 质量门 (Gate 0-5 + 导演准入) | 交付前 |
| 3 | `wuhoo-game-plan` | 规划 (GDD→任务→DAG→变更) | /plan 或 "规划" |
| 4 | `wuhoo-game-exec` | 执行 (任务→代码→测试) | "执行 T0xx" |
| 5 | `wuhoo-game-review` | 审查 (diff→验收，独立上下文) | 任务完成后 |
| 6 | `wuhoo-game-art` | 美术 (style guide→生图→后处理) | 需要精灵/贴图 |
| 7 | `wuhoo-game-audio` | 音频 (prompt→生成→标准化) | 需要 BGM/SFX |
| 8 | `wuhoo-game-voice` | 配音 (qwen-audio-3.0-tts 对白/旁白) | 需要角色配音 |
| 9 | `wuhoo-game-scene` | 场景 (Author→新鲜度→完整性) | 改了 SceneKit |
| 10 | `wuhoo-game-ci` | CI/CD (构建+27 pitfall+lint) | CI 红了 |
| 11 | `wuhoo-game-debug` | 调试 (症状→决策树→定位) | 崩溃/运行时 bug |
| 12 | `wuhoo-game-gpu` | GPU (健康检查+MCP+远程环境) | GPU 节点操作 |
| 13 | `wuhoo-game-balance` | 数值 (Monte Carlo 平衡验证) | 调数值后 |
| 14 | `wuhoo-unity-reference` | UnityCsReference 查询 (版本对齐/模块地图) | 查 API 实现/行为 |
| 15 | `wuhoo-unity-headless` | 无头操作 (Client API 装包/batchmode) | 无头/CI 装包构建 |
| 16 | `wuhoo-sprite-pipeline` | 精灵批量处理 (ISpriteEditorDataProvider) | 批量切割/锚点/部件 |
| 17 | `wuhoo-ui-ugui` | uGUI/TMP UI 规范 (含竖排文字专项) | 搭/修 UI、字体 |

## 合并来源

| 新 Skill | 合并自 |
|----------|--------|
| wuhoo-game-ci | daily-build + unity-ci-pitfalls + unity-ci-diagnosis + unity-ci-ui-builder |
| wuhoo-game-debug | unity-crash-bisection + player-crashes + debug-player-crash |
| wuhoo-game-gpu | gpu-ops + remote-env + gpu-batch |
| wuhoo-game-plan | gdd-to-tasks + software-development/game-dev |
| wuhoo-game-exec | code-from-task + unity-game-patterns |
| wuhoo-game-review | review-task (改写) |
| wuhoo-game-art | sprite-from-task (改写) |
| wuhoo-game-audio | music-from-task (改写) |
| wuhoo-game-voice | 新建 (2026-08-03, qwen-audio-3.0-tts) |
| wuhoo-game-balance | balance-validate (改名) |
| wuhoo-game-arch | 新建 |
| wuhoo-game-gates | 新建 |
| wuhoo-game-scene | 新建 |
| wuhoo-unity-reference | 新建 (2026-08-20, UnityCsReference 查询方法论) |
| wuhoo-unity-headless | 改编 Unity-Technologies/skills unity-cli + unity-package-management |
| wuhoo-sprite-pipeline | 改编 Unity-Technologies/skills sprite-editor |
| wuhoo-ui-ugui | 改编 Unity-Technologies/skills ui-ugui + optimize-text-mesh-pro |

## 规则

- canonical 位置: `wuhoo-workspace/skills/gamedev/`（Hermes external_dirs 直接加载，不在 ~/.hermes/skills 建 wuhoo skill）
- 发布仓库: `~/wuhoo-skills`（git@github.com:wuhoo-ai/wuhoo-skills.git）— workspace 改动后整体 sync 提交推送
- wuhoo-workspace/skills 只通过 git 更新，**不手动 cp**
- 通用游戏方法论保留在 `gaming/game-development/`（非 wuhoo 专用）
