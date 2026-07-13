---
name: wuhoo-game-dev-balance-validate
description: "Use when you have numerical design tables (CSV in GDD) and need to validate balance — damage curves, economy flow, upgrade progression. Reads CSV data, runs Monte Carlo simulation, detects anomalies, and generates a balance report with suggested adjustments. Leverages the user's quantitative analysis background."
version: 1.0.0
author: Wuhoo
license: MIT
metadata:
  hermes:
    tags: [wuhoo, game-dev, balance, numerical-design, csv, simulation, monte-carlo]
    related_skills: [wuhoo-game-dev-gdd-to-tasks, data-science]
---

# Wuhoo Balance Validate

CSV 数值表 → 模拟 → 异常检测 → 平衡报告。

## When to Use

- 写完或修改了数值表 (weapons.csv / minerals.csv / upgrades.csv)
- 新增了物品/武器/升级, 不确定是否破坏平衡
- 里程碑前的平衡审查
- 用户说: "帮我看看这个数值有没有问题"

## Peak-Hour Guard

```python
# 蒙特卡洛模拟 token 消耗中等, 高峰时也可入队
guard_result = peak_hour_guard(
    task_type='balance-sim',
    task_id=f'balance_{timestamp}',
    task_context={'spec': '数值平衡模拟', 'params': {}, 'output': 'balance-report.md'}
)
if guard_result == 'deferred':
    return  # 入队, 低谷时自动跑并生成报告
```

> 如果用户说 "现在就分析" → 跳过 guard 直接执行

## Workflow

### Step 1: 读取数值表

从 GDD 同级目录读取 CSV:

```python
import csv, json

# 读取武器表
with open('GDD/balance/weapons.csv') as f:
    weapons = list(csv.DictReader(f))

# 读取矿物表
with open('GDD/balance/minerals.csv') as f:
    minerals = list(csv.DictReader(f))
```

### Step 2: 构建模拟模型

```python
def simulate_mining_session(level, pickaxe_level, stamina=100):
    """模拟一次采矿"""
    earnings = 0
    remaining_stamina = stamina

    # 根据深度层确定矿物分布
    mineral_pool = get_minerals_for_level(level)

    while remaining_stamina > 0:
        mineral = random.choices(mineral_pool, weights=get_weights(level))[0]
        cost = float(mineral['stamina_cost']) * stamina_multiplier(pickaxe_level)
        if remaining_stamina < cost:
            break
        remaining_stamina -= cost
        earnings += float(mineral['sell_price'])

    return {
        'earnings': earnings,
        'stamina_used': stamina - remaining_stamina,
        'efficiency': earnings / (stamina - remaining_stamina)  # $/体力
    }
```

### Step 3: 蒙特卡洛模拟

```python
# 每个深度层 × 每个镐等级, 跑 1000 次
results = {}
for level in [1, 2, 3]:
    for pick in [1, 2, 3]:
        sessions = [simulate_mining_session(level, pick) for _ in range(1000)]
        avg = sum(s['earnings'] for s in sessions) / len(sessions)
        results[f'L{level}_P{pick}'] = {
            'avg_earnings': avg,
            'min': min(s['earnings'] for s in sessions),
            'max': max(s['earnings'] for s in sessions),
            'efficiency': sum(s['efficiency'] for s in sessions) / len(sessions)
        }
```

### Step 4: 异常检测规则

| 检查 | 规则 | 严重级别 |
|------|------|---------|
| 效率倒挂 | 深层效率 < 浅层效率 | 🔴 ERROR |
| 升级无用 | Lv2 效率 ≤ Lv1 效率 | 🔴 ERROR |
| 悬崖跳变 | 相邻层效率差 > 3x | 🟡 WARNING |
| 付费墙 | 升级费用 > 该层 10 趟平均收入 | 🟡 WARNING |
| 死循环 | 需要 Lv2 镐才能挖的矿物在只有 Lv1 镐时才大量出现 | 🔴 ERROR |

### Step 5: 生成报告

```markdown
# 数值平衡分析报告 — 矿工守夜 v0.1

**分析日期**: 2026-07-13

## 采矿效率曲线 ($/体力)

| 深度 | 镐 Lv1 | 镐 Lv2 | 镐 Lv3 |
|------|--------|--------|--------|
| 浅层 | $4.82 | $6.15 | $7.30 |
| 中层 | $8.10 | $11.42 | $14.80 |
| 深层 | $11.50 | $18.20 | $30.05 |

## 升级回收周期 (趟数)

| 升级 | 费用 | Lv1 区域 | Lv2 区域 |
|------|------|---------|---------|
| 镐 Lv2 ($200) | $200 | 42 趟 (浅层) | 25 趟 (中层) |
| 镐 Lv3 ($800) | $800 | — | 54 趟 (中层) |
| 护甲 Lv2 ($150) | $150 | 32 趟 | 19 趟 |

## 异常检测

✅ 效率曲线单调递增 — 深层效率始终 > 浅层效率
✅ 升级回报为正 — 每次升级都有明确收益
⚠️ 镐 Lv3 回收周期偏长 (54 趟中层) — 建议费用从 $800 降到 $500-600
⚠️ 黑曜石 $300 售价可能导致运气方差过大 — 建议加 1-2 个中间值矿物

## 建议

1. 镐 Lv3: $800 → $600
2. 新增矿物 "月光石": 中层出现, $80, 体力消耗 6
3. 背包 Lv2 容量: 10→20 格, 但费用 $100 可能太低 → 建议 $300
```

## 执行

使用 `execute_code` 或 `terminal` 运行 Python 模拟脚本。脚本应当短小 (<100 行), 直接在 Hermes 中执行。

## Pitfalls

1. CSV 格式错误 — 确保列名一致, 数值列不含 $ 符号
2. 模拟次数不足 — 至少要 500+ 次才有统计意义
3. 忽略方差 — 只看平均值, 不看 min/max → 黑曜石 $300 但概率 5% 会造成巨大方差
4. 过度依赖模拟 — 模拟不能替代实际游玩。模拟通过 → 你亲自玩一遍验证手感

## Verification

- [ ] 所有 CSV 数值表都能正确解析
- [ ] 每个(深度×镐等级)组合至少 500 次模拟
- [ ] 异常检测规则全部覆盖
- [ ] 报告包含图表 (效率曲线 + 回收周期表)
- [ ] 每个 ⚠️ WARNING 都附了建议修改
