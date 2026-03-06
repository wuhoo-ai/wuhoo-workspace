# TOOLS.md - main-agent 工具笔记

## 已配置渠道

### DingTalk
- **CorpId**: ding69c47ef3fc079e42f5bf40eda33b7ba0
- **AgentId**: 4201415235
- **RobotCode**: dingpssp8htuirt74hjs
- **用途**: 热点推送、交易通知、定时提醒

## 可用技能

### 信息检索
- `web_search`: Brave Search API，联网检索
- `web_fetch`: 网页内容提取

### 个人事务
- `weather`: 天气查询 (wttr.in / Open-Meteo)
- `himalaya`: 邮件管理 (需配置)
- `notion` / `obsidian`: 知识管理 (需配置)

### 系统工具
- `read` / `edit` / `write`: 文件操作
- `exec`: 命令执行 (有限权限)
- `browser`: 浏览器自动化

## TrendRadar 集成

### MCP Server 位置
```
~/openclaw/workspace/Code/TrendRadar/mcp_server/
```

### 配置热点关键词
编辑 `~/openclaw/workspace/Code/TrendRadar/config/config.yaml`:
```yaml
keywords:
  - "AI"
  - "量化交易"
  - "跨境电商"
  - "大模型"
  - "芯片"
  - "新能源"
```

### 通知推送
TrendRadar 已配置 DingTalk，推送至当前渠道。

## 常用命令

```bash
# 查看 OpenClaw 状态
openclaw status

# 查看配置
openclaw config get agents.defaults.model

# 重启 Gateway
openclaw gateway restart
```

## API Key 管理

所有敏感配置存储在 `~/.openclaw/.env`:
```bash
# 查看 (不要分享)
cat ~/.openclaw/.env
```

---

*更新时请保持简洁，只记录关键信息*
