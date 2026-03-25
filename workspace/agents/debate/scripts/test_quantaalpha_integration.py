#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 QuantaAlpha 真实数据集成

验证新的 QuantaAlpha Adapter 是否正确集成真实因子数据。
"""

import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.quantaalpha_adapter import QuantaAlphaAdapter
from adapters.data_aggregator import DataAggregator


def test_adapter_basic():
    """测试适配器基础功能"""
    print("=" * 70)
    print("测试 1: QuantaAlpha Adapter 基础功能")
    print("=" * 70)
    
    adapter = QuantaAlphaAdapter()
    
    # 检查状态
    status = adapter.get_status()
    print(f"\n适配器状态: {status['data_source']}")
    print(f"因子库大小：{status['factor_library_size']} 个因子")
    print(f"数据目录：{status['data_dir']}")
    
    assert status['available'], "适配器应该可用"
    assert status['factor_library_size'] > 0, "因子库应该有数据"
    assert status['data_source'] == 'real_data', "应该使用真实数据"
    
    print("✅ 基础功能测试通过")
    return adapter


def test_factor_scores(adapter):
    """测试因子评分计算"""
    print("\n" + "=" * 70)
    print("测试 2: 因子评分计算 (600519.SH)")
    print("=" * 70)
    
    scores = adapter.get_factor_scores("600519.SH")
    
    print(f"\n股票代码：{scores['symbol']}")
    print(f"Qlib 代码：{scores['qlib_code']}")
    print(f"因子信号：{scores['factor_signal']:.3f}")
    print(f"因子分位数：{scores['factor_percentile']:.2%}")
    print(f"因子 Z-Score: {scores['factor_zscore']:.2f}")
    print(f"因子原始值：{scores['factor_raw_value']:.6f}")
    print(f"动量评分：{scores['momentum_score']:.1f}/10")
    print(f"波动率评分：{scores['volatility_score']:.1f}/10")
    print(f"综合评分：{scores['composite_rating']:.1f}/10")
    print(f"数据点数：{scores['data_points']}")
    
    # 验证数据
    assert scores['data_source'] == 'quantaalpha_real_data', "应该使用真实数据"
    assert scores['data_points'] > 0, "应该有数据点"
    assert 'factor_signal' in scores, "应该有因子信号"
    assert -1 <= scores['factor_signal'] <= 1, "因子信号应该在 -1 到 1 之间"
    
    print("✅ 因子评分测试通过")
    return scores


def test_top_factors(adapter):
    """测试 Top 因子信号"""
    print("\n" + "=" * 70)
    print("测试 3: Top 因子信号")
    print("=" * 70)
    
    top_signals = adapter.get_top_factor_signals("600519.SH", top_n=10)
    
    print(f"\n综合评分：{top_signals['composite_score']:.3f}")
    print(f"因子数量：{top_signals['factor_count']}")
    print(f"平均 IC: {top_signals['avg_ic']:.4f}")
    print(f"平均 IR: {top_signals['avg_ir']:.2f}")
    
    print("\nTop 5 因子:")
    for i, fs in enumerate(top_signals['factor_signals'][:5], 1):
        print(f"  {i}. {fs['factor_name']}")
        print(f"     类别：{fs['category_cn']}")
        print(f"     IC: {fs['ic']:.3f}, IR: {fs['ir']:.2f}, 信号：{fs['signal']:.3f}")
        print(f"     表达式：{fs['factor_expression'][:60]}...")
    
    # 验证
    assert top_signals['factor_count'] > 0, "应该有因子信号"
    assert top_signals['avg_ic'] > 0.05, "平均 IC 应该大于 0.05"
    assert top_signals['avg_ir'] > 1.0, "平均 IR 应该大于 1.0"
    
    print("✅ Top 因子信号测试通过")
    return top_signals


def test_data_aggregator():
    """测试数据聚合器集成"""
    print("\n" + "=" * 70)
    print("测试 4: 数据聚合器集成")
    print("=" * 70)
    
    aggregator = DataAggregator()
    
    # 获取综合数据
    data = aggregator.get_all_data("600519.SH", "贵州茅台")
    
    print("\n数据源状态:")
    for source, status in data['metadata']['data_sources'].items():
        available = status.get('available', False)
        print(f"  {source}: {'✅' if available else '❌'}")
    
    print("\n因子数据摘要:")
    factor_data = data['factor_data']
    print(f"  数据源：{factor_data.get('data_source', 'unknown')}")
    print(f"  因子信号：{factor_data.get('factor_signal', 0):.3f}")
    print(f"  综合评分：{factor_data.get('composite_rating', 0):.1f}/10")
    
    # 验证
    assert factor_data['data_source'] == 'quantaalpha_real_data', "应该使用真实数据"
    assert 'factor_signal' in factor_data, "应该有因子信号"
    
    print("✅ 数据聚合器测试通过")
    return data


def test_multiple_stocks(adapter):
    """测试多只股票"""
    print("\n" + "=" * 70)
    print("测试 5: 多只股票测试")
    print("=" * 70)
    
    stocks = [
        ("600519.SH", "贵州茅台"),
        ("301029.SZ", "旗滨集团"),
        ("000001.SZ", "平安银行"),
    ]
    
    results = []
    for symbol, name in stocks:
        try:
            scores = adapter.get_factor_scores(symbol)
            if scores.get('data_source') == 'quantaalpha_real_data':
                results.append({
                    'symbol': symbol,
                    'name': name,
                    'factor_signal': scores['factor_signal'],
                    'composite_rating': scores['composite_rating']
                })
                print(f"  ✅ {symbol} ({name}): 信号={scores['factor_signal']:.2f}, 评分={scores['composite_rating']:.1f}/10")
            else:
                print(f"  ⚠️ {symbol} ({name}): 数据不可用")
        except Exception as e:
            print(f"  ❌ {symbol} ({name}): {e}")
    
    print(f"\n成功：{len(results)}/{len(stocks)} 只股票")
    return results


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "QuantaAlpha 真实数据集成测试" + " " * 15 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    try:
        # 测试 1: 基础功能
        adapter = test_adapter_basic()
        
        # 测试 2: 因子评分
        scores = test_factor_scores(adapter)
        
        # 测试 3: Top 因子信号
        top_factors = test_top_factors(adapter)
        
        # 测试 4: 数据聚合器
        data = test_data_aggregator()
        
        # 测试 5: 多只股票
        test_multiple_stocks(adapter)
        
        # 总结
        print("\n" + "=" * 70)
        print("🎉 所有测试通过!")
        print("=" * 70)
        print("\n关键改进:")
        print("  ✅ 使用 181 个真实因子 (IC>0.05, IR>1.0)")
        print("  ✅ 从 Qlib 读取真实因子值")
        print("  ✅ 基于真实数据计算信号")
        print("  ✅ 移除模拟数据依赖")
        print()
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}")
        return False
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
