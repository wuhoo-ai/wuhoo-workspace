---
name: wuhoo-game-gpu
description: "Use for GPU node ops: health, MCP, sync, remote env."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, gpu, remote, mcp, frp, ssh, unity-editor]
    related_skills: [wuhoo-game-ci, wuhoo-game-debug, wuhoo-game-scene]
---

# wuhoo-game-gpu — GPU 节点运维

> 合并自: gpu-ops + remote-env + gpu-batch(FUTURE)。
> GPU 节点 = Windows PC (RTX 4070Ti) + Unity Editor + frp 隧道。

## 触发条件

- GPU 节点上线/下线
- MCP 连接断开
- 需要远程 Unity 操作（Author/截图/PlayMode）
- 代码同步（云端→GPU）

## 1. 连接信息

```bash
# SSH 通过 frp 隧道
ssh -i ~/.ssh/hermes-gpu -p 2222 -o ServerAliveInterval=15 haohaijiao@localhost

# 项目路径 (Windows)
cd C:\\Users\\haohaijiao\\miners-watch
```

## 2. 健康检查清单

```bash
# 一键检查
ssh -i ~/.ssh/hermes-gpu -p 2222 haohaijiao@localhost "
  echo '=== SSH ===' && echo OK
  echo '=== Unity ===' && tasklist | findstr Unity
  echo '=== Git ===' && cd C:\Users\haohaijiao\miners-watch && git status --short && git log --oneline -1
  echo '=== frpc ===' && tasklist | findstr frpc
"
```

| 检查项 | 期望 | 失败处理 |
|--------|------|---------|
| SSH 隧道 | 连接成功 | 检查 frpc 服务 / 用户 PC 是否开机 |
| Unity Editor | 进程存在 | 手动启动或 MCP 重连 |
| MCP 连接 | 可执行 read_console | 重启 Unity AI Assistant 插件 |
| Git 工作区 | 干净 + 最新 commit | `git pull --rebase origin v1.1-dev` |
| frpc 自启 | schtasks 已配置 | 重新配置任务计划 |

## 3. 代码同步

```bash
# 云端 push 后，GPU 拉取
ssh -i ~/.ssh/hermes-gpu -p 2222 haohaijiao@localhost \
  "cd C:\Users\haohaijiao\miners-watch && git pull --rebase origin v1.1-dev 2>&1"

# GPU push 后（场景 Author 等），云端拉取
cd /home/admin/miners-watch && git pull --rebase origin v1.1-dev
```

## 4. MCP 操作

```bash
# 读取 Unity Console（编译状态）
# 通过 MCP 工具: read_console

# 截图
# 通过 MCP 工具: capture_screenshot

# 执行菜单命令（Author 场景）
# 通过 MCP 工具: execute_menu_item "Hermes/Author Surface Scene"
```

## 5. 场景 Author（GPU 专属操作）

```
Hermes → Author Surface Scene
Hermes → Author Shallow Cave Scene
Hermes → Author Mid Cave Scene
Hermes → Author Deep Cave Scene
```

Author 后必须 commit + push .unity 文件。

## 6. 用户离开前准备清单

当用户（haohaijiao）要离开 PC 时：
1. 确认 frpc 自启已配置（schtasks）
2. 确认 Unity Editor 保持运行
3. 确认 git 工作区干净
4. 确认 SSH 隧道可连通
5. 关闭显示器但**不关机不休眠**

## 7. 远程环境搭建（新节点）

如需在新 Windows 机器上搭建：
1. 安装 Unity Hub + Unity 6000.5.4f1
2. 安装 Git + 配置 SSH key
3. 安装 frpc + 配置隧道（SSH 端口 2222）
4. 配置 schtasks 自启 frpc
5. 安装 Unity AI Assistant 插件（MCP Bridge）
6. 克隆仓库 + 打开项目
7. 验证: 云端 SSH → MCP read_console → 0 errors

## 8. GPU 批处理任务（FUTURE）

> 当前未启用。GPU 节点空闲时可运行:
> - HeartMuLa 音乐生成
> - Blender headless 3D 建模
> - 批量 AI 生图后处理
>
> 启用条件: 用户明确指示 + 节点空闲 > 2h。
