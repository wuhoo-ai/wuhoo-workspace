"""
Workflow B 审计模块测试
"""
import sys
from pathlib import Path

TRADE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(TRADE_DIR))

SKILL_DIR = Path.home() / 'wuhoo-skills' / 'wuhoo-stock-deep-analysis'
sys.path.insert(0, str(SKILL_DIR))

from workflow_b_audit import WorkflowBAudit, build_audit_context


class TestWorkflowBAudit:
    """Workflow B 审计测试"""

    def test_build_audit_context(self):
        """测试审计上下文构建"""
        ctx = build_audit_context(
            symbol="600519",
            name="贵州茅台",
            decision={"score": 7.5},
        )
        assert ctx["symbol"] == "600519"
        assert ctx["name"] == "贵州茅台"
        assert ctx["decision"]["score"] == 7.5

    def test_audit_with_mock_data(self):
        """测试 mock 数据审计"""
        ctx = build_audit_context(
            symbol="TEST",
            name="测试公司",
            akshare_data={},
            factor_data={},
            debate_data={},
            dcf_data={"available": False, "reason": "mock"},
            decision={"score": 5},
        )
        audit = WorkflowBAudit(ctx)
        result = audit.run()

        assert "reliability" in result
        assert "alerts" in result
        assert result["reliability"]["score"] >= 0
        assert result["reliability"]["score"] <= 100

    def test_audit_complete_data(self):
        """测试完整数据审计"""
        ctx = build_audit_context(
            symbol="600519",
            name="贵州茅台",
            akshare_data={
                "available": True,
                "basic": {"industry": "白酒", "pe_ttm": 35, "pb": 10},
                "indicators": [{"加权净资产收益率(%)": 25} for _ in range(4)],
                "income": [{"revenue": 100} for _ in range(3)],
                "cashflow": [{"ocf": 50}],
                "valuation_history": [],
                "holders": [],
                "dividend": [],
            },
            factor_data={"available": True},
            debate_data={
                "method": "full",
                "bull_points": ["品牌优势", "渠道扩张"],
                "bear_points": ["估值偏高"],
                "confidence": 70,
                "recommendation": "看多",
            },
            dcf_data={
                "available": True,
                "scenarios": {
                    "乐观": {"value_per_share": 2000},
                    "悲观": {"value_per_share": 1200},
                },
                "margin_of_safety": 25,
            },
            valuation_summary={
                "has_relative_valuation": True,
                "has_historical_valuation": True,
            },
            decision={"score": 7.5},
        )
        audit = WorkflowBAudit(ctx)
        result = audit.run()

        assert result["reliability"]["score"] >= 60
        critical = sum(1 for a in result["alerts"] if a["level"] == "CRITICAL")
        assert critical == 0

    def test_markdown_report(self):
        """测试 Markdown 报告生成"""
        ctx = build_audit_context(symbol="TEST", name="测试")
        audit = WorkflowBAudit(ctx)
        result = audit.run()
        md = audit.generate_markdown(result)
        assert "审计报告" in md
        assert "可靠性得分" in md


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
