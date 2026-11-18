# 2026-11-17 B轨首次正式生产剖析（Production Autopsy）

> 剖析对象：11-17 08:10 新闻情报 daily 管线（B轨 shadow，cron a898cbb5e6a5）首次按调度正式生产，
> 及同日 08:00 A轨微信对照（cron d6d628cc68a1）。全部数字来自现场证据：
> news.db / cards_20261117.json / pipeline_20261117.log / hourly_fetch.log / state.db / podman inspect / jobs.json。
> 本文档为只读剖析，未改动任何生产代码。index.html 深度定制方案待用户讨论后另行拍板。

## 0. 一句话结论

管线全链路跑通、10 张四段卡数字核验 10/10 通过、网页按时发布；但今天的成品有三处实质质量缺陷：
黄仁勋同一个故事占了 TOP10 的 3 个席位（跨语言欠合并）、第 4 张卡把两条无关新闻混在一起（The Verge 复合标题）、
生产时 RSSHub 挂死导致 41/91 个源缺席且无健康闸门。另发现个人化种子 7 个 A股实体键全部失效、A轨模型已被切到 qwen4-max（明日成本跳升）。

## 1. 今天的"正式生产"是什么：双轨架构

11-16 一次性建成 WP0-WP8 事件中心管线后，系统按 D3 拍板进入约 2 周双轨观察期：

- A轨（对照组，旧规则引擎）：cron d6d628cc68a1，每日 08:00，agent 模式，
  加载 wuhoo-news-rss + wuhoo-rss-briefing 技能，48h 窗口 + 610 行噪声黑名单 + 标题级去重，
  四大类各 TOP5，deliver=origin 推微信。今天 08:00:24 派发，08:28:44 完成，last_status=ok，微信投递成功。
- B轨（新管线，事件中心）：cron a898cbb5e6a5，每日 08:10，no_agent 纯脚本，
  fetch→embed→cluster→salience→synthesize TOP10→publish web，deliver=local 只存档不推微信。
  今天 08:10:27 START，08:15:53 DONE，全程 5 分 26 秒。这是建成后第一次按调度正式生产。
- 支撑 cron：bb84c71fff5b 每小时 :05 采集；bb3616830971 每小时 :20 算 TrendRadar 速度信号；
  关注巡检告警 9c6449d45c15（*/30min）按施工期约定 paused。

用户在微信收到的仍是 A轨简报；B轨成品在 https://wuhoo.shanavasa.click/news/daily/2026-11-17.html
（独立 basic auth，无凭据 401 是预期；已验证 /var/www/news 与 staging 文件 sha256 一致）。

## 2. 模型与 tokens（state.db session_model_usage + cards JSON 实测）

B轨合成模型：qwen3.8-flash（token-plan 阿里云 MaaS compatible-mode，关思考 reasoning_effort=none，
temperature=0.2，每卡 max_tokens=520，总预算 60000）。今天 10 次调用：
prompt 9617 + completion 1718 = 11335 tokens，平均 1134/卡，quota_hit=False，预算仅用 19%。

A轨 agent 模型：qwen3.8-flash（会话 local-d0a2cdcc…，42 次 API 调用，40 次工具调用，83 条消息，28 分 17 秒）：
input 167064 + output 38435（含推理 21528）= 205499 非缓存 tokens，另 cache_read 4614400。

嵌入模型：fastembed paraphrase-multilingual-MiniLM-L12-v2（384 维，本地 CPU），914 篇 168.7 秒，零 API tokens。
velocity/watchlist/聚类/排序全部纯脚本，零 tokens。

  项目              模型            调用数   非缓存tokens    缓存读
  B轨 web 生产      qwen3.8-flash   10       11335           0
  A轨 微信对照      qwen3.8-flash   42       205499          4614400
  合计              —               52       216834          4614400

A轨占非缓存消耗 94.8%。B轨用 5.2% 的 tokens 产出了信息密度更高的成品（事件级去重+四段卡+数字核验）。

⚠ 模型漂移预警：jobs.json 里 A轨 model 现为 qwen4-max（今天 10:11-11:55 "GPU 代理清理与 qwen4-max 默认模型切换"
会话所改；08:00 生产时还是 flash）。明天 08:00 起 A轨将用 qwen4-max 跑同样的 42 调用流程，配额消耗将显著上升。
A轨是冻结 fallback，是否需要 premium 模型值得拍板（见 §9 P1-6）。

## 3. 系统运行过程（今日完整时间线，hourly_fetch.log + pipeline log + podman inspect）

- 00:05-10:05 hourly 采集 11 轮：每轮 41-43 个源 Connection refused。
  根因：RSSHub 容器 conmon/libpod 内部错误挂死（容器状态 Up 但进程不响应，老坑"Up 但 HTTP 000"复发），
  至少从 00:06 持续到 10:07。newsnow/trendradar/trendradar-mcp 同样挂死。
- 08:00:24 A轨派发 → 08:00-08:02:30 fetch（残缺口径）→ agent 直查 SQLite/过滤/分类/合成 → 08:28:44 微信投递 ok。
- 08:05 hourly（08:09:26 END，新增 3）。
- 08:10:27 B轨 START：
  1) fetch（08:11:23 END，新增 0，flock 与 hourly 串行）
  2) embed：72h 窗口 5463 篇，已有向量 4549，待嵌 914，分 4 批 168.7s（约 5.4 篇/秒 CPU）
  3) cluster：5463 篇 → 4093 事件，60.4s，合并率 25.1%，多源事件(≥2成员) 561
  4) brief --top 10 --budget 60000：10 卡 11335 tokens，数字核验 10/10，
     微信文本 3799B + 全量 HTML 16022B + 兜底 /tmp/nb20261117.html + cards JSON
  5) publish_web：6 HTML → /var/www/news，重建 index.html
- 08:15:53 DONE。08:20 velocity cron：从 2026-11-16.db（昨日数据，TrendRadar 挂死无新爬）算出 1406 条。
  即 08:10 生产时 V 因子用的是昨日热榜排名。
- 10:11-11:16 另一 CLI 会话做 GPU 清理+模型切换，期间发现容器挂死，
  10:23:54-58 批量 podman restart 四容器（trendradar-mcp SIGTERM 超时转 SIGKILL）。
- 11:05 hourly 首个健康轮：总条目 2940→3923，失败 41→5，新增 617（积压涌入）；12:09 新增 337；13:09 新增 306。
  这 1260 篇恢复后的新文章没有进入今天的 daily brief（brief 08:15 已发布）。
- 13:20 velocity 恢复当日数据：746 条（weibo/ithome/toutiao/baidu/36kr 等 10+ 平台）。
- 13:38 qwen 配额探针 silent（配额正常）。

## 4. 配置了哪些主体和关键词

源配置（feeds/config.yaml + feed_health 表）：91 个源，7 类别：
财经 25 / 科技 22 / 综合 16 / 足球 9 / AI 8 / 投资 6 / 游戏 5。feed_weights 90 项。
层级金字塔：T0=6（上交所科创板/上交所披露/美联储新闻/arXiv NLP/机器学习/图形学），
T1=8（财联社电报/加红/公司公告/深度、金十重要/数据、华尔街见闻实时、格隆汇首页），T2=70，T4=7（游戏/Anthropic/UW 等）。
当前健康：ok 84 / degraded 4（CoinDesk/Stratechery/Telegraph Football/美联社）/ down 1（arXiv 量化金融）/ empty 2（36氪/Google DeepMind）。

主体与关键词分四层：
1) watchlist.yaml 7 组（告警扫描用）：美股科技（NVDA/TSLA/AAPL/MSFT/GOOG/GOOGL/AMZN/META/AMD/AVGO/NFLX/PLTR + 8 中文词）、
   AI大模型（OpenAI/Anthropic/Claude/DeepSeek/大模型/算力/Gemini/GPT/智谱/月之暗面等 11 词）、
   宏观货币（美联储/降息/加息/CPI/非农/关税/人民币/央行/鲍威尔/国债收益率）、
   A股港股（A股/沪指/恒生/北向资金/涨停/证监会/沪深/创业板/科创板）、
   游戏开发（Unity/Unreal/虚幻引擎/Steam/任天堂/米哈游/游戏版号/像素/guimei/独立游戏/Godot）、
   期货大宗（原油/黄金/沪铜/期货/OPEC/螺纹钢/大宗商品）、加密（BTC/ETH+比特币/以太坊/加密/稳定币）。
2) DB watchlist 16 条（sync-profiles 跨 profile 只读种子）：trader 7 个 A股持仓名
   （五粮液/意华股份/宁德时代/恒瑞医药/贵州茅台/中国平安/中贝通信）+ gamedev 9 个技术词
   （Blender/Godot/Steam/Unity/guimei/rig/shader/独立游戏/皮影）。告警 cron paused，切换后启用。
3) interest_profile 12 键（salience P 因子）：上述 7 个 entity 键 w=0.3（trader_workflow_b 种子，60 天过期）、
   topic:游戏 0.3（gamedev_guimei）、topic:财经 0.25（feedback）、entity:NVIDIA 0.2（tune）、
   topic:科技 -0.1（feedback）、topic:足球 -0.3（tune）。
   topic_burst：科技 +0.5，TTL 至 11-23（"科技很热" tune 测试写入）。
4) 聚类内置词典：ENTITY_ALIASES 约 40 组中英别名归一（英伟达→NVIDIA、宁德时代→CATL、美联储→FED 等）+
   STOP_TICKERS 26 个泛词停用 + _NON_COMPANY 约 90 个非公司主语 blocklist + A股公告动作词正则。
A轨另有旧规则引擎遗产：EXPANDED_KEYWORDS 200+（hot_score 用，已退化不可信）+ NOISE_PATTERNS 610 行噪声黑名单。

## 5. 找到了多少篇文章

今日采集（00:06-13:09，16 轮 = 14 轮 hourly + A/B 轨各 1 轮）：
新增入库 1958 篇，hash 去重跳过 21522 条次，源失败累计 553 次（前 11 轮每轮 41-43，恢复后每轮 5）。
今日新增类别：财经 914 / 科技 421 / 综合 218 / 投资 168 / AI 135 / 足球 86 / 游戏 16。
今日产出最高源：Seeking Alpha 268 / UnusualWhales 148 / IT之家 116 / arXiv AI 90 / 华尔街见闻实时 77。

生产时口径（08:10）：72h 窗口 5463 篇 → 4093 事件（合并率 25.1%），多源事件 561（13.7%）。
当前窗口已涨到 6816 篇（恢复后涌入）。全库累计 129818 篇（2026-04-22 起）。
A轨自己的 48h 口径（08:19 统计行原文）：总 4864 / 过滤后 2412 / 事件合并 2026 / 未匹配 377。

## 6. 去重怎么做的（三层）

第 1 层 入库 hash 去重：fetcher INSERT OR IGNORE，今日挡掉 21522 条次重复。
第 2 层 语义聚类（event_center.py，窗口重建式）：文章按 fetched_at 升序逐篇并入事件，三条合并路径 + 一个精度 guard：
  a. 直接合并：与事件质心 cosine ≥ 0.82（校准值：跨事件 inter_max 0.81，同事件 intra_p10 0.819）；
  b. 实体合并：cosine ≥ 0.75 且共享实体 ≥ 1（校准：共享实体 p95=0.708，跨语同事件 0.78）；
  c. 通稿兜底：norm_title_key（去 HTML/栏目前缀/标点，仅 CJK+字母数字 lower）≥8 字符完全相同 → 强制合并，override cosine；
  d. 精度 guard：A股公告公司主语（冒号+动作词模式）前 2 字符核心不同 → 拒绝合并（防通威/赛伍/盛屯同模板误并），
     _NON_COMPANY blocklist 防国家/政府/媒体/人名误判公司。
  嵌入文本 = 标题 + 摘要前 300 字（clean_text 剥 HTML，防同骨架假高 cosine）。
第 3 层 独立源计数：WIRE_GROUPS 把路透社/美联社/彭博/法新/新华同稿源归并为 1 个独立键，n_indep 防通稿灌水。
canonical 代表作 = TIER_BONUS × (0.4 + 0.3×全文长度 + 0.2×数字密度 + 0.1×源权重)，选信息量最大的一篇。

已知边界（今天实测暴露）：跨语言同故事 cosine 落在 0.75 以下时三条路径全不命中 → 欠合并（见 §9 P0-2）。
黄金集 50 对（cross-feed 同标题正 / cross-company 负）P/R/F1=1.0，但没有跨语言同事件正对，掩盖了这类漏合并。

## 7. 排序怎么做的（salience 公式与今日实际分布）

S = W × (1 + ln(1+N_indep)) × V × D × P × B
  W = 簇内最高源权重（feed_weights，FT=10、华尔街见闻=9、未配置=3）
  N_indep = 独立源数（通讯社归并后），对数增益防灌水
  V = 1 + min(1, velocity/4)，TrendRadar 热榜速度，标题指纹（前 40 字符）匹配
  D = exp(-Δt/12h)，以 canonical 的 fetched_at 计时间衰减
  P = clamp(1 + Σinterest_gain, 0.3, 2.0) × (1 + topic_burst)，实体+类别兴趣，负 gain 可 demote
  B = tier bonus（T0=1.5 / T1=1.2 / T2=1.0 / T3=0.8 / T4=1.0）

今日实际：active 事件 4615（含 522 个窗口外陈旧事件，见 P2-7），分布：
≥40 分 2 个 / 20-40 分 5 个 / 10-20 分 408 / 5-10 分 855 / <5 分 3345（72.5%）。
TOP10 门槛 19.21，第 11 名 18.71（SA 基金评论并列簇），差距仅 0.5，排序脆弱。
今日 P 因子实际生效项：科技 burst +0.5 压过 interest -0.1（P=0.9×1.5=1.35）→ TOP10 里 8 科技 2 财经；
NVIDIA +0.2、财经 +0.25 生效；7 个 A股 entity 种子全部未生效（P1-5）。
V 因子生产时用昨日热榜（TrendRadar 挂死），且高速条目多为 producthunt/juejin，与新闻标题指纹匹配率低，多数事件 V≈1。

## 8. 最终呈现的内容是怎么筛选的

cmd_brief 直接取 salience TOP10（ec.top_events），没有任何噪声过滤、主题多样性约束、窗口守卫或单源惩罚
——A轨的 610 行噪声黑名单在 B轨不存在，质量完全依赖聚类+salience。逐事件流程：
1) gather_context：成员按 similarity 排序，主体实体 = ≥2 成员提及或出现在代表作（incidental 单源实体抑制）；
2) build_user_prompt：≤3200 字符 = 事件元数据 + 参考日期（last_seen，防臆造年份）+ 成员标题+180 字摘要（预算 2400）+ 代表作全文 700 字；
3) qwen3.8-flash 关思考输出四段 JSON：fact（2-3 句，数字带单位）/ impact（一句话）/ divergence（仅多源不一致时）/ next_step；
   SYSTEM 铁律：只用来源内事实、数字可溯源、禁编造链接、中文完整展开、年份 grounding；
4) verify_numbers：fact 中每个数字在成员全语料匹配（浮点等价 + 日期词按参考日期放行，数量不 whitewash）。
   今日 10/10 全核验通过，unverified_numbers 全空；
5) links = 成员 article.link 真实 permalink（排除 127.0.0.1 RSSHub feed），去重，canonical 优先。9/10 卡 ≥2 链接；
6) 产出四件套：微信文本 ≤4KB（标题截 40 字 + fact 截 90 字 + 1 链接 + 全量链接 + 反馈 footer，实际 3799B）、
   daily HTML（16022B，四段卡全量 + 主体实体 + S 分 + 来源列表）、兜底 /tmp/nb20261117.html、cards JSON；
7) publish_web 全量 copy 到 /var/www/news + 重建 index.html。B轨 deliver=local，微信文本只存档不推送。

今日 TOP10 成品：黄仁勋回归议程(4源 S46.0) / 加州起诉 OpenAI(8源 S42.4) / 美联航系统故障(6源) /
酒店氯气+微软 outage 混合卡(3源) / Trump 挺黄仁勋(3源) / 英伟达董事会不考虑回归(3源) /
SemiAnalysis 下修 AI 算力(6源) / 胜宏科技 707 亿授信(5源) / 法拉第未来财报(1源) / 英伟达 Rubin GPU(1源)。

## 9. 优化点清单（现象→根因→建议，按优先级）

P0-1 生产无源健康闸门。现象：今天 brief 用 41/91 源缺席的残缺口径发布；10:23 恢复后 11-13 点涌入 1260 篇没进今日简报。
根因：RSSHub conmon 挂死无自动检测/重启/告警（靠另一个会话人工发现）；管线对源健康零感知。
建议：brief 前跑健康探针（fail_streak/HTTP 抽查），低于阈值则延迟重试或降级并在页面标注"源覆盖残缺"；
hourly wrapper 检测连续 N 轮 Connection refused 自动 podman restart + 告警；恢复后可选补发增量版。

P0-2 跨语言同事件欠合并。现象：黄仁勋故事占 TOP10 三席（#1 中文簇 2622 / #5 Trump 英文簇 4129 / #6 董事会英文簇 2318），
11 篇文章合成 3 张卡，3003 tokens（占今日 26.5%）讲同一个故事。
根因：multilingual-MiniLM 跨语短标题 cosine < 0.75，实体路径不命中；norm_title 只认完全相同；
黄金集无跨语正对，P/R/F1=1.0 属过拟合。
建议（三选一或组合）：a. brief 层对 TOP20 候选做一次 LLM 辅助同故事归并（一次 flash 调用约 1K tokens，性价比最高）；
b. 聚类加实体锚定路径：共享 ≥2 实体且含主体实体时阈值降到 0.65-0.70；
c. 黄金集补跨语同事件正对 + 同故事不同角度负对，重新校准。另加 brief 层同主体故事多样性上限兜底。

P1-3 复合标题污染。现象：#4 卡"15 hotel guests…due to Microsoft's global email outage"把氯气中毒和微软 outage 两条无关新闻混进一张卡，fact 段落前后不连贯。
根因：The Verge quickpost/liveblog 源用复合标题打包多条新闻，聚类把它当单事件，合成器忠实混合。
建议：识别 liveblog/quickpost 类源（feed 标记或标题连接词模式），禁选 canonical 或降权；对成员间 cosine 方差大的低内聚簇打标复审。

P1-4 Seeking Alpha 噪声洪水。现象：SA 窗口内 496 篇（占 9%），今日 268 篇（13.7%），其中 77 篇财报电话会转录/基金评论；
"Q3 2026 Comment"类单源事件 salience 18.71 并列排在 #11-15，新闻淡日会灌满 TOP10。
根因：SA 源权重 9 + 财经 interest +0.25，单源无惩罚，无标题类型过滤。
建议：SA 标题模式黑名单（Earnings Call Transcript / Q3 2026 Comment / Presents at）；单源观点类降权；TOP10 原则上要求 n_indep≥2（S 极高例外）。

P1-5 个人化种子全死。现象：interest_profile 7 个 trader A股 entity 键从未命中任何事件。
根因：extract_entities 只认 ENTITY_ALIASES（约 40 组）+ 大写 ticker；五粮液/茅台/恒瑞/平安/意华/中贝 6 个名字不在词典；
宁德时代虽在词典但规范名是 CATL，interest 键却是 entity:宁德时代，键名不匹配。D1 个人化对 A股持仓实际失效。
建议：sync-profiles 写规范键（entity:CATL）；把 watchlist/interest 的实体名动态注册进别名表；A股名称直接子串匹配。

P1-6 A轨成本与模型漂移。现象：A轨每日 205K 非缓存 + 4.61M 缓存读（B轨的 18 倍），且 jobs.json 模型已被切到 qwen4-max，明日成本跳升。
建议（需拍板）：A轨钉回 qwen3.8-flash（冻结 fallback 不需要 premium 模型）；或提前 D3 切换、pause A轨。双轨观察期成本应最小化。

P2-7 陈旧事件永不归档：522 个 last_seen 出窗事件仍 active，排序池与 recompute 扫描量只增不减。建议出窗置 status='archived'。
P2-8 排序脆弱+无多样性：#10 与 #11 仅差 0.5 分；科技 burst 一边倒（8/10）。建议主题/主体配额（同主体故事 ≤1-2、单主题 ≤6），顺带兜底 P0-2。
P2-9 velocity 新鲜度与相关性：生产时用昨日热榜；高速条目多为 producthunt/juejin 与新闻标题匹配率低。建议 computed_at 新鲜度检查（>2h 则 V=1 并记日志）+ 平台白名单。
P2-10 微信截断体验：英文标题 40 字硬截断词（"disrupts d"）、fact 90 字硬截句。建议词边界截断+省略号；或合成时顺带产出中文标题（每卡约 +20 tokens）。
P3-11 性能余量：聚类暴力余弦 5463×4093 用 60.4s，随窗口线性增长，万篇级仍可用；嵌入 5.4 篇/秒 CPU。暂不需要 ANN，记录观察阈值。

## 10. index.html 现状与定制入口（供方案讨论）

现状：staging ~/wuhoo-workspace/news-web/index.html（1944B），publish_web 每次 brief/dive 都拷到 /var/www/news/index.html。
生成代码：intel.py build_index_html()（190-207 行）+ write_html()（170-187 行，全站共享内联 CSS）。
内容 = 4 张静态卡片：A/B 评测链接 / 每日简报归档列表（≤60 条，仅日期字符串）/ 事件深卡列表（≤30）/ 说明文字。
无 JS、无搜索、无筛选、无元数据（不显示每日条数/主题/热度）、无分页，max-width 760 移动友好。

定制关键约束：index.html 是每次 publish 自动重建的产物，手改文件会被覆盖——深度定制必须改 build_index_html 代码，
或引入模板机制（模板文件 + 数据注入）。数据都在本地（news.db events/articles + cards_*.json + daily/*.html），
纯静态生成即可实现门户化，不需要后端服务。可讨论方向：今日 TOP10 直出门户、主题/实体筛选、归档元数据化、
搜索（FTS5 预生成索引或前端 lunr）、深色模式、阅读反馈入口（对接 tune）、A/B 评测入口收纳等。具体方案等用户拍板方向后再出设计稿。

## 11. 拍板记录（2026-11-17 用户）

1. 模型：qwen4-max。A轨 cron 已钉 qwen4-max（jobs.json 确认）；B轨合成与同故事归并调用切换 qwen4-max（synthesize.py MODEL，探针实测关思考 wire shape 200 无 reasoning tokens）。
2. 优化清单：P0 全部立项并完成（P0-1 源健康闸门+RSSHub 挂死自动重启；P0-2 跨语同故事归并三层防线+黄金集跨语类）。P1-4/P1-5 结合近期金融投资信息更新并完成：workflow_d 2026-06-30 美股持仓 FITB/FAST/HBAN 种子（陈旧140天已标注，trader 恢复后自动刷新）+ 北交所新股关键词（9月打新活动）；SA 噪声持仓豁免；canonical 键迁移 + 动态别名注册。P1-6 成本项随模型拍板解决（A轨保留 qwen4-max，用户接受）。
3. index.html 深度定制：方向待讨论（§10 为基础），未动代码。

施工与验证证据见 docs/news-intel-build/AUDIT-LOG.md「2026-11-17 生产后修复」段。