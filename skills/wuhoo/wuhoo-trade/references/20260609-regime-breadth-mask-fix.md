# 2026-06-09 Regime 广度 Mask 修复

## 问题

CN 市场自适应回测 -17.77%，比纯超跌 (+14.3%) 和纯动量 (-2.7%) 都差。

根因：market_regime.py 的 MA 位置维度权重 30%，当少数大票拉高指数但广度极差时（CN: 仅 27% 股票站上 MA50），composite 仍被推到正数 → 误判 BULL_TRENDING → 走趋势动量 → 追高被套。

## 具体案例 (CN 2026-01-15)

```
维度          得分    权重    贡献
MA位置        +2     30%    +0.60  ← 大票拉高，假阳性
广度          -2     25%    -0.50  ← 仅27%站上MA50
趋势强度      +2     20%    +0.40
波动率        +1     15%    +0.15
动量广度      -2     10%    -0.20
───────────────────────────────
Composite = +0.45 → 实际应 ≤ +0.40 (RANGING)
但未修复前 >= 0.5 即判 BULL_TRENDING
```

## 修复

在 `detect_regime()` 中，composite 加权计算后加入广度 mask：

```python
breadth_score = scores["breadth"]["score"]
if breadth_score <= -1:
    # Composite capped at +0.4 → can only be RANGING or BEAR, never BULL
    composite = min(composite, 0.4)
```

修复后 CN 正确判为 RANGING → oversold_rebound。

## 适用范围

此修复是通用模式，适用于所有市场。当 market breadth 显示大部分股票在 MA50 下方时，即使指数均线位置看牛，也不应走趋势动量策略。

核心原则：**广度比 MA 位置更真实反映市场参与度**。
