#!/usr/bin/env python3.11
"""产物配对上传器 — 目录规范: <root>/<类型>/<内容>-<YYYYMMDD>/prompt.md + 素材文件。

用法:
  python3.11 upload_deliverable.py --type 视频 --name guimei-ch01-shot02-李章武 \
      --prompt /path/prompt.md --asset /path/shot-02.mp4 [--extra sidecar.json] [--dry-run]

规范（用户 2026-11-17 拍板）: 父文件夹=类型，子文件夹=内容+生产时间，
内部 1 个提示词 md + 1 个素材文件（--extra 可加留证附件）。
提示词与产物必须成对提交，prompt.md 自包含（完整提示词+参数+来源+元数据）。
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PCS = Path(__file__).resolve().parent / "pcs.sh"
DEFAULT_ROOT = "/wuhoo-assets"
TYPES = ("视频", "图片", "音频", "文档")


def run(args, check=True):
    r = subprocess.run(["bash", str(PCS)] + args, capture_output=True, text=True, timeout=1800)
    if check and r.returncode != 0:
        print(f"[FAIL] pcs {' '.join(args[:2])}...\n{r.stdout[-800:]}\n{r.stderr[-800:]}", file=sys.stderr)
        sys.exit(1)
    return r


def ensure_login():
    # BaiduPCS-Go 未登录时 who 仍 rc=0 输出 "uid: 0"——必须解析 uid 数值判非零
    r = run(["who"], check=False)
    m = re.search(r"uid:\s*(\d+)", r.stdout + r.stderr)
    if r.returncode != 0 or not m or int(m.group(1)) == 0:
        print("[未登录] 先运行 scripts/login.sh（凭证文件自建，见技能 SKILL.md）", file=sys.stderr)
        sys.exit(2)


def mkdir_remote(path: str):
    parts = [p for p in path.split("/") if p]
    cur = ""
    for p in parts:
        cur += "/" + p
        r = run(["mkdir", cur], check=False)
        if r.returncode != 0 and "已存在" not in r.stdout + r.stderr and "exist" not in (r.stdout + r.stderr).lower():
            print(f"[FAIL] mkdir {cur}: {r.stdout[-300:]} {r.stderr[-300:]}", file=sys.stderr)
            sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="百度网盘产物配对上传")
    ap.add_argument("--type", required=True, choices=TYPES)
    ap.add_argument("--name", required=True, help="内容 slug，如 guimei-ch01-shot02-李章武")
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--prompt", required=True, help="提示词 md 本地路径（上传后统一命名 prompt.md）")
    ap.add_argument("--asset", required=True, help="素材文件本地路径")
    ap.add_argument("--extra", action="append", default=[], help="附加留证文件（sidecar/接触表等）")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    prompt = Path(args.prompt).expanduser().resolve()
    asset = Path(args.asset).expanduser().resolve()
    extras = [Path(x).expanduser().resolve() for x in args.extra]
    for f in [prompt, asset] + extras:
        if not f.is_file():
            print(f"[FAIL] 文件不存在: {f}", file=sys.stderr)
            sys.exit(1)
    if asset.name == "prompt.md":
        print("[FAIL] 素材文件名不能叫 prompt.md（与提示词冲突）", file=sys.stderr)
        sys.exit(1)

    remote_dir = f"{args.root}/{args.type}/{args.name}-{args.date}"
    print(f"目标: {remote_dir}/")
    print(f"  prompt.md  <- {prompt} ({prompt.stat().st_size/1024:.0f}KB)")
    print(f"  {asset.name}  <- {asset} ({asset.stat().st_size/1024/1024:.1f}MB)")
    for x in extras:
        print(f"  {x.name}  <- {x}")
    if args.dry_run:
        print("[dry-run] 不执行上传")
        return

    ensure_login()
    mkdir_remote(remote_dir)

    stage = Path(tempfile.mkdtemp(prefix="netdisk-stage-", dir=os.path.expanduser("~/.hermes/cache/scratch")))
    try:
        shutil.copy2(prompt, stage / "prompt.md")
        files = [stage / "prompt.md", asset] + extras
        r = run(["upload"] + [str(f) for f in files] + [remote_dir])
        print(r.stdout[-1500:])
        # 验证：ls 目标目录，确认每个文件名在列
        v = run(["ls", remote_dir])
        listing = v.stdout
        missing = [f.name for f in files if f.name not in listing]
        if missing:
            print(f"[FAIL] 上传后 ls 未见: {missing}\n{listing[-800:]}", file=sys.stderr)
            sys.exit(1)
        print(f"[OK] 配对上传完成并验证: {remote_dir}/ ({len(files)} 个文件)")
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    main()