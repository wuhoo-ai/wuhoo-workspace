# 2026-06-09 全策略回测大排名

12个月 Walk-forward，三市场各策略对比。

## US Market (S&P 500, 505 stocks)

| Strategy              | CumRet% | Sharpe | WinRate | 信号/月 | 评价 |
|-----------------------|---------|--------|---------|---------|------|
| 🥇 Dual Momentum       | +99.65  | 1.253  | 83.3%   | 12/12   | 全策略最佳，SMA200过滤天然风控 |
| 🥈 Trend Momentum      | +83.30  | 0.848  | 83.3%   | 12/12   | 牛市动量强劲 |
| 🥉 Adaptive            | +45.14  | 0.673  | 66.7%   | 12/12   | 2月BEAR空仓避险 |
|    Contrarian          | +19.45  | 1.011  | 91.7%   | 12/12   | 稳健但收益低 |
|    Bollinger MR        | +9.00   | 0.401  | 60.0%   | 10/12   | 仅震荡期有效 |

**Dual Momentum 关键选股**：PLTR, HOOD, APP, SNDK, LITE — 持续出现，2025-2026最强趋势股。

## CN Market (中证1000, ~1000 stocks)

| Strategy              | CumRet% | Sharpe | WinRate | 评价 |
|-----------------------|---------|--------|---------|------|
| 🥇 Contrarian          | +14.34  | 0.196  | 66.7%   | CN最佳，超跌反弹有效 |
|    Small-cap Reversal  | +0.51   | 0.029  | 50.0%   | 纯市值+动量不够 |
|    Trend Momentum      | -2.70   | 0.016  | 50.0%   | A股追高被套 |
|    Adaptive (修复后)   | 需回测  | —      | —       | breadth-mask修复后待验证 |
|    Bollinger MR        | -18.75  | -0.586 | 20.0%   | 超卖继续跌 |

## HK Market (Top 500, 601 stocks)

| Strategy              | CumRet% | Sharpe | WinRate | 评价 |
|-----------------------|---------|--------|---------|------|
| 🥇 Trend Momentum      | +9.60   | 0.145  | 41.7%   | 略优但不可靠 |
|    Contrarian          | +0.50   | 0.030  | 50.0%   | 基本失效 |
|    Adaptive            | +0.42   | 0.034  | 25.0%   | 空仓避了部分损失 |
|    Large Momentum      | —       | —      | —       | 12/12月零信号 |

## 推荐部署

```
US:  Dual Momentum 主力 (100%) + Bollinger 辅助 (震荡期)
CN:  超跌反弹 主力 (80%)
HK:  动量 (减仓至50%) + 等待大盘动量修复
```
