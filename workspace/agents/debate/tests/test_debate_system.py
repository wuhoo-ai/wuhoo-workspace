#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多空辩论系统测试套件
"""

import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.data_aggregator import DataAggregator
from adapters.trendradar_adapter import TrendRadarAdapter
from adapters.akshare_adapter import AkShareAdapter


def test_data_aggregator():
    """测试数据聚合器"""
    print("\n" + "="*60)
    print("测试：DataAggregator")
    print("="*60)
    
    aggregator = DataAggregator()
    
    # 测试获取数据
    data = aggregator.get_all_data("600519.SH", "贵州茅台")
    
    assert "factor_data" in data, "缺少因子数据"
    assert "technical_data" in data, "缺少技术面数据"
    assert "sentiment_data" in data, "缺少舆情数据"
    assert "fundamental_data" in data, "缺少基本面数据"
    
    print("✅ 数据聚合器工作正常")
    print("   因子评分：{}".format(data["factor_data"].get("momentum_score", 0)))
    print("   技术信号：{}".format(data["technical_data"].get("signal", "unknown")))
    print("   舆情评分：{}".format(data["sentiment_data"].get("sentiment_score", 0)))
    
    return True


def test_trendradar_adapter():
    """测试 TrendRadar 适配器"""
    print("\n" + "="*60)
    print("测试：TrendRadarAdapter")
    print("="*60)
    
    adapter = TrendRadarAdapter()
    
    # 测试获取舆情数据
    sentiment = adapter.get_sentiment_data("600519.SH", "贵州茅台")
    
    assert "sentiment_score" in sentiment, "缺少舆情评分"
    assert "hot_topics" in sentiment, "缺少热点话题"
    
    print("✅ TrendRadar 适配器工作正常")
    print("   热点话题：{}".format(", ".join(sentiment.get("hot_topics", []))))
    
    return True


def test_akshare_adapter():
    """测试 AkShare 适配器"""
    print("\n" + "="*60)
    print("测试：AkShareAdapter")
    print("="*60)
    
    adapter = AkShareAdapter()
    
    # 测试获取技术面数据
    technical = adapter.get_technical_data("600519.SH")
    
    assert "macd" in technical, "缺少 MACD"
    assert "rsi" in technical, "缺少 RSI"
    
    print("✅ AkShare 适配器工作正常")
    print("   akshare 可用：{}".format(adapter.is_available()))
    print("   技术信号：{}".format(technical.get("signal", "unknown")))
    
    return True


def test_full_debate():
    """测试完整辩论流程"""
    print("\n" + "="*60)
    print("测试：完整辩论流程")
    print("="*60)
    
    from run_debate import run_full_debate
    
    result = run_full_debate(
        symbol="600519.SH",
        company_name="贵州茅台",
        output_dir="tests/data",
        use_real_data=False  # 使用模拟数据避免依赖
    )
    
    assert "debate_id" in result, "缺少辩论 ID"
    assert "bull_view" in result, "缺少 Bull 观点"
    assert "bear_view" in result, "缺少 Bear 观点"
    assert "trader_decision" in result, "缺少 Trader 决策"
    assert "risk_approval" in result, "缺少 Risk 审批"
    assert "final_action" in result, "缺少最终动作"
    
    print("✅ 完整辩论流程测试通过")
    print("   辩论 ID: {}".format(result["debate_id"]))
    print("   最终动作：{}".format(result["final_action"]))
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 多空辩论系统测试套件")
    print("="*60)
    
    tests = [
        ("TrendRadar 适配器", test_trendradar_adapter),
        ("AkShare 适配器", test_akshare_adapter),
        ("数据聚合器", test_data_aggregator),
        ("完整辩论流程", test_full_debate)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print("❌ {} 测试失败：{}".format(name, e))
            failed += 1
    
    print("\n" + "="*60)
    print("测试结果：{} 通过，{} 失败".format(passed, failed))
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
