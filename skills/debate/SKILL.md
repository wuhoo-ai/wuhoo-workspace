---
name: wuhoo-debate
description: 多空辩论分析模块。对个股进行多维度辩论分析，生成投资决策建议。
metadata: { "hermes": { "requires": { "bins": ["python3.11"] } } }
---

# wuhoo-debate — 多空辩论分析

## 执行入口
`python3.11 run_debate.py`

## 模块结构
- agents/: 多空Agent实现
- adapters/: 数据适配器（akshare、RSS、趋势雷达等）
- prompts/: 辩论提示词模板
- protocols/: 辩论协议
- rules/: 风控规则
