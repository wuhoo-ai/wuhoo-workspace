# 生产剖析（Production Autopsy）— daily 管线只读取证流程

何时用：用户要求剖析某日新闻生产（用了什么模型/花了多少 tokens/运行过程/配置了哪些主体关键词/找到多少文章/去重排序/成品筛选/优化点）。全程只读，不改生产代码；优化建议分级列给用户拍板，不自行立项。

## 1. 证据源（按取证顺序）

路径未注明者相对 `~/wuhoo-workspace/skills/default/wuhoo-news-intel/`。

1. **管线日志** `data/pipeline_<YYYYMMDD>.log`：每步耗时、embed/cluster 数量与合并率、tokens、四件套输出路径。B轨总时长 = START→DONE 时间差。
2. **cron 输出** `~/.hermes/cron/output/<job_id>/<date>_*.md`：A轨（agent 模式）尾部 = 最终微信简报正文 + 统计行（48h 总/过滤后/事件合并/未匹配）；B轨（no_agent）= 管线日志尾。投递成败看 jobs.json 的 `last_status` / `last_delivery_error`（执行成功≠投递成功）。
3. **cards JSON** `data/cards_<YYYYMMDD>.json`：顶层 meta `model/total_tokens/quota_hit/coverage/dedup_mode/noise_filtered/merged_groups`；逐卡 `usage.prompt_tokens/completion_tokens/total_tokens`、`numbers_verified`、`unverified_numbers`、`links`、`salience`、`n_indep`、`primary_entities`、`merged_from`（归并卡）。Σusage+归并调用 usage = B轨合成成本（每卡量级随模型档位变化，勿硬编码）；预算利用率 = total/60000。
4. **news.db**（`wuhoo-news-rss/data/news.db`，sqlite3 + row_factory）：
   - 今日入库：`articles WHERE fetched_at>='<YYYY-MM-DD>'`（ISO 本地时间字符串，可直接比较），GROUP BY category / feed_name。
   - 生产口径：72h 窗口文章数；`events WHERE status='active' ORDER BY salience DESC` 取 TOP-N + 分数分桶分布；陈旧事件 = active AND last_seen < 窗口 cutoff（永不归档，已知）。
   - 疑似重复事件：`event_members JOIN articles` 看成员标题 + similarity——跨语同故事簇内 sim 0.75-0.85 但簇间互不合并。
   - 个人化与信号：interest_profile / topic_burst / watchlist 全表；`velocity_signals MAX(computed_at)` 新鲜度。
   - 源健康：feed_health（tier/status/fail_streak）。
5. **hourly_fetch.log** 正则解析每轮统计：
   `r"总条目:\s*(\d+)\s*\n\s*新增:\s*(\d+)\s*\n\s*重复:\s*(\d+)\s*\n\s*失败:\s*(\d+)\s*\n(<date> [\d:]+) END"`
   失败数突增且全为 Connection refused = RSSHub conmon 挂死（判定与修复见 wuhoo-news-rss 同名 pitfall）；恢复后首轮新增激增 = 积压涌入，这些文章不进已发布的 brief。注意区分 hourly 轮与双轨管线内 fetch 轮（flock 串行，END 时刻相邻）。
6. **A轨 token/模型**（`~/.hermes/state.db`）：
   - `sessions WHERE source='cron' AND title LIKE '<job名>%'`；**started_at/last_activity_at 是 epoch float**，用 datetime.fromtimestamp 转换后过滤，按日期字符串 LIKE 必空。
   - `session_model_usage WHERE session_id=…`：按模型的 input/output/cache_read/reasoning/api_call_count = 权威用量。
   - **实际运行模型以 sessions.model 为准**；jobs.json 的 model 是当前配置，可能被后续默认模型切换会话改掉（漂移）——两者都查、分别报告，并提示次日成本变化。
7. **容器时间线**：`podman inspect <ct> --format '{{.State.StartedAt}} {{.State.FinishedAt}} {{.RestartCount}}'`——FinishedAt≈StartedAt-3s 且 restarts=0 = 手动批量重启时刻；对照 hourly 失败数界定挂死窗口。newsnow/trendradar 挂死期间 velocity 从前一日 db 计算（V 因子陈旧），查 velocity cron 输出确认数据来源日期。
8. **发布验证**：`sha256sum` staging `news-web/daily/<date>.html` vs `/var/www/news/daily/<date>.html` 一致；curl 无凭据返回 401 是预期（不代测凭据）。
9. **配置面**：feeds/config.yaml 源数/类别/feed_weights；watchlist.yaml 分组；jobs.json 全量 cron（含 velocity job bb3616830971 每小时 :20、告警 job paused 状态）。

## 2. 成品质量审计 checklist（对 TOP-N 卡逐条过）

- **跨语同故事重复**：按主体实体+故事分组；同一事件中英文簇各占一席 = 欠合并，统计浪费席位数与 tokens 占比。量化用质心互 cos：`event_members → ec.load_vectors → 归一化均值=质心 → 两两 @`；判读：≥0.75 却未并=聚类候选扫描/到达顺序问题，0.4-0.6 跨语=嵌入模型跨语短标题极限（聚类层勿强并，brief 层归并兜底），<0.3 同实体=不同故事勿并。
- **复合标题污染**：The Verge quickpost/liveblog 类标题打包多条无关故事；检查 fact 段落是否前后跳变不连贯。
- **单源噪声贴门槛**：看第 N+1..N+5 名——SA "Q3 … Comment / Earnings Call Transcript / Presents at" 类单源同分并列（源权重 9 × 财经 interest），新闻淡日会灌满 TOP-N。选择层现已有模式过滤（持仓豁免）+单源 ×0.9 降权；审计 cards meta `noise_filtered` 与漏网案例，勿假设无过滤。
- **个人化死键**：interest entity 键必须等于 extract_entities 规范输出（ENTITY_ALIASES 值/大写 ticker）；A股名不在别名表永不命中，规范名不匹配（宁德时代 vs CATL）也是死键。列出"实际生效键"与"死键"两张清单。
- **P 因子交互**：burst 可压过负 interest（如 科技 -0.1 × burst +0.5 → P=1.35），解释成品主题偏斜。
- **排序脆弱性**：第 N 与 N+1 名分差；salience 长尾分布（<5 分占比）。
- **源覆盖**：读 `data/source_coverage.json`（ok/total/ratio/refused/ts，hourly wrapper 每轮写）；ratio<0.70=降级，brief 已有有界重试+降级横幅。审计历史运行时用 hourly 失败数重建生产时点覆盖并在报告标注。
- **微信截断**：英文标题 40 字 / fact 90 字硬截会断词断句。

## 3. 报告与收工约定

- 中文完整展开（是什么/为什么/怎么落地），每个数字来自现场证据并注明来源路径；禁止名词堆叠。
- 落盘 `~/wuhoo-workspace/docs/news-intel-build/PRODUCTION-AUTOPSY-<YYYY-MM-DD>.md`；优化点按 P0/P1/P2 分级（现象→根因→建议）；待拍板事项单列（含模型钉定/切换节奏这类有时效项）。
- 收工写 1 条 MemPalace pitfall（wing=project-hermes-infra）：check_duplicate → add_drawer → search 独特短语验证 top3。
- 若用户接着要定制 index.html：先说明 publish_web 每次自动重建 index（build_index_html），手改会被覆盖，定制须改代码或模板机制——方案讨论前不动代码。

## 4. 修复后验证纪律（剖析转施工时）

- 重生成 brief 前把 cards/brief/pipeline log/HTML 拷入 `data/archive_pre_fix_<date>/` 留 before/after。
- 重生成会覆盖当日发布页且成为当前时点快照：salience 半衰 12h 会让早间故障事件衰减出 TOP20 候选窗，页面"看起来正常"≠修复生效。必须对原故障事件直接调 `intel.build_groups` / `same_story_rule` 做定向断言（目标组归并+反例独立），这才是修复证据。
- 黄金集 eval 分 clustering_only 与 combined（生产路径）双层报告；验收看 combined，单层满分可能是过拟合；补跨语正对后重跑 build+eval。
- 验证命令（pytest/bash -n）单独一条 terminal 调用运行，不与其他命令串接（exit 归因，见 wuhoo-skill-testing）。
