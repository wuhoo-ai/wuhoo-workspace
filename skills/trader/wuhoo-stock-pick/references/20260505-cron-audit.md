# 2026-05-05 Cron 数据更新审计

## 执行摘要

- **日期**: 2026-05-05 08:00 HKT
- **结果**: 全部成功 ✅
- **耗时**: ~17 分钟（HK 2.5min + CN 14min）

## 前置检查

| 检查项 | 结果 |
|--------|------|
| Tushare Token | ✅ |
| OpenD (11111) | ✅ 端口监听中 |
| python3.11 核心依赖 | ✅ tushare, pandas, numpy, talib |
| CN daily_data 污染检查 | ✅ 001309.SZ 格式正常 |
| 脚本路径 | ✅ ~/wuhoo-workspace/skills/trader/wuhoo-stock-pick/ |

## 执行详情

### HK 港股 (fetch_hk_data.py --incremental)
- 耗时: ~2.5 分钟
- 成分股: 500 只（跳过更新）
- 增量窗口: 2026-03-31 ~ 2026-05-05
- 成功: 95/500（仅统计增量窗口内有新数据的股票）
- 总记录: 284,111，含换手率: 3,111 (1%)
- 文件更新: 202603.csv, 202604.csv, 202605.csv

### CN A股 (update_all_data.py --market cn --incremental)
- 耗时: ~14 分钟
- 成分股: 999 只（中证1000，跳过更新）
- Tushare 日线: 0 个月更新（202603/202604 已存在且最新）
- efinance 换手率: 999/999 只成功，3,421,683 条记录
- 进程状态监控:
  - Tushare 阶段（前 5 分钟）: 无文件写入，rchar 持续增长至 115MB
  - efinance 阶段（后 9 分钟）: 写入 425 个 turnover_data CSV，内存峰值 ~700MB
  - 两个 Tushare 连接进入 CLOSE-WAIT 后进程切换至 efinance（短连接）

### S&P 500 成分股
- 来源: GitHub datasets/s-and-p-500-companies
- 数量: 242 → 503 只
- 格式: SYMBOL.US ✅

## 发现与问题

### 正常现象（无需处理）
1. **CN 202605.csv 缺失**: Tushare 五月数据未入库（五一假期 5/1-5/5），确认 000001.SZ 返回 0 条
2. **CN Tushare 日线 "0 months updated"**: 202603/202604 已存在，正常跳过
3. **HK 95/500 成功率**: 仅统计增量窗口内有新数据的股票，非总覆盖率
4. **输出缓冲**: background 模式下 stdout 完全不可见，需通过 /proc + find 监控

### US daily_data_us ts_code 格式
- daily_data_us CSV 中 ts_code 为裸代码（`MMM`），非 `MMM.US`
- stock_info_us_top500.csv 要求 `SYMBOL.US` 格式
- 两者不同，但因子计算使用 yfinance API 不受影响
- 格式检查时需注意区分

## 最终数据状态

| 市场 | 文件数 | 最新月份 | 股票数 | 状态 |
|------|--------|----------|--------|------|
| CN daily_data | 25 | 202604 (5/1) | 999 | ✅ |
| CN turnover | 425 | 全部 (5/5) | 999 | ✅ |
| HK daily_data_hk | 31 | 202605 (5/5) | 596 | ✅ |
| US daily_data_us | 29 | 202605 (5/4) | 503 | ✅ |
| S&P 500 constituents | 1 | 5/5 | 503 | ✅ |
