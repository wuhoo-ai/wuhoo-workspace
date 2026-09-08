---
name: wuhoo-sprite-pipeline
description: "Use when batch-editing sprite metadata: slicing, pivot, border, atlas. 皮影部件批处理。"
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, unity, sprite, pipeline, importer, 2d]
    related_skills: [wuhoo-game-art, wuhoo-unity-headless, wuhoo-game-arch]
---

# wuhoo-sprite-pipeline — 精灵批量处理(ISpriteEditorDataProvider)

> 2026-08-20 建立。改编自 Unity-Technologies/skills 官方 sprite-editor skill,
> 面向 guimei 皮影部件管线(决策110: 部件集→AI拆分→装配 全链路)。
>
> 2026-09-03 路线升级(决策117): 皮影角色改为 B' 大块铰链——主身 10–14 大块 + 5–8 覆盖层,
> 不再批量处理 52 件细部件; pivot/切块按大块铰链点设置。
>
> **2026-09-08 决策122: 本技能降级为可选粗分层工具**——整图表演路线无批量切块/无部件批量 pivot;
> 仅当需要头层裁切/可选手臂粗层/表情头茬网格时才使用本技能的 importer 操作。

## 核心事实

- sprite 元数据(rect/border/pivot/outline)活在 **importer** 里(TextureImporter/PSBImporter),
  不是可手改的文件 → 必须通过 C# 驱动运行中的编辑器
- **绝不手改 .meta 文件**改 sprite 数据 — importer 拥有该数据, 手改即损坏
- 通道: 编辑器在跑 → MCP `mcp__unity__execute_code`; 没跑 → batchmode -executeMethod(见 wuhoo-unity-headless)

## 模板骨架

```csharp
// MCP execute_code 内: 类型必须全限定(无 using, CS0210 坑)
var path = "Assets/Art/Sprites/皮影部件/xxx.png";
var importer = UnityEditor.AssetImporter.GetAtPath(path) as UnityEditor.TextureImporter;
var provider = importer.GetDataProvider<UnityEditor.U2D.Sprites.ISpriteEditorDataProvider>();
var spriteRects = provider.GetSpriteRects();
// 改 rect/border/pivot → SetSpriteRects → provider.Apply() → importer.SaveAndReimport()
```

## 能力检查(必须先查后改, 防止数据损坏)

| 操作 | 需要 provider 支持 |
|------|-------------------|
| 改名称/rect/border/pivot | EditSpriteName / EditSpriteRect / EditBorder / EditPivot |
| 增删/切片 | CreateAndDeleteSprite |
| 轮廓 | ISpriteOutlineDataProvider.SetOutlines(GUID, Vector2[][]) |

## 常见操作

- 批量切割: 自动切割(alpha)/网格切割/等距切割, 用 TextureImporter.spritesheet 或 provider 的 SpriteRect 数组
- 批量改 pivot: 统一锚点(皮影部件按骨骼点锚定), 枚举用命名值 `(int)SpriteAlignment.Custom` 不用魔法数
- 九宫格边框: 改 SpriteRect.border(皮影道具/容器花纹)
- 图集: 精灵图集(Sprite Atlas)下子图数据仍由 importer 管理

## 皮影整图路线下的可选用途(guimei, 决策122)

1. 整身母版插画导入(统一 PPU/过滤模式) + 头层裁切 importer 设置(可选项)
2. 头层/手臂粗层 pivot 设置(挂点=neck/shoulder, 格式 docs/guimei-puppet-format-v0.2.md)
3. 表情头茬网格切片(换头茬集, 挂在头层)
4. 每步留验证: Unity Console 0 error + 资源窗口抽查

〔历史〕B' 大块切块流程(决策117)与 52 件批量 pivot 已废止, 不再执行。

## 坑

- enum 赋值永远用命名值+cast, 不用裸数字
- 不用 AssetPostprocessor / MenuItem 模式做批处理(官方 skill 明确禁止)
- 一次一改+验证, 禁止批量乱改后一起看结果
- 改完必须 SaveAndReimport 才落盘
