#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速展示辩论详情"""

import sys
import json
from datetime import datetime
sys.path.insert(0, '/home/admin/.openclaw/workspace/agents/debate')

from adapters.data_aggregator import DataAggregator
from protocols.debate_protocol import DebateProtocol
from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent
from agents.risk_agent import RiskAgent

symbol = "301029.SZ"
name = "怡合达"

print("="*70)
print(f"🎯 多空辩论详情：{symbol} - {name}")
print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

# 加载数据
aggregator = DataAggregator()
data = aggregator.get_all_data(symbol, name)

# 初始化 Agent
protocol = DebateProtocol(data_dir="/home/admin/.openclaw/workspace/agents/debate/data")
bull = BullAgent()
bear = BearAgent()
trader = TraderAgent()
risk = RiskAgent()

protocol.start_debate(symbol)

# Bull 分析
print("\n" + "="*70)
print("🐂 Bull Agent (多头分析师)")
print("="*70)
bull_view = bull.analyze(
    symbol=symbol,
    factor_data=data.get("factor_data"),
    technical_data=data.get("technical_data"),
    sentiment_data=data.get("sentiment_data"),
    fundamental_data=data.get("fundamental_data")
)
protocol.submit_bull_view(bull_view)

print(f"推荐方向：【BUY】")
print(f"置信度：{bull_view.get('confidence', 0):.2f}")
print(f"关键理由:")
for i, p in enumerate(bull_view.get('key_points', [])[:5], 1):
    print(f"  {i}. {p}")

# Bear 分析
print("\n" + "="*70)
print("🐻 Bear Agent (空头分析师)")
print("="*70)
bear_view = bear.analyze(
    symbol=symbol,
    factor_data=data.get("factor_data"),
    technical_data=data.get("technical_data"),
    sentiment_data=data.get("sentiment_data"),
    fundamental_data=data.get("fundamental_data"),
    bull_view=bull_view
)
protocol.submit_bear_view(bear_view)

print(f"推荐方向：【SELL】")
print(f"置信度：{bear_view.get('confidence', 0):.2f}")
print(f"关键理由:")
for i, p in enumerate(bear_view.get('key_points', [])[:5], 1):
    print(f"  {i}. {p}")
print(f"反驳观点:")
for i, r in enumerate(bear_view.get('rebuttals', [])[:3], 1):
    print(f"  {i}. {r}")

# 辩论分析
print("\n" + "="*70)
print("📊 辩论分析")
print("="*70)
analysis = protocol.analyze_debate()
print(f"共识点：{len(analysis.get('consensus', []))} 个")
for p in analysis.get('consensus', [])[:3]:
    print(f"  • {p}")
print(f"分歧点：{len(analysis.get('disagreements', []))} 个")
for p in analysis.get('disagreements', [])[:3]:
    print(f"  • {p}")

# Trader 决策
print("\n" + "="*70)
print("💼 Trader Agent (交易决策)")
print("="*70)
trader_decision = trader.make_decision(
    symbol=symbol,
    bull_view=bull_view,
    bear_view=bear_view,
    consensus_points=analysis.get('consensus', []),
    disagreement_points=analysis.get('disagreements', [])
)
print(f"最终决策：【{trader_decision.get('decision', 'N/A')}】")
print(f"置信度：{trader_decision.get('confidence', 0):.2f}")
print(f"建议仓位：{trader_decision.get('position_size', 0):.1%}")

# Risk 审核
print("\n" + "="*70)
print("🛡️ Risk Agent (风控审核)")
print("="*70)
risk_review = risk.review(
    symbol=symbol,
    trader_decision=trader_decision,
    current_position={"cash": 100000, "positions": {}}
)
print(f"风险等级：{risk_review.get('risk_level', 'N/A')}")
print(f"风险评分：{risk_review.get('risk_score', 0)}/100")
print(f"审核结果：【{risk_review.get('approval', 'N/A')}】")

# 最终结果
print("\n" + "="*70)
print("📋 最终结果汇总")
print("="*70)
print(f"股票：{name} ({symbol})")
print(f"Bull: BUY (置信度 {bull_view.get('confidence', 0):.2f})")
print(f"Bear: SELL (置信度 {bear_view.get('confidence', 0):.2f})")
print(f"Trader: {trader_decision.get('decision', 'N/A')} (置信度 {trader_decision.get('confidence', 0):.2f})")
print(f"Risk: {risk_review.get('approval', 'N/A')}")
print(f"最终行动：{'✅ 执行' if risk_review.get('approval') == 'APPROVED' else '⏸️ 暂缓'}")
print("="*70)

# 保存记录
record = {
    "symbol": symbol,
    "name": name,
    "timestamp": datetime.now().isoformat(),
    "bull_confidence": bull_view.get('confidence', 0),
    "bear_confidence": bear_view.get('confidence', 0),
    "trader_decision": trader_decision.get('decision', 'N/A'),
    "trader_confidence": trader_decision.get('confidence', 0),
    "risk_approval": risk_review.get('approval', 'N/A'),
    "risk_score": risk_review.get('risk_score', 0)
}
output_path = f"/home/admin/.openclaw/workspace/agents/debate/data/debate_detail_{symbol.replace('.', '')}.json"
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(record, f, ensure_ascii=False, indent=2)
print(f"\n💾 已保存至：{output_path}")
