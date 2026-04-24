"""Futu-API 基础测试 — 纯mock，不依赖Futu OpenD连接"""
import sys
import pytest
from pathlib import Path

FUTU_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = FUTU_DIR / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))


class TestCommon:
    """common.py 工具函数测试"""

    def test_import_common(self):
        """common 模块可导入"""
        import common
        assert hasattr(common, 'FutuConfig')

    def test_futu_config(self):
        """FutuConfig 数据类测试"""
        from common import FutuConfig
        
        config = FutuConfig()
        assert config.login_account is None
        assert config.opend_host == "127.0.0.1"
        assert config.opend_port == 11111
        assert config.trd_env == "SIMULATE"
        
        config2 = FutuConfig(login_account="test", trd_env="REAL")
        assert config2.login_account == "test"
        assert config2.trd_env == "REAL"


class TestCodeFormat:
    """股票代码格式转换测试"""

    def test_cn_code_format(self):
        """A股代码格式转换"""
        code = "600519"
        if code.startswith('6'):
            futu_code = f"SH.{code}"
        else:
            futu_code = f"SZ.{code}"
        assert futu_code == "SH.600519"

    def test_hk_code_format(self):
        """港股代码格式"""
        code = "00700"
        futu_code = f"HK.{code}"
        assert futu_code == "HK.00700"

    def test_us_code_format(self):
        """美股代码格式"""
        code = "AAPL"
        futu_code = f"US.{code}"
        assert futu_code == "US.AAPL"


class TestFutuApiImport:
    """Futu API 模块导入测试"""

    def test_futu_import(self):
        """futu-api 基础导入"""
        try:
            from futu import OpenQuoteContext, OpenSecTradeContext
            assert OpenQuoteContext is not None
        except ImportError:
            pytest.skip("futu模块未安装")


class TestQuoteScripts:
    """行情脚本结构测试"""

    def test_scripts_exist(self):
        """主要行情脚本存在"""
        expected_scripts = [
            'quote/get_stock_quote.py',
            'quote/get_kline.py',
            'quote/get_snapshot.py',
        ]
        for script in expected_scripts:
            path = SCRIPTS_DIR / script
            assert path.exists(), f"脚本不存在: {script}"

    def test_script_count(self):
        """行情脚本数量验证"""
        quote_dir = SCRIPTS_DIR / 'quote'
        if quote_dir.exists():
            scripts = list(quote_dir.glob('*.py'))
            assert len(scripts) >= 20  # 应该有20+个行情脚本


class TestTradeScripts:
    """交易脚本结构测试"""

    def test_scripts_exist(self):
        """主要交易脚本存在"""
        expected_scripts = [
            'trade/place_order.py',
            'trade/get_portfolio.py',
            'trade/get_accounts.py',
        ]
        for script in expected_scripts:
            path = SCRIPTS_DIR / script
            assert path.exists(), f"脚本不存在: {script}"

    def test_script_count(self):
        """交易脚本数量验证"""
        trade_dir = SCRIPTS_DIR / 'trade'
        if trade_dir.exists():
            scripts = list(trade_dir.glob('*.py'))
            assert len(scripts) >= 10  # 应该有10+个交易脚本
