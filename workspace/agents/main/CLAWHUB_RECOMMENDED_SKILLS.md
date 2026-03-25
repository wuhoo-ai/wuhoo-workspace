# ClawHub 热门 Skills 推荐

**更新时间**: 2026-03-10  
**来源**: ClawHub Registry (https://clawhub.com)

---

## 📊 评分说明

ClawHub 使用 5 分制评分：
- ⭐⭐⭐⭐⭐ (4.5-5.0): 强烈推荐
- ⭐⭐⭐⭐ (3.5-4.5): 推荐
- ⭐⭐⭐ (3.0-3.5): 可选
- ⭐⭐ (2.0-3.0): 谨慎选择

---

## 🔥 综合热门 Top 10

| 排名 | Skill | 评分 | 用途 | 推荐度 |
|------|-------|------|------|--------|
| 1 | **weather** | 3.85 | 天气查询 | 🔴 高 |
| 2 | **baidu-search** | 3.69 | 百度搜索 | 🔴 高 |
| 3 | **file-search** | 3.60 | 文件搜索 | 🔴 高 |
| 4 | **ai-notes-of-video** | 3.57 | 视频 AI 笔记 | 🟡 中 |
| 5 | **web-search-pro** | 3.58 | 专业网页搜索 | 🔴 高 |
| 6 | **ai-agent-helper** | 3.57 | AI 助手辅助 | 🟡 中 |
| 7 | **database-operations** | 3.53 | 数据库操作 | 🟡 中 |
| 8 | **google-weather** | 3.52 | Google 天气 | 🟡 中 |
| 9 | **weather-pollen** | 3.53 | 花粉天气 | 🟢 低 |
| 10 | **rag-search** | 3.46 | RAG 搜索 | 🟡 中 |

---

## 📂 分类推荐

### 🔍 搜索类 (Search)

| Skill | 评分 | 说明 | 推荐度 |
|-------|------|------|--------|
| **baidu-search** | 3.69 | 百度搜索集成 | 🔴 国内必备 |
| **web-search-pro** | 3.58 | 专业网页搜索 | 🔴 推荐 |
| **file-search** | 3.60 | 本地文件搜索 | 🔴 实用 |
| **multi-search-engine-2-0-1** | 3.43 | 多搜索引擎 | 🟡 可选 |
| **bailian-web-search** | 3.45 | 通义千问搜索 | 🟡 推荐 |

**推荐组合**:
```bash
# 国内用户
clawhub install baidu-search
clawhub install web-search-pro

# 已有 jina_search，可选装
clawhub install multi-search-engine-2-0-1
```

---

### 🌤️ 天气类 (Weather)

| Skill | 评分 | 说明 | 推荐度 |
|-------|------|------|--------|
| **weather** | 3.85 | 通用天气查询 | 🔴 最高推荐 |
| **google-weather** | 3.52 | Google 天气 | 🟡 备选 |
| **weather-pollen** | 3.53 | 花粉指数天气 | 🟢 过敏人群 |
| **openmeteo-sh-weather-advanced** | 3.41 | OpenMeteo 高级版 | 🟡 开发者 |

**推荐**:
```bash
clawhub install weather
```

---

### 🤖 AI 类 (AI Tools)

| Skill | 评分 | 说明 | 推荐度 |
|-------|------|------|--------|
| **ai-notes-of-video** | 3.57 | 视频 AI 笔记 | 🔴 推荐 |
| **ai-agent-helper** | 3.57 | AI 助手辅助 | 🟡 实用 |
| **ai-news-research** | 3.37 | AI 行业新闻 | 🟡 可选 |
| **chinese-ai-agent-guide** | 3.35 | 中文 AI 指南 | 🟢 入门 |
| **hk-ai-stock-expert** | 3.52 | 港股 AI 投研 | 🟡 投资者 |

**推荐**:
```bash
clawhub install ai-notes-of-video
clawhub install ai-agent-helper
```

---

### 💾 数据库类 (Database)

| Skill | 评分 | 说明 | 推荐度 |
|-------|------|------|--------|
| **database-operations** | 3.53 | 数据库操作 | 🔴 推荐 |
| **database-manager** | 3.28 | 数据库管理 | 🟡 可选 |
| **rag-search** | 3.46 | RAG 向量搜索 | 🔴 推荐 |

**推荐**:
```bash
clawhub install database-operations
clawhub install rag-search
```

---

### 📝 笔记类 (Notes)

*注：搜索遇到限流，以下为已知热门*

| Skill | 评分 | 说明 | 推荐度 |
|-------|------|------|--------|
| **notion** | - | Notion 集成 | 🔴 已有 |
| **obsidian** | - | Obsidian 集成 | 🔴 已有 |
| **bear-notes** | - | Bear Notes | 🔴 已有 |

---

### 🛠️ 开发工具类 (Dev Tools)

| Skill | 评分 | 说明 | 推荐度 |
|-------|------|------|--------|
| **github** | - | GitHub 集成 | 🔴 已有 |
| **file-search** | 3.60 | 文件搜索 | 🔴 推荐 |

**推荐**:
```bash
clawhub install file-search
```

---

## 🎯 按场景推荐

### 场景 1：日常办公

```bash
# 天气查询
clawhub install weather

# 文件搜索
clawhub install file-search

# 网页搜索
clawhub install web-search-pro
```

**总评分**: ⭐⭐⭐⭐⭐ (15.03/5)

---

### 场景 2：内容创作

```bash
# 视频笔记
clawhub install ai-notes-of-video

# AI 助手
clawhub install ai-agent-helper

# 百度搜索
clawhub install baidu-search
```

**总评分**: ⭐⭐⭐⭐⭐ (10.82/5)

---

### 场景 3：数据分析

```bash
# 数据库操作
clawhub install database-operations

# RAG 搜索
clawhub install rag-search

# 多搜索引擎
clawhub install multi-search-engine-2-0-1
```

**总评分**: ⭐⭐⭐⭐ (10.42/5)

---

### 场景 4：投资研究

```bash
# 港股 AI 专家
clawhub install hk-ai-stock-expert

# 百度搜索
clawhub install baidu-search

# 网页搜索专业版
clawhub install web-search-pro
```

**总评分**: ⭐⭐⭐⭐ (10.75/5)

---

## 📦 当前系统已有 Skills 对比

### 已安装 (54 个)

| 类别 | 已有 | 是否需要补充 |
|------|------|-------------|
| **搜索** | jina_search (付费) | ✅ 可补充免费搜索 |
| **天气** | weather | ❌ 已有，无需安装 |
| **笔记** | notion, obsidian, bear-notes | ❌ 已有 |
| **数据库** | - | ✅ 可安装 database-operations |
| **文件** | - | ✅ 可安装 file-search |
| **AI 工具** | - | ✅ 可安装 ai-notes-of-video |

---

## 🎯 最终推荐清单

### 🔴 强烈推荐 (必装)

| Skill | 评分 | 用途 | 命令 |
|-------|------|------|------|
| **file-search** | 3.60 | 本地文件搜索 | `clawhub install file-search` |
| **web-search-pro** | 3.58 | 专业网页搜索 | `clawhub install web-search-pro` |

**理由**: 补充现有 jina_search 的不足，提供免费搜索选项

---

### 🟡 推荐安装 (实用)

| Skill | 评分 | 用途 | 命令 |
|-------|------|------|------|
| **database-operations** | 3.53 | 数据库操作 | `clawhub install database-operations` |
| **ai-notes-of-video** | 3.57 | 视频 AI 笔记 | `clawhub install ai-notes-of-video` |
| **rag-search** | 3.46 | RAG 向量搜索 | `clawhub install rag-search` |

**理由**: 扩展 Agent 能力边界

---

### 🟢 可选安装 (按需)

| Skill | 评分 | 用途 | 适合人群 |
|-------|------|------|----------|
| **baidu-search** | 3.69 | 百度搜索 | 国内用户 |
| **ai-agent-helper** | 3.57 | AI 助手辅助 | 开发者 |
| **hk-ai-stock-expert** | 3.52 | 港股 AI 投研 | 投资者 |
| **google-weather** | 3.52 | Google 天气 | 备选天气 |

---

## 📝 安装建议

### 方案 A：最小安装 (2 个)

```bash
clawhub install file-search
clawhub install web-search-pro
```

**总评分**: 7.18/5 ⭐⭐⭐⭐⭐

---

### 方案 B：标准安装 (5 个)

```bash
clawhub install file-search
clawhub install web-search-pro
clawhub install database-operations
clawhub install ai-notes-of-video
clawhub install rag-search
```

**总评分**: 17.74/5 ⭐⭐⭐⭐⭐

---

### 方案 C：完整安装 (8 个)

```bash
clawhub install file-search
clawhub install web-search-pro
clawhub install database-operations
clawhub install ai-notes-of-video
clawhub install rag-search
clawhub install baidu-search
clawhub install ai-agent-helper
clawhub install hk-ai-stock-expert
```

**总评分**: 28.45/5 ⭐⭐⭐⭐⭐

---

## ⚠️ 注意事项

1. **评分仅供参考**: 评分基于 ClawHub 用户反馈
2. **功能重叠**: 部分 Skill 可能与已有 Skills 功能重叠
3. **API 依赖**: 某些 Skills 可能需要配置 API Key
4. **更新维护**: 定期使用 `clawhub update --all` 更新

---

## 🔧 安装后配置

安装 Skills 后，需要添加到 Agent 的 `tools.allow`：

```json
{
  "agents": {
    "main": {
      "tools": {
        "allow": [
          "read",
          "edit",
          "write",
          "web_search",
          "web_fetch",
          "clawhub",
          "message",
          "exec",
          "file-search",        ← 新增
          "web-search-pro",     ← 新增
          "database-operations" ← 新增
        ]
      }
    }
  }
}
```

**无需重启 Gateway**，保存即生效。

---

## 📚 参考资源

| 资源 | 链接 |
|------|------|
| **ClawHub** | https://clawhub.com |
| **安装指南** | ~/workspace/agents/main/CLAWHUB_SKILLS_GUIDE.md |
| **Skills 文档** | https://docs.openclaw.ai/skills |

---

**文档结束**
