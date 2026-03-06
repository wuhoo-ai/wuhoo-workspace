# OpenClaw Agent 配置方案

## 配置概览

基于你的工作需求和现有 model 配置，设计以下 agent 架构：

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenClaw Gateway                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  main-agent  │  │  dev-agent   │  │ trade-agent  │          │
│  │  (qwen3.5-   │  │  (qwen-coder │  │  (待配置)    │          │
│  │   plus/max)  │  │   -next)     │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Shared Skills                         │   │
│  │  web_search | web_fetch | exec | browser | sessions_*   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent 详细配置

### 1. main-agent (主对话代理)

**用途**: 日常对话、讨论、信息检索、个人事务处理

**Model**: `bailian/qwen3.5-plus` (主) / `bailian/qwen3-max-2026-01-23` (备选)

**核心 Skills**:
- `web_search` - 联网检索重要信息
- `web_fetch` - 获取网页内容
- `weather` - 天气查询
- `himalaya` - 邮件管理 (可选)
- `notion` / `obsidian` - 知识管理 (可选)

**工作流集成**:
- TrendRadar 热点推送 → 通过 dingtalk 渠道接收
- 个人事务提醒 → 通过 cron/heartbeat 定时检查

---

### 2. dev-agent (开发代理)

**用途**: 代码编写、调试、审查、重构

**Model**: `bailian/qwen-coder-next` (主) / `bailian/qwen-coder-plus` (备选)

**核心 Skills**:
- `coding-agent` - 代码生成与审查
- `github` - 仓库管理
- `gh-issues` - Issue 追踪
- `tmux` - 远程开发会话

**工作流**:
```
用户请求 → dev-agent → 读取代码 → 分析/修改 → 提交 PR/Commit
                ↓
         (需要时调用)
                ↓
         main-agent (解释说明)
```

---

### 3. trade-agent (量化交易代理)

**用途**: AI-Trader 项目集成，自动化交易决策

**Model**: 待分析 AI-Trader 后确定 (建议 `qwen3.5-plus` 或专用金融模型)

**核心 Skills** (需定制):
- `oracle` - 行情数据查询
- 自定义 skill: `ai-trader-mcp` - 对接 AI-Trader 的 MCP 服务
- 自定义 skill: `trading-tools` - 交易工具封装

**AI-Trader 集成架构**:
```
┌─────────────────────────────────────────────────────────────┐
│                      trade-agent                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   搜索工具   │  │   行情工具   │  │   交易工具   │          │
│  │  (Jina)     │  │ (AlphaVantage)│  │  (MCP Trade) │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         ▼                ▼                ▼                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              AI-Trader BaseAgent                      │   │
│  │  - MCP Client (math, stock_local, search, trade)     │   │
│  │  - LangChain Agent with tool calling                 │   │
│  │  - Position Management                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**MCP 服务端口** (来自 AI-Trader 配置):
- `math`: 8000
- `trade`: 8002
- `stock_local`: 8003
- `search`: 8004

---

### 4. personal-agent (个人事务代理)

**说明**: 与 main-agent 合并，通过任务路由区分

**TrendRadar 集成**:
```
┌─────────────────────────────────────────────────────────┐
│                   TrendRadar                            │
├─────────────────────────────────────────────────────────┤
│  Crawler → Storage → Notification                       │
│                      ↓                                  │
│              (MCP Server)                               │
│                      ↓                                  │
│              main-agent                                 │
│                      ↓                                  │
│              DingTalk 推送                              │
└─────────────────────────────────────────────────────────┘
```

**配置要点**:
- TrendRadar 已支持 MCP Server (`mcp_server/` 目录)
- 可通过 MCP 协议获取热点新闻
- 通知已配置 dingtalk 渠道

---

## 工作流设计

### 工作流 1: 热点资讯 → 交易信号

```
TrendRadar 监控热点
        ↓
  发现关键词匹配 (如 "AI", "芯片", "新能源")
        ↓
  推送至 DingTalk → main-agent 接收
        ↓
  main-agent 分析热点 → 调用 trade-agent
        ↓
  trade-agent 查询相关股票 → AI-Trader MCP 工具
        ↓
  生成交易建议 → 用户确认 → 执行交易
```

### 工作流 2: 代码开发循环

```
用户需求 → main-agent 理解 → 路由至 dev-agent
                              ↓
                    读取代码仓库 → 分析
                              ↓
                    生成修改方案 → 用户确认
                              ↓
                    执行修改 → Commit/PR
                              ↓
                    返回 main-agent → 汇报结果
```

### 工作流 3: 定时交易任务

```
Cron 定时触发 (每小时/每日)
        ↓
  trade-agent 启动交易会话
        ↓
  AI-Trader BaseAgent.run_trading_session()
        ↓
  - 获取昨日持仓
  - 获取今日价格
  - MCP 工具搜索市场新闻
  - LLM 分析决策
  - 执行交易/保持持仓
        ↓
  记录日志 → 推送结果至 DingTalk
```

---

## 配置文件建议

### openclaw.json agents 配置

```json5
{
  "agents": {
    "list": [
      {
        "id": "main",
        "model": "bailian/qwen3.5-plus",
        "tools": {
          "exec": { "allow": ["read", "edit", "write", "web_search", "web_fetch"] }
        },
        "workspace": "~/.openclaw/workspace"
      },
      {
        "id": "dev",
        "model": "bailian/qwen-coder-next",
        "tools": {
          "exec": { 
            "allow": ["read", "edit", "write", "exec"],
            "node": "local"
          }
        },
        "workspace": "~/.openclaw/workspace/Code"
      },
      {
        "id": "trade",
        "model": "bailian/qwen3.5-plus",
        "tools": {
          "exec": {
            "allow": ["read", "exec"],
            "node": "local",
            "allowlist": ["python", "ai-trader-*"]
          }
        },
        "workspace": "~/.openclaw/workspace/Code/AI-Trader"
      }
    ],
    "defaults": {
      "model": { "primary": "bailian/qwen3.5-plus" },
      "workspace": "~/.openclaw/workspace",
      "heartbeat": { "every": "2h" }
    }
  }
}
```

---

## 下一步行动

1. **更新 openclaw.json** - 添加 agents.list 配置
2. **创建 agent 工作区文件** - 为每个 agent 创建 SOUL.md、USER.md 等
3. **配置 TrendRadar MCP** - 启用 MCP Server，对接 main-agent
4. **配置 AI-Trader MCP** - 启动 MCP 服务，创建 trade-agent skill
5. **设置 DingTalk 路由** - 配置消息路由规则
6. **创建 cron 任务** - 定时交易任务和热点检查

---

## 安全注意事项

- **交易权限**: trade-agent 的交易执行需要用户确认 (建议设置审批)
- **API Key 管理**: 所有 API Key 存储在 `~/.openclaw/.env`，不要提交到仓库
- **代码执行**: dev-agent 的 exec 权限限制在 Code 目录
- **消息推送**: DingTalk webhook 妥善保管，不要公开

---

*配置版本：v1.0 | 创建时间：2026-03-01*
