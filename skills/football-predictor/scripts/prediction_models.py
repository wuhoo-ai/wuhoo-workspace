"""
足球赛事预测模型
包含：Poisson 分布、Elo 评分、因子模型、集成推荐
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional


class PoissonModel:
    """Poisson 分布预测模型"""
    
    def __init__(self):
        self.max_goals = 7  # 最大预测进球数
    
    def predict(self, lambda_a: float, lambda_b: float) -> dict:
        """
        预测比赛结果
        lambda_a: 主队预期进球
        lambda_b: 客队预期进球
        """
        # 计算比分概率矩阵
        score_probs = {}
        home_win = 0
        draw = 0
        away_win = 0
        
        for i in range(self.max_goals + 1):
            for j in range(self.max_goals + 1):
                prob = self._poisson_prob(i, lambda_a) * self._poisson_prob(j, lambda_b)
                score_key = f"{i}-{j}"
                score_probs[score_key] = prob
                
                if i > j:
                    home_win += prob
                elif i == j:
                    draw += prob
                else:
                    away_win += prob
        
        # 最常见的 3 个比分
        top_scores = sorted(score_probs.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'home_win': home_win,
            'draw': draw,
            'away_win': away_win,
            'top_scores': [(s, round(p * 100, 2)) for s, p in top_scores],
            'expected_goals_a': round(lambda_a, 2),
            'expected_goals_b': round(lambda_b, 2)
        }
    
    def _poisson_prob(self, k: int, lam: float) -> float:
        """Poisson 概率质量函数"""
        if lam <= 0:
            return 0.0
        return (lam ** k) * math.exp(-lam) / math.factorial(k)


class EloModel:
    """Elo 评分预测模型"""
    
    def __init__(self, k_factor: float = 20, home_advantage: float = 65):
        self.k_factor = k_factor
        self.home_advantage = home_advantage
    
    def predict(self, elo_a: float, elo_b: float, is_neutral: bool = True) -> dict:
        """使用 Elo 差值预测"""
        elo_diff = elo_a - elo_b
        if not is_neutral:
            elo_diff += self.home_advantage
        
        # 预期胜率
        expected_a = 1 / (1 + 10 ** (-elo_diff / 400))
        expected_b = 1 - expected_a
        
        # 平局概率（赛事类型调整）
        draw_base = 0.25  # 基础平局概率
        # 实力越接近，平局概率越高
        draw_factor = 1 - abs(expected_a - expected_b)
        draw_prob = draw_base * (0.5 + 0.5 * draw_factor)
        
        # 调整胜负概率
        remaining = 1 - draw_prob
        home_win = remaining * expected_a
        away_win = remaining * expected_b
        
        # 归一化
        total = home_win + draw_prob + away_win
        home_win /= total
        draw_prob /= total
        away_win /= total
        
        return {
            'home_win': round(home_win, 3),
            'draw': round(draw_prob, 3),
            'away_win': round(away_win, 3),
            'elo_diff': elo_diff
        }
    
    def update_elo(self, rating_a: float, rating_b: float, 
                   score_a: int, score_b: int, is_neutral: bool = True) -> tuple:
        """更新 Elo 评分"""
        expected = self.predict(rating_a, rating_b, is_neutral)
        
        # 实际结果
        if score_a > score_b:
            actual_a = 1
        elif score_a == score_b:
            actual_a = 0.5
        else:
            actual_a = 0
        
        # 进球差奖励
        goal_diff = abs(score_a - score_b)
        k_multiplier = 1 + 0.1 * goal_diff
        
        new_a = rating_a + self.k_factor * k_multiplier * (actual_a - expected['home_win'])
        new_b = rating_b + self.k_factor * k_multiplier * ((1 - actual_a) - expected['away_win'])
        
        return new_a, new_b


class FactorModel:
    """多因子预测模型"""
    
    def __init__(self):
        # 因子权重（可优化）
        self.weights = {
            'elo_diff': 0.30,
            'recent_form': 0.20,
            'head_to_head': 0.15,
            'avg_goals': 0.15,
            'news_sentiment': 0.10,
            'tournament_context': 0.10
        }
    
    def predict(self, factors: dict) -> dict:
        """
        基于多因子预测
        factors 包含:
        - elo_diff: Elo 差值 (归一化到 -1 到 1)
        - recent_form: 近期状态差 (-1 到 1)
        - head_to_head: 交锋优势 (-1 到 1)
        - avg_goals: 进球能力差 (-1 到 1)
        - news_sentiment: 新闻情绪差 (-1 到 1)
        - tournament_context: 赛事上下文 (-1 到 1)
        """
        # 加权综合得分
        score = 0
        for factor, weight in self.weights.items():
            score += factors.get(factor, 0) * weight
        
        # 转换为概率
        home_win = 1 / (1 + 10 ** (-score * 2))
        away_win = 1 - home_win
        
        # 平局概率
        competitiveness = 1 - abs(score)
        draw_prob = 0.25 * (0.5 + 0.5 * competitiveness)
        
        # 归一化
        remaining = 1 - draw_prob
        home_win = remaining * home_win
        away_win = remaining * away_win
        
        total = home_win + draw_prob + away_win
        home_win /= total
        draw_prob /= total
        away_win /= total
        
        return {
            'home_win': round(home_win, 3),
            'draw': round(draw_prob, 3),
            'away_win': round(away_win, 3),
            'factor_score': round(score, 3)
        }


class EnsembleModel:
    """集成模型：组合多个预测器"""
    
    def __init__(self):
        self.poisson = PoissonModel()
        self.elo = EloModel()
        self.factors = FactorModel()
        
        # 集成权重
        self.model_weights = {
            'poisson': 0.25,
            'elo': 0.35,
            'factors': 0.40
        }
    
    def predict(self, team_a: str, team_b: str, 
                elo_a: float, elo_b: float,
                goals_a: float, goals_b: float,
                factors: dict,
                is_neutral: bool = True) -> dict:
        """集成预测"""
        predictions = {}
        
        # 1. Poisson 模型
        poisson_result = self.poisson.predict(goals_a, goals_b)
        predictions['poisson'] = {
            'home_win': poisson_result['home_win'],
            'draw': poisson_result['draw'],
            'away_win': poisson_result['away_win']
        }
        
        # 2. Elo 模型
        elo_result = self.elo.predict(elo_a, elo_b, is_neutral)
        predictions['elo'] = {
            'home_win': elo_result['home_win'],
            'draw': elo_result['draw'],
            'away_win': elo_result['away_win']
        }
        
        # 3. 因子模型
        factor_result = self.factors.predict(factors)
        predictions['factors'] = {
            'home_win': factor_result['home_win'],
            'draw': factor_result['draw'],
            'away_win': factor_result['away_win']
        }
        
        # 加权平均
        ensemble = {'home_win': 0, 'draw': 0, 'away_win': 0}
        for model_name, weight in self.model_weights.items():
            pred = predictions[model_name]
            ensemble['home_win'] += pred['home_win'] * weight
            ensemble['draw'] += pred['draw'] * weight
            ensemble['away_win'] += pred['away_win'] * weight
        
        # 归一化
        total = sum(ensemble.values())
        for k in ensemble:
            ensemble[k] = round(ensemble[k] / total, 3)
        
        predictions['ensemble'] = ensemble
        
        # 推荐
        if ensemble['home_win'] > ensemble['draw'] and ensemble['home_win'] > ensemble['away_win']:
            recommendation = f"主胜 ({team_a})"
        elif ensemble['away_win'] > ensemble['draw'] and ensemble['away_win'] > ensemble['home_win']:
            recommendation = f"客胜 ({team_b})"
        else:
            recommendation = "平局"
        
        return {
            'predictions': predictions,
            'recommendation': recommendation,
            'top_scores': poisson_result.get('top_scores', []),
            'expected_goals': {
                'team_a': poisson_result['expected_goals_a'],
                'team_b': poisson_result['expected_goals_b']
            }
        }


# 便捷函数
def predict_match(team_a: str, team_b: str,
                  elo_a: float = 1500, elo_b: float = 1500,
                  goals_a: float = 1.3, goals_b: float = 1.3,
                  factors: dict = None,
                  is_neutral: bool = True) -> dict:
    """单场比赛预测便捷函数"""
    if factors is None:
        factors = {
            'elo_diff': (elo_a - elo_b) / 400,
            'recent_form': 0,
            'head_to_head': 0,
            'avg_goals': (goals_a - goals_b) / 3,
            'news_sentiment': 0,
            'tournament_context': 0
        }
    
    ensemble = EnsembleModel()
    return ensemble.predict(
        team_a=team_a, team_b=team_b,
        elo_a=elo_a, elo_b=elo_b,
        goals_a=goals_a, goals_b=goals_b,
        factors=factors,
        is_neutral=is_neutral
    )


if __name__ == "__main__":
    # 测试
    result = predict_match("Argentina", "France", 1859, 1856, 1.8, 1.7)
    print("集成预测结果:")
    print(f"推荐: {result['recommendation']}")
    print(f"概率: {result['predictions']['ensemble']}")
    print(f"预期进球: {result['expected_goals']}")
    print(f"热门比分: {result['top_scores']}")
