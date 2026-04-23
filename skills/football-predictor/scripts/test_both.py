from backtest import Backtester

bt = Backtester()

print("=" * 50)
print("2022 世界杯回测")
print("=" * 50)
bt.run_backtest("worldcup", 2022)

print()
print()
print("=" * 50)
print("2024 欧洲杯回测")
print("=" * 50)
bt.run_backtest("euro", 2024)
