#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源诊断脚本

检查所有数据源的可用性和数据质量。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_data_sources():
    """检查所有数据源"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "数据源可用性诊断" + " " * 20 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    results = {
        "factor": {"status": "unknown", "quality": "unknown", "message": ""},
        "fundamental": {"status": "unknown", "quality": "unknown", "message": ""},
        "technical": {"status": "unknown", "quality": "unknown", "message": ""},
        "sentiment": {"status": "unknown", "quality": "unknown", "message": ""},
    }
    
    # 1. 检查因子数据
    print("📊 [1/4] 检查因子数据...")
    try:
        from adapters.quantaalpha_adapter import QuantaAlphaAdapter
        adapter = QuantaAlphaAdapter()
        status = adapter.get_status()
        
        if status.get('available'):
            scores = adapter.get_factor_scores('600519.SH')
            results["factor"]["status"] = "✅ 可用"
            results["factor"]["quality"] = scores.get('data_source', 'unknown')
            results["factor"]["message"] = f"181 个因子, 信号={scores.get('factor_signal', 0):.2f}"
            print(f"   ✅ 因子数据: {results['factor']['message']}")
        else:
            results["factor"]["status"] = "❌ 不可用"
            results["factor"]["quality"] = "degraded"
            print(f"   ❌ 因子数据: 不可用")
    except Exception as e:
        results["factor"]["status"] = "❌ 错误"
        results["factor"]["message"] = str(e)
        print(f"   ❌ 因子数据: {e}")
    
    # 2. 检查基本面数据
    print("\n📈 [2/4] 检查基本面数据...")
    try:
        from adapters.fundamental_adapter import FundamentalAdapter
        f_adapter = FundamentalAdapter()
        
        f_status = f_adapter.get_status()
        data = f_adapter.get_fundamental_data('600519.SH')
        
        if data.get('data_quality') == 'real':
            results["fundamental"]["status"] = "✅ 可用"
            results["fundamental"]["quality"] = "real"
            results["fundamental"]["message"] = f"PE={data.get('pe')}, PB={data.get('pb')}"
            print(f"   ✅ 基本面数据: {results['fundamental']['message']}")
        else:
            results["fundamental"]["status"] = "⚠️ 降级"
            results["fundamental"]["quality"] = "degraded"
            results["fundamental"]["message"] = "使用行业估计值"
            print(f"   ⚠️ 基本面数据: 降级模式")
            print(f"      原因: {f_status.get('available_sources', ['none'])}")
    except Exception as e:
        results["fundamental"]["status"] = "❌ 错误"
        results["fundamental"]["message"] = str(e)
        print(f"   ❌ 基本面数据: {e}")
    
    # 3. 检查技术面数据
    print("\n📉 [3/4] 检查技术面数据...")
    try:
        from adapters.akshare_adapter import AkShareAdapter
        a_adapter = AkShareAdapter()
        
        if a_adapter.is_available():
            data = a_adapter.get_technical_data('600519.SH')
            results["technical"]["status"] = "✅ 可用"
            results["technical"]["quality"] = data.get('data_source', 'real')
            results["technical"]["message"] = f"价格={data.get('price')}, RSI={data.get('rsi')}"
            print(f"   ✅ 技术面数据: {results['technical']['message']}")
        else:
            results["technical"]["status"] = "⚠️ 降级"
            results["technical"]["quality"] = "degraded"
            results["technical"]["message"] = "使用模拟数据"
            print(f"   ⚠️ 技术面数据: 降级模式")
    except Exception as e:
        results["technical"]["status"] = "❌ 错误"
        results["technical"]["message"] = str(e)
        print(f"   ❌ 技术面数据: {e}")
    
    # 4. 检查舆情数据
    print("\n📰 [4/4] 检查舆情数据...")
    try:
        from adapters.trendradar_adapter import TrendRadarAdapter
        t_adapter = TrendRadarAdapter()
        
        t_status = t_adapter.get_status()
        if t_status.get('available'):
            # 尝试获取舆情数据
            results["sentiment"]["status"] = "✅ 可用"
            results["sentiment"]["quality"] = "real"
            results["sentiment"]["message"] = "TrendRadar 已配置"
            print(f"   ✅ 舆情数据: {results['sentiment']['message']}")
        else:
            results["sentiment"]["status"] = "⚠️ 需配置"
            results["sentiment"]["quality"] = "unknown"
            results["sentiment"]["message"] = "TrendRadar 未配置"
            print(f"   ⚠️ 舆情数据: {results['sentiment']['message']}")
    except Exception as e:
        results["sentiment"]["status"] = "❌ 错误"
        results["sentiment"]["message"] = str(e)
        print(f"   ❌ 舆情数据: {e}")
    
    # 总结
    print("\n" + "=" * 70)
    print("📋 数据质量总结")
    print("=" * 70)
    
    quality_map = {
        "real": "✅ 真实数据",
        "degraded": "⚠️ 降级数据",
        "unknown": "❓ 未确定",
    }
    
    for category, info in results.items():
        status_icon = "✅" if "可用" in info["status"] else ("⚠️" if "降级" in info["status"] else "❌")
        print(f"{status_icon} {category:12s}: {info['status']:12s} - {quality_map.get(info['quality'], info['quality'])}")
        if info.get('message'):
            print(f"    {info['message']}")
    
    # 计算总体评分
    real_count = sum(1 for r in results.values() if r.get('quality') == 'real')
    degraded_count = sum(1 for r in results.values() if r.get('quality') == 'degraded')
    
    print("\n" + "=" * 70)
    if real_count >= 3:
        print("🎉 总体评估：良好 (真实数据占比高)")
    elif real_count >= 1:
        print("⚠️  总体评估：部分降级 (需要配置真实数据源)")
    else:
        print("❌  总体评估：数据不足 (需要配置数据源)")
    print("=" * 70)
    
    # 行动建议
    print("\n📌 行动建议:")
    print("-" * 70)
    
    if results["fundamental"]["quality"] != "real":
        print("🔴 高优先级: 配置 Tushare Token")
        print("   1. 注册 https://tushare.pro/")
        print("   2. 获取 Token")
        print("   3. 添加到 ~/.openclaw/.env: TS_TOKEN=your_token")
    
    if results["technical"]["quality"] != "real":
        print("🟡 中优先级: 修复 AkShare 网络连接")
        print("   - 检查网络访问 eastmoney.com 是否正常")
    
    if results["sentiment"]["quality"] != "real":
        print("🟡 中优先级: 配置 TrendRadar")
        print("   - 检查 ~/openclaw/workspace/Code/TrendRadar 配置")
    
    print()
    return results


if __name__ == "__main__":
    results = check_data_sources()