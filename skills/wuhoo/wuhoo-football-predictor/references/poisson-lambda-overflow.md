# Poisson λ 溢出与概率颠倒 — 诊断与修复

> 版本: v5.6.1 | 日期: 2026-06-28
> 触发: Argentina vs Cape Verde 推演概率颠倒（强者 1.9% vs 弱者 98.1%）

## 症状

全量推演中 Argentina 2399 vs Cape Verde 1782（Δ=617），结果显示:
- Argentina R16 晋级率 26.7%（应为 ~90%+）
- Argentina 冠军率 1.9%

## 根因

`bracket_simulator.py` 的 Poisson λ 公式:

```python
lam_a = 1.45 * 10 ** (elo_diff / 500)  # 617/500 = 1.234 → 10^1.234 = 17.1
# lam_a = 1.45 * 17.1 = 24.85  ← 荒谬
```

λ=24.85 表示 Argentina 预期进球 25 个——不合理。

更致命的是，后续求和:

```python
for i in range(12):  # 只求和到 11 球
    pi_a = Poisson(i; 24.85)  # P(i<=11) ≈ 0.2%
```

λ=24.85 的分布集中在 20-30 球，而求和只到 11 球——**99.8% 的概率质量被截断**。剩余 0.2% 的质量中大部分是 Cape Verde 的进球（λ=0.2），所以 Cape Verde "胜率"极高。

```python
# 验证
import math
lam = 24.85
cdf = sum(lam**i * math.exp(-lam) / math.factorial(i) for i in range(12))
# cdf ≈ 0.002 → 只有 0.2% 概率被计算，99.8% 丢失
```

## 修复: λ 上限

```python
MAX_LAM = 4.0
lam_a = max(0.2, min(MAX_LAM, 1.45 * 10 ** (elo_diff / 500)))
```

### 合理性

- λ=4.0 对应 ELO 差 ≈ 220
- 预期进球 4.0 的球队 ≈ 80% 胜率
- 更大的 ELO 差 → 概率已接近饱和，不需要 λ>4.0
- P(≤11; λ=4.0) = 99.9% → 分布完整

### 对比

| 对阵 | ELO差 | 旧λ | 新λ | 旧P(胜) | 新P(胜) |
|------|-------|-----|-----|---------|---------|
| Argentina vs Cape Verde | 617 | 24.85 | 4.0 | 0.2% | 91.2% |
| France vs Sweden | 567 | 19.73 | 4.0 | 0.5% | 91.2% |
| Colombia vs Ghana | 219 | 3.99 | 3.99 | 87.8% | 87.8% |

Colombia vs Ghana 不受影响（ELO差在 λ 上限内），修复仅影响大 ELO 差场景。

## 实现位置

`scripts/bracket_simulator.py` `simulate_match()`:
```python
MAX_LAM = 4.0
lam_a = max(0.2, min(MAX_LAM, base_lam * 10 ** (elo_diff / 500)))
lam_b = max(0.2, min(MAX_LAM, base_lam * 10 ** (-elo_diff / 500)))
```

## 相关陷阱

- `wc2026_predict.py` 的 λ 上限为 3.0（小组赛），bracket_simulator 用 4.0（淘汰赛稍高因为KBC会进一步抑制）
- 求和范围 0-11 对 λ≤4.0 覆盖 99.9%+
- 如果未来放宽 λ 上限，需同步扩大求和范围
