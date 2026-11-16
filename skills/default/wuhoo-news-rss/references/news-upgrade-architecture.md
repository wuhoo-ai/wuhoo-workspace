# 新闻智能升级架构（v2，待拍板）

> 状态：设计文档已落盘，D1-D4 待用户拍板后执行。
> 完整方案：`~/wuhoo-workspace/docs/NEWS-INTELLIGENCE-UPGRADE-2026-11-16.md`

## 源金字塔五层（解决数据源头不足）

根因诊断：源头不足不是"数量少"一个问题，是五重结构性缺口：
- G1 数量：有效源仅 37，长尾极薄
- G2 类型：全是媒体文章，无官方公告/实时电报/社会热榜/开发者信号/游戏垂直
- G3 一手性：零一手源，全二手转述，无法核验
- G4 时效：每天 08:00 一张快照
- G5 独立性：feedx 单点 + 通稿灌水

| 层 | 职责 | 代表源 | 采集方式 |
|----|------|--------|----------|
| T0 一手官方 | ground truth，代表作优先 | 交易所公告/央行/SEC EDGAR/arXiv/GitHub release | RSSHub 路由 + 原生 RSS |
| T1 实时快讯 | 分钟级速度 | 财联社加红/金十/富途/GDELT DOC 2.0 | RSSHub + GDELT API |
| T2 深度媒体 | 解释层 | 修复现有 14 坏源 + 机器之心/晚点/CNBC | RSSHub + 原生 RSS |
| T3 社会热度 | velocity 信号（不进正文） | TrendRadar 热榜 | TrendRadar MCP |
| T4 垂直纵深 | 按业务加权 | Unity/葡萄/GameDiscoverCo/HF/官博/arXiv q-fin | RSSHub + 原生 RSS |

目标：有效供给 37 → ≥120，约 70 个新源。

## TrendRadar 集成设计

三容器：
1. newsnow 自建 `ghcr.io/ourongxing/newsnow:latest` :4444（/api/s）
2. trendradar 主程序（爬取热榜 → 本地 SQLite + HTML）
3. trendradar-mcp `wantcat/trendradar-mcp` :3333/mcp（streamableHttp）

Hermes 注册：
```yaml
mcp_servers:
  trendradar:
    url: http://127.0.0.1:3333/mcp
```
重启生效（可与 8642 收尾 /restart 合并）。

集成原则：
- rss=false, notification=false, ai_analysis=false（避免双抓双推）
- TrendRadar 仅供 T3 velocity 信号 + 27 个 MCP 分析工具
- GPL-3.0 隔离：独立容器 + MCP/数据卷读取，不链接代码
- 数据是本地 output/（非实时联网），trigger_crawl 需 save_to_local=true

## 事件中心设计

- 向量：fastembed multilingual MiniLM 384d + numpy cosine（本地 CPU，零 API 成本，不上向量 DB）
- 合并阈值：cosine ≥ 0.88 直接并；≥ 0.82 + 实体重叠 ≥ 1
- 窗口：72h
- canonical 优先级：T0 > T1 > T2 > T3
- 独立源计数：去掉通稿/转载灌水

## salience 排序公式

```
salience = W × (1 + ln(1 + N_indep)) × V × D(half-life 12h) × P × B
```
- W: 源基础权重
- N_indep: 独立源数
- V: velocity（TrendRadar 热榜速度）
- D: 时间衰减（半衰期 12h）
- P: 个人化相关度
- B: 业务加权（投资40/科技AI30/宏观20/游戏10）

## 工作包（一次性施工顺序）

WP0 源探测与修复 → WP1 TrendRadar/newsnow 部署 → WP2 采集提频 → WP3 事件聚类 → WP4 salience 排序 → WP5 agent 原生工具 → WP6 合成与投递 → WP7 反馈闭环 → WP8 A/B 观察

约 13.5 人日 + 2 周 A/B。

## 待拍板决策

- D1 个人化范围：A 兴趣档案+对话反馈 / B 跨 profile / C 不做
- D2 投递面：A 微信+本地网页 / B 仅微信 / C +邮件
- D3 规则引擎：A 双轨 A/B 两周 / B 直接替换 / C 规则为主
- D4 TrendRadar 推送：A 关闭统一 Hermes / B 保留备用

## GDELT DOC 2.0 API

- 端点：`api.gdeltproject.org/api/v2/doc/doc`
- 参数：query, mode=ArtList/Timeline, format=json, timespan, maxrecords
- 免费无 key，15min 更新，滚动窗口默认 24h（最长 3 月）
- 用途：全球传播速度 + 跨语言覆盖（补 RSS 采不到的境外本地媒体）

## RSSHub 候选路由（待实测）

金融：/cls/telegraph, /cls/depth/1000, /jin10, /futunn/highlights, /gelonghui/home, /sse/disclosure, /bse/:category?, /gov/pbc/goutongjiaoliu
科技：/github/trending/daily/any, /producthunt/today, /huggingface/blog, /anthropic/news
游戏：/unity/blog, /steam/news, /gamelook, /youxiputao, /chuapp, /yystv
热榜：/weibo/hot, /zhihu/hotlist, /bilibili/hot-search, /baidu/top, /douyin/hot, /toutiao/hot

⚠️ 全部待 WP0 实测确认（路由探测需用户授权执行）。
