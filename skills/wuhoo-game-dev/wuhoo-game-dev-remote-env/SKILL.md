---
name: wuhoo-game-dev-remote-env
description: "Unity 远程开发环境搭建 — Windows GPU 节点通过 frp 隧道连接云 Hermes，配置 SSH 免密、Unity Editor、AI Assistant MCP Bridge，使 Hermes 可远程操作 Unity 场景/编译/调试。触发：用户提及 GPU 节点、远程 Unity、MCP 接入、frp 隧道、Windows SSH 搭建。"
version: 1.0.0
author: Wuhoo
tags: [wuhoo, game-dev, unity, gpu-node, mcp, remote-dev, frp, ssh]
category: wuhoo
metadata:
  hermes:
    related_skills: [wuhoo-game-dev-gpu-batch, wuhoo-game-dev-code-from-task, wuhoo-game-dev-daily-build]
---

# Unity 远程开发环境搭建

在 Windows GPU 节点（杭州住宅）与云 Hermes（新加坡）之间建立 frp 隧道 + SSH + Unity MCP 全链路。

## 架构

```
云 Hermes (新加坡, 无GPU)        Windows GPU 节点 (杭州, RTX 4070Ti)
┌──────────────────────┐  frp   ┌──────────────────────────────┐
│ Hermes Agent         │◄──────►│ Unity Editor (haohaijiao)     │
│ config.yaml          │ 隧道    │   → MCP Bridge (IPC)         │
│  mcp_servers:        │        │   → relay_win.exe --mcp      │
│   → ssh → relay.exe  │        │      (stdio, 同用户运行)       │
└──────────────────────┘        └──────────────────────────────┘
```

**关键约束**：relay `--mcp` 模式使用标准 MCP JSON-RPC（stdio），是 Hermes 原生 MCP 客户端唯一支持的 Unity 连接方式。但 relay 的 IPC 通道是 Windows 用户隔离的——必须以 Unity 同一用户（haohaijiao）运行。`--relay` 模式使用自定义 WebSocket 协议，不是标准 MCP，Hermes 无法对接（会收到 `RELAY_UNKNOWN_MESSAGE_TYPE`）。

## Phase 1: frp 隧道

### 云端 (frps)

```bash
# 下载 frp v0.61.0+
frps --version
# 配置 ~/frp/frps.toml:
# bindPort = 7000
# auth.token = "<强随机token>"
frps -c ~/frp/frps.toml  # 后台运行
```

### 杭州 PC (frpc)

frpc.toml 模板：
```toml
serverAddr = "<云公网IP>"
serverPort = 7000
auth.token = "<相同token>"

[[proxies]]
name = "ssh"
type = "tcp"
localIP = "127.0.0.1"
localPort = 22
remotePort = 2222

[[proxies]]
name = "unity-mcp"
type = "tcp"
localIP = "127.0.0.1"
localPort = 6400
remotePort = 6400
```

**⚠️ 阿里云安全组**：需要在控制台开放入方向 TCP 7000 端口。

## Phase 2: Windows SSH 配置

### 用户名密码创建

```powershell
# % 在 cmd/powershell 中有特殊含义，密码必须用双引号包裹！
net user hermes-agent "H%emersAgent" /add /active:yes /passwordchg:no /expires:never
net localgroup administrators hermes-agent /add
```

### OpenSSH 配置陷阱

**陷阱 1：`Match Group administrators` 块覆盖全局配置**

Windows sshd_config 底部有：
```
Match Group administrators
    AuthorizedKeysFile __PROGRAMDATA__/ssh/administrators_authorized_keys
```

这个块内的设置会**覆盖**全局的同名设置。必须在此块内显式开启：
```
Match Group administrators
    AuthorizedKeysFile .ssh/authorized_keys
    PubkeyAuthentication yes
    PasswordAuthentication yes    # ← 容易漏！
```

**陷阱 2：公钥文件位置**

`hermes-agent` 是管理员 → 公钥放 `C:\Users\hermes-agent\.ssh\authorized_keys`（非 `C:\ProgramData\ssh\administrators_authorized_keys`，前提是 Match 块内改成了 `.ssh/authorized_keys`）。

**陷阱 3：跨用户 Unity 操作**

Hermes 通过 `hermes-agent` SSH 登录，但 Unity Editor 由 `haohaijiao` 运行。IPC 命名管道是用户隔离的 → relay 用 `--mcp` 模式（stdio IPC）找不到 Unity 进程。

**解决方案**：为 `haohaijiao` 配置 SSH 密钥（见 Phase 4），让 Hermes 通过 `ssh haohaijiao@localhost relay_win.exe --mcp` 以 Unity 同一用户运行 relay。注意：`--relay` 模式（TCP）看似可跨用户，但使用自定义协议而非标准 MCP，Hermes 原生客户端无法对接（返回 `RELAY_UNKNOWN_MESSAGE_TYPE`）。

**陷阱 4：`.ssh` 目录/文件权限过宽导致公钥认证被拒**

Windows OpenSSH 严格要求 `.ssh` 目录和 `authorized_keys` 文件的权限——只能由**用户自己**和 **SYSTEM** 访问。若 `BUILTIN\Administrators` 有权限（即使该用户本人就是管理员），SSH 会拒绝公钥认证且不给出明确错误信息。

修复：
```powershell
# 移除 Administrators 组对 .ssh 目录的权限
icacls C:\Users\haohaijiao\.ssh /remove:g Administrators
# 确保 authorized_keys 也只有 haohaijiao + SYSTEM
icacls C:\Users\haohaijiao\.ssh\authorized_keys /inheritance:r /grant:r haohaijiao:F /grant:r SYSTEM:F
```

检查当前权限：`icacls C:\Users\haohaijiao\.ssh` 和 `icacls C:\Users\haohaijiao\.ssh\authorized_keys`

### 云→PC SSH 免密

```bash
# 云端生成密钥
ssh-keygen -t ed25519 -f ~/.ssh/hermes-gpu -N ""
# 复制公钥到 PC（先用密码登录一次）
sshpass -p '<密码>' ssh-copy-id -i ~/.ssh/hermes-gpu.pub -p 2222 hermes-agent@localhost
# 或手动追加到 Windows 侧 authorized_keys
```

配置 `~/.ssh/config` 别名：
```
Host gpu
    HostName localhost
    Port 2222
    User hermes-agent
    IdentityFile ~/.ssh/hermes-gpu
    StrictHostKeyChecking accept-new
```

## Phase 3: Unity 环境

### 版本匹配

检查 `ProjectSettings/ProjectVersion.txt`：
```
m_EditorVersion: 6000.5.4f1   # 必须匹配安装的 Editor 版本
```

若 Editor 版本比项目新 → 编辑此文件升级版本号即可。

### 包版本兼容性

**Unity 6000.5 废弃了 `TreeView`/`TreeViewItem`/`TreeViewState` 旧 API**。

若导入时大量 `CS0619`（obsolete）错误，检查 `Packages/manifest.json`：
- `com.unity.inputsystem`: 1.7.0 → **1.11.2**（最低版本）
- `com.unity.render-pipelines.universal`: 需匹配 Unity 6 最新

改 manifest.json 后 Unity 自动重新解析并下载新包版本。

## Phase 4: Unity MCP Relay

### relay 双模式说明

| 模式 | 协议 | 传输 | Hermes 兼容 |
|------|------|------|-------------|
| `--relay` | 自定义 relay 协议 | TCP WebSocket | ❌ 返回 `RELAY_UNKNOWN_MESSAGE_TYPE` |
| `--mcp` | 标准 MCP JSON-RPC | stdio | ✅ 原生支持 |

**⚠️ `--mcp` 模式约束**：relay 通过 IPC（named pipe）与 Unity MCP Bridge 通信，IPC 是 **Windows 用户隔离** 的。必须以 Unity 同一用户（`haohaijiao`）运行，不能跨用户（如 `hermes-agent`）。

### 确认包已安装

`Packages/manifest.json` 中必须有：
```json
"com.unity.ai.assistant": "2.15.0-pre.1"
```

### Unity Editor 侧

1. **Edit → Project Settings → AI → Unity MCP**
2. 确认 Bridge 状态 **Running**（绿色）
3. relay 路径：`C:\\Users\\haohaijiao\\.unity\\relay\\relay_win.exe`

### haohaijiao SSH 密钥配置（必须）

> **⚠️ hermes-agent（管理员）也无法跨用户修改 haohaijiao 的文件**（Windows UAC 权限隔离）。此步只能由 **haohaijiao 本人在 PC 桌面手动操作**。

将云端的公钥追加到 `C:\Users\haohaijiao\.ssh\authorized_keys`：

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIABf+nQYfb39xx0P0pNcT2qPGRvyQ/qPnWWbUbiGeOSG admin@iZt4n2wdvn39ky2rq7pm7fZ
```

验证 SSH 连通：
```bash
ssh -i ~/.ssh/hermes-gpu -p 2222 haohaijiao@localhost "hostname"
# 预期输出: haijiao-windows
```

### 云端 MCP 配置

**⚠️ Hermes native MCP 配置在 `config.yaml` 的 `mcp_servers` 键下，不是独立的 `mcp.json` 文件。**

`~/.hermes/config.yaml`：
```yaml
mcp_servers:
  unity:
    command: "ssh"
    args:
      - "-i"
      - "/home/admin/.ssh/hermes-gpu"
      - "-p"
      - "2222"
      - "haohaijiao@localhost"
      - "C:\\Users\\haohaijiao\\.unity\\relay\\relay_win.exe"
      - "--mcp"
    timeout: 180
    connect_timeout: 30
```

或使用 CLI：
```bash
hermes mcp add unity \
  --command ssh \
  --args "-i" "/home/admin/.ssh/hermes-gpu" "-p" "2222" "haohaijiao@localhost" "C:\\Users\\haohaijiao\\.unity\\relay\\relay_win.exe" "--mcp"
```

### 首次连接审批

Hermes 首次连接时，Unity Editor → **Edit → Project Settings → AI → Unity MCP** 页面会出现 **Pending Connection**，需点击 **Approve**。审批后自动信任，后续连接无需重复审批。

### MCP 状态检查

```bash
hermes mcp list          # 列出已配置的 MCP 服务器
hermes mcp test unity    # 测试 Unity MCP 连接
```

## 连接 Hermes Desktop

Windows 安装 Hermes Desktop 后可通过配对码连接云端同一 Agent 实例：

1. [下载](https://hermes-agent.nousresearch.com/) 安装
2. 生成配对码 → 发到微信
3. 云端：`hermes pairing approve <code>`
4. 桌面 App 成为云端 Agent 的前端

**Remote Gateway 直连**（替代方案）：桌面 App → Settings → Remote Gateway，填：
- URL: `http://47.79.255.24:8642`（API Server 默认端口 8642，需云端启用 `api_server` 平台并开放端口）
- API Server 端口定义在 `gateway/platforms/api_server.py` 的 `DEFAULT_PORT = 8642`

## 已验证的完整环境

| 项目 | 值 |
|------|-----|
| 云 OS | Alibaba Cloud Linux 8 (RHEL-like) |
| GPU | RTX 4070 Ti / 12GB / driver 610.62 |
| Windows | Windows 11 Pro (10.0.26200) |
| OpenSSH | OpenSSH_for_Windows_9.5 |
| Unity | 6000.5.4f1 (Personal License) |
| relay | unity-ai-relay v1.0.12-build.97 |
| AI Assistant | com.unity.ai.assistant@2.15.0-pre.1 |
| frp | v0.61.0 |
| 工程路径 | `C:\Users\haohaijiao\miners-watch` |

## Pitfalls

1. `%` 字符在 cmd 中特殊 → 密码须用双引号包裹，`net user` 创建时注意
2. `Match Group administrators` 块内需显式配置所有认证选项，否则全局配置被覆盖
3. **relay `--relay` ≠ 标准 MCP**：`--relay` 模式使用自定义 relay 协议（非 MCP JSON-RPC），Hermes 原生 MCP 客户端发送标准 MCP 消息会收到 `RELAY_UNKNOWN_MESSAGE_TYPE`。**必须用 `--mcp` 模式**（stdio）。
4. **relay `--mcp` 不能跨 Windows 用户**：IPC（named pipe）是用户隔离的。必须以 Unity 同一用户（`haohaijiao`）运行 relay。需要为 haohaijiao 配置 SSH 密钥（**只能在 PC 桌面手动操作**，hermes-agent 管理员也无法跨用户写文件）。
5. **MCP 配置在 `config.yaml`，不是 `mcp.json`**：`hermes mcp add` CLI 或直接编辑 `~/.hermes/config.yaml` 的 `mcp_servers` 键。独立 `mcp.json` 不会被原生 MCP 客户端读取。
6. gateway 无法从内部重启（SIGTERM 传播），改 mcp 配置后需等待下一会话或用外部 shell 重启
7. `serivices.unity.com` DNS 错误是 Unity 代码中的拼写错误（应为 `services`），不影响编译，可忽略
8. 远程编辑 manifest.json 时，cmd `echo` 单引号比双引号更可靠（避免转义问题）。PowerShell `Get-Content -replace` 链在 SSH 远程调用时转义极易出错 → 直接 `echo` 覆写整个文件更可靠。
9. Unity batchmode 需要完整的用户配置文件路径（`AppData/Local/Unity/Caches`），用 `hermes-agent` 用户跑 batchmode 会因缺少这些目录而失败 → batchmode 只适合在桌面用户（haohaijiao）的会话中运行。
10. `hermes gateway restart` 在 gateway 进程内被硬阻断（gateway 不能自己杀自己），只能用外部 shell（SSH 登录 admin@主机 后执行）或等下一会话自动加载新配置。
11. **haohaijiao SSH 密钥添加**：Windows UAC 下管理员也无法跨用户修改文件。公钥内容需发给用户手动追加到 `C:\\Users\\haohaijiao\\.ssh\\authorized_keys`。
12. **`.ssh` 目录/文件继承权限导致公钥认证静默失败**：`.ssh` 和 `authorized_keys` 通常会从父目录继承 `BUILTIN\\Administrators` 的 FullControl。仅 `/remove:g` 不够——权限会随继承刷新回来。必须 **`/inheritance:r` 先清除继承**，再 `/grant:r` 只授予 haohaijiao+SYSTEM。且 `icacls` 必须在 **cmd** 中运行，PowerShell 会误将 `(F)` 解析为命令。
13. **`authorized_keys` UTF-16 LE 编码陷阱**：Windows 记事本默认保存为 UTF-16 LE（BOM=`FF FE`），OpenSSH 只认 UTF-8/ASCII。用 `[System.IO.File]::WriteAllText` 配合 `UTF8Encoding($false)` 写无 BOM UTF-8。验证：`Format-Hex` 看开头是否为 `73 73 68`（s s h）而非 `FF FE`。
