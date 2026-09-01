
#!/usr/bin/env python3.11
import sys
sys.path.insert(0, '.')
from scripts.analysis_engine import load_data
from scripts.monte_carlo import _compute_window_stats, backtest_strategy, PRIZE_STRUCTURE

df = load_data()
print('预计算窗口...')
stats_cache = _compute_window_stats(df, window_size=100, periods=500)

# 回测所有策略并收集大奖详情
strategies = ['random', 'frequency_weighted', 'big_prize']

for s in strategies:
    print(f'\n回测 {s}...')
    result = backtest_strategy(stats_cache, df, s, predict_count=5, periods=500, random_seed=42)
    print(f'  奖级分布: {dict(result["wins"])}')
    print(f'  ROI: {result["roi"]}%, 总奖金: {result["total_prize"]}')
    
    # 显示高等级奖项
    high = [d for d in result['win_details'] if d['level'] <= 4]
    if high:
        print(f'  🏆 高等级奖项 {len(high)}次:')
        for d in high[:5]:
            prize = PRIZE_STRUCTURE[d['level']]
            print(f'    {d["period"]} {prize["desc"]} ¥{prize["amount"]}')
            red_match = len(set(d['predicted']) & set(d['actual']))
            blue_match = 1 if d['blue_pred'] == d['blue_actual'] else 0
            print(f'    预测:{d["predicted"]}+{d["blue_pred"]} 实际:{d["actual"]}+{d["blue_actual"]}')
            print(f'    匹配: 红{red_match} 蓝{blue_match}')
