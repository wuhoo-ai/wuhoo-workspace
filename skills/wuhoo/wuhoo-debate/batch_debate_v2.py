#!/usr/bin/env python3.11
"""
batch_debate_v2.py — 辩论框架 v2.0 批量管线
============================================
4-Phase pipeline: Quant → Advocate Bull → Skeptic Bear → Trader v2

改进:
- Phase 0: 统计底座 (pattern_backtest) 为所有后续阶段提供锚定
- Bull 改为辩护律师（禁止 SELL）
- Bear 改为逐条反驳（不重复因子数据）
- Trader 改为概率+Kelly决策（不做方向预测）

用法:
  export $(grep -v '^#' ~/.hermes/.env | xargs)
  python3.11 batch_debate_v2.py --date 20260608 --market cn --workers 2
"""

import argparse, json, os, sys, time, re
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

# ── Paths ────────────────────────────────────
DEBATE_DIR = Path(__file__).parent
AGENTS_DIR = DEBATE_DIR / 'agents'
PROMPTS_DIR = DEBATE_DIR / 'prompts'
SCRIPTS_DIR = DEBATE_DIR / 'scripts'
DATA_BASE = Path.home() / 'wuhoo-workspace' / 'data' / 'stock-pick'
DEBATE_OUT = Path.home() / 'wuhoo-workspace' / 'data' / 'debate'

sys.path.insert(0, str(DEBATE_DIR))
sys.path.insert(0, str(AGENTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent
from agents.trader_v2_agent import TraderV2Agent
from agents.quant_agent import QuantAgent

# ── Market config ────────────────────────────
MARKET_CONFIG = {
    'cn': {'prefix': 'cn', 'account': '18767295'},
    'hk': {'prefix': 'hk', 'account': '18767294'},
    'us': {'prefix': 'us', 'account': '18767293'},
}


def load_factors(date_str, market):
    """Load factor data from stock-pick results CSV (prefer result over full factors)."""
    # Prefer result file (selected stocks) over full factor file (500+ stocks)
    csv_path = DATA_BASE / 'factors' / f'result_{market}_{date_str}.csv'
    if not csv_path.exists():
        csv_path = DATA_BASE / 'factors' / f'factors_{market}_{date_str}.csv'
    if not csv_path.exists():
        raise FileNotFoundError(f"No factor file for {market} on {date_str}")
    
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    
    stocks = []
    for _, row in df.iterrows():
        code = str(row['ts_code']).strip()
        stocks.append({
            'symbol': code,
            'name': str(row.get('name', code)),
            'factor_data': {
                'residual_vol': float(row.get('residual_vol', row.get('volatility', 30))),
                'turnover_5d': float(row.get('turnover_5d', 0)),
                'momentum_5d': float(row.get('momentum_5d', 0)),
                'beta_20d': float(row.get('beta_20d', 1.0)),
                'momentum_10d': float(row.get('momentum_10d', 0)),
            }
        })
    
    return stocks


def load_regime(date_str):
    """Load market regime for the given date."""
    regime_file = REGIME_OUT = Path.home() / 'wuhoo-workspace' / 'data' / 'regime' / f'regime_all_{date_str}.json'
    if regime_file.exists():
        data = json.loads(regime_file.read_text())
        return data
    return {}


def debate_single(quant_agent, bull_agent, bear_agent, trader_agent, stock, regime=None):
    """Run full 4-phase debate for a single stock."""
    symbol = stock['symbol']
    name = stock['name']
    factor_data = stock['factor_data']
    start = time.time()
    
    try:
        # Phase 0: Quant — statistical anchor
        t0 = time.time()
        quant_result = quant_agent.analyze(factor_data, regime=regime)
        quant_time = time.time() - t0
        
        # Inject quant stats into fundamental_data for agents to see
        fundamental = {
            'name': name,
            'pattern_stats': json.dumps(quant_result, ensure_ascii=False, indent=2),
        }
        
        # Phase 1: Advocate Bull
        t1 = time.time()
        bull_view = bull_agent.analyze(
            symbol, factor_data=factor_data,
            technical_data={}, sentiment_data={},
            fundamental_data=fundamental
        )
        bull_time = time.time() - t1
        
        # Phase 2: Skeptic Bear
        t2 = time.time()
        bear_view = bear_agent.analyze(
            symbol, factor_data=factor_data,
            technical_data={}, sentiment_data={},
            fundamental_data=fundamental,
            bull_view=bull_view
        )
        bear_time = time.time() - t2
        
        # Phase 3: Trader v2 (with quant stats)
        t3 = time.time()
        trader_decision = trader_agent.make_decision(
            symbol,
            bull_view=bull_view,
            bear_view=bear_view,
            consensus_points=bull_view.get('key_points', [])[:2],
            disagreement_points=[],
            quant_stats=quant_result,
        )
        trader_time = time.time() - t3
        
        total_time = round(time.time() - start, 1)
        
        result = {
            'symbol': symbol,
            'name': name,
            'factor_data': factor_data,
            'quant': quant_result,
            'bull': bull_view,
            'bear': bear_view,
            'trader': trader_decision,
            'timing': {
                'quant_s': round(quant_time, 1),
                'bull_s': round(bull_time, 1),
                'bear_s': round(bear_time, 1),
                'trader_s': round(trader_time, 1),
                'total_s': total_time,
            },
            'version': 'v2.0',
        }
        
        return result
    
    except Exception as e:
        import traceback
        return {
            'symbol': symbol,
            'name': name,
            'error': str(e),
            'traceback': traceback.format_exc()[-500:],
            'elapsed_s': round(time.time() - start, 1),
        }


def run_batch(date_str, market, workers=2):
    """Run debate v2 pipeline for all stocks in a market on a given date."""
    
    # Load data
    stocks = load_factors(date_str, market)
    print(f"[Batch] {market.upper()} {date_str}: {len(stocks)} stocks, {workers} workers")
    
    regimes = load_regime(date_str)
    market_regime = regimes.get(market.upper(), {}).get('regime', None) if regimes else None
    print(f"[Batch] Market regime: {market_regime or 'UNKNOWN'}")
    
    # Initialize Quant agent (shared — loads PatternBacktest once)
    print(f"[Batch] Loading Quant agent (pattern backtest)...")
    t_start = time.time()
    quant_agent = QuantAgent(market=market)
    print(f"[Batch] Quant agent ready ({time.time()-t_start:.0f}s)")
    
    # Initialize LLM agents with new prompts
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    api_base = os.environ.get('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
    
    bull_prompt = str(PROMPTS_DIR / 'advocate_bull.md')
    bear_prompt = str(PROMPTS_DIR / 'skeptic_bear.md')
    trader_prompt = str(PROMPTS_DIR / 'trader_v2.md')
    
    # Run debate
    results = []
    errors = []
    
    if workers <= 1:
        # Sequential mode
        for stock in stocks:
            r = debate_single(quant_agent, None, None, None, None, stock, regime=market_regime)
            # Need to create agents per stock due to shared state concerns
            # Actually, let's create agents once and reuse
            pass
    
    # Parallel mode — create agents inside each thread to avoid shared state
    def _debate_with_agents(stock):
        # Create fresh agents per thread (LLM clients not thread-safe for shared state)
        bull = BullAgent(prompt_path=bull_prompt, model='deepseek-v4-pro',
                         api_key=api_key, api_base=api_base, provider='openai')
        bear = BearAgent(prompt_path=bear_prompt, model='deepseek-v4-pro',
                         api_key=api_key, api_base=api_base, provider='openai')
        trader = TraderV2Agent(prompt_path=trader_prompt, model='deepseek-v4-pro',
                             api_key=api_key, api_base=api_base, provider='openai')
        return debate_single(quant_agent, bull, bear, trader, stock, regime=market_regime)
    
    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_debate_with_agents, s): s for s in stocks}
        for future in as_completed(futures):
            stock = futures[future]
            try:
                result = future.result()
                if 'error' in result:
                    errors.append(result)
                    print(f"  ❌ {result['symbol']}: {result['error'][:80]}")
                else:
                    results.append(result)
                    t = result['trader']
                    p_up = t.get('P_up', None)
                    p_up_str = f"{p_up:.2f}" if isinstance(p_up, (int, float)) else str(p_up)
                    print(f"  ✅ {result['symbol']:15s} {result['name'][:8]:8s} "
                          f"Q={result['quant']['statistical_edge']:20s} "
                          f"Bull={result['bull']['recommendation']:4s}({result['bull']['confidence']:.2f}) "
                          f"Bear={result['bear']['recommendation']:4s}({result['bear']['confidence']:.2f}) "
                          f"Trader={t['decision']:4s} P={p_up_str:>6s} "
                          f"[{result['timing']['total_s']:.0f}s]")
            except Exception as e:
                errors.append({'symbol': stock['symbol'], 'error': str(e)})
                print(f"  ❌ {stock['symbol']}: {e}")
            completed += 1
    
    # Save summary
    out_dir = DEBATE_OUT / date_str / 'deepseek_v2'
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Save individual results
    for r in results:
        sym_file = r['symbol'].replace('.', '_')
        with open(out_dir / f'debate_{sym_file}.json', 'w') as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
    
    # Generate summary
    summary = {
        'metadata': {
            'date': date_str,
            'market': market,
            'version': 'v2.0',
            'total_stocks': len(stocks),
            'completed': len(results),
            'errors': len(errors),
            'workers': workers,
            'generated_at': datetime.now().isoformat(),
        },
        'statistics': _compute_statistics(results),
        'results': [{
            'symbol': r['symbol'],
            'name': r['name'],
            'quant_edge': r.get('quant', {}).get('statistical_edge'),
            'bull': r.get('bull', {}).get('recommendation', 'ERROR'),
            'bull_conf': r.get('bull', {}).get('confidence', 0),
            'bear': r.get('bear', {}).get('recommendation', 'ERROR'),
            'bear_conf': r.get('bear', {}).get('confidence', 0),
            'trader': r.get('trader', {}).get('decision', 'ERROR'),
            'trader_P_up': r.get('trader', {}).get('P_up'),
            'trader_position': r.get('trader', {}).get('position_size'),
        } for r in results],
        'errors': [{'symbol': e['symbol'], 'error': e['error'][:200]} for e in errors],
    }
    
    with open(out_dir / 'debate_summary.json', 'w') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # Print summary
    stats = summary['statistics']
    print(f"\n{'='*60}")
    print(f"完成: {len(results)}/{len(stocks)} | 错误: {len(errors)}")
    print(f"决策分布: BUY={stats['buy']} SKIP={stats['skip']} HOLD={stats['hold']}")
    print(f"Bull分布: BUY={stats['bull_buy']} HOLD={stats['bull_hold']} SELL={stats['bull_sell']}")
    print(f"Bear分布: BUY={stats['bear_buy']} HOLD={stats['bear_hold']} SELL={stats['bear_sell']}")
    print(f"输出: {out_dir}/")
    
    return summary


def _compute_statistics(results):
    """Compute summary statistics from debate results."""
    stats = {
        'buy': 0, 'skip': 0, 'hold': 0,
        'bull_buy': 0, 'bull_hold': 0, 'bull_sell': 0,
        'bear_buy': 0, 'bear_hold': 0, 'bear_sell': 0,
    }
    for r in results:
        # Trader decision
        d = r['trader'].get('decision', 'HOLD')
        stats[d.lower()] = stats.get(d.lower(), 0) + 1
        
        # Bull (should never SELL, but count anyway)
        b = r['bull'].get('recommendation', 'HOLD')
        key = f'bull_{b.lower()}'
        stats[key] = stats.get(key, 0) + 1
        
        # Bear
        br = r['bear'].get('recommendation', 'HOLD')
        key = f'bear_{br.lower()}'
        stats[key] = stats.get(key, 0) + 1
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Batch debate v2.0 pipeline')
    parser.add_argument('--date', required=True, help='Factor date (YYYYMMDD)')
    parser.add_argument('--market', default='cn', choices=['cn', 'hk', 'us'])
    parser.add_argument('--workers', type=int, default=2, help='Parallel workers')
    args = parser.parse_args()
    
    run_batch(args.date, args.market, workers=args.workers)


if __name__ == '__main__':
    main()
