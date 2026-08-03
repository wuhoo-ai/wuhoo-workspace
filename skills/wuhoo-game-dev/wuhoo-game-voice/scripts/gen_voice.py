#!/usr/bin/env python3.11
"""gen_voice.py — qwen-audio-3.0-tts 游戏配音生成 (token-plan workspace)

用法:
  python3.11 gen_voice.py --text "客官，要打尖还是住店？" --voice longanhuan_v3.6 -o /tmp/out.wav
  python3.11 gen_voice.py --file dialog.txt --voice longanlufeng \
      --instruction "沉稳温和的青年书生声音，像在灯下读诗" --format wav44 -o Assets/Audio/VO/line01.wav

模型: qwen-audio-3.0-tts-plus (高质量) / qwen-audio-3.0-tts-flash (低延迟)
音色: 见 SKILL.md 音色表。CosyVoice 的 long*_v3 音色在本模型上无效。
依赖: pip3.11 install dashscope   (仅 python3.11 装了)
密钥: ~/.hermes/.env 的 TOKEN_PLAN_API_KEY
"""
import argparse
import io
import os
import re
import sys
import wave

ENV_PATH = "~/.hermes/.env"
WS_URL = "wss://token-plan.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"

FORMATS = {
    "wav48": "WAV_48000HZ_MONO_16BIT",   # 最高品质
    "wav44": "WAV_44100HZ_MONO_16BIT",   # Unity 资产标准 (wuhoo-game-audio)
    "mp3hq": "MP3_48000HZ_MONO_256KBPS",
    "mp3": "MP3_22050HZ_MONO_256KBPS",   # 默认值, 品质低, 勿用于资产
}


def load_api_key():
    key = os.environ.get("TOKEN_PLAN_API_KEY")
    if key:
        return key
    path = os.path.expanduser(ENV_PATH)
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line.startswith("TOKEN_PLAN_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("错误: 找不到 TOKEN_PLAN_API_KEY (环境变量或 %s)" % ENV_PATH)


def split_text(text, max_chars=500):
    """按句号/问号/叹号/换行切块, 单块 <= max_chars。"""
    parts = re.split(r"(?<=[。！？；!?…\n])", text)
    chunks, buf = [], ""
    for p in parts:
        if not p.strip():
            continue
        if len(buf) + len(p) <= max_chars:
            buf += p
        else:
            if buf:
                chunks.append(buf)
            # 单句超长则硬切
            while len(p) > max_chars:
                chunks.append(p[:max_chars])
                p = p[max_chars:]
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


def _wav_data(payload):
    """从 WAV 字节流中提取纯 PCM 数据和 (rate, sampwidth, nchannels)。

    dashscope 流式产物的 header 长度字段不可靠, 因此手动定位 RIFF
    中的 'data' chunk, 返回 data chunk 声明长度内的字节 (若声明长度
    超过实际剩余字节, 取到末尾)。
    """
    import struct
    i = payload.find(b"data")
    if i < 0:
        raise ValueError("未找到 WAV data chunk")
    (size,) = struct.unpack("<I", payload[i + 4:i + 8])
    body = payload[i + 8:]
    body = body[:size] if size < len(body) else body
    # fmt chunk 提取参数
    j = payload.find(b"fmt ")
    if j < 0:
        raise ValueError("未找到 WAV fmt chunk")
    (fsize,) = struct.unpack("<I", payload[j + 4:j + 8])
    fmt = payload[j + 8:j + 8 + fsize]
    (_tag, nch, rate, _br, _ba, sampw) = struct.unpack("<HHIIHH", fmt[:16])
    return body, (rate, sampw // 8, nch)


def concat_wav(parts, gap_s=0.15):
    """拼接多段 WAV, 段间插入静音。"""
    params = None
    frames = []
    for p in parts:
        body, info = _wav_data(p)
        if params is None:
            params = info  # (rate, sampwidth, nchannels)
        frames.append(body)
    assert params is not None, "没有可拼接的音频段"
    rate, sampw, nch = params
    gap = b"\x00" * int(rate * sampw * nch * gap_s)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        total_frames = sum(len(f) // (sampw * nch) for f in frames) + \
            len(gap) * (len(frames) - 1) // (sampw * nch)
        w.setparams((nch, sampw, rate, total_frames, "NONE", "not compressed"))
        for i, f in enumerate(frames):
            w.writeframes(f)
            if i < len(frames) - 1:
                w.writeframes(gap)
    return out.getvalue()


def main():
    ap = argparse.ArgumentParser(description="qwen-audio-3.0-tts 游戏配音生成")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="要合成的文本")
    g.add_argument("--file", help="文本文件路径 (UTF-8)")
    ap.add_argument("--voice", default="longanhuan_v3.6", help="音色 (默认 longanhuan_v3.6)")
    ap.add_argument("--model", default="qwen-audio-3.0-tts-plus",
                    choices=["qwen-audio-3.0-tts-plus", "qwen-audio-3.0-tts-flash"])
    ap.add_argument("--instruction", default=None,
                    help="freestyle 指令: 情绪/角色/语速/风格, 如 '哀婉幽怨的年轻女子声音，语速缓慢'")
    ap.add_argument("--format", default="wav44", choices=list(FORMATS),
                    help="输出格式 (默认 wav44 = Unity 资产标准)")
    ap.add_argument("--rate", type=float, default=None, help="语速倍率 (0.5~2.0)")
    ap.add_argument("--pitch", type=float, default=None, help="音调倍率")
    ap.add_argument("--volume", type=int, default=None, help="音量 0~100")
    ap.add_argument("--max-chunk", type=int, default=500, help="单块最大字符数")
    ap.add_argument("-o", "--output", default=None, help="输出文件路径")
    args = ap.parse_args()

    text = args.text if args.text else open(args.file, encoding="utf-8").read()
    text = text.strip()
    if not text:
        sys.exit("错误: 文本为空")

    import dashscope
    from dashscope.audio.tts_v2 import AudioFormat, SpeechSynthesizer

    dashscope.api_key = load_api_key()
    dashscope.base_websocket_api_url = WS_URL
    fmt = getattr(AudioFormat, FORMATS[args.format])

    chunks = split_text(text, args.max_chunk)
    parts = []
    for i, ch in enumerate(chunks, 1):
        kw = dict(model=args.model, voice=args.voice, format=fmt)
        if args.instruction:
            kw["instruction"] = args.instruction
        if args.rate is not None:
            kw["speech_rate"] = args.rate
        if args.pitch is not None:
            kw["pitch_rate"] = args.pitch
        if args.volume is not None:
            kw["volume"] = args.volume
        syn = SpeechSynthesizer(**kw)
        audio = syn.call(ch)
        rid = syn.get_last_request_id()
        if not audio:
            sys.exit("错误: 第 %d/%d 块合成失败 (request_id=%s)。"
                     "常见原因: 音色名无效 (本模型须用 v3.6/longan* 系列) 或文本含违禁内容"
                     % (i, len(chunks), rid))
        parts.append(audio)
        print("[%d/%d] OK %dB rid=%s" % (i, len(chunks), len(audio), rid), file=sys.stderr)

    if args.format.startswith("wav"):
        data = concat_wav(parts) if len(parts) > 1 else parts[0]
        ext = ".wav"
    else:
        data = b"".join(parts)
        ext = ".mp3"

    out = args.output or os.path.join("voice_out", "voice_%s%s" % (
        __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S"), ext))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)

    if args.format.startswith("wav"):
        with wave.open(out, "rb") as w:
            fr = w.getframerate()
            # header 的 nframes 不可靠(dashscope 流式产物), 按字节计算
            secs = len(data) / (fr * w.getsampwidth() * w.getnchannels())
            print("输出: %s | %.1fs | %dHz %dch %dbit | %dB" % (
                out, secs, fr, w.getnchannels(), w.getsampwidth() * 8, len(data)))
    else:
        print("输出: %s | %dB" % (out, len(data)))


if __name__ == "__main__":
    main()
