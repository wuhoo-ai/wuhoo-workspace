# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenClaw configuration repository for a multi-agent AI system focused on quantitative trading and information management.

### Core Agents

| Agent | Model | Purpose | Workspace |
|-------|-------|---------|-----------|
| **main-agent** | bailian/qwen3.5-plus | Daily assistant, information retrieval, task routing | `workspace/agents/main/` |
| **dev-agent** | bailian/qwen3-coder-next | Code generation, review, debugging (via coding-agent) | `workspace/agents/dev/` |
| **trade-agent** | bailian/qwen3.5-plus | Quantitative trading, market analysis, risk management | `workspace/agents/trade/` |
| **debate-agent** | - | Multi-agent debate for stock analysis | `workspace/agents/debate/` |

## Architecture

```
~/.openclaw/
├── openclaw.json              # Main configuration (models, agents, channels, plugins)
├── .env                       # Environment variables (API keys, secrets)
├── scripts/                   # Utility scripts (backup, heartbeat, testing)
├── skills/                    # Custom skills (symlinks to .agents/skills/)
├── extensions/                # Plugin extensions
│   ├── openclaw-china/       # Channels plugin (DingTalk, WeCom)
│   └── openclaw-weixin/      # WeChat integration
├── workspace/
│   ├── agents/               # Agent workspaces (main, dev, trade, debate)
│   └── projects/             # External projects
│       ├── AI-Trader/        # Quantitative trading system
│       └── TrendRadar/       # Hotspot monitoring MCP server
└── data/                     # Persistent data storage & backups
```

## Key Projects

### AI-Trader (`workspace/projects/AI-Trader/`)

Autonomous AI trading agents competing in NASDAQ 100, A-shares, and cryptocurrency markets.

```bash
cd workspace/projects/AI-Trader

# US Stocks workflow
bash scripts/main.sh                    # Complete workflow
bash scripts/main_step1.sh              # Prepare price data
bash scripts/main_step2.sh              # Start MCP services
bash scripts/main_step3.sh              # Run trading agent

# A-Shares workflow
bash scripts/main_a_stock_step1.sh      # A-share data preparation
bash scripts/main_a_stock_step2.sh      # Start MCP services
bash scripts/main_a_stock_step3.sh      # Run A-share agent

# Crypto workflow
bash scripts/main_crypto_step1.sh       # Crypto data preparation
bash scripts/main_crypto_step2.sh       # Start MCP services
bash scripts/main_crypto_step3.sh       # Run crypto agent

# View performance
python tools/calculate_metrics.py --signature trade-agent
python tools/plot_metrics.py --signature trade-agent
```

**Data paths:**
- Price data: `data/daily_prices_*.json`, `data/merged.jsonl`
- Trading records: `data/agent_data/`, `data/agent_data_astock/`, `data/agent_data_crypto/`

### TrendRadar (`workspace/projects/TrendRadar/`)

MCP server for real-time hotspot monitoring and trend analysis.

```bash
cd workspace/projects/TrendRadar

# Run locally
./run-local.sh

# Test MCP server
python -m mcp_server
```

## Configuration

### Environment Variables (`~/.openclaw/.env`)

Key variables (actual values stored in `.env` file):
- `BAILIAN_API_KEY` / `CODING_PLAN_KEY` -阿里云百炼 API
- `TUSHARE_TOKEN` - Tushare Pro 金融数据
- `JINA_API_KEY` - Jina AI 搜索
- `DINGTALK_*` - 钉钉机器人配置
- `WECOM_*` - 企业微信配置
- `GATEWAY_AUTH_TOKEN` - Gateway 认证

### Model Configuration

All models use Alibaba Bailian provider via `https://coding.dashscope.aliyuncs.com/v1`:

| Model | Use Case |
|-------|----------|
| qwen3.5-plus | General tasks, trading analysis |
| qwen3-coder-next | Code generation (dev-agent default) |
| qwen3-coder-plus | Code understanding |
| MiniMax-M2.5 | Fallback model |
| glm-5, glm-4.7 | Alternative general models |
| kimi-k2.5 | Multimodal tasks |

## Channels

| Channel | Mode | Purpose |
|---------|------|---------|
| **DingTalk** | HTTP | Hotspot push, trading notifications |
| **WeCom** | WebSocket | Direct messaging, session management |

Both channels configured with:
- `dmPolicy: open` - Direct messages enabled
- `groupPolicy: closed` - Group messages restricted
- `messageType: markdown` - Rich formatting
- Session persistence and auto-reconnect

## Skills System

### Bundled Skills (enabled)
- `weather`, `web_search`, `web_fetch` - Information retrieval
- `clawhub`, `file-search`, `browse` - File/web operations
- `jina_search`, `tavily_search` - Specialized search
- `coding-agent` - Code generation via Bailian
- `github` - Repository operations
- `summarize`, `get-tldr` - Content summarization

### Custom Skills
- `quantaalpha-deep` - Alpha factor mining (main-agent)
- `stock-pick` - Stock screening (main-agent)
- `vnpy-futu-trader` - VnPy + Futu trading execution (trade-agent)
- `akshare-stock` - A-share real-time quotes
- `china-stock-analysis` - Value investment analysis

## Trading Pipeline (Automated)

```
因子挖掘 (QuantaAlpha) → 选股 (Stock-Pick) → 辩论 (Debate) → 人工确认 → 交易执行 (VnPy) → 持仓管理
```

See `workspace/agents/trade/AUTOMATION_PIPELINE.md` for full specification.

### Risk Controls
- Single stock position ≤ 20%
- Total position ≥ 10% cash
- Stop-loss: -8% per trade, -15% total account
- Large trades (>5% position) require user confirmation

## Development Workflow

### dev-agent Usage

```bash
# Send coding tasks to dev-agent
/dev 帮我写一个 Python 函数计算斐波那契数列
/dev 帮我审查这段代码...
/dev 这个函数有 bug，帮我修复一下...
```

### Code Review Checklist
- Logic correctness
- Edge case handling
- Error handling
- Performance implications
- Security vulnerabilities
- Code readability and comments

### Git Convention

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Python Environments

| Project | Virtual Environment |
|---------|---------------------|
| AI-Trader | `workspace/projects/AI-Trader/venv/` |
| TrendRadar | `workspace/projects/TrendRadar/venv/` |
| Trade (Futu) | `workspace/agents/trade/venv-futu/` |
| Debate | `workspace/agents/debate/venv/` |

**Python Version**: 3.11+

## Utility Scripts

```bash
# Backup secrets (daily at 3:00 AM via cron)
scripts/backup-secrets.sh

# Test Claude Code Bailian connection
scripts/test-claude-code-bailian.sh

# Heartbeat news push
scripts/heartbeat-news.sh

# Set channel defaults
scripts/set-channel-defaults.sh
```

## Data & Logs

### Trade Agent
- Position: `workspace/projects/AI-Trader/data/agent_data/trade-agent/position/position.jsonl`
- Logs: `workspace/projects/AI-Trader/data/agent_data/trade-agent/log/{date}/log.jsonl`

### Backups
- Encrypted backups to `data/backups/secrets/` using age encryption
- Daily automatic backup at 3:00 AM
- 30-day retention

## Important Notes

1. **API Key Security**: All sensitive data in `.env` - never commit to git
2. **Simulated Trading First**: New strategies must validate in simulation before live trading
3. **User Confirmation Required**: First trade and large trades always need approval
4. **Model Routing**: dev-agent uses qwen3-coder-next for code, trade/main use qwen3.5-plus

## Documentation

- `workspace/agents/trade/AUTOMATION_PIPELINE.md` - Full trading pipeline design
- `workspace/agents/*/SOUL.md` - Agent persona and behavior guidelines
- `workspace/agents/*/TOOLS.md` - Agent-specific tool documentation
- `data/ai-trader/configs/README.md` - AI-Trader configuration guide
- `docs/CLAUDE-CODE-BAILIAN-CONFIG.md` - Bailian coding-agent setup
