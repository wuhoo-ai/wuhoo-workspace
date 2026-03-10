# TOOLS.md - main-agent 工具笔记

## 已配置渠道

### DingTalk
- **CorpId**: ding69c47ef3fc079e42f5bf40eda33b7ba0
- **AgentId**: 4201415235
- **RobotCode**: dingpssp8htuirt74hjs
- **用途**: 热点推送、交易通知、定时提醒

## 可用技能

### 信息检索
- `jina_search`: **Jina AI API**（主力）- 高质量搜索，注重相关性和准确性
- `web_fetch`: 网页内容提取（配合 jina_search 使用）
- ~~`web_search`: Brave Search API~~（已弃用，改用 Jina）

#### Jina Search 使用方式
```bash
# 基础搜索（exec 调用）
exec curl -s -X POST "https://api.jina.ai/v1/search" \
  -H "Authorization: Bearer $JINA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "关键词", "count": 8}'

# 带时间过滤
exec curl -s -X POST "https://api.jina.ai/v1/search" \
  -H "Authorization: Bearer $JINA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "关键词", "count": 8, "freshness": "pm"}'

# 读取 URL 全文
exec curl -s -H "Authorization: Bearer $JINA_API_KEY" "https://r.jina.ai/https://example.com"
```

#### 时间过滤参数
| 参数 | 说明 |
|------|------|
| `pd` | 最近 1 天 |
| `pw` | 最近 1 周 |
| `pm` | 最近 1 月 |
| `py` | 最近 1 年 |

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
