# 小组赛 Venue 映射机制

> v2.2 新增 — 各组 3 个比赛日匹配到实际球场

## 数据来源

`data/group_venues.json` — 基于 Sports Illustrated 2026 世界杯完整赛程 (2026-05-21)

每组 3 个比赛日，每个比赛日一个 venue。各组的 venue 选取原则：以该组种子队 (Pot 1) 的实际比赛球场为准。因同组两场比赛通常在邻近城市/同一球场，此近似合理。

## 比赛日映射算法

小组 4 队索引为 0,1,2,3 (按 GROUPS 字典顺序)。6 场小组赛配对：

```
MD1: (0,1) (2,3)
MD2: (0,2) (1,3)
MD3: (0,3) (1,2)
```

代码实现：
```python
if (i == 0 and j == 1) or (i == 2 and j == 3):
    md = 0  # MD1
elif (i == 0 and j == 2) or (i == 1 and j == 3):
    md = 1  # MD2
else:
    md = 2  # MD3

venue_name = group_venue_list[md]
ga, gb = sim_match(home, away, elo_home, elo_away, home_adv, venue_name=venue_name)
```

## 12 组 Venue 分配

| 组 | MD1 | MD2 | MD3 | 依据 |
|----|-----|-----|-----|------|
| A | Azteca | Akron | Azteca | Mexico 种子队 |
| B | BMO Field | BC Place | BC Place | Canada 种子队 |
| C | MetLife | Lincoln | Hard Rock | Brazil 种子队 |
| D | SoFi | Lumen | SoFi | USA 种子队 |
| E | NRG | BMO Field | MetLife | Germany 种子队 |
| F | AT&T | NRG | AT&T | Netherlands 种子队 |
| G | Lumen | SoFi | BC Place | Belgium 种子队 |
| H | Mercedes-Benz | Hard Rock | Hard Rock | Spain 种子队 |
| I | MetLife | Lincoln | Gillette | France 种子队 |
| J | Arrowhead | AT&T | AT&T | Argentina 种子队 |
| K | NRG | NRG | Hard Rock | Portugal 种子队 |
| L | AT&T | Gillette | MetLife | England 种子队 |

## 关键球场特征

- **Estadio Azteca** (2200m): 高海拔惩罚 ~68 ELO，适应队: Mexico, Ecuador, Colombia
- **Hard Rock Stadium** (Miami, 32°C): 高温惩罚 ~8 ELO
- **NRG Stadium** (Houston, 34°C): 室内，高温惩罚减半

## Venue 惩罚逻辑

```python
def get_venue_penalty(team, venue_name):
    # 返回正值 → 在 sim_match 中从 ELO 减去
    # 海拔: (alt_m - 500) / 1000 * penalty_per_1000m
    # 高温: (temp_c - threshold_c) / 5 * penalty_per_5c
    # 室内高温: ×0.5
```

## 校验

`validate_data()` 已扩展为检查 `group_venues.json` 中所有 venue 名称是否在 `venues.json` 中存在。
