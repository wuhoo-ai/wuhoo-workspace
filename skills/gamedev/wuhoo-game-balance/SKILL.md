---
name: wuhoo-game-balance
description: "Use to validate game balance via simulation."
version: 2.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo-game, balance, monte-carlo, economy,数值]
    related_skills: [wuhoo-game-plan, wuhoo-game-exec]
---

# wuhoo-game-balance — 数值平衡验证

> 改名自: balance-validate。内容基本不变。

## 触发条件

- GDD 中有数值表（CSV）需要验证
- 调整了伤害/经济/升级曲线后需要回归验证
- 用户问"这个数值合理吗"

## 流程

```
1. 读取 GDD 中的 CSV 数值表
2. Monte Carlo 模拟（1000+ 次）
3. 检测异常（曲线断裂、经济通胀、难度悬崖）
4. 输出平衡报告 + 调整建议
```

## 检查维度

| 维度 | 检查内容 |
|------|---------|
| 伤害曲线 | DPS 递增是否平滑，有无断崖 |
| 经济流 | 金币收入 vs 支出，是否通胀/通缩 |
| 升级曲线 | 升级成本递增是否合理 |
| 难度曲线 | 敌人 HP/伤害 vs 玩家能力 |
| 掉落率 | 期望获取时间是否合理 |

## 输出格式

```
═══ 平衡报告 ═══
模拟次数: 1000
通关率: 73% (目标 60-80%) ✅
平均通关时间: 23min (目标 20-30min) ✅
经济通胀: Night 5 后金币溢出 ⚠️
建议: Night 5+ 增加建造消耗或降低掉落率
```
