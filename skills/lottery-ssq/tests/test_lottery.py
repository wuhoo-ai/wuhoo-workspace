#!/usr/bin/env python3.11
"""lottery-ssq 测试模块"""

import csv
import os
import sys
import tempfile
from pathlib import Path

import pytest

# 添加项目路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from scripts.analysis_engine import (
    analyze_frequency,
    analyze_omission,
    analyze_zone_distribution,
    analyze_odd_even,
    analyze_sum,
    analyze_ac_value,
    analyze_consecutive,
    analyze_repeat,
    analyze_blue_ball,
    calculate_ac_value,
)
from scripts.predictor import (
    generate_predictions,
    get_blue_recommendations,
    get_default_config,
)
from scripts.money_management import (
    calculate_budget,
    fixed_investment_strategy,
    risk_assessment,
    generate_advice,
)
from scripts.monte_carlo import check_prize


# =============================================================================
# 测试数据
# =============================================================================

@pytest.fixture
def sample_data():
    """创建模拟开奖数据"""
    data = []
    for i in range(1, 201):  # 200 期
        red = sorted([1, 2, 3, 4, 5, i % 33 + 1])  # 确保有效
        if len(set(red)) < 6:
            red = [1, 5, 10, 15, 20, 25]
        data.append({
            "期号": f"2026{i:03d}",
            "日期": f"2026-01-{i % 28 + 1:02d}",
            "红1": red[0], "红2": red[1], "红3": red[2],
            "红4": red[3], "红5": red[4], "红6": red[5],
            "蓝球": (i % 16) + 1,
            "销售额": "200000000",
            "奖池": "1000000000",
        })
    return data


@pytest.fixture
def sample_df(sample_data):
    """创建 DataFrame"""
    import pandas as pd
    return pd.DataFrame(sample_data)


# =============================================================================
# 分析引擎测试
# =============================================================================

class TestAnalysisEngine:
    def test_frequency_analysis(self, sample_df):
        result = analyze_frequency(sample_df)
        assert "hot_red" in result
        assert "cold_red" in result
        assert len(result["hot_red"]) == 10
        assert len(result["cold_red"]) == 10
    
    def test_omission_analysis(self, sample_df):
        result = analyze_omission(sample_df)
        assert "red_omission" in result
        assert len(result["red_omission"]) == 33
        assert "blue_omission" in result
        assert len(result["blue_omission"]) == 16
    
    def test_zone_distribution(self, sample_df):
        result = analyze_zone_distribution(sample_df)
        assert "zone_counts" in result
        assert "recommended_ratio" in result
    
    def test_odd_even(self, sample_df):
        result = analyze_odd_even(sample_df)
        assert "ratios" in result
        assert "recommended" in result
    
    def test_sum_analysis(self, sample_df):
        result = analyze_sum(sample_df)
        assert "mean" in result
        assert "median" in result
        assert "std" in result
    
    def test_ac_value_calculation(self):
        # AC值 = 不同差值数量 - (号码数量 - 1)
        # [1,2,3,4,5,6] -> 差值有 1,2,3,4,5 -> 5个 -> AC = 5 - 5 = 0
        assert calculate_ac_value([1, 2, 3, 4, 5, 6]) == 0
        # [1,5,10,15,20,30] -> 更多不同差值
        ac = calculate_ac_value([1, 5, 10, 15, 20, 30])
        assert ac >= 0
    
    def test_ac_value_analysis(self, sample_df):
        result = analyze_ac_value(sample_df)
        assert "mean" in result
        assert "distribution" in result
    
    def test_consecutive_analysis(self, sample_df):
        result = analyze_consecutive(sample_df)
        assert "has_consecutive_rate" in result
        assert "distribution" in result
    
    def test_repeat_analysis(self, sample_df):
        result = analyze_repeat(sample_df)
        assert "distribution" in result
    
    def test_blue_ball_analysis(self, sample_df):
        result = analyze_blue_ball(sample_df)
        assert "odd_rate" in result
        assert "even_rate" in result


# =============================================================================
# 预测引擎测试
# =============================================================================

class TestPredictor:
    def test_generate_predictions(self, sample_df):
        stats = {
            "frequency": analyze_frequency(sample_df),
            "omission": analyze_omission(sample_df),
            "zone": analyze_zone_distribution(sample_df),
        }
        
        config = get_default_config()
        config["generate_count"] = 5
        
        predictions = generate_predictions(stats, config, count=5)
        assert len(predictions) == 5
        
        for pred in predictions:
            assert len(pred["red"]) == 6
            assert all(1 <= r <= 33 for r in pred["red"])
            assert 1 <= pred["blue"] <= 16
            assert pred["red"] == sorted(pred["red"])
    
    def test_blue_recommendations(self, sample_df):
        stats = {
            "frequency": analyze_frequency(sample_df),
            "omission": analyze_omission(sample_df),
        }
        
        recs = get_blue_recommendations(stats, count=5)
        assert len(recs) == 5
        
        for rec in recs:
            assert "number" in rec
            assert "score" in rec


# =============================================================================
# 资金管理测试
# =============================================================================

class TestMoneyManagement:
    def test_calculate_budget(self):
        result = calculate_budget(100)
        assert result["monthly_budget"] == 100
        assert result["notes_per_draw"] >= 1
        assert result["cost_per_note"] == 2
    
    def test_fixed_investment(self):
        result = fixed_investment_strategy(50, months=6)
        assert result["monthly_budget"] == 50
        assert result["months"] == 6
        assert result["total_cost"] > 0
    
    def test_risk_assessment_low(self):
        result = risk_assessment(10)
        assert "低" in result["risk_level"]
    
    def test_risk_assessment_high(self):
        result = risk_assessment(500)
        assert "高" in result["risk_level"]
    
    def test_generate_advice(self):
        advice = generate_advice(20, months=12)
        assert "budget" in advice
        assert "investment" in advice
        assert "risk" in advice
        assert "summary" in advice


# =============================================================================
# 回测测试
# =============================================================================

class TestMonteCarlo:
    def test_check_prize_first_prize(self):
        # 6红 + 1蓝
        level, amount = check_prize([1, 2, 3, 4, 5, 6], 7, [1, 2, 3, 4, 5, 6], 7)
        assert level == 1
    
    def test_check_prize_sixth_prize(self):
        # 0红 + 1蓝
        level, amount = check_prize([1, 2, 3, 4, 5, 6], 7, [10, 11, 12, 13, 14, 15], 7)
        assert level == 6
        assert amount == 5
    
    def test_check_prize_no_win(self):
        # 0红 + 0蓝
        level, amount = check_prize([1, 2, 3, 4, 5, 6], 7, [10, 11, 12, 13, 14, 15], 8)
        assert level == 0
        assert amount == 0
