---
name: wuhoo-news-rss
description: "RSS 资讯采集与检索引擎。通过 RSSHub + 原生 RSS 源自动采集多类别资讯，存储到 SQLite (FTS5 全文搜索)，支持关键词告警、热点评分、按类别/时间检索。wuhoo 冠名 skill 为 Hermes 企业级关键 skill，需重点维护。"
tags: ["wuhoo"]
category: wuhoo
metadata: { "hermes": { "emoji": "📰", "requires": { "bins": ["python3.11"], "pip": ["feedparser", "pyyaml"] } } }
---

# wuhoo-news-rss — RSS 资讯采集与检索引擎

> **⚠️ 企业级关键 Skill**
> 以 `wuhoo-` 冠头的 skill 是当前 Hermes 系统的**企业级关键 skill**，承担核心业务价值。
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
                                     Cron Job (每日 09:30, deliver=local)
                                     自动拉取 + 生成热点简报（local 日志，非微信推送）
```

## 使用方式

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-news-rss

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

调用路径：`wuhoo-stock-deep-analysis/strategy_report.py → DataAggregator → news_rss.get_sentiment_data(symbol, company_name)`

## 依赖

- **Python 3.11+**（系统默认 python3 是 3.6.8，请使用 `/usr/bin/python3.11`）
- `feedparser` - RSS 解析
- `pyyaml` - 配置解析
- RSSHub (Podman, `--network host`, 端口 1200)

## 已知问题 / 注意事项

- **`--top` 返回 hot_score=0.0**：当前热点评分系统未启用，`--top N` 按最近拉取时间排序而非实际热度。对于主题简报等需要按主题筛选的场景，应使用 `--fts` 全文搜索组合关键词查询来获取更精准的结果。
- **路径硬编码**：调用 fetcher.py 时请使用绝对路径 `/home/admin/wuhoo-workspace/skills/wuhoo/wuhoo-news-rss/src/fetcher.py`，避免相对路径歧义。
- **手动简报生成模式**：当 cron 推送失败时，可通过 FTS5 JSON + Python 多查询模式手动生成。详见 [`references/manual-briefing-generation.md`](references/manual-briefing-generation.md)。
- **微信推送 gateway timeout**：cron delivery 阶段可能出现 `"Timeout context manager should be used inside a task"` 错误（非 session expired）。内容已生成但投递失败。临时方案：保存到本地文件，gateway 恢复后补发。
- **RSS 源失效诊断**：ESPN(403)、Goal.com(404)、FIFA(不再提供RSS)、UEFA(超时) 已于 2026-06-02 确认失效并替换为 Football Rankings + SoccerNews + World Soccer Talk + Football Italia。源诊断与替换工作流详见 [`references/rss-feed-diagnosis.md`](references/rss-feed-diagnosis.md)。
- **RSS 源验证方法**：系统性地测试新 RSS/RSSHub 路由可用性的标准流程 (批量 HTTP 测试 + Debug Info 分析 + 内容抽样)，详见 [`references/rss-source-verification.md`](references/rss-source-verification.md)。
- **RSSHub 小红书路由限制**：仅 `/xiaohongshu/user` 路由可用（需 `XIAOHONGSHU_COOKIE`），无搜索/热榜/话题路由。关键词采集需使用 Python 替代方案 (XHS-Downloader)。详见 [`references/rsshub-xiaohongshu-limitations.md`](references/rsshub-xiaohongshu-limitations.md)。

## Cron 自动简报

> **2026-05-09 更新**：09:30 cron 已恢复，使用 **`deliver=local`** 绕过 Gateway asyncio timeout bug。简报保存到 cron 日志而非微信推送，需要时手动查看或转发。

### Cron 配置

- **Schedule**: `30 9 * * *`（每日 09:30）
- **Skills**: `wuhoo-news-rss`, `wuhoo-rss-briefing`
- **Delivery**: `local`（⚠️ 不使用 WeChat/auto，避免 asyncio `Timeout context manager` bug）
- **流程**: fetch → SQLite 直查 → 噪音过滤 → 四类 TOP 5 输出

### 手动触发（备用）

用户发送"更新收集rss信息，并推送关键主题top新闻给我"即可触发：

1. **拉取**：`/usr/bin/python3.11 ~/wuhoo-workspace/skills/wuhoo/wuhoo-news-rss/src/fetcher.py --fetch`
2. **分类生成**：使用 `wuhoo-rss-briefing` skill 的 SQLite 直查 + 噪音过滤 + 事件去重流程
3. **格式化输出**：按四大类各取 TOP，合并多源，微信 Markdown 格式

### 四大分类

| 分类 | 覆盖范围 |
|------|---------|
| 🔬 **科技/AI** | 技术突破、AI产品、大模型、半导体 |
| 💰 **财经/投资** | 港股/美股市场、量化、IPO、大宗商品 |
| 🏛️ **宏观政策** | 央行政策、地缘政治、贸易协定、监管 |
| 🏭 **产业/公司** | 重点公司动态、财报、并购、产品发布 |

### 微信推送格式规范

```markdown
# 📰 Wuhoo 新闻早报 — 2026-05-02

## 🔬 科技/AI
1. **文章标题** — 来源 | YYYY-MM-DD
   摘要一句话，不超过50字。

2. **热点话题** [3源] — 源A / 源B | YYYY-MM-DD
   多源报道同一事件时合并为一条，标注源数。

---

## 💰 财经/投资
1. ...

---

## 🏛️ 宏观政策
...
```

**格式规则**：
- 每条标题**加粗**，后附来源和日期
- 摘要一行，**不超过 50 字**
- 大类之间用 `---` 分隔
- 同主题不同来源的文章**合并为一条**，标注 `[N源]`
- 底部标注：总文章数、来源数、检索时间范围

### 主题简报（非微信场景）

生成多主题分类简报的标准流程：

1. **拉取**：`/usr/bin/python3.11 src/fetcher.py --fetch`
2. **多查询采集**：对每个主题运行 `--fts "<关键词>" --limit 30 --json`，覆盖所有目标主题
3. **去重分类**：按文章 hash 去重，再按预定义关键词表打分归类
4. **排序输出**：每个主题按匹配分降序、日期降序排列，取 TOP10
5. **格式化**：按 `【主题名称】\n 1. 标题 | 来源 | 热度分\n    摘要（100字内）` 格式输出

主题关键词表设计原则：
- 每个主题 20-50 个关键词，覆盖中英文、缩写、别名
- 关键词应包含名词（芯片/GPU）、品牌名（NVIDIA/英伟达）、技术术语（HBM/光刻）
- 避免过于通用的词汇（如"价格"），防止误匹配

## 版本

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.8 | 2026-06-18 | 足球源 7→10：新增 懂球帝早报 (RSSHub, 中文), BBC Sport Football RSSHub 路由, Breaking The Lines (战术分析)；失效路由标注更新 (虎扑/直播吧/fifa/espn 503)；新增 RSS 源验证方法参考文档 |
| 1.7 | 2026-06-02 | 足球 RSS 源大修：4 个失效源替换为 Football Rankings/ SoccerNews/ World Soccer Talk/ Football Italia；新增 RSS 源诊断参考文档 |
| 1.6 | 2026-05-09 | 恢复 09:30 cron（deliver=local 绕过 Gateway asyncio bug），同时加载 wuhoo-rss-briefing skill |
| 1.5 | 2026-05-03 | 删除 09:30 cron 微信推送（Gateway asyncio bug），改为手动触发模式；推送格式改用 wuhoo-rss-briefing skill 的 SQLite 直查流程 |
| 1.4 | 2026-05-02 | Cron push format finalized: 4 categories TOP10, merged multi-source articles [N源], 50-char summaries. WeChat delivery blocked by gateway asyncio timeout bug. |
| 1.2 | 2026-05-01 | 修复路径错误，添加热点评分说明，新增主题简报生成流程与脚本 |
| 1.1 | 2026-04-13 | RSSHub 切换为 host 网络模式 + Python 版本检查 + 修复不可用路由 |
| 1.0 | 2026-04-13 | 初始版本：RSSHub + 原生 RSS 采集，SQLite 存储，FTS5 搜索 |
