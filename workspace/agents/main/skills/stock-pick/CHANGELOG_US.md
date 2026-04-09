# 美股选股升级日志

**版本**: v2.0 - 完整因子版  
**升级日期**: 2026-03-27  
**数据源**: yfinance

---

## 📊 因子定义升级

### v1.0 (简化版) - 已弃用
| 因子 | 计算方式 |
|------|---------|
| 252 日波动率 | 简单标准差 |
| 5 日动量 | TA-Lib ROC |
| 10 日动量 (排序) | TA-Lib ROC |

### v2.0 (完整版) - 当前版本
| 因子 | 计算方式 | 单位 | 筛选逻辑 |
|------|---------|------|---------|
| **252 日残差波动率** | 相对于 SPY 回归残差的年化标准差 | 百分比 (%) | 越低越好，前 50% |
| **5 日平均成交量** | log(成交量均值 + 1) | 对数标度 | 越高越好，前 50% |
| **5 日价格动量** | TA-Lib ROC(close, 5) | 百分比 (%) | 越高越好，前 30% |
| **20 日 Beta** | 相对于 SPY 的 20 日 Beta | 系数 | 越高越好，前 30% |
| **10 日价格动量** (排序用) | TA-Lib ROC(close, 10) | 百分比 (%) | 最终排序，越低越好 Top 10 |

---

## 🔧 技术实现

### 数据源
- **yfinance**: 美股历史 K 线数据
- **SPY**: 作为市场基准（标普 500 ETF）

### 残差波动率计算
```python
# 1. 计算 252 日收益率
stock_ret = np.diff(close_prices) / close_prices[:-1]
spy_ret = np.diff(spy_close) / spy_close[:-1]

# 2. 计算 Beta 和 Alpha
beta_252 = np.cov(stock_ret[-252:], spy_ret[-252:])[0, 1] / np.var(spy_ret[-252:])
alpha_252 = np.mean(stock_ret[-252:]) - beta_252 * np.mean(spy_ret[-252:])

# 3. 计算残差
residual = stock_ret[-252:] - (alpha_252 + beta_252 * spy_ret[-252:])

# 4. 年化残差波动率
residual_vol = np.std(residual) * np.sqrt(252) * 100
```

### 选股流程
```
242 只成分股
  ↓
残差波动率 ≤ 24.29 (前 50%) → 121 只
  ↓
成交量 ≥ 15.13 (前 50%) → 61 只
  ↓
5 日动量 ≥ 2.15% (前 30%) → 19 只
  ↓
20 日 Beta ≥ 0.965 (前 30%) → 6 只
  ↓
按 10 日动量升序排序 → Top 10
```

---

## 📁 文件变更

### 修改文件
- `stock_pick.py`: 新增 `calculate_factors_us_complete()` 函数
- `stock_pick.py`: 新增 `select_stocks_us_complete()` 函数
- `stock_pick.py`: 更新 `print_results()` 支持美股完整因子格式
- `stock_pick.py`: 更新 `main()` 调用逻辑

### 输出文件
- `factors_us_YYYYMMDD.csv`: 完整因子数据 (242 只股票)
- `result_us_YYYYMMDD.csv`: 选股结果 (Top 10)

---

## 🧪 测试结果

**测试日期**: 2026-03-27  
**成分股数量**: 242 只  
**有效数据**: 242 只 (100%)  
**选出股票**: 6 只 (因筛选条件严格)

### 2026-03-26 选股结果
| 排名 | 代码 | 名称 | 10 日 ROC% | 残差波% | 5 日量 (log) | 5 日 ROC% | 20 日 Beta |
|------|------|------|----------|---------|-------------|----------|-----------|
| 1 | TFC.US | Truist Financial | -0.57 | 19.66 | 16.21 | 3.51 | 1.23 |
| 2 | ADI.US | Analog Devices | 0.88 | 23.94 | 15.19 | 4.36 | 1.70 |
| 3 | HST.US | Host Hotels | 1.51 | 22.39 | 16.01 | 2.15 | 1.60 |
| 4 | FITB.US | Fifth Third Bancorp | 1.66 | 22.27 | 16.40 | 4.35 | 1.04 |
| 5 | JCI.US | Johnson Controls | 2.16 | 21.66 | 15.23 | 2.78 | 1.70 |
| 6 | C.US | Citigroup | 4.84 | 22.06 | 16.69 | 5.35 | 1.15 |

---

## 📝 使用说明

### 运行美股选股
```bash
cd /home/admin/.openclaw/workspace/agents/main/skills/stock-pick
source venv/bin/activate
python3 stock_pick.py --market us --date 2026-03-27
```

### 参数说明
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--market` | 市场 (cn/hk/us) | cn |
| `--date` | 选股日期 (YYYY-MM-DD) | 昨天 |
| `--update-data` | 更新数据 (仅 A 股) | - |

---

## ⚠️ 注意事项

1. **数据依赖**: 需要 yfinance 可访问（可能需要网络代理）
2. **SPY 基准**: 如果 SPY 数据获取失败，自动降级为简单波动率
3. **成分股**: 使用 `index_members_us_top500.csv` (242 只)
4. **筛选严格**: 5 个因子连续筛选可能导致选出股票 < 10 只

---

## 🔄 未来改进

- [ ] 增加市值筛选（排除小盘股）
- [ ] 增加流动性筛选（最小成交额）
- [ ] 支持自定义因子权重
- [ ] 增加行业中性化处理
- [ ] 定期自动更新成分股列表

---

**升级完成时间**: 2026-03-27 17:00  
**升级执行**: main-agent
