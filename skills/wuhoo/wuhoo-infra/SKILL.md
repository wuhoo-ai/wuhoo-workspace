---
name: wuhoo-infra
description: "Hermes 运维基础设施：RSSHub 恢复、frp 隧道、cron 管理、PDF 微信投递命名规范。Wuhoo 项目通用运维操作手册。"
version: 1.0
tags: ["wuhoo", "infra", "ops"]
category: wuhoo
---

# Wuhoo 基础设施运维

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
