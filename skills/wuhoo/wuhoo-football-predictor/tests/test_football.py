"""
足球赛事预测系统单元测试
"""

import pytest
import sys
from pathlib import Path

# 添加脚本路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fetch_data import DataFetcher
from prediction_models import PoissonModel, EloModel, FactorModel, EnsembleModel, predict_match
from sentiment_analyzer import SentimentAnalyzer


class TestDataFetcher:
    """测试数据采集模块"""
    
    def test_init(self):
        """测试初始化"""
        fetcher = DataFetcher()
        assert fetcher.data_dir is not None
    
    def test_default_elo(self):
        """测试默认 Elo 数据"""
        fetcher = DataFetcher()
        elo = fetcher._get_default_elo()
        assert 'Argentina' in elo
        assert elo['Argentina']['elo'] > 1800


class TestPoissonModel:
    """测试 Poisson 预测模型"""
    
    def test_predict_basic(self):
        """测试基本预测"""
        model = PoissonModel()
        result = model.predict(1.5, 1.2)
        
        assert 'win_a' in result
        assert 'draw' in result
        assert 'win_b' in result
        assert abs(result['win_a'] + result['draw'] + result['win_b'] - 1.0) < 0.01
    
    def test_predict_equal_teams(self):
        """测试势均力敌的球队"""
        model = PoissonModel()
        result = model.predict(1.5, 1.5)
        
        # 平局概率应该较高（约 24%）
        assert result['draw'] > 0.20
        # 双方胜率接近
        assert abs(result['win_a'] - result['win_b']) < 0.05
    
    def test_poisson_pmf(self):
        """测试 Poisson PMF"""
        model = PoissonModel()
        
        # k=0, lambda=1: e^-1 ≈ 0.368
        p0 = model._poisson_pmf(0, 1.0)
        assert abs(p0 - 0.368) < 0.01
        
        # 概率和应接近 1
        total = sum(model._poisson_pmf(k, 1.5) for k in range(20))
        assert abs(total - 1.0) < 0.01


class TestEloModel:
    """测试 Elo 预测模型"""
    
    def test_predict_basic(self):
        """测试基本预测"""
        model = EloModel()
        result = model.predict(1800, 1700)
        
        assert result['win_a'] > result['win_b']
        assert abs(result['win_a'] + result['draw'] + result['win_b'] - 1.0) < 0.01
    
    def test_equal_elo(self):
        """测试相同 Elo"""
        model = EloModel()
        result = model.predict(1500, 1500)
        
        # 胜率应该接近
        assert abs(result['win_a'] - result['win_b']) < 0.05
    
    def test_home_advantage(self):
        """测试主场优势"""
        model = EloModel(home_advantage=65)
        
        # 中立场地
        result_neutral = model.predict(1600, 1600, is_neutral=True)
        # 主场
        result_home = model.predict(1600, 1600, is_neutral=False)
        
        assert result_home['win_a'] > result_neutral['win_a']


class TestFactorModel:
    """测试因子模型"""
    
    def test_predict_basic(self):
        """测试基本预测"""
        model = FactorModel()
        factors = {
            'recent_form': 0.3,
            'head_to_head': 0.2,
            'team_strength': 0.25,
            'tournament_context': 0.1,
            'news_sentiment': 0.05
        }
        result = model.predict(factors)
        
        assert result['win_a'] > result['win_b']
        assert abs(result['win_a'] + result['draw'] + result['win_b'] - 1.0) < 0.01
    
    def test_negative_factors(self):
        """测试负面因子"""
        model = FactorModel()
        factors = {
            'recent_form': -0.3,
            'head_to_head': -0.2,
            'team_strength': -0.25,
            'tournament_context': -0.1,
            'news_sentiment': -0.05
        }
        result = model.predict(factors)
        
        assert result['win_b'] > result['win_a']


class TestEnsembleModel:
    """测试集成模型"""
    
    def test_ensemble_basic(self):
        """测试集成预测"""
        model = EnsembleModel()
        predictions = [
            {'model': 'elo', 'win_a': 0.6, 'draw': 0.2, 'win_b': 0.2},
            {'model': 'poisson', 'win_a': 0.55, 'draw': 0.25, 'win_b': 0.2},
        ]
        result = model.predict(predictions)
        
        assert 0.5 < result['win_a'] < 0.65
        assert result['confidence'] > 0
    
    def test_ensemble_single(self):
        """测试单个模型集成"""
        model = EnsembleModel()
        predictions = [
            {'model': 'elo', 'win_a': 0.5, 'draw': 0.3, 'win_b': 0.2},
        ]
        result = model.predict(predictions)
        
        assert abs(result['win_a'] - 0.5) < 0.01


class TestSentimentAnalyzer:
    """测试情感分析器"""
    
    def test_positive_text(self):
        """测试正面文本"""
        analyzer = SentimentAnalyzer()
        score = analyzer.analyze_text("brilliant victory excellent form")
        assert score > 0
    
    def test_negative_text(self):
        """测试负面文本"""
        analyzer = SentimentAnalyzer()
        score = analyzer.analyze_text("defeat crisis poor results")
        assert score < 0
    
    def test_injury_impact(self):
        """测试伤停影响"""
        analyzer = SentimentAnalyzer()
        score = analyzer.analyze_text("player injured out with knee injury")
        # 伤停应该是负面
        assert score <= 0
    
    def test_batch_analysis(self):
        """测试批量分析"""
        analyzer = SentimentAnalyzer()
        news = [
            {'title': 'Team wins brilliantly', 'content': ''},
            {'title': 'Player injured', 'content': ''},
            {'title': 'Normal match report', 'content': ''},
        ]
        result = analyzer.analyze_news_batch(news)
        
        assert result['num_news'] == 3
        assert 'sentiment_score' in result
        assert 'trend' in result


class TestPredictMatch:
    """测试完整预测流程"""
    
    def test_predict_match(self):
        """测试完整预测"""
        result = predict_match(
            team_a="Argentina",
            team_b="France",
            elo_a=1859,
            elo_b=1856,
            goals_a=1.8,
            goals_b=1.7,
            factors={
                'recent_form': 0.3,
                'head_to_head': 0.0,
                'team_strength': 0.2,
                'tournament_context': 0.0,
                'news_sentiment': 0.1
            }
        )
        
        assert 'match' in result
        assert 'predictions' in result
        assert 'recommendation' in result
        assert 'poisson' in result['predictions']
        assert 'elo' in result['predictions']
        assert 'ensemble' in result['predictions']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
