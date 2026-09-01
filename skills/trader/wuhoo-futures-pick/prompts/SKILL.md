---
name: wuhoo-futures-debate
description: 期货多空辩论 — 复用 wuhoo-debate agent 框架，4 角色（Bull/Bear/Trader/Risk）期货专用 prompt，DeepSeek v4-pro API
version: 0.1.0
category: wuhoo
tags: [wuhoo, futures, debate]
---
# wuhoo-futures-debate

## 辩论流程
Bull(技术面多头) → Bear(风险/空头) → Trader(交易决策) → Risk(风控审核)

## 使用
```bash
cd ~/wuhoo-workspace/skills/trader/wuhoo-futures-pick
$VENV futures_debate.py --date 2026-05-08                  # 批量辩论
$VENV futures_debate.py --date 2026-05-08 --code US.MNQmain # 单品种
```

## 期货 vs 股票 prompt 差异
- 无 PE/PB/ROE 基本面 → 技术面主导
- 强调杠杆风险、合约到期、隔夜跳空
- 输出包含仓位百分比和保证金约束

## 输出
`~/wuhoo-workspace/data/futures/debate/{date}/debate_{code}.json`
