# Unity 官方参考工程调研与落地记录 (2026-08-20)

> 调研对象: github.com/Unity-Technologies (451 仓库, 按星数 Top50 筛选)
> 结论已与用户确认: 1)拉取UnityCsReference 2)竖排/动画时查源码 3)透光shader暂缓 4)执行skills适配 5)许可证红线
> 存档位置: wuhoo-workspace/docs/ (本文件) + docs/reference/unity-game-programming-patterns-ebook.pdf (11.8MB, Web Archive镜像)

## 一、UnityCsReference 解读

- 引擎/编辑器 C# 部分官方源码参考镜像, ~1.3万星, 88MB。
- master 跟踪最新 alpha (当前 6000.7.0a4); 有逐版本分支 6000.0~6000.7 / 2023.x / 2022.x。
  **guimei 用 6000.5.4f1 → 对齐分支 6000.5** (已 clone 到 GPU C:\ai\ref\UnityCsReference)。
- 结构: Runtime/ + Modules/ (159 模块) + Editor/ + External/ + Projects/。
- 许可证: **Unity Reference Only License — 只读, 禁止修改/分发/拷贝入项目, 不收PR**。当"API 文档的源码级字典"用, 不 copy 代码。
- 对 guimei 的命脉级用途:
  1. 竖排文字: Modules/TextCoreFontEngine + TextRendering + UI (UGUI/TMP 排版管线)
  2. 皮影部件动画: Modules/U2DRuntime + U2DEditor (2D Animation/Sprite Shape) + SpriteMask
  3. 透光渲染 (暂缓): SpriteMask + Graphics 仓库配合
  4. 探索地图: Modules/Tilemap + Grid + Physics2D
  5. 编辑器工具: Modules/AssetPipelineEditor + UIElementsEditor
  6. 疑难排查: 序列化/弃用API/Editor行为

## 二、Org 高星项目盘点 (分级)

### A 级: 直接进开发流程
| 仓库 | 星 | 要点 |
|------|-----|------|
| Graphics | ~3k | URP/HDRP 官方源码, 包可本地安装可改 (与UnityCsReference不同)。URP 2D Renderer + Light2D Freeform = 皮影打光主战场; Sprite-Lit-Default = 透光shader起点; 分支 {版本}/staging |
| 2d-extras | ~1.6k | 已停更只读, 内容并入 Package Manager 的 Tilemap Extras 包 (RuleTile等)。**已装 6.0.3** |
| 2d-techdemos | ~1k (MIT) | Palette Swap (昼夜/鬼节换皮)、Destructible (运行时改Tilemap) 可直接抄 |
| InputSystem | ~1.5k | 官方 Samples: UIvsGameInput (QTE/UI仲裁)、InGameHints、RebindingUI。Android触控受益 |
| game-programming-patterns-demo | ~1.7k | 官方电子书配套工程。三步傩仪=State Pattern; GameEventBus=Observer; QTE=Command; 对象池 |
| Unity-Technologies/skills | ~274 | 官方 AI agent skills (SKILL.md 格式, 与 Hermes 同构)。22个: unity-cli/package-management/ui-*/sprite-editor 等。**已 clone 评估, 改编方案见第四节** |

### B 级: 按需精读
- com.unity.toonshader ~1.6k: UTS3 卡通着色, 3D向不直接套, 分级阴影/轮廓线思路可参考
- uGUI ~1.6k: UI 源码, 与 UnityCsReference Modules/UI 同源
- UniversalRenderingExamples ~2.3k: URP 自定义 Renderer Feature 示例
- Addressables-Sample ~1.5k: 内容分包/Android AAB 时再看

### C 级: 不引入 (一句话原因)
- ml-agents 19.6k: RL, 单机叙事用不上 (除非未来 QTE 难度自适应)
- ECS/DOTS 全家桶 8.2k+1.6k+1k: 内容型 2D 不需要
- FPS 5.1k/BoatAttack 2.8k/BossRoom 2k/Megacity 1.2k: 3D 演示, BossRoom 架构可偶尔翻
- VisualEffectGraph-Samples 2.1k: 偏 3D/HDRP, 2D 用 ParticleSystem
- NavMesh 3.1k/AutoLOD 2k/VolumetricLighting 1.8k/PostProcessing 3.7k(归档): 3D向或已并入URP

## 三、执行记录 (2026-08-20)

已完成:
- [x] GPU C:\ai\ref\UnityCsReference: git clone --depth=1 --branch 6000.5 (github直连恢复, 08-07通道矩阵已过时)
- [x] guimei-codeup manifest.json 加 com.unity.2d.tilemap.extras 6.0.3, commit 0c62d82 push Codeup (pre-commit L1 门禁全过: GDD linter 71文档 0err + mark + dialogue)
- [x] 电子书入库: docs/reference/unity-game-programming-patterns-ebook.pdf (11.8MB, %PDF-1.7 完整, commit 4bbf465)
- [x] 新版电子书入库: docs/reference/design-patterns-solid-ebook.pdf (6.8MB, 2024 Unity6版, MD5 a6511f12 与NAS源一致, 2026-08-20)
- [x] Unity-Technologies/skills clone 到 /tmp/unity-tech-skills (22个 skill)
- [ ] 结论存档 (本文档) → commit push

暂缓: 透光 shader 相关 (Graphics 仓库深读, 用户暂缓)
待办:
- Unity 编辑器下次打开 guimei-codeup 时解析 tilemap.extras (当前编辑器进程在跑, 外部改 manifest 需重载)

## 四、Unity-Technologies/skills 适配评估 (待用户确认后落盘)

官方 22 个 agent skill, 与 guimei 相关分级:

**建议改编为 wuhoo-game-* 家族 (git托管 ~/wuhoo-workspace/skills/gamedev/):**
1. **wuhoo-unity-headless** (新) ← unity-cli + unity-package-management
   - 无头装包 Client API + 不 -quit 模式 (已实证: 官方 skill 明确不要手改 manifest)
   - Unity CLI: 装编辑器/建项目/跑构建/驱动运行中编辑器
   - 合并我们的 GPU 无头经验 (schtasks启动/TestRunnerApi/batchmode)
2. **wuhoo-sprite-pipeline** (新) ← sprite-editor (ISpriteEditorDataProvider)
   - 批量改 sprite 属性: 切割/PPU/九宫格/图集 — 皮影部件批处理刚需
3. **wuhoo-ui-ugui** (新) ← ui-ugui + optimize-text-mesh-pro
   - uGUI Canvas/RectTransform/布局规范 + TMP 字体预算
   - 预留竖排文字专项 (guimei 命脉, 结合 UnityCsReference TextCore 源码)

**收藏备用 (不改编, 记录入口):**
- urp-postprocessing (Volume 后处理, 探索/战斗氛围)
- validate-urp-render-graph-renderer-feature (自定义 render pass 时)
- optimize-audio (音频导入优化)
- ui-uitk / ui-imgui (编辑器工具 UI)
- shader-graph-create-custom-node (自定义节点)
- localization (含 CJK 字体支持)

**不引入:** ads/IAP/levelplay/multiplayer/vivox/optimize-web/physics-3d/navmesh/new-unity-project

## 五、许可证红线备忘 (已告知用户)

- UnityCsReference / 官方包: Unity Companion/Reference Only License, 只读参考
- 可放心抄: 2d-techdemos (MIT)、Tilemap Extras 包 (包内许可)、电子书/文档
- 改编官方 skills 为 Hermes skill: 属知识整理, 遵循各仓库 LICENSE (skills 仓库需确认, 内容为文档性质)
