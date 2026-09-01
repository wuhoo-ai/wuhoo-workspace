"""
足球赛事预测系统单元测试 (修复版 — 匹配实际 API)
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
        
        assert 'home_win' in result
        assert 'draw' in result
        assert 'away_win' in result
        assert abs(result['home_win'] + result['draw'] + result['away_win'] - 1.0) < 0.01
    
    def test_predict_equal_teams(self):
        """测试势均力敌的球队"""
        model = PoissonModel()
        result = model.predict(1.5, 1.5)
        
        # 平局概率应该较高（约 24%）
        assert result['draw'] > 0.20
        # 双方胜率接近
        assert abs(result['home_win'] - result['away_win']) < 0.05
    
    def test_poisson_prob(self):
        """测试 Poisson PMF"""
        model = PoissonModel()
        
        # k=0, lambda=1: e^-1 ≈ 0.368
        p0 = model._poisson_prob(0, 1.0)
        assert abs(p0 - 0.368) < 0.01
        
        # 概率和应接近 1
        total = sum(model._poisson_prob(k, 1.5) for k in range(20))
        assert abs(total - 1.0) < 0.01


class TestEloModel:
    """测试 Elo 预测模型"""
    
    def test_predict_basic(self):
        """测试基本预测"""
        model = EloModel()
        result = model.predict(1800, 1700)
        
        assert result['home_win'] > result['away_win']
        assert abs(result['home_win'] + result['draw'] + result['away_win'] - 1.0) < 0.01
    
    def test_equal_elo(self):
        """测试相同 Elo"""
        model = EloModel()
        result = model.predict(1500, 1500)
        
        # 胜率应该接近
        assert abs(result['home_win'] - result['away_win']) < 0.05
    
    def test_home_advantage(self):
        """测试主场优势"""
        model = EloModel(home_advantage=65)
        
        # 中立场地
        result_neutral = model.predict(1600, 1600, is_neutral=True)
        # 主场
        result_home = model.predict(1600, 1600, is_neutral=False)
        
        assert result_home['home_win'] > result_neutral['home_win']


class TestFactorModel:
    """测试因子模型"""
    
    def test_predict_basic(self):
        """测试基本预测"""
        model = FactorModel()
        factors = {
            'elo_diff': 0.3,
            'recent_form': 0.3,
            'head_to_head': 0.2,
            'avg_goals': 0.25,
            'news_sentiment': 0.05,
            'tournament_context': 0.1
        }
        result = model.predict(factors)
        
        assert result['home_win'] > result['away_win']
        assert abs(result['home_win'] + result['draw'] + result['away_win'] - 1.0) < 0.01
    
    def test_negative_factors(self):
        """测试负面因子"""
        model = FactorModel()
        factors = {
            'elo_diff': -0.3,
            'recent_form': -0.3,
            'head_to_head': -0.2,
            'avg_goals': -0.25,
            'news_sentiment': -0.05,
            'tournament_context': -0.1
        }
        result = model.predict(factors)
        
        assert result['away_win'] > result['home_win']


class TestEnsembleModel:
    """测试集成模型"""
    
    def test_ensemble_basic(self):
        """测试集成预测"""
        model = EnsembleModel()
        factors = {
            'elo_diff': 0.2,
            'recent_form': 0.1,
            'head_to_head': 0,
            'avg_goals': 0.1,
            'news_sentiment': 0,
            'tournament_context': 0
        }
        result = model.predict(
            team_a="Argentina", team_b="Brazil",
            elo_a=2114, elo_b=2061,
            goals_a=1.8, goals_b=1.7,
            factors=factors
        )
        
        assert 'predictions' in result
        assert 'ensemble' in result['predictions']
        assert result['predictions']['ensemble']['home_win'] > 0
    
    def test_ensemble_equal(self):
        """测试势均力敌的集成预测"""
        model = EnsembleModel()
        factors = {
            'elo_diff': 0,
            'recent_form': 0,
            'head_to_head': 0,
            'avg_goals': 0,
            'news_sentiment': 0,
            'tournament_context': 0
        }
        result = model.predict(
            team_a="TeamA", team_b="TeamB",
            elo_a=1900, elo_b=1900,
            goals_a=1.5, goals_b=1.5,
            factors=factors
        )
        
        ensemble = result['predictions']['ensemble']
        # 势均力敌时，主客胜率应该接近
        assert abs(ensemble['home_win'] - ensemble['away_win']) < 0.1


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
        """测试批量分析 (analyze_news_batch 返回 per-team dict)"""
        analyzer = SentimentAnalyzer()
        news = [
            {'team': 'TestTeam', 'title': 'Team wins brilliantly', 'content': ''},
            {'team': 'TestTeam', 'title': 'Player injured', 'content': ''},
            {'team': 'TestTeam', 'title': 'Normal match report', 'content': ''},
        ]
        result = analyzer.analyze_news_batch(news)
        
        # result is {team_lower: sentiment_score}
        assert 'testteam' in result
        assert isinstance(result['testteam'], float)


class TestPredictMatch:
    """测试完整预测流程"""
    
    def test_predict_match(self):
        """测试完整预测"""
        result = predict_match(
            team_a="Argentina",
            team_b="France",
            elo_a=2114,
            elo_b=2075,
            goals_a=1.8,
            goals_b=1.7,
            factors={
                'elo_diff': (2114 - 2075) / 400,
                'recent_form': 0.3,
                'head_to_head': 0.0,
                'avg_goals': 0.1,
                'news_sentiment': 0.1,
                'tournament_context': 0.0
            }
        )
        
        assert 'predictions' in result
        assert 'recommendation' in result
        assert 'poisson' in result['predictions']
        assert 'elo' in result['predictions']
        assert 'ensemble' in result['predictions']


class TestDataIntegration:
    """测试数据加载集成"""
    
    def test_elo_json_format(self):
        """测试 ELO JSON 格式兼容性"""
        import json
        elo_path = Path(__file__).parent.parent / "data" / "elo_ratings.json"
        with open(elo_path) as f:
            data = json.load(f)
        
        ratings = data.get('ratings', {})
        assert len(ratings) >= 45, f"Expected ≥45 teams, got {len(ratings)}"
        
        # 验证 dict 格式
        for team, info in ratings.items():
            assert 'elo' in info, f"{team} missing 'elo' key"
            assert isinstance(info['elo'], (int, float)), f"{team} elo not numeric"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
