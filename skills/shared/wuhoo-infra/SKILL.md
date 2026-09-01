---
name: wuhoo-infra
description: "Hermes 运维基础设施：RSSHub 恢复、frp 隧道、cron 管理、PDF 微信投递命名规范。Wuhoo 项目通用运维操作手册。"
version: 1.0
tags: ["wuhoo", "infra", "ops"]
category: wuhoo
---

# Wuhoo 基础设施运维

## Hermes 多 Profile 拓扑 (2026-09-01 拆分后)

单 gateway multiplex（default 独占微信+api_server）：default=总控/运维/RSS简报；trader=投资15 cron+wuhoo 投资技能（external_dirs→skills/trader）；gamedev=游戏线+GPU健康cron+Unity MCP（external_dirs→skills/gamedev）。三 profile 统一 [skills/shared, skills/<自身>]。
铁律：
- 次级 profile 的 .env/config **严禁** WEIXIN_* 与 api_server 绑定——multiplex 会整个跳过该 profile（SecondaryPortBindingConfigError）；微信单 token 不可两 profile 共用。
- default 的 `~/.hermes/skills/feeds-lib/` 用 symlink 引 workspace 原件（wuhoo-news-rss/infra/football-predictor），external_dirs 已清空。
- 次级 profile cron 由 default gateway 的 ticker 代跑；`hermes -p X cron status` 显示 "gateway not running" 是误报，以 default 侧为准。
- cron 漂移钉定：drift_skip 报错时 `hermes -p X cron edit <ID> --provider token-plan --model qwen3.8-flash`。
- GPU 健康检查 job 9eb1f08c4100 挂 monitor 脚本 `~/.hermes/scripts/gpu_health_monitor.sh`（确定性分桶输出，状态无变化 0 LLM 唤醒）。
- Dashboard 服务：systemd --user `hermes-dashboard.service`，0.0.0.0:9119，basic auth（配置在 config.yaml dashboard.basic_auth）。
- 回退基线：`config.yaml.bak.split-20260901` / `cron/jobs.json.bak.split-20260901`。
- 重启 gateway 会牵连 Unity MCP 子进程（现挂 gamedev 域）：重启后按下方"GPU 节点"节验证。

## RSSHub 容器恢复

容器 `Up` 但端口不监听（`ss -tlnp | grep 1200` 为空）→ 内部进程崩溃 → 重建容器一次解决：

```bash
podman rm -f rsshub 2>/dev/null; \
podman pull docker.io/diygod/rsshub:latest && \
podman run -d --name rsshub --network host --restart unless-stopped \
  docker.io/diygod/rsshub:latest && \
sleep 8 && curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:1200/
```

验证：重新跑 fetch，Connection Refused 源数应从 19+ → 0。路透社/B站排行榜两个 HTML 非 XML 源是 RSSHub 路由层面的已知问题，不归容器恢复。

**Pitfall**: `podman stop` 可能卡死（conmon exited prematurely），直接用 `podman rm -f` 跳过 stop。容器 Up 但端口不监听 = 内部 Node.js 崩溃，必须重建。
**Pitfall (2026-08-04)**: `podman rm -f rsshub` 在 `;` 串联命令中可能未生效（容器名仍被占用导致 run 失败 "container name already in use"）。rm 后加 `sleep 2` 并确认返回后再 run。重建后失败源应从 19+ → 3（路透社/B站 HTML 非 XML + Stratechery junk 为已知路由问题）。

## FRP 隧道

### 架构

云 Hermes（新加坡）← frp → 杭州 PC（RTX 4070Ti, haijiao-windows）
- frps 端口：`0.0.0.0:7000`（需阿里云安全组开放 TCP 入方向）
- SSH 代理：`*:2222` → PC `127.0.0.1:22`
- Unity MCP 代理：`*:6400` → PC `127.0.0.1:6400`

### 云端 frps 配置

`~/frp/frps.toml`：
```toml
bindPort = 7000
auth.token = "<强随机token>"
```

### 状态检查

```bash
# 进程 + 端口一站式检查
ps aux | grep frp | grep -v grep
ss -tlnp | grep -E '7000|2222|6400'
```

正常输出应显示 frps 进程 + 三个端口全部 LISTEN。

### frps systemd 服务（推荐）

frps 可能静默挂掉（无 crash 日志，疑似 OOM kill）。创建 user systemd 服务实现自动重启：

**1. 创建服务文件** `~/.config/systemd/user/frps.service`：

```ini
[Unit]
Description=FRP Server (frps)
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/frps -c /home/admin/frp/frps.toml
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=append:/home/admin/frp/frps.log
StandardError=append:/home/admin/frp/frps.log

[Install]
WantedBy=default.target
```

**2. 启用并启动**：

```bash
# 允许用户服务在登出后继续运行
sudo loginctl enable-linger admin

# 重载并启动
systemctl --user daemon-reload
systemctl --user enable frps.service
systemctl --user start frps.service
systemctl --user status frps.service
```

**3. 常用管理命令**：

```bash
systemctl --user status frps      # 查看状态
systemctl --user restart frps     # 重启
journalctl --user -u frps -f      # 实时日志
```

**4. 验证隧道恢复**：

杭州端 frpc 配置了自动重连，frps 重启后会自动接上：

```bash
ss -tlnp | grep -E '7000|2222|6400'  # 三个端口都应 LISTEN
ssh -i ~/.ssh/hermes-gpu -p 2222 hermes-agent@localhost "hostname"
# 预期输出: haijiao-windows
```

### 手动重启 frps（无 systemd 时）

```bash
# 必须用 terminal(background=true) — frps 是长驻守护进程
frps -c /home/admin/frp/frps.toml
```

### Pitfalls

1. **frps 静默死亡**：进程消失但 frps.log 无任何错误或 shutdown 记录，根因未确认（可能 OOM kill）。**修复**：systemd `Restart=always` + `RestartSec=10` 自动恢复，杭州端 frpc 自动重连。
2. **端口占用导致 systemd 启动失败**：旧 frps 进程未完全退出时，systemd 会反复 restart 失败。先用 `fuser 7000/tcp` 查占用进程并 `kill`，再 `systemctl --user restart frps`。
3. **SSH 认证**：必须指定 `-i ~/.ssh/hermes-gpu`，默认密钥不匹配 Windows 侧 authorized_keys。
4. frps binary 位置：`/usr/local/bin/frps`（v0.61.0），由 root 安装。

## GPU 节点健康检查

cron 心跳任务：`~/.hermes/guimei-gpu-health.md`（追加，无异常静默 [SILENT]）。

**Pitfall (2026-08-31)**: Windows 新版已移除 `wmic`（"'wmic' 不是内部或外部命令"），磁盘查询改用 PowerShell：
```bash
ssh -i ~/.ssh/hermes-gpu -p 2222 haohaijiao@localhost "powershell -NoProfile -Command \"[math]::Round((Get-PSDrive C).Free/1GB,1)\""
```
其他检查命令：`nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader`（GPU）、`curl -s http://127.0.0.1:8188/system_stats | findstr /i cuda`（ComfyUI）、`sc query frpc | findstr STATE`（应含 RUNNING，被杀 15s 自愈）。

## Gateway 维护陷阱

`hermes gateway restart` 在 gateway 进程内执行被硬阻断（gateway 不能自己杀自己，SIGTERM 会传播）。需从**外部 shell** 执行：

```bash
# 方式1：SSH 登录管理员 shell
ssh admin@主机 "systemctl --user restart hermes-gateway"

# 方式2：等下一会话自动加载新配置（mcp.json 等会在新 turn 时刷新）
```

注意：`hermes desktop` 的 remote gateway 功能通过 API Server（默认端口 8642）连接，需先在云端启用 `api_server` 平台并开放端口。

## Cron 关键任务

| 任务 | 时间 | Job ID |
|------|------|--------|
| RSS 简报推送 | `0 8 * * *` | d6d628cc68a1 |
| WC2026 预测 | 已暂停 | c1e357b05736 |

## PDF 微信投递

命名规范：`/tmp/{YYYYMMDD}_{ISO3}_{ISO3}.pdf`
- ✅ `20260715_FRA_ESP.pdf` — 成功
- ❌ `SF1_FRA_vs_ESP_20260715.pdf` — 多下划线 + 后缀导致静默失败
- ❌ `france-spain.pdf` — 短横线静默失败
- ✅ `sf1.pdf` — 成功但不含日期/球队信息
