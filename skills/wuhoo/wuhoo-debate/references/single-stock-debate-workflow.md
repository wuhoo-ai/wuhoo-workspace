# Single-Stock Manual Debate Workflow

Use when a user requests debate on a stock **not in any batch pick result** — no precomputed factor data, no Tushare daily_data CSV.

## When This Applies

- User asks "analyze/debate stock X" and X is not in recent `result_{market}_{date}.csv`
- X is not in `~/wuhoo-workspace/data/stock-pick/daily_data/` (Tushare)
- Need to source factor data from akshare directly

## Step 1: Get Price Data & Compute Factors

```bash
python3.11 -c "
import akshare as ak
import pandas as pd
import numpy as np
import json

code = '002261'  # 6-digit A-share code

# Exchange prefix for sina endpoint: 6xx→sh, 0xx/3xx→sz, 8xx→sh (科创)
exch = 'sh' if code.startswith(('6', '8')) else 'sz'
# Primary: sina endpoint (reliable, fallback when East Money fails)
df = ak.stock_zh_a_daily(symbol=exch + code, start_date='20260101', end_date='20260609', adjust='qfq')

closes = df['close'].values
price = float(df.iloc[-1]['close'])

# momentum
momentum_5d = round((closes[-1] / closes[-6] - 1) * 100, 2)
momentum_10d = round((closes[-1] / closes[-11] - 1) * 100, 2)

# turnover (5-day avg)
turnover_5d = round(float(df['turnover'].tail(5).mean()) * 100, 2)

# residual_vol: 30-day annualized std of returns
import numpy as np
rets = np.diff(closes[-31:]) / closes[-31:-1]
residual_vol = round(np.std(rets) * np.sqrt(252) * 100, 2)

# beta vs index
idx = ak.stock_zh_a_daily(symbol='sh000001', start_date='20260501', end_date='20260609', adjust='')
idx_c = idx['close'].values
ml = min(22, len(closes), len(idx_c))
sr = np.diff(closes[-ml:]) / closes[-ml:-1]
ir = np.diff(idx_c[-ml:]) / idx_c[-ml:-1]
cov = np.cov(sr, ir)[0][1]; var = np.var(ir)
beta_20d = round(cov / var, 2) if var > 0 else 1.0

# name
info = ak.stock_profile_cninfo(symbol=code)
name = info[info['item'] == '公司名称']['value'].values[0]

factors = {
    'symbol': f'{code}.SZ',
    'name': name,
    'latest_price': price,
    'momentum_5d': momentum_5d,
    'momentum_10d': momentum_10d,
    'turnover_5d': turnover_5d,
    'residual_vol': residual_vol,
    'beta_20d': beta_20d,
}
json.dump(factors, open('/tmp/debate_factors.json', 'w'), ensure_ascii=False, indent=2)
print(json.dumps(factors, ensure_ascii=False, indent=2))
"
```

**Key pitfalls:**
- `stock_zh_a_hist()` (East Money) may fail with `RemoteDisconnected` → use `stock_zh_a_daily()` (sina) instead
- `stock_zh_a_daily()` requires **exchange prefix**: `sz` for Shenzhen (002xxx/300xxx), `sh` for Shanghai (600xxx/688xxx). Detect with `'sh' if code.startswith(('6','8')) else 'sz'`
- `np.diff(closes[-31:]) / closes[-31:-1]` — diff of 31 gives 30 returns; divisor must be 30 elements too
- Beta requires index data (sh000001); allow 60s timeout for the extra API call
- `stock_zh_a_daily` column names are lowercase: `close`, `volume`, `turnover` (not `收盘`/`成交量`/`换手率` like East Money)

## Step 2: Run the Debate

Write to `/tmp/run_debate.py` and execute:

```python
import sys, os, json, time
sys.path.insert(0, os.path.expanduser('~/wuhoo-workspace/skills/wuhoo/wuhoo-debate'))
from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent

with open('/tmp/debate_factors.json') as f:
    factors = json.load(f)

api_key = os.environ['DEEPSEEK_API_KEY']
api_base = 'https://api.deepseek.com/v1'
symbol = factors['symbol']
name = factors['name']

fd = {k: factors[k] for k in ['residual_vol','turnover_5d','momentum_5d','beta_20d','momentum_10d','latest_price']}

bull = BullAgent(model='deepseek-v4-pro', api_base=api_base, api_key=api_key, provider='openai')
bear = BearAgent(model='deepseek-v4-pro', api_base=api_base, api_key=api_key, provider='openai')
trader = TraderAgent(model='deepseek-v4-pro', api_base=api_base, api_key=api_key, provider='openai')

# Phase 1-4 (expect ~3-4 min total)
bull_view = bull.analyze(symbol, factor_data=fd, technical_data={}, sentiment_data={}, fundamental_data={'name': name, 'price': fd['latest_price']})
bear_view = bear.analyze(symbol, factor_data=fd, technical_data={}, sentiment_data={}, fundamental_data={'name': name, 'price': fd['latest_price']}, bull_view=bull_view)
bull_rebuttal = bull.analyze_with_context(symbol, data={'factor_data': fd, 'technical_data': {}, 'sentiment_data': {}, 'fundamental_data': {'name': name, 'price': fd['latest_price']}}, bear_view=bear_view)
trader_decision = trader.make_decision(symbol, bull_view=bull_rebuttal, bear_view=bear_view, consensus_points=[], disagreement_points=[])

# Save
date_str = factors.get('latest_date', time.strftime('%Y%m%d')).replace('-', '')
out_dir = os.path.expanduser(f'~/wuhoo-workspace/data/debate/{date_str}/deepseek/')
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, f'debate_{symbol.replace(".", "_")}.json')
result = {'symbol': symbol, 'name': name, 'factor_data': fd, 'bull': bull_view, 'bear': bear_view, 'bull_rebuttal': bull_rebuttal, 'trader': trader_decision}
json.dump(result, open(out_file, 'w'), ensure_ascii=False, indent=2)
print(f"Saved: {out_file}")
```

Run: `export $(grep -v '^#' ~/.hermes/.env | xargs) && python3.11 /tmp/run_debate.py`

## Step 3: Recover from Trader JSON Parse Failure

If Trader outputs natural-language reasoning instead of JSON (`ValueError: Failed to parse JSON from: ...`), the bull/bear/rebuttal phases are still valid. **Retry only Trader** by passing the saved views directly:

```python
# After Step 2 failure, save bull/bear views manually then retry:
trader = TraderAgent(model='deepseek-v4-pro', api_base=api_base, api_key=api_key, provider='openai')
trader_decision = trader.make_decision(
    symbol,
    bull_view=bull_rebuttal,   # from Step 2 output
    bear_view=bear_view,       # from Step 2 output
    consensus_points=["双动量深度负值", "残差波极端异常"],
    disagreement_points=[]
)
# Save the completed result
```

This avoids re-running the expensive bull/bear/rebuttal phases (~60s each) when only Trader (~20s) failed.

## Step 4: Integrate with Deep Analysis

`deep_analysis.py --code XXXXXX --market cn` reads debate JSON from `data/debate/{date}/deepseek/debate_{CODE}_{EXCH}.json`. **Must run debate FIRST**, then deep_analysis — running in parallel causes deep_analysis to use degraded simplified debate (rule-based, not LLM).
