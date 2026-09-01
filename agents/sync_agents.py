#!/usr/bin/env python3.11
"""agents/sync_agents.py — profile 运行时资产 ↔ wuhoo-workspace/agents/ 双向同步.

pull (默认, 夜间 cron 跑): profile home → 仓库. 有 diff 则 git commit + push.
  - SOUL.md → agents/<p>/soul.md
  - cron jobs.json → agents/<p>/cron.json  (剥运行时字段: 状态/时间戳/告警位, 只留声明式定义)
  - scripts 白名单 → agents/<p>/scripts/
apply (手动, 跨机部署/回滚): 仓库 → profile home. SOUL+scripts 覆盖; cron 只打印 diff 供人工/hermes cron edit.
"""
import argparse, difflib, json, os, shutil, subprocess, sys

WS = '/home/admin/wuhoo-workspace'
AG = f'{WS}/agents'
HOMES = {
    'default': '/home/admin/.hermes',
    'trader': '/home/admin/.hermes/profiles/trader',
    'gamedev': '/home/admin/.hermes/profiles/gamedev',
    'gpu-worker': f'{WS}/agents/gpu-worker.template',  # apply-only: GPU 机上的 gpu-worker
}
RUNTIME_KEYS = {'last_run_at', 'last_status', 'last_error', 'next_run_at', 'failure_streak',
                'fire_claim', 'drift_alerted', 'last_delivery_error', 'state', 'paused_at',
                'paused_reason', 'created_at', 'run_count', 'last_context_hash',
                'monitor_last_hash', 'notepad', 'execution_id'}
# continuity / monitor_script / script 等声明性字段保留(曾因此被剥掉)
SCRIPTS_ALLOW = {
    'default': [],
    'trader': ['check_cn_trading_day.py', 'check_us_trading_day.py'],
    'gamedev': ['gpu_health_monitor.sh'],
    'gpu-worker': [],
}

def shell(cmd, cwd=WS):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()

def clean_jobs(path):
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    jobs = d if isinstance(d, list) else d.get('jobs', [])
    out = []
    for j in jobs:
        out.append({k: v for k, v in sorted(j.items()) if k not in RUNTIME_KEYS})
    return json.dumps(out, ensure_ascii=False, indent=2) + '\n'

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def pull():
    changed = []
    for prof, home in HOMES.items():
        if prof == 'gpu-worker' or not os.path.isdir(home):
            continue
        dst = f'{AG}/{prof}'
        ensure_dir(dst)
        ensure_dir(f'{dst}/scripts')
        # SOUL
        src = f'{home}/SOUL.md'
        if os.path.exists(src):
            shutil.copy2(src, f'{dst}/soul.md')
        # cron (剥离运行时字段)
        cj = clean_jobs(f'{home}/cron/jobs.json')
        if cj is not None:
            with open(f'{dst}/cron.json', 'w') as f:
                f.write(cj)
        # scripts 白名单
        for s in SCRIPTS_ALLOW.get(prof, []):
            sp = f'{home}/scripts/{s}'
            if os.path.exists(sp):
                shutil.copy2(sp, f'{dst}/scripts/{s}')
    rc, out = shell('git add agents/ && git status --porcelain agents/')
    if out.strip():
        shell(f'git commit -m "agents snapshot $(date +%F)" && git push origin HEAD')
        print('committed+pushed:\n', out[:500])
    else:
        print('agents/ no change')

def apply(prof):
    src = f'{AG}/{prof}'
    # GPU 机部署: 先 export HERMES_APPLY_HOME=<该机 profile home> 再 apply(云上默认走 HOMES 表)
    home = os.environ.get('HERMES_APPLY_HOME') or HOMES.get(prof)
    if not os.path.isdir(src):
        sys.exit(f'no agents/{prof} in repo')
    if not home or not os.path.isdir(home):
        sys.exit(f'unknown/missing home for {prof} (set HERMES_APPLY_HOME on remote boxes)')
    print(f'== apply {prof} -> {home} ==')
    if os.path.exists(f'{src}/soul.md'):
        shutil.copy2(f'{src}/soul.md', f'{home}/SOUL.md')
        print('SOUL.md applied')
    for f in os.listdir(f'{src}/scripts') if os.path.isdir(f'{src}/scripts') else []:
        ensure_dir(f'{home}/scripts')
        shutil.copy2(f'{src}/scripts/{f}', f'{home}/scripts/{f}')
        os.chmod(f'{home}/scripts/{f}', 0o755)
        print(f'scripts/{f} applied')
    if os.path.exists(f'{src}/cron.json'):
        cur = clean_jobs(f'{home}/cron/jobs.json') or '[]'
        new = open(f'{src}/cron.json').read()
        if cur == new:
            print('cron.json 与本机一致')
        else:
            print('!! cron 定义有差异, 手动合并(声明式, 勿整文件覆盖运行中的库):')
            for line in difflib.unified_diff(cur.splitlines(), new.splitlines(),
                                             'local', 'repo', lineterm='', n=1):
                print(line[:140])

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['pull', 'apply'])
    ap.add_argument('--profile', default='default')
    a = ap.parse_args()
    pull() if a.action == 'pull' else apply(a.profile)
