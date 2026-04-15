---
name: wuhoo-news-rss
description: "RSS 资讯采集与检索引擎。通过 RSSHub + 原生 RSS 源自动采集多类别资讯，存储到 SQLite (FTS5 全文搜索)，支持关键词告警、热点评分、按类别/时间检索。wuhoo 冠名 skill 为 OpenClaw 企业级关键 skill，需重点维护。"
metadata: { "openclaw": { "emoji": "📰", "requires": { "bins": ["python3.11"], "pip": ["feedparser", "pyyaml"] } } }
---

# wuhoo-news-rss — RSS 资讯采集与检索引擎

> **⚠️ 企业级关键 Skill**
> 以 `wuhoo-` 冠头的 skill 是当前 OpenClaw 系统的**企业级关键 skill**，承担核心业务价值。
>
> **舆情管线优先数据源**：在辩论系统 (Workflow B/C/D) 中，RSS 舆情是综合评分的**最高权重**数据源 (50%)，优先于 TrendRadar 和 Web Search。

## 功能概述

通过 RSSHub（自部署）+ 原生 RSS 源，自动采集科技/AI/财经/投资/跨境电商/综合等多类别资讯，实现：

- **多源采集**: 同时从 RSSHub 路由和原生 RSS 源拉取
- **去重存储**: SQLite + FTS5 全文搜索
- **热点评分**: 关键词匹配 + 多源覆盖度评分
- **关键词告警**: 命中关注词自动标记
- **灵活检索**: 按类别/关键词/时间/热度检索

## 架构

RSSHub 容器以 `--network host` 模式运行，共享宿主机网络栈，可直接访问所有外部网站。

```
RSSHub (--network host, 端口 1200)    Python 采集引擎 (python3.11)
┌──────────────────────────┐         ┌─────────────────────────────┐
│ 5000+ 路由 (宿主机网络)    │         │ feedparser 解析              │
│ 网站 → RSS 转换           │──RSS──→│ SQLite + FTS5 存储           │
│ 同时兼容原生 RSS           │         │ 热点评分 + 关键词告警          │
└──────────────────────────┘         │ 检索接口                     │
       ↕ 外网直连                     └─────────────────────────────┘
                                              ↕
                                     Heartbeat / Cron
                                     每小时自动拉取
```

## 使用方式

```bash
cd ~/.openclaw/workspace/agents/main/skills/wuhoo-news-rss

# 注意：必须使用 Python 3.11+
# 系统默认 python3 是 3.6.8，请使用 /usr/bin/python3.11

# 拉取所有源
/usr/bin/python3.11 src/fetcher.py --fetch

# 按类别拉取
/usr/bin/python3.11 src/fetcher.py --fetch --category AI
/usr/bin/python3.11 src/fetcher.py --fetch --category 财经

# 查看源状态
/usr/bin/python3.11 src/fetcher.py --list

# 关键词搜索
/usr/bin/python3.11 src/fetcher.py --search "量化交易" --limit 10

# FTS5 全文搜索（更精准）
/usr/bin/python3.11 src/fetcher.py --fts "NVIDIA AND GPU"

# 热门文章
/usr/bin/python3.11 src/fetcher.py --top 20
/usr/bin/python3.11 src/fetcher.py --top 10 --category 财经 --hours 12

# 关键词告警
/usr/bin/python3.11 src/fetcher.py --keywords "AI,英伟达,量化交易" --hours 6

# JSON 输出模式（供程序调用）
/usr/bin/python3.11 src/fetcher.py --search "NVDA" --json
/usr/bin/python3.11 src/fetcher.py --top 10 --json
```

## 配置

### 添加新源

编辑 `feeds/config.yaml`:

```yaml
feeds:
  - name: "源名称"
    url: "https://example.com/feed.xml"       # 原生 RSS
    # 或 url: "http://127.0.0.1:1200/xxx/yyy"  # RSSHub 路由
    category: "类别"
    tags: ["标签1", "标签2"]
```

### 修改告警关键词

编辑 `src/fetcher.py` 中的 `KEYWORDS_ALERT` 列表。

### 修改拉取频率

编辑 `feeds/config.yaml` 中的 `settings.fetch_interval_minutes`。

## 数据输出

所有数据存储在 `data/news.db` (SQLite):
- `articles` 表：文章主数据
- `articles_fts` 表：FTS5 全文索引

## 与 TrendRadar 的关系

| 工具 | 定位 | 数据源 | 特点 | 权重 |
|------|------|--------|------|------|
| **wuhoo-news-rss** ⚠️ | 资讯内容 | RSSHub + RSS | 深度内容，可检索，可告警 | **50%** |
| **TrendRadar** | 热点榜单 | 42 平台爬虫 | 实时热搜，短平快 | 30-40% |
| **Web Search** | 个股精准舆情 | Tavily/Jina | 个股精准搜索 | 20% |

三者**并存互补**，wuhoo-news-rss 看"大家在关注什么新闻"，TrendRadar 看"大家在搜什么"，Web Search 提供个股精准舆情。

## 与辩论系统的集成

wuhoo-news-rss 通过 `debate/adapters/news_rss_adapter.py` 集成到 DataAggregator 的舆情管线：

```
DataAggregator._get_combined_sentiment()
  ├── 源1: RSSNewsAdapter (50% 权重) ← wuhoo-news-rss
  ├── 源2: TrendRadarAdapter (30-40% 权重)
  └── 源3: WebSearchAdapter (20% 权重)
        ↓
  加权平均 → sentiment_score (-1 ~ +1)
```

调用路径：`workflow_b_deep_analysis.py → DataAggregator → news_rss.get_sentiment_data(symbol, company_name)`

## 依赖

- **Python 3.11+**（系统默认 python3 是 3.6.8，请使用 `/usr/bin/python3.11`）
- `feedparser` - RSS 解析
- `pyyaml` - 配置解析
- RSSHub (Podman, `--network host`, 端口 1200)

## 版本

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.1 | 2026-04-13 | RSSHub 切换为 host 网络模式 + Python 版本检查 + 修复不可用路由 |
| 1.0 | 2026-04-13 | 初始版本：RSSHub + 原生 RSS 采集，SQLite 存储，FTS5 搜索 |
