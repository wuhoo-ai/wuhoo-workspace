---
name: wuhoo-game-dev-sprite-from-task
description: "Use when you need to generate 2D pixel art sprites from an art task specification. Input: one task from tasks.json with type=art. Output: pixel-art PNG spritesheet + Unity .meta configuration. Automatically invokes pixel-art skill for generation and writes AssetPostprocessor scripts for automatic Unity import settings."
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, pixel-art, sprite, aseprite, unity, asset-pipeline]
    related_skills: [pixel-art, wuhoo-game-dev-gdd-to-tasks, wuhoo-game-dev-review-task]
---

# Wuhoo Sprite From Task

单个 art task → 像素画 spritesheet + Unity 自动导入配置。

## When to Use

- 用户分配了 type=art 的 task
- 需要生成角色 sprite、物品图标、UI 元素、tilemap 瓦片
- 需要批量生成像素画资产

## Workflow

### Step 1: 读取 Task Spec

```
task.spec: "生成近战攻击动画: 4帧 64x64 调色板 palette_warm_stone"
task.params: { "frames": 4, "width": 64, "height": 64, "palette": "warm_stone" }
task.output: "Assets/Sprites/player_attack.png"
```

### Step 2: 确定风格参数

根据 GDD 章节 5.1 (风格指南) 中的规格：

| 资产类型 | 分辨率 | 调色板 | 帧数 |
|---------|--------|--------|------|
| 主角 | 48×48 | warm_character | 4-6 |
| 怪物 | 32×32 | cool_enemy | 2-4 |
| 物品图标 | 32×32 | item_palette | 1 |
| UI 元素 | 可变 | ui_palette | 1-3 |
| Boss | 64×64 | boss_palette | 6+ |

### Step 3: 调用 pixel-art skill

使用 Hermes 内置 pixel-art skill 作为生成引擎：

```python
# via terminal tool
cd ~/.hermes/skills/creative/pixel-art/scripts

# 如果 task 有参考图:
python pixel_art.py reference.png output.png --preset snes --block 4

# 纯文字描述 (先让 LLM 生成参考描述, 再调 pixel-art):
# pixel-art skill 需要输入图片, 可以用画图工具先做草图
```

**备用方案** (无参考图时):
- 使用终端中的 Python + Pillow 直接生成基础形状
- 或使用 Midjourney/Stable Diffusion 生成参考图 → pixel-art skill 转换

### Step 4: 设置 Unity 导入参数

生成 sprite 后, 必须创建/更新 `AssetPostprocessor` 脚本：

```csharp
// Assets/Editor/AutoImportPixelArt.cs
// This file auto-configures pixel art texture import settings
using UnityEditor;

public class AutoImportPixelArt : AssetPostprocessor
{
    void OnPreprocessTexture()
    {
        if (!assetPath.StartsWith("Assets/Sprites/")) return;

        var importer = (TextureImporter)assetImporter;
        importer.textureType = TextureImporterType.Sprite;
        importer.filterMode = FilterMode.Point;      // 像素风: 不模糊
        importer.textureCompression = TextureImporterCompression.Uncompressed;
        importer.spritePixelsPerUnit = 16;

        // spritesheet 自动切片
        if (assetPath.Contains("_anim"))
        {
            importer.spriteImportMode = SpriteImportMode.Multiple;
        }
    }
}
```

### Step 5: 输出报告

```markdown
## Task {id} 精灵完成报告

**状态**: ✅
**输出文件**: Assets/Sprites/player_attack.png (256×64, 4帧 spritesheet)
**调色板**: warm_stone (已对齐 GDD 规格)
**帧数**: 4 (idle→windup→strike→recover)
**Unity 配置**: AutoImportPixelArt.cs 自动设置为 Point filter + Uncompressed
**Self-Review**: ✅ 分辨率/帧数/调色板均符合 task.spec
**注意事项**: 攻击帧的碰撞检测框需要在 Unity Sprite Editor 中手动调整 pivot
```

## 批量生成策略

当一个 task 需要多个 sprite (如 "生成 5 种矿物图标"):

1. 并行生成所有 sprite (独立任务可同时)
2. 统一检查风格一致性 (调色板/分辨率/线条粗细)
3. 一次性写入 AssetPostprocessor 覆盖所有路径

## 调色板管理

项目级调色板定义在 `Assets/Palettes/` (JSON 格式):

```json
{
  "warm_stone": ["#F5DEB3","#D2B48C","#8B7355","#5C4033","#3B2518"],
  "cool_enemy": ["#87CEEB","#4169E1","#191970","#0F0F2E","#050510"],
  "item_palette": ["#FF6B6B","#FFD93D","#6BCB77","#4D96FF","#9B59B6","#1A1A2E"]
}
```

Agent 生成 sprite 时必须使用对应调色板。

## Pitfalls

1. 忘记关 Anti-aliasing — 像素画导入 Unity 后模糊 → 检查 `filterMode: Point`
2. spritesheet 没切片 — 多帧动画导入后只显示第一帧 → 设置 `spriteImportMode: Multiple`
3. 调色板不一致 — 同一角色的不同动画看起来像不同角色 → 所有生成用同一个 palette JSON
4. 分辨率不匹配 — 48px 角色放在 32px 格子里会溢出 → 检查 GDD 规格
5. 色彩空间: Unity Linear vs Gamma — 像素画用 Gamma, 在 Project Settings → Player → Color Space 设为 Gamma

## Verification

- [ ] .png 文件在正确的 output 路径
- [ ] 分辨率/帧数符合 task.params
- [ ] 调色板符合 GDD 风格指南
- [ ] AutoImportPixelArt 脚本覆盖该路径
- [ ] 在 Unity Editor 中打开确认 Point filter 生效
