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
                                     Cron Job (每日 09:30, deliver=origin)
                                     自动拉取 + 生成热点简报（微信推送）
```

## 使用方式

```bash
cd ~/wuhoo-workspace/skills/default/wuhoo-news-rss

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

## 热点评分体系 (v2.0, 2026-07-03)

三层加权评分系统，替代了旧的单一关键词匹配：

### 第 1 层：Feed 源基础权重 (1-10)
每个 RSS 源根据信息质量和信号密度预设基础分（`feed_weights` in `feeds/config.yaml`）：
- **10 分**: Financial Times（顶级财经源）
- **9 分**: Seeking Alpha, 华尔街见闻, 华尔街见闻热门, 路透社国际, OpenAI Blog, Google DeepMind, Anthropic Blog, Stratechery
- **8 分**: NYT Business, BBC Business, 第一财经, 格隆汇, TechCrunch, The Verge, 美联社, HuggingFace Blog, Google AI Blog
- **7 分**: IT之家, 36氪, 虎嗅, Ars Technica, BBC World, 卫报国际, BBC 中文, 纽约时报中文, 日经中文网
- **0 分**: 足球源（在投资简报中自动排除）
- 未配置源默认 3 分

详细架构、pitfall 和调试方法见 [`references/hot-score-architecture-v2.md`](references/hot-score-architecture-v2.md)。常见陷阱（`\b`中文失效、短关键词污染、INSERT遗漏评分字段）见 [`references/rss-hot-score-pitfalls.md`](references/rss-hot-score-pitfalls.md)。

### 第 2 层：关键词增强 (每个 +3 分)
`EXPANDED_KEYWORDS` 包含 200+ 个关键词覆盖：量化/交易、AI/大模型、半导体/芯片、电商/跨境、市场/宏观、公司/财报、科技/产业、A股/港股/美股个股、行业热点。使用 `\b` 词边界正则匹配避免子串误匹配（如 `PE` 不会匹配到 "Ramos" 中的 "pe"）。

### 第 3 层：模糊多源覆盖 (每个额外源 +8 分)
`_fuzzy_normalize()` 对标题去前缀（IT之家消息/36氪获悉）和标点归一化后取前 40 字符作为指纹，`Counter` 统计同事件多源覆盖度。

### 评分示例
- 格隆汇文章"Crypto billionaire Justin Sun sues..."：base=8 + keywords(crypto+NVIDIA+Bitcoin...共10个×3=30) + 多源覆盖=0 → **38 分**
- FT 文章"Tesla boosts spending..."：base=10 + keywords=0 → **10 分**
- BBC Sport 足球文章：base=0 → **0 分**（投资简报中自动过滤）

### ⚠️ 关键陷阱：`insert_article` 必须包含评分字段
旧版 `insert_article` SQL 中缺少 `hot_score`, `is_alert`, `alert_keywords` 列，导致尽管 `calc_hot_score` 正确计算了分数，但数据库始终存储默认值 0。修复时需确保 INSERT 语句包含这三列。

## 已知问题 / 注意事项

- **cron 环境禁止用绝对路径调用 python3.11 (2026-08-04)**：终端命令写成 `/usr/bin/python3.11 src/fetcher.py --fetch` 会触发 Hermes cron lifecycle guard 递归扫描该"被引用脚本"（含 `/` 的 executable token 被视为脚本），读取 ELF 二进制内容时崩溃 `ValueError: embedded null byte`。**必须用裸命令名**：`python3.11 src/fetcher.py --fetch`（guard 只扫描含 `/` 或 .sh 后缀的 executable）。execute_code 的 terminal() 同样受影响。
- **RSSHub 容器 Up 但 HTTP 000 (2026-08-04)**：19 个 RSSHub 路由源 Connection refused。恢复流程见 wuhoo-infra skill。Pitfall：`podman rm -f rsshub` 后必须确认删除成功再 `podman run`，`;` 串联时 rm 可能未生效导致 "container name already in use"；rm 后加 `sleep 2`。
- **RSSHub 路由大面积 503** (2026-07-03)：`seekingalpha`, `stcn`, `reddit`, `cls/telegraph` 等多个路由返回 503。Seeking Alpha 使用原生 `feed.xml` 绕过。需定期更新 RSSHub 版本或排查特定路由。
- **路透社国际 / B站排行榜 RSSHub 路由**：返回 HTML 而非 XML（`text/html is not an XML media type`）。B站排行榜周期性失效。
- **词边界匹配**：使用 `\b` regex 避免子串误匹配，但中文关键词的 `\b` 行为可能不完全理想。中文文本中 `\b` 依赖 Unicode 词边界，CJK 字符间无词边界。
- **路径硬编码**：调用 fetcher.py 时请使用绝对路径 `/home/admin/wuhoo-workspace/skills/default/wuhoo-news-rss/src/fetcher.py`，避免相对路径歧义。
- **手动简报生成模式**：当 cron 推送失败时，可通过 FTS5 JSON + Python 多查询模式手动生成。详见 [`references/manual-briefing-generation.md`](references/manual-briefing-generation.md)。
- **微信推送 gateway timeout**：cron delivery 阶段可能出现 `"Timeout context manager should be used inside a task"` 错误（非 session expired）。内容已生成但投递失败。临时方案：保存到本地文件，gateway 恢复后补发。
- **RSS 源失效诊断**：源诊断与替换工作流详见 [`references/rss-feed-diagnosis.md`](references/rss-feed-diagnosis.md)。
- **RSS 源验证方法**：系统性地测试新 RSS/RSSHub 路由可用性的标准流程，详见 [`references/rss-source-verification.md`](references/rss-source-verification.md)。
- **RSSHub 小红书路由限制**：仅 `/xiaohongshu/user` 路由可用，详见 [`references/rsshub-xiaohongshu-limitations.md`](references/rsshub-xiaohongshu-limitations.md)。

## Cron 自动简报

> **2026-07-03 更新**：09:30 cron 已恢复为 **`deliver=origin`**（微信推送）。hot_score 系统已全面修复，现在按真实热度排序。cron 配置详见 cronjob list。新增 7 个高质量源（Stratechery/Seeking Alpha/DeepMind/CoinDesk 等），移除 11 个死亡源。

### Cron 配置

- **Schedule**: `30 9 * * *`（每日 09:30）
- **Skills**: `wuhoo-news-rss`, `wuhoo-rss-briefing`
- **Delivery**: `origin`（微信推送）
- **流程**: fetch → SQLite 直查 → 噪音过滤 → 四类 TOP 5 输出

### 手动触发（备用）

用户发送"更新收集rss信息，并推送关键主题top新闻给我"即可触发：

1. **拉取**：`/usr/bin/python3.11 ~/wuhoo-workspace/skills/default/wuhoo-news-rss/src/fetcher.py --fetch`
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
| 2.0 | 2026-07-03 | **热点评分系统大修**：三层评分 (Feed权重 + 200关键词增强 + 模糊多源覆盖)；修复 `insert_article` 缺少 hot_score 列的严重 bug；修复 RSSNewsAdapter DB 路径 (skills/news-rss → skills/default/wuhoo-news-rss)；源清理：移除 11 个死亡源 (酷壳/cnbang/澎湃/品玩等)，合并 4 组冗余源；新增 7 个高质量源 (Stratechery/Seeking Alpha/Google DeepMind/CoinDesk/Meta/集思录/Google AI Blog)；关键词匹配增加 `\b` 词边界；RSSHub 路由大面积 503 标注 |
| 1.8 | 2026-06-18 | 足球源 7→10：新增 懂球帝早报, BBC Sport Football RSSHub 路由, Breaking The Lines；失效路由标注更新 |
| 1.7 | 2026-06-02 | 足球 RSS 源大修：4 个失效源替换为 Football Rankings/SoccerNews/World Soccer Talk/Football Italia |
| 1.6 | 2026-05-09 | 恢复 09:30 cron（deliver=local 绕过 Gateway asyncio bug），同时加载 wuhoo-rss-briefing skill |
| 1.5 | 2026-05-03 | 删除 09:30 cron 微信推送，改为手动触发模式 |
| 1.4 | 2026-05-02 | Cron push format finalized |
| 1.2 | 2026-05-01 | 修复路径错误，添加热点评分说明 |
| 1.1 | 2026-04-13 | RSSHub host 网络模式 + Python 版本检查 |
| 1.0 | 2026-04-13 | 初始版本 |
