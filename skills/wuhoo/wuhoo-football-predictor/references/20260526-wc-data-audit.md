# 2026-05-26 世界杯数据更新与预测审计

## 执行摘要

- **日期**: 2026-05-26
- **ELO 数据**: May 24, 2026 (eloratings.net)，与上次仅差 1 天，无需刷新
- **ELO 队名匹配**: GROUPS 已使用规范名（Czech Republic, Bosnia and Herzegovina, DR Congo），48/48 匹配通过
- **伤病更新**: 7→10 队，15 名球员
- **元数据更新**: 20→36 队（75% 覆盖率）
- **预测结果**: 阿根廷 38.1%, 西班牙 33.7%, 法国 22.0%
- **最大变化**: 英格兰从 2.3%→0.2%（Foden/Palmer/TAA OUT）

## 伤病数据变更详情

### 新增
| 球队 | Penalty | 球员 | 来源 |
|------|---------|------|------|
| England | -90 | Foden(-40), Palmer(-30), TAA(-20) | BBC: "Foden, Palmer, Alexander-Arnold to miss World Cup" |
| Ghana | -20 | Kudus(DOUBTFUL) | Yahoo/BBC: quad since Jan |
| Argentina | -15 | Romero(DOUBTFUL) | Yahoo/BBC: knee April |
| Canada | -10 | Davies(DOUBTFUL) | Yahoo/BBC: recurring muscle |

### 更新
| 球队 | 旧 Penalty | 新 Penalty | 变更 |
|------|-----------|-----------|------|
| Brazil | -60 | -80 | Estevao DOUBTFUL→OUT (-10→-30) |
| Germany | -35 | -45 | Gnabry DOUBTFUL→OUT (-15→-30), ter Stegen -20→-15 |
| Japan | -25 | -50 | Mitoma 新增 OUT(-30), Minamino -10→-5 |
| Spain | -15 | -30 | Merino 新增 DOUBTFUL(-15) |

### 移除
| 球队 | 旧 Penalty | 原因 |
|------|-----------|------|
| Egypt | -10 | Salah FIT，确认入大名单 |

## 预测对比 (v2.3 vs v2.4)

| 球队 | v2.3 (May 21) | v2.4 (May 26) | 变化 |
|------|:---:|:---:|------|
| Argentina | 41.6% | 38.1% | -3.5% (Romero DOUBTFUL) |
| Spain | 32.2% | 33.7% | +1.5% |
| France | 18.9% | 22.0% | +3.1% |
| England | 2.3% | **0.2%** | **-91%** 🚨 |
| Portugal | 1.9% | 2.3% | +0.4% |
| Colombia | 1.2% | 2.2% | +1.0% |
| Brazil | 0.1% | 0.1% | 持平 |

## 测试失败 (7/66)

全部因 v2.3 参数变更后测试断言未同步：
- 4x upset probability 期望 0.18→应更新为 0.22
- 1x host_advantage USA tag 逻辑
- 1x ELO range 下限 1600→应调至 1400
- 1x Haiti adjustment 在新冷门模型下无法触发

## 6 月 1 日前的待办

1. 修复 7 个测试失败
2. 报告模板去硬编码
3. 补充剩余 12 队元数据
4. 根据最终大名单（Jun 1 deadline）做最后一次伤病刷新
