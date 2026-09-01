---
name: wuhoo-game-voice
description: "Use for game VO/dialogue TTS. qwen-audio-3.0 pipeline."
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, voice, tts, dialogue, narration, qwen-audio]
    related_skills: [wuhoo-game-audio, wuhoo-game-exec, wuhoo-game-art]
---

# wuhoo-game-voice — 游戏配音管线 (qwen-audio-3.0-tts)

> 2026-08-03 新建。token-plan workspace 实测验证通过。
> 定位：**语音配音**（对白 VO / 旁白 / 剧情朗读），不是音乐。
> BGM/SFX 走 `wuhoo-game-audio`（HeartMuLa），本 skill 不重叠。

## 触发条件

- 需要生成角色对白配音、旁白、剧情语音
- GDD 中 voice_assets / 对白音频条目需要实现
- 鬼魅(guimei)项目哈迪斯2式竖版对白需要语音化

## 模型选型

| 模型 | 定位 | 何时用 |
|------|------|--------|
| `qwen-audio-3.0-tts-plus` | 高质量，Artificial Analysis 全球榜单第一 | 游戏资产默认选它 |
| `qwen-audio-3.0-tts-flash` | 首包 300ms 低延迟 | 仅实时交互原型 |

能力要点（实测）：
- **指令控制 (freestyle)**: 自然语言控制情绪/角色/语速/风格，如"哀婉幽怨的年轻女子声音，语速缓慢，带一丝叹息"。实测遵循度高。
- **细粒度标签**: 文本内嵌 `[sigh]`(叹息) `[gasp]`(抽气) `[giggles]`(轻笑) `[angry]` 等约 86 个标签，控制精度到单字。实测 `[sigh]` 生效。
- **音质**: 支持 48kHz/16bit WAV 输出（录音棚级）。
- **长度**: 单次合成最长约 3 分钟；长文本由脚本自动分块拼接（默认 500 字/块）。
- **音色**: 系统音色 + 500 余个基础音色(`qwen-audio-3.0-tts-plus-{后缀}`, 列表见官方 Excel) + 声音复刻(每账号 1000 配额)。
- **价格**: 1.4 元/万字符（北京地域）。

## 调用通道（重要）

token-plan workspace 走 **DashScope WebSocket SDK**，不是 OpenAI 兼容接口：

```python
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat
dashscope.api_key = TOKEN_PLAN_API_KEY          # ~/.hermes/.env
dashscope.base_websocket_api_url = \
  'wss://token-plan.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference'
syn = SpeechSynthesizer(model="qwen-audio-3.0-tts-plus", voice="longanhuan_v3.6",
                        format=AudioFormat.WAV_44100HZ_MONO_16BIT,
                        instruction="...")
audio_bytes = syn.call(text)
```

## 快速使用

```bash
# 单句
python3.11 scripts/gen_voice.py --text "客官，要打尖还是住店？" \
    --voice longanhuan_v3.6 -o /tmp/out.wav

# 批量对白文件 + 角色指令 + Unity 标准格式(44.1kHz wav)
python3.11 scripts/gen_voice.py --file dialog.txt --voice longanlufeng \
    --instruction "沉稳温和的青年书生声音，像在灯下读诗" \
    --format wav44 -o Assets/Audio/VO/ch01_line01.wav
```

脚本能力: `--format {wav48,wav44,mp3hq,mp3}` / `--instruction` / `--rate` / `--pitch` / `--volume` / 长文本自动分块+段间 0.15s 静音拼接。

## 音色表（qwen-audio-3.0-tts-plus 系统音色）

| voice 参数 | 角色 | 特质 | 语言 |
|-----------|------|------|------|
| `longanlingxin` | 旗舰女 | 知心温暖 | 中/英 |
| `longanlufeng` | 旗舰男 | 明亮开朗 | 中/英 |
| `longanhuan_v3.6` | 精品中文女 | 25岁 | 中/英 |
| `longjielidou_v3.6` | 男童 | 天真，5岁 | 中/英 |
| `loongeva_v3.6` | 英文女 | 高智美音 | 英 |
| `loongjohn` | 英文男 | 沉稳美音 | 英 |

苍老/特殊音色：系统音色无老者选项 → 用基础音色(官方 Excel)或声音复刻；或 `--pitch` 压低临时顶上。

### 鬼魅(guimei)角色映射建议（待用户试听定稿）

| 角色 | voice | instruction 方向 |
|------|-------|-----------------|
| 吴守桥(书生主角) | longanlufeng | 沉稳温和的青年书生，灯下读诗，略带感慨 |
| 苏小小(水鬼) | longanhuan_v3.6 | 哀婉幽怨年轻女子，语速缓慢，深夜古渡口诉说往事，带叹息 |
| 旁白/志怪朗读 | longanlingxin | 冷静克制的女声旁白，缓慢庄重 |
| 龙套(老翁/判官等) | 基础音色或复刻 | 按角色定 |

## 格式标准（对齐 wuhoo-game-audio）

```
对白 VO: WAV 44.1kHz mono 16bit  (--format wav44)
预览草稿: mp3 默认即可
文件命名: Assets/Audio/VO/<chapter>_<role>_<line>.wav
```

## Pitfalls（实测踩坑）

1. **OpenAI 兼容接口不支持 TTS**: POST `/compatible-mode/v1/audio/speech` 返回 400 `url error`。必须走 WebSocket SDK。
2. **CosyVoice 音色名无效**: `longnan_v3`、`longlaobo_v3` 等 `long*_v3` 音色在本模型上 `call()` 静默返回 None。只认 v3.6 / longan* 系统音色和 `qwen-audio-3.0-tts-plus-*` 基础音色。
3. **dashscope 只装在 python3.11**: 脚本必须用 `python3.11` 跑；系统 python3=3.6 会报 ModuleNotFoundError。安装: `pip3.11 install dashscope`。
4. **失败时查 request_id**: `syn.get_last_request_id()` 打印出来供排查。
5. **纯标点文本被拒**: 服务端返回 `InvalidParameter: Please ensure input text is valid.`。长文本分块时若边界切出孤立标点 chunk 会失败——脚本已自动合并纯标点碎片到相邻块并逐块重试 3 次。
6. **地域**: token-plan 是 cn-beijing workspace，WebSocket URL 里的 workspace 前缀不能丢。
7. **指令用中文写**: freestyle instruction 中文效果最好。
8. **WAV header nframes 不可靠**: dashscope 流式产物的 header 长度字段可能失真，脚本按字节计算时长、手动解析 RIFF data chunk 做拼接。

## 验证记录（2026-08-03）

- 基础合成 ✓ (mp3 默认)
- WAV 48kHz + instruction 指令控制 ✓ (longanhuan_v3.6 苏小小风格, 934KB)
- longanlufeng 男声 + 李贺诗台词 ✓ (911KB)
- longanlingxin 旁白 + 太平广记引文 ✓ (1.0MB)
- 细粒度标签 [sigh] ✓
- 无效音色验证: longnan_v3 / longlaobo_v3 / longshuo_v3.6 均失败 ✓
- gen_voice.py 端到端: 单句 wav44 ✓ / 分块拼接(max-chunk=8, 3块) ✓ / WAV header-body 时长一致 ✓
- split_text 单元测试: 5 用例全过 (含纯标点/空文本边界) ✓
- 纯标点输入正确报错退出 ✓
- 修复: 孤立标点 chunk 合并 + 逐块重试3次 + WAV 字节级时长计算
