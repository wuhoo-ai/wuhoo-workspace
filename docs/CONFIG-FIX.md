{
  "status": "success",
  "message": "配置已修正",
  "changes": [
    "agents.list[].tools.allow 已移至 tools 级别（正确位置）",
    "agents.list[].tools.exec.node 保留在 exec 子对象中"
  ],
  "config": {
    "agents": {
      "list": [
        {
          "id": "main",
          "model": "bailian/qwen3.5-plus",
          "workspace": "~/.openclaw/workspace/agents/main",
          "tools": {
            "allow": ["read", "edit", "write", "web_search", "web_fetch", "message"]
          }
        },
        {
          "id": "dev",
          "model": "bailian/qwen3-coder-next",
          "workspace": "~/.openclaw/workspace/agents/dev",
          "tools": {
            "allow": ["read", "edit", "write", "exec"],
            "exec": { "node": "local" }
          }
        },
        {
          "id": "trade",
          "model": "bailian/qwen3.5-plus",
          "workspace": "~/.openclaw/workspace/agents/trade",
          "tools": {
            "allow": ["read", "exec"],
            "exec": { "node": "local" }
          }
        }
      ]
    }
  }
}
