# 选股因子定义与 TA-Lib 实现

## 1. 252 日残差收益波动率 (Residual Volatility)

**定义**: 个股日收益相对市场收益的残差的标准差（年化）

**正确计算步骤**:
```
1. 获取个股 252 日收盘价和指数 252 日收盘价
2. 计算日收益率: ret = (close_t - close_{t-1}) / close_{t-1}
3. 使用线性回归计算 Alpha 和 Beta:
   ret_stock = Alpha + Beta * ret_market + epsilon
4. 计算残差: epsilon = ret_stock - (Alpha + Beta * ret_market)
5. 残差波动率 = Std(epsilon) * sqrt(252)
```

**TA-Lib 实现**:
```python
# 方法 1: 使用 LINEARREG 计算预测值，然后计算残差
predicted = talib.LINEARREG(ret_stock, timeperiod=252)  # 这不对，LINEARREG 是对时间回归

# 方法 2: 手动计算（推荐，因为 TA-Lib 没有直接的对另一序列回归的函数）
beta = np.cov(ret_stock, ret_market)[0,1] / np.var(ret_market)
alpha = np.mean(ret_stock) - beta * np.mean(ret_market)
residual = ret_stock - (alpha + beta * ret_market)
residual_vol = np.std(residual) * np.sqrt(252)
```

**注意**: TA-Lib 的 `BETA` 函数就是计算这个的！
```python
beta = talib.BETA(ret_stock, ret_market, timeperiod=252)
```

---

## 2. 5 日平均换手率 (5-Day Average Turnover Rate) ⚠️

**定义**: 过去 5 个交易日的平均换手率（%）

**正确计算**:
```
turnover_5d = SMA(turnover_rate, 5)
```

**数据来源**: 
- 需要从 tushare `daily_basic` 接口获取 `turnover_rate` 字段
- 不能用成交量 (vol) 替代！

**TA-Lib 实现**:
```python
turnover_5d = talib.SMA(turnover_rate, timeperiod=5)
```

**积分要求**: daily_basic 接口需要约 3000 积分，当前 2120 积分可能不够。
备选方案：用 `vol / float_share` 估算换手率。

---

## 3. 5 日价格动量 (5-Day Price Momentum)

**定义**: 过去 5 日的价格变化率

**正确计算**:
```
momentum_5d = (close_t / close_{t-5} - 1) * 100
```

**TA-Lib 实现**:
```python
# 方法 1: ROC (Rate of Change)
momentum_5d = talib.ROC(close, timeperiod=5)

# 方法 2: MOM (Momentum)
momentum_5d = talib.MOM(close, timeperiod=5)  # 返回 close_t - close_{t-5}
```

**推荐**: 使用 `ROC`，直接返回百分比变化。

---

## 4. 20 日 Beta 值 (20-Day Beta)

**定义**: 个股相对市场的 20 日 Beta

**正确计算**:
```
Beta = Cov(ret_stock, ret_market) / Var(ret_market)
```

**TA-Lib 实现**:
```python
beta = talib.BETA(ret_stock, ret_market, timeperiod=20)
```

**注意**: 输入应该是收益率，不是价格！

---

## 5. 10 日价格动量 (10-Day Price Momentum) - 最终排序

**定义**: 过去 10 日的价格变化率

**TA-Lib 实现**:
```python
momentum_10d = talib.ROC(close, timeperiod=10)
```

---

## 数据需求总结

| 数据项 | 来源 | 字段 | 说明 |
|--------|------|------|------|
| 个股日线 | tushare.daily | close | 收盘价 |
| 个股日线 | tushare.daily | vol | 成交量（手）|
| 换手率 | tushare.daily_basic | turnover_rate | 换手率 (%) |
| 指数日线 | tushare.index_daily | close | 中证 1000 收盘价 |
| 流通股本 | tushare.stock_basic | float_share | 流通股本（万股）|

## TA-Lib 函数映射

| 因子 | TA-Lib 函数 | 输入 | 输出 |
|------|-----------|------|------|
| 残差波动率 | 手动计算 (np.cov) | ret_stock, ret_market | 残差标准差 |
| 5 日平均换手率 | `SMA` | turnover_rate | 5 日均值 |
| 5 日动量 | `ROC` | close | 变化率 % |
| 20 日 Beta | `BETA` | ret_stock, ret_market | Beta 值 |
| 10 日动量 | `ROC` | close | 变化率 % |

## 关键修正

1. **Beta 计算输入应该是收益率，不是价格**
2. **换手率需要从 daily_basic 获取，不能用 vol 替代**
3. **动量使用 ROC 而不是手动计算**
