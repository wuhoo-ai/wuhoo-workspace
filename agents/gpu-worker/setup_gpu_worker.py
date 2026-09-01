# -*- coding: utf-8 -*-
"""GPU gpu-worker profile 配置器(在 GPU 上用 hermes venv python 跑).
用法: python setup_gpu_worker.py <ws_dir>
ws_dir = C:\ai\wuhoo-workspace (解压后的代码包)
"""
import os, sys, shutil, subprocess

WS = sys.argv[1] if len(sys.argv) > 1 else r'C:\ai\wuhoo-workspace'
HERMES_HOME = os.environ.get('GPU_HERMES_ROOT') or os.path.expandvars(r'%LOCALAPPDATA%\hermes')
PROFILE = os.path.join(HERMES_HOME, 'profiles', 'gpu-worker')
import yaml

def hermes_cli(args):
    exe = os.path.join(HERMES_HOME, 'hermes-agent', 'venv', 'Scripts', 'hermes.exe')
    # Windows 下 hermes 输出 UTF-8, 默认 GBK 解码会炸线程 → 显式 utf-8 + replace
    return subprocess.run([exe] + args, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')

# 1) 建 profile(若缺) — 用命令行(无 -p 即 default home)
if not os.path.isdir(PROFILE):
    r = hermes_cli(['profile', 'create', 'gpu-worker', '--clone'])
    print('create rc=', r.returncode, (r.stdout + r.stderr)[-200:])
assert os.path.isdir(PROFILE), 'profile 未建成'

# 2) SOUL
soul_src = os.path.join(WS, 'agents', 'gpu-worker', 'soul.md')
if os.path.exists(soul_src):
    shutil.copy2(soul_src, os.path.join(PROFILE, 'SOUL.md'))
    print('SOUL applied')

# 3) 读 default 配置作底, 重配模型/provider/技能/网关
# Windows 默认 GBK 编码读 UTF-8 的 yaml 会 UnicodeDecodeError → 显式 utf-8
dcfg = yaml.safe_load(open(os.path.join(HERMES_HOME, 'config.yaml'), encoding='utf-8'))
cfg = yaml.safe_load(open(os.path.join(PROFILE, 'config.yaml'), encoding='utf-8'))

cfg['timezone'] = 'Asia/Shanghai'
# 模型栈: 与云端一致的 token-plan(键在 .env)
cfg['model'] = {
    'default': 'qwen3.8-flash',
    'provider': 'token-plan',
}
# 保留 providers 里 token-plan 块(从 default 复制)
if 'providers' in dcfg and 'token-plan' in dcfg['providers']:
    prov = dict(cfg.get('providers') or {})
    prov['token-plan'] = dcfg['providers']['token-plan']
    cfg['providers'] = prov
cfg['fallback_providers'] = []
cfg['delegation'] = {'model': 'qwen3.8-max', 'provider': 'token-plan', 'reasoning_effort': 'max'}
# auxiliary 全部指向 token-plan/qwen3.8-flash 不思考(照云端模式, 从 default 复制改 provider)
if 'auxiliary' in dcfg:
    aux = dcfg['auxiliary']
    for k in aux:
        if isinstance(aux[k], dict):
            aux[k]['provider'] = 'token-plan'
            aux[k]['model'] = 'qwen3.8-flash'
            eb = aux[k].setdefault('extra_body', {})
            eb['reasoning'] = {'enabled': False}
    cfg['auxiliary'] = aux

# 技能: 只挂 workspace 域目录
cfg['skills'] = dict(cfg.get('skills') or {})
cfg['skills']['external_dirs'] = [
    os.path.join(WS, 'skills', 'shared'),
    os.path.join(WS, 'skills', 'gamedev'),
]
cfg['skills']['disabled'] = []

# 网关: gpu-worker 独立网关自绑 api_server(GPU 不开 multiplex, 不碰桌面版 default)
gw = dict(cfg.get('gateway') or {})
gw['platforms'] = {'api_server': {'enabled': True, 'host': '0.0.0.0', 'port': 8642}}
gw.pop('home_channel', None)
cfg['gateway'] = gw

with open(os.path.join(PROFILE, 'config.yaml'), 'w', encoding='utf-8') as f:
    yaml.dump(cfg, f, allow_unicode=True, sort_keys=False)
print('config written')

# 4) .env: 注入 TOKEN_PLAN_API_KEY / API_SERVER_KEY(GPU 本机 api_server 鉴权), 清 weixin
from pathlib import Path
envp = Path(PROFILE) / '.env'
lines = []
if envp.exists():
    lines = [l for l in envp.read_text(encoding='utf-8').splitlines() if not l.startswith(('WEIXIN_', 'API_SERVER_'))]
envf = Path(HERMES_HOME) / '.env'
denv = {}
for l in envf.read_text(encoding='utf-8').splitlines():
    if '=' in l and not l.strip().startswith('#'):
        k, v = l.split('=', 1)
        denv[k] = v
inject = {
    'TOKEN_PLAN_API_KEY': denv.get('TOKEN_PLAN_API_KEY', ''),
    'API_SERVER_ENABLED': 'true',
    'API_SERVER_KEY': open(os.path.join(HERMES_HOME, 'deploy', 'gpu_api_key.txt')).read().strip(),
}
# GPU 默认 .env 可能没有 token-plan key → 回退读部署包
if not inject['TOKEN_PLAN_API_KEY']:
    alt = os.path.join(r'C:\ai\deploy', 'token_plan_key.txt')
    if os.path.exists(alt):
        inject['TOKEN_PLAN_API_KEY'] = open(alt).read().strip()
        print('token_plan key 取自部署包回退文件')
for k, v in inject.items():
    if v:
        lines.append(f'{k}={v}')
envp.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('env written')

# 5) peer cloud 注册(GPU→云端 default 的 8642, key=云端 default 的)
ckey = open(os.path.join(HERMES_HOME, 'deploy', 'cloud_api_key.txt')).read().strip()
r = hermes_cli(['-p', 'gpu-worker', 'peer', 'add', 'cloud', '--url', 'http://47.79.255.24:8642', '--key', ckey])
print('peer add rc=', r.returncode, (r.stdout + r.stderr)[-160:])
print('== GPU_SETUP_PY_DONE ==')
