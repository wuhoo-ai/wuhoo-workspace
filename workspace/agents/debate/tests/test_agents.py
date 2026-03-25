#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 单元测试套件
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent
from agents.risk_agent import RiskAgent
from agents.portfolio_manager import PortfolioManager


def test_bull_agent():
    """测试 Bull Agent"""
    print("\n测试：Bull Agent")
    
    agent = BullAgent()
    
    # 模拟数据
    result = agent.analyze(
        symbol="600519.SH",
        factor_data={"momentum_score": 8.5},
        technical_data={"macd": "golden_cross", "rsi": 55},
        sentiment_data={"sentiment_score": 0.4},
        fundamental_data={"pe": 25, "roe": 0.15}
    )
    
    assert result["agent"] == "bull"
    assert result["symbol"] == "600519.SH"
    assert "recommendation" in result
    assert "confidence" in result
    assert "bullish_points" in result
    
    print("  ✅ Bull Agent 输出格式正确")
    print("     推荐：{}, 置信度：{:.2f}".format(
        result["recommendation"], result["confidence"]
    ))
    return True


def test_bear_agent():
    """测试 Bear Agent"""
    print("\n测试：Bear Agent")
    
    agent = BearAgent()
    
    bull_view = {
        "recommendation": "BUY",
        "confidence": 0.75,
        "bullish_points": [
            {"category": "factor", "point": "动量强势", "evidence": "评分 8.5", "weight": 0.3}
        ]
    }
    
    result = agent.analyze(
        symbol="600519.SH",
        factor_data={"momentum_score": 8.5, "volatility_score": 7.8},
        technical_data={"rsi": 78},  # 超买
        bull_view=bull_view
    )
    
    assert result["agent"] == "bear"
    assert result["symbol"] == "600519.SH"
    assert "recommendation" in result
    assert "bearish_points" in result
    
    print("  ✅ Bear Agent 输出格式正确")
    print("     推荐：{}, 置信度：{:.2f}".format(
        result["recommendation"], result["confidence"]
    ))
    return True


def test_trader_agent():
    """测试 Trader Agent"""
    print("\n测试：Trader Agent")
    
    agent = TraderAgent()
    
    bull_view = {
        "recommendation": "BUY",
        "confidence": 0.75,
        "target_price": 1500,
        "stop_loss": 1350
    }
    
    bear_view = {
        "recommendation": "SELL",
        "confidence": 0.65,
        "target_price": 1200,
        "stop_loss": 1450
    }
    
    result = agent.make_decision(
        symbol="600519.SH",
        bull_view=bull_view,
        bear_view=bear_view,
        consensus_points=["双方都认同需要止损"],
        disagreement_points=["目标价分歧"]
    )
    
    assert result["agent"] == "trader"
    assert result["decision"] in ["BUY", "SELL", "HOLD"]
    assert "position_size" in result
    assert "risk_reward_ratio" in result
    
    print("  ✅ Trader Agent 输出格式正确")
    print("     决策：{}, 仓位：{:.1%}".format(
        result["decision"], result["position_size"]
    ))
    return True


def test_risk_agent():
    """测试 Risk Agent"""
    print("\n测试：Risk Agent")
    
    agent = RiskAgent()
    
    trader_decision = {
        "decision": "BUY",
        "position_size": 0.10,
        "risk_reward_ratio": 2.5,
        "action": {
            "side": "buy",
            "stop_loss": 1350,
            "take_profit": 1500
        }
    }
    
    result = agent.review(
        symbol="600519.SH",
        trader_decision=trader_decision,
        market_data={"volatility": 0.35, "daily_turnover": 80000000}
    )
    
    assert result["agent"] == "risk"
    assert "approved" in result
    assert "recommendation" in result
    assert result["recommendation"] in ["APPROVE", "CONDITIONAL", "REJECT"]
    assert "checks" in result
    
    print("  ✅ Risk Agent 输出格式正确")
    print("     审批：{}, 风险评分：{:.2f}".format(
        result["recommendation"], result["risk_score"]
    ))
    return True


def test_portfolio_manager():
    """测试 Portfolio Manager"""
    print("\n测试：Portfolio Manager")
    
    pm = PortfolioManager()
    
    trader_decision = {
        "decision": "BUY",
        "position_size": 0.15,  # 15% 仓位
        "action": {
            "side": "buy",
            "quantity": 100
        }
    }
    
    risk_approval = {
        "recommendation": "APPROVE",
        "risk_score": 0.35
    }
    
    result = pm.review_decision(
        symbol="600519.SH",
        trader_decision=trader_decision,
        risk_approval=risk_approval
    )
    
    assert result["agent"] == "portfolio_manager"
    assert result["action"] in ["approve", "reject", "pending_user_approval"]
    assert "requires_user_approval" in result
    
    print("  ✅ Portfolio Manager 输出格式正确")
    print("     动作：{}, 需用户确认：{}".format(
        result["action"], result["requires_user_approval"]
    ))
    return True


def test_agent_initialization():
    """测试所有 Agent 初始化"""
    print("\n测试：Agent 初始化")
    
    agents = {
        "BullAgent": BullAgent,
        "BearAgent": BearAgent,
        "TraderAgent": TraderAgent,
        "RiskAgent": RiskAgent,
        "PortfolioManager": PortfolioManager
    }
    
    for name, cls in agents.items():
        try:
            agent = cls()
            assert hasattr(agent, "name")
            assert hasattr(agent, "analyze") or hasattr(agent, "make_decision") or hasattr(agent, "review") or hasattr(agent, "review_decision")
            print("  ✅ {} 初始化成功".format(name))
        except Exception as e:
            print("  ❌ {} 初始化失败：{}".format(name, e))
            return False
    
    return True


def run_all_tests():
    """运行所有 Agent 测试"""
    print("\n" + "="*60)
    print("🧪 Agent 单元测试套件")
    print("="*60)
    
    tests = [
        ("Agent 初始化", test_agent_initialization),
        ("Bull Agent", test_bull_agent),
        ("Bear Agent", test_bear_agent),
        ("Trader Agent", test_trader_agent),
        ("Risk Agent", test_risk_agent),
        ("Portfolio Manager", test_portfolio_manager)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print("❌ {} 测试失败".format(name))
        except Exception as e:
            failed += 1
            print("❌ {} 测试异常：{}".format(name, e))
    
    print("\n" + "="*60)
    print("测试结果：{} 通过，{} 失败".format(passed, failed))
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
