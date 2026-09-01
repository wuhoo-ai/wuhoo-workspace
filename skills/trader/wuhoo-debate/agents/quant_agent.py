"""Quant Agent — statistical interpreter for debate v2.

Not an LLM agent by itself; wraps pattern_backtest results into a structured JSON
that gets injected into the Advocate Bull and Skeptic Bear prompts.

This is intentionally non-LLM to keep the statistical anchor objective.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.pattern_backtest import PatternBacktest


class QuantAgent:
    """Statistical analyst that queries pattern_backtest and formats results."""

    def __init__(self, market='cn'):
        self.market = market.lower()
        self.bt = PatternBacktest(market=self.market)

    def analyze(self, factor_data, regime=None):
        """Run pattern backtest and format as quant analysis JSON."""
        result = self.bt.query(factor_data, regime=regime)

        if not result or 'error' in result:
            return {
                'agent': 'quant',
                'error': result.get('error', 'unknown error') if result else 'no data',
                'forward_5d_win_rate': None,
                'statistical_edge': 'unknown',
                'sample_quality': 'none',
            }

        fwd5 = result.get('forward_5d') or {}
        fwd20 = result.get('forward_20d') or {}

        # Compute statistical edge
        win_rate = fwd5.get('win_rate', 0.5) if fwd5 else 0.5
        avg_ret = fwd5.get('avg_return', 0) if fwd5 else 0
        edge_raw = win_rate - (1 - win_rate)

        if edge_raw > 0.10:
            edge_label = 'significant_bullish'
        elif edge_raw > 0.05:
            edge_label = 'slight_bullish'
        elif edge_raw > -0.05:
            edge_label = 'neutral'
        elif edge_raw > -0.10:
            edge_label = 'slight_bearish'
        else:
            edge_label = 'significant_bearish'

        sample_size = fwd5.get('sample_size', 0) if fwd5 else 0
        if sample_size < 20:
            quality = 'low'
        elif sample_size < 50:
            quality = 'medium'
        else:
            quality = 'high'

        # Build regime note
        rb = result.get('regime_breakdown', {})
        regime_note_parts = []
        for r, stats in sorted(rb.items()):
            regime_note_parts.append(f"{r}: 胜率{stats['win_rate']*100:.0f}% 均值{stats['avg_return']:+.1f}%")
        regime_note = ' | '.join(regime_note_parts) if regime_note_parts else '无细分数据'

        # Build key finding
        key_parts = [f"基于{sample_size}个历史相似模式"]
        if fwd5:
            key_parts.append(f"5日胜率{win_rate*100:.0f}%，均值{avg_ret:+.2f}%")
        if fwd5 and fwd5.get('max_up') and fwd5.get('max_down'):
            key_parts.append(f"尾部风险：最大反弹+{fwd5['max_up']:.1f}%，最大下跌{fwd5['max_down']:.1f}%")

        return {
            'agent': 'quant',
            'symbol': factor_data.get('symbol', ''),
            'timestamp': factor_data.get('latest_date', ''),
            'forward_5d_win_rate': round(win_rate, 3),
            'forward_5d_avg_return': round(avg_ret, 2) if fwd5 else None,
            'forward_5d_max_up': fwd5.get('max_up') if fwd5 else None,
            'forward_5d_max_down': fwd5.get('max_down') if fwd5 else None,
            'forward_5d_sharpe': fwd5.get('sharpe') if fwd5 else None,
            'forward_20d_win_rate': round(fwd20.get('win_rate', 0), 3) if fwd20 else None,
            'forward_20d_avg_return': round(fwd20.get('avg_return', 0), 2) if fwd20 else None,
            'statistical_edge': edge_label,
            'edge_magnitude': round(edge_raw, 3),
            'sample_size': sample_size,
            'sample_quality': quality,
            'key_finding': '。'.join(key_parts) + '。',
            'regime_breakdown': result.get('regime_breakdown', {}),
            'regime_note': regime_note,
            'total_matches': result.get('total_matches', 0),
            'mean_distance': result.get('mean_distance', None),
            'query_factors': result.get('query_factors', {}),
        }


if __name__ == '__main__':
    # Quick test
    qa = QuantAgent('cn')
    factors = {
        'residual_vol': 50.82, 'momentum_5d': -11.25,
        'momentum_10d': -18.45, 'beta_20d': 2.25, 'turnover_5d': 3.92,
        'symbol': '002261.SZ', 'latest_date': '20260608'
    }
    result = qa.analyze(factors, regime='RANGING')
    print(json.dumps(result, ensure_ascii=False, indent=2))
