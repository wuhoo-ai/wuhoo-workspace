"""Debate 系统核心测试"""
import sys
from pathlib import Path

DEBATE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(DEBATE_DIR))

from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent
from agents.risk_agent import RiskAgent
from protocols.debate_protocol import DebateProtocol


class TestDebateAgents:
    """Debate Agent 基础测试"""

    def test_bull_agent_init(self):
        """Bull Agent 可初始化"""
        agent = BullAgent()
        assert agent is not None

    def test_bear_agent_init(self):
        """Bear Agent 可初始化"""
        agent = BearAgent()
        assert agent is not None

    def test_trader_agent_init(self):
        """Trader Agent 可初始化"""
        agent = TraderAgent()
        assert agent is not None

    def test_risk_agent_init(self):
        """Risk Agent 可初始化"""
        agent = RiskAgent()
        assert agent is not None

    def test_debate_protocol(self):
        """辩论协议可初始化"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            protocol = DebateProtocol(data_dir=tmpdir)
            assert protocol is not None
            protocol.start_debate("TEST.ST")
            assert protocol.state == "ongoing"


class TestDataAggregator:
    """Data Aggregator 测试"""

    def test_import(self):
        """DataAggregator 可导入"""
        from adapters.data_aggregator import DataAggregator
        agg = DataAggregator()
        assert agg is not None

    def test_mock_data(self):
        """模拟数据聚合"""
        from adapters.data_aggregator import DataAggregator
        agg = DataAggregator()
        # 即使数据源不可用，也应该返回结构
        data = agg.get_all_data("600519", "贵州茅台")
        assert isinstance(data, dict)
        assert "data_quality" in data


class TestAdapters:
    """适配器测试"""

    def test_akshare_adapter_import(self):
        """AkShare 适配器可导入"""
        from adapters.akshare_adapter import AkShareAdapter
        assert AkShareAdapter is not None

    def test_data_aggregator_import(self):
        """Data Aggregator 可导入"""
        from adapters.data_aggregator import DataAggregator
        assert DataAggregator is not None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
