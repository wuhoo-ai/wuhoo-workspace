#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多空辩论批量测试 - 对 Stock-Pick 选出的 10 只股票进行辩论测试
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/home/admin/.openclaw/workspace/agents/debate')

from adapters.data_aggregator import DataAggregator
from protocols.debate_protocol import DebateProtocol
from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent
from agents.risk_agent import RiskAgent

# Stock-Pick 选出的 10 只股票
STOCKS = [
    {"code": "002254.SZ", "name": "泰和新材"},
    {"code": "601858.SH", "name": "中国科传"},
    {"code": "600552.SH", "name": "凯盛科技"},
    {"code": "300232.SZ", "name": "洲明科技"},
    {"code": "688327.SH", "name": "云从科技-UW"},
    {"code": "301029.SZ", "name": "怡合达"},
    {"code": "600667.SH", "name": "太极实业"},
    {"code": "002745.SZ", "name": "木林森"},
    {"code": "600100.SH", "name": "同方股份"},
    {"code": "002815.SZ", "name": "崇达技术"},
]

def run_single_debate(stock, use_mock_data=True):
    """执行单只股票的多空辩论"""
    symbol = stock["code"]
    name = stock["name"]
    
    print(f"\n{'='*60}")
    print(f"🎯 辩论：{symbol} - {name}")
    print(f"{'='*60}")
    
    # 加载数据
    aggregator = DataAggregator()
    data = aggregator.get_all_data(symbol, name)
    
    # 初始化 Agent
    protocol = DebateProtocol(data_dir="/home/admin/.openclaw/workspace/agents/debate/data")
    bull = BullAgent()
    bear = BearAgent()
    trader = TraderAgent()
    risk = RiskAgent()
    
    # 开始辩论
    protocol.start_debate(symbol)
    
    # Bull 分析
    print("\n🐂 Bull Agent 分析中...")
    bull_view = bull.analyze(
        symbol=symbol,
        factor_data=data.get("factor_data"),
        technical_data=data.get("technical_data"),
        sentiment_data=data.get("sentiment_data"),
        fundamental_data=data.get("fundamental_data")
    )
    protocol.submit_bull_view(bull_view)
    print(f"   推荐：{bull_view.get('recommendation', 'N/A')}")
    print(f"   置信度：{bull_view.get('confidence', 0):.2f}")
    print(f"   关键理由：{bull_view.get('key_points', ['N/A'])[0] if bull_view.get('key_points') else 'N/A'}")
    
    # Bear 分析
    print("\n🐻 Bear Agent 分析中...")
    bear_view = bear.analyze(
        symbol=symbol,
        factor_data=data.get("factor_data"),
        technical_data=data.get("technical_data"),
        sentiment_data=data.get("sentiment_data"),
        fundamental_data=data.get("fundamental_data"),
        bull_view=bull_view
    )
    protocol.submit_bear_view(bear_view)
    print(f"   推荐：{bear_view.get('recommendation', 'N/A')}")
    print(f"   置信度：{bear_view.get('confidence', 0):.2f}")
    print(f"   关键理由：{bear_view.get('key_points', ['N/A'])[0] if bear_view.get('key_points') else 'N/A'}")
    
    # 分析辩论
    print("\n📊 辩论分析...")
    analysis = protocol.analyze_debate()
    print(f"   共识点：{len(analysis.get('consensus', []))} 个")
    print(f"   分歧点：{len(analysis.get('disagreements', []))} 个")
    
    # Trader 决策
    print("\n💼 Trader Agent 决策...")
    trader_decision = trader.make_decision(
        symbol=symbol,
        bull_view=bull_view,
        bear_view=bear_view,
        consensus_points=analysis.get('consensus', []),
        disagreement_points=analysis.get('disagreements', [])
    )
    print(f"   决策：{trader_decision.get('decision', 'N/A')}")
    print(f"   仓位：{trader_decision.get('position_size', 0):.1%}")
    print(f"   理由：{trader_decision.get('rationale', 'N/A')[:50]}...")
    
    # Risk 审核
    print("\n🛡️ Risk Agent 审核...")
    risk_assessment = risk.assess(
        symbol=symbol,
        trader_decision=trader_decision,
        market_data=data.get("technical_data", {})
    )
    risk_level = risk_assessment.get('risk_level', 'N/A')
    approved = risk_assessment.get('approved', False)
    print(f"   风险等级：{risk_level}")
    print(f"   审批结果：{'✅ 通过' if approved else '❌ 拒绝'}")
    if not approved:
        print(f"   拒绝原因：{risk_assessment.get('rejection_reason', 'N/A')}")
    
    # 汇总结果
    result = {
        "symbol": symbol,
        "name": name,
        "timestamp": datetime.now().isoformat(),
        "bull_view": {
            "recommendation": bull_view.get("recommendation"),
            "confidence": bull_view.get("confidence", 0),
            "key_points": bull_view.get("key_points", [])
        },
        "bear_view": {
            "recommendation": bear_view.get("recommendation"),
            "confidence": bear_view.get("confidence", 0),
            "key_points": bear_view.get("key_points", [])
        },
        "debate_analysis": {
            "consensus_count": len(analysis.get("consensus", [])),
            "disagreement_count": len(analysis.get("disagreements", []))
        },
        "trader_decision": {
            "decision": trader_decision.get("decision"),
            "position_size": trader_decision.get("position_size", 0),
            "rationale": trader_decision.get("ration", "")
        },
        "risk_assessment": {
            "risk_level": risk_level,
            "approved": approved,
            "rejection_reason": risk_assessment.get("rejection_reason")
        }
    }
    
    return result


def main():
    print("="*60)
    print("🐂🐻 多空辩论批量测试")
    print("股票池：Stock-Pick 2026-03-18 Top 10")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = []
    
    for i, stock in enumerate(STOCKS, 1):
        print(f"\n[{i}/{len(STOCKS)}]")
        try:
            result = run_single_debate(stock, use_mock_data=True)
            results.append(result)
        except Exception as e:
            print(f"   ❌ 错误：{e}")
            results.append({
                "symbol": stock["code"],
                "name": stock["name"],
                "error": str(e)
            })
    
    # 保存结果
    output_dir = Path("/home/admin/.openclaw/workspace/agents/debate/data")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"debate_results_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_date": timestamp,
            "stock_pool": "Stock-Pick 2026-03-18 Top 10",
            "total_stocks": len(STOCKS),
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print("✅ 测试完成！")
    print(f"结果已保存：{output_file}")
    print(f"{'='*60}")
    
    # 汇总统计
    print("\n📊 汇总统计")
    print("-"*60)
    
    approved_count = sum(1 for r in results if r.get("risk_assessment", {}).get("approved", False))
    buy_count = sum(1 for r in results if r.get("trader_decision", {}).get("decision") == "BUY")
    hold_count = sum(1 for r in results if r.get("trader_decision", {}).get("decision") == "HOLD")
    sell_count = sum(1 for r in results if r.get("trader_decision", {}).get("decision") == "SELL")
    
    print(f"风控通过：{approved_count}/{len(results)} ({approved_count/len(results)*100:.1f}%)")
    print(f"买入信号：{buy_count} 只")
    print(f"持有观望：{hold_count} 只")
    print(f"卖出信号：{sell_count} 只")
    
    # 输出详细结果表
    print("\n📋 详细结果")
    print("-"*60)
    print(f"{'股票':<12} {'名称':<10} {'Bull':<8} {'Bear':<8} {'Trader':<8} {'风控':<6}")
    print("-"*60)
    
    for r in results:
        if "error" in r:
            print(f"{r['symbol']:<12} {r['name']:<10} {'错误':<8} {'错误':<8} {'错误':<8} {'错误':<6}")
        else:
            bull_rec = r.get("bull_view", {}).get("recommendation", "N/A")
            bear_rec = r.get("bear_view", {}).get("recommendation", "N/A")
            trader_rec = r.get("trader_decision", {}).get("decision", "N/A")
            risk_approved = "✅" if r.get("risk_assessment", {}).get("approved", False) else "❌"
            
            print(f"{r['symbol']:<12} {r['name']:<10} {bull_rec:<8} {bear_rec:<8} {trader_rec:<8} {risk_approved:<6}")
    
    print("-"*60)


if __name__ == "__main__":
    main()
