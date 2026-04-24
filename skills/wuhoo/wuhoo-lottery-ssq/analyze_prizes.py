
#!/usr/bin/env python3.11
"""分析500期回测中的大奖记录"""
import sys
sys.path.insert(0, '.')
from scripts.analysis_engine import load_data
from scripts.monte_carlo import (
    _compute_window_stats, backtest_strategy, PRIZE_STRUCTURE
)

df = load_data()
print("预计算窗口...")
stats_cache = _compute_window_stats(df, window_size=100, periods=500)
print(f"✅ {len(stats_cache)} 个窗口")

strategies = ['random', 'frequency_weighted', 'omission_recovery', 
              'statistical_filter', 'pattern_matching', 'integrated']

print("\n📊 回测策略并统计大奖...")
for s in strategies:
    print(f"  回测 {s}...")
    result = backtest_strategy(stats_cache, df, s, predict_count=5, periods=500, random_seed=42)
    print(f"  {s}: {result['periods']}期, {sum(result['wins'].values())}次中奖")
    print(f"  奖级分布: {dict(result['wins'])}")
    print(f"  ROI: {result['roi']}%, 总投入: {result['total_cost']}, 总奖金: {result['total_prize']}")
    
    # 显示高等级奖项
    high_prizes = [d for d in result['win_details'] if d['level'] <= 4]
    if high_prizes:
        print(f"  🏆 高等级奖项: {len(high_prizes)}次")
        for p in high_prizes[:5]:  # 只显示前5个
            prize = PRIZE_STRUCTURE[p['level']]
            print(f"    期号:{p['period']} {prize['desc']} ¥{prize['amount']}")
            print(f"    预测:{p['predicted']}+{p['blue_pred']} 实际:{p['actual']}+{p['blue_actual']}")
