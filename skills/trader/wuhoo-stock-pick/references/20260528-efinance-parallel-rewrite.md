# 2026-05-28 — efinance 换手率并行重写审计

## 背景

Cron `市场数据更新`（08:00）运行 `update_all_data.py --market cn --incremental` 时，
efinance 换手率阶段超时（exit code 124, timeout=480s）。

## 根因

`update_cn_turnover_efinance()` 纯串行逐只拉取 999 只股票换手率，
每只 ~4 秒，全量需 67 分钟，远超 cron 480s 超时。

初次超时时已拉取 929 只，但旧代码将所有数据累积在内存中（`all_data` 列表），
循环结束后才统一写入 CSV —— 超时后 929 只数据全部丢失。

## 修复（v3.6）

在 `update_all_data.py` 中重写 `update_cn_turnover_efinance()`：

### 1. 并行化
```python
MAX_WORKERS = 20
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(_fetch_one, code): code for code in to_fetch}
    for future in as_completed(futures):
        pass  # 结果在 _fetch_one 中已 lock 保护地收集
```

### 2. 增量检测（断点续传）
```python
current_ym = end_date.strftime('%Y%m')
existing_member_files = set()
year_dir = TURNOVER_DATA_DIR / current_ym[:4]
if year_dir.exists() and not force:
    for f in year_dir.glob(f"{current_ym}*.csv"):
        existing_df = pd.read_csv(f)
        existing_member_files.update(existing_df['ts_code'].unique().tolist())

to_fetch = [m for m in members if m not in existing_member_files]
```

### 3. 增量合并写入
```python
if month_file.exists():
    existing = pd.read_csv(month_file)
    ym_data = pd.concat([existing, ym_data], ignore_index=True)
    ym_data = ym_data.drop_duplicates(subset=['ts_code', 'trade_date'])
month_file.parent.mkdir(parents=True, exist_ok=True)
ym_data.to_csv(month_file, index=False)
```

## 验证结果

- 首次运行：929 只已缓存（跳过），70 只待拉取
- 47/70 成功（67%），23 失败（efinance 限流）
- 新写入 117,030 条记录
- 总数据覆盖 2000-01 到 2026-05，202605.csv 11,946 行
- 耗时 < 2 分钟（vs 旧版 67 分钟）

## 后续日常预期

- 增量运行：999 只全部跳过（秒级完成）
- 月初新月份：~70 只（2 分钟内完成）
- 失败股票下次重试自动补齐
