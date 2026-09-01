---
name: wuhoo-game-audio
description: "Use for BGM/SFX generation. Audio pipeline."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, audio, music, sfx, heartmula, suno]
    related_skills: [wuhoo-game-exec, wuhoo-game-art]
---

# wuhoo-game-audio — 音频管线

> 改写自: music-from-task。
> 管线：prompt 模板 → 生成 → 格式标准化 → 导入验证。

## 触发条件

- 需要生成/替换 BGM 或 SFX
- GDD 中 audio_assets 条目需要实现

## Prompt 模板 (Docs/Audio/prompt-templates.yaml)

```yaml
bgm_surface:
  prompt: "8-bit chiptune, peaceful mining village, warm acoustic, 120bpm, loop"
  duration: "60s"
bgm_cave:
  prompt: "8-bit ambient, dark cave, dripping water, tension, 90bpm, loop"
  duration: "60s"
bgm_night:
  prompt: "8-bit battle, urgent, drums, 140bpm, loop"
  duration: "45s"
sfx_mine:
  prompt: "8-bit pickaxe hit rock, 0.2s, single"
sfx_hit:
  prompt: "8-bit impact, metallic clang, 0.2s"
sfx_coin:
  prompt: "8-bit coin collect, bright ding, 0.15s"
```

## 生成工具

| 工具 | 用途 | 接入 |
|------|------|------|
| HeartMuLa | BGM 生成 (Suno-like) | skill: heartmula |
| numpy+soundfile | 程序化 SFX | Python 脚本 |
| OpenGameArt/Freesound | 占位/参考 | 手动下载 |

## 格式标准化

```
所有音频: WAV 44.1kHz mono
BGM: < 2MB, loop-friendly (首尾静音 < 0.1s)
SFX: < 500KB, 单声道, 无尾部静音
```

## 导入 Unity

- 路径: `Assets/Resources/Audio/{BGM|SFX}/{name}.wav`
- 运行时: `Resources.Load<AudioClip>("Audio/SFX/sfx_mine")`
- AudioSource 配置: BGM loop=true, SFX loop=false

## 终审

- 用户试听 → 确认/替换
- 不阻塞开发：先用占位音频，最终替换不影响代码
