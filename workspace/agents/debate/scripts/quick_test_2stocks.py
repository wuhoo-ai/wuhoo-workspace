#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试 - 2 只股票验证流程"""

import json, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/admin/.openclaw/workspace/agents/debate')

from adapters.data_aggregator import DataAggregator
from protocols.debate_protocol import DebateProtocol
from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent
from agents.risk_agent import RiskAgent

# 只测试 2 只
TEST_STOCKS = [
    {"symbol": "301029.SZ", "name": "怡合达"},
    {"symbol": "600667.SH", "name": "太极实业"},
]

print("="*80)
print("🚀 多空辩论流程快速测试 (2 只股票)")
print("="*80)

aggregator = DataAggregator()
protocol = DebateProtocol(data_dir="/home/admin/.openclaw/workspace/agents/debate/data")
bull = BullAgent()
bear = BearAgent()
trader = TraderAgent()
risk = RiskAgent()

results = []

for i, stock in enumerate(TEST_STOCKS, 1):
    symbol = stock["symbol"]
    name = stock["name"]
    
    print(f"\n{'='*80}")
    print(f"📈 [{i}/2] {symbol} - {name}")
    print(f"{'='*80}")
    
    result = {"symbol": symbol, "name": name, "steps": [], "errors": []}
    
    # 步骤 1: 数据加载
    print("\n📊 步骤 1: 数据加载...")
    t0 = time.time()
    try:
        data = aggregator.get_all_data(symbol, name)
        protocol.start_debate(symbol)  # 开始辩论
        t1 = time.time() - t0
        result["steps"].append({"name": "数据加载", "duration": round(t1, 2), "status": "success"})
        print(f"   ✅ {t1:.2f}s | 舆情：{data.get('sentiment_data', {}).get('sentiment_score', 'N/A')}")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   ❌ {e}")
        continue
    
    # 步骤 2: Bull
    print("\n🐂 步骤 2: Bull Agent...")
    t0 = time.time()
    try:
        bull_view = bull.analyze(symbol=symbol, **{k: data.get(k) for k in ['factor_data', 'technical_data', 'sentiment_data', 'fundamental_data']})
        t1 = time.time() - t0
        protocol.submit_bull_view(bull_view)
        result["steps"].append({"name": "Bull", "duration": round(t1, 2), "output": {"rec": bull_view.get("recommendation"), "conf": bull_view.get("confidence", 0)}})
        print(f"   ✅ {t1:.2f}s | {bull_view.get('recommendation')} ({bull_view.get('confidence', 0):.2f})")
        print(f"   关键点：{bull_view.get('key_points', [])[:2]}")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   ❌ {e}")
        continue
    
    # 步骤 3: Bear
    print("\n🐻 步骤 3: Bear Agent...")
    t0 = time.time()
    try:
        bear_view = bear.analyze(symbol=symbol, **{k: data.get(k) for k in ['factor_data', 'technical_data', 'sentiment_data', 'fundamental_data']}, bull_view=bull_view)
        t1 = time.time() - t0
        protocol.submit_bear_view(bear_view)
        result["steps"].append({"name": "Bear", "duration": round(t1, 2), "output": {"rec": bear_view.get("recommendation"), "conf": bear_view.get("confidence", 0)}})
        print(f"   ✅ {t1:.2f}s | {bear_view.get('recommendation')} ({bear_view.get('confidence', 0):.2f})")
        print(f"   关键点：{bear_view.get('key_points', [])[:2]}")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   ❌ {e}")
        continue
    
    # 步骤 4: 辩论分析
    print("\n📊 步骤 4: 辩论分析...")
    t0 = time.time()
    try:
        analysis = protocol.analyze_debate()
        t1 = time.time() - t0
        result["steps"].append({"name": "辩论分析", "duration": round(t1, 2)})
        print(f"   ✅ {t1:.2f}s | 共识:{len(analysis.get('consensus', []))} 分歧:{len(analysis.get('disagreements', []))}")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   ❌ {e}")
        continue
    
    # 步骤 5: Trader
    print("\n💼 步骤 5: Trader Agent...")
    t0 = time.time()
    try:
        trader_decision = trader.make_decision(symbol=symbol, bull_view=bull_view, bear_view=bear_view, consensus_points=analysis.get('consensus', []), disagreement_points=analysis.get('disagreements', []))
        t1 = time.time() - t0
        result["steps"].append({"name": "Trader", "duration": round(t1, 2), "output": {"decision": trader_decision.get("decision"), "conf": trader_decision.get("confidence", 0)}})
        print(f"   ✅ {t1:.2f}s | {trader_decision.get('decision')} ({trader_decision.get('confidence', 0):.2f})")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   ❌ {e}")
        continue
    
    # 步骤 6: Risk
    print("\n🛡️ 步骤 6: Risk Agent...")
    t0 = time.time()
    try:
        risk_review = risk.review(symbol=symbol, trader_decision=trader_decision, current_position=None, market_data=data.get('technical_data', {}))
        t1 = time.time() - t0
        approval = risk_review.get("approval", False)  # 默认为 False
        result["steps"].append({"name": "Risk", "duration": round(t1, 2), "output": {"approval": approval, "score": risk_review.get("risk_score", 0), "recommendation": risk_review.get("recommendation", "N/A")}})
        print(f"   ✅ {t1:.2f}s | approval={approval} recommendation={risk_review.get('recommendation')} (风险:{risk_review.get('risk_score', 0)})")
    except Exception as e:
        result["errors"].append(str(e))
        risk_review = None
        approval = None
        print(f"   ❌ {e}")
    
    # 最终
    result["final"] = {"decision": trader_decision.get("decision"), "approval": approval}
    results.append(result)
    
    print(f"\n📋 最终：{trader_decision.get('decision')} | Risk: {risk_review.get('approval', 'N/A') if 'risk_review' in dir() else 'N/A'}")

# 汇总
print("\n" + "="*80)
print("📊 测试汇总")
print("="*80)
print(f"测试：{len(results)} 只股票")
for r in results:
    print(f"  {r['symbol']} {r['name']}: {r.get('final', {}).get('decision', 'ERROR')} | 错误:{len(r['errors'])}")
print("="*80)

# 保存
output = Path("/home/admin/.openclaw/workspace/agents/debate/data/quick_test_results.json")
with open(output, 'w', encoding='utf-8') as f:
    json.dump({"results": results, "timestamp": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
print(f"\n💾 结果已保存：{output}")
