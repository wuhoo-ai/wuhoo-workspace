# 新闻/简报能力升级方案 v3（决策锁定 · 待审阅后施工）

日期：2026-11-16（v3，替代 v2；v1 审计数据、v2 源金字塔与集成细节全部保留）
状态：**D1-D4 已由用户拍板（见 §12），方案待用户最终审阅，审阅通过前不执行任何管线/基础设施改动。**

v3 修订依据（用户 2026-11-16 拍板原话）：
- D1：跨 profile，"我需要更精准的抓取我自己的喜好内容"。
- D2：A，"微信推简报+全量内容链接我自己打开读详细"；文本不友好可发 HTML，但注意微信文件大小限制；或以当前环境+域名给只读安全链接。
- D3：A（双轨 A/B），"要能够根据我的反馈和近期热点情况接受我的调节输入"。
- D4：A，"交给 hermes 统一投递"。

---

## 0. 版本演进

| 版本 | 核心变化 |
|---|---|
| v1 | 全面审计 + 八层架构 + P0/P1/P2 分阶段（已被取代） |
| v2 | 改一次性集成构建；源金字塔五层 + ~70 新源；TrendRadar 三容器 + MCP 27 工具；细节落到 DDL/伪码/公式/cron/prompt |
| **v3** | **锁定 D1-D4**；跨 profile 个人化落到真实读取路径与隐私边界（§8.6）；投递改为"微信简报 + 只读安全链接"主路径 + HTML 兜底，nginx 鉴权配置具体化（§8.1-8.4）；新增反馈/热点调节输入语义与即时生效机制（§8.7、§7）；新增施工授权清单（§14） |

---

## 1. 根因再诊断：数据源头不足的五重缺口

v1 审计实测（2026-11-16）：60 feed 仅 46 可用、14 硬故障、21 七日零产出，**有效源 37**；抓取 100% 集中每天 08:00；hot_score 95.7% 落 1-9 分（≥40 分 0 条）；事件合并率 7%（52/740）；29.3%（217/740）未分类丢弃；alert 命中 977 条/7 日零推送；投递 5 天 3 败。

"源头不足"不是单一的数量问题，是五重结构性缺口：

| # | 缺口 | 现状证据 | 后果 |
|---|---|---|---|
| G1 | **数量缺口** | 有效 37 源，日产 ~600 条，高度集中（第一财经 350/7日、IT之家 349/7日，长尾极薄） | 覆盖面窄，冷门但重要的事件无源可采 |
| G2 | **类型缺口** | 全是"媒体文章"：无官方公告、无实时电报、无社会热榜、无开发者信号、无游戏垂直源 | 只看得到"别人写好的报道"，看不到"正在发生的事"和"社区在讨论什么" |
| G3 | **一手性缺口** | 零一手源：无 SEC/交易所公告、无央行原文、无公司 IR、无 arXiv 原文、无 GitHub release | 全是二手转述，无法核验，时效滞后于源头 |
| G4 | **时效缺口** | 日级快照（08:00 一次），配置 60 分钟从未生效 | 白天大事次日才见；"热点"无从谈起 |
| G5 | **独立性缺口** | 8 个高价值源全押 feedx.net 单点；通讯社通稿被多家转载算"多源" | 单点故障一次丢 8 源；"多源覆盖"是假象，热度被通稿灌水 |

**根治思路**：重建**源金字塔**——按"一手性 × 时效 × 独立性"分层供给，每层有明确职责和冗余，汇入同一个事件中心；并用**跨 profile 个人化**让源本身按用户喜好定制（per-ticker 公告源、per-项目技术源），而不只是对通用新闻重排序。

---

## 2. 源金字塔：五层架构 + 具体扩容清单

### 2.1 分层职责

```
T0 一手/官方   ground truth，低噪声，canonical 优先    公告/财报/央行/交易所/arXiv/GitHub release
T1 实时快讯    速度层，分钟级，事件首发信号            财联社电报/金十/华尔街见闻live/富途/GDELT
T2 深度媒体    解释层，小时-天级，分析与背景           现有 FT/BBC/卫报/第一财经 + 修复 + 新增
T3 社会热度    信号层，只贡献 velocity 不进正文        TrendRadar 热榜(微博/知乎/百度/抖音/B站/头条…)
T4 垂直纵深    用户业务层，按兴趣档案加权              游戏(Unity/GDC/葡萄/GameDiscoverCo)/AI(HF/官博)/量化(arXiv q-fin)
```

原则：
- **canonical 代表作按 T0>T1>T2>T3 优先**（一手原文压过转述）。
- **独立源计数去通稿**：同一通讯社稿源（Reuters/AP/彭博通稿）只算 1 个独立源，避免 G5 灌水。
- **T3 只进 velocity 信号**，热榜标题党不直接进简报正文。
- **每层有冗余**：feedx 8 源各配直连/镜像备胎；RSSHub 路由配原生 RSS 备胎。
- **T0/T4 按个人化动态生成**：持仓 ticker → per-ticker EDGAR/finviz/seekingalpha 源；guimei 技术栈 → 对应 Unity/AI 源加权（§8.6）。

### 2.2 扩容清单（约 70 新源，精确路由/URL）

状态标注：【文档】=RSSHub 官方文档确认路由存在；【原生】=官方 RSS/Atom 直连；【待测】=候选，WP0 实测验收。所有路由以本机 RSSHub 实测为准（镜像升级后复测）。**本次会话候选路由实测被安全闸拦下（未授权），已列为 WP0 施工首步，需用户授权后执行（§14）。**

#### T0 一手/官方（新增 ~14）

| 源 | 路由/URL | 语言 | 状态 | 备注 |
|---|---|---|---|---|
| 上交所公告披露 | `/sse/disclosure/:query?`（productId=持仓股） | zh | 【文档】 | 按持仓 ticker 动态订阅 |
| 上交所科创板动态 | `/sse/renewal` | zh | 【文档】 | IPO/再融资审核 |
| 北交所要闻/发行/监管 | `/bse/important_news`、`/bse/fxrz_list`、`/bse/cxjg_list`、`/bse/audit_result` | zh | 【文档】 | **用户北交所打新直接相关** |
| 深交所公告 | `/szse/:category?` | zh | 【待测】 | WP0 验证 |
| 港交所披露易 | `/hkex/:category?` | zh | 【待测】 | 港股持仓相关 |
| 央行沟通交流 | `/gov/pbc/goutongjiaoliu` | zh | 【文档】 | 依赖 Puppeteer，需 browserless |
| 央行公开市场公告 | `/gov/pbc/tradeAnnouncement` | zh | 【文档】 | 依赖 Puppeteer |
| 央行政策研究/工作论文 | `/gov/pbc/zcjl`、`/gov/pbc/gzlw` | zh | 【文档】 | |
| SEC EDGAR 8-K/10-Q/S-1 | `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=8-K&output=atom` | en | 【原生】 | **按 watchlist ticker 自动生成**；另用 EDGAR 全文搜索 API |
| GitHub Release（跟踪仓库） | `https://github.com/{owner}/{repo}/releases.atom` | en | 【原生】 | Unity 相关 OSS、自研仓库、关键依赖 |
| arXiv cs.AI/cs.CL/cs.LG/cs.GR/q-fin | `http://arxiv.org/rss/{cat}` | en | 【原生】 | **替换现有空路由**；cs.GR 图形学供游戏开发 |
| 美联储 press releases | `https://www.federalreserve.gov/feeds/press_all.xml` | en | 【原生】 | 宏观 |
| ECB press | `/ecb/press` 或原生 | en | 【待测】 | |
| 外交部/国防部例行 | `/gov/mfa/:category?`、`/gov/mod/:category?` | zh | 【待测】 | 地缘 |

#### T1 实时快讯（新增 ~10）

| 源 | 路由/URL | 语言 | 状态 | 备注 |
|---|---|---|---|---|
| 财联社电报-全部 | `/cls/telegraph` | zh | 【文档】 | 分钟级电报 |
| 财联社电报-加红 | `/cls/telegraph/red` | zh | 【文档】 | **重要快讯，告警主力** |
| 财联社电报-公司/港股 | `/cls/telegraph/announcement`、`/cls/telegraph/hk` | zh | 【文档】 | |
| 财联社深度 | `/cls/depth/1000` | zh | 【文档】 | |
| 金十数据-重要 | `/jin10/1` | zh | 【文档】 | important=1 只看重要 |
| 华尔街见闻实时 | `/wallstreetcn/live` | zh | 【待测】 | 现有 news 路由保留 |
| 富途牛牛要闻 | `/futunn/highlights` | zh | 【文档】 | **用户用 Futu，直接相关** |
| 格隆汇首页/快讯 | `/gelonghui/home`、`/gelonghui/live` | zh | 【文档】 | 现有保留+补快讯 |
| 中证快讯 | `/cs/news/zzkx` | zh | 【文档】 | |
| GDELT DOC 2.0 | `https://api.gdeltproject.org/api/v2/doc/doc?query={entity}&mode=ArtList&format=json&maxrecords=75&timespan=24h` | 100+语言 | 【原生API】 | 免费无 key，15min 更新；按 watchlist 实体轮询；TimelineMode 取传播速度 |

#### T2 深度媒体（修复 14 + 新增 ~16）

修复（具体替换）：
| 坏源 | 替换方案 |
|---|---|
| Hacker News 503 | 原生 `https://hnrss.org/frontpage`（+`/best`） |
| 美联社 503 | RSSHub `/apnews/:category?` 复测，备胎 feedx 镜像 |
| 半岛 503 | `/aljazeera/:category?` 复测，备胎原生 `https://www.aljazeera.com/xml/rss/all.xml` |
| CoinDesk 403 | 原生 `https://www.coindesk.com/arc/outboundfeeds/rss/` |
| Stratechery 403 | feedx 镜像（付费墙，仅摘要） |
| 36氪空 | `/36kr/newsflashes`（快讯）+ `/36kr/information/web_news` |
| arXiv×2 空 | 原生 arxiv.org/rss（见 T0） |
| Telegraph 402 | 移除（付费墙无解），卫报/FT 已覆盖 |
| 5 个超时源 | 镜像升级后复测；仍超时则降频/移除 |
| 3 个陈旧源 | 移除或换路由 |

新增：
| 源 | 路由/URL | 状态 |
|---|---|---|
| 机器之心 | `/jiqizhixin/:category?` | 【待测】 |
| 量子位 | `/qbitai/:category?` | 【待测】 |
| 新智元 | `/xinzhiyuan/:category?` | 【待测】 |
| 晚点 LatePost | `/latepost/:category?` | 【待测】 |
| 钛媒体 | `/tmtpost/:category?` | 【待测】 |
| 界面新闻 | `/jiemian/:category?` | 【待测】 |
| 财新（免费最新） | `/caixin/:category?` | 【待测】 |
| 环球网/观察者网/参考消息 | `/huanqiu/:category?`、`/guancha/:category?`、`/cankaoxiaoxi/:category?` | 【待测】 |
| MIT Tech Review | `/technologyreview/:category?` | 【待测】 |
| InfoQ | `/infoq/:category?` | 【待测】 |
| CNBC | 原生 `https://www.cnbc.com/id/100003114/device/rss/rss.html` | 【原生】 |
| MarketWatch | 原生 `http://feeds.marketwatch.com/marketwatch/topstories/` | 【原生】 |
| Yahoo Finance | 原生 `https://finance.yahoo.com/news/rssindex` | 【原生】 |
| 智通财经（港股/美股/公告） | `/zhitongcaijing/hkstock`、`/zhitongcaijing/meigu`、`/zhitongcaijing/announcement` | 【文档】 |
| 巴伦周刊中文 | `/barronschina` | 【文档】 |
| finviz 个股新闻 | `/finviz/news/{ticker}` | 【文档】 | **按 watchlist ticker 生成** |

#### T3 社会热度（TrendRadar 供给，~15-20 平台）

由 TrendRadar 统一采集（数据源 newsnow，自建），**不逐个配 RSS**：
- 默认配置已含：toutiao、baidu、wallstreetcn-hot、thepaper、bilibili-hot-search、cls-hot、ifeng、tieba、weibo、douyin、zhihu（11 个）
- 按 newsnow 支持列表扩展（部署时以 MCP Resource `config://platforms` 实测为准）：ithome、36kr、sspai、juejin、github-trending、producthunt、hackernews、v2ex、linuxdo、nodeseek 等
- 职责：**只贡献 velocity 信号**（rank 0.6/frequency 0.3/hotness 0.1），热榜标题不进简报正文

#### T4 垂直纵深（新增 ~15）

游戏（用户独立游戏开发，guimei）：
| 源 | 路由/URL | 状态 |
|---|---|---|
| Unity Blog | 原生 `https://blog.unity.com/feed` 或 `/unity/blog` | 【待测】 |
| Unity Releases | `/unity/release` | 【待测】 |
| GameDiscoverCo | 原生 `https://newsletter.gamediscover.co/feed` | 【原生】 | **独立游戏商业分析，高价值** |
| gamesindustry.biz | 原生 `https://www.gamesindustry.biz/feed` | 【原生】 |
| 游戏葡萄 | `/youxiputao/:category?` | 【待测】 |
| GameLook | `/gamelook/:category?` | 【待测】 |
| 触乐 | `/chuapp/:category?` | 【待测】 |
| 游研社 | `/yystv/:category?` | 【待测】 |
| indienova | `/indienova/:category?` | 【待测】 |
| Steam 新闻（跟踪游戏） | 原生 `https://store.steampowered.com/feeds/news/app/{appid}` | 【原生】 |
| GDC Vault | `/gdc/:category?` 或原生 | 【待测】 |

AI/量化（用户数字内容+投资）：
| 源 | 路由/URL | 状态 |
|---|---|---|
| Anthropic News | `/anthropic/news` | 【待测】 |
| HuggingFace Papers | `/huggingface/papers` 或原生 | 【待测】 |
| Import AI（Jack Clark） | 原生 `https://importai.substack.com/feed` | 【原生】 |
| The Batch（DeepLearning.AI） | 原生 `https://www.deeplearning.ai/the-batch/rss/` | 【待测】 |
| Seeking Alpha 个股 | `/seekingalpha/{symbol}/news`、`/transcripts` | 【文档】 | **按 watchlist** |
| Unusual Whales | `/unusualwhales/news` | 【文档】 | 期权异动 |

**扩容后目标**：T0 ~14 + T1 ~10 + T2 ~40（修复后）+ T3 ~20 平台 + T4 ~15 ≈ **有效供给 ≥120**。WP0 实测后出最终清单，达不到则补候选。

---

## 3. 总体架构（事件中心 + 三源汇流 + agent 原生 + 跨 profile 个人化）

```
┌─ 供给层 ────────────────────────────────────────────────┐
│ RSSHub(升级+browserless)  ── T0/T1/T2/T4 ~100 源 ──┐    │
│ 原生 RSS/Atom/EDGAR/GDELT ── 直连冗余 ────────────┤    │
│ TrendRadar(+自建 newsnow) ── T3 热榜 ~20 平台 ────┤    │
│ per-ticker/per-项目源 ── 由兴趣档案动态生成 ──────┤    │
└───────────────────────────────────────────────────┼────┘
                                                    ▼
┌─ 事件中心（news.db 扩展，增量不推倒）─────────────────────┐
│ L2 规范化 → L3 向量聚类 → L4 LLM富化 → L5 salience排序     │
│ → L6 逐事件四段卡合成 + 数字核验 + 链接引用                │
└───────────────────────────────────────────────────┬────┘
                                                    ▼
┌─ 投递层（D2/D4：Hermes 统一投递）────────────────────────┐
│ 微信简报(08:00,≤4KB,摘要+全量链接) + watchlist告警(15min) │
│ 只读安全链接 https://wuhoo.shanavasa.click/news/ (TLS+鉴权)│
│ HTML 文件兜底(MEDIA:附件,≤100KB) + 网页全文卡/检索/归档    │
└───────────────────────────────────────────────────┬────┘
                                                    ▼
┌─ Agent 原生层（Hermes 本体）─────────────────────────────┐
│ skill wuhoo-news-intel: fetch/audit/cluster/rank/brief/   │
│   alert/search/timeline/dive/watch/profile/tune/sync/health│
│ MCP trendradar(27工具): 热榜/趋势/情感/跨平台/全文/爬取    │
│ 跨 profile 个人化(D1): 读 trader持仓/gamedev项目→定制源+权重│
│ 调节输入(D3): "多点X/少点Y/最近关注Z/这条没用"→即时生效    │
│ 反馈闭环: 隐式(追问/收藏)+显式(有用/没用) → 周更权重        │
└──────────────────────────────────────────────────────────┘
```

三源分工不重叠：
- **RSSHub + 原生 RSS**：owns 全部 RSS 文章（T0/T1/T2/T4），fetcher.py 统一抓取。
- **TrendRadar**：owns 热榜平台（T3），`rss.enabled=false` 避免双抓；只供 velocity + MCP 分析工具。
- **GDELT**：owns 全球传播速度/跨语言覆盖，按 watchlist 实体轮询 DOC API。

---

## 4. TrendRadar 集成细节（落到命令和配置）

### 4.1 部署（podman，与现有 rsshub/v2ray 同栈）

```bash
# 1) 自建 newsnow（去除共享 API 单点依赖；TrendRadar 数据源）
podman run -d --name newsnow --restart=always \
  -p 127.0.0.1:4444:4444 \
  -v newsnow_data:/usr/app/.data \
  -e INIT_TABLE=true -e ENABLE_CACHE=true -e HOST=0.0.0.0 -e PORT=4444 \
  ghcr.io/ourongxing/newsnow:latest
# 国内镜像备选: ghcr.nju.edu.cn/ourongxing/newsnow:latest

# 2) TrendRadar 主程序（采集+存储，不推送）
mkdir -p ~/trendradar/{config,output}
podman run -d --name trendradar --restart=always \
  -v ~/trendradar/config:/app/config:ro \
  -v ~/trendradar/output:/app/output \
  wantcat/trendradar:latest

# 3) TrendRadar MCP Server（共享 output 数据卷）
podman run -d --name trendradar-mcp --restart=always \
  -p 127.0.0.1:3333:3333 \
  -v ~/trendradar/config:/app/config:ro \
  -v ~/trendradar/output:/app/output:ro \
  wantcat/trendradar-mcp:latest
```

### 4.2 config.yaml 关键值（~/trendradar/config/config.yaml）

```yaml
app: { timezone: "Asia/Shanghai" }
schedule: { enabled: false }          # 由 Hermes cron 驱动 trigger_crawl
platforms:
  enabled: true
  api_url: "http://127.0.0.1:4444/api/s"   # 指向自建 newsnow
  sources:                            # 以 config://platforms Resource 实测列表为准
    - { id: "cls-hot", name: "财联社热门", expected_domain: "cls.cn" }
    - { id: "wallstreetcn-hot", name: "华尔街见闻", expected_domain: "wallstreetcn.com" }
    - { id: "weibo", name: "微博", expected_domain: "weibo.com" }
    - { id: "zhihu", name: "知乎", expected_domain: "zhihu.com" }
    - { id: "baidu", name: "百度热搜", expected_domain: "baidu.com" }
    - { id: "douyin", name: "抖音", expected_domain: "douyin.com" }
    - { id: "toutiao", name: "今日头条", expected_domain: "toutiao.com" }
    - { id: "bilibili-hot-search", name: "B站热搜", expected_domain: "bilibili.com" }
    - { id: "thepaper", name: "澎湃", expected_domain: "thepaper.cn" }
    - { id: "ifeng", name: "凤凰网", expected_domain: "ifeng.com" }
    # + github-trending/producthunt/hackernews/ithome/36kr/sspai/juejin/v2ex 等（实测后补）
rss: { enabled: false }               # RSS 归 fetcher，避免双抓
report: { mode: "incremental", display_mode: "keyword", rank_threshold: 5 }
filter: { method: "keyword" }         # frequency_words.txt 由 watchlist 同步生成
notification: { enabled: false }      # D4 已定：统一 Hermes 投递
storage:
  backend: "local"
  formats: { sqlite: true, txt: false, html: true }
  local: { data_dir: "output", retention_days: 90 }
ai_analysis: { enabled: false }       # 分析归 Hermes 合成层
advanced:
  crawler: { request_interval: 2000, use_proxy: false }
  weight: { rank: 0.6, frequency: 0.3, hotness: 0.1 }
```

### 4.3 MCP 注册进 Hermes（agent 原生获得 27 工具）

`~/.hermes/config.yaml` 追加：
```yaml
mcp_servers:
  trendradar:
    url: "http://127.0.0.1:3333/mcp"
    timeout: 180
    connect_timeout: 60
```
- 生效需重启 gateway——**与待办的 8642 收尾 /restart 合并为同一次重启**（§14 授权项）。
- 验证：`hermes mcp list` + `hermes mcp test trendradar`（不耗模型调用）。
- 工具前缀 `mcp_trendradar_*`，27 工具（已对官方 docs/mcp 2026-07-07 逐类核实）：

| 工具组 | 工具 | agent 用途 |
|---|---|---|
| 基础查询 | get_latest_news / get_news_by_date / get_trending_topics | "今天有什么热点"；**D3 热点调节输入用它检测近期热点** |
| 智能搜索 | search_news / find_related_news | 事件关联发现 |
| 深度分析 | analyze_topic_trend / analyze_data_insights / analyze_sentiment / aggregate_news / compare_periods / generate_summary_report | "特斯拉这周趋势""对比本周上周" |
| RSS 查询 | get_latest_rss / search_rss / get_rss_feeds_status | 源状态巡检 |
| 全文读取 | read_article / read_articles_batch（Jina，≤5篇） | 深挖取正文（与 web_extract 互为备胎） |
| 推送 | send_notification / get_channel_format_guide / get_notification_channels | **D4 已定关闭，不用** |
| 系统 | get_current_config / get_system_status / resolve_date_range / check_version / trigger_crawl | cron 驱动爬取、日期解析 |
| 存储 | sync_from_remote / get_storage_status / list_available_dates | 数据就绪检查 |

- MCP Resources（4 个）：`config://platforms`、`config://rss-feeds`、`config://keywords`、`data://available-dates`——WP1 用 platforms 实测定 T3 清单。
- 安全：GPL-3.0，**独立容器 + MCP/数据卷读取集成，不链接代码进 Hermes**，许可证隔离。HTTP 模式（容器自管生命周期）。

### 4.4 数据流共享

- TrendRadar `output/` 按日期分文件夹存 SQLite + HTML；主程序与 MCP 共享卷。
- 事件中心 batch 侧读 `output/{date}/*.sqlite` 取热榜排名轨迹 → velocity（schema 部署后实测，WP1 验收）。
- agent 侧走 MCP（自然语言），batch 侧走文件/SQLite（确定性），两路不冲突。
- cron 每 30min `trigger_crawl(save_to_local=true)` 驱动采集。

---

## 5. RSSHub 治理细节

| 项 | 具体动作 | 验收 |
|---|---|---|
| 镜像升级 | `podman pull docker.io/diygod/rsshub:latest` → 重建容器（保留 1200 映射）；升级前备份配置 | 版本日期更新；现有 OK 路由回归不退化 |
| Puppeteer 依赖 | T0 央行/部分 gov 路由需浏览器渲染 → 部署 browserless（`browserless/chrome`），RSSHub 配 `PUPPETEER_WS_ENDPOINT` | `/gov/pbc/goutongjiaoliu` 实测 200 |
| 路由实测 | WP0 对 §2.2 全部【待测】路由逐个 curl 实测（**需用户授权，§14**），出 `route_verification.json` | 每个新源有实测状态码+条目数 |
| 坏源修复 | 按 §2.2 T2 修复表替换；feedx 8 源各配直连/镜像备胎，主备自动切换 | 硬故障 14→≤5；feedx 单点消除 |
| 源健康表 | `feed_health(feed_id, last_ok, last_err, fail_streak, items_7d, avg_latency, status)`；连续 5 次失败自动 disabled；每周一 07:00 巡检 | 21 零产出源全有状态；死源不耗抓取 |
| 条件 GET | fetcher 增 ETag/Last-Modified 缓存 | 304 比例可观测 |

---

## 6. 事件中心核心（schema + 算法 + 公式）

### 6.1 新增表（news.db 增量，不动现有 articles/FTS5）

```sql
CREATE TABLE events (
  event_id INTEGER PRIMARY KEY,
  label TEXT, topic TEXT,
  first_seen TEXT, last_seen TEXT,
  canonical_id INTEGER, salience REAL,
  n_indep_sources INTEGER, status TEXT DEFAULT 'active'
);
CREATE TABLE event_members (
  event_id INTEGER, article_id INTEGER, similarity REAL,
  PRIMARY KEY(event_id, article_id)
);
CREATE TABLE entities (
  entity_id INTEGER PRIMARY KEY, name TEXT, type TEXT, aliases TEXT
);
CREATE TABLE event_entities (event_id INTEGER, entity_id INTEGER, role TEXT);
CREATE TABLE event_facts (
  event_id INTEGER, claim TEXT, numbers TEXT, source_article_id INTEGER,
  verified INTEGER DEFAULT 0
);
CREATE TABLE article_vectors (article_id INTEGER PRIMARY KEY, emb BLOB);  -- 384d float32
CREATE TABLE interest_profile (
  key TEXT PRIMARY KEY,      -- topic:xxx / entity:xxx / keyword:xxx / source_pref:xxx
  weight REAL, updated TEXT,
  source TEXT,               -- coldstart/feedback/manual/crossprofile
  origin_profile TEXT,       -- default/trader/gamedev（跨 profile 来源标记）
  expires TEXT               -- 临时热点 boost 的过期时间（NULL=长期）
);
CREATE TABLE watchlist (
  id INTEGER PRIMARY KEY, kind TEXT, value TEXT,
  threshold REAL, alert_channel TEXT, enabled INTEGER, origin_profile TEXT
);
CREATE TABLE topic_burst (    -- D3 近期热点临时调节
  topic TEXT PRIMARY KEY, boost REAL, reason TEXT, expires_ts TEXT
);
CREATE TABLE feedback (       -- D3 反馈日志
  id INTEGER PRIMARY KEY, event_id INTEGER, kind TEXT,  -- useful/not_useful/more/less/mute
  raw_text TEXT, ts TEXT, applied INTEGER DEFAULT 0
);
CREATE TABLE feed_health (...);  -- 见 §5
CREATE TABLE velocity_signals (
  event_id INTEGER, ts TEXT, source TEXT, rank INTEGER, mention_count INTEGER, hotness REAL
);
```

### 6.2 向量与聚类（已定案）

- **模型**：`paraphrase-multilingual-MiniLM-L12-v2`（384 维，多语，CPU ~10ms/篇），**fastembed（ONNX）** 加载避免 torch；模型 ~470MB，HF 慢则 hf-mirror.com。备选 qwen text-embedding API（WP3 实测决定）。
- **存储**：SQLite BLOB + numpy 暴力余弦。~1500 篇/日 × 72h ≈ 4500 向量，毫秒级，**无需向量数据库**。
- **聚类**（增量）：
  ```
  for art in new_articles:
    v = embed(art.title + " " + art.summary)
    sims = cosine(v, recent_vectors(window=72h))
    best = argmax(sims)
    if sims[best] >= 0.88: merge(art, event_of[best])
    elif sims[best] >= 0.82 and entity_overlap(art, event_of[best]) >= 1: merge(...)
    else: new_event(art)
  ```
- **canonical**：`tier_bonus(T0=1.5,T1=1.2,T2=1.0,T3=0.8) × fulltext_len × number_density × source_weight` 取最高。
- **独立源计数**：簇内按原始稿源归并（Reuters/AP/彭博通稿识别），同稿源只计 1。

### 6.3 富化与排序

- **LLM 抽取**（qwen flash 批量 JSON）：每日候选 TOP ~100 事件代表作 → entities/numbers/claims。
- **salience**：
  ```
  S = W_source × (1 + ln(1 + N_indep)) × V × D × P × B
  V = 1 + normalize(热榜排名上升速度 + GDELT mention 增速)
  D = exp(-Δt_hours / 12)                 # 半衰 12h
  P = (1 + interest_profile 匹配增益, 上限2.0) × (1 + topic_burst.boost)   # D3 热点调节叠加
  B = tier_bonus
  ```
  TOP5 分差 ≥15（归一化 0-100）。替代"关键词×3"。

### 6.4 合成与核验

- 每日 TOP 20-30 事件，逐条**四段卡**：
  ```
  【事件标题】[N独立源] [topic]
  事实：…（仅来源内事实，数字带单位）
  影响：…（为什么重要，一句话）
  分歧/未核实：…（多源数字不一致标注；无则省略）
  下一步关注：…
  来源：url1 | url2 | url3（≥2 链接）
  ```
- **数字核验**：每个数字须能在 ≥1 来源正文正则匹配，否则标"未核实"。
- **全文**：TOP 事件 web_extract（firecrawl）；备胎 TrendRadar read_articles_batch（Jina）。付费墙仅摘要。
- **prompt 骨架**：system 固定"只允许来源内事实/数字可溯源/不编造链接"，user 给簇成员标题+摘要+全文片段。每事件 ~1.5K in / 300 out。

---

## 7. Agent 原生能力（一次性建成）

### 7.1 新技能 wuhoo-news-intel（scripts/intel.py CLI）

| 子命令 | 功能 | 触发示例 |
|---|---|---|
| `fetch [--all/--feed X]` | 驱动采集（幂等） | cron / 手动 |
| `audit` | 源健康巡检 + 路由实测 | 每周一 cron |
| `cluster` | 增量聚类 | 每批 fetch 后 |
| `rank` | salience 排序 | 简报前 |
| `brief [--date] [--format wechat/html/web]` | 生成日报（微信版+网页版+HTML兜底） | 08:00 cron |
| `alert` | watchlist 巡检 + 告警 | 15min cron |
| `search <query>` | FTS5 + 向量混合检索 | "搜最近固态电池新闻" |
| `timeline <entity/event_id>` | 实体/事件时间线 | "昨天那条有后续吗" |
| `dive <event_id>` | 簇内全文→交叉核验→带引用深挖报告 | "深挖第3条" |
| `watch add/list/remove` | watchlist 管理 | "盯着英伟达财报" |
| `profile show/update` | 兴趣档案查看/手改 | "看看我的兴趣档案" |
| **`tune <自然语言>`** | **D3 调节输入解析→即时改权重/混排/热点boost** | "多点量化监管，少点足球" |
| **`sync-profiles`** | **D1 跨 profile 同步（读 trader/gamedev→定制源+权重）** | 周更 cron / "更新我的兴趣" |
| `health` | 管线指标/投递账本/容器状态 | 运维 |

### 7.2 对话场景（WP5 验收用例，7 个）

1. **深挖**："深挖简报第3条" → `dive event_id` → 簇内 web_extract 全文 → 数字/主张交叉核验 → 带引用报告（回复 + 落网页 /news/event/<id>.html）。
2. **时间线**："上周苹果换帅后来怎样了" → `timeline entity:Apple` → events 时间排序 + MemPalace 历史结论 → 演进摘要。
3. **watchlist**："盯着财联社加红里含'固态电池'的，重要推我" → `watch add keyword 固态电池 threshold=red` → 15min 巡检命中即推。
4. **趋势对比**："对比本周上周 AI 热点" → MCP compare_periods + 事件库统计 → 上升/下降/新出现。
5. **反馈调节（D3）**："这条没用，多点量化监管" → `tune` 解析 → event 标 not_useful + topic:量化监管 weight +0.2 **即时生效**（不等周更）+ feedback 入档。
6. **近期热点调节（D3）**："最近固态电池很热，多推点相关的" → agent 用 MCP get_trending_topics 确认热点 → `topic_burst` 设 topic:固态电池 boost=0.5 TTL 7天 → salience P 因子叠加 → 7天后自动回落。
7. **跨 profile 精准（D1）**："更新我的兴趣" → `sync-profiles` → 读 trader 最新持仓报告 ticker + gamedev guimei 技术栈 → 生成 per-ticker EDGAR/finviz 源 + 调整 T4 权重 → 回报"新增盯盘 NVDA/AAPL，游戏源权重↑"。

### 7.3 与现有 Hermes 能力的关系

- 不新增 MCP server（除 TrendRadar），intel.py 走 skill 脚本，符合单 hub 铁律。
- 深挖/检索复用 web_extract、FTS5、MemPalace；TrendRadar MCP 补热榜/趋势/情感/全文。
- 简报条目带 event_id 序号，微信里引用序号触发深挖；全量链接见 §8。
- **跨 profile 只读不写**：sync-profiles 仅读取其他 profile 的记忆/产物，绝不修改 trader/gamedev 的任何文件（遵守 profile 隔离规则，用户已授权读取）。

---

## 8. 投递与个人化（D1/D2/D3/D4 锁定）

### 8.1 投递总策略（D2 + D4）

**主路径 = 微信推简报摘要 + 全量内容只读安全链接，用户自己打开读详细。** Hermes 统一投递（D4），TrendRadar 自带推送关闭。

```
每日 08:00：
  微信 ← 简报摘要(≤4KB：头部统计 + 四主题TOP5精简卡 + watchlist命中 + 全量链接 + "回复序号深挖")
  用户点开链接 → https://wuhoo.shanavasa.click/news/daily/2026-11-16.html
                 (TLS + basic auth 只读；全文四段卡 + ≥2来源链接 + 检索 + 归档)
  文本不友好/链接不便时兜底：微信发 HTML 文件附件(MEDIA:，≤100KB，自包含inline CSS)
实时：
  watchlist 命中 → 微信告警(≤2KB) + 事件深链 /news/event/<id>.html
```

### 8.2 微信简报（08:00）

- 结构：头部（日期/独立源数/事件数）→ 四主题 TOP5（标题+影响句+event_id 序号）→ watchlist 命中专区 → **全量链接 1 条** → "深挖请回复序号"。
- 体积 **≤4KB**（iLink 限流教训：64KB 必触限流）；微信只推摘要+入口，全文在链接。
- 每条有影响句；全量链接指向当日网页（含所有来源 URL，解决 v1"0 链接"）。

### 8.3 只读安全链接（nginx /news/，具体配置）

现状（已核实）：`/etc/nginx/conf.d/hermes-dashboard.conf`，443 TLS（wuhoo.shanavasa.click，证书 /etc/nginx/ssl/wuhoo.shanavasa.click/），`location /` 反代 127.0.0.1:9119 仪表盘，鉴权在应用层（nous 登录），nginx 层无 basic auth。

**新增独立 location（WP6 施工，需 sudo 授权 §14）**：
```nginx
# 追加到 443 server 块内（hermes-dashboard.conf）
location /news/ {
    alias /home/admin/wuhoo-workspace/news-web/;
    auth_basic "Wuhoo News";
    auth_basic_user_file /etc/nginx/.htpasswd-news;   # 独立凭据，与仪表盘分离
    autoindex off;                                     # 禁目录列表
    default_type text/html;
    add_header X-Content-Type-Options nosniff always;
    limit_except GET HEAD { deny all; }                # 只读：仅 GET/HEAD
}
```
- **只读**：纯静态文件，无写端点，`limit_except GET HEAD` 拒绝其他方法。
- **安全**：TLS（已有）+ basic auth（独立账号，`htpasswd -c /etc/nginx/.htpasswd-news wuhoo` 创建，密码口头交付不入库）+ 禁目录列表 + nosniff。
- **权限**：news-web/ 目录 755、文件 644（admin 属主，nginx worker 可读）；生成器只写该目录。
- **URL 方案**：
  - 日报：`/news/daily/YYYY-MM-DD.html`
  - 事件深卡：`/news/event/<event_id>.html`
  - 检索：`/news/search.html`（前端 FTS 查询页，只读）
  - 归档索引：`/news/index.html`
  - 源健康看板：`/news/health.html`
- 静态 HTML 由 `intel.py brief --format web` 生成于 `~/wuhoo-workspace/news-web/`（尚未创建，WP6 建）。

### 8.4 HTML 文件兜底（微信附件）

- 触发：用户说"发我 HTML"/链接不便/微信内置浏览器打开受限时。
- 命令：`hermes send -t 'weixin:<chat_id>' "MEDIA:/tmp/nbYYYYMMDD.html"`（hermes send 用 MEDIA:<path> 发文件附件，已核实）。
- 约束：**≤100KB**（微信文件限制 + iLink 教训），**/tmp 短 ASCII 名**（用户既定规则），自包含 inline CSS 无外部依赖，微信内可直接打开。
- 内容：当日全量四段卡 + 来源链接（与网页版同源数据，单文件版）。

### 8.5 watchlist 告警（15min 巡检）

- 触发：新事件命中 watchlist，或已有事件**实质升级**（salience 跳升≥阈值 / 新独立源≥2 / 财联社加红 / GDELT mention 突增）。
- 去重：同事件 24h 最多 1 次（除非升级）；日限 5 条。
- 通道：微信（主，≤2KB + 事件深链）；失败退避重试 3 次（5/15/45min）+ 落盘 + 次日补投。
- watchlist 来源：手动添加 + **D1 跨 profile 自动种子**（持仓 ticker、guimei 关键词）。

### 8.6 跨 profile 个人化（D1=B，精准抓取喜好）

**目标**：不止对通用新闻重排序，而是让"源本身"和"权重"按用户真实业务定制。

**只读数据源（已核实真实路径）**：

| profile | 读取对象 | 提取什么 | 落到哪 |
|---|---|---|---|
| default | `~/.hermes/memories/USER.md` + MemPalace profile-default | 业务领域（金融/数字内容/coding）、游戏偏好（Dave the Diver/Terraria/收集经营）、工具链（Unity 6 URP/Aseprite/Blender） | interest_profile 冷启动 topic/keyword |
| trader | `~/.hermes/profiles/trader/memories/MEMORY.md`+`USER.md`；**最新持仓诊断报告** `~/wuhoo-workspace/data/trade/workflow_d/<date>/workflow_d_report.md`；MemPalace project-invest | 持仓 ticker/sector、投资偏好、风控关注 | entity:<ticker> 权重 + watchlist 自动种子 + **per-ticker EDGAR/finviz/seekingalpha 源动态生成** |
| gamedev | `~/.hermes/profiles/gamedev/memories/MEMORY.md`+`USER.md`；`~/wuhoo-workspace/games/guimei/docs/INDEX.md`+`DOCUMENT-MAP.md`+`AGENTS.md`；MemPalace project-guimei | 当前项目技术栈（Unity 6 URP/2D像素/骨骼动画/shader/dsh插件）、美术管线关注 | topic:游戏开发 权重 + keyword watchlist + T4 游戏/AI 源加权 |

**关键现实约束（已核实，诚实标注）**：
- 云端**无 FutuOpenD 进程**（OpenD 在 GPU/Windows，GPU 已退役关机），故**不依赖云端实时 Futu 抓取**。
- 落盘持仓报告**最新为 2026-06-30**（trader 15 个 cron 自 07-01 暂停，报告偏旧）。处理：
  - 持仓 ticker 作为"**历史持仓种子**"入 interest_profile，weight 中等（1.5），标记 origin_profile=trader + 报告日期。
  - **自动刷新**：sync-profiles 检测 workflow_d/ 下出现更新日期的报告（mtime）即重新提取；用户在 GPU 跑 trader 诊断或恢复 cron 后，新报告落地自动生效。
  - **对话确认**：用户可"我现在持仓是 X/Y/Z"即时覆盖种子（manual 来源优先级最高）。
  - 不拿陈旧持仓当当前事实推送；仅用于"兴趣方向"匹配，简报不暴露持仓数量/成本/盈亏。

**同步机制**：
- `sync-profiles` 子命令：周更 cron（周日 21:00，早于 profile 周更 22:00）+ 手动"更新我的兴趣" + 新报告 mtime 触发。
- 流程：读三 profile 记忆/产物 → 抽取 ticker/keyword/topic → upsert interest_profile（source=crossprofile, origin_profile 标记）→ 生成 per-ticker 源（EDGAR atom/finviz/seekingalpha）+ watchlist 种子 → 调整 T4 垂直权重 → 回报变更摘要。
- **隐私边界**：跨 profile **只读不写**；持仓数值（qty/cost/P&L）**绝不**入 interest_profile、绝不进网页/微信；只用 ticker 符号+sector 作匹配键；网页 basic auth  gated；interest_profile 存本地 SQLite；MemPalace 只写聚合偏好（不写持仓）。

**精准化的体现**：持仓 NVDA → 自动订阅 NVDA 的 EDGAR 8-K atom + finviz/news/NVDA + seekingalpha/NVDA/news，并 watchlist 盯 NVDA 财报/加红快讯；guimei 用 Unity 6 URP → Unity Blog/Releases + cs.GR arXiv 加权。这是"按喜好定制源"，比通用重排序精准一个量级。

### 8.7 反馈与调节输入（D3=A 双轨 + 接受调节）

**双轨 A/B**：规则引擎（旧 daily_briefing）与向量聚类（新）并行出两份简报 2 周，人工盲评后切换（D3=A）。旧 670 行正则冻结为 fallback（只修 bug 不加规则），610 行噪声黑名单保留为安全网。**A/B 期间调节输入作用于新管线 interest_profile**，两份简报均标注来源便于对比。

**调节输入语义（`tune` 解析规则，即时生效不等周更）**：

| 用户说 | 解析动作 | 生效 |
|---|---|---|
| "多点X / 多推X" | topic/keyword X weight +0.2 | 即时 |
| "少点Y / 别推Y" | Y weight -0.3；"别推"=mute（weight→0.2 下限） | 即时 |
| "这条没用" | event not_useful + 关联 topic -0.1 + feedback 入档 | 即时 |
| "这条有用 / 收藏" | event useful + 关联 topic +0.1 | 即时 |
| "最近关注Z / 盯着Z" | watch add Z + topic_burst boost=0.5 TTL 7天 | 即时+自动回落 |
| "最近X热点多推点" | MCP get_trending_topics 确认 → topic_burst X boost TTL 7天 | 即时+回落 |
| "通用多点/个人少点" | 混排比例调整（默认通用60/个人40 → 如50/50） | 下一期 |
| "更新我的兴趣" | 触发 sync-profiles（§8.6） | 即时 |

**近期热点响应**：`topic_burst` 表存临时 boost（reason+expires_ts），salience P 因子 = 基础个人增益 ×(1+burst)。用户提及当前热点 → agent 用 TrendRadar 确认热度 → 设 burst → 7天自动过期回落，避免长期偏置。

**周更兜底**：每周日 22:00 按 feedback 日志汇总调整长期权重（±0.1 步进，范围 [0.2,3.0]），与即时调节叠加；即时调节优先，周更做平滑。

**混排防茧房**：通用 60% + 个人 40%（可调），同主题 ≤2 条（多样性配额）。

---

## 9. 一次性构建工作包（WP0-WP8，按依赖连续执行）

| WP | 内容 | 关键产出/命令 | 验收 | 工期 |
|---|---|---|---|---|
| WP0 | 源治理与扩容 | RSSHub 升级+browserless；§2.2 全路由实测（**需授权**）→route_verification.json；修复14坏源；新增T0/T1/T4~40源；feed_health+自动停用；feedx备胎 | 有效源≥80（T3计入≥120）；硬故障≤5；每源有实测记录 | 1.5d |
| WP1 | TrendRadar+newsnow | §4.1 三容器；§4.2 config；MCP注册；hermes mcp test；config://platforms实测定T3；output schema实测 | 27工具可调用；热榜流入；velocity可读 | 1d |
| WP2 | 采集提频+GDELT | cron `0 * * * *` fetch；GDELT poller（30min）；watchlist巡检（15min） | 24h覆盖≥20整点；GDELT入库；告警通道通 | 1d |
| WP3 | 事件中心 | §6.1 DDL（含 topic_burst/feedback/interest_profile 扩展）；fastembed+模型；聚类；canonical；salience；独立源计数 | 黄金集P≥0.85/R≥0.80；合并率≥25%；TOP5分差≥15 | 3d |
| WP4 | 合成与核验 | 四段卡prompt；web_extract全文；数字核验；链接引用 | 抽检20条事实错误≤5%；每条≥2链接+影响句 | 2d |
| WP5 | Agent原生层 | wuhoo-news-intel + intel.py 14子命令（含 tune/sync-profiles）；§7.2 七场景；MCP用法固化 | 7对话场景实测通过；深挖带引用；调节即时生效 | 2d |
| WP6 | 投递与个人化 | 微信简报+全量链接；**nginx /news/ basic auth+htpasswd（需sudo授权）**；HTML兜底；告警去重/限流/重试；interest_profile冷启动+**跨profile sync**+反馈解析 | 投递成功率100%（含补投）；链接只读鉴权可访问；跨profile种子生效；反馈入档 | 2d |
| WP7 ✅ | 评测与双轨（完成 11-16 20:12） | 50事件黄金集（独立ground truth）；回归脚本PASS P/R/F1=1.0；A/B双简报并行2周；指标看板dashboard.html+盲评blind.html；B轨端到端exit=0 | 盲评新≥旧（观察期用户拍板）；指标可观测✅ | 1d+2周观察 |
| WP8 ✅ | 收尾（完成 11-16 20:30） | SKILL.md+AUDIT-LOG WP7/8；MemPalace决策抽屉；cron清单；回滚开关（每层独立disable）；旧daily_briefing冻结fallback；git commit | 全链路可回滚✅；交接完整✅ | 0.5d |

**总计 ~14 人日 + 2 周 A/B 观察**（WP6 因跨 profile + 鉴权链接从 1.5d 增到 2d）。一次性连续构建，agent 原生（WP5）与事件中心（WP3/4）同批，不 defer。

> **施工状态（2026-11-16 20:30 CST）：WP0-WP8 全部完成并真实端到端验证。** 审计全证据见 `docs/news-intel-build/AUDIT-LOG.md`。B 轨管线 exit=0（5207篇→3845事件，合并26.2%，微信3768B≤4KB，cards10/10核验，quota False）；黄金集回归 P/R/F1=1.0；A/B 看板+盲评页发布 /news/eval/（auth 门后只读）。**剩余为观察期与用户拍板项**：① 双轨并行约 2 周用户盲评（/news/eval/blind.html）→ 微信正式切换拍板（D3-A）；② A5 gateway /restart（live TrendRadar MCP 注入 + 8642 收尾，用户触发）；③ 用户侧认证 200 验证（口头凭据）。当前 A 轨仍推微信、B 轨 shadow 只读，零未授权推送。

依赖链：WP0→WP1→WP2→WP3→WP4→WP5→WP6→WP7→WP8。WP1 MCP 生效依赖 gateway 重启，与 8642 收尾 /restart 合并。

---

## 10. 评测与验收

- **黄金集**：50 真实事件 ×（应合并/不应合并组），人工标注；含跨语言对、通稿对、易混淆对。每月扩充。
- **指标**：去重 P/R、合并率、TOP5 人工相关性(1-5)、噪声率、合成事实错误率（周抽检20）、投递成功率、端到端延迟、token/日、源健康度、**个人化命中率（简报中匹配兴趣档案/持仓/项目的条目占比）**、**调节响应延迟（用户 tune → 下一期生效）**。
- **A/B**：规则 vs 向量并行 2 周盲评再切换（D3）。
- **回归**：每次改动跑黄金集 + 现有 OK 路由回归。

---

## 11. 成本 / 风险 / 安全

| 项 | 评估 | 应对 |
|---|---|---|
| 向量计算 | 本地 CPU ~15s/日，模型~470MB+向量~70MB | 零 API 成本；fastembed ONNX |
| LLM 合成 | TOP30×1.8K + 富化~3万 ≈ **8-9万 token/日** | qwen flash；周配额探针耗尽降级纯规则 |
| 容器资源 | newsnow+TrendRadar+MCP+browserless ≈4容器 <1GB RAM | podman 同栈；磁盘79%关注（retention 90天） |
| GDELT | 免费无key 15min | 轮询30min maxrecords75 |
| newsnow 善意 | 上游要求勿竭泽而渔 | 自建；request_interval 2000ms |
| 过度合并 | 双阈值+黄金集+规则兜底 | 宁少并不错并 |
| 合成幻觉 | 来源内事实+数字核验+未核实标注 | 深挖必给链接 |
| 个人化茧房 | 通用60/个人40+多样性配额 | 同主题≤2 |
| **跨 profile 隐私** | 持仓数值敏感 | **只读不写；数值不入库不进网页/微信；只用 ticker/sector 匹配；网页鉴权** |
| **陈旧持仓** | 报告最新 2026-06-30 | 标历史种子+自动刷新+对话确认；不当当前事实 |
| GPL-3.0 | TrendRadar 独立容器+MCP/卷读取 | 不链接代码 |
| 投递限流 | 微信≤4KB+重试+补投+链接/HTML兜底 | v1 教训固化 |
| **只读链接安全** | 公网可访问风险 | TLS+独立basic auth+只读GET/HEAD+禁目录列表+nosniff |
| 复杂度 | 每层独立开关 | 失败降级当前管线，可回滚 |
| secrets | TrendRadar notification 关闭无webhook密钥；MCP仅loopback；htpasswd密码口头交付不入库 | 不引入新凭据入库 |

---

## 12. 决策状态（D1-D4 已拍板）+ 已定案实现细节

### 已拍板（2026-11-16 用户确认）

| # | 决策 | 用户选择 | 落地章节 |
|---|---|---|---|
| D1 | 个人化数据范围 | **B 跨 profile**（读 trader 持仓/gamedev 项目，精准抓取喜好） | §8.6 |
| D2 | 投递面 | **A 微信简报 + 全量只读安全链接**（用户自己打开读详细；HTML 兜底注意微信大小限制） | §8.1-8.4 |
| D3 | 规则引擎去留 | **A 双轨 A/B 两周后切换** + **接受反馈与近期热点调节输入** | §8.7、§7.2 |
| D4 | TrendRadar 自带推送 | **A 关闭，Hermes 统一投递** | §4.2、§8.1 |

### 已定案（实现细节，可异议）

- 向量：fastembed + paraphrase-multilingual-MiniLM-L12-v2（384d CPU），SQLite BLOB + numpy 余弦，不上向量库。
- 聚类：cosine≥0.88 直接并 / ≥0.82+实体重叠≥1；窗口72h；canonical T0>T1>T2>T3。
- salience：W×(1+ln(1+N_indep))×V×D(半衰12h)×P×B；P 叠加 topic_burst；TOP5分差≥15。
- 调度：fetch每小时、TrendRadar crawl 30min、GDELT 30min、告警15min、日报08:00、源巡检周一07:00、**跨profile sync 周日21:00**、profile周更周日22:00。
- 合成：qwen flash，TOP30四段卡，数字核验，日预算8-9万token。
- 投递：微信简报≤4KB+全量链接；告警≤2KB日限5/同事件24h限1；重试5/15/45min+补投；HTML兜底≤100KB /tmp短ASCII名。
- 只读链接：nginx /news/ alias + 独立 basic auth（.htpasswd-news）+ limit_except GET HEAD + autoindex off；URL /news/daily|event|search|index|health。
- 个人化：通用60/个人40（可调），同主题≤2，权重步进±0.1范围[0.2,3.0]；即时调节优先于周更。
- 跨 profile：只读不写；持仓数值不入库；历史种子weight1.5+自动刷新+对话确认；per-ticker源动态生成。
- 垂直权重默认：投资40/科技AI30/宏观20/游戏10（按业务重心，可调；跨profile sync 会按实际持仓/项目微调）。
- TrendRadar：rss/notification/ai_analysis 均 false，schedule 由 Hermes cron 驱动，自建 newsnow。
- 规则引擎：670行正则冻结fallback（只修bug），610行噪声黑名单保留安全网。

---

## 13. 附录：证据与引用

实测（2026-11-16，v1 审计，保留）：
- 源审计 60→46 OK/14 BAD/21 零产出；明细 `~/.hermes/cache/scratch/feed_audit_20261116.json`
- 抓取100% hour=08；hot_score 95.7%落1-9、≥40为0；合并52/740=7%；未分类217/740=29.3%；alert 977/7日零推送；投递5天3败；正文2583字符0 URL
- RSSHub running/0重启/created 09-01/root 37ms；daily_briefing.py 1775行（噪声152-763/关键词764-942/去重943-1615）

v2 证据（保留）：
- TrendRadar v6.11.0 / MCP v4.1.1，27工具已对官方docs/mcp（2026-07-07）逐类核实（早期snippet 13/17差异以官方27为准）；8类；Resources 4个；Docker wantcat/trendradar + wantcat/trendradar-mcp，HTTP streamableHttp :3333/mcp，数据源newsnow（自建ghcr.io/ourongxing/newsnow:latest :4444 /api/s），storage local SQLite+HTML output/（MCP分析本地非实时），GPL-3.0
- RSSHub金融路由文档确认：/cls/telegraph/:category?（red=加红）、/cls/depth/1000、/jin10/:important?、/futunn/highlights、/gelonghui/home、/sse/disclosure/:query?、/sse/renewal、/bse/:category?、/gov/pbc/goutongjiaoliu（Puppeteer）、/cs/news/zzkx、/zhitongcaijing/:id?、/barronschina、/finviz/news/:ticker、/seekingalpha/:symbol/:category?、/unusualwhales/news
- GDELT DOC 2.0：api.gdeltproject.org/api/v2/doc/doc，mode=ArtList/Timeline，format=json，免费无key，15min，滚动窗口默认24h（最长3月）
- Hermes MCP：config.yaml mcp_servers.{name}.url（HTTP），前缀mcp_{server}_{tool}，hermes mcp list/test，重启生效

v3 新增证据（2026-11-16 现场核实）：
- nginx `/etc/nginx/conf.d/hermes-dashboard.conf`（1599字节）：80→301 https；443 TLS wuhoo.shanavasa.click，证书/etc/nginx/ssl/wuhoo.shanavasa.click/{fullchain,key}.pem；location / proxy_pass 127.0.0.1:9119；client_max_body_size 64m；HSTS+nosniff；**nginx层无auth_basic（鉴权在仪表盘应用层）**→ /news/ 需新增独立basic auth
- 持仓：云端**无FutuOpenD进程**；落盘诊断报告最新 `~/wuhoo-workspace/data/trade/workflow_d/2026-06-30/workflow_d_report.md`（trader cron 07-01起暂停，报告偏旧）；get_portfolio.py 需 OpenD（GPU/Windows），云端不可达 → 以落盘报告+记忆为准
- gamedev：`~/wuhoo-workspace/games/guimei/docs/`（INDEX.md/DOCUMENT-MAP.md/AGENTS.md/impl-*/ops-* 齐全）；gamedev MEMORY.md 6348字节/USER.md 2579字节；trader MEMORY.md 182字节/USER.md 2579字节
- hermes send：`-f` 读文本正文；**文件附件用 MEDIA:<path>**（已核实 --help）；weixin 目标格式 weixin:<chat_id>
- news-web 目录尚未创建（WP6 建）

引用：
- TrendRadar https://github.com/sansan0/TrendRadar ；MCP https://trendradar.sandev.cc/zh/docs/mcp/
- newsnow https://github.com/ourongxing/newsnow
- RSSHub金融路由 https://rsshub-doc.pages.dev/finance.html
- GDELT https://gdeltproject.org/ ；DOC API https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- 事件去重实践 https://scanbrief.dev/blog/posts/ai-news-aggregation-deduplication.html
- IMPACT https://github.com/RetryRain/IMPACT
- 新闻推荐综述 https://link.springer.com/article/10.1007/s41019-023-00228-5

---

## 14. 审阅清单 + 施工授权清单（审阅通过前不动手）

### 请用户审阅的重点

1. **源金字塔分层与 ~70 新源清单**（§2）：分层职责、垂直权重默认（投资40/科技AI30/宏观20/游戏10）是否合业务重心。
2. **跨 profile 读取范围与隐私边界**（§8.6）：读 trader 持仓报告（最新 2026-06-30，偏旧）+ gamedev guimei 文档；只读不写、持仓数值不入库不进网页/微信——是否认可这个边界；陈旧持仓作"历史种子+自动刷新+对话确认"的处理是否接受。
3. **只读链接鉴权方式**（§8.3）：nginx /news/ 独立 basic auth（独立账号，密码口头交付）+ 只读 GET/HEAD + TLS——是否认可；或偏好沿用仪表盘 nous 登录（需把 /news/ 挂到仪表盘应用后，改造更大）。
4. **调节输入语义**（§8.7）：tune 解析规则表、即时生效、热点 burst 7天回落——是否符合"根据反馈和近期热点接受调节"的预期。
5. **一次性施工顺序与工期**（§9）：WP0-WP8 ~14人日+2周A/B。

### 施工需用户授权的动作（批准方案后逐项执行，不默认动手）

| # | 动作 | 涉及 | 章节 |
|---|---|---|---|
| A1 | 候选 RSSHub 路由 curl 实测（本次被安全闸拦下） | 本机 1200 端口批量探测 | WP0/§5 |
| A2 | podman 拉镜像 + 起 newsnow/trendradar/trendradar-mcp/browserless 容器 | 新增4容器 | WP1/§4.1 |
| A3 | 编辑 ~/.hermes/config.yaml 追加 mcp_servers.trendradar | Hermes 配置 | WP1/§4.3 |
| A4 | **sudo 编辑 nginx conf 追加 /news/ + 创建 .htpasswd-news + nginx -t + reload** | 公网基础设施 | WP6/§8.3 |
| A5 | gateway /restart（合并 8642 收尾 + MCP 生效） | 用户触发 | WP1/§4.3 |
| A6 | 新增/修改 cron（fetch hourly/GDELT/告警/sync/周更） | Hermes cron | WP2/WP6 |
| A7 | news.db 增量建表 + fastembed 模型下载 | 数据/依赖 | WP3 |

**当前状态（2026-11-16 20:30 CST 更新）：方案 v3 已落盘 + 用户已授权施工 + WP0-WP8 全部完成并真实端到端验证（审计见 docs/news-intel-build/AUDIT-LOG.md）。A1-A4/A6/A7 已执行；A5 gateway /restart 仍待用户触发（合并 8642 收尾 + live TrendRadar MCP 生效）。微信正式切换待 D3-A 双轨约 2 周盲评后用户拍板，当前零未授权推送。**
