---
name: wuhoo-news-intel
description: "Use when 新闻情报简报/聚类去重/双轨评测/分类门户/生产剖析/只读安全链接. 事件中心管线."
tags: ["wuhoo"]
category: research
---

# Wuhoo 新闻情报（agent 原生事件中心）

从 `wuhoo-news-rss` 的 SQLite 库出发，做语义聚类去重 → 事件中心 → salience 排序 → 四段卡合成（数字核验）→ 微信简报 + 全量只读安全链接 → 反馈/个人化闭环。替代旧规则引擎 `wuhoo-rss-briefing`（冻结为 A 轨 fallback）。

> **依赖**: `wuhoo-news-rss`（DB `skills/default/wuhoo-news-rss/data/news.db`，共享）；fastembed（paraphrase-multilingual-MiniLM-L12-v2，384d CPU）；qwen4-max 合成（2026-11-17 用户拍板，关思考，wire shape 与 qwen3.8 相同）。
> **Python**: 必须 `/usr/bin/python3.11`。
> **方案**: `docs/NEWS-INTELLIGENCE-UPGRADE-2026-11-16.md`（v3）；**施工审计**: `docs/news-intel-build/AUDIT-LOG.md`（WP0-WP8 全证据）。
> **根目录**: `~/wuhoo-workspace/skills/default/wuhoo-news-intel/`（src/ scripts/ data/）。

## 何时使用

- 生成每日新闻情报简报（事件级去重，非标题级）、深挖某事件、按实体/主题检索时间线。
- 调个人化（多点X/少点X/这条没用）、跨 profile 同步兴趣种子、watchlist 告警。
- 评测聚类质量（黄金集回归）、A/B 双轨指标看板、双轨盲评。
- 排查管线（fetch→embed→cluster→brief→publish→deliver）某步失败。
- 剖析某日正式生产（模型/tokens/过程/主体关键词/文章数/去重排序/成品筛选/优化点）：只读取证流程与质量审计 checklist 见 `references/production-autopsy.md`。

## 架构与管线（B 轨 shadow）

`scripts/daily_intel_pipeline.sh`（cron `a898cbb5e6a5` 08:10）链式执行，任一步 rc≠0 即停后续：

```
fetch（hourly cron bb84c71fff5b，wrapper 含 coverage 统计 + RSSHub 挂死自动重启）
  → 覆盖闸门: ratio<0.70 → 告警 + sleep 300 重采一次（有界单重试）
  → event_center.py run --window 72   # embed 新文章 + 聚类(top-K扫描) + salience + 落库
  → intel.py brief --format web       # 噪声过滤(SA机械类,持仓豁免) → 同故事归并(qwen4-max LLM组 ∪ 确定性实体锚组)
                                      #   → TOP10 四段卡 + 微信≤4KB + daily HTML(降级横幅) + 兜底≤100KB
  → portal.py build --edition $EDITION # 13类目×≤4卡+导读+总览 + 兴趣深挖(持仓雷达+六段增强卡+Jina全文) + 热榜交叉
                                      #   → 门户 index.html + portal/{date}-{edition}.html + .portal_index 标记
  → intel.py publish（publish_web）    # 标记感知: 有.portal_index copy门户index, 无则旧归档索引(回滚开关)
  → deliver local                      # shadow 仅存档，不推微信
```

- **聚类阈值（现场校准值，非 plan 初始值）**: direct cosine≥0.82 直接并 / entity≥0.75+实体重叠≥1；窗口 72h；canonical T0>T1>T2>T3。2026-11-17: top-K(8) 候选扫描替代贪心 argmax（修最高cos候选无共享实体时的漏并）；跨语同事件 cos 实测 0.48-0.51 远低于安全阈值 → 由 brief 层归并兜底，不在聚类层强并。
- **召回兜底**: 同 `norm_title_key`（去 HTML/栏目前缀/标点，仅 CJK+字母+数字 lower，≥8 字符）跨 feed 强制合并（通稿同故事，覆盖 cosine 限制）。
- **精度 guard**: `company_subject` 提取公司公告主语（前 2 字符核心），`_NON_COMPANY` blocklist 拒绝国家/政府/央行/媒体/人名/时段/板块等非公司主语；不同公司核心不合并。
- **动态别名（P1-5）**: interest_profile entity 键 + watchlist 启用值自动注册进 extract_entities（refresh_dynamic_aliases）；interest 键必须用 canonical_entity 规范名（宁德时代→CATL），否则种子永不命中。别名含人物锚（黄仁勋→JENSEN_HUANG/Trump→TRUMP 等）+ A股/美股持仓名；STOP_TICKERS 扩充英文泛词（US/TO/IN/OF/SAYS/SH/SZ 等实测 junk）。
- **brief 层同故事归并（P0-2）**: 一次 qwen4-max 调用判 TOP20 候选（跨语/跨角度），其组与确定性规则组取**并集**（union-find，mode=llm+deterministic）——LLM 事件级判定较严（同一 saga 的不同角度视为不同事件，跨语正对只并部分），确定性实体锚（共享实体≥2 含强实体 + 同主题或共享≥3 + 质心 cos≥0.30）补故事级归并；LLM 失败/quota 回退纯确定性。归并卡语料/链接/独立源取并集，cards JSON 记 merged_from/dedup_mode/model/coverage/noise_filtered。
- **选择层噪声过滤（P1-4+D）**：SA 机械类（Earnings Call Transcript/Presentation、Slideshow、Presents at、基金评论）过滤，命中 interest/watchlist 实体（持仓）豁免；单源事件选择分 ×0.9 降权（不改落库 salience）。2026-11-18(拍板D)扩展：①DIGEST_META_PATTERN 每日聚合meta文章(早间精选/见闻早餐/投资日历/晨会精华/【早报】/【晚报】/昨夜今晨/要闻速递/金十数据整理等)无条件过滤不豁免持仓；②CATEGORY_NOISE 类目内异类排除(足球NON_FOOTBALL: 板球ODI/F1/赛马/拳击WBC/高尔夫; 游戏NON_GAMING: 影视James Bond/Casting/Box Office)，仅作用对应类目不误伤综合源。
- **salience**: W×(1+ln(1+N_indep))×V×D(半衰12h)×P×B；P 叠加 topic_burst + interest_profile（负 gain 允许 demote，floor 0.3）。
- **re-cluster 删除用子查询**（非 IN 枚举）：规避 SQLite 999 变量上限（事件>999 必崩 too many SQL variables，WP6 根因修复）。

## 命令清单

### 事件中心 `src/event_center.py`
- `run --window 72`：embed + cluster + salience + 落库（管线核心）。
- `embed_articles` / `cluster`：可单独委托（WP5 wiring）。

### Agent 层 `src/intel.py`（14 子命令）
- `health`：articles/events/members/vectors/entities/核验率/容器/deliveries 总览。
- `rank [--top N]`：salience TOP 事件。
- `brief [--top N] [--format web|wechat]`：噪声过滤→同故事归并→四段卡（事实/影响/分歧/下一步）+ 数字核验 + 微信≤4KB + daily HTML（源降级横幅）+ 兜底。
- `coverage`：解析 hourly 最后一轮采集 → data/source_coverage.json（ok/failed/refused/ratio/ts）；hourly wrapper 每轮自动调用，brief 读取判降级。
- `dive <event_id> [--html]`：事件深卡（primary/incidental 实体频次加权抑制）+ event HTML。
- `search <关键词>` / `timeline <实体>`：检索 + 逆时序事件线。
- `audit`：源健康（ok/degraded/down/empty）。
- `watch add|list|remove` / `alert [--dry-run]`：watchlist 告警（去重/限流/重试）。
- `profile show|update` / `tune` / `sync-profiles`：个人化 + 反馈调节 + 跨 profile 种子（workflow_b A股 + workflow_d 美股持仓 FITB/FAST/HBAN，仅 ticker+名称+行业；watchlist 去重；旧键名自动迁移 canonical）。
- `fetch [--dry-run]` / `cluster`：采集/聚类委托。
- 发布: `intel.publish_web()` 是函数非独立子命令（CLI 无 publish 选项，2026-11-18 实测）；portal.py build 末尾自动调用（staging→/var/www/news/ + index 归档，.portal_index 标记感知）；intel.py brief/dive 内部也调。

### 门户 `src/portal.py`（2026-11-17 用户拍板 tophub 式分类门户）
- `build [--edition morning|evening] [--budget 90000] [--dry] [--no-llm]`：六区单文件静态 HTML+原生 JS。
  A 顶栏(日期下拉回看/版次/数据截至/覆盖徽章/搜索/夜间) B 今日总览(结构化条目化:主线+3-5要点+关注) C 分类热点(13类分页,每类8-40条动态上限=4深度卡+热度榜紧凑卡+类目导读)
  D 兴趣深挖(持仓雷达+六段增强卡+Jina全文深读+watchlist命中流) E 热榜交叉(velocity×事件+RSS盲区) F 归档。
  v2(2026-11-18用户反馈): 类目分页(tab/←→/键盘/hash路由), 卡片默认展开单列宽幅(max1200), 日期下拉, 总览JSON条目化。
  热度榜N=clamp(高于top×0.25事件数,8,CAT_LIST_MAX[类目]): 财经/AI/宏观/美股40, A股/商品/医药/新能源/消费/地缘25, 游戏/加密/足球10(2026-11-18拍板A), 冷类目(top<5)封顶8; 紧凑卡无LLM, 扩容零token增量。热度榜跨语去重dedup_heat(拍板E): 贪心非传递——与深度卡primary+已留heat比对same_story_rule命中丢弃(heat_dup记录), 禁union-find传递闭包(防过并吞多样性)。
  归并仅限头部DEEP_CAND=6候选(防财报日同主语传递闭包过并吞空热度榜), 热度榜取其余候选独立呈现。内部链接/news/绝对前缀。
- 13 类目(2026-11-18拍板B: +美股/医药健康/地缘与军工/新能源与汽车/消费): 财经/美股/A股港股/宏观与政策/地缘与军工/AI与科技/医药健康/新能源与汽车/消费/商品期货/加密/游戏/足球。分类=关键词优先(sector在a_hk前, 持仓按主题归sector: CATL→新能源/HENGRUI→医药/MOUTAI→消费)+持仓实体兜底a_hk+topic兜底(医药/新能源/加密/军工)；优先级 crypto>commodity>new_energy>pharma>consumer>us_stock>a_hk>geopolitics>macro>ai_tech>gaming>football>finance；consumer用零售(?!销售)放行macro数据；词边界 \bETH\b/\bAI\b 防误匹配。军工选择分×1.3(CAT_SALIENCE_MULT, 落库salience不变)。
- 知识档: 主体 L2 四段卡+导读+总览；兴趣区 L3 六段增强卡(background 段强制"背景补充(模型知识,非当日报道):"前缀,
  不含需溯源数字；fact/data 经 verify_numbers)。Jina Reader 抓兴趣事件 top2 链接全文, CAPTCHA/失败降级摘要。
- `--dry` 打印分类/候选/兴趣/热榜计划(零token)；`--no-llm` 从已存 portal JSON 重渲染(改样式/回滚验证, 零token)。
- 预算 Budget 类有界(90k)+quota 回退；data/portal_{date}_{edition}.json 全量留档。
- 管线 daily_intel_pipeline.sh $1=edition(morning默认/evening)；晨版 cron a898cbb5e6a5(08:10)无参=morning，
  晚版 cron 750003d2ce23(18:00, script news_intel_evening.sh)。启动器 "$@" 透传。

### 评测 `scripts/eval_golden.py`（4 子命令）
- `build`：黄金集（cross-feed 同 norm_title 正 + cross-company 负 + 同实体不同故事负 + 2026-11-17 人工核验跨语正对/Rubin 负对），独立 ground truth，needs_review；同实体负对自动跳过共享实体≥2 的疑似同故事（防与跨语正对矛盾）。
- `eval [--llm]`：双层回归（聚类层 + brief 归并层 combined）P/R/F1 + by_kind + fp/fn_cases → data/eval_report.json。验收看生产路径 combined P≥0.85 R≥0.80；--llm 用真实 qwen4-max 归并调用评 L2 层。
- `ab`：A/B 五维指标看板 → /var/www/news/eval/dashboard.html（A 标题去重基线 vs B 语义合并）。
- `blind`：双轨盲评页 → /var/www/news/eval/blind.html（A 规则 vs B 事件同日并排 + 5 维判读 guide）。

## D1-D4 落地（用户已拍板）

- **D1 跨 profile 个人化**：读 trader 持仓报告 + gamedev guimei 文档（只读不写，持仓数值不入库不进网页/微信）；历史种子 weight1.5 + 自动刷新 + 对话确认；sync-profiles 周日 21:00。
- **D2 投递面**：微信简报≤4KB（iLink≤2000 字符单分片）+ 全量只读安全链接（用户自己打开读四段卡）；HTML 兜底≤100KB /tmp 短 ASCII 名。
- **D3 双轨 + 反馈**：A 轨（旧规则）vs B 轨（事件中心）并行约 2 周 → 用户盲评拍板微信切换；tune 即时生效（多点/少点/没用），topic_burst 7 天回落。
- **D4 统一投递**：TrendRadar rss/notification/ai_analysis 均 false，Hermes cron 驱动；告警≤2KB 日限 5/同事件 24h 限 1，重试 5/15/45min+补投。

## 只读安全链接（D2，nginx）

- `https://wuhoo.shanavasa.click/news/`：独立 basic auth（`/etc/nginx/.htpasswd-news`，**密码口头交付不入库**）+ `limit_except GET HEAD { deny all; }` 只读 + autoindex off + HSTS/nosniff/no-store。
- 路径：`index.html`（门户，.portal_index 标记感知）、`portal/{date}-{edition}.html`（版次归档）、`daily/{date}.html`（每日简报）、`event/{id}.html`（深卡）、`eval/dashboard.html`（A/B 看板）、`eval/blind.html`（盲评）。
- 无 creds 访问返回 **401 是预期**（非发布失败）；用户持口头凭据侧 200。
- staging `~/wuhoo-workspace/news-web/` → publish_web 拷 `/var/www/news/`（755）。
- conf `/etc/nginx/conf.d/hermes-dashboard.conf`（备份 `.bak-wp6`）。

## cron 清单（D4）

| job_id | 名称 | schedule | 模式 | 角色 |
|---|---|---|---|---|
| d6d628cc68a1 | RSS资讯简报推送 | 0 8 * * * | agent/origin | A 轨 control（微信，冻结 fallback，末条=完整简报正文纪律） |
| a898cbb5e6a5 | 新闻情报daily管线(B轨shadow) | 10 8 * * * | no_agent/local | B 轨 shadow 晨版（brief+门户 morning，web 只读，待切换） |
| 750003d2ce23 | 新闻情报晚版管线(B轨shadow+门户) | 0 18 * * * | no_agent/local | B 轨 shadow 晚版（brief+门户 evening，2026-11-17 用户拍板双版） |
| bb84c71fff5b | hourly 采集 | 每小时 | no_agent | 持续入库 + coverage 统计 + RSSHub 挂死自动重启（refused≥10 连续2轮 → podman restart rsshub，记 ops_alerts.log） |
| bb3616830971 | TrendRadar速度信号 | 20 * * * * | no_agent | velocity_signals 全量刷新（salience V 因子数据源；TrendRadar 挂死时从前一日 db 计算=陈旧） |
| 9c6449d45c15 | 关注巡检告警（paused） | */30 * * * * | — | 施工期防误推，切换后启用 |

## 回滚 runbook（每层独立 disable）

- B 轨停：`cronjob_manage pause job_id=a898cbb5e6a5`（A 轨微信 fallback 自动接管）；晚版另 pause 750003d2ce23。
- 门户回滚：`rm ~/wuhoo-workspace/news-web/.portal_index` 后重跑 brief/publish → publish_web 回退旧 build_index_html 归档索引（portal.py 代码保留，删标记即切换）。
- 微信切换（用户拍板后）：B 轨 cron 改 deliver origin + 推微信；A 轨 pause 保留 fallback。回退=B pause + A resume。
- 采集停：pause bb84c71fff5b。
- nginx 停：`sudo cp /etc/nginx/conf.d/hermes-dashboard.conf.bak-wp6 /etc/nginx/conf.d/hermes-dashboard.conf && sudo nginx -t && sudo nginx -s reload`。
- web 清：`rm -rf /var/www/news/*`（workspace news-web canonical 保留）。
- 凭据轮换：重跑 wp6_htpasswd.py（旧密码立即失效）。
- 规则引擎 fallback：旧 daily_briefing.py 670 行正则冻结（只修 bug），610 行噪声黑名单安全网。

## 踩坑（必读）

1. **黄金集勿循环采样**：正对从「已合并 events」采样 → guard 合并的必 TP → recall 虚高。必须独立 ground truth（cross-feed 同 norm_title 正 / cross-company 负）。
2. **company_subject 须 blocklist 非公司主语**：否则韩国/吴清/美媒/美联储/晚间/A股 误判公司，污染 guard + 负对。
3. **同标题不同摘要会欠合并**：summary[:300] 摘录异 → cosine 偏低（国家统计局案例 cos0.7265）；norm_title 召回兜底修。
4. **re-cluster DELETE 勿 IN 枚举**：事件>999 崩 too many SQL variables；用子查询（WP6 修复）。
5. **自动 PASS ≠ 人工盲评**：50 对启发式 needs_review；微信切换须 2 周观察 + 用户拍板，施工期零未授权推送。
6. **凭据不入库**：/news/ 密码口头交付，不保存/打印/代测；401 无 creds 是预期。
7. **阈值以现场代码为准**：plan §12 写 0.88/0.82，代码校准 direct0.82/entity0.75（wp3_calibration.json）。
8. **大文本微信限流**：64KB 简报触 iLink 限流失败；判读见 hermes-fleet-ops §11。简报≤4KB/≤2000 字符已满足。
9. **跨语同事件 cosine 远低于假定**：multilingual-MiniLM 跨语短标题 cos 实测可低至 0.48-0.51（英英同故事 0.768），低于 entity 阈值 0.75，norm_title 兜底只认完全相同 → 同一故事中英簇各占一席。聚类层勿降阈值强并（会过并同实体不同故事），由 brief 层 LLM+确定性实体锚并集归并。审计 TOP-N 先按主体实体+故事分组查跨语重复；黄金集必须含跨语正对，否则 P/R/F1=1.0 是过拟合。
10. **interest entity 键必须等于 extract_entities 的规范输出**（ENTITY_ALIASES 值/大写 ticker/动态注册名），否则永不命中：名称不在别名表则根本不识别；规范名与键不一致（宁德时代→CATL 而键写 entity:宁德时代）同样是死键。sync-profiles 用 canonical_entity 写键+自动迁移旧键（保留 source/origin_profile）；加种子后验证键能命中再收工。
11. **成品噪声审计两类**：Seeking Alpha 机械类（财报转录/幻灯片/基金评论，单源同分并列贴门槛，淡日灌榜）→ 选择层模式过滤+持仓豁免，不在入库层删（保留数据）；The Verge quickpost 复合标题把多条无关故事混一卡。窗口外事件永不归档仍 active，排序池只增不减；选择层仍无主题多样性配额与窗口守卫（观察项）。审计成品先查这两类噪声与陈旧事件占比。
12. **源健康闸门**：RSSHub conmon 挂死时容器 Up 但全路由 Connection refused，无闸门则管线用残缺口径发布且无感知；现 hourly refused≥10 连续2轮自动 podman restart + brief 前 ratio<0.70 有界重试 + 降级横幅。告警落 data/ops_alerts.log，不做未授权微信推送。
13. **index.html 生成权**：旧由 publish_web/build_index_html 每次 brief/dive 重建（手改必被覆盖）；2026-11-17 起门户模式由 portal.py 生成 index.html + .portal_index 标记，publish_web 标记感知（有标记 copy 门户 index，无标记回退旧归档索引=回滚开关）。定制改 portal.py，勿手改 staging。数据全在 news.db/cards JSON/velocity_signals.json，纯静态生成。
14. **回归测试**：tests/test_intel_fixes_20261117.py（42 用例）+ tests/test_portal.py（45 用例），共 87（2026-11-18 v3 新增 32：13类目分类/动态上限/军工加权/digest过滤/类目噪声/热度去重贪心非传递/429退避），纯逻辑/内存DB/mock LLM；分 skill 运行 `python3.11 -m pytest tests/ -v`（wuhoo-skill-testing 规范）。测试SQL含撇号标题必须参数化(?)勿拼字面量。
16. **门户分类词边界**：关键词正则英文缩写必须左右双边界（\bETH\b/\bAI\b/\bFed\b/\bCOIN\b），否则 Hegseth 尾音 eth 误判加密、Shanghai 尾音 ai 误判科技、Bitcoin 尾音 coin 误判。NBA 2K/GTA 是游戏非足球。分类后必跑 --dry 抽查各类目 top 卡归位。
17. **增强卡背景段纪律**：background 允许模型知识但强制"背景补充(模型知识,非当日报道):"前缀且不含需溯源数字/日期/价格；fact/data 仍经 verify_numbers 对语料(含Jina全文)核验。Jina(r.jina.ai)部分源 CAPTCHA/空 → 降级摘要合成，不编造全文。
18. **门户版次管道**：daily_intel_pipeline.sh $1=edition，启动器 ~/.hermes/scripts/*.sh 用 "$@" 透传（晨版无参=morning，晚版 launcher 写死 evening）。改管线后确认启动器是薄转发（exec bash workspace脚本）而非独立副本，否则 cron 跑旧码。
19. **门户热度榜扩充须限头部归并池**：类目候选扩到8-15后，若 build_groups 跑全部候选，财报日同一主语(NVIDIA)10+事件共享强实体+cos≥0.30 经 union-find 传递闭包塌缩成1张巨卡吞空热度榜(n_total=2)。修：归并仅限头部 DEEP_CAND=6 出深度卡，热度榜取 cands[6:]+头部leftover独立呈现(无全局传递归并)。头部跨语归并(Jensen修复)不回退。审计类目多样性先看 n_total 与 merged_from 长度。
15. **验证修复勿只看重生成页面**：salience 半衰 12h 会让原故障事件跌出 brief 候选窗，页面"看起来正常"不等于修复生效；对原故障事件直接调 build_groups/same_story_rule 做定向断言（目标组归并+反例独立），重生成前把 cards/brief/log/HTML 留档 before/after。

20. **429≠配额耗尽（2026-11-18）**：call_qwen 原对任何429立即标quota=True且零重试→单次瞬时RPM限流即Budget.quota停掉整个门户后续合成。已修：429退避重试15/30/60s(不消耗5xx attempt)，连续失败才标quota；5xx/4xx语义不变。v3构建实测dedup层瞬时429(回退确定性规则是设计内)。回归TestCallQwen429Backoff。
21. **源URL频道错配（2026-11-18）**：Sky Sports Football rss/12040实为综合体育频道(混板球ODI/F1/赛马/拳击WBC/高尔夫)，纯足球是rss/11095；IGN ign/all混影视娱乐，纯游戏是games-all。教训：加源后必抽查实际文章标题的类目纯度(dry看类目TOP)，HTTP 200+XML有效≠内容符合类目。存量污染由选择层CATEGORY_NOISE排除(换URL只管增量)。
22. **dry审计是分类改动必经闸**：v3十三类目上线dry三轮渐进暴露digest变体(【早报】/昨夜今晨/要闻速递)、足球异类、游戏影视、consumer抢macro零售销售——均在选择层/模式层修复并补回归。分类改动后必跑--dry抽查各类目TOP归位(踩坑16的延伸)。

23. **多会话共享 workspace 的 git 卷入（2026-11-18 实证）**：并行 guimei/netdisk 会话 git add -A 会把本会话暂存的 news 文件卷进它的提交（消息不含 news，审计索引断裂）。对策：git add 具体路径后立即 commit+push 不留暂存窗口；提交后 git show --name-only 核对文件清单+内容抽查；被卷入时补审计索引提交恢复可追溯，不重写历史。

## 待用户/观察期

- A5 gateway /restart（WP1 live TrendRadar MCP 注入 + 8642 收尾，用户触发）。
- 微信正式切换（D3-A 盲评约 2 周后拍板）。
- 用户侧认证 200 验证（口头凭据）。
- WP4 link gap（金十/UnusualWhales permalink 提取缺口，全库 0.2%）归 fetcher 后续。