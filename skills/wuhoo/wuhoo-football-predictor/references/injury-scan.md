# 赛前伤病扫描参考

## 数据源

### 1. ESPN 伤病追踪器（主源）
URL: `https://www.espn.com/soccer/story/_/id/48572979/2026-fifa-world-cup-injuries-tracker-which-stars-miss-latest-info`
- 覆盖所有 48 队伤病汇总
- 分为三档：Will Miss / Concerning / Should Play
- 更新频率：不固定，last update 6/9
- 抓取方式：`web_extract([url])` → 提取伤病列表 → 与 injuries.json 比对

### 2. 赛前定向搜索（补漏）
格式：`web_search("Team_Name World Cup 2026 injury illness OUT news June XX")`
- 用于捕捉 ESPN 追踪器未覆盖的突发公告
- 例：Doku illness 是 @BelRedDevils 6/20 发推，ESPN 追踪器未包含
- 关键时间窗口：赛前 24-48h

### 3. 球队官方 Twitter/X（未来）
- @BelRedDevils (比利时)
- @OnsOranje (荷兰)
- @DFB_Team (德国)
- @USMNT (美国)
等

## 已知盲区

| 盲区类型 | 案例 | 如何补漏 |
|----------|------|----------|
| 赛前生病 (illness) | Doku 6/20 宣布缺席 vs Iran | web_search 赛前定向扫描 |
| 个人原因缺席 | Doku 妻子生产（7月） | 同上 |
| 战术轮换 | 提前出线后轮休主力 | 需关注小组形势 |
| 赛前热身受伤 | 最后训练受伤 | 几乎无法预判 |

## 流程

```
1. ESPN 追踪器 → 提取伤病列表 → 更新 injuries.json
2. web_search 定向搜索明日所有球队
3. 发现新伤病 → patch injuries.json
4. 重跑 predict_by_date.py --date <tomorrow>
5. 重跑 generate_daily_report.py --date <tomorrow>
```
