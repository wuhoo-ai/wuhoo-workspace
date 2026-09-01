#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多空辩论系统主入口

用法:
    python run_debate.py --symbol 600519.SH --mode full
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from protocols.debate_protocol import DebateProtocol
from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent
from agents.risk_agent import RiskAgent
from adapters.data_aggregator import DataAggregator


def run_full_debate(
    symbol: str,
    company_name: Optional[str] = None,
    output_dir: str = "data",
    use_real_data: bool = True
) -> Dict:
    """执行完整的多空辩论流程"""
    print("\n" + "="*60)
    print("🎯 开始多空辩论：{}".format(symbol))
    if company_name:
        print("   公司：{}".format(company_name))
    print("="*60 + "\n")
    
    # 加载数据
    print("📥 加载数据...")
    aggregator = DataAggregator()
    
    if use_real_data:
        data = aggregator.get_all_data(symbol, company_name)
        print("   因子数据：{}".format("✅" if data.get('factor_data') else "⚠️"))
        print("   技术面：{}".format("✅" if data.get('technical_data') else "⚠️"))
        print("   舆情：{}".format("✅" if data.get('sentiment_data') else "⚠️"))
        print("   基本面：{}".format("✅" if data.get('fundamental_data') else "⚠️"))
    else:
        data = _get_mock_data(symbol)
        print("   ⚠️  使用模拟数据")
    print()
    
    # 初始化
    protocol = DebateProtocol(data_dir=output_dir)
    bull = BullAgent()
    bear = BearAgent()
    trader = TraderAgent()
    risk = RiskAgent()
    
    # 1. 开始辩论
    protocol.start_debate(symbol)
    
    # 2. Bull 分析
    print("🐂 Bull Agent 分析中...")
    bull_view = bull.analyze(
        symbol=symbol,
        factor_data=data.get("factor_data"),
        technical_data=data.get("technical_data"),
        sentiment_data=data.get("sentiment_data"),
        fundamental_data=data.get("fundamental_data")
    )
    protocol.submit_bull_view(bull_view)
    print("   推荐：{}, 置信度：{:.2f}\n".format(
        bull_view.get('recommendation'),
        bull_view.get('confidence', 0)
    ))
    # 3. Bear 反驳（针对 Bull 观点）
    print("\U0001f43b Bear Agent 反驳中...")
    bear = BearAgent()
    bear_view = bear.analyze(
        symbol=symbol,
        factor_data=data.get("factor_data"),
        technical_data=data.get("technical_data"),
        sentiment_data=data.get("sentiment_data"),
        fundamental_data=data.get("fundamental_data"),
        bull_view=bull_view
    )
    protocol.submit_bear_view(bear_view)
    print("   推荐：{}, 置信度：{:.2f}\n".format(
        bear_view.get('recommendation'),
        bear_view.get('confidence', 0)
    ))
    
    # 4. Bull 反驳轮次（Rebuttal - 回应 Bear 的质疑）
    print("\U0001f402 Bull Agent 反驳轮次...")
    bull_rebuttal = bull.analyze_with_context(
        symbol=symbol,
        data={
            "factor_data": data.get("factor_data"),
            "technical_data": data.get("technical_data"),
            "sentiment_data": data.get("sentiment_data"),
            "fundamental_data": data.get("fundamental_data"),
        },
        bear_view=bear_view
    )
    print("   反驳后推荐：{}, 置信度：{:.2f}\n".format(
        bull_rebuttal.get('recommendation'),
        bull_rebuttal.get('confidence', 0)
    ))
    
    # 使用反驳后的观点提交（保留原始观点用于对比）
    protocol.submit_bull_rebuttal(bull_rebuttal)
    # 同时更新 bull_view 为 rebuttal 版本，用于后续分析
    protocol.current_debate.bull_view = bull_rebuttal
    
    # 5. 分析辩论
    print("\\U0001f4ca 分析辩论...")
    analysis = protocol.analyze_debate()
    print("   共识点：{} 个".format(len(analysis['consensus'])))
    for point in analysis['consensus']:
        print("      \u2022 {}".format(point))
    print("   分歧点：{} 个".format(len(analysis['disagreement'])))
    for point in analysis['disagreement']:
        print("      \u2022 {}".format(point))
    print()
    
    # 6. Trader 决策
    print("\U0001f4bc Trader Agent 决策中...")
    trader_decision = trader.make_decision(
        symbol=symbol,
        bull_view=bull_rebuttal,
        bear_view=bear_view,
        consensus_points=analysis['consensus'],
        disagreement_points=analysis['disagreement']
    )
    protocol.submit_trader_decision(trader_decision)
    print("   决策：{}, 仓位：{:.1%}\n".format(
        trader_decision.get('decision'),
        trader_decision.get('position_size', 0)
    ))
    
    # 6. Risk 审批
    print("\\U0001f6e1\\U000fe0 Risk Agent 审核中...")
    
    # 加载当前持仓上下文 (用于集中度检查)
    current_position = None
    portfolio_file = Path(output_dir) / f"portfolio_{symbol.split('.')[-1].lower()}.json"
    if portfolio_file.exists():
        try:
            with open(portfolio_file, 'r', encoding='utf-8') as f:
                current_position = json.load(f)
            print(f"   加载持仓上下文: {portfolio_file.name}")
        except Exception as e:
            print(f"   警告: 无法加载持仓文件 {e}")
    
    risk_approval = risk.review(
        symbol=symbol,
        trader_decision=trader_decision,
        current_position=current_position,
        market_data=data.get("market_data")
    )
    protocol.submit_risk_approval(risk_approval)
    print("   审批：{}, 风险评分：{:.2f}\n".format(
        risk_approval.get('recommendation'),
        risk_approval.get('risk_score', 0)
    ))
    
    # 7. 最终决策
    if risk_approval.get("recommendation") == "REJECT":
        action = "reject"
        reason = "Risk Agent 拒绝交易"
    elif risk_approval.get("recommendation") == "CONDITIONAL":
        action = "modify"
        reason = "有条件通过：" + ", ".join(risk_approval.get('conditions', []))
    elif trader_decision.get("position_size", 0) > 0.10:
        action = "pending_user_approval"
        reason = "大额交易，需要用户确认"
    else:
        action = "execute"
        reason = "审批通过，执行交易"
    
    # 8. 完成辩论
    record = protocol.finalize(action=action, reason=reason)

    # 附加数据质量信息
    result_dict = record.to_dict()
    if use_real_data:
        result_dict['data_quality'] = data.get('data_quality', {})
        result_dict['sentiment_summary'] = {
            'source': data.get('sentiment_data', {}).get('source', 'unknown'),
            'label': data.get('sentiment_data', {}).get('sentiment_label', 'unknown'),
            'score': data.get('sentiment_data', {}).get('sentiment_score', 0),
        }

    print("="*60)
    print("✅ 辩论完成：{}".format(record.debate_id))
    print("   最终动作：{}".format(action))
    print("   原因：{}".format(reason))
    print("="*60 + "\n")

    return result_dict


def _get_mock_data(symbol: str) -> Dict:
    """生成模拟数据"""
    return {
        "factor_data": {
            "momentum_score": 7.5,
            "volatility_score": 5.2,
            "turnover_score": 6.8
        },
        "technical_data": {
            "macd": "golden_cross",
            "rsi": 55,
            "trend": "uptrend"
        },
        "sentiment_data": {
            "sentiment_score": 0.4,
            "hot_topics": ["AI", "芯片"]
        },
        "fundamental_data": {
            "pe": 25.5,
            "roe": 0.15,
            "revenue_growth": 0.20
        },
        "market_data": {
            "volatility": 0.35,
            "daily_turnover": 80000000
        }
    }


def run_quick_debate(symbol: str) -> Dict:
    """快速辩论 (使用模拟数据)"""
    return run_full_debate(symbol, use_real_data=False)


def main():
    parser = argparse.ArgumentParser(description="多空辩论系统")
    parser.add_argument("--symbol", type=str, required=True, help="股票代码")
    parser.add_argument("--name", type=str, default=None, help="公司名称")
    parser.add_argument("--mode", type=str, choices=["full", "quick"], default="full", help="运行模式")
    parser.add_argument("--output", type=str, default="data", help="输出目录")
    
    args = parser.parse_args()
    
    if args.mode == "quick":
        result = run_quick_debate(args.symbol)
    else:
        result = run_full_debate(args.symbol, args.name, args.output, use_real_data=True)
    
    # 输出摘要
    print("\n📋 辩论结果摘要:")
    print(json.dumps({
        "debate_id": result.get("debate_id"),
        "symbol": result.get("symbol"),
        "bull_recommendation": result.get("bull_view", {}).get("recommendation"),
        "bear_recommendation": result.get("bear_view", {}).get("recommendation"),
        "trader_decision": result.get("trader_decision", {}).get("decision"),
        "risk_approval": result.get("risk_approval", {}).get("recommendation"),
        "final_action": result.get("final_action", {}).get("action")
    }, indent=2, ensure_ascii=False))
    
    return result


if __name__ == "__main__":
    main()
