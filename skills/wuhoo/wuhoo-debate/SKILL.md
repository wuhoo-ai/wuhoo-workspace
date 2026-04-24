---
name: wuhoo-debate
description: 多空辩论分析模块。对个股进行多维度辩论分析，生成投资决策建议。
tags: ["wuhoo"]
category: wuhoo
metadata: { "hermes": { "requires": { "bins": ["python3.11"] } } }
---

# wuhoo-debate — 多空辩论分析

## 执行入口
`python3.11 run_debate.py --symbol 600519.SH --mode full`

## 模块结构
- agents/: 多空Agent实现
- adapters/: 数据适配器（akshare、RSS、趋势雷达等）
- prompts/: 辩论提示词模板
- protocols/: 辩论协议
- rules/: 风控规则

## ✅ 已修复问题 (2026-04-24)

### ✅ P0: RiskAgent 风控被绕过 — 已修复
- `workflow_c_multi_market.py` 的 `_debate_quick()` 方法已集成 `RiskAgent.review()`
- 构建完整的 `trader_decision` 结构（含 stop_loss/take_profit/position_size/rrr）
- 如果 RiskAgent 不可用，降级到简化版风控（检查波动率、涨幅、Beta）
- `trader_agent.py` 的 `quick_decision()` 方法已修正 RRR 计算：
  - 旧公式: `bull_upside / (bear_downside + 0.01)` （错误）
  - 新公式: `潜在收益 / 潜在损失` = `(止盈价-现价) / (现价-止损价)`
  - 测试验证: AAPL (目标120, 止损92) → RRR=2.5 ✅

## ⚠️ 待解决问题 (2026-04-24)

### P1: 辩论结果高度趋同
- Bull Agent 输出固定为 BUY (0.58-0.65)
- Bear Agent 输出固定为 SELL (0.55-0.62)
- 缺少去趋同机制，需要添加 `divergence_checker.py` 强制观点差异度≥0.15

### P1: 辩论脚本超时
- `run_debate.py --symbol XXX --mode full` 执行超过 300 秒被强制终止
- 可能原因：LLM 调用延迟、数据获取卡住、交互轮次过多
