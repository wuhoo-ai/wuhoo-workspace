---
name: wuhoo-news-intel
description: "Use when 新闻情报简报/事件聚类去重/双轨A-B评测/只读安全链接. 事件中心管线+agent原生层,  companion to wuhoo-news-rss."
tags: ["wuhoo"]
category: research
---

# Wuhoo 新闻情报（agent 原生事件中心）

从 `wuhoo-news-rss` 的 SQLite 库出发，做语义聚类去重 → 事件中心 → salience 排序 → 四段卡合成（数字核验）→ 微信简报 + 全量只读安全链接 → 反馈/个人化闭环。替代旧规则引擎 `wuhoo-rss-briefing`（冻结为 A 轨 fallback）。

> **依赖**: `wuhoo-news-rss`（DB `skills/default/wuhoo-news-rss/data/news.db`，共享）；fastembed（paraphrase-multilingual-MiniLM-L12-v2，384d CPU）；qwen flash 合成。
> **Python**: 必须 `/usr/bin/python3.11`。
> **方案**: `docs/NEWS-INTELLIGENCE-UPGRADE-2026-11-16.md`（v3）；**施工审计**: `docs/news-intel-build/AUDIT-LOG.md`（WP0-WP8 全证据）。
> **根目录**: `~/wuhoo-workspace/skills/default/wuhoo-news-intel/`（src/ scripts/ data/）。

## 何时使用

- 生成每日新闻情报简报（事件级去重，非标题级）、深挖某事件、按实体/主题检索时间线。
- 调个人化（多点X/少点X/这条没用）、跨 profile 同步兴趣种子、watchlist 告警。
- 评测聚类质量（黄金集回归）、A/B 双轨指标看板、双轨盲评。
- 排查管线（fetch→embed→cluster→brief→publish→deliver）某步失败。

## 架构与管线（B 轨 shadow）

`scripts/daily_intel_pipeline.sh`（cron `a898cbb5e6a5` 08:10）链式执行，任一步 rc≠0 即停后续：

```
fetch（hourly cron bb84c71fff5b 已入库）
  → event_center.py run --window 72   # embed 新文章 + 聚类 + salience + 落库
  → intel.py brief --format web       # TOP10 四段卡 + 微信≤4KB + daily HTML + 兜底≤100KB
  → intel.py publish（publish_web）    # staging news-web/ → /var/www/news/（nginx 只读 auth）
  → deliver local                      # shadow 仅存档，不推微信
```

- **聚类阈值（现场校准值，非 plan 初始值）**: direct cosine≥0.82 直接并 / entity≥0.75+实体重叠≥1；窗口 72h；canonical T0>T1>T2>T3。
- **召回兜底**: 同 `norm_title_key`（去 HTML/栏目前缀/标点，仅 CJK+字母+数字 lower，≥8 字符）跨 feed 强制合并（通稿同故事，覆盖 cosine 限制）。
- **精度 guard**: `company_subject` 提取公司公告主语（前 2 字符核心），`_NON_COMPANY` blocklist 拒绝国家/政府/央行/媒体/人名/时段/板块等非公司主语；不同公司核心不合并。
- **salience**: W×(1+ln(1+N_indep))×V×D(半衰12h)×P×B；P 叠加 topic_burst + interest_profile（负 gain 允许 demote，floor 0.3）。
- **re-cluster 删除用子查询**（非 IN 枚举）：规避 SQLite 999 变量上限（事件>999 必崩 too many SQL variables，WP6 根因修复）。

## 命令清单

### 事件中心 `src/event_center.py`
- `run --window 72`：embed + cluster + salience + 落库（管线核心）。
- `embed_articles` / `cluster`：可单独委托（WP5 wiring）。

### Agent 层 `src/intel.py`（14 子命令）
- `health`：articles/events/members/vectors/entities/核验率/容器/deliveries 总览。
- `rank [--top N]`：salience TOP 事件。
- `brief [--top N] [--format web|wechat]`：四段卡（事实/影响/分歧/下一步）+ 数字核验 + 微信≤4KB + daily HTML + 兜底。
- `dive <event_id> [--html]`：事件深卡（primary/incidental 实体频次加权抑制）+ event HTML。
- `search <关键词>` / `timeline <实体>`：检索 + 逆时序事件线。
- `audit`：源健康（ok/degraded/down/empty）。
- `watch add|list|remove` / `alert [--dry-run]`：watchlist 告警（去重/限流/重试）。
- `profile show|update` / `tune` / `sync-profiles`：个人化 + 反馈调节 + 跨 profile 种子。
- `fetch [--dry-run]` / `cluster`：采集/聚类委托。
- `publish`：publish_web（staging→/var/www/news/ + index 归档）。

### 评测 `scripts/eval_golden.py`（4 子命令）
- `build`：50 对黄金集（25 正 cross-feed 同 norm_title + 25 负 cross-company），独立 ground truth，needs_review。
- `eval`：回归 P/R/F1 + fp_cases/fn_cases → data/eval_report.json。验收 P≥0.85 R≥0.80。
- `ab`：A/B 五维指标看板 → /var/www/news/eval/dashboard.html（A 标题去重基线 vs B 语义合并）。
- `blind`：双轨盲评页 → /var/www/news/eval/blind.html（A 规则 vs B 事件同日并排 + 5 维判读 guide）。

## D1-D4 落地（用户已拍板）

- **D1 跨 profile 个人化**：读 trader 持仓报告 + gamedev guimei 文档（只读不写，持仓数值不入库不进网页/微信）；历史种子 weight1.5 + 自动刷新 + 对话确认；sync-profiles 周日 21:00。
- **D2 投递面**：微信简报≤4KB（iLink≤2000 字符单分片）+ 全量只读安全链接（用户自己打开读四段卡）；HTML 兜底≤100KB /tmp 短 ASCII 名。
- **D3 双轨 + 反馈**：A 轨（旧规则）vs B 轨（事件中心）并行约 2 周 → 用户盲评拍板微信切换；tune 即时生效（多点/少点/没用），topic_burst 7 天回落。
- **D4 统一投递**：TrendRadar rss/notification/ai_analysis 均 false，Hermes cron 驱动；告警≤2KB 日限 5/同事件 24h 限 1，重试 5/15/45min+补投。

## 只读安全链接（D2，nginx）

- `https://wuhoo.shanavasa.click/news/`：独立 basic auth（`/etc/nginx/.htpasswd-news`，**密码口头交付不入库**）+ `limit_except GET HEAD { deny all; }` 只读 + autoindex off + HSTS/nosniff/no-store。
- 路径：`daily/{date}.html`（每日简报）、`event/{id}.html`（深卡）、`eval/dashboard.html`（A/B 看板）、`eval/blind.html`（盲评）、`index.html`（归档）。
- 无 creds 访问返回 **401 是预期**（非发布失败）；用户持口头凭据侧 200。
- staging `~/wuhoo-workspace/news-web/` → publish_web 拷 `/var/www/news/`（755）。
- conf `/etc/nginx/conf.d/hermes-dashboard.conf`（备份 `.bak-wp6`）。

## cron 清单（D4）

| job_id | 名称 | schedule | 模式 | 角色 |
|---|---|---|---|---|
| d6d628cc68a1 | RSS资讯简报推送 | 0 8 * * * | agent/origin | A 轨 control（微信，冻结 fallback，末条=完整简报正文纪律） |
| a898cbb5e6a5 | 新闻情报daily管线(B轨shadow) | 10 8 * * * | no_agent/local | B 轨 shadow（web 只读，待切换） |
| bb84c71fff5b | hourly 采集 | 每小时 | no_agent | 持续入库 |
| watchlist 告警 | （paused） | 15min | — | 施工期防误推，切换后启用 |

## 回滚 runbook（每层独立 disable）

- B 轨停：`cronjob_manage pause job_id=a898cbb5e6a5`（A 轨微信 fallback 自动接管）。
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

## 待用户/观察期

- A5 gateway /restart（WP1 live TrendRadar MCP 注入 + 8642 收尾，用户触发）。
- 微信正式切换（D3-A 盲评约 2 周后拍板）。
- 用户侧认证 200 验证（口头凭据）。
- WP4 link gap（金十/UnusualWhales permalink 提取缺口，全库 0.2%）归 fetcher 后续。