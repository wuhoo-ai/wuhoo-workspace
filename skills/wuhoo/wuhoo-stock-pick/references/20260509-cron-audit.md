# 2026-05-09 Cron 数据更新审计

## 执行时间
2026-05-09 08:39 UTC+8 (周六，非交易日)

## 前置检查
- ✅ TUSHARE_TOKEN (56 chars)
- ✅ OpenD 端口 11111 已监听
- ✅ python3.11 + tushare/pandas/yfinance 正常
- ⚠️ `terminal` 工具 `workdir` 不支持 `~` 展开，需用绝对路径 `/home/admin/`

## 更新结果

| 市场 | 状态 | 耗时 | 详情 |
|------|------|------|------|
| US | ✅ 完成 | ~2 min | 503/503 只，189,631 条记录。2 只失败(BF.B/BRK.B — 退市/时区) |
| HK | ✅ 完成 | ~3 min | 97/500 只新增数据，284,541 条总记录。换手率覆盖率 1% |
| CN | ✅ 正常 | ~37+ min | efinance 换手率阶段未完成（进程仍活跃，rchar 速率 ~300 KB/s） |

## 关键观察

### CN efinance 阻塞完整报告
- US 和 HK 在 ~3 分钟内完成，CN 在 37 分钟后仍在 efinance 下载阶段
- 导致无法产出完整的三市场报告
- **经验**：cron job 应先等待 US+HKC 完成并报告，再异步等待 CN

### 进程监控正确执行
- 识别到 `output_preview: ""` 为输出缓冲陷阱（非卡死）
- 通过 `pgrep -P <bash_pid>` 定位 Python 子进程
- 使用 rchar 速率法确认进程存活（8 次采样，速率 159-431 KB/s，始终 > 100 KB/s）
- 内存从 130MB 增长到 207MB，符合 efinance 数据累积行为

### efinance 行为确认
- 速率稳定在 159-431 KB/s（不随时间衰减）
- 内存缓慢增长至 ~207MB（非 700MB，低于预期但进程正常）
- `turnover_data/` 无新文件写入（符合"for 循环结束后才写 CSV"的预期）

## 数据文件快照

| 数据集 | 文件数 | 最近 5 月记录数 |
|--------|--------|----------------|
| daily_data/ (CN) | 26 | 77,832 |
| daily_data_hk/ (HK) | 31 | 29,323 |
| daily_data_us/ (US) | 29 | 44,264 |
| turnover_data/ (CN) | 426 | — |

## 待完成
- CN efinance 进程完成后，`turnover_data/` 将刷新
- 换手率因子缺失属已知降级（efinance ~2.3% 成功率）
