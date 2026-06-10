#!/usr/bin/env python3.11
"""
Phase 0: 统计底座 — 历史因子相似度匹配与正向收益统计
=====================================================
为辩论框架 v2.0 提供统计锚定。给定股票因子 profile，
在历史因子数据中找到最相似的 K 个实例，统计 5日/20日 正向收益分布。

用法:
  python3.11 pattern_backtest.py --market cn --factors '{"residual_vol":50.8,"momentum_10d":-18.5,"beta_20d":2.25,"momentum_5d":-11.3}'
"""

import argparse, json, os, sys
from pathlib import Path
from collections import defaultdict
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import euclidean_distances

DATA_BASE = Path.home() / 'wuhoo-workspace' / 'data' / 'stock-pick'
REGIME_BASE = Path.home() / 'wuhoo-workspace' / 'data' / 'regime'

# Feature columns used for similarity matching
FEATURE_COLS = ['residual_vol', 'momentum_5d', 'momentum_10d', 'beta_20d', 'turnover_5d']


def _load_all_factors(market):
    """Load and concatenate all factor CSV files for a market."""
    prefix = f'factors_{market}_'
    files = sorted(DATA_BASE.glob(f'factors/{prefix}*.csv'))
    if not files:
        raise FileNotFoundError(f"No factor files for market={market}")
    dfs = []
    for f in files:
        date_str = f.stem.replace(prefix, '')
        try:
            df = pd.read_csv(f, encoding='utf-8-sig')
        except Exception:
            df = pd.read_csv(f, encoding='utf-8')
        df['factor_date'] = date_str
        dfs.append(df)
    combined = pd.concat(dfs, ignore_index=True)
    combined['ts_code'] = combined['ts_code'].astype(str).str.strip()
    return combined


def _load_price_index(market):
    """Build (ts_code, date) -> close price lookup."""
    daily_dirs = {
        'cn': DATA_BASE / 'daily_data',
        'us': DATA_BASE / 'daily_data_us',
        'hk': DATA_BASE / 'daily_data_hk',
    }
    base = daily_dirs.get(market, DATA_BASE / 'daily_data')
    price_map = {}
    
    col_map = {
        'cn': {'date_col': 'trade_date', 'code_col': 'ts_code', 'price_col': 'close'},
        'us': {'date_col': 'Date', 'code_col': 'ts_code', 'price_col': 'Close'},
        'hk': {'date_col': 'time_key', 'code_col': 'ts_code', 'price_col': 'close'},
    }
    cols = col_map.get(market, col_map['cn'])
    
    for csv_file in sorted(base.rglob('*.csv')):
        try:
            df = pd.read_csv(csv_file)
            if cols['date_col'] not in df.columns:
                continue
            for _, row in df.iterrows():
                code = str(row[cols['code_col']]).strip()
                date_val = str(row[cols['date_col']]).strip().replace('-', '')
                price = float(row[cols['price_col']])
                if price > 0 and len(date_val) == 8:
                    price_map[(code, date_val)] = price
        except Exception:
            continue
    return price_map


def _load_regimes():
    regimes = {}
    for f in sorted(REGIME_BASE.glob('regime_all_*.json')):
        try:
            data = json.loads(f.read_text())
            date = f.stem.replace('regime_all_', '')
            regimes[date] = {}
            for mkt, info in data.items():
                regimes[date][mkt.upper()] = info.get('regime', 'UNKNOWN')
        except Exception:
            continue
    return regimes


class PatternBacktest:
    """Similarity-based statistical pattern matcher."""
    
    def __init__(self, market='cn', top_k=50):
        self.market = market.lower()
        self.top_k = top_k
        print(f"[PatternBacktest] Loading {market} data...", file=sys.stderr)
        
        self.factors_df = _load_all_factors(self.market)
        print(f"  Factors: {len(self.factors_df)} rows, {self.factors_df['factor_date'].nunique()} dates", file=sys.stderr)
        
        self.price_map = _load_price_index(self.market)
        print(f"  Prices: {len(self.price_map)} entries", file=sys.stderr)
        
        self.regimes = _load_regimes()
        
        # Prepare feature matrix for fast similarity search
        self._prepare_features()
        print(f"  Feature matrix: {self.X.shape} ready", file=sys.stderr)
    
    def _prepare_features(self):
        """Build normalized feature matrix and forward returns."""
        df = self.factors_df
        self.records = []  # metadata for each row
        self.y_5d = []     # forward 5d returns
        self.y_20d = []    # forward 20d returns
        X_list = []        # feature rows (list of lists)
        
        all_dates = sorted(df['factor_date'].unique())
        
        for idx, row in df.iterrows():
            code = str(row['ts_code']).strip()
            date = str(row['factor_date']).strip()
            
            # Current price
            if (code, date) not in self.price_map:
                continue
            p0 = self.price_map[(code, date)]
            
            # Forward returns
            date_idx = all_dates.index(date) if date in all_dates else -1
            if date_idx < 0:
                continue
            
            fwd_5d = None
            if date_idx + 5 < len(all_dates):
                d5 = all_dates[date_idx + 5]
                if (code, d5) in self.price_map:
                    fwd_5d = (self.price_map[(code, d5)] - p0) / p0
            
            fwd_20d = None
            if date_idx + 20 < len(all_dates):
                d20 = all_dates[date_idx + 20]
                if (code, d20) in self.price_map:
                    fwd_20d = (self.price_map[(code, d20)] - p0) / p0
            
            if fwd_5d is None and fwd_20d is None:
                continue
            
            # Extract features
            feats = []
            for col in FEATURE_COLS:
                val = row.get(col, np.nan)
                feats.append(float(val) if pd.notna(val) and str(val) != 'nan' else 0.0)
            
            self.records.append({
                'ts_code': code,
                'date': date,
                'fwd_5d': fwd_5d,
                'fwd_20d': fwd_20d,
                'regime': self._get_regime(date),
            })
            self.y_5d.append(fwd_5d)
            self.y_20d.append(fwd_20d)
            X_list.append(feats)
        
        self.X = np.array(X_list)
        self.scaler = StandardScaler()
        self.X_scaled = self.scaler.fit_transform(self.X)
    
    def _get_regime(self, date_str):
        candidates = [d for d in self.regimes if d <= date_str]
        if not candidates:
            return 'UNKNOWN'
        closest = max(candidates)
        return self.regimes[closest].get(self.market.upper(), 'UNKNOWN')
    
    def query(self, factors, regime=None):
        """
        Query historical stats for a factor profile.
        Returns top-K similar historical patterns and their forward return stats.
        """
        # Build query vector
        query_vec = []
        for col in FEATURE_COLS:
            val = factors.get(col, 0)
            query_vec.append(float(val) if val is not None else 0.0)
        query_vec = np.array([query_vec])
        
        # Normalize and compute distances
        query_scaled = self.scaler.transform(query_vec)
        distances = euclidean_distances(query_scaled, self.X_scaled)[0]
        
        # Get top K
        top_indices = np.argsort(distances)[:self.top_k]
        
        matches = []
        for i in top_indices:
            if distances[i] > 3.0:  # Skip very dissimilar
                continue
            rec = self.records[i]
            matches.append({
                'ts_code': rec['ts_code'],
                'date': rec['date'],
                'distance': round(float(distances[i]), 3),
                'fwd_5d': rec['fwd_5d'],
                'fwd_20d': rec['fwd_20d'],
                'regime': rec['regime'],
            })
        
        if not matches:
            return {"error": "no similar patterns found in historical data"}
        
        # Filter by regime if specified
        regime_matches = [m for m in matches if m['regime'] == regime] if regime else []
        
        result = {
            'query_factors': {k: factors.get(k, None) for k in FEATURE_COLS},
            'total_matches': len(matches),
            'mean_distance': round(float(np.mean([m['distance'] for m in matches])), 3),
            'forward_5d': self._summarize_returns([m['fwd_5d'] for m in matches if m['fwd_5d'] is not None]),
            'forward_20d': self._summarize_returns([m['fwd_20d'] for m in matches if m['fwd_20d'] is not None]),
            'regime_breakdown': self._regime_breakdown(matches),
        }
        
        if regime_matches and len(regime_matches) >= 5:
            result['regime_filtered'] = {
                'regime': regime,
                'sample_size': len(regime_matches),
                'forward_5d': self._summarize_returns([m['fwd_5d'] for m in regime_matches if m['fwd_5d'] is not None]),
            }
        
        return result
    
    @staticmethod
    def _summarize_returns(returns):
        if not returns:
            return None
        arr = np.array([r for r in returns if r is not None])
        if len(arr) < 3:
            return None
        return {
            'sample_size': len(arr),
            'win_rate': round(float(np.mean(arr > 0)), 3),
            'avg_return': round(float(np.mean(arr)) * 100, 2),
            'median_return': round(float(np.median(arr)) * 100, 2),
            'max_up': round(float(np.max(arr)) * 100, 2),
            'max_down': round(float(np.min(arr)) * 100, 2),
            'std': round(float(np.std(arr)) * 100, 2),
            'sharpe': round(float(np.mean(arr) / np.std(arr)) * np.sqrt(252), 2) if np.std(arr) > 0 else 0,
        }
    
    @staticmethod
    def _regime_breakdown(matches):
        regime_groups = defaultdict(list)
        for m in matches:
            if m['fwd_5d'] is not None:
                regime_groups[m['regime']].append(m['fwd_5d'])
        
        result = {}
        for r, rets in sorted(regime_groups.items()):
            if len(rets) >= 3:
                arr = np.array(rets)
                result[r] = {
                    'sample_size': len(arr),
                    'win_rate': round(float(np.mean(arr > 0)), 3),
                    'avg_return': round(float(np.mean(arr)) * 100, 2),
                }
        return result


def main():
    parser = argparse.ArgumentParser(description='Pattern backtest for debate v2')
    parser.add_argument('--market', default='cn', choices=['cn', 'us', 'hk'])
    parser.add_argument('--factors', type=str, help='JSON factor dict')
    parser.add_argument('--factors-json', type=str, help='Path to factor JSON file')
    parser.add_argument('--regime', type=str, default=None,
                        help='Filter by regime (BULL_TRENDING, RANGING, BEAR_TRENDING, etc.)')
    parser.add_argument('--top-k', type=int, default=50, help='Number of similar patterns to match')
    args = parser.parse_args()
    
    bt = PatternBacktest(market=args.market, top_k=args.top_k)
    
    # Load factors
    if args.factors_json:
        with open(args.factors_json) as f:
            factors = json.load(f)
    elif args.factors:
        factors = json.loads(args.factors)
    else:
        print("ERROR: --factors or --factors-json required", file=sys.stderr)
        sys.exit(1)
    
    result = bt.query(factors, regime=args.regime)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
