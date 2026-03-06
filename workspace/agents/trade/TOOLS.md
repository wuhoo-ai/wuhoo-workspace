# TOOLS.md - trade-agent 工具笔记

## AI-Trader 配置

### 项目路径
```
~/openclaw/workspace/Code/AI-Trader/
```

### MCP 服务端口
| 服务 | 端口 | 用途 |
|------|------|------|
| math | 8000 | 数学计算 |
| trade | 8002 | 交易执行 |
| stock_local | 8003 | 股票价格 |
| search | 8004 | 新闻搜索 |

### 配置文件
- **主配置**: `configs/default_config.json`
- **环境变量**: `.env` (基于 `.env.example` 创建)

### 数据目录
```
data/
├── agent_data/
│   └── trade-agent/
│       ├── position/
│       │   └── position.jsonl    # 持仓记录
│       └── log/
│           └── {date}/
│               └── log.jsonl     # 交易日志
└── price_data/
    └── merged.jsonl              # 价格数据
```

## 交易配置

### 市场设置
- **美股**: NASDAQ 100 (默认)
- **A 股**: SSE 50
- **加密货币**: BTC, ETH 等 10 种主流币种

### 交易参数
```json
{
  "initial_cash": 10000.0,      // 初始资金 (美股/加密货币)
  "initial_cash_cn": 100000.0,  // 初始资金 (A 股，人民币)
  "max_steps": 30,              // 最大推理步数
  "max_retries": 3,             // 重试次数
  "verbose": true               // 详细日志
}
```

### 交易时间
- **美股**: 北京时间 21:30-04:00 (夏令时) / 22:30-05:00 (冬令时)
- **A 股**: 北京时间 09:30-11:30, 13:00-15:00
- **加密货币**: 24/7

## 可用工具

### MCP 工具
- `math_*`: 数学计算工具
- `stock_*`: 股票价格工具
- `search_*`: 新闻搜索工具
- `trade_*`: 交易执行工具

### OpenClaw 工具
- `exec`: 运行 Python 脚本
- `read`: 读取持仓和日志
- `message`: 发送交易通知 (DingTalk)

## 常用命令

### 启动服务
```bash
cd ~/openclaw/workspace/Code/AI-Trader

# 启动所有 MCP 服务
python agent_tools/start_mcp_services.py

# 单独启动某个服务
python -m tools.mcp_servers.math_server
python -m tools.mcp_servers.stock_server
python -m tools.mcp_servers.search_server
python -m tools.mcp_servers.trade_server
```

### 运行交易
```bash
# 运行主程序 (并行多模型)
python main_parrallel.py

# 运行单个模型
python main.py --config configs/default_config.json

# 注册新 agent
python -c "from agent.base_agent.base_agent import BaseAgent; agent = BaseAgent('my-strategy', 'qwen3.5-plus'); agent.register_agent()"
```

### 查看数据
```bash
# 查看持仓
cat data/agent_data/trade-agent/position/position.jsonl | tail -1 | jq

# 查看日志
tail -f data/agent_data/trade-agent/log/*/log.jsonl

# 计算收益
python tools/calculate_metrics.py --signature trade-agent

# 生成图表
python tools/plot_metrics.py --signature trade-agent
```

## 风险控制

### 仓位限制
- 单股票最大仓位：20%
- 最小现金仓位：10%
- 行业集中度：单行业 ≤ 40%

### 止损规则
- 单笔止损：-8%
- 总账户止损：-15%
- 连续亏损 3 笔：暂停交易，复盘策略

### 审批流程
```
交易决策 → 金额 < $1000? 
         ├─ 是 → 自动执行
         └─ 否 → 用户确认 → 执行
```

## 通知推送

### DingTalk 消息模板
```markdown
## 交易执行通知

**策略**: trade-agent
**时间**: {timestamp}
**操作**: BUY/SELL/HOLD
**标的**: {symbol}
**数量**: {quantity}
**价格**: {price}
**金额**: {amount}
**原因**: {reason}
```

## API Key 配置

在 `.env` 文件中配置:
```bash
# OpenAI 兼容 API (用于 LangChain)
OPENAI_API_BASE=https://coding.dashscope.aliyuncs.com/v1
OPENAI_API_KEY=sk-xxx

# AlphaVantage (股票价格)
ALPHA_VANTAGE_API_KEY=xxx

# Jina (新闻搜索)
JINA_API_KEY=xxx

# MCP 服务端口
MATH_HTTP_PORT=8000
TRADE_HTTP_PORT=8002
GETPRICE_HTTP_PORT=8003
SEARCH_HTTP_PORT=8004
```

---

*交易有风险，决策需谨慎*
