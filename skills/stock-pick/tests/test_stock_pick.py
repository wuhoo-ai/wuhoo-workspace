#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stock_pick.py 单元测试

覆盖:
- 日期解析 (YYYY-MM-DD / YYYYMMDD)
- 分位筛选逻辑
- 空数据降级
- Top-N 排序
- 因子配置加载
- 选股函数 (A股/港股/美股)
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

# 导入被测模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import stock_pick as sp


# ============================================================
# 1. 日期解析
# ============================================================

class TestParseDate:
    def test_yyyy_mm_dd(self):
        dt = sp.parse_date('2026-04-15')
        assert dt == datetime(2026, 4, 15)

    def test_yyyymmdd(self):
        dt = sp.parse_date('20260415')
        assert dt == datetime(2026, 4, 15)

    def test_invalid(self):
        with pytest.raises(ValueError):
            sp.parse_date('not-a-date')


class TestFormatDate:
    def test_format(self):
        assert sp.format_date(datetime(2026, 4, 15)) == '20260415'


# ============================================================
# 2. 分位筛选 — get_percentile / get_top_n / get_sort_config
# ============================================================

class TestPercentileDefaults:
    def test_residual_vol(self):
        assert sp.get_percentile('residual_vol', 'cn') == 0.50

    def test_turnover(self):
        assert sp.get_percentile('turnover_5d', 'cn') == 0.50

    def test_momentum_5d(self):
        assert sp.get_percentile('momentum_5d', 'cn') == 0.30

    def test_beta(self):
        assert sp.get_percentile('beta_20d', 'cn') == 0.30

    def test_volatility_hk(self):
        assert sp.get_percentile('volatility', 'hk') == 0.50


class TestTopN:
    def test_default(self):
        sp.FACTOR_CONFIG = {}
        assert sp.get_top_n() == 10


class TestSortConfig:
    def test_default(self):
        sp.FACTOR_CONFIG = {}
        cfg = sp.get_sort_config('cn')
        assert cfg == {'factor': 'momentum_10d', 'ascending': True}

    def test_custom(self):
        sp.FACTOR_CONFIG = {'cn': {'sort_factor': 'residual_vol', 'sort_ascending': True}}
        cfg = sp.get_sort_config('cn')
        assert cfg['factor'] == 'residual_vol'
        sp.FACTOR_CONFIG = {}  # cleanup


# ============================================================
# 3. JSON 因子配置加载
# ============================================================

class TestLoadFactorsConfig:
    def test_load_from_file(self):
        sp.FACTOR_CONFIG = {}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'cn': {'top_n': 5, 'percentiles': {'residual_vol': 0.40}}}, f)
            f.flush()
            sp.load_factors_config(f.name)
        assert sp.FACTOR_CONFIG['cn']['top_n'] == 5
        assert sp.FACTOR_CONFIG['cn']['percentiles']['residual_vol'] == 0.40
        os.unlink(f.name)
        sp.FACTOR_CONFIG = {}

    def test_nonexistent_file(self):
        sp.FACTOR_CONFIG = {}
        result = sp.load_factors_config('/nonexistent/path.json')
        # Should return empty or unchanged FACTOR_CONFIG
        assert result == {}
        sp.FACTOR_CONFIG = {}


# ============================================================
# 4. 选股函数 — select_stocks (A 股完整因子)
# ============================================================

class TestSelectStocks:
    def _make_df(self, n=100):
        np.random.seed(42)
        return pd.DataFrame({
            'ts_code': [f'{i:06d}.SH' for i in range(n)],
            'name': [f'股票{i}' for i in range(n)],
            'residual_vol': np.random.uniform(10, 40, n),
            'turnover_5d': np.random.uniform(0.5, 15, n),
            'momentum_5d': np.random.uniform(-20, 30, n),
            'beta_20d': np.random.uniform(0.3, 2.5, n),
            'momentum_10d': np.random.uniform(-15, 25, n),
        })

    def test_normal_flow(self):
        sp.FACTOR_CONFIG = {}
        df = self._make_df(200)
        result = sp.select_stocks(df, has_turnover=True)
        assert len(result) <= 10
        assert 'ts_code' in result.columns
        assert 'momentum_10d' in result.columns

    def test_custom_top_n(self):
        sp.FACTOR_CONFIG = {'cn': {'top_n': 5}}
        df = self._make_df(200)
        result = sp.select_stocks(df, has_turnover=True)
        assert len(result) <= 5
        sp.FACTOR_CONFIG = {}

    def test_custom_percentiles(self):
        sp.FACTOR_CONFIG = {'cn': {
            'percentiles': {
                'residual_vol': 0.80,
                'turnover_5d': 0.80,
                'momentum_5d': 0.60,
                'beta_20d': 0.60,
            }
        }}
        df = self._make_df(200)
        result = sp.select_stocks(df, has_turnover=True)
        # 宽松阈值应该保留更多股票
        assert len(result) <= 10
        sp.FACTOR_CONFIG = {}

    def test_empty_input(self):
        sp.FACTOR_CONFIG = {}
        df = pd.DataFrame()
        result = sp.select_stocks(df, has_turnover=True)
        assert result.empty

    def test_too_strict_percentile(self):
        sp.FACTOR_CONFIG = {'cn': {
            'percentiles': {
                'residual_vol': 0.01,
                'turnover_5d': 0.01,
                'momentum_5d': 0.01,
                'beta_20d': 0.01,
            }
        }}
        df = self._make_df(50)
        result = sp.select_stocks(df, has_turnover=True)
        # 极严格阈值可能选出 0 只
        assert len(result) <= 10
        sp.FACTOR_CONFIG = {}

    def test_no_turnover_proxy(self):
        sp.FACTOR_CONFIG = {}
        df = self._make_df(200)
        result = sp.select_stocks(df, has_turnover=False)
        assert len(result) <= 10


# ============================================================
# 5. 选股函数 — select_stocks_simple (港股简化因子)
# ============================================================

class TestSelectStocksSimple:
    def _make_df(self, n=100):
        np.random.seed(42)
        return pd.DataFrame({
            'ts_code': [f'HK.{i:05d}' for i in range(n)],
            'name': [f'港股{i}' for i in range(n)],
            'volatility': np.random.uniform(15, 50, n),
            'momentum_5d': np.random.uniform(-20, 30, n),
            'momentum_10d': np.random.uniform(-15, 25, n),
        })

    def test_normal(self):
        sp.FACTOR_CONFIG = {}
        df = self._make_df(100)
        result = sp.select_stocks_simple(df, market='hk')
        assert len(result) <= 10
        assert 'ts_code' in result.columns

    def test_empty(self):
        sp.FACTOR_CONFIG = {}
        df = pd.DataFrame()
        result = sp.select_stocks_simple(df, market='hk')
        assert result.empty


# ============================================================
# 6. 选股函数 — select_stocks_us_complete (美股完整因子)
# ============================================================

class TestSelectStocksUSComplete:
    def _make_df(self, n=100):
        np.random.seed(42)
        return pd.DataFrame({
            'ts_code': [f'{chr(65+i)}.US' for i in range(n)],
            'name': [f'US Stock {i}' for i in range(n)],
            'residual_vol': np.random.uniform(10, 40, n),
            'turnover_5d': np.random.uniform(5, 20, n),
            'momentum_5d': np.random.uniform(-20, 30, n),
            'beta_20d': np.random.uniform(0.3, 2.5, n),
            'momentum_10d': np.random.uniform(-15, 25, n),
        })

    def test_normal(self):
        sp.FACTOR_CONFIG = {}
        df = self._make_df(100)
        result = sp.select_stocks_us_complete(df)
        assert len(result) <= 10
        assert 'ts_code' in result.columns

    def test_empty(self):
        sp.FACTOR_CONFIG = {}
        df = pd.DataFrame()
        result = sp.select_stocks_us_complete(df)
        assert result.empty


# ============================================================
# 7. 市场配置
# ============================================================

class TestMarketConfig:
    def test_cn_config(self):
        assert sp.MARKET_CONFIG['cn']['name'] == 'A 股 (中证 1000)'
        assert sp.MARKET_CONFIG['cn']['use_full_factors'] is True

    def test_hk_config(self):
        assert sp.MARKET_CONFIG['hk']['name'] == '港股 Top 500'
        assert sp.MARKET_CONFIG['hk']['use_full_factors'] is False

    def test_us_config(self):
        assert sp.MARKET_CONFIG['us']['name'] == '美股 Top 500'
        assert sp.MARKET_CONFIG['us']['use_full_factors'] is False


# ============================================================
# 8. 数据加载 — load_daily_data (mocked)
# ============================================================

class TestLoadDailyData:
    def test_no_files(self):
        # 如果没有任何月度文件，返回空 DataFrame
        original_dir = sp.DAILY_DATA_DIR
        with tempfile.TemporaryDirectory() as tmpdir:
            sp.DAILY_DATA_DIR = Path(tmpdir)
            try:
                df = sp.load_daily_data('2024-01-01', '2026-04-15')
                assert df.empty
            finally:
                sp.DAILY_DATA_DIR = original_dir


# ============================================================
# 9. 备份文件
# ============================================================

class TestBackupFile:
    def test_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / 'backups'
            backup_dir.mkdir()
            test_file = Path(tmpdir) / 'test.csv'
            test_file.write_text('a,b\n1,2')

            original_backup = sp.BACKUPS_DIR
            sp.BACKUPS_DIR = backup_dir

            sp.backup_file(test_file)
            backups = list(backup_dir.glob('test_*.csv'))
            assert len(backups) == 1

            sp.BACKUPS_DIR = original_backup

    def test_backup_nonexistent(self):
        # 不应抛出异常
        sp.backup_file(Path('/nonexistent/file.txt'))
