
import pandas as pd
import sys

url = 'https://raw.githubusercontent.com/martj42/international_results/master/results.csv'
print("Downloading data...")
df = pd.read_csv(url)
print(f"Total matches: {len(df)}")

# 过滤 2022 世界杯
wc2022 = df[(df['tournament'] == 'FIFA World Cup') & (df['date'].str.startswith('2022'))]
print(f"2022 World Cup: {len(wc2022)} matches")

# 过滤 2024 欧洲杯
euro2024 = df[(df['tournament'] == 'UEFA Euro') & (df['date'].str.startswith('2024'))]
print(f"2024 Euro: {len(euro2024)} matches")

# 保存
wc2022.to_csv('/home/admin/wuhoo-workspace/skills/football-predictor/data/worldcup_2022_full.csv', index=False)
euro2024.to_csv('/home/admin/wuhoo-workspace/skills/football-predictor/data/euro_2024_full.csv', index=False)

# 完整数据集（2018+）
recent = df[df['date'] >= '2018-01-01']
recent.to_csv('/home/admin/wuhoo-workspace/skills/football-predictor/data/international_full.csv', index=False)
print(f"Recent data (2018+): {len(recent)} matches")
print("Done!")
