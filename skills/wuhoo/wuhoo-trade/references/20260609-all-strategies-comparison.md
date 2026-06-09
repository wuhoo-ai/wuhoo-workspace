# 2026-06-09 全策略回测大排名

## 三市场所有策略 Walk-Forward 12 月对比

```
Market │ Strategy              │ CumRet% │ Sharpe │ WinRate │ 信号/月 │ 适用
───────┼───────────────────────┼─────────┼────────┼─────────┼─────────┼──────
US     │ 🥇 Dual Momentum      │ +99.65  │ 1.253  │ 83.3%   │ 12/12   │ 主力
US     │ 🥈 Trend Momentum     │ +83.30  │ 0.848  │ 83.3%   │ 12/12   │ 主力
US     │ 🥉 Adaptive           │ +45.14  │ 0.673  │ 66.7%   │ 12/12   │ 辅助
US     │    Contrarian         │ +19.45  │ 1.011  │ 91.7%   │ 12/12   │ 震荡期
US     │    Bollinger MR       │ +9.00   │ 0.401  │ 60.0%   │ 10/12   │ 震荡期
───────┼───────────────────────┼─────────┼────────┼─────────┼─────────┼──────
CN     │ 🥇 Contrarian         │ +14.34  │ 0.196  │ 66.7%   │ 12/12   │ 主力
CN     │    Small-cap Reversal │ +0.51   │ 0.029  │ 50.0%   │ 12/12   │ 探索
CN     │    Trend Momentum     │ -2.70   │ 0.016  │ 50.0%   │ 12/12   │ ❌
CN     │    Bollinger MR       │ -18.75  │ -0.586 │ 20.0%   │ 10/12   │ ❌
CN     │    Adaptive           │ -17.77  │ -0.351 │ 41.7%   │ 12/12   │ ❌ (已修复)
───────┼───────────────────────┼─────────┼────────┼─────────┼─────────┼──────
HK     │    Trend Momentum     │ +9.60   │ 0.145  │ 41.7%   │ 12/12   │ 减仓
HK     │    Contrarian         │ +0.50   │ 0.030  │ 50.0%   │ 12/12   │ 减仓
HK     │    Adaptive           │ +0.42   │ 0.034  │ 25.0%   │ 12/12   │ 探索
HK     │    Large Momentum     │ —       │ —      │ —       │ 0/12    │ 待修复
```

## 策略详解

### Dual Momentum (US 🥇)
- **逻辑**: 12月相对动量排名前30% + 绝对动量过滤(价格 > SMA200)
- **参数**: top_n=10, hold=20d
- **典型持仓**: PLTR, HOOD, APP, SNDK, LITE — 过去12个月最强趋势股
- **为何有效**: SMA200 过滤天然内置熊市避险，相对动量确保持续选择最强标的
- **风险**: 趋势反转时可能大幅回撤

### Bollinger Mean Reversion
- **逻辑**: 触及布林下轨(2σ) + RSI<30 超卖确认
- **参数**: top_n=10, hold=10d
- **US**: +9.0% 稳健但信号稀疏 (10/12月)
- **CN**: -18.75% 完全失败 — 超卖后继续下跌(接飞刀)

### Small-cap Reversal (CN)
- **逻辑**: 最小市值30%(成交额代理) + 5日最大跌幅
- **参数**: top_n=10, hold=20d
- **CN**: +0.51% 基本平盘 — 需叠加基本面因子(ROE/营收增速)

### HK Large-cap Momentum
- **逻辑**: Top 30 市值 + 10日正动量
- **状态**: ❌ 无信号 — market_cap 数据中的代码与回测数据代码不匹配，需修复

## 推荐部署方案

```
US:  Dual Momentum 主力(100%) + Bollinger 震荡期辅助
CN:  超跌反弹 主力(80%) + 小市值反转 探索(20%)
HK:  动量(50%减仓) + 等待大盘动量修复
```

## Regime Breadth-Mask 修复 (2026-06-09)

**问题**: CN市场MA位置检测+2(被少数大盘股拉高)但广度-2(仅27%站上MA50)，composite仍被推至BULL区→错误启用趋势动量→追高被套。

**修复**: `market_regime.py` detect_regime() 新增广度遮罩 — 当 breadth_score ≤ -1 时 composite 强制 cap 到 +0.4（最多RANGING，永不到BULL）。

```python
# 在 composite 计算后立即插入
breadth_score = scores["breadth"]["score"]
if breadth_score <= -1:
    composite = min(composite, 0.4)  # cap at RANGING max
```
