#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整辩论流程测试脚本

测试 10 只股票的完整辩论流程，详细记录每个步骤
用于排查问题和验证优化效果
"""

import json
import sys
import time
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

# 测试股票池 (10 只)
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

class DebateFlowTester:
    """辩论流程测试器"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent.parent / "data" / "test_results"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.aggregator = DataAggregator()
        self.protocol = DebateProtocol(data_dir=str(self.output_dir))
        self.bull = BullAgent()
        self.bear = BearAgent()
        self.trader = TraderAgent()
        self.risk = RiskAgent()
        
        # 测试结果
        self.results = []
        self.start_time = None
    
    def run_full_debate(self, stock: dict) -> dict:
        """执行单只股票的完整辩论流程"""
        symbol = stock["symbol"]
        name = stock["name"]
        
        print("\n" + "="*80)
        print(f"🎯 开始辩论：{symbol} - {name}")
        print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        result = {
            "symbol": symbol,
            "name": name,
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "errors": []
        }
        
        # ========== 步骤 1: 数据加载 ==========
        print("\n📊 步骤 1: 数据加载...")
        step1_start = time.time()
        
        try:
            data = self.aggregator.get_all_data(symbol, name)
            step1_time = time.time() - step1_start
            
            result["steps"].append({
                "step": 1,
                "name": "数据加载",
                "duration": round(step1_time, 2),
                "status": "success",
                "data_sources": data.get("metadata", {}).get("data_sources", {})
            })
            
            print(f"   ✅ 耗时：{step1_time:.2f}s")
            print(f"   因子数据：{'✓' if data.get('factor_data') else '✗'}")
            print(f"   技术数据：{'✓' if data.get('technical_data') else '✗'}")
            print(f"   舆情数据：{'✓' if data.get('sentiment_data') else '✗'}")
            print(f"   基本面：{'✓' if data.get('fundamental_data') else '✗'}")
            
            if data.get("sentiment_data"):
                print(f"   舆情来源：{data['sentiment_data'].get('sources', ['unknown'])}")
                print(f"   舆情评分：{data['sentiment_data'].get('sentiment_score', 0):.3f}")
            
        except Exception as e:
            step1_time = time.time() - step1_start
            result["steps"].append({
                "step": 1,
                "name": "数据加载",
                "duration": round(step1_time, 2),
                "status": "failed",
                "error": str(e)
            })
            result["errors"].append(f"数据加载失败：{e}")
            print(f"   ❌ 失败：{e}")
            return result
        
        # ========== 步骤 2: Bull Agent 分析 ==========
        print("\n🐂 步骤 2: Bull Agent 多头分析...")
        step2_start = time.time()
        
        try:
            bull_view = self.bull.analyze(
                symbol=symbol,
                factor_data=data.get("factor_data"),
                technical_data=data.get("technical_data"),
                sentiment_data=data.get("sentiment_data"),
                fundamental_data=data.get("fundamental_data")
            )
            step2_time = time.time() - step2_start
            
            self.protocol.submit_bull_view(bull_view)
            
            result["steps"].append({
                "step": 2,
                "name": "Bull Agent 分析",
                "duration": round(step2_time, 2),
                "status": "success",
                "output": {
                    "recommendation": bull_view.get("recommendation"),
                    "confidence": bull_view.get("confidence", 0),
                    "key_points": bull_view.get("key_points", [])[:3]
                }
            })
            
            print(f"   ✅ 耗时：{step2_time:.2f}s")
            print(f"   推荐：{bull_view.get('recommendation', 'N/A')}")
            print(f"   置信度：{bull_view.get('confidence', 0):.2f}")
            print(f"   关键点：{bull_view.get('key_points', [])[:2]}")
            
        except Exception as e:
            step2_time = time.time() - step2_start
            result["steps"].append({
                "step": 2,
                "name": "Bull Agent 分析",
                "duration": round(step2_time, 2),
                "status": "failed",
                "error": str(e)
            })
            result["errors"].append(f"Bull 分析失败：{e}")
            print(f"   ❌ 失败：{e}")
            return result
        
        # ========== 步骤 3: Bear Agent 分析 ==========
        print("\n🐻 步骤 3: Bear Agent 空头分析...")
        step3_start = time.time()
        
        try:
            bear_view = self.bear.analyze(
                symbol=symbol,
                factor_data=data.get("factor_data"),
                technical_data=data.get("technical_data"),
                sentiment_data=data.get("sentiment_data"),
                fundamental_data=data.get("fundamental_data"),
                bull_view=bull_view
            )
            step3_time = time.time() - step3_start
            
            self.protocol.submit_bear_view(bear_view)
            
            result["steps"].append({
                "step": 3,
                "name": "Bear Agent 分析",
                "duration": round(step3_time, 2),
                "status": "success",
                "output": {
                    "recommendation": bear_view.get("recommendation"),
                    "confidence": bear_view.get("confidence", 0),
                    "key_points": bear_view.get("key_points", [])[:3],
                    "rebuttals": bear_view.get("rebuttals", [])[:2]
                }
            })
            
            print(f"   ✅ 耗时：{step3_time:.2f}s")
            print(f"   推荐：{bear_view.get('recommendation', 'N/A')}")
            print(f"   置信度：{bear_view.get('confidence', 0):.2f}")
            print(f"   关键点：{bear_view.get('key_points', [])[:2]}")
            if bear_view.get("rebuttals"):
                print(f"   反驳：{bear_view['rebuttals'][:1]}")
            
        except Exception as e:
            step3_time = time.time() - step3_start
            result["steps"].append({
                "step": 3,
                "name": "Bear Agent 分析",
                "duration": round(step3_time, 2),
                "status": "failed",
                "error": str(e)
            })
            result["errors"].append(f"Bear 分析失败：{e}")
            print(f"   ❌ 失败：{e}")
            return result
        
        # ========== 步骤 4: 辩论分析 ==========
        print("\n📊 步骤 4: 辩论分析...")
        step4_start = time.time()
        
        try:
            analysis = self.protocol.analyze_debate()
            step4_time = time.time() - step4_start
            
            result["steps"].append({
                "step": 4,
                "name": "辩论分析",
                "duration": round(step4_time, 2),
                "status": "success",
                "output": {
                    "consensus_count": len(analysis.get("consensus", [])),
                    "disagreements_count": len(analysis.get("disagreements", [])),
                    "consensus": analysis.get("consensus", [])[:2],
                    "disagreements": analysis.get("disagreements", [])[:2]
                }
            })
            
            print(f"   ✅ 耗时：{step4_time:.2f}s")
            print(f"   共识点：{len(analysis.get('consensus', []))} 个")
            print(f"   分歧点：{len(analysis.get('disagreements', []))} 个")
            
        except Exception as e:
            step4_time = time.time() - step4_start
            result["steps"].append({
                "step": 4,
                "name": "辩论分析",
                "duration": round(step4_time, 2),
                "status": "failed",
                "error": str(e)
            })
            result["errors"].append(f"辩论分析失败：{e}")
            print(f"   ❌ 失败：{e}")
            return result
        
        # ========== 步骤 5: Trader Agent 决策 ==========
        print("\n💼 步骤 5: Trader Agent 决策...")
        step5_start = time.time()
        
        try:
            trader_decision = self.trader.make_decision(
                symbol=symbol,
                bull_view=bull_view,
                bear_view=bear_view,
                consensus_points=analysis.get("consensus", []),
                disagreement_points=analysis.get("disagreements", [])
            )
            step5_time = time.time() - step5_start
            
            result["steps"].append({
                "step": 5,
                "name": "Trader Agent 决策",
                "duration": round(step5_time, 2),
                "status": "success",
                "output": {
                    "decision": trader_decision.get("decision"),
                    "confidence": trader_decision.get("confidence", 0),
                    "position_size": trader_decision.get("position_size", 0),
                    "reasoning": trader_decision.get("reasoning", [])[:3]
                }
            })
            
            print(f"   ✅ 耗时：{step5_time:.2f}s")
            print(f"   决策：{trader_decision.get('decision', 'N/A')}")
            print(f"   置信度：{trader_decision.get('confidence', 0):.2f}")
            print(f"   仓位：{trader_decision.get('position_size', 0):.1%}")
            
        except Exception as e:
            step5_time = time.time() - step5_start
            result["steps"].append({
                "step": 5,
                "name": "Trader Agent 决策",
                "duration": round(step5_time, 2),
                "status": "failed",
                "error": str(e)
            })
            result["errors"].append(f"Trader 决策失败：{e}")
            print(f"   ❌ 失败：{e}")
            return result
        
        # ========== 步骤 6: Risk Agent 审核 ==========
        print("\n🛡️ 步骤 6: Risk Agent 风控审核...")
        step6_start = time.time()
        
        try:
            risk_review = self.risk.review(
                symbol=symbol,
                trader_decision=trader_decision,
                current_position={"cash": 100000, "positions": {}},
                market_data=data.get("technical_data", {})
            )
            step6_time = time.time() - step6_start
            
            result["steps"].append({
                "step": 6,
                "name": "Risk Agent 审核",
                "duration": round(step6_time, 2),
                "status": "success",
                "output": {
                    "approval": risk_review.get("approval"),
                    "risk_score": risk_review.get("risk_score", 0),
                    "risk_level": risk_review.get("risk_level", "N/A"),
                    "warnings": risk_review.get("warnings", [])[:2]
                }
            })
            
            print(f"   ✅ 耗时：{step6_time:.2f}s")
            print(f"   审批：{risk_review.get('approval', 'N/A')}")
            print(f"   风险评分：{risk_review.get('risk_score', 0)}/100")
            print(f"   风险等级：{risk_review.get('risk_level', 'N/A')}")
            
        except Exception as e:
            step6_time = time.time() - step6_start
            result["steps"].append({
                "step": 6,
                "name": "Risk Agent 审核",
                "duration": round(step6_time, 2),
                "status": "failed",
                "error": str(e)
            })
            result["errors"].append(f"Risk 审核失败：{e}")
            print(f"   ❌ 失败：{e}")
            # Risk 失败不影响最终结果，继续
        
        # ========== 最终结果 ==========
        result["end_time"] = datetime.now().isoformat()
        result["final_decision"] = trader_decision.get("decision", "N/A")
        result["final_approval"] = risk_review.get("approval") if 'risk_review' in dir() else None
        result["total_duration"] = sum(s.get("duration", 0) for s in result["steps"])
        
        print("\n" + "="*80)
        print(f"📋 最终结果：{symbol} - {name}")
        print("="*80)
        print(f"Bull: {bull_view.get('recommendation')} ({bull_view.get('confidence', 0):.2f})")
        print(f"Bear: {bear_view.get('recommendation')} ({bear_view.get('confidence', 0):.2f})")
        print(f"Trader: {trader_decision.get('decision', 'N/A')} ({trader_decision.get('confidence', 0):.2f})")
        print(f"Risk: {risk_review.get('approval', 'N/A') if 'risk_review' in dir() else 'N/A'}")
        print(f"总耗时：{result['total_duration']:.2f}s")
        
        return result
    
    def run_batch_test(self, stocks: list = None):
        """批量测试"""
        if stocks is None:
            stocks = TEST_STOCKS
        
        self.start_time = datetime.now()
        
        print("="*80)
        print("🚀 多空辩论系统 - 完整流程批量测试")
        print("="*80)
        print(f"测试股票数：{len(stocks)}")
        print(f"开始时间：{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"输出目录：{self.output_dir}")
        
        # 执行测试
        for i, stock in enumerate(stocks, 1):
            print(f"\n{'='*80}")
            print(f"📈 进度：{i}/{len(stocks)}")
            print(f"{'='*80}")
            
            result = self.run_full_debate(stock)
            self.results.append(result)
        
        # 生成汇总报告
        self.generate_summary_report()
        
        return self.results
    
    def generate_summary_report(self):
        """生成汇总报告"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        # 统计
        total = len(self.results)
        successful = sum(1 for r in self.results if not r["errors"])
        buy_count = sum(1 for r in self.results if r.get("final_decision") == "BUY")
        sell_count = sum(1 for r in self.results if r.get("final_decision") == "SELL")
        hold_count = sum(1 for r in self.results if r.get("final_decision") == "HOLD")
        
        avg_duration = sum(r["total_duration"] for r in self.results) / total if total > 0 else 0
        
        # 汇总报告
        summary = {
            "test_info": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_duration_seconds": round(total_duration, 2),
                "stocks_tested": total
            },
            "statistics": {
                "successful": successful,
                "failed": total - successful,
                "success_rate": f"{successful/total*100:.1f}%" if total > 0 else "0%",
                "decisions": {
                    "BUY": buy_count,
                    "SELL": sell_count,
                    "HOLD": hold_count
                },
                "avg_duration_per_stock": round(avg_duration, 2)
            },
            "results": self.results
        }
        
        # 保存报告
        report_path = self.output_dir / f"full_debate_test_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # 打印汇总
        print("\n" + "="*80)
        print("📊 测试汇总报告")
        print("="*80)
        print(f"测试股票：{total} 只")
        print(f"成功：{successful} 只 ({successful/total*100:.1f}%)")
        print(f"失败：{total - successful} 只")
        print(f"\n决策分布:")
        print(f"  BUY:  {buy_count} 只 ({buy_count/total*100:.1f}%)")
        print(f"  SELL: {sell_count} 只 ({sell_count/total*100:.1f}%)")
        print(f"  HOLD: {hold_count} 只 ({hold_count/total*100:.1f}%)")
        print(f"\n平均耗时：{avg_duration:.2f}s/只")
        print(f"总耗时：{total_duration:.2f}s")
        print(f"\n💾 报告已保存：{report_path}")
        print("="*80)


if __name__ == "__main__":
    tester = DebateFlowTester()
    tester.run_batch_test()
