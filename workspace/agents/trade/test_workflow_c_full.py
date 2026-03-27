#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow C 全链路验证测试

验证环节:
1. 选股数据就绪
2. 分析模块可用
3. 辩论模块可用
4. 交易执行正常 (CN/HK/US)
"""

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

os.environ['FUTU_HOST'] = '127.0.0.1'
os.environ['FUTU_PORT'] = '11111'
os.environ['FUTU_ENV'] = 'SIMULATE'


def check_data_files():
    """检查数据文件"""
    print("=" * 60)
    print("1. 检查数据文件")
    print("=" * 60)

    files_to_check = {
        '港股成分股': Path.home() / '.openclaw/workspace/agents/main/data/stock-pick/index_members_hk_top500.csv',
        '美股成分股': Path.home() / '.openclaw/workspace/agents/main/data/stock-pick/index_members_us_top500.csv',
        'A 股数据 (202603)': Path.home() / '.openclaw/workspace/agents/main/data/stock-pick/daily_data/2026/202603.csv',
        '股票名称': Path.home() / '.openclaw/workspace/agents/main/data/stock-pick/stock_names.csv',
    }

    all_ok = True
    for name, path in files_to_check.items():
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"  ✅ {name}: {path.name} ({size_kb:.1f} KB)")
        else:
            print(f"  ❌ {name}: 不存在 - {path}")
            all_ok = False

    return all_ok


def check_modules():
    """检查模块可用性"""
    print("\n" + "=" * 60)
    print("2. 检查模块可用性")
    print("=" * 60)

    modules = {
        'futu-api': lambda: __import__('futu'),
        'yfinance': lambda: __import__('yfinance'),
        'pandas': lambda: __import__('pandas'),
        'debate (run_debate)': lambda: __import__('run_debate', level=0),
    }

    all_ok = True
    for name, import_func in modules.items():
        try:
            import_func()
            print(f"  ✅ {name}: 可用")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            all_ok = False

    return all_ok


def check_workflow_script():
    """检查 Workflow 脚本"""
    print("\n" + "=" * 60)
    print("3. 检查 Workflow C 脚本")
    print("=" * 60)

    script_path = Path(__file__).parent / 'workflow_c_multi_market.py'
    if script_path.exists():
        print(f"  ✅ workflow_c_multi_market.py: 存在 ({script_path.stat().st_size} bytes)")

        # 检查关键方法
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()

        methods = [
            'step1_select_stocks',
            'step2_analyze_stocks',
            'step3_debate',
            'step4_generate_recommendations',
            'step5_execute_trades',
            '_execute_trades_direct',
            '_convert_code',
            '_get_price',
        ]

        for method in methods:
            if f'def {method}' in content:
                print(f"      ✅ {method}()")
            else:
                print(f"      ❌ {method}() - 缺失")

        return True
    else:
        print(f"  ❌ workflow_c_multi_market.py: 不存在")
        return False


def test_trade_execution():
    """测试交易执行 (各市场模拟下单)"""
    print("\n" + "=" * 60)
    print("4. 测试交易执行 (模拟)")
    print("=" * 60)

    from workflow_c_multi_market import WorkflowCHandler

    markets = [
        ('cn', 'A 股', '603220.SH', '中贝通信'),
        ('hk', '港股', '00700', '腾讯控股'),
        ('us', '美股', 'AAPL', 'Apple Inc'),
    ]

    all_ok = True
    for market, market_name, code, name in markets:
        print(f"\n  测试 {market_name}...")

        handler = WorkflowCHandler(market=market, date='2026-03-27')
        recommendations = {
            'recommendations': [{'code': code, 'name': name, 'action': 'BUY'}]
        }

        try:
            result = handler.step5_execute_trades(recommendations)
            if result.get('success'):
                if result.get('trade_results'):
                    trade = result['trade_results'][0]
                    if trade.get('status') == 'SUBMITTED':
                        print(f"    ✅ {market_name} 下单成功 - 订单 ID: {trade.get('order_id')}")
                    else:
                        print(f"    ⚠️ {market_name} 订单状态：{trade.get('status')}")
                else:
                    print(f"    ⚠️ {market_name} 无交易结果")
            else:
                print(f"    ❌ {market_name} 失败：{result.get('error', 'Unknown')}")
                all_ok = False
        except Exception as e:
            print(f"    ❌ {market_name} 异常：{e}")
            all_ok = False

    return all_ok


def main():
    """主测试函数"""
    print("Workflow C 全链路验证测试")
    print("时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()

    results = []

    # 1. 数据文件
    results.append(('数据文件', check_data_files()))

    # 2. 模块可用性
    results.append(('模块可用性', check_modules()))

    # 3. Workflow 脚本
    results.append(('Workflow 脚本', check_workflow_script()))

    # 4. 交易执行
    results.append(('交易执行', test_trade_execution()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")

    all_passed = all(r[1] for r in results)
    print()
    if all_passed:
        print("🎉 Workflow C 全链路验证通过!")
    else:
        print("⚠️ 部分环节存在问题，请检查修复")

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
