"""Debate 系统核心测试 — 纯mock，不依赖真实LLM调用"""
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

DEBATE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(DEBATE_DIR))

from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent
from agents.risk_agent import RiskAgent
from protocols.debate_protocol import DebateProtocol


# Mock LLM 响应
MOCK_LLM_RESPONSE = json.dumps({
    "recommendation": "BUY",
    "confidence": 0.75,
    "target_price": 100.0,
    "stop_loss": 90.0,
    "position_size": 0.1
})


@pytest.fixture
def mock_llm():
    """Mock所有LLM调用"""
    with patch.object(BullAgent, '_call_llm', return_value=MOCK_LLM_RESPONSE) as bull_mock, \
         patch.object(BearAgent, '_call_llm', return_value=MOCK_LLM_RESPONSE) as bear_mock, \
         patch.object(TraderAgent, '_call_llm', return_value=MOCK_LLM_RESPONSE) as trader_mock, \
         patch.object(RiskAgent, '_call_llm', return_value=MOCK_LLM_RESPONSE) as risk_mock:
        yield {
            "bull": bull_mock,
            "bear": bear_mock,
            "trader": trader_mock,
            "risk": risk_mock
        }


class TestDebateAgents:
    """Debate Agent 基础测试"""

    def test_bull_agent_init(self):
        """Bull Agent 可初始化"""
        agent = BullAgent()
        assert agent is not None
        assert agent.name == "bull"

    def test_bear_agent_init(self):
        """Bear Agent 可初始化"""
        agent = BearAgent()
        assert agent is not None
        assert agent.name == "bear"

    def test_trader_agent_init(self):
        """Trader Agent 可初始化"""
        agent = TraderAgent()
        assert agent is not None
        assert agent.name == "trader"

    def test_risk_agent_init(self):
        """Risk Agent 可初始化"""
        agent = RiskAgent()
        assert agent is not None
        assert agent.name == "risk"

    def test_debate_protocol_init(self):
        """辩论协议可初始化"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            protocol = DebateProtocol(data_dir=tmpdir)
            assert protocol is not None
            assert protocol.state == "idle"

    def test_debate_protocol_lifecycle(self):
        """辩论协议完整生命周期（不依赖LLM）"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            protocol = DebateProtocol(data_dir=tmpdir)

            # 开始辩论
            record = protocol.start_debate("TEST.ST")
            assert protocol.state == "ongoing"
            assert record.symbol == "TEST.ST"

            # 提交各方观点
            bull_view = {"agent": "bull", "recommendation": "BUY", "confidence": 0.8, "stop_loss": 90.0, "target_price": 110.0}
            bear_view = {"agent": "bear", "recommendation": "SELL", "confidence": 0.6, "stop_loss": 85.0, "target_price": 80.0}
            trader_decision = {"agent": "trader", "decision": "HOLD"}
            risk_approval = {"agent": "risk", "recommendation": "APPROVE"}

            protocol.submit_bull_view(bull_view)
            protocol.submit_bear_view(bear_view)
            protocol.analyze_debate()
            protocol.submit_trader_decision(trader_decision)
            protocol.submit_risk_approval(risk_approval)

            # 完成辩论
            final = protocol.finalize("HOLD", "综合决策")
            assert final.final_action["action"] == "HOLD"
            assert protocol.state == "idle"

    def test_debate_with_mock_llm(self, mock_llm):
        """使用mock LLM的完整辩论流程"""
        bull = BullAgent()
        bear = BearAgent()
        trader = TraderAgent()
        risk = RiskAgent()

        # 调用analyze，确保mock生效
        result = bull.analyze("600519.SH", factor_data={"momentum": 8.5})
        assert "recommendation" in result
        assert result["agent"] == "bull"
        assert mock_llm["bull"].called

        result = bear.analyze("600519.SH", factor_data={"volatility": 25.0})
        assert result["agent"] == "bear"
        assert mock_llm["bear"].called

        # TraderAgent 使用 make_decision 而非 analyze
        result = trader.make_decision("600519.SH", bull_view={}, bear_view={})
        assert result["agent"] == "trader"
        assert mock_llm["trader"].called

        # RiskAgent 使用 review 而非 analyze
        result = risk.review("600519.SH", trader_decision={"target_price": 100}, market_data={})
        assert result["agent"] == "risk"
        assert "approved" in result


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
    pytest.main([__file__, "-v"])
