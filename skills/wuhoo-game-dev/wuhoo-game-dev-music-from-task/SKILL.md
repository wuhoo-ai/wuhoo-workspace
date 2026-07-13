---
name: wuhoo-game-dev-music-from-task
description: "Use when you need to generate background music or sound effects from an audio task specification. Input: one task from tasks.json with type=audio. Output: .mp3/.wav audio files. Primary engine: HeartMuLa (local GPU, free, Apache-2.0). Songwriting skill used for prompt/lyrics engineering. SFX via procedural generation (numpy+soundfile) for short sounds."
version: 1.1.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, audio, music, sfx, heartmula, songwriting]
    related_skills: [heartmula, songwriting-and-ai-music, wuhoo-game-dev-gdd-to-tasks, wuhoo-game-dev-review-task]
---

# Wuhoo Music From Task

单个 audio task → BGM .mp3 + SFX .wav 文件。

**主引擎**: HeartMuLa (本地 GPU, 开源免费, 12GB VRAM 可跑 3B 模型)
**辅助**: songwriting skill (prompt/lyrics 工程), numpy+soundfile (短音效程序化生成)
**云端备用**: Suno/Udio (HeartMuLa 不可用时)

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

### Step 2: 确定音频类型与引擎 + 峰谷检查

| 类型 | 引擎 | 格式 | 参数 | 高峰行为 |
|------|------|------|------|---------|
| BGM (>30s) | **HeartMuLa** (本地 GPU) | .mp3 | BPM, mood, tags, loop, duration | ⏳ 入队 |
| SFX (<2s) | **Python 程序化** (numpy+soundfile) | .wav | 事件类型, 变体数 | ✅ 直接跑 (轻量) |
| 环境音 (10-30s) | HeartMuLa 或 程序化噪声 | .mp3 | 场景氛围描述 | ⏳ 入队 (如需 HeartMuLa) |

**峰谷检查** (BGM/HeartMuLa 类任务)：
```python
if task_needs_heartmula:
    guard_result = peak_hour_guard(
        task_type='heartmula',
        task_id=task['id'],
        task_context={'spec': task['spec'], 'params': task['params'], 'output': task['output']}
    )
    if guard_result == 'deferred':
        return  # 入队, 等低谷 GPU 批处理
```
SFX 程序化生成不受影响——高峰直接跑。

### Step 3: BGM 生成 (HeartMuLa)

**3a. 用 songwriting skill 写 prompt**:

加载 songwriting-and-ai-music skill → 根据 task.spec 生成:
- `tags.txt`: 逗号分隔风格标签, 如 `adventure,orchestral,70bpm,cinematic,hopeful,major-key`
- `lyrics.txt`: 如果 BGM 不需要歌词 → 用 `[Instrumental]` 标记; 如果需要 → 写对应语言的歌词

**3b. 调用 HeartMuLa**:

```bash
cd ~/heartlib && .venv/bin/activate
python ./examples/run_music_generation.py \
  --model_path=./ckpt \
  --version="3B" \
  --lyrics=./assets/lyrics.txt \
  --tags=./assets/tags.txt \
  --save_path="Assets/Audio/BGM/bgm_day.mp3" \
  --lazy_load true \
  --max_audio_length_ms 120000
```

**3c. 无缝循环处理**:

生成后, 用 ffmpeg 检查并修复循环点:

```bash
# 检查开头和结尾振幅是否平滑
ffmpeg -i bgm_day.mp3 -af "volumedetect" -f null /dev/null 2>&1

# 如果结尾不平滑, 做 50ms 淡出
ffmpeg -i bgm_day.mp3 -af "afade=t=out:st=119.95:d=0.05" bgm_day_looped.mp3
```

### Step 4: SFX 生成 (程序化)

短音效 (<2s) 用 Python 程序化生成 (零 API 调用):

```python
import numpy as np
import soundfile as sf

def generate_hit_sfx(filename, duration=0.3, sr=44100, decay=20):
    """生成撞击音效: 白噪声+指数衰减"""
    t = np.linspace(0, duration, int(sr * duration))
    hit = np.random.randn(len(t)) * np.exp(-t * decay)
    hit = hit / np.max(np.abs(hit))  # 归一化
    sf.write(filename, hit, sr)

def generate_mine_sfx(base_name, variants=2):
    """生成挖矿音效变体"""
    for i in range(variants):
        # 每个变体用不同 decay 模拟不同矿物硬度
        decay = 15 + i * 5
        generate_hit_sfx(f'{base_name}_{i+1:02d}.wav', decay=decay)

def generate_collect_sfx(filename):
    """金币收集音: 高频叮当声"""
    sr, dur = 44100, 0.15
    t = np.linspace(0, dur, int(sr * dur))
    # 两个正弦波叠加模拟金属撞击
    ding = (np.sin(2*np.pi*1200*t) + 0.5*np.sin(2*np.pi*2400*t)) * np.exp(-t*30)
    sf.write(filename, ding / np.max(np.abs(ding)), sr)
```

### Step 5: Unity 音频配置

写入 `AssetPostprocessor` 补充音频设置:

```csharp
// 追加到 Assets/Editor/AutoImportAudio.cs
void OnPreprocessAudio()
{
    var importer = (AudioImporter)assetImporter;

    if (assetPath.Contains("BGM/"))
    {
        importer.defaultSampleSettings = new AudioImporterSampleSettings
        {
            loadType = AudioClipLoadType.Streaming,
            compressionFormat = AudioCompressionFormat.Vorbis,
            quality = 0.7f
        };
    }
    else if (assetPath.Contains("SFX/"))
    {
        importer.defaultSampleSettings = new AudioImporterSampleSettings
        {
            loadType = AudioClipLoadType.DecompressOnLoad,
            compressionFormat = AudioCompressionFormat.PCM,
        };
    }
}
```

### Step 6: 输出报告

```markdown
## Task {id} 音频完成报告

**状态**: ✅
**引擎**: HeartMuLa 3B | Python 程序化
**输出文件**:
  - Assets/Audio/BGM/bgm_day.mp3 (120s, 70BPM, 3.2MB)
  - Assets/Audio/SFX/sfx_mine_01.wav (0.3s, 52KB)
  - Assets/Audio/SFX/sfx_mine_02.wav (0.25s, 44KB)
**音频配置**: BGM=Vorbis Streaming / SFX=PCM DecompressOnLoad
**Self-Review**: ✅ BPM 匹配, 变体数到位, 无缝循环已验证
```

## BGM 风格标签速查 (for HeartMuLa tags.txt)

| 场景 | BPM | tags.txt 示例 |
|------|-----|---------------|
| 白天探索 | 60-80 | `adventure,orchestral,cinematic,hopeful,light-percussion,major-key` |
| 夜晚防御 | 100-130 | `tense,electronic,drums,aggressive,minor-key,bass-heavy` |
| Boss 战 | 130-160 | `epic,orchestral,choir,metal,driving-percussion,dark` |
| 主菜单 | 70-90 | `atmospheric,ambient,piano,nostalgic,warm,lo-fi` |

## SFX 规格速查

| 事件 | 数量 | 长度 | 程序化方法 |
|------|------|------|-----------|
| 挖矿 | 2-3 变体 | 0.2-0.5s | 噪声+不同 decay |
| 收集物品 | 1 | 0.15s | 双正弦叠加 |
| 怪物受伤 | 2 变体 | 0.2-0.4s | 低频噪声 |
| UI 点击 | 1-2 变体 | 0.1s | 短 sine ping |
| 昼夜切换 | 1 | 1-2s | 渐变 pad (HeartMuLa) |
| 胜利/失败 | 各 1 | 2-3s | HeartMuLa 短片段 |

## HeartMuLa 硬件要求

| GPU | 能跑吗 | 配置 |
|-----|--------|------|
| RTX 4070 Ti (12GB) | ✅ | `--version 3B --lazy_load true` (~6.2GB) |
| RTX 3060 (12GB) | ✅ | 同上 |
| RTX 4060 (8GB) | ⚠️ | 3B 勉强, 关闭其他程序 |
| 无 GPU | ❌ | 走云端备用 Suno/Udio |

## Pitfalls

1. HeartMuLa --lazy_load 拼写 — 是 `lazy_load` 不是 `lazy-load`
2. HeartCodec 用 fp32 — 不要用 bf16, 会劣化音质
3. tags 可能被忽略 — lyrics 权重更高, 如果 BGM 不需要歌词, lyrics.txt 写 `[Instrumental]`
4. BGM 无缝循环 — 开头末尾振幅不匹配 → ffmpeg 做 50ms 淡入淡出
5. SFX 延迟 — 移动端关键 → DecompressOnLoad + PCM
6. 包体过大 — 所有 BGM < 10MB → Vorbis quality=0.5
7. 缺少变体 — 同一音效反复播放会疲劳 → 每个 SFX 至少 2 变体
8. HeartMuLa 首次安装需要 30min — 下载模型 ~5GB, Python 3.10 venv
9. RTX 5080 已知不兼容 — 上游 issue 跟踪中

## Verification

- [ ] 音频文件在正确的 output 路径
- [ ] BGM: 时长/BPM/mood 符合 task.params
- [ ] SFX: 长度 ≤ 2s, 变体数达标
- [ ] AutoImportAudio.cs 覆盖对应路径
- [ ] Unity Editor 中播放无削波/失真
- [ ] BGM 无缝循环 (听开头 5s → 结尾 5s 过渡)
