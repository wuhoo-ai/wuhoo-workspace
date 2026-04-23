"""
足球赛事数据采集模块
数据源：International Results (GitHub)、clubelo.com、新闻 RSS
"""

import os
import json
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict


class DataFetcher:
    """足球赛事数据采集器"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.elo_file = self.data_dir / "elo_ratings.json"
        self.full_data_file = self.data_dir / "international_full.csv"
        
    def fetch_worldcup_history(self, year: Optional[int] = None) -> pd.DataFrame:
        """加载世界杯历史数据"""
        wc_file = self.data_dir / f"worldcup_{year or 2022}_full.csv"
        
        if wc_file.exists():
            df = pd.read_csv(wc_file)
            df = self._normalize_columns(df)
            print(f"📊 加载本地世界杯数据: {len(df)} 场比赛")
            return df
        
        # 回退到完整数据过滤
        return self._filter_from_full_data("FIFA World Cup", year)
    
    def fetch_euro_history(self, year: Optional[int] = None) -> pd.DataFrame:
        """加载欧洲杯历史数据"""
        euro_file = self.data_dir / f"euro_{year or 2024}_full.csv"
        
        if euro_file.exists():
            df = pd.read_csv(euro_file)
            df = self._normalize_columns(df)
            print(f"📊 加载本地欧洲杯数据: {len(df)} 场比赛")
            return df
        
        return self._filter_from_full_data("UEFA Euro", year)
    
    def _filter_from_full_data(self, tournament: str, year: Optional[int] = None) -> pd.DataFrame:
        """从完整数据中过滤"""
        if not self.full_data_file.exists():
            print("⚠️ 完整数据文件不存在")
            return pd.DataFrame()
        
        df = pd.read_csv(self.full_data_file)
        df = self._normalize_columns(df)
        
        mask = df['tournament'] == tournament
        if year:
            mask = mask & (df['date'].str.startswith(str(year)))
        
        result = df[mask]
        print(f"📊 从完整数据过滤: {len(result)} 场比赛")
        return result
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        col_mapping = {
            'home_team': 'team_a',
            'away_team': 'team_b',
            'home_score': 'score_a',
            'away_score': 'score_b',
        }
        
        for old, new in col_mapping.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        # 确保必要列存在
        required = ['date', 'team_a', 'team_b', 'score_a', 'score_b']
        for col in required:
            if col not in df.columns:
                df[col] = None
        
        # 添加 tournament 和 stage
        if 'tournament' not in df.columns:
            df['tournament'] = 'unknown'
        if 'stage' not in df.columns:
            df['stage'] = 'Match'
        
        # 标准化 tournament 名称
        df['tournament'] = df['tournament'].str.lower().str.replace(' ', '_')
        df['tournament'] = df['tournament'].replace({
            'fifa_world_cup': 'worldcup',
            'uefa_euro': 'euro'
        })
        
        # 分数转整数
        df['score_a'] = pd.to_numeric(df['score_a'], errors='coerce').fillna(0).astype(int)
        df['score_b'] = pd.to_numeric(df['score_b'], errors='coerce').fillna(0).astype(int)
        
        return df
    
    def fetch_elo_ratings(self) -> dict:
        """获取 Elo 评分"""
        if self.elo_file.exists():
            with open(self.elo_file, 'r') as f:
                elo_data = json.load(f)
            last_update = datetime.fromisoformat(elo_data.get('last_update', '2000-01-01'))
            if datetime.now() - last_update < timedelta(hours=24):
                print(f"📊 加载本地 Elo: {len(elo_data.get('ratings', {}))} 支球队")
                return elo_data.get('ratings', {})
        
        try:
            print("📥 从 clubelo.com 获取 Elo...")
            url = "http://api.clubelo.com/Ranking"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            elo_ratings = {}
            
            for line in lines[1:]:
                values = line.split(',')
                if len(values) >= 4:
                    team = values[0]
                    try:
                        elo = float(values[3])
                        elo_ratings[team] = {
                            'elo': elo,
                            'rank': int(values[1]) if values[1].isdigit() else None,
                            'country': values[2]
                        }
                    except (ValueError, IndexError):
                        continue
            
            elo_data = {
                'last_update': datetime.now().isoformat(),
                'ratings': elo_ratings
            }
            with open(self.elo_file, 'w') as f:
                json.dump(elo_data, f, indent=2)
            
            print(f"✅ 获取 {len(elo_ratings)} 支球队 Elo")
            return elo_ratings
            
        except Exception as e:
            print(f"⚠️ Elo 获取失败: {e}")
            return self._get_default_elo()
    
    def get_recent_form(self, team: str, matches: pd.DataFrame, n_games: int = 5) -> float:
        """计算球队近期状态（胜率）"""
        team_matches = matches[
            ((matches['team_a'] == team) | (matches['team_b'] == team))
        ].sort_values('date', ascending=False).head(n_games)
        
        if len(team_matches) == 0:
            return 0.0
        
        wins = 0
        draws = 0
        for _, match in team_matches.iterrows():
            if match['team_a'] == team:
                if match['score_a'] > match['score_b']:
                    wins += 1
                elif match['score_a'] == match['score_b']:
                    draws += 0.5
            else:
                if match['score_b'] > match['score_a']:
                    wins += 1
                elif match['score_a'] == match['score_b']:
                    draws += 0.5
        
        return (wins + draws) / n_games
    
    def get_head_to_head(self, team_a: str, team_b: str, matches: pd.DataFrame, n_games: int = 5) -> float:
        """计算历史交锋优势 (-1 到 1)"""
        h2h = matches[
            ((matches['team_a'] == team_a) & (matches['team_b'] == team_b)) |
            ((matches['team_a'] == team_b) & (matches['team_b'] == team_a))
        ].sort_values('date', ascending=False).head(n_games)
        
        if len(h2h) == 0:
            return 0.0
        
        score = 0
        for _, match in h2h.iterrows():
            if match['team_a'] == team_a:
                if match['score_a'] > match['score_b']:
                    score += 1
                elif match['score_a'] < match['score_b']:
                    score -= 1
            else:
                if match['score_b'] > match['score_a']:
                    score += 1
                elif match['score_a'] > match['score_b']:
                    score -= 1
        
        return score / n_games
    
    def get_team_avg_goals(self, team: str, matches: pd.DataFrame, n_games: int = 10) -> float:
        """计算球队平均进球"""
        team_matches = matches[
            ((matches['team_a'] == team) | (matches['team_b'] == team))
        ].sort_values('date', ascending=False).head(n_games)
        
        if len(team_matches) == 0:
            return 1.3  # 默认值
        
        total_goals = 0
        for _, match in team_matches.iterrows():
            if match['team_a'] == team:
                total_goals += match['score_a']
            else:
                total_goals += match['score_b']
        
        return total_goals / len(team_matches)
    
    def _get_default_elo(self) -> dict:
        """默认 Elo 评分"""
        return {
            'Argentina': {'elo': 1859, 'rank': 1, 'country': 'Argentina'},
            'France': {'elo': 1856, 'rank': 2, 'country': 'France'},
            'Brazil': {'elo': 1838, 'rank': 3, 'country': 'Brazil'},
            'England': {'elo': 1817, 'rank': 4, 'country': 'England'},
            'Spain': {'elo': 1840, 'rank': 5, 'country': 'Spain'},
            'Germany': {'elo': 1800, 'rank': 6, 'country': 'Germany'},
            'Portugal': {'elo': 1790, 'rank': 7, 'country': 'Portugal'},
            'Netherlands': {'elo': 1780, 'rank': 8, 'country': 'Netherlands'},
            'Italy': {'elo': 1760, 'rank': 9, 'country': 'Italy'},
            'Croatia': {'elo': 1730, 'rank': 10, 'country': 'Croatia'},
            'Belgium': {'elo': 1750, 'rank': 11, 'country': 'Belgium'},
            'Morocco': {'elo': 1690, 'rank': 12, 'country': 'Morocco'},
        }


if __name__ == "__main__":
    fetcher = DataFetcher()
    wc = fetcher.fetch_worldcup_history(2022)
    print(f"\n2022 世界杯: {len(wc)} 场")
    
    euro = fetcher.fetch_euro_history(2024)
    print(f"2024 欧洲杯: {len(euro)} 场")
