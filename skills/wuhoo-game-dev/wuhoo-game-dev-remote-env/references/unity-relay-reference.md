# Unity AI Relay 命令行参考

```
Unity AI Relay Server (unity-ai-relay v1.0.12-build.97)

USAGE:
    relay --relay [OPTIONS]       Start relay server (TCP)
    relay --mcp [OPTIONS]         Start MCP server (stdio)
    relay --version               Show version information
    relay --help                  Show this help message

RELAY MODE OPTIONS:
    --port, -p <number>           WebSocket port (default: 9001)
    --mcp-client-port <number>    MCP client REST API port (default: 9002)
    --editor-pid <string>         Unity Editor process ID (default: 'unknown')
    --shutdown-delay <seconds>    Auto-shutdown delay (default: 120)

MCP MODE OPTIONS:
    --name <string>               Custom MCP server name
    --project-path <path>         Connect to Unity instance with this project path
    --instance-id <pid>           Connect to Unity instance with this editor PID

COMMON OPTIONS:
    --debug                       Enable debug logging
    --log, -l <level>             Log level: debug, info, error (default: info)
    --log-dir <path>              Log output directory (default: ./Logs)
```

## 两种模式的选择

| 模式 | 传输 | 适用场景 | 跨用户? |
|------|------|---------|:---:|
| `--mcp` | stdio | 同一用户本地运行 relay + Unity | ❌ |
| `--relay` | WebSocket | Hermes 远程连接跨用户 Unity 节点 | ✅ |

## 已验证工作命令

```powershell
# 在 Windows 桌面 (haohaijiao) 启动 relay TCP
& "C:\Users\haohaijiao\.unity\relay\relay_win.exe" --relay --port 6400 --mcp-client-port 6401
```

云端 Hermes 通过 frp → localhost:6400 连接。

## MCP 工具列表

首次连接审批后，Hermes 可获得以下 Unity MCP 工具：
- Unity_ManageScene
- Unity_ManageGameObject
- Unity_ReadConsole
- Unity_ManageAsset
- 及项目自定义 `[McpTool]` 工具
