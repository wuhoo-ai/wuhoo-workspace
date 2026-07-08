# 单场PDF报告生成器 (v5.5)

## 概述

`scripts/generate_single_match_pdf.py` — 使用 reportlab 直接生成单场预测PDF，替代 xhtml2pdf 方案。
解决xhtml2pdf的中文emoji乱码、字体渲染差、不可控等问题。

## 特性

- **纯reportlab生成** — 完全控制布局、字体、表格
- **无emoji** — 使用文字标签替代 (📋→[规则], ⚡→[修正])
- **数据源全标注** — 每个分析层标注数据来源文件/API
- **obj条件因子** — L4a天气(Open-Meteo) + L4b赛程密度(Haversine)
- **RSS报道** — 5天窗口，搜索标题+摘要，展示来源和标题
- **v5.5推理路径** — 规则链完整展示（50行）
- **<100KB** — 满足微信文件推送限制

## CLI

```bash
# 单场
python3.11 scripts/generate_single_match_pdf.py 1 --date 2026-06-25

# 全部
python3.11 scripts/generate_single_match_pdf.py --date 2026-06-25 --all

# 输出: data/reports/single/report_2026-06-25_瑞士_vs_加拿大.pdf
```

## 报告结构

| 层级 | 标题 | 数据源 |
|------|------|--------|
| L1 | ELO基础实力 | elo_ratings.json |
| L2 | 伤病影响 | injuries.json (ESPN/BBC/Fox) |
| L2.5 | 出线动机QMF | compute_motivation.py |
| L3 | 教练/团队磨合 | team_profiles.json |
| L4 | 场地影响 | venues.json + wc2026_schedule.json |
| L4a | 天气因子 | fetch_weather.py (Open-Meteo) |
| L4b | 赛程密度 | 赛程表 + Haversine距离 |
| L4.5 | 热身赛状态 | friendly_form_adjustments.json |
| L4.6 | 本届比赛表现 | wc2026_results.json |
| L5 | 新闻情感+RSS | news.db (5天窗口/标题+摘要) |
| — | 有效ELO汇总 | 含引擎增量 |
| — | Poisson预测 | xG/比分/置信度 |
| — | v5.5推理路径 | rules_v1.json规则链 |

## RSS搜索策略

- 窗口：pub_date > datetime('now', '-5 days')
- 字段：title LIKE OR summary LIKE（比仅搜标题命中率高3-5倍）
- 排除：SoccerNews, World Soccer Talk, Football Rankings（低质源）
- 去重：按title去重，上限8篇

## 已知问题

- 部分球队近5天无高质量RSS报道（如海地、卡塔尔），搜索放宽到summary后仍有噪音标题混入
- 引擎增量字段在合并后的JSON中位于 effective_elo.engine_delta_a/b 顶层
