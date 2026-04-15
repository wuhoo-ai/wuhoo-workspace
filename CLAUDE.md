# CLAUDE.md

OpenClaw 配置仓库。管理模型、Agent、Channel、Skills 等核心配置。

## 仓库架构

当前 `.openclaw/` 是配置中心，代码通过软链接引用独立仓库：

| 组件 | 路径 | 独立仓库 |
|------|------|----------|
| Config | `~/.openclaw/` | 当前仓库 |
| Skills | `skills/` → `~/skills-openclaw/` | [skills-openclaw](~/skills-openclaw/) |
| Agent 代码 | `workspace/agents/` → `~/agents-openclaw/` | [agents-openclaw](~/agents-openclaw/) |
| Projects | `workspace/projects/` | 各自独立仓库 |

### Core Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| **main-agent** | bailian/qwen3.5-plus | 日常助手、信息检索、任务路由 |
| **dev-agent** | bailian/qwen3-coder-next | 代码生成、审查、调试 |
| **trade-agent** | bailian/qwen3.5-plus | 量化交易、市场分析、风险管理 |
| **debate-agent** | - | 多 agent 辩论分析股票 |

### 模型配置

通过百炼代理 `https://coding.dashscope.aliyuncs.com/apps/anthropic`：

| Model | 用途 |
|-------|------|
| qwen3.5-plus | 通用任务、交易分析 |
| qwen3-coder-next | 代码生成 (dev-agent) |
| MiniMax-M2.5 | 降级模型 |

### Channel 配置

| Channel | Mode | 用途 |
|---------|------|------|
| **DingTalk** | HTTP | 热点推送、交易通知 |
| **WeCom** | WebSocket | 直接消息、会话管理 |

## Skills 系统

### 企业级关键 Skills (wuhoo-*)

> 修改这些 skill 时需特别谨慎，承担核心业务价值。

| Skill | 用途 |
|-------|------|
| **wuhoo-stock-deep-analysis** | Workflow B — 单股深度分析 |
| **wuhoo-stock-autopick-trade** | Workflow C — 多市场自动选股 |
| **wuhoo-trade-diagnose** | Workflow D — 持仓诊断与调仓 |
| **wuhoo-news-rss** | RSS 资讯引擎 |

### 其他 Skills

| Skill | 用途 |
|-------|------|
| futu-api | 富途 OpenAPI (57 脚本) |
| stock-pick | A股因子选股 |
| install-futu-opend | Futu OpenD 安装 |

Skills 通过 `skills.load.extraDirs: ["~/.openclaw/skills"]` 加载。

## Trading Pipeline

```
选股 (Stock-Pick) → 辩论 (Debate) → 人工确认 → 交易执行 (Futu) → 持仓管理 (Trade-Diagnose)
```

### 风控规则
- 单股仓位 ≤ 20%
- 总仓位 ≥ 10% 现金
- 止损: -8%/笔, -15%/账户
- 大额交易 (>5% 仓位) 需用户确认

## 环境变量

关键变量在 `.env` 中：`BAILIAN_API_KEY`, `TUSHARE_TOKEN`, `JINA_API_KEY`, `DINGTALK_*`, `WECOM_*`

## 开发工作流

```bash
# dev-agent 用法
/dev 帮我写一个 Python 函数
/dev 帮我审查这段代码
```

### Git 规范

`<type>(<scope>): <subject>` — types: feat, fix, docs, refactor, test, chore

## 工具脚本

```bash
scripts/backup-secrets.sh            # 每日备份
scripts/test-claude-code-bailian.sh  # 连接测试
scripts/heartbeat-news.sh            # 心跳推送
```
