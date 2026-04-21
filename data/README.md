# 全市场股票数据

## 目录结构
```
data/
├── cn/                          # A股
│   ├── daily/                   # 日线 (OHLCV + MA/EMA/RSI/DIF等技术指标)
│   ├── hourly/                  # 小时线
│   └── stock_info.csv           # 股票基本信息
├── hk/                          # 港股
│   ├── daily/                   # 日线 (OHLCV)
│   └── stock_info.csv           # 港股500成分股信息
├── us/                          # 美股
│   ├── daily/                   # 日线 (待补充)
│   ├── factors/                 # 选股因子数据
│   ├── stock_info.csv           # 美股500成分股信息
│   └── index_members.csv        # 指数成分股
└── README.md
```

## 数据来源
- A股: akshare (通过 wuhoo-stock-pick skill)
- 港股: akshare
- 美股: yfinance / akshare

## 更新频率
每日收盘后自动更新 (cron job)

## 数据格式
- A股日线: stock_name, stock_code, trade_date, open, close, high, low, volume, amount, MA_5/10/20/60, EMA_5/10/20/60, RSI, DIF, DEA, ATR, OBV
- 港股日线: ts_code, time_key, open, close, high, low, volume, turnover_rate, turnover
- 美股因子: 各因子列 + 筛选结果
