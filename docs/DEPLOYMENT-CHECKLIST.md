# Agent 配置部署清单

## ✅ 已完成 (2026-03-01 13:45)

### 1. 代码仓库下载
- [x] AI-Trader: `~/.openclaw/workspace/Code/AI-Trader/`
- [x] TrendRadar: `~/.openclaw/workspace/Code/TrendRadar/`

### 2. Agent 配置文件创建
- [x] `agents/main/SOUL.md` - main-agent 人格定义
- [x] `agents/main/USER.md` - 用户信息
- [x] `agents/main/TOOLS.md` - 工具笔记
- [x] `agents/dev/SOUL.md` - dev-agent 人格定义
- [x] `agents/dev/TOOLS.md` - 工具笔记
- [x] `agents/trade/SOUL.md` - trade-agent 人格定义
- [x] `agents/trade/TOOLS.md` - 工具笔记
- [x] `IDENTITY.md` - 系统身份配置
- [x] `AGENTS-CONFIG.md` - 总体配置方案
- [x] `SUMMARY.md` - 完成总结

### 3. OpenClaw 配置更新
- [x] `~/.openclaw/openclaw.json` - 添加 agents.list 配置

### 4. Git 提交
- [x] 已提交到仓库 (commit: 4d4d64d)

---

## ⏳ 待完成

### 1. Gateway 重启
```bash
openclaw gateway restart
```

### 2. TrendRadar MCP Server 配置
- [ ] 编辑 `config/config.yaml` 配置热点关键词
- [ ] 启动 MCP Server
- [ ] 测试与 main-agent 集成

### 3. AI-Trader MCP 服务配置
- [ ] 创建 `.env` 文件 (基于 `.env.example`)
- [ ] 配置 API Key (AlphaVantage, Jina 等)
- [ ] 启动 MCP 服务
- [ ] 测试 trade-agent 交易流程

### 4. DingTalk 消息路由
- [ ] 配置消息路由规则
- [ ] 测试推送通知

### 5. Cron 定时任务
- [ ] 配置热点检查 (每 2 小时)
- [ ] 配置交易任务 (根据市场时间)

---

## 快速启动命令

### 重启 Gateway
```bash
openclaw gateway restart
```

### 测试 main-agent
```bash
# 在当前对话中直接测试
# 已配置 qwen3.5-plus 模型
```

### 启动 TrendRadar
```bash
cd ~/openclaw/workspace/Code/TrendRadar
python -m trendradar
```

### 启动 AI-Trader MCP 服务
```bash
cd ~/openclaw/workspace/Code/AI-Trader
python agent_tools/start_mcp_services.py
```

---

## 配置验证

### 检查 Agent 配置
```bash
openclaw config get agents.list
```

### 检查模型配置
```bash
openclaw config get models.providers.bailian
```

### 检查渠道配置
```bash
openclaw config get channels.dingtalk
```

---

## 下一步建议

1. **重启 Gateway** - 应用新配置
2. **测试 main-agent** - 验证对话和检索功能
3. **配置 TrendRadar** - 设置热点关键词，测试推送
4. **配置 AI-Trader** - 填写 API Key，启动 MCP 服务
5. **创建 trade-agent skill** - 封装 AI-Trader 功能为 OpenClaw skill

---

*创建时间：2026-03-01*
