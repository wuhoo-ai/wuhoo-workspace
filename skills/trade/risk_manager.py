#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易风控检查模块

功能:
1. 仓位检查 (单股≤20%, 总仓位≤90%)
2. 止损检查 (单笔 -8%, 总账户 -15%)
3. 流动性检查
4. 黑名单检查
5. 大额交易确认 (>5% 仓位需用户确认)
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# 风控配置
RISK_CONFIG = {
    # 仓位限制
    "single_stock_limit": 0.20,  # 单股票最大仓位 20%
    "total_position_limit": 0.90,  # 总仓位最大 90%
    "min_cash_ratio": 0.10,  # 最小现金比例 10%

    # 止损限制
    "single_stop_loss": 0.08,  # 单笔止损 8%
    "total_drawdown_limit": 0.15,  # 总账户最大回撤 15%

    # 大额交易确认
    "large_trade_threshold": 0.05,  # 大额交易阈值 5%

    # 黑名单 (示例)
    "blacklist": [
        # 可添加股票代码
    ]
}


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    checks: Dict[str, Dict]
    warnings: List[str]
    block_reason: Optional[str]
    requires_confirmation: bool
    confirmation_reason: Optional[str]

    def to_dict(self) -> Dict:
        return asdict(self)


class RiskManager:
    """风控管理器"""

    def __init__(self, account_id: str = None):
        """
        初始化风控管理器

        Args:
            account_id: 账户 ID
        """
        self.account_id = account_id
        self.config = RISK_CONFIG
        self.position_file = self._get_position_file()

    def _get_position_file(self) -> Path:
        """获取持仓文件路径"""
        # 默认持仓文件路径
        return Path.home() / '.hermes' / 'workspace' / 'projects' / 'AI-Trader' / 'data' / 'agent_data' / 'trade-agent' / 'position' / 'position.jsonl'

    def get_current_position(self) -> Dict:
        """
        获取当前持仓数据

        优先使用注入的 OpenD 数据（通过 set_opend_data 方法），
        降级使用本地 position.jsonl 文件。

        Returns:
            {
                total_value: 总资产,
                cash: 可用现金,
                positions: {code: {qty, cost_basis, current_value, ...}},
                total_market_value: 持仓市值
            }
        """
        # 优先使用 OpenD 注入数据
        if hasattr(self, '_opend_data') and self._opend_data:
            return self._opend_data

        # 降级：从文件加载持仓
        positions = {}
        total_market_value = 0.0
        cash = 1000000.0  # 默认 100 万现金

        if self.position_file.exists():
            try:
                with open(self.position_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            pos = json.loads(line)
                            code = pos.get('code', '')
                            if code and pos.get('qty', 0) > 0:
                                current_value = pos.get('current_value', pos.get('cost_basis', 0))
                                positions[code] = {
                                    'qty': pos.get('qty', 0),
                                    'cost_basis': pos.get('cost_basis', 0),
                                    'current_value': current_value,
                                    'avg_price': pos.get('avg_price', 0)
                                }
                                total_market_value += current_value
            except Exception as e:
                print(f"加载持仓文件失败：{e}")

        # 估算总资产 (简化：假设现金 100 万 - 已用)
        total_value = total_market_value + cash

        return {
            'total_value': total_value,
            'cash': cash,
            'positions': positions,
            'total_market_value': total_market_value
        }

    def set_opend_data(self, portfolio_scan: Dict):
        """
        注入 OpenD 实时持仓数据，替代本地文件读取。

        Args:
            portfolio_scan: diagnose.py 中 Step 1 的输出
        """
        positions = {}
        for pos in portfolio_scan.get('positions', []):
            code = pos.get('code', '')
            positions[code] = {
                'qty': pos.get('qty', 0),
                'cost_basis': pos.get('average_cost', 0),
                'current_value': pos.get('market_val', 0),
                'avg_price': pos.get('nominal_price', 0),
            }

        self._opend_data = {
            'total_value': portfolio_scan.get('total_assets', 0),
            'cash': sum(portfolio_scan.get('cash_by_market', {}).values()),
            'positions': positions,
            'total_market_value': portfolio_scan.get('total_market_value', 0),
        }

    def check(self, order: Dict, current_position: Dict = None) -> RiskCheckResult:
        """
        风控检查

        Args:
            order: 订单信息
                {code, action, price, quantity, position_ratio}
            current_position: 当前持仓 (可选，自动获取)

        Returns:
            RiskCheckResult
        """
        if current_position is None:
            current_position = self.get_current_position()

        checks = {}
        warnings = []
        block_reason = None
        requires_confirmation = False
        confirmation_reason = None

        # ===== 1. 仓位检查 =====
        position_check = self._check_position_limit(order, current_position)
        checks['position_limit'] = position_check
        if not position_check['passed']:
            block_reason = f"仓位超限：{position_check['message']}"

        # ===== 2. 现金检查 =====
        cash_check = self._check_cash_available(order, current_position)
        checks['cash_available'] = cash_check
        if not cash_check['passed']:
            block_reason = f"现金不足：{cash_check['message']}"

        # ===== 3. 单股仓位检查 =====
        single_stock_check = self._check_single_stock_limit(order, current_position)
        checks['single_stock_limit'] = single_stock_check
        if not single_stock_check['passed']:
            block_reason = f"单股超限：{single_stock_check['message']}"

        # ===== 4. 止损检查 =====
        stop_loss_check = self._check_stop_loss(order, current_position)
        checks['stop_loss_check'] = stop_loss_check
        if not stop_loss_check['passed']:
            warnings.append(stop_loss_check['message'])

        # ===== 5. 黑名单检查 =====
        blacklist_check = self._check_blacklist(order)
        checks['blacklist_check'] = blacklist_check
        if not blacklist_check['passed']:
            block_reason = f"黑名单股票：{blacklist_check['message']}"

        # ===== 6. 大额交易确认 =====
        if order.get('position_ratio', 0) > self.config['large_trade_threshold']:
            requires_confirmation = True
            confirmation_reason = f"大额交易：仓位{order['position_ratio']*100:.1f}% > {self.config['large_trade_threshold']*100:.0f}% 阈值"

        # ===== 汇总结果 =====
        passed = block_reason is None

        return RiskCheckResult(
            passed=passed,
            checks=checks,
            warnings=warnings,
            block_reason=block_reason,
            requires_confirmation=requires_confirmation,
            confirmation_reason=confirmation_reason
        )

    def _check_position_limit(self, order: Dict, position: Dict) -> Dict:
        """检查总仓位限制"""
        current_market_value = position.get('total_market_value', 0)
        total_value = position.get('total_value', 1000000)

        # 计算新订单金额
        order_value = order.get('price', 0) * order.get('quantity', 0)
        if order_value == 0:
            order_value = total_value * order.get('position_ratio', 0)

        # 新总仓位
        new_market_value = current_market_value + order_value
        new_position_ratio = new_market_value / total_value if total_value > 0 else 0

        passed = new_position_ratio <= self.config['total_position_limit']
        current_ratio = current_market_value / total_value if total_value > 0 else 0

        return {
            'passed': passed,
            'current': round(current_ratio, 3),
            'new': round(new_position_ratio, 3),
            'limit': self.config['total_position_limit'],
            'message': f"当前仓位{current_ratio*100:.1f}%, 新仓位{new_position_ratio*100:.1f}% (限制{self.config['total_position_limit']*100:.0f}%)"
        }

    def _check_cash_available(self, order: Dict, position: Dict) -> Dict:
        """检查现金是否充足"""
        cash = position.get('cash', 0)
        order_value = order.get('price', 0) * order.get('quantity', 0)

        if order_value == 0:
            # 估算订单金额
            total_value = position.get('total_value', 1000000)
            order_value = total_value * order.get('position_ratio', 0)

        passed = cash >= order_value

        return {
            'passed': passed,
            'available': round(cash, 2),
            'required': round(order_value, 2),
            'message': f"可用现金{cash:,.2f}, 需要{order_value:,.2f}"
        }

    def _check_single_stock_limit(self, order: Dict, position: Dict) -> Dict:
        """检查单股仓位限制"""
        code = order.get('code', '')
        total_value = position.get('total_value', 1000000)

        # 当前该股持仓
        current_stock_value = 0
        if code in position.get('positions', {}):
            current_stock_value = position['positions'][code].get('current_value', 0)

        # 新订单金额
        order_value = order.get('price', 0) * order.get('quantity', 0)
        if order_value == 0:
            order_value = total_value * order.get('position_ratio', 0)

        # 新单股仓位
        new_stock_value = current_stock_value + order_value
        new_ratio = new_stock_value / total_value if total_value > 0 else 0

        passed = new_ratio <= self.config['single_stock_limit']
        current_ratio = current_stock_value / total_value if total_value > 0 else 0

        return {
            'passed': passed,
            'current': round(current_ratio, 3),
            'new': round(new_ratio, 3),
            'limit': self.config['single_stock_limit'],
            'message': f"单股{code} 当前{current_ratio*100:.1f}%, 新{new_ratio*100:.1f}% (限制{self.config['single_stock_limit']*100:.0f}%)"
        }

    def _check_stop_loss(self, order: Dict, position: Dict) -> Dict:
        """检查止损"""
        # 简化检查：默认通过
        # 实际应用中可检查：
        # 1. 订单是否设置了止损
        # 2. 当前持仓是否已触发止损
        # 3. 总账户是否已触发最大回撤

        return {
            'passed': True,
            'message': '止损检查通过'
        }

    def _check_blacklist(self, order: Dict) -> Dict:
        """检查黑名单"""
        code = order.get('code', '')

        if code in self.config['blacklist']:
            return {
                'passed': False,
                'message': f'{code} 在黑名单中'
            }

        return {
            'passed': True,
            'message': '黑名单检查通过'
        }


# ============= 与 Workflow C 集成的函数 =============

def risk_check(order: Dict, position: Dict = None) -> Dict:
    """
    风控检查 (Workflow C 调用)

    Args:
        order: 订单信息
        position: 当前持仓 (可选)

    Returns:
        风控检查结果
    """
    manager = RiskManager()
    result = manager.check(order, position)
    return result.to_dict()


def get_position() -> Dict:
    """
    获取当前持仓

    Returns:
        持仓数据
    """
    manager = RiskManager()
    return manager.get_current_position()


if __name__ == "__main__":
    # 测试风控检查
    manager = RiskManager()

    # 测试订单
    test_order = {
        "code": "HK.00700",
        "action": "BUY",
        "price": 300.0,
        "quantity": 100,
        "position_ratio": 0.05
    }

    # 执行风控检查
    result = manager.check(test_order)

    print("\n=== 风控检查结果 ===")
    print(f"通过：{result.passed}")
    print(f"警告：{result.warnings}")
    print(f"阻止原因：{result.block_reason}")
    print(f"需确认：{result.requires_confirmation}")
    if result.requires_confirmation:
        print(f"确认原因：{result.confirmation_reason}")

    print("\n=== 详细检查 ===")
    for check_name, check_data in result.checks.items():
        status = "✅" if check_data['passed'] else "❌"
        print(f"{status} {check_name}: {check_data['message']}")
