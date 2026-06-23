# 客观条件因子分析 — v5.2 设计文档

> 触发: 2026-06-22 France vs Iraq (Lincoln Financial Field, Philadelphia) 雷暴中断2小时

## 因子清单

| 因子 | 优先级 | ELO量级 | 数据源 | 实现状态 |
|------|--------|---------|--------|----------|
| 降水 (Rain) | P0 | -15~-50 | Open-Meteo WMO天气码 | ✅ Layer 4a |
| 实时温度 | P1 | 替换静态均温 | Open-Meteo | ✅ Layer 4a |
| 风力 (Wind) | P1 | 0~-15 | Open-Meteo, 室内豁免 | ✅ Layer 4a |
| 旅途疲劳 | P2 | 0~-20 | schedule + venue坐标 | ✅ Layer 4b (合并) |
| 休息天数 | P2 | ±24 | schedule | ✅ Layer 4b (合并) |
| 草皮类型 | P3 | ±10 | venues.json 静态 | ⏳ 后置 |

## 关键设计决策

### 数据源: Open-Meteo
- 免费, 无需 API key
- 全球覆盖, 支持 forecast_days=7
- 三重降级: API → venues.json 静态均值 → 0
- 温和限速: 0.1s delay per call

### 风格分类: 关键词规则
`team_profiles.json` 48 个 style_tag 全为自由文本中文描述 (如 "天赋溢出、阵容深度恐怖")。
通过关键词规则自动分类为 6 类枚举:
- `possession`: "传控" "技术流"
- `physical`: "身体" "对抗" "硬朗"
- `counter`: "反击" "速度"
- `defensive`: "防守" "铁桶" "纪律"
- `high_press`: "压迫" "跑动"
- `balanced`: 默认

**注意**: 关键词分类可能有误，需人工复核。

### WMO Weather Code 映射
```
0=clear, 1=mainly_clear, 2=partly_cloudy, 3=overcast
45/48=fog
51-57=drizzle (light/moderate)
61-67=rain (light/moderate/heavy)
80-82=rain showers
85-86/95-99=thunderstorm
```

### 赛程密度公式
```
travel_penalty = -min(distance_km / 500 × 5, 20)
rest_bonus = clamp((rest_team - rest_opponent) × 8, -24, 24)
net_density = (travel + rest) / 2, capped ±20
```

### 权重设计
- 天气因子: 基准 5% (rain 特殊处理 max ±30 ELO)
- 赛程密度: 基准 3% (max ±20 ELO)
- 低权重设计意图: 实验性因子，附加参考，不做方向性判断

## 文件变更
- `scripts/fetch_weather.py`: 新建, Open-Meteo 天气采集
- `wc2026_predict.py`: 新增 Layer 4a (Weather) + Layer 4b (Schedule Density)
- `scripts/predict_by_date.py`: 报告底部新增客观条件因子模块
- `data/venues.json`: 16场馆补充 coordinates + pitch_type
- `data/team_profiles.json`: 48队新增 style_category
- Cron: 5154715032ec + 86912ff0a4aa 更新

## 端到端测试 (2026-06-24 预测)
```
🌧️ 客观条件因子 (v5.2 实验性)
葡萄牙vs乌兹别克斯坦    中雨    室内      +0/-7
英格兰vs加纳            无   breezy     -10/+0   ← England飞2493km
巴拿马vs克罗地亚         无    室内    -10/-10
哥伦比亚vs刚果民主共和国   中雨  breezy      +0/-7
```
