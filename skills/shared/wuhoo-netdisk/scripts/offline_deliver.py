#!/usr/bin/env python3.11
"""offline_deliver.py — 百度网盘离线下载入库（跨境上传阻断的替代通道）。

原理：SG 服务器把素材布点到 nginx /media-temp/<token>/ 临时 HTTPS 链接，
调百度 cloud_dl API 让百度服务器回源下载（百度→SG 下载方向不受跨境上传 policing 限制），
直接落到网盘目标目录（可一步到位配对目录）。

用法：
  python3.11 offline_deliver.py --url https://host/media-temp/<token>/a.mp4 \
      --save-path /wuhoo-assets/视频/xxx-20261118 --name a.mp4 --size 45600213 \
      [--timeout 900] [--interval 5]

退出码：0=成功且落盘验证通过；2=任务失败/验证不符；3=超时；4=凭证/登录问题。
凭证只从 ~/.config/baidupcs/credentials.env 读取（0600 强制），永不打印值。
"""
import argparse
import json
import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path

import httpx

PCS = str(Path.home() / 'wuhoo-workspace/skills/shared/wuhoo-netdisk/scripts/pcs.sh')
CRED = Path.home() / '.config/baidupcs/credentials.env'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
BASE = 'https://pan.baidu.com/rest/2.0/services/cloud_dl'
META_SIZE_RE = re.compile(r'(?:文件大小|size)\s*[:：]?\s*(\d+)', re.I)


def load_cookies():
    if not CRED.exists():
        print('[凭证] 缺少 ~/.config/baidupcs/credentials.env，先运行 scripts/login.sh', file=sys.stderr)
        sys.exit(4)
    mode = stat.S_IMODE(CRED.stat().st_mode)
    if mode != 0o600:
        print(f'[凭证] 权限 {oct(mode)} 非 600，拒绝执行（chmod 600 后重试）', file=sys.stderr)
        sys.exit(4)
    vals = {}
    for line in CRED.read_text().splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            vals[k.strip()] = v.strip()
    if not vals.get('BDUSS'):
        print('[凭证] credentials.env 缺 BDUSS', file=sys.stderr)
        sys.exit(4)
    cookies = {'BDUSS': vals['BDUSS']}
    if vals.get('STOKEN'):
        cookies['STOKEN'] = vals['STOKEN']
    return cookies


def pcs_ls(path):
    r = subprocess.run(['bash', PCS, 'ls', path], capture_output=True, text=True, timeout=90)
    return r.stdout + r.stderr


def main():
    ap = argparse.ArgumentParser(description='百度离线下载入库')
    ap.add_argument('--url', required=True, help='素材 HTTPS 直链（百度服务器可回源）')
    ap.add_argument('--save-path', required=True, help='网盘目标目录（绝对路径）')
    ap.add_argument('--name', help='期望落盘文件名（默认取 URL 末段）')
    ap.add_argument('--size', type=int, help='期望字节数（落盘验证用）')
    ap.add_argument('--timeout', type=int, default=900, help='轮询超时秒数')
    ap.add_argument('--interval', type=int, default=5, help='轮询间隔秒数')
    args = ap.parse_args()
    name = args.name or args.url.rstrip('/').rsplit('/', 1)[-1]

    cookies = load_cookies()
    s = httpx.Client(cookies=cookies, timeout=30, follow_redirects=True,
                     headers={'User-Agent': UA, 'Referer': 'https://pan.baidu.com/disk/home',
                              'Accept-Encoding': 'identity'})  # 百度偶发损坏gzip响应致DecodingError，identity绕开
    r = s.get('https://pan.baidu.com/api/gettemplatevariable',
              params={'clienttype': 0, 'app_id': 250528, 'web': 1,
                      'fields': json.dumps(['bdstoken'])})
    try:
        bdstoken = r.json()['result']['bdstoken']
    except Exception:
        print('[登录] gettemplatevariable 失败（BDUSS 可能过期）:', r.text[:200])
        sys.exit(4)
    if not bdstoken:
        print('[登录] bdstoken 为空，BDUSS 可能过期，重跑 login.sh')
        sys.exit(4)
    common = {'app_id': 250528, 'bdstoken': bdstoken, 'clienttype': 0, 'web': 1}

    # 1) add_task
    r = s.get(BASE, params={**common, 'method': 'add_task',
                            'save_path': args.save_path, 'source_url': args.url})
    j = r.json()
    print('[add_task]', json.dumps(j, ensure_ascii=False))
    task_id = j.get('task_id')
    if not task_id:
        print('[失败] add_task 未返回 task_id')
        sys.exit(2)

    # 2) 轮询 query_task（API 返回字符串，必须 int 转换）
    deadline = time.time() + args.timeout
    ti = {}
    outcome = 'timeout'
    polls = 0
    while time.time() < deadline:
        time.sleep(args.interval)
        polls += 1
        r = s.get(BASE, params={**common, 'method': 'query_task',
                                'task_ids': str(task_id), 'op_type': 1})
        q = r.json()
        ti = (q.get('task_info') or {}).get(str(task_id), {})
        fs = int(ti.get('file_size') or 0)
        fin = int(ti.get('finished_size') or 0)
        st = int(ti.get('status') if ti.get('status') is not None else -1)
        if polls % 6 == 0:
            print(f'[poll{polls}] status={st} {fin}/{fs}B', flush=True)
        if args.size and fs > 0 and fs != args.size:
            outcome = 'failed'
            print(f'[失败] 回源尺寸不符 poll{polls}: file_size={fs} 期望={args.size}（错误页/假完成）')
            break
        if st == 0 and fs > 0 and fin >= fs:
            outcome = 'success'
            print(f'[完成] status=0 字节达标 poll{polls}: {fin}/{fs}')
            break
        if st == 0 and polls >= 3:
            outcome = 'success'
            print(f'[完成] status=0 完成态 poll{polls}')
            break
        if st >= 3:
            outcome = 'failed'
            print(f'[失败] 终态 status={st} poll{polls}:', json.dumps(ti, ensure_ascii=False)[:400])
            break
    if outcome == 'timeout':
        print(f'[超时] {args.timeout}s 未完成，task_id={task_id} 可稍后手动 query_task')
        print('[最后状态]', json.dumps(ti, ensure_ascii=False)[:400])
        sys.exit(3)
    if outcome == 'failed':
        sys.exit(2)

    # 3) 落盘验证：ls 目标目录，文件名+大小为准（不迷信 md5，百度端记录可能有 bug）
    time.sleep(3)
    out = pcs_ls(args.save_path)
    print('[ls 验证]\n' + out)
    ok_name = name in out
    ok_size = True
    if args.size:
        # pcs ls 人类可读大小（KB/MB）仅作粗校验；精确校验用 meta 的 size 字段
        r = subprocess.run(['bash', PCS, 'meta', f'{args.save_path}/{name}'],
                           capture_output=True, text=True, timeout=90)
        meta = r.stdout + r.stderr
        m = META_SIZE_RE.search(meta)
        if m:
            ok_size = int(m.group(1)) == args.size
            print(f'[meta] size={m.group(1)} 期望={args.size} -> {"PASS" if ok_size else "FAIL"}')
        else:
            print('[meta] 未解析到精确字节数，原始输出：\n' + meta[:600])
            ok_size = ok_name  # 退化为存在性校验
    if ok_name and ok_size:
        print(f'[结果] SUCCESS task_id={task_id} -> {args.save_path}/{name}')
        sys.exit(0)
    print(f'[结果] VERIFY-FAIL name_ok={ok_name} size_ok={ok_size}')
    sys.exit(2)


if __name__ == '__main__':
    main()
