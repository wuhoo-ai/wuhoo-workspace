# 新闻检索技能状态

**更新时间**: 2026-03-13 14:52  
**状态**: ✅ 已优化

---

## ✅ 可用技能 (5 个)

| 技能 | 用途 | API Key | 状态 |
|------|------|---------|------|
| **agent-news** | AI Agent 行业新闻 | - | ✅ 可用 |
| **technews** | 科技新闻聚合 | - | ✅ 可用 |
| **jina_search** | Jina AI 搜索 | `$JINA_API_KEY` ✅ | ✅ 可用 |
| **browse** | 网页内容提取 | `$JINA_API_KEY` ✅ | ✅ 可用 |
| **openclaw-tavily-search** | Tavily AI 搜索 | `$TAVILY_API_KEY` ✅ | ✅ 可用 |

---

## ❌ 已禁用技能 (1 个)

| 技能 | 原因 | 状态 |
|------|------|------|
| **web-search-pro** | BRAVE_API_KEY 免费额度用完，人民币支付不友好 | 🚫 已禁用 |

**禁用操作**:
```bash
# 移动技能到 .disabled 目录
mv ~/.agents/skills/web-search-pro ~/.agents/skills/web-search-pro.disabled

# 从 main-agent 工具列表移除
# 工具数：17 → 16
```

---

## 📋 技能详解

### 1. agent-news (AI 行业新闻) ⭐⭐⭐⭐⭐

**用途**: AI Agent 行业最新动态

**使用**:
```bash
openclaw agent --agent main --message "今天的 AI 行业新闻"
```

**输出**: 精简摘要，每条≤50 字，标注来源和时间

---

### 2. technews (科技新闻) ⭐⭐⭐⭐⭐

**用途**: 科技新闻、行业动态、创业新闻

**使用**:
```bash
openclaw agent --agent main --message "今天的科技新闻"
```

**数据来源**: TechCrunch, The Verge, Hacker News, 36 氪，机器之心

---

### 3. jina_search (Jina AI 搜索) ⭐⭐⭐⭐⭐

**用途**: 高质量网络搜索，支持时间过滤

**API**: `$JINA_API_KEY` (已配置 ✅)

**使用示例**:
```bash
# 基础搜索
curl -s -X POST "https://api.jina.ai/v1/search" \
  -H "Authorization: Bearer $JINA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "AI agent trends 2026", "count": 10}'

# 带时间过滤
curl -s -X POST "https://api.jina.ai/v1/search" \
  -H "Authorization: Bearer $JINA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "量化交易", "count": 10, "freshness": "pm"}'
```

**时间过滤**:
- `pd` - 最近 1 天
- `pw` - 最近 1 周
- `pm` - 最近 1 月
- `py` - 最近 1 年

---

### 4. browse (网页提取) ⭐⭐⭐⭐

**用途**: 提取网页全文内容

**API**: `$JINA_API_KEY` (已配置 ✅)

**使用示例**:
```bash
curl -s -H "Authorization: Bearer $JINA_API_KEY" \
  "https://r.jina.ai/https://example.com/article"
```

**输出**: Markdown 格式的网页全文

---

### 5. openclaw-tavily-search (Tavily 搜索) ⭐⭐⭐⭐

**用途**: AI 优化的网络搜索

**API**: `$TAVILY_API_KEY` (已配置 ✅)

**使用示例**:
```bash
curl -X POST https://api.tavily.com/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -d '{"query": "AI agent trends 2026", "search_depth": "advanced"}'
```

**特点**: 返回简洁、相关的结果，适合 AI agent 使用

---

## 🎯 推荐使用场景

| 场景 | 推荐技能 | 理由 |
|------|---------|------|
| **AI 行业新闻** | agent-news | 专注 AI Agent 领域 |
| **科技新闻** | technews | 覆盖全面，多来源 |
| **精确搜索** | jina_search | 支持时间过滤，质量高 |
| **网页提取** | browse | 提取全文，Markdown 格式 |
| **快速搜索** | openclaw-tavily-search | AI 优化，结果简洁 |

---

## 📝 Heartbeat 自动新闻摘要

**配置**: 每日 9:00 和 18:00 自动触发

**内容**:
- AI Agent 行业动态 (agent-news) ✅
- 科技新闻/大模型/融资 (technews) ✅
- 伊朗/中东局势 (jina_search) ✅

**Cron 任务**:
```bash
0 9,18 * * * openclaw agent --agent main --message "Read HEARTBEAT.md..."
```

---

## 🔧 API Key 状态

| API Key | 状态 | 用途 |
|---------|------|------|
| `$JINA_API_KEY` | ✅ 已配置 | jina_search, browse |
| `$TAVILY_API_KEY` | ✅ 已配置 | openclaw-tavily-search |
| `$TUSHARE_TOKEN` | ✅ 已配置 | tushare_search (金融数据) |
| `$BRAVE_API_KEY` | ❌ 未配置 | web-search-pro (已禁用) |

---

## 💡 替代方案

如果需要多引擎搜索，可以考虑：

1. **使用 jina_search** - 质量高，支持时间过滤
2. **使用 Tavily** - AI 优化，结果简洁
3. **直接调用搜索 API** - 通过 exec 工具调用

---

**维护者**: main-agent  
**最后更新**: 2026-03-13 14:52  
**状态**: ✅ 已优化
