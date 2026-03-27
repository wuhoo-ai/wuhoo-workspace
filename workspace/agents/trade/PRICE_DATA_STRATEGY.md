# Workflow C 价格获取与交易执行策略

**更新时间**: 2026-03-27
**状态**: ✅ 统一富途 OpenAPI 方案

---

## 价格获取策略

根据市场不同，使用不同的数据源获取股票价格：

| 市场 | 优先数据源 | 备用数据源 | 说明 |
|------|------------|------------|------|
| **港股 (HK)** | 富途 API | - | 实时行情，需要港股行情权限 |
| **A 股 (CN)** | 富途 API → 本地 CSV | - | 有行情权限用富途，无权限用本地数据 |
| **美股 (US)** | yfinance | - | Yahoo Finance 免费数据 |

---

## 交易执行策略

### 统一富途 OpenAPI 方案

**架构决策**: 使用直接富途 OpenAPI，弃用 VnPy

| 市场 | 交易接口 | 账户 | 订单类型 |
|------|----------|------|----------|
| **A 股 (CN)** | OpenCNTradeContext | 18767295 | DAY (当日有效) |
| **港股 (HK)** | OpenHKTradeContext | 18767294 | GTC (好至取消) |
| **美股 (US)** | OpenUSTradeContext | 动态获取 | GTC |

### 为什么选择直接 API？

**原因**:
1. **简单直接** - 无额外依赖，代码易理解
2. **账户隔离清晰** - 每个市场使用独立交易上下文
3. **无需补丁** - 官方 API 稳定，无需维护技术债务
4. **业务匹配** - Workflow C 不需要 VnPy 的事件驱动特性

**详细说明**: 参见 `ARCHITECTURE_COMPARISON.md`

---

## 数据源说明

### 1. 港股 - 富途 API

```python
from futu import OpenQuoteContext

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, snapshot = quote_ctx.get_market_snapshot('HK.00700')
if ret == 0:
    price = snapshot['last_price'].iloc[0]
```

**要求**: 需要在富途 APP 开通港股行情权限

---

### 2. A 股 - 本地数据文件

**数据路径**: `~/.openclaw/workspace/agents/main/data/stock-pick/daily_data/2026/202603.csv`

**数据格式**:
```csv
ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount,year_month
603220.SH,20260323,24.77,25.78,23.96,24.1,25.84,-1.74,-6.7337,384731.91,955600.49,202603
```

**代码示例**:
```python
import pandas as pd

df = pd.read_csv('daily_data/2026/202603.csv')
# 富途格式 SH.603220 → ts_code: 603220.SH
ts_code = f"{full_code.split('.')[1]}.{full_code.split('.')[0]}"
stock_rows = df[df['ts_code'] == ts_code]
price = float(stock_rows.iloc[0]['close'])
```

**数据更新**: 通过 `fetch_global_members.py` 或 Tushare API 定期更新

---

### 3. 美股 - yfinance

**安装**: `pip install yfinance` (已在 venv-futu 中安装，版本 1.2.0)

**代码示例**:
```python
import yfinance as yf

ticker = yf.Ticker('AAPL')
info = ticker.info
price = info.get('regularMarketPrice')  # 实时价格
market_cap = info.get('marketCap')      # 市值
```

**数据格式转换**:
- 富途格式：`US.AAPL`
- yfinance 格式：`AAPL`

---

## Workflow C 集成

### 代码位置

`workflow_c_multi_market.py` - `step5_execute_trades()` 方法

### 执行逻辑

```python
# 1. 根据市场推导代码格式
if market == 'cn':
    full_code = 'SH.603220'  # 富途格式
elif market == 'hk':
    full_code = 'HK.00700'
elif market == 'us':
    full_code = 'US.AAPL'

# 2. 根据市场选择数据源
if market == 'hk':
    # 富途 API
    price = futu_get_snapshot(full_code)
elif market == 'cn':
    # 先尝试富途，失败则用本地数据
    price = futu_get_snapshot(full_code) or local_csv_get(full_code)
elif market == 'us':
    # yfinance
    symbol = full_code.replace('US.', '')
    price = yf.Ticker(symbol).info['regularMarketPrice']

# 3. 限价设置
if market == 'cn':
    # A 股平价下单
    order_price = round(price, 2)
else:
    # 港股/美股高 1% 确保成交
    order_price = round(price * 1.01, 2)
```

---

## 数据源优先级总结

| 场景 | 数据源选择 | 原因 |
|------|------------|------|
| 港股交易 | 富途 API | 最准确，实时数据 |
| A 股交易 (有权限) | 富途 API | 实时数据 |
| A 股交易 (无权限) | 本地 CSV | 无需行情权限 |
| 美股交易 | yfinance | 免费，无需富途权限 |

---

## 相关 MCP/Skill

### 已安装
- **yfinance**: v1.2.0 - 美股数据
- **futu-api**: 港股/A 股数据
- **tushare**: A 股历史数据

### 可选安装
- **mcp-server-yfinance**: 未找到官方 MCP 实现
- **akshare**: A 股备用数据源

### 建议
当前方案已经满足需求，不需要额外安装 MCP server。

---

## 下一步

1. **A 股数据更新**: 确保本地 CSV 文件每日更新
2. **美股数据测试**: 验证 yfinance 在 Workflow C 中的表现
3. **港股行情**: 如有需要可在富途 APP 开通行情权限

---

## 相关文件

- 价格获取逻辑：`workflow_c_multi_market.py`
- A 股数据目录：`workspace/agents/main/data/stock-pick/daily_data/`
- 美股成分股：`workspace/agents/main/data/stock-pick/index_members_us_top500.csv`
