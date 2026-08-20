---
name: wuhoo-unity-reference
description: "Use when querying UnityCsReference for API internals. 版本对齐+模块地图+查询流程+许可证红线。"
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, unity, reference, source, api]
    related_skills: [wuhoo-game-arch, wuhoo-game-debug, wuhoo-ui-ugui]
---

# wuhoo-unity-reference — UnityCsReference 查询方法论

> 2026-08-20 建立。调研结论存档: wuhoo-workspace/docs/unity-reference-research-2026-08-20.md

## 触发条件

- 需要查 Unity 引擎/编辑器 API 的实现细节、行为边界、序列化规则
- 文档没说清/行为不符合预期时(竖排文字排版、Sprite Swap、遮罩、Editor API)
- 排查 CS0618 弃用、Editor 与运行时行为差异

## 仓库位置

| 位置 | 路径 | 说明 |
|------|------|------|
| 云端 (Hermes) | ~/unity-csref | 6000.5 分支 --depth=1, search_files 直接查 |
| GPU 节点 | C:\ai\ref\UnityCsReference | 6000.5 分支, 75MB |

- 版本对齐: master = 最新 alpha(现在是 6000.7.0a4), **禁止当正式版行为看**。
- 项目用 6000.5.4f1 → 只看 6000.5 分支(HEAD = 6000.5.9f1 源码)。
- 更新: `git -C ~/unity-csref pull`(深度1, 快)。

## 模块地图(guimei 业务映射)

| 需求 | Modules/ 下的模块 | 说明 |
|------|------------------|------|
| 竖排文字/排版 | TextCoreFontEngine, TextCoreTextEngine, TextRendering, UI | UGUI/TMP 排版管线 |
| 皮影部件动画 | U2DRuntime, U2DEditor, SpriteMask, SpriteMaskEditor | 2D Animation/Sprite Shape/Sprite Swap |
| 探索地图 | Tilemap, TilemapEditor, Grid, Physics2D | 瓦片地图/碰撞 |
| 透光渲染(暂缓) | SpriteMask + Graphics 仓库 URP 2D 光照 | 配合 Graphics 仓库 |
| 编辑器工具 | AssetPipelineEditor, UIElementsEditor, UIBuilder | 资产卡批量工具 |
| 输入 | Input, InputForUI, InputLegacy | 触控/QTE |
| 动画 | Animation, AnimationWindow | 状态机/补间 |

## 查询流程

1. 先官方文档(最快, 覆盖 80% 场景)
2. 再本地源码: `search_files(pattern, path=~/unity-csref/Modules/<模块>)`
3. 看 ScriptBindings(API 绑定) + Managed(托管实现) 两部分
4. Editor 行为问题看 Editor/ 目录对应模块
5. 结论要对照 6000.5 分支, 不要引 master 内容当版本事实

## 许可证红线(必须遵守)

- Unity Reference Only License: **只读参考, 禁止修改/分发/拷贝代码进项目**
- 看实现、抄思路、自己重写; 绝不 copy-paste
- 想改引擎源码需 Unity 商业源码授权

## 常见姿势

- 查某 API 真实行为: 找到对应模块 → 搜类名 → 读实现
- 查属性是否序列化: 搜 SerializeField / Serialize 相关标记
- 查 Editor 菜单/窗口: 找 Editor/ 下同名模块
- 对比版本差异: 需要时临时 `git fetch origin 6000.6` 后 diff(深度1 需先 unshallow, 慎用)
