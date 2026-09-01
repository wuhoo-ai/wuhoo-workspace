# WC2026 预测日报 v5.0
生成: 2026-06-24T15:08 BJT  |  共 6 场
格式: 证据链 (数据源+本届战绩+RSS关键信息)

### #1  瑞士 vs 加拿大
2026-06-25 03:00 BJT  |  Group B MD3  |  BC Place

#### [证据链]

**L1  ELO基础实力**  (来源: *elo_ratings.json*)
> 瑞士  FIFA#14  **1803**  (防守稳固、战术成熟)  vs  加拿大  FIFA#34  **1827**  (速度型、年轻阵容)
> 基础差 **-24**,  基础胜率 **46.6%**

**L2  伤病影响**  (来源: *injuries.json*)
> 加拿大: **Alphonso Davies** [DOUBTFUL] Hamstring strain (recurring, since May 6); ran laps pre-Uzbe  -> 罚 **-20**
> 加拿大: **Marcelo Flores** [OUT] ACL rupture (Concacaf Champions Cup final)  -> 罚 **-5**
> 加拿大: **Moise Bombito** [OUT] Shin fracture relapse (Jun 2026)  -> 罚 **-5**

**L3  教练/团队磨合**  (来源: *TEAM_PROFILES*)
> 瑞士: WC13届, 队史八强 (1954)  |  加拿大: WC3届, 队史小组赛

```
  评估维度         瑞士       加拿大      说明
  --------------------------------------------------
  教练经验           +8       0    世界杯执教场次/成绩
  历史战绩           +2       0    队史最佳成绩加分
  阵容稳定         +12.0    +4.0    核心球员保留率
  团队化学         +8.4    +5.4    合练场次/友谊赛默契度
  --------------------------------------------------
  合计           +30       +9
```

**L4  场地影响**  (来源: *wc2026_schedule.json*)
> Vancouver, 19C | 室内球场
> 瑞士 罚 **0**  /  加拿大 罚 **0**

**L4.5  热身赛表现**  (来源: *friendly_form 赛前3场*)
> 瑞士 **+28**  /  加拿大 **+13**

**L4.6  本届比赛表现**  (来源: *wc2026_results.json*  权重0.12)
> 瑞士 **+28**  /  加拿大 **+48**
>   [06-14] D 1-1 vs 卡塔尔 (1512ELO q=+0.03 r=1.0x) → +0
>   [06-19] W 4-1 vs 波黑 (1552ELO q=+0.13 r=1.3x) → +27
>   [06-13] D 1-1 vs 波黑 (1552ELO q=+0.13 r=1.0x) → +1
>   [06-19] W 6-0/CS vs 卡塔尔 (1512ELO q=+0.03 r=1.3x) → +47

**本届战绩**  (Group B)

  * 瑞士  [14/06]  vs 卡塔尔  --  1-1 平
  * 瑞士  [19/06]  vs 波黑  --  4-1 胜
  * 加拿大  [13/06]  vs 波黑  --  1-1 平
  * 加拿大  [19/06]  vs 卡塔尔  --  6-0 胜

  Group B 积分榜:
```
  排名   球队         场   胜   平   负    进    失   分
  ----------------------------------------
  1    加拿大        2   1   1   0    7    1   4
  2    瑞士         2   1   1   0    5    2   4
  3    波黑         2   0   1   1    2    5   1
  4    卡塔尔        2   0   1   1    1    7   1
```

**L5  RSS新闻情感**  (来源: *news.db*  权重0.05)
> 瑞士 **0**  /  加拿大 **0**
>    2026 World Cup: Switzerland 对阵. Bosnia confirmed line-ups – 
>    Manzambi double inspires Switzerland rout of 10-man Bosnia a [胜负]
>    Super sub Manzambi helps Switzerland close on knockout stage [胜负]

**L5.5  v5.0 LLM非结构化信号**  (来源: *signal_cache*  权重0.15)
> 瑞士 **0**  /  加拿大 **0**  |  战术匹配 **+0.00**  |  7类信号:伤病/战术/状态/团队/阵容/外部/纪律

---
#### [有效ELO汇总]

```
              瑞士         加拿大       
  ------------------------------
  ELO原始      1803      1827 
  L1-L4.6+L5.5  +83       +25
  ------------------------------
  有效ELO       1886      1852 
  有效差                  +34
  🧠引擎增量              +18       +14
```

#### [Poisson预测]

```
  瑞士胜        41.5%
  平局          25.3%
  加拿大胜        33.2%
  最可能比分    1-1  (xG 1.48/1.29)
  置信度        [LOW]
```

**判定: 倾向平局**

#### [v5.5 推理路径]
Switzerland (+18 ELO):
  📋 半区路径偏好(+0, conf=medium×0.7) → +0.0
  └ 证据: BPP分析 — R32对阵路径ELO对比
  📋 出线动机 — TOP_SEED(+8, conf=high×1.0) → +8.0
  ⚡ 饱和: ×0.512 → +4.1
  └ 证据: QMF自动分类 — 头名之争
  📋 热身赛状态(+0, conf=low×0.4) → +0.0
  └ 证据: friendly_form_adjustments.json — 热身赛ELO差异
  📋 锦标赛形态(+14, conf=low×0.4) → +5.6
  ⚡ 饱和: ×0.512 → +2.9
  └ 证据: 随机抽样的锦标赛形态波动
  📋 天气因子(+0, conf=medium×0.7) → +0.0
  └ 证据: Open-Meteo API — 比赛日预报
  📋 赛程密度(+0, conf=medium×0.7) → +0.0
  └ 证据: Haversine距离+休息天数计算
  📋 场馆效应(+0, conf=high×1.0) → +0.0
  └ 证据: venues.json — 16场馆数据
  📋 教练/磨合因子(+30, conf=medium×0.7) → +21.0
  ⚡ 饱和: ×0.512 → +10.8
  └ 证据: team_metadata.json — 静态元数据
  📋 手动调整(+0, conf=high×1.0) → +0.0
  └ 证据: manual_adjustments.json
  ⚡ 饱和: 正面累计=35 → sigmoid → +18
  ────────────────────────────────────────
  净调整: +18 ELO
Canada (+14 ELO):
  📋 半区路径偏好(+0, conf=medium×0.7) → +0.0
  └ 证据: BPP分析 — R32对阵路径ELO对比
  📋 出线动机 — TOP_SEED(+8, conf=high×1.0) → +8.0
  └ 证据: QMF自动分类 — 头名之争
  📋 热身赛状态(+0, conf=low×0.4) → +0.0
  └ 证据: friendly_form_adjustments.json — 热身赛ELO差异
  📋 锦标赛形态(+0, conf=low×0.4) → +0.0
  └ 证据: 随机抽样的锦标赛形态波动
  📋 天气因子(+0, conf=medium×0.7) → +0.0
  └ 证据: Open-Meteo API — 比赛日预报
  📋 赛程密度(+0, conf=medium×0.7) → +0.0
  └ 证据: Haversine距离+休息天数计算
  📋 场馆效应(+0, conf=high×1.0) → +0.0
  └ 证据: venues.json — 16场馆数据
  📋 教练/磨合因子(+9, conf=medium×0.7) → +6.3
  └ 证据: team_metadata.json — 静态元数据
  📋 手动调整(+0, conf=high×1.0) → +0.0
  └ 证据: manual_adjustments.json
  ────────────────────────────────────────
  净调整: +14 ELO

[!] 预测仅供娱乐参考 | v5.0.0