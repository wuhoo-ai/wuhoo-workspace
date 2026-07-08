# MD3 锁定出线 ELO 非对称降权 — 技术文档

> 版本: v5.6.1 | 日期: 2026-06-28
> 触发: 用户指出"轮换阵容都能大胜，上主力岂不是更厉害"

## 问题

小组赛 MD3（第三轮）出现大量已锁定出线球队大幅轮换的情形。传统 ELO 使用统一 K=60 处理所有比赛，导致：
- **轮换后输球**: 真实实力被低估（主力得到了休息，轮换阵容不代表全力）
- **轮换后赢球**: 真实实力被低估更多（板凳深度强，主力休息后更强）

对称降权（K=60→30 for all）解决了一半问题（输球不夸大），但制造了另一半问题（赢球被低估）。

## 方案: 非对称 K-factor

```python
# 伪代码
if team.locked_before_md3:
    if team.won:
        K = 60    # 全额: 轮换还能赢 = 实力被低估
    elif team.drew:
        K = 30    # 降权: 轮换平局不反映真实实力
    elif team.lost:
        K = 30    # 降权: 轮换输球不反映真实实力
```

### 判定标准

锁定出线条件（赛前）:
- 领先第 3 名 > 3 分，或
- 领先第 3 名 = 3 分且净胜球 > 5

### 2026 WC MD3 实际应用

| 球队 | MD3 结果 | K | 理由 |
|------|----------|---|------|
| France | 4-1 胜 Norway | 60 | 轮换还能大胜，板凳深度强 |
| Mexico | 3-0 胜 Czech | 60 | 轮换大胜 |
| Germany | 1-2 负 Ecuador | 30 | 轮换输球，不反映真实力 |
| Canada | 1-2 负 Switzerland | 30 | 同上 |
| Norway | 1-4 负 France | 30 | 同上 |
| Colombia | 0-0 平 Portugal | 30 | 双方均锁定，保守平局 |

### 实现位置

`scripts/update_elo_from_results.py`:
- `K_FACTOR_LOCKED_WIN = 60` (不降)
- `K_FACTOR_LOCKED_LOSE = 30` (50%降权)
- `compute_pre_md3_locked_teams()` — 赛前锁定判定
- `update_elo_from_match()` — K选择逻辑（基于实际比分，非预期值）

### 边界条件

- **挪威 vs 法国**: 双方均锁定。Norway 输→K=30，France 赢→K=60
- **Colombia vs Portugal**: Colombia 锁定，Portugal 未锁定。Colombia 平→K=30，Portugal K=60
- **Argentina**: 6pts 领先 3pts Austria(GD+5)，GD 不大于 5 → **未锁定**（数学上可被超越）→ K=60

## 验证

修复前 France ELO: 2309 (在 1-4 轮换后被低估)
修复后 France ELO: 2399 (与 Argentina 并列第一)

修复前 bracket_simulator: Argentina 1.9% → 修复后: 41.8%
