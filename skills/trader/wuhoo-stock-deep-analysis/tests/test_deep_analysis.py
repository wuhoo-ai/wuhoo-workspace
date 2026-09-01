"""Deep-Analysis 基础测试 — 纯mock，不依赖真实LLM/网络"""
import sys
import pytest
from pathlib import Path

DA_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(DA_DIR))


class TestSafeConverters:
    """安全转换函数测试"""

    def test_safe_float_valid(self):
        from deep_analysis import safe_float
        assert safe_float("123.45") == 123.45
        assert safe_float(100) == 100.0
        assert safe_float("50%") == 50.0

    def test_safe_float_invalid(self):
        from deep_analysis import safe_float
        assert safe_float(None) is None
        assert safe_float("") is None
        assert safe_float("--") is None
        assert safe_float("N/A") is None
        assert safe_float("abc") is None

    def test_safe_float_nan_inf(self):
        from deep_analysis import safe_float
        import math
        assert safe_float(float('nan')) is None
        assert safe_float(float('inf')) is None


class TestAkshareFetcher:
    """AkshareFetcher 模块测试"""

    def test_import(self):
        from deep_analysis import AkshareFetcher
        f = AkshareFetcher()
        # akshare 可能未安装，但不能 crash
        assert hasattr(f, 'is_available')
        assert hasattr(f, 'fetch_all')

    def test_not_available_returns_error(self):
        from deep_analysis import AkshareFetcher
        f = AkshareFetcher()
        if not f.is_available():
            result = f.fetch_all("600519", "贵州茅台")
            assert "error" in result or "available" in result


class TestFactorDataLoader:
    """FactorDataLoader 模块测试"""

    def test_import(self):
        from deep_analysis import FactorDataLoader
        loader = FactorDataLoader()
        assert hasattr(loader, 'is_available')
        assert hasattr(loader, 'load_all')


class TestDebateRunner:
    """DebateRunner 模块测试"""

    def test_import(self):
        from deep_analysis import DebateRunner
        runner = DebateRunner()
        assert hasattr(runner, 'is_available')
        assert hasattr(runner, 'run')

    def test_quick_analysis_from_akshare(self):
        from deep_analysis import DebateRunner
        runner = DebateRunner()
        
        # 模拟低PE高ROE数据（应该看多）
        ak_data = {
            "basic": {"pe_ttm": "15", "market_cap": "10000000000"},
            "indicators": [{"指标": "加权净资产收益率(%)", "2024": "20.5"}]
        }
        result = runner._quick_analysis_from_akshare(ak_data)
        assert "recommendation" in result
        assert "bull_points" in result
        assert "bear_points" in result

    def test_quick_analysis_high_pe(self):
        from deep_analysis import DebateRunner
        runner = DebateRunner()
        
        # 模拟高PE数据（应该看空）
        ak_data = {
            "basic": {"pe_ttm": "80", "market_cap": "10000000000"},
            "indicators": []
        }
        result = runner._quick_analysis_from_akshare(ak_data)
        assert any("估值偏高" in p for p in result["bear_points"])


class TestFinancialAnalyzer:
    """FinancialAnalyzer 模块测试"""

    def test_debt_analysis_low_debt(self):
        from deep_analysis import FinancialAnalyzer
        data = {
            'balance': [
                {'资产总计': 1000000, '负债合计': 300000, 'REPORT_DATE_NAME': '2024Q4'},
                {'资产总计': 900000, '负债合计': 280000, 'REPORT_DATE_NAME': '2023Q4'},
            ],
            'indicators': []
        }
        analyzer = FinancialAnalyzer(data)
        result = analyzer.analyze_debt()
        assert "稳健" in result["assessment"] or "可控" in result["assessment"]
        assert result["trend"][0]["debt_ratio"] == 0.3

    def test_debt_analysis_high_debt(self):
        from deep_analysis import FinancialAnalyzer
        data = {
            'balance': [
                {'资产总计': 1000000, '负债合计': 850000, 'REPORT_DATE_NAME': '2024Q4'},
            ],
            'indicators': []
        }
        analyzer = FinancialAnalyzer(data)
        result = analyzer.analyze_debt()
        assert "过高" in result["assessment"] or "较大" in result["assessment"]
        assert "80%" in " ".join(result["alerts"])

    def test_profitability_excellent(self):
        from deep_analysis import FinancialAnalyzer
        data = {
            'balance': [],
            'indicators': [
                {'加权净资产收益率(%)': 25, '销售毛利率(%)': 60, '销售净利率(%)': 30, '日期': '2024'},
                {'加权净资产收益率(%)': 22, '销售毛利率(%)': 58, '销售净利率(%)': 28, '日期': '2023'},
                {'加权净资产收益率(%)': 20, '销售毛利率(%)': 55, '销售净利率(%)': 25, '日期': '2022'},
            ]
        }
        analyzer = FinancialAnalyzer(data)
        result = analyzer.analyze_profitability()
        assert "优秀" in result["assessment"] or "强" in result["assessment"]
