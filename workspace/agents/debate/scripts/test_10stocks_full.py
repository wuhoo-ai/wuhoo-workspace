#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""10 只股票完整辩论流程测试 - 修复 Risk Agent 后"""

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

# 10 只测试股票
TEST_STOCKS = [
    # Batch 3 (5 只)
    {"symbol": "301029.SZ", "name": "怡合达"},
    {"symbol": "600667.SH", "name": "太极实业"},
    {"symbol": "002745.SZ", "name": "木林森"},
    {"symbol": "600100.SH", "name": "同方股份"},
    {"symbol": "002815.SZ", "name": "崇达技术"},
    # Batch 2 (4 只)
    {"symbol": "601858.SH", "name": "中国科传"},
    {"symbol": "600552.SH", "name": "凯盛科技"},
    {"symbol": "300232.SZ", "name": "洲明科技"},
    {"symbol": "688327.SH", "name": "云从科技-UW"},
    # 额外 1 只
    {"symbol": "002254.SZ", "name": "泰和新材"},
]

print("="*80)
print("🚀 多空辩论系统 - 10 只股票完整流程测试")
print("="*80)
print(f"测试股票数：{len(TEST_STOCKS)}")
print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

aggregator = DataAggregator()
protocol = DebateProtocol(data_dir="/home/admin/.openclaw/workspace/agents/debate/data")
bull = BullAgent()
bear = BearAgent()
trader = TraderAgent()
risk = RiskAgent()

results = []
start_time = time.time()

for i, stock in enumerate(TEST_STOCKS, 1):
    symbol = stock["symbol"]
    name = stock["name"]
    
    print(f"\n{'='*80}")
    print(f"📈 [{i}/10] {symbol} - {name}")
    print(f"{'='*80}")
    
    result = {"symbol": symbol, "name": name, "steps": [], "errors": []}
    
    # 步骤 1: 数据加载
    print("\n📊 步骤 1: 数据加载...")
    t0 = time.time()
    try:
        data = aggregator.get_all_data(symbol, name)
        protocol.start_debate(symbol)
        t1 = time.time() - t0
        result["steps"].append({"name": "数据加载", "duration": round(t1, 2), "status": "success"})
        sentiment = data.get('sentiment_data', {}).get('sentiment_score', 'N/A')
        print(f"   ✅ {t1:.2f}s | 舆情评分：{sentiment}")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   ❌ {e}")
        results.append(result)
        continue
    
    # 步骤 2: Bull
    print("\n🐂 步骤 2: Bull Agent...")
    t0 = time.time()
    try:
        bull_view = bull.analyze(symbol=symbol, **{k: data.get(k) for k in ['factor_data', 'technical_data', 'sentiment_data', 'fundamental_data']})
        t1 = time.time() - t0
        protocol.submit_bull_view(bull_view)
        result["steps"].append({"name": "Bull", "duration": round(t1, 2), "output": {"rec": bull_view.get("recommendation"), "conf": round(bull_view.get("confidence", 0), 2)}})
        print(f"   ✅ {t1:.2f}s | {bull_view.get('recommendation')} ({bull_view.get('confidence', 0):.2f})")
        kps = bull_view.get('key_points', [])
        if kps: print(f"   关键点：{kps[:2]}")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   ❌ {e}")
        results.append(result)
        continue
    
    # 步骤 3: Bear
    print("\n🐻 步骤 3: Bear Agent...")
    t0 = time.time()
    try:
        bear_view = bear.analyze(symbol=symbol, **{k: data.get(k) for k in ['factor_data', 'technical_data', 'sentiment_data', 'fundamental_data']}, bull_view=bull_view)
        t1 = time.time() - t0
        protocol.submit_bear_view(bear_view)
        result["steps"].append({"name": "Bear", "duration": round(t1, 2), "output": {"rec": bear_view.get("recommendation"), "conf": round(bear_view.get("confidence", 0), 2)}})
        print(f"   ✅ {t1:.2f}s | {bear_view.get('recommendation')} ({bear_view.get('confidence', 0):.2f})")
        kps = bear_view.get('key_points', [])
        if kps: print(f"   关键点：{kps[:2]}")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   ❌ {e}")
        results.append(result)
        continue
    
    # 步骤 4: 辩论分析
    print("\n📊 步骤 4: 辩论分析...")
    t0 = time.time()
    try:
        analysis = protocol.analyze_debate()
        t1 = time.time() - t0
        result["steps"].append({"name": "辩论分析", "duration": round(t1, 2), "output": {"consensus": len(analysis.get('consensus', [])), "disagreements": len(analysis.get('disagreements', []))}})
        print(f"   ✅ {t1:.2f}s | 共识:{len(analysis.get('consensus', []))} 分歧:{len(analysis.get('disagreements', []))}")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   ❌ {e}")
        results.append(result)
        continue
    
    # 步骤 5: Trader
    print("\n💼 步骤 5: Trader Agent...")
    t0 = time.time()
    try:
        trader_decision = trader.make_decision(symbol=symbol, bull_view=bull_view, bear_view=bear_view, consensus_points=analysis.get('consensus', []), disagreement_points=analysis.get('disagreements', []))
        t1 = time.time() - t0
        result["steps"].append({"name": "Trader", "duration": round(t1, 2), "output": {"decision": trader_decision.get("decision"), "conf": round(trader_decision.get("confidence", 0), 2)}})
        print(f"   ✅ {t1:.2f}s | {trader_decision.get('decision')} ({trader_decision.get('confidence', 0):.2f})")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"   ❌ {e}")
        results.append(result)
        continue
    
    # 步骤 6: Risk
    print("\n🛡️ 步骤 6: Risk Agent...")
    t0 = time.time()
    try:
        risk_review = risk.review(symbol=symbol, trader_decision=trader_decision, current_position=None, market_data=data.get('technical_data', {}))
        t1 = time.time() - t0
        approved = risk_review.get("approved", False)  # 修复：正确字段名
        recommendation = risk_review.get("recommendation", "N/A")
        result["steps"].append({"name": "Risk", "duration": round(t1, 2), "output": {"approved": approved, "recommendation": recommendation, "score": round(risk_review.get("risk_score", 0), 2)}})
        print(f"   ✅ {t1:.2f}s | approved={approved} rec={recommendation} (风险:{risk_review.get('risk_score', 0):.2f})")
    except Exception as e:
        result["errors"].append(str(e))
        risk_review = None
        approved = None
        recommendation = "ERROR"
        print(f"   ❌ {e}")
    
    # 最终
    result["final"] = {
        "decision": trader_decision.get("decision"),
        "bull": bull_view.get("recommendation"),
        "bear": bear_view.get("recommendation"),
        "approved": approved,
        "recommendation": recommendation
    }
    results.append(result)
    
    print(f"\n📋 最终决策：{trader_decision.get('decision')} | Risk: {recommendation}")

# 汇总
total_time = time.time() - start_time
print("\n" + "="*80)
print("📊 测试汇总报告")
print("="*80)
print(f"测试股票：{len(results)} 只")
print(f"总耗时：{total_time:.2f}s ({total_time/60:.1f}分钟)")
print(f"平均耗时：{total_time/len(results):.2f}s/只")

# 决策统计
decisions = {"BUY": 0, "SELL": 0, "HOLD": 0, "ERROR": 0}
for r in results:
    d = r.get("final", {}).get("decision", "ERROR")
    decisions[d] = decisions.get(d, 0) + 1

print(f"\n决策分布:")
for d, c in decisions.items():
    if c > 0:
        print(f"  {d}: {c} 只 ({c/len(results)*100:.1f}%)")

# 成功率
successful = sum(1 for r in results if not r["errors"])
print(f"\n成功率：{successful}/{len(results)} ({successful/len(results)*100:.1f}%)")

# 详细结果
print("\n📋 详细结果:")
print("-"*80)
for r in results:
    symbol = r["symbol"]
    name = r["name"]
    final = r.get("final", {})
    status = "✅" if not r["errors"] else "❌"
    print(f"{status} {symbol} {name}: Bull={final.get('bull','?')} Bear={final.get('bear','?')} → {final.get('decision','ERROR')} | Risk={final.get('recommendation','?')}")

# 保存
output = Path("/home/admin/.openclaw/workspace/agents/debate/data/10stocks_full_test.json")
with open(output, 'w', encoding='utf-8') as f:
    json.dump({
        "test_info": {
            "start_time": datetime.now().isoformat(),
            "total_duration": round(total_time, 2),
            "stocks_count": len(results)
        },
        "statistics": {
            "decisions": decisions,
            "success_rate": f"{successful/len(results)*100:.1f}%",
            "avg_duration": round(total_time/len(results), 2)
        },
        "results": results
    }, f, ensure_ascii=False, indent=2)

print(f"\n💾 详细结果已保存：{output}")
print("="*80)
