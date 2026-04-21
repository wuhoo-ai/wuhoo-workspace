"""风控模块测试"""
import sys
from pathlib import Path

TRADE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(TRADE_DIR))


class TestRiskManager:
    """风控测试"""

    def test_import(self):
        """测试 risk_manager 可导入"""
        from risk_manager import RiskManager
        mgr = RiskManager()
        assert mgr is not None

    def test_single_position_limit(self):
        """测试单股仓位限制 (≤20%)"""
        from risk_manager import RiskManager
        mgr = RiskManager()
        result = mgr.check({
            "code": "600519",
            "action": "BUY",
            "price": 1500,
            "quantity": 100,
            "position_ratio": 0.25,  # 25% > 20%
        })
        assert not result["passed"]

    def test_normal_position(self):
        """测试正常仓位"""
        from risk_manager import RiskManager
        mgr = RiskManager()
        result = mgr.check({
            "code": "600519",
            "action": "BUY",
            "price": 1500,
            "quantity": 100,
            "position_ratio": 0.10,  # 10% < 20%
        })
        assert result["passed"]


class TestPortfolioMetrics:
    """组合指标测试"""

    def test_import(self):
        """测试 portfolio_metrics 可导入"""
        from portfolio_metrics import calculate_sharpe_ratio
        assert callable(calculate_sharpe_ratio)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
