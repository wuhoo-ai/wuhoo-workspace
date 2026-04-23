"""
回测验证模块 - 增强版
使用历史赛事数据验证预测模型准确性
包含：动态 Elo 更新、真实统计数据、滚动窗口分析
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from prediction_models import predict_match, EloModel
from fetch_data import DataFetcher


class Backtester:
    """足球赛事回测引擎 - 增强版"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "data"
        self.results_dir = self.data_dir / "backtest_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.fetcher = DataFetcher(data_dir)
        self.elo_model = EloModel(k_factor=20, home_advantage=65)
    
    def run_backtest(self, tournament: str, year: int, 
                     model_name: str = 'ensemble',
                     use_dynamic_elo: bool = True) -> Dict:
        """
        执行回测
        model_name: 'ensemble', 'poisson', 'elo', 'factors'
        use_dynamic_elo: 是否使用动态 Elo 更新
        """
        print(f"🏆 开始回测 {year} {tournament.upper()}...")
        
        # 加载数据
        if tournament == 'worldcup':
            matches = self.fetcher.fetch_worldcup_history(year)
        else:
            matches = self.fetcher.fetch_euro_history(year)
        
        if matches.empty:
            print("❌ 没有比赛数据")
            return {}
        
        print(f"📊 共 {len(matches)} 场比赛")
        
        # 加载 Elo
        elo_ratings = self.fetcher.fetch_elo_ratings()
        
        # 加载历史数据用于统计
        all_history = self._load_history(tournament, year)
        
        # 预测每场比赛
        predictions = []
        actuals = []
        
        for idx, match in matches.iterrows():
            # 检查是否有比分
            if pd.isna(match.get('score_a')) or pd.isna(match.get('score_b')):
                continue
            
            # 获取 Elo（默认 1500）
            elo_a = elo_ratings.get(match['team_a'], {}).get('elo', 1500)
            elo_b = elo_ratings.get(match['team_b'], {}).get('elo', 1500)
            
            # 计算真实统计数据
            avg_goals_a = self.fetcher.get_team_avg_goals(match['team_a'], all_history)
            avg_goals_b = self.fetcher.get_team_avg_goals(match['team_b'], all_history)
            recent_form_a = self.fetcher.get_recent_form(match['team_a'], all_history)
            recent_form_b = self.fetcher.get_recent_form(match['team_b'], all_history)
            h2h = self.fetcher.get_head_to_head(match['team_a'], match['team_b'], all_history)
            
            # 因子
            factors = {
                'elo_diff': (elo_a - elo_b) / 400,
                'recent_form': recent_form_a - recent_form_b,
                'head_to_head': h2h,
                'avg_goals': (avg_goals_a - avg_goals_b) / 3,
                'news_sentiment': 0,
                'tournament_context': 0.1 if idx < 16 else 0.2  # 淘汰赛加分
            }
            
            # 预测
            is_neutral = str(match.get('neutral', 'True')).lower() == 'true'
            
            try:
                result = predict_match(
                    team_a=match['team_a'],
                    team_b=match['team_b'],
                    elo_a=elo_a,
                    elo_b=elo_b,
                    goals_a=avg_goals_a,
                    goals_b=avg_goals_b,
                    factors=factors,
                    is_neutral=is_neutral
                )
                
                pred = result['predictions'][model_name if model_name != 'ensemble' else 'ensemble']
                predictions.append({
                    'match': f"{match['team_a']} vs {match['team_b']}",
                    'prediction': pred,
                    'model': model_name
                })
                
                actuals.append({
                    'match': f"{match['team_a']} vs {match['team_b']}",
                    'actual': self._result_to_vector(match['score_a'], match['score_b'])
                })
                
                # 动态更新 Elo
                if use_dynamic_elo:
                    new_a, new_b = self.elo_model.update_elo(
                        elo_a, elo_b, match['score_a'], match['score_b'], is_neutral
                    )
                    elo_ratings[match['team_a']] = {'elo': new_a}
                    elo_ratings[match['team_b']] = {'elo': new_b}
                
            except Exception as e:
                print(f"  ⚠️ 跳过比赛 {match['team_a']} vs {match['team_b']}: {e}")
                continue
        
        if not predictions:
            print("❌ 没有有效的预测结果")
            return {}
        
        # 计算指标
        metrics = self._calculate_metrics(predictions, actuals)
        
        # 保存结果
        self._save_results(tournament, year, model_name, metrics, predictions, actuals)
        
        # 输出报告
        self._print_report(tournament, year, model_name, metrics)
        
        return metrics
    
    def _load_history(self, tournament: str, year: int) -> pd.DataFrame:
        """加载历史数据（包含过往赛事）"""
        full_file = self.data_dir / "international_full.csv"
        if full_file.exists():
            df = pd.read_csv(full_file)
            df = self.fetcher._normalize_columns(df)
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            cutoff = pd.Timestamp(f"{year}-01-01")
            df = df[df['date'] < cutoff]
            return df
        return pd.DataFrame()
    
    def _result_to_vector(self, score_a: int, score_b: int) -> List[float]:
        """将比分转换为结果向量 [主胜, 平局, 客胜]"""
        if score_a > score_b:
            return [1, 0, 0]
        elif score_a == score_b:
            return [0, 1, 0]
        else:
            return [0, 0, 1]
    
    def _calculate_metrics(self, predictions: List[Dict], actuals: List[Dict]) -> Dict:
        """计算评估指标"""
        n = len(predictions)
        correct = 0
        brier_score = 0
        log_loss = 0
        
        for pred, actual in zip(predictions, actuals):
            p = pred['prediction']
            a = actual['actual']
            
            # 准确率
            pred_result = np.argmax([p['home_win'], p['draw'], p['away_win']])
            actual_result = np.argmax(a)
            if pred_result == actual_result:
                correct += 1
            
            # Brier Score
            probs = np.array([p['home_win'], p['draw'], p['away_win']])
            brier_score += np.sum((probs - a) ** 2)
            
            # Log Loss
            prob_actual = max(probs[actual_result], 1e-15)
            log_loss -= np.log(prob_actual)
        
        return {
            'accuracy': correct / n,
            'random_baseline': 0.33,
            'improvement': (correct / n - 0.33) / 0.33 * 100,
            'brier_score': brier_score / n,
            'log_loss': log_loss / n,
            'total_matches': n,
            'correct_predictions': correct
        }
    
    def _save_results(self, tournament: str, year: int, model_name: str,
                      metrics: Dict, predictions: List, actuals: List):
        """保存回测结果"""
        result_file = self.results_dir / f"{tournament}_{year}_{model_name}.json"
        
        result = {
            'tournament': tournament,
            'year': year,
            'model': model_name,
            'metrics': metrics,
            'predictions': predictions,
            'actuals': actuals,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"💾 结果已保存: {result_file}")
    
    def _print_report(self, tournament: str, year: int, model_name: str, metrics: Dict):
        """打印回测报告"""
        print(f"\n{'=' * 50}")
        print(f"📊 回测报告: {year} {tournament.upper()}")
        print(f"{'=' * 50}")
        print(f"  模型: {model_name.upper()}")
        print(f"  比赛数量: {metrics['total_matches']}")
        print(f"  正确预测: {metrics['correct_predictions']}")
        print(f"  准确率: {metrics['accuracy'] * 100:.1f}%")
        print(f"  随机基准: {metrics['random_baseline'] * 100:.1f}%")
        print(f"  提升幅度: {metrics['improvement']:+.1f}%")
        print(f"  Brier Score: {metrics['brier_score']:.4f}")
        print(f"  Log Loss: {metrics['log_loss']:.4f}")
        print(f"{'=' * 50}")
        
        if metrics['accuracy'] > metrics['random_baseline']:
            print("✅ 模型表现优于随机猜测")
        else:
            print("⚠️ 模型表现未超过随机基准")


if __name__ == "__main__":
    bt = Backtester()
    bt.run_backtest("worldcup", 2022)
