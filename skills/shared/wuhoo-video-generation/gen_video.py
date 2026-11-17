#!/usr/bin/env python3.11
"""Wan3.0-Video(-Prime) generation via Token Plan DashScope async API.

Modes: t2v / first_frame / first+last / reference(image|video|audio) / file / link.
Contract: references/wan3-api-contract.md (official docs verified 2026-11-17).
"""

import argparse
import base64
import io
import json
import os
import sys
import time
from pathlib import Path

import httpx
import yaml
from PIL import Image

PRIME = "wan3.0-video-prime"
STANDARD = "wan3.0-video"
MODELS = (PRIME, STANDARD)
RESOLUTIONS = ("480P", "720P", "1080P")
RATIOS = ("adaptive", "21:9", "16:9", "4:3", "1:1")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
JPEG_THRESHOLD = 4 * 1024 * 1024  # compress above this to avoid base64 WriteTimeout


def load_env_file(env_path: Path) -> dict:
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def get_config():
    """Return (dashscope_root_url, api_key). Env loads FIRST (v1 NameError fix)."""
    env_vars = load_env_file(Path.home() / ".hermes" / ".env")
    env_vars = {**env_vars, **os.environ}

    config_path = Path.home() / ".hermes" / "config.yaml"
    base_url = env_vars.get("TOKEN_PLAN_BASE_URL", "").rstrip("/")
    if not base_url and config_path.exists():
        cfg = yaml.safe_load(config_path.read_text()) or {}
        model_cfg = cfg.get("model", {}) or {}
        base_url = (model_cfg.get("base_url") or "").rstrip("/")
        # Token Plan gateway scan: new-style providers/fallback_providers first,
        # legacy sections kept for older configs (v1 scan missed providers.qwen).
        sections = []
        providers = cfg.get("providers")
        if isinstance(providers, dict):
            sections.extend(providers.values())
        fp = cfg.get("fallback_providers")
        if isinstance(fp, list):
            sections.extend(fp)
        elif isinstance(fp, dict):
            sections.extend(fp.values())
        sections.extend([cfg.get("fallback_model"), cfg.get("llm"),
                         (cfg.get("auxiliary", {}) or {}).get("vision")])
        legacy = cfg.get("custom_providers")
        if isinstance(legacy, dict):
            sections.extend(legacy.values())
        for section in sections:
            if isinstance(section, dict):
                u = section.get("base_url", "") or ""
                if "token-plan" in u:
                    base_url = u.rstrip("/")
                    break

    api_key = env_vars.get("TOKEN_PLAN_API_KEY", "")
    if not api_key:
        raise ValueError("TOKEN_PLAN_API_KEY not found in env or ~/.hermes/.env")
    if not base_url:
        raise ValueError("No token-plan base_url found (config.yaml or TOKEN_PLAN_BASE_URL)")
    for suffix in ("/compatible-mode/v1", "/v1"):
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)]
            break
    return base_url, api_key


def prepare_image(path: str) -> str:
    """Local image -> base64 data URL, enforcing wan3.0 input limits.

    - RGBA/P-with-alpha -> composite over WHITE (guimei white-bg convention; API
      rejects transparent PNG).
    - side outside [240, 8000] -> rescale keeping aspect.
    - >4MB or alpha-converted or >20MB -> JPEG q85 (base64 WriteTimeout pitfall).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    raw = p.read_bytes()
    img = Image.open(io.BytesIO(raw))
    had_alpha = img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info)
    if had_alpha:
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    rescaled = False
    if max(w, h) > 8000 or min(w, h) < 240:
        scale = min(8000 / max(w, h), max(240 / min(w, h), 1.0))
        if max(w, h) * scale > 8000:
            scale = 8000 / max(w, h)
        img = img.resize((max(240, int(w * scale)), max(240, int(h * scale))),
                         Image.Resampling.LANCZOS)
        rescaled = True
        print(f"  image rescaled {w}x{h} -> {img.size[0]}x{img.size[1]}")
    if max(img.size) / min(img.size) > 8:
        raise ValueError(f"Image aspect ratio > 8:1 ({img.size}), not accepted by API")

    suffix = p.suffix.lower()
    # rescaled forces re-encode: raw bytes would still carry the original size
    need_jpeg = (had_alpha or rescaled or len(raw) > JPEG_THRESHOLD
                 or suffix not in IMAGE_SUFFIXES)
    if need_jpeg or len(raw) > MAX_IMAGE_BYTES:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85)
        data = buf.getvalue()
        mime = "image/jpeg"
        print(f"  image -> JPEG q85 ({len(data)/1024:.0f}KB, alpha={had_alpha})")
    else:
        data = raw
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".bmp": "image/bmp", ".webp": "image/webp"}[suffix]
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"Image still >20MB after compression: {path}")
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def media_url(path_or_url: str, kind: str) -> str:
    """Images go through prepare_image; video/audio local files -> raw base64."""
    if path_or_url.startswith(("http://", "https://", "data:", "oss://")):
        return path_or_url
    p = Path(path_or_url)
    if not p.exists():
        raise FileNotFoundError(f"Media not found: {path_or_url}")
    if kind == "image":
        return prepare_image(path_or_url)
    size = p.stat().st_size
    limit = 100 * 1024 * 1024 if kind == "video" else 15 * 1024 * 1024
    if size > limit:
        raise ValueError(f"{kind} file >{limit//1024//1024}MB: {path_or_url}")
    if size > 50 * 1024 * 1024:
        print(f"  WARNING: {size/1024/1024:.0f}MB {kind} as base64 risks write timeout; "
              "prefer a public URL", file=sys.stderr)
    mime = "video/mp4" if kind == "video" else "audio/mpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def build_media(args) -> list:
    media = []
    if args.image:
        media.append({"type": "first_frame", "url": media_url(args.image, "image")})
    if args.last_frame:
        media.append({"type": "last_frame", "url": media_url(args.last_frame, "image")})
    for x in args.ref_image or []:
        media.append({"type": "reference_image", "url": media_url(x, "image")})
    for x in args.ref_video or []:
        media.append({"type": "reference_video", "url": media_url(x, "video")})
    for x in args.ref_audio or []:
        media.append({"type": "reference_audio", "url": media_url(x, "audio")})
    if args.file:
        media.append({"type": "file", "url": args.file})
    if args.link:
        media.append({"type": "link", "url": args.link})
    validate_combo(media)
    return media


def validate_combo(media: list):
    """Client-side preflight of official combo rules — reject before spending."""
    types = [m["type"] for m in media]
    n = {t: types.count(t) for t in set(types)}
    if n.get("first_frame", 0) > 1 or n.get("last_frame", 0) > 1:
        raise ValueError("first_frame/last_frame 各最多 1 张")
    if n.get("reference_image", 0) > 10:
        raise ValueError("reference_image 最多 10 张")
    if n.get("reference_video", 0) > 5 or n.get("reference_audio", 0) > 5:
        raise ValueError("reference_video/audio 各最多 5 段")
    if n.get("file", 0) + n.get("link", 0) > 1:
        raise ValueError("file 与 link 二选一，不可同传")
    frame_side = {"first_frame", "last_frame"} & set(types)
    ref_side = {"reference_image", "reference_video", "reference_audio",
                "file", "link"} & set(types)
    if frame_side and ref_side:
        raise ValueError("首帧/尾帧 与 reference_*/file/link 互斥，不可混用；"
                         "音频驱动请用 reference_image+reference_audio")


def build_parameters(args, media) -> dict:
    if args.duration != -1 and not (2 <= args.duration <= 30):
        raise ValueError("duration 须为 [2,30] 整数或 -1(智能时长)")
    params = {
        "resolution": args.resolution,
        "ratio": args.ratio,
        "duration": args.duration,
        "audio": args.audio,
        "watermark": args.watermark,
    }
    has_doc = any(m["type"] in ("file", "link") for m in media)
    params["prompt_extend"] = True if has_doc else args.prompt_extend
    if args.seed is not None:
        if not (-1 <= args.seed <= 2147483647):
            raise ValueError("seed 取值 -1 或 [0,2147483647]")
        params["seed"] = args.seed
    return params


def submit_task(base_url, api_key, body) -> dict:
    url = f"{base_url}/api/v1/services/aigc/video-generation/video-synthesis"
    resp = httpx.post(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }, json=body, timeout=600)
    return {"http": resp.status_code, "json": resp.json() if resp.content else {}}


def model_unavailable(result: dict) -> bool:
    if result["http"] == 200:
        return False
    j = result["json"]
    code = str(j.get("code", ""))
    msg = str(j.get("message", "")).lower()
    return ("model" in code.lower()
            or ("model" in msg and any(k in msg for k in
                ("not exist", "not found", "not support", "unsupported", "invalid",
                 "不存在", "不支持"))))


def poll_task(task_id, base_url, api_key, max_wait) -> dict | None:
    url = f"{base_url}/api/v1/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + max_wait
    while time.time() < deadline:
        resp = httpx.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"Poll error: HTTP {resp.status_code} {resp.text[:200]}", file=sys.stderr)
            return None
        data = resp.json()
        status = (data.get("output") or {}).get("task_status", "")
        if status == "SUCCEEDED":
            return data
        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            msg = (data.get("output") or {}).get("message", "")
            print(f"Task {status}: {msg}", file=sys.stderr)
            return None
        print(f"  [{status}] {time.strftime('%H:%M:%S')} waiting...", file=sys.stderr)
        time.sleep(15)
    print(f"Timed out after {max_wait}s — resume with --task-id {task_id}", file=sys.stderr)
    return None


def download_with_retry(url, max_attempts=3) -> bytes:
    last = None
    for i in range(max_attempts):
        try:
            r = httpx.get(url, timeout=300, follow_redirects=True)
            if r.status_code == 200 and r.content:
                return r.content
            last = f"HTTP {r.status_code}, {len(r.content)}B"
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:120]}"
        print(f"  download attempt {i+1}/{max_attempts} failed: {last}", file=sys.stderr)
        time.sleep(5 * (i + 1))
    print(f"Error: download failed after {max_attempts} attempts: {last}", file=sys.stderr)
    sys.exit(1)


def finish(data, task_id, args, model_used, fallback_note, prompt, params):
    out = data.get("output") or {}
    video_url = out.get("video_url") or ""
    if not video_url:
        results = out.get("results") or []
        video_url = results[0].get("url", "") if results else ""
    if not video_url:
        print(f"Error: no video URL in response: {json.dumps(data)[:500]}", file=sys.stderr)
        sys.exit(1)
    ts = time.strftime("%Y%m%d_%H%M%S")
    if args.output:
        video_path = Path(args.output).expanduser()
    else:
        video_path = Path.home() / ".hermes" / "video_cache" / f"wan3_{ts}.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    print("Downloading video...")
    content = download_with_retry(video_url)
    video_path.write_bytes(content)
    if video_path.stat().st_size < 1024:
        print(f"Error: downloaded file too small ({video_path.stat().st_size}B)", file=sys.stderr)
        sys.exit(1)
    usage = data.get("usage") or {}
    sidecar = {
        "task_id": task_id, "model_requested": args.model, "model_used": model_used,
        "fallback": fallback_note, "prompt": prompt, "parameters": params,
        "usage": usage, "video_url": video_url,
        "submit_time": out.get("submit_time"), "end_time": out.get("end_time"),
        "saved_at": time.strftime("%F %T %z"),
        "file": str(video_path), "bytes": video_path.stat().st_size,
    }
    sidecar_path = video_path.with_suffix(".json")
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=1))
    mb = video_path.stat().st_size / 1024 / 1024
    print(f"Video saved to: {video_path} ({mb:.1f} MB)")
    print(f"Sidecar: {sidecar_path}")
    print(f"Usage: duration={usage.get('duration')}s fps={usage.get('fps')} "
          f"SR={usage.get('SR')} ratio={usage.get('ratio')}")
    if fallback_note:
        print(f"NOTE: {fallback_note}")


def main():
    ap = argparse.ArgumentParser(description="Wan3.0-Video(-Prime) via Token Plan")
    ap.add_argument("--prompt", "-p", default=None)
    ap.add_argument("--model", "-m", default=PRIME, choices=MODELS)
    ap.add_argument("--image", "-i", default=None, help="first frame image")
    ap.add_argument("--last-frame", default=None, help="last frame image")
    ap.add_argument("--ref-image", action="append", help="reference image (repeatable, <=10)")
    ap.add_argument("--ref-video", action="append", help="reference video (repeatable, <=5, total<=15s)")
    ap.add_argument("--ref-audio", action="append", help="reference audio (repeatable, <=5, total<=15s)")
    ap.add_argument("--file", default=None, help="document URL (forces prompt_extend=true)")
    ap.add_argument("--link", default=None, help="web page URL (forces prompt_extend=true)")
    ap.add_argument("--resolution", "-r", default="720P", choices=RESOLUTIONS)
    ap.add_argument("--ratio", default="adaptive", choices=RATIOS)
    ap.add_argument("--duration", "-d", type=int, default=5, help="[2,30] or -1=smart")
    ap.add_argument("--audio", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--prompt-extend", action=argparse.BooleanOptionalAction, default=False)
    ap.add_argument("--watermark", action="store_true", default=False)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--output", "-o", default=None)
    ap.add_argument("--max-wait", type=int, default=1200)
    ap.add_argument("--submit-only", action="store_true")
    ap.add_argument("--task-id", default=None, help="resume polling/download of existing task")
    args = ap.parse_args()

    base_url, api_key = get_config()

    if args.task_id:
        data = poll_task(args.task_id, base_url, api_key, args.max_wait)
        if data is None:
            sys.exit(1)
        finish(data, args.task_id, args, args.model, None, args.prompt, {})
        return

    if not args.prompt:
        ap.error("--prompt is required (unless --task-id)")
    media = build_media(args)
    params = build_parameters(args, media)
    body = {"model": args.model, "input": {"prompt": args.prompt}, "parameters": params}
    if media:
        body["input"]["media"] = media
    mode = "t2v" if not media else "+".join(m["type"] for m in media)
    print(f"Model: {args.model} | mode: {mode} | {args.resolution} {args.ratio} "
          f"{args.duration}s audio={args.audio}")

    result = submit_task(base_url, api_key, body)
    fallback_note = None
    model_used = args.model
    if result["http"] != 200 and args.model == PRIME and model_unavailable(result):
        fallback_note = (f"{PRIME} unavailable here (HTTP {result['http']}: "
                         f"{json.dumps(result['json'], ensure_ascii=False)[:200]}); "
                         f"fell back to {STANDARD}")
        print(f"WARNING: {fallback_note}", file=sys.stderr)
        body["model"] = STANDARD
        model_used = STANDARD
        result = submit_task(base_url, api_key, body)
    if result["http"] != 200:
        print(f"Error: HTTP {result['http']}\n{json.dumps(result['json'], ensure_ascii=False)}",
              file=sys.stderr)
        sys.exit(1)
    task_id = (result["json"].get("output") or {}).get("task_id")
    if not task_id:
        print(f"Error: no task_id: {result['json']}", file=sys.stderr)
        sys.exit(1)
    print(f"Task submitted: {task_id} (model_used={model_used})")
    if args.submit_only:
        print(f"Resume: python3.11 {Path(__file__).resolve()} --task-id {task_id} "
              f"--output <path.mp4>")
        return
    data = poll_task(task_id, base_url, api_key, args.max_wait)
    if data is None:
        sys.exit(1)
    finish(data, task_id, args, model_used, fallback_note, args.prompt, params)


if __name__ == "__main__":
    main()