
#!/usr/bin/env python3.11
"""分析大奖特征并设计搏大奖策略"""
import sys
sys.path.insert(0, '.')
import random
import numpy as np
from scripts.analysis_engine import load_data, analyze_frequency, analyze_omission
from scripts.monte_carlo import check_prize, PRIZE_STRUCTURE

df = load_data()

# 分析最近100期的热号和遗漏
recent_100 = df.tail(100)
freq = analyze_frequency(recent_100)
omission = analyze_omission(df)

print("🔥 最近100期热号:")
print(f"  红球: {freq['hot_red']}")
print(f"  蓝球: {freq['hot_blue']}")

print("\n❄️ 高遗漏红球:")
print(f"  {omission['high_omission_red'][:10]}")

print("\n💡 搏大奖策略设计:")
print("1. 红球选择: 热号(60%) + 温号(30%) + 冷号(10%)")
print("2. 蓝球选择: 全包(16个) 或 热号+遗漏回补")
print("3. 投注方式: 胆拖/复式")

# 模拟不同策略的期望值
print("\n🎲 策略模拟:")

# 策略1: 热号集中 (选最热12个红球，随机组合)
hot_reds = [int(x) for x in freq['hot_red'][:12]]
print(f"\n策略1 - 热号集中 (红球池:{hot_reds}):")
for _ in range(3):
    reds = sorted(random.sample(hot_reds, 6))
    blue = random.randint(1, 16)
    print(f"  {reds}+{blue}")

# 策略2: 胆拖 (3个胆码 + 9个拖码)
胆码 = [int(x) for x in freq['hot_red'][:3]]
拖码 = [int(x) for x in freq['hot_red'][3:12]]
print(f"\n策略2 - 胆拖 (胆:{胆码}, 拖:{拖码}):")
# 胆拖组合数: C(9,3) = 84注
import itertools
combos = list(itertools.combinations(拖码, 3))
print(f"  组合数: {len(combos)}注 (成本: {len(combos)*2}元)")
# 显示前3个组合
for combo in combos[:3]:
    reds = sorted(胆码 + list(combo))
    print(f"  {reds}")
