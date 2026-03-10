# AI-Trader 本地容器化运行

## 概述

AI-Trader 是一个基于 LLM 的 A 股交易智能体，支持回测和实时交易模式。本地容器化运行替代 AWS ECS 部署。

## 项目路径

| 路径 | 说明 |
|------|------|
| `/home/admin/.openclaw/workspace/projects/AI-Trader` | 源码目录 |
| `/home/admin/.openclaw/data/ai-trader` | 持久化数据目录 |
| `/home/admin/.openclaw/data/ai-trader/configs` | 配置文件 |
| `/home/admin/.openclaw/data/ai-trader/data` | 交易数据 |
| `/home/admin/.openclaw/data/ai-trader/logs` | 执行日志 |

## 快速开始

### 回测模式

```bash
cd /home/admin/.openclaw/workspace/projects/AI-Trader

# 基本用法
./run-local.sh configs/astock_config_daily_20260119.json 2026-01-19 2026-01-26

# 指定单个 Agent
./run-local.sh configs/astock_config_daily_20260119.json 2026-01-19 2026-01-26 --agent Test_nuts_260119

# 跳过数据准备（数据已就绪）
./run-local.sh configs/xxx.json 2026-01-19 2026-01-26 --skip-data-prep
```

### LIVE 实时交易模式

```bash
./run-local.sh configs/astock_config_hourly_260202.json --live
```

## 命令行选项

| 选项 | 说明 |
|------|------|
| `--live` | LIVE 实时交易模式 |
| `--agent SIGNATURE` | 只运行指定的 Agent |
| `--skip-data-prep` | 跳过数据准备步骤 |
| `--build` | 强制重新构建 Docker 镜像 |
| `-h, --help` | 显示帮助信息 |

## 执行流程

```
┌─────────────────────────────────────────┐
│  run-local.sh                           │
├─────────────────────────────────────────┤
│  1. 检查/构建 Docker 镜像                │
│  2. 从配置文件提取 DATE_SUFFIX           │
│  3. 加载 Agent 列表 (enabled=true)       │
├─────────────────────────────────────────┤
│  Step 1: 数据准备容器                    │
│    ├─ Tushare 日线数据获取               │
│    ├─ EF 日线/小时线数据获取             │
│    └─ 数据合并 (merged_*.jsonl)         │
├─────────────────────────────────────────┤
│  Step 2: 并行运行 Agent 容器             │
│    ├─ 启动 MCP 服务 (4个端口)            │
│    ├─ 执行交易决策                       │
│    └─ 推送持仓通知                       │
└─────────────────────────────────────────┘
```

## Docker 镜像管理

```bash
# 查看镜像
docker images | grep ai-trader

# 强制重新构建
./run-local.sh configs/xxx.json --build

# 手动构建镜像
cd /home/admin/.openclaw/workspace/projects/AI-Trader
podman build -t ai-trader:latest .
```

## 配置文件规范

配置文件名必须包含日期后缀：

```
configs/astock_config_daily_20260119.json
                         ^^^^^^^^
                         DATE_SUFFIX = 20260119
```

配置文件结构：
```json
{
  "date_range": {
    "init_date": "2026-01-19",
    "end_date": "2026-01-26"
  },
  "models": [
    {
      "name": "Test Agent",
      "signature": "Test_nuts_260119",
      "basemodel": "deepseek-chat",
      "enabled": true
    }
  ]
}
```

## 数据文件

数据文件命名规范：
- `merged_20260119.jsonl` - 合并的价格数据
- `sse_pick_20260119.csv` - 股票选择列表

数据目录结构：
```
data/ai-trader/data/
├── A_stock/
│   ├── merged_20260119.jsonl
│   ├── sse_pick_20260119.csv
│   └── agent_data_astock/
│       └── Test_nuts_260119/
│           └── position/
│               └── position.jsonl
```

## 环境变量

关键环境变量在 `data/ai-trader/.env` 中配置：

| 变量 | 说明 |
|------|------|
| `OPENAI_API_BASE` | LLM API 地址 |
| `OPENAI_API_KEY` | LLM API 密钥 |
| `TUSHARE_TOKEN` | Tushare 数据源 Token |
| `JINA_API_KEY` | Jina 搜索 API Key |

## 日志查看

```bash
# 查看容器日志
docker logs trader-agent-Test_nuts_260119

# 查看持久化日志
tail -f /home/admin/.openclaw/data/ai-trader/logs/Test_nuts_260119/*.log
```

## 常见问题

### Q: 数据文件找不到
**A**: 运行数据准备步骤，或检查 `DATE_SUFFIX` 是否正确。

### Q: MCP 服务启动超时
**A**: 检查端口 8000-8003 是否被占用。

### Q: 推送通知失败
**A**: 检查 notify.sh 脚本是否存在和可执行。

## 相关文件

- `run-local.sh` - 本地运行入口脚本
- `Dockerfile` - 镜像构建文件
- `scripts/container_entrypoint.sh` - Agent 容器入口
- `scripts/data_preparation_entrypoint.sh` - 数据准备入口
- `webhook/notify_client.py` - 统一推送模块
