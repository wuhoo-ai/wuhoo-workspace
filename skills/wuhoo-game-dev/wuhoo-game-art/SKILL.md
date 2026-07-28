---
name: wuhoo-game-art
description: "Use for sprite/texture generation. Art pipeline."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, art, pixel-art, sprite, palette, wan2.7]
    related_skills: [wuhoo-game-exec, wuhoo-game-gates]
---

# wuhoo-game-art — 美术管线

> 改写自: sprite-from-task。
> 核心原则：风格一致性靠**后处理管线**，不靠 AI 画得好。

## 触发条件

- 需要生成/替换精灵、贴图、UI 图标
- 美术资产风格不一致需要统一

## 管线流程

```
[人类一次性决策]           [管线自动化]           [人类终审]
style-guide.yaml    →   批量生成(同seed)   →   小批量审
调色板 32色 PNG     →   后处理标准化       →   批量审
参考图 3-5张       →   格式验证           →   入库
```

## Style Guide (Docs/Art/style-guide.yaml)

```yaml
palette: "Assets/Art/Palette/miners-watch-palette.png"  # 32色
resolution:
  characters: 48x48
  enemies: 48x48
  items: 32x32
  tiles: 256x256 (tileable)
  ui: 64x64 (buttons), 9-slice panels
style_keywords: "pixel art, 16-bit era, dark cave palette, warm torchlight"
negative_keywords: "3d render, photorealistic, smooth gradient, anime"
post_processing:
  - "resize to target (nearest neighbor)"
  - "quantize to palette (Floyd-Steinberg)"
  - "trim transparent border"
  - "export PNG with alpha"
```

## 后处理脚本 (Tools/art-pipeline.py)

```python
from PIL import Image
# 1. resize (nearest neighbor, 不插值)
img = img.resize((48, 48), Image.NEAREST)
# 2. palette quantize
palette_img = Image.open("palette.png").convert("P")
img = img.quantize(palette=palette_img, dither=Image.FLOYDSTEINBERG)
# 3. trim + export
```

## 精灵表规范

- 角色动画 = 一张 sprite sheet (4行×4列)
- 行: idle / walk / attack / mine
- 列: 4 帧
- 每帧 48x48，总表 192x192
- 帧顺序: 左→右，上→下

## AI 生图约束

- 模型: wan2.7-image-pro (token-plan)
- 同组资产使用相同 seed + style prompt
- prompt 模板: `"pixel art, {subject}, 16-bit, dark cave background, {palette_desc}, single sprite, transparent background, 48x48"`
- negative: `"3d, photorealistic, gradient, anime, multiple objects"`

## 导入 Unity

- 路径: `Assets/Art/Sprites/{Category}/{name}.png`
- 运行时加载的放 `Assets/Resources/Art/`
- TextureImporter: spriteMode=single(图标) / multiple(精灵表)
- FilterMode: Point (no filter)
- Compression: None

## 终审规则

- 小批量验证: 先做 1 组(16帧) → 用户审 → 确认风格 → 批量
- 批量送审: 每批 ≤ 20 张，附截图对比
- 不通过: 调 style guide 参数，重来一轮
