---
name: wuhoo-game-dev-music-from-task
description: "Use when you need to generate background music or sound effects from an audio task specification. Input: one task from tasks.json with type=audio. Output: .mp3/.wav audio files. Invokes songwriting/heartmula skills for BGM, generates SFX via Suno sound-effect mode or procedural generation."
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, audio, music, sfx, suno, heartmula]
    related_skills: [songwriting-and-ai-music, heartmula, wuhoo-game-dev-gdd-to-tasks, wuhoo-game-dev-review-task]
---

# Wuhoo Music From Task

单个 audio task → BGM .mp3 + SFX .wav 文件。

## When to Use

- task.type = "audio"
- 需要生成背景音乐 (白天/夜晚/Boss)
- 需要生成音效 (挖矿/攻击/UI/环境)

## Workflow

### Step 1: 读取 Task Spec

```
task.spec: "生成白天探索 BGM: 轻松节奏 60-80BPM 循环 无歌词"
task.params: { "bpm": 70, "mood": "exploration", "loop": true, "duration": 120 }
task.output: "Assets/Audio/BGM/bgm_day.mp3"
```

### Step 2: 确定音频类型

| 类型 | 工具 | 格式 | 参数 |
|------|------|------|------|
| BGM | songwriting/heartmula | .mp3 (压缩) | BPM, mood, loop, duration |
| SFX (1-2s) | Suno 音效模式 或 Python 程序化 | .wav (未压缩) | 事件类型, 变体数 |
| 环境音 | Suno 或 程序化噪声 | .mp3 | 场景氛围描述 |

### Step 3: 生成

**BGM 生成 (songwriting skill)**:

```
加载 songwriting-and-ai-music skill → 按照 task.spec 生成歌词/曲风提示词
→ 调用 Suno/heartmula 生成 → 下载 → 裁剪到 duration
→ 确保开头和结尾可无缝循环 (loop 标记)
```

**SFX 生成 (程序化优先)**:

短音效 (<2s) 优先用 Python 程序化生成 (减少 API 调用):

```python
# 例: 挖矿音效 - 用 numpy 生成撞击声
import numpy as np
import soundfile as sf

sr = 44100
duration = 0.3
t = np.linspace(0, duration, int(sr * duration))
# 噪声衰减模拟撞击
hit = np.random.randn(len(t)) * np.exp(-t * 20)
hit = hit / np.max(np.abs(hit))
sf.write('sfx_mine_1.wav', hit, sr)
```

如果程序化效果不够 → 用 Suno 音效模式。

### Step 4: Unity 音频配置

写入 `AssetPostprocessor` 补充音频设置：

```csharp
// 追加到 Assets/Editor/AutoImportAudio.cs
void OnPreprocessAudio()
{
    var importer = (AudioImporter)assetImporter;

    if (assetPath.Contains("BGM/"))
    {
        // BGM: 压缩, 流式加载
        importer.defaultSampleSettings = new AudioImporterSampleSettings
        {
            loadType = AudioClipLoadType.Streaming,
            compressionFormat = AudioCompressionFormat.Vorbis,
            quality = 0.7f
        };
    }
    else if (assetPath.Contains("SFX/"))
    {
        // SFX: 解压, 低延迟
        importer.defaultSampleSettings = new AudioImporterSampleSettings
        {
            loadType = AudioClipLoadType.DecompressOnLoad,
            compressionFormat = AudioCompressionFormat.PCM,
        };
    }
}
```

### Step 5: 输出报告

```markdown
## Task {id} 音频完成报告

**状态**: ✅
**输出文件**:
  - Assets/Audio/BGM/bgm_day.mp3 (120s, 70BPM, 3.2MB)
  - Assets/Audio/SFX/sfx_mine_01.wav (0.3s, 52KB)
  - Assets/Audio/SFX/sfx_mine_02.wav (0.25s, 44KB)
**音频配置**: BGM=Vorbis Streaming / SFX=PCM DecompressOnLoad
**Self-Review**: ✅ BPM 匹配, 变体数到位, 无缝循环已验证
```

## BGM 规格速查

| 场景 | BPM | 风格关键词 | 时长 |
|------|-----|-----------|------|
| 白天探索 | 60-80 | 轻松/冒险/lo-fi 节拍 | 90-180s |
| 夜晚防御 | 100-130 | 紧张/电子/鼓点驱动 | 90-120s |
| Boss 战 | 130-160 | 史诗/管弦/重金属 | 60-120s |
| 主菜单 | 70-90 | 氛围/主题曲 | 60-90s |

## SFX 规格速查

| 事件 | 数量 | 长度 | 说明 |
|------|------|------|------|
| 挖矿 | 2-3 变体 | 0.2-0.5s | 不同矿物不同音色 |
| 收集物品 | 1 | 0.3s | 金币叮当声 |
| 怪物受伤 | 2 变体 | 0.2-0.4s | 不同怪物不同音色 |
| UI 点击 | 1-2 变体 | 0.1s | 干净清脆 |
| 昼夜切换 | 1 | 1-2s | 过渡氛围 |
| 胜利/失败 | 各 1 | 2-3s | 有仪式感 |

## Pitfalls

1. BGM 无缝循环失败 — 开头和结尾振幅不匹配 → 检查前 0.1s 和后 0.1s 是否平滑
2. SFX 延迟太高 — 移动端关键 → 用 DecompressOnLoad + PCM 格式
3. 包体过大 — 所有 BGM 加起来 < 10MB → 用 Vorbis 压缩 quality=0.5
4. 缺少变体 — 同一个音效反复播放会疲劳 → 每个 SFX 事件至少 2 个变体
5. 版权问题 — Suno/Udio 付费版允许商用 → 确认授权后再用

## Verification

- [ ] 音频文件在正确的 output 路径
- [ ] BGM: 时长/BPM/mood 符合 task.params
- [ ] SFX: 长度 ≤ 2s, 至少 2 个变体 (如果 task 要求)
- [ ] AutoImportAudio.cs 覆盖对应路径
- [ ] 在 Unity Editor 中播放测试, 无削波/失真
