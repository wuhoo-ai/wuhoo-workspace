---
name: wuhoo-game-art
description: "Use for sprite/texture generation. Art pipeline."
version: 3.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, art, sprite, texture, guimei, shadow-puppet, z-image, pixel-art]
    related_skills: [wuhoo-game-exec, wuhoo-game-gates, zimage-local-image-generation]
---

# wuhoo-game-art — 美术管线

> 核心原则：风格一致性靠**管线与配方**，不靠 AI 画得好。
> guimei（皮影柔情国风）走 §2 皮影配方；miners-watch（像素风）走 §1 像素管线。

## 触发条件

- 需要生成/替换精灵、贴图、UI 图标、立绘、背景景片
- 美术资产风格不一致需要统一
- guimei 皮影资产出图（Z-Image/SenseNova/wan2.7）

---

## §1 像素管线（miners-watch）

```
[人类一次性决策]           [管线自动化]           [人类终审]
style-guide.yaml    →   批量生成(同seed)   →   小批量审
调色板 32色 PNG     →   后处理标准化       →   批量审
参考图 3-5张       →   格式验证           →   入库
```

- Style Guide: `Docs/Art/style-guide.yaml`（32色 palette / 48x48 / style_keywords + negative_keywords）
- 后处理: `Tools/art-pipeline.py`（resize NEAREST → palette quantize FloydSteinberg → trim → PNG alpha）
- 精灵表: 4行×4列（idle/walk/attack/mine），每帧 48x48，总表 192x192
- AI 生图: wan2.7-image-pro，同组同 seed + style prompt
- Unity 导入: spriteMode single/multiple, FilterMode Point, Compression None

---

## §2 guimei 皮影风格出图（Z-Image 实测配方）

> 实测日期: 2026-08-22（R1-R6 共 15 张探索 + 用户反馈迭代）。管线细节/部署坑见 zimage-local-image-generation + wuhoo-game-gpu §10.8。
> 风格圣经: GDD/07-style-bible-production.md (SB v3.1 已验收) + GDD/40-shadow-puppet-direction.md。

### 管线定位

- **Z-Image Turbo**（GPU ComfyUI 8188, GGUF Q8）= 主力（~20s/张, 剪影/剪纸感好）
- SenseNova U1.5 = 备用（~10min/张, 偏水墨, 编辑/4K）
- 交付: 只推 Codeup（微信不发图）；GitHub 周同步一次；preview/ 1280px JPEG 走普通 git

### 皮影配方 6 条（R1-R5 实测）

1. **cfg=2.0 + 负面提示 = 消渐变开关**: cfg=1(官方默认)负面不参与采样必带 3D 渐变; cfg=2 扁平度 50→95 分
   负面清单: `3d render, photorealistic, gradient, soft shading, volume, depth of field, anime, cel shading, oil painting, watercolor wash, realistic skin, glossy highlights, translucent material, backlit glow, seamless whole puppet, busy background, text, watermark`
2. **真扁平词块**: `flat vector illustration, 2D flat design, solid flat colors, matte flat coloring, clean hard edges, flat cutout puppet pieces with visible joint lines, silhouette`
3. **实体词陷阱**: `shadow puppet / piying xi / translucent leather / backlight` 反而触发 3D 半透明材质（训练数据里 shadow puppet 3D render 多）——皮影只作内容元素轻提，不作风格主词
4. **禁用词**: `cinematic / close-up / 3/4` 镜头词触发 3D 渲染模式; 中文抽象工艺描述执行有限
5. **元素驱动 > 风格术语**: 具体物件清单（白衣湿透/长发垂水/红带/木梳/刻线眉眼）比抽象风格词有效
6. **最佳结构**: 扁平词块 + 具体元素清单 + cfg=2 + 负面清单

### R6 教训: 发光 vs 透射（2026-08-22 用户反馈"透光质感出戏"）

**皮影的"透光"= 背光透射**：灯在幕布后，光穿过半透明染色兽皮 → 平面、暖色、色块分明、镂空处透亮、染色不均匀有手工感（r3_a/b 正确示范：暖白/琥珀、米黄平背景、无硬阴影、无体积光）。

**反面教材（r6_b）**：把"磷光"写成 glowing/发光体 → 模型进入 3D 材质模式——内部自发光（荧光绿裙摆）、次表面散射（玉石/磨砂玻璃）、边缘轮廓光（月亮勾边）、水面倒影、体积纵深。全部是 3D 渲染光语言。

**规则**:
- 内容需求里的"光/磷光/荧光"类描述 → 写成**染在皮革上的颜色在透射光下的呈现**（`cold jade-green dye on translucent leather, color visible where light passes through`），禁止 `glowing / neon / luminous` 等发光体词
- 光物理词只允许: `backlit, light transmitted through the material, warm lamp glow behind the screen, flat silhouette`
- 负面追加: `glowing edges, rim light, neon, sub-surface scattering, jade glass, volumetric light, water reflection, depth`
- 皮影光物理三特征（对照检查）: ①平面无体积 ②光从背后穿过材质 ③色块鲜明+镂空透亮；出现"发光/描边/倒影/纵深"任一 = 3D 光，打回

### 内容吻合度检查（出图后 vision 自审三问）

1. 内容符合度: prompt 关键元素是否齐全（湿衣/长发/泪痕/法器/背景）
2. 风格执行度: 是否平面皮影（非 3D 渲染/非 Q 卡通）
3. 最明显缺陷: 一句话指出最需修的 1 点（用于下一轮 prompt 定向修正）

---

## §3 通用约束

- 小批量验证: 先出 2-3 张 → 用户审 → 确认方向 → 批量
- 每轮迭代必须记录 prompt 变体与效果（review/ 目录 + 会话）
- prompt 必须先给用户看再执行（用户铁律）
