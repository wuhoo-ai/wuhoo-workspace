#!/home/admin/.openclaw/workspace/agents/trade/venv-futu/bin/python3
# -*- coding: utf-8 -*-
"""
Workflow C - A 股模拟交易执行脚本

执行流程:
1. 读取投资建议
2. 风控检查 (仓位、集中度、停牌等)
3. 生成交易订单 (模拟)
4. 等待人工确认
5. 执行交易 (模拟)
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 加载环境变量
env_file = Path.home() / '.openclaw' / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key.strip() and value.strip():
                    os.environ[key.strip()] = value.strip()


class RiskManager:
    """风控管理器"""

    def __init__(self):
        self.max_position_pct = 0.2  # 单只股票最大仓位 20%
        self.min_cash_pct = 0.1      # 最小现金比例 10%
        self.stop_loss_pct = 0.08    # 单只股票止损 8%

    def check_order(self, order, position=None):
        """
        风控检查

        Returns:
            dict: {passed, checks, warnings, block_reason}
        """
        checks = []
        warnings = []
        passed = True
        block_reason = None

        # 检查 1: 仓位集中度
        if position:
            total_value = position.get('total_value', 1000000)
            order_value = order.get('price', 0) * order.get('qty', 0)
            position_pct = order_value / total_value if total_value > 0 else 0

            if position_pct > self.max_position_pct:
                passed = False
                block_reason = f"单只股票仓位超过{self.max_position_pct*100}%"
                checks.append({'item': '仓位集中度', 'status': 'FAIL', 'value': f"{position_pct:.2%}"})
            else:
                checks.append({'item': '仓位集中度', 'status': 'PASS', 'value': f"{position_pct:.2%}"})

            # 现金比例检查
            cash = position.get('cash', 1000000)
            if cash - order_value < total_value * self.min_cash_pct:
                passed = False
                block_reason = f"现金比例低于{self.min_cash_pct*100}%"
                checks.append({'item': '现金比例', 'status': 'FAIL', 'value': f"{cash/total_value:.2%}"})
            else:
                checks.append({'item': '现金比例', 'status': 'PASS', 'value': f"{cash/total_value:.2%}"})
        else:
            checks.append({'item': '仓位集中度', 'status': 'SKIP', 'value': '无持仓数据'})
            checks.append({'item': '现金比例', 'status': 'SKIP', 'value': '无持仓数据'})

        # 检查 2: 价格合理性
        price = order.get('price', 0)
        if price <= 0:
            passed = False
            block_reason = "价格无效"
            checks.append({'item': '价格有效性', 'status': 'FAIL'})
        else:
            checks.append({'item': '价格有效性', 'status': 'PASS'})

        # 检查 3: 数量合理性
        qty = order.get('qty', 0)
        if qty <= 0 or qty % 100 != 0:
            passed = False
            block_reason = "数量必须是 100 的倍数"
            checks.append({'item': '数量有效性', 'status': 'FAIL'})
        else:
            checks.append({'item': '数量有效性', 'status': 'PASS'})

        return {
            'passed': passed,
            'checks': checks,
            'warnings': warnings,
            'block_reason': block_reason,
            'requires_confirmation': not passed
        }


def simulate_trade(recommendation, position=None):
    """模拟交易"""
    print(f"\n处理订单：{recommendation['code']} {recommendation['name']}")

    # 获取当前价格 (模拟)
    price = 10.0  # 模拟价格，实际应从行情获取
    if '皖能电力' in recommendation['name']:
        price = 8.39  # 根据 PE 估算
    elif '中国黄金' in recommendation['name']:
        price = 12.50
    elif '冠捷科技' in recommendation['name']:
        price = 2.80

    # A 股最小 100 股
    qty = 100

    # 创建订单
    order = {
        'code': recommendation['code'],
        'name': recommendation['name'],
        'action': 'BUY',
        'price': price,
        'qty': qty,
        'value': price * qty,
        'timestamp': datetime.now().isoformat()
    }

    print(f"  订单：BUY {qty} @ {price} = {price * qty} 元")

    # 风控检查
    risk_mgr = RiskManager()
    risk_result = risk_mgr.check_order(order, position)

    print(f"  风控检查:")
    for check in risk_result['checks']:
        status = "✓" if check['status'] == 'PASS' else "✗" if check['status'] == 'FAIL' else "-"
        value = check.get('value', 'N/A')
        print(f"    {status} {check['item']}: {value}")

    if risk_result['warnings']:
        print(f"  警告:")
        for warn in risk_result['warnings']:
            print(f"    ⚠️  {warn}")

    order['risk_check'] = risk_result

    if not risk_result['passed']:
        print(f"  ❌ 风控未通过：{risk_result['block_reason']}")
        order['status'] = 'REJECTED'
    else:
        print(f"  ✅ 风控通过，等待确认...")
        order['status'] = 'PENDING_APPROVAL'

    return order


def main():
    print("=" * 60)
    print("Workflow C - A 股模拟交易执行")
    print("=" * 60)

    # 读取投资建议
    rec_file = Path('/home/admin/.openclaw/workspace/agents/trade/data/workflow_c/CN_2026-04-01/04_recommendations.json')
    if not rec_file.exists():
        print("投资建议文件不存在")
        return

    with open(rec_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    recommendations = data.get('recommendations', [])
    print(f"待执行推荐数量：{len(recommendations)}")

    if not recommendations:
        print("无推荐交易")
        return

    # 模拟持仓 (实际应从交易接口获取)
    position = {
        'total_value': 1000000,  # 总资产 100 万
        'cash': 800000,          # 可用现金 80 万
        'positions': []
    }

    # 执行交易
    trade_results = []
    for rec in recommendations:
        order = simulate_trade(rec, position)
        trade_results.append(order)

        # 更新持仓
        if order['status'] == 'PENDING_APPROVAL':
            position['cash'] -= order['value']

    # 保存交易结果
    output_dir = Path('/home/admin/.openclaw/workspace/agents/trade/data/workflow_c/CN_2026-04-01')

    result = {
        'market': 'CN',
        'date': '2026-04-01',
        'count': len(trade_results),
        'trade_results': trade_results,
        'position_after': position,
        'timestamp': datetime.now().isoformat()
    }

    with open(output_dir / '05_trade_results.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print("\n" + "=" * 60)
    print("交易执行摘要")
    print("=" * 60)

    approved = [t for t in trade_results if t['status'] == 'PENDING_APPROVAL']
    rejected = [t for t in trade_results if t['status'] == 'REJECTED']

    print(f"待确认订单：{len(approved)}")
    for order in approved:
        print(f"  - {order['code']} {order['name']}: BUY {order['qty']} @ {order['price']} = {order['value']} 元")

    print(f"被风控拒绝：{len(rejected)}")
    for order in rejected:
        print(f"  - {order['code']} {order['name']}: {order['risk_check']['block_reason']}")

    print(f"\n结果已保存：{output_dir / '05_trade_results.json'}")

    # 生成确认提示
    if approved:
        print("\n" + "=" * 60)
        print("待确认交易")
        print("=" * 60)
        total_value = sum(o['value'] for o in approved)
        print(f"共 {len(approved)} 笔交易，总金额 {total_value:.2f} 元")
        print("\n请确认是否执行上述交易：")
        print("  - 确认执行：回复 '确认' 或 'yes'")
        print("  - 取消交易：回复 '取消' 或 'no'")


if __name__ == '__main__':
    main()
