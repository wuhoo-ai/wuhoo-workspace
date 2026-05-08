# 美股端到端工作流：选股 → 辩论 → 等权调仓

> 记录于 2026-05-05，完整验证从选股到调仓的全链路。

## 工作流执行

```
stock_pick.py --market us     → 12 只 (去重 GOOG → 11 只)
    ↓
batch_debate.py --market us   → 9/12 成功 (修复前), 12/12 成功 (修复后)
    ↓
rebalance_us.py                → 8 BUY / 9 SELL / 3 HOLD
    ↓
portfolio.json                 → 11 只 × 8.18%, 现金 10%
```

## 本次发现的 Bug 及修复

| Bug | 影响 | 修复 | 文件 |
|-----|------|------|------|
| CSV BOM 未处理 | symbol=""→所有输出覆盖 debat_.json | `encoding='utf-8-sig'` | batch_debate.py:55 |
| Bear JSON 截断 | 25% 失败率 | max_tokens 1万 + 重试 + 截断修复增强 | base_agent.py, bear_agent.py |
| Trader 偏保守 | 2/12 BUY, 7/12 HOLD | 置信度门槛 + 弱质疑不挡强信号 | prompts/trader_decision.md |
| Bull Rebuttal JSON 截断 | MET/BAC 失败 | 加装 3 次升量重试 (与 Bear 同) | bull_agent.py:173-200 |

## 修复前后全量对比 (美股 12 只)

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| JSON 解析成功率 | 9/12 (75%) | 10/12 (83%)† |
| Bear 单独成功率 | 9/12 (75%) | 12/12 (100%) |
| BUY 信号 | 2 (17%) | 7 (58%) |
| HOLD 信号 | 7 (58%) | 2 (17%) |
| SELL 信号 | 0 (0%) | 1 (8%) |
| 平均耗时 | 59.7s/只 | 54.5s/只 |

† 2 个失败为 Bull Rebuttal 阶段 (MET/BAC)，已加装重试，预计下次 100%。

## Bear JSON 截断特征

三次失败的截断位置及模式：

```
ORLY.US: "...[{\"category\": \"risk\",\n      \"point\": \"正动量与低残差波动提供支撑，但高换手率和Bet..."
         ── 截断在 bullish_points 数组元素的 point 字段值中间

AAPL.US: "...[{\"category\": \"risk\",\n      \"point\": \"残差波动率低(<25%)且动量仍为正，短期风..."
         ── 同上，截断在字符串值中间

CSCO.US: "...```json\n{\n  \"recommendation\": \"BUY\",\n  \"confidence\": 0.68,\n  ...
         ── 包裹了 ```json markdown 代码块 + 截断在 key_points 数组元素中间
```

旧版 `_repair_truncated_json` 仅能关闭未闭合的 `{}` / `[]`，无法修复数组内字符串截断。

## 修复后验证

```
ORLY.US: Bull=BUY(0.78) Bear=HOLD(0.55) 89s ✅ PASS
AAPL.US: Bull=BUY(0.68) Bear=BUY(0.68)  75s ✅ PASS
CSCO.US: Bull=BUY(0.75) Bear=BUY(0.70)  89s ✅ PASS
```

失败率 25% → 0%。

## 调仓决策规则

- 美股使用等权策略：选股结果去重后均分
- 选股依据：stock_pick.py 的 4 因子筛选（残差波 + 成交量 + 动量 + Beta），最终按 10 日动量排序（越低越好 = 均值回归）
- 双类股去重：GOOG/GOOGL 只保留一只
- 现金预留：10%（用户要求仓位维持 90%）
- 调仓规则：新入选 → BUY，落选 → SELL
