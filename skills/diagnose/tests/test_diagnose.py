"""Diagnose 基础测试 — 纯mock，不依赖Futu/LLM"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

DIAGNOSE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(DIAGNOSE_DIR))


class TestNormalizeCode:
    """股票代码规范化测试"""

    def test_sh_code(self):
        from diagnose import _normalize_code_for_workflow_b
        code, market = _normalize_code_for_workflow_b("SH.600519")
        assert code == "600519"
        assert market == "A"

    def test_sz_code(self):
        from diagnose import _normalize_code_for_workflow_b
        code, market = _normalize_code_for_workflow_b("SZ.000001")
        assert code == "000001"
        assert market == "A"

    def test_hk_code(self):
        from diagnose import _normalize_code_for_workflow_b
        code, market = _normalize_code_for_workflow_b("HK.00700")
        assert code == "00700"
        assert market == "HK"

    def test_us_code(self):
        from diagnose import _normalize_code_for_workflow_b
        code, market = _normalize_code_for_workflow_b("US.AAPL")
        assert code == "US.AAPL"
        assert market == "US"

    def test_empty_code(self):
        from diagnose import _normalize_code_for_workflow_b
        code, market = _normalize_code_for_workflow_b("")
        assert code == ""


class TestSignalConstants:
    """调仓信号常量测试"""

    def test_signals_exist(self):
        from diagnose import SIGNAL_HOLD, SIGNAL_ADD, SIGNAL_REDUCE, SIGNAL_CLEAR, SIGNAL_SKIP
        assert SIGNAL_HOLD == "HOLD"
        assert SIGNAL_ADD == "ADD"
        assert SIGNAL_REDUCE == "REDUCE"
        assert SIGNAL_CLEAR == "CLEAR"
        assert SIGNAL_SKIP == "SKIP"

    def test_all_signals_list(self):
        from diagnose import ALL_SIGNALS
        assert len(ALL_SIGNALS) == 5
        assert "HOLD" in ALL_SIGNALS
        assert "ADD" in ALL_SIGNALS


class TestWorkflowDHandler:
    """WorkflowDHandler 模块测试"""

    def test_import(self):
        from diagnose import WorkflowDHandler
        assert WorkflowDHandler is not None

    def test_determine_signal_hold(self):
        """评估良好应持有"""
        from diagnose import WorkflowDHandler, SIGNAL_HOLD
        handler = WorkflowDHandler(market='CN', account_id=18767295)
        
        signal, reason = handler._determine_signal(
            code="600519",
            pl_ratio=5.0,
            weight=0.08,
            diag_status="success",
            wb_signal="持有",
            has_violation=False,
            data_quality="good"
        )
        assert signal == SIGNAL_HOLD

    def test_determine_signal_clear(self):
        """评估差应清仓"""
        from diagnose import WorkflowDHandler, SIGNAL_CLEAR
        handler = WorkflowDHandler(market='CN', account_id=18767295)
        
        signal, reason = handler._determine_signal(
            code="600519",
            pl_ratio=-20.0,
            weight=0.08,
            diag_status="success",
            wb_signal="强烈卖出",
            has_violation=False,
            data_quality="good"
        )
        assert signal == SIGNAL_CLEAR

    def test_determine_signal_skip(self):
        """数据不足应跳过"""
        from diagnose import WorkflowDHandler, SIGNAL_SKIP
        handler = WorkflowDHandler(market='CN', account_id=18767295)
        
        signal, reason = handler._determine_signal(
            code="600519",
            pl_ratio=0,
            weight=0.08,
            diag_status="error",
            wb_signal="",
            has_violation=False,
            data_quality="degraded"
        )
        assert signal == SIGNAL_SKIP

    def test_determine_signal_reduce(self):
        """风控违规应减仓"""
        from diagnose import WorkflowDHandler, SIGNAL_REDUCE
        handler = WorkflowDHandler(market='CN', account_id=18767295)
        
        signal, reason = handler._determine_signal(
            code="600519",
            pl_ratio=-5.0,
            weight=0.08,
            diag_status="success",
            wb_signal="持有",
            has_violation=True,
            data_quality="good"
        )
        assert signal == SIGNAL_REDUCE

    def test_calculate_target_weight(self):
        """目标权重计算"""
        from diagnose import WorkflowDHandler, SIGNAL_HOLD, SIGNAL_CLEAR
        handler = WorkflowDHandler(market='CN', account_id=18767295)
        
        assert handler._calculate_target_weight(SIGNAL_HOLD, 0.10) == 0.10
        assert handler._calculate_target_weight(SIGNAL_CLEAR, 0.10) == 0.0
        assert handler._calculate_target_weight("REDUCE", 0.10) == 0.05


class TestMarketAccounts:
    """市场账户映射测试"""

    def test_market_accounts(self):
        from diagnose import MARKET_ACCOUNTS
        assert 'CN' in MARKET_ACCOUNTS
        assert 'HK' in MARKET_ACCOUNTS
        assert 'US' in MARKET_ACCOUNTS
        assert isinstance(MARKET_ACCOUNTS['CN'], int)
