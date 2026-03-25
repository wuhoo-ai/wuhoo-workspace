#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
展示单只股票的详细辩论过程
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/admin/.openclaw/workspace/agents/debate')

from adapters.data_aggregator import DataAggregator
from protocols.debate_protocol import DebateProtocol
from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent
from agents.risk_agent import RiskAgent

def show_debate_detail(symbol: str, name: str):
    """执行并展示详细辩论过程"""
    
    print("="*70)
    print(f"🎯 多空辩论详情：{symbol} - {name}")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 加载数据
    print("\n📊 加载数据...")
    aggregator = DataAggregator()
    data = aggregator.get_all_data(symbol, name)
    
    print(f"   因子数据：{'✓' if data.get('factor_data') else '✗'}")
    print(f"   技术数据：{'✓' if data.get('technical_data') else '✗'}")
    print(f"   舆情数据：{'✓' if data.get('sentiment_data') else '✗'}")
    print(f"   基本面数据：{'✓' if data.get('fundamental_data') else '✗'}")
    
    # 初始化
    protocol = DebateProtocol(data_dir="/home/admin/.openclaw/workspace/agents/debate/data")
    bull = BullAgent()
    bear = BearAgent()
    trader = TraderAgent()
    risk = RiskAgent()
    
    # 开始辩论
    protocol.start_debate(symbol)
    
    # ========== Bull 分析 ==========
    print("\n" + "="*70)
    print("🐂 Bull Agent (多头分析师) 观点")
    print("="*70)
    
    bull_view = bull.analyze(
        symbol=symbol,
        factor_data=data.get("factor_data"),
        technical_data=data.get("technical_data"),
        sentiment_data=data.get("sentiment_data"),
        fundamental_data=data.get("fundamental_data")
    )
    
    protocol.submit_bull_view(bull_view)
    
    print(f"\n推荐方向：【{bull_view.get('recommendation', 'N/A')}】")
    print(f"置信度：{bull_view.get('confidence', 0):.2f}")
    print(f"\n关键理由:")
    for i, point in enumerate(bull_view.get('key_points', []), 1):
        print(f"   {i}. {point}")
    
    print(f"\n风险因素:")
    for i, risk in enumerate(bull_view.get('risks', []), 1):
        print(f"   {i}. {risk}")
    
    # ========== Bear 分析 ==========
    print("\n" + "="*70)
    print("🐻 Bear Agent (空头分析师) 观点")
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
    
    print(f"\n推荐方向：【{bear_view.get('recommendation', 'N/A')}】")
    print(f"置信度：{bear_view.get('confidence', 0):.2f}")
    print(f"\n关键理由:")
    for i, point in enumerate(bear_view.get('key_points', []), 1):
        print(f"   {i}. {point}")
    
    print(f"\n对 Bull 的反驳:")
    for i, rebuttal in enumerate(bear_view.get('rebuttals', []), 1):
        print(f"   {i}. {rebuttal}")
    
    # ========== 辩论分析 ==========
    print("\n" + "="*70)
    print("📊 辩论分析")
    print("="*70)
    
    analysis = protocol.analyze_debate()
    
    print(f"\n共识点 ({len(analysis.get('consensus', []))} 个):")
    for i, point in enumerate(analysis.get('consensus', []), 1):
        print(f"   {i}. {point}")
    
    print(f"\n分歧点 ({len(analysis.get('disagreements', []))} 个):")
    for i, point in enumerate(analysis.get('disagreements', []), 1):
        print(f"   {i}. {point}")
    
    print(f"\n关键争议:")
    for i, point in enumerate(analysis.get('key_contentions', []), 1):
        print(f"   {i}. {point}")
    
    # ========== Trader 决策 ==========
    print("\n" + "="*70)
    print("💼 Trader Agent (交易决策) 决策")
    print("="*70)
    
    trader_decision = trader.make_decision(
        symbol=symbol,
        bull_view=bull_view,
        bear_view=bear_view,
        consensus_points=analysis.get('consensus', []),
        disagreement_points=analysis.get('disagreements', [])
    )
    
    print(f"\n最终决策：【{trader_decision.get('decision', 'N/A')}】")
    print(f"置信度：{trader_decision.get('confidence', 0):.2f}")
    print(f"建议仓位：{trader_decision.get('position_size', 0):.1%}")
    
    print(f"\n决策理由:")
    for i, reason in enumerate(trader_decision.get('reasoning', []), 1):
        print(f"   {i}. {reason}")
    
    print(f"\n交易计划:")
    plan = trader_decision.get('action_plan', {})
    print(f"   入场价：{plan.get('entry_price', 'N/A')}")
    print(f"   目标价：{plan.get('target_price', 'N/A')}")
    print(f"   止损价：{plan.get('stop_loss', 'N/A')}")
    print(f"   持有期：{plan.get('holding_period', 'N/A')}")
    
    # ========== Risk 审核 ==========
    print("\n" + "="*70)
    print("🛡️ Risk Agent (风控) 审核")
    print("="*70)
    
    risk_assessment = risk.review(
        symbol=symbol,
        trader_decision=trader_decision,
        current_position={"cash": 100000, "positions": {}}
    )
    
    print(f"\n风险等级：{risk_assessment.get('risk_level', 'N/A')}")
    print(f"风险评分：{risk_assessment.get('risk_score', 0)}/100")
    print(f"审核结果：【{risk_assessment.get('approval', 'N/A')}】")
    
    print(f"\n风控意见:")
    for i, comment in enumerate(risk_assessment.get('comments', []), 1):
        print(f"   {i}. {comment}")
    
    print(f"\n风控要求:")
    for i, req in enumerate(risk_assessment.get('requirements', []), 1):
        print(f"   {i}. {req}")
    
    # ========== 最终结果 ==========
    print("\n" + "="*70)
    print("📋 最终结果")
    print("="*70)
    
    final_action = "执行" if risk_assessment.get('approval') == 'APPROVED' else "暂缓"
    print(f"\n最终行动：【{final_action}】")
    print(f"决策：{trader_decision.get('decision', 'N/A')}")
    print(f"仓位：{trader_decision.get('position_size', 0):.1%}")
    
    # 保存记录
    record = {
        "symbol": symbol,
        "name": name,
        "timestamp": datetime.now().isoformat(),
        "bull_view": bull_view,
        "bear_view": bear_view,
        "debate_analysis": analysis,
        "trader_decision": trader_decision,
        "risk_assessment": risk_assessment,
        "final_action": final_action
    }
    
    output_path = f"/home/admin/.openclaw/workspace/agents/debate/data/debate_detail_{symbol.replace('.', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 详细记录已保存至：{output_path}")
    print("="*70)
    
    return record

if __name__ == "__main__":
    show_debate_detail("301029.SZ", "怡合达")
