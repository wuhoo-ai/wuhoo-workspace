#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A 股数据可靠拉取脚本 — 中证 1000 成分股 + 日线 + 换手率

设计目标:
- 限流保护：动态调整批次大小和间隔，自适应 Tushare 限流
- 断点续传：按月检查，已存在的月份自动跳过
- 重试机制：指数退避，网络抖动自动恢复
- 增量更新：盘后执行，只拉取缺失数据，为次日开盘做好准备

用法:
    source ~/.openclaw/skills/wuhoo-stock-pick/venv/bin/activate
    python fetch_cn_data.py --full           # 全量拉取 2 年数据
    python fetch_cn_data.py --incremental    # 增量更新（最近 1 个月）
    python fetch_cn_data.py --daily          # 盘后增量（仅今日，适合 cron）
    python fetch_cn_data.py --full --force   # 强制重建
"""

import os
import sys
import time
import random
import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ============== 配置 ==============
DATA_DIR = Path.home() / '.openclaw' / 'data' / 'stock-pick'
DAILY_DATA_DIR = DATA_DIR / 'daily_data'
TURNOVER_DATA_DIR = DATA_DIR / 'turnover_data'
FACTORS_DIR = DATA_DIR / 'factors'
BACKUPS_DIR = DATA_DIR / 'backups'
STATUS_FILE = DATA_DIR / 'fetch_status.json'

INDEX_CODE = '000852.SH'  # 中证 1000

# 限流配置
BATCH_SIZE = 20              # 每批股票数
INITIAL_DELAY = 0.8          # 批次间基础延迟（秒）
MAX_DELAY = 10.0             # 最大退避延迟
MAX_RETRIES = 5              # 最大重试次数
RATE_LIMIT_WINDOW = 60       # 限流检测窗口（秒）
MAX_CALLS_PER_WINDOW = 120   # 每分钟最大调用次数（根据积分调整）


class RateLimiter:
    """自适应限流器"""

    def __init__(self, max_calls_per_window=MAX_CALLS_PER_WINDOW, window_sec=RATE_LIMIT_WINDOW):
        self.max_calls = max_calls_per_window
        self.window = window_sec
        self.timestamps = []
        self.current_delay = INITIAL_DELAY
        self.total_calls = 0
        self.total_retries = 0
        self.total_sleep = 0.0

    def wait(self):
        """调用前等待，确保不超过限流"""
        now = time.time()
        # 清理窗口外的记录
        self.timestamps = [t for t in self.timestamps if now - t < self.window]

        # 如果接近限流阈值，主动减速
        if len(self.timestamps) >= self.max_calls * 0.8:
            oldest = self.timestamps[0] if self.timestamps else now
            wait_time = self.window - (now - oldest) + 0.5
            if wait_time > 0:
                print(f"    [限流] 窗口内 {len(self.timestamps)} 次调用，等待 {wait_time:.1f}s")
                time.sleep(wait_time)
                self.timestamps = []
                self.total_sleep += wait_time

        time.sleep(self.current_delay)
        self.total_sleep += self.current_delay

    def record_call(self):
        """记录一次 API 调用"""
        self.timestamps.append(time.time())
        self.total_calls += 1

    def on_rate_limit(self):
        """触发限流时增加延迟"""
        self.current_delay = min(self.current_delay * 2, MAX_DELAY)
        self.total_retries += 1
        print(f"    [限流触发] 延迟调整到 {self.current_delay:.1f}s")
        time.sleep(self.current_delay)

    def on_success(self):
        """成功调用，逐步减少延迟"""
        if self.current_delay > INITIAL_DELAY:
            self.current_delay = max(self.current_delay * 0.9, INITIAL_DELAY)

    def report(self):
        return (
            f"API 调用: {self.total_calls} 次 | "
            f"重试: {self.total_retries} 次 | "
            f"累计等待: {self.total_sleep:.1f}s | "
            f"当前延迟: {self.current_delay:.2f}s"
        )


class CnDataFetcher:
    """A 股数据拉取器"""

    def __init__(self, force=False):
        self.force = force
        self.rate_limiter = RateLimiter()
        self.pro = None

    def connect(self):
        """连接 Tushare"""
        import tushare as ts
        token = os.environ.get('TUSHARE_TOKEN')
        if not token:
            raise ValueError("TUSHARE_TOKEN 环境变量未设置")
        ts.set_token(token)
        self.pro = ts.pro_api()
        print("Tushare 连接成功")

    def retry_call(self, func, *args, **kwargs):
        """带重试的 API 调用"""
        for attempt in range(MAX_RETRIES):
            try:
                self.rate_limiter.wait()
                result = func(*args, **kwargs)
                self.rate_limiter.record_call()

                # 检查是否触发限流（返回空但实际应该有数据）
                if result is not None and not result.empty:
                    self.rate_limiter.on_success()
                    return result

                # 空结果也可能是正常的（如某月无交易），短暂等待后重试一次
                if attempt == 0:
                    time.sleep(1)
                    continue

                return result

            except Exception as e:
                error_str = str(e)
                if '每分钟' in error_str or '频率' in error_str or 'limit' in error_str.lower():
                    self.rate_limiter.on_rate_limit()
                    continue
                elif attempt < MAX_RETRIES - 1:
                    wait = min(2 ** attempt + random.random(), MAX_DELAY)
                    print(f"    重试 {attempt+1}/{MAX_RETRIES}，等待 {wait:.1f}s: {e}")
                    time.sleep(wait)
                    self.rate_limiter.total_retries += 1
                else:
                    raise

        return pd.DataFrame()

    # ──────────────────────────────────────────────────────
    # 成分股
    # ──────────────────────────────────────────────────────

    def fetch_members(self):
        """获取中证 1000 成分股"""
        print("\n[1/3] 获取中证 1000 成分股...")
        members_file = DATA_DIR / 'index_members.csv'

        if members_file.exists() and not self.force:
            members = pd.read_csv(members_file)['code'].tolist()
            print(f"  已有成分股 {len(members)} 只，跳过 (使用 --force 强制更新)")
            return members

        print("  从 Tushare 获取最新成分股...")
        # 从最近 3 个月查找，选择有数据的最近月份
        members = []
        for i in range(3):
            check_date = datetime.now() - pd.DateOffset(months=i)
            check_date = check_date.replace(day=1)
            start_str = check_date.strftime('%Y%m%d')
            end_str = (check_date + pd.DateOffset(months=1) - timedelta(days=1)).strftime('%Y%m%d')

            try:
                df = self.retry_call(self.pro.index_weight, index_code=INDEX_CODE,
                                     start_date=start_str, end_date=end_str)
                if not df.empty:
                    members = df['con_code'].unique().tolist()
                    print(f"  使用 {check_date.strftime('%Y年%m月')} 成分股: {len(members)} 只")
                    break
            except Exception as e:
                print(f"  {check_date.strftime('%Y-%m')}: {e}")

        if not members:
            print("  ⚠️  无法获取成分股数据")
            return []

        # 获取股票基本信息，过滤 ST/退市
        print("  获取股票基本信息...")
        try:
            basic = self.retry_call(self.pro.stock_basic, fields='ts_code,symbol,name,list_status')
            non_st = basic[~basic['name'].str.contains('ST|退', na=False)]
            members = [m for m in members if m in non_st['ts_code'].values]
            print(f"  过滤 ST/退市后: {len(members)} 只")

            name_map = non_st.set_index('ts_code')['name'].to_dict()
            pd.Series(name_map).to_csv(DATA_DIR / 'stock_names.csv', header=['name'])
        except Exception as e:
            print(f"  ⚠️  获取股票信息失败: {e}")

        # 保存
        if members:
            pd.DataFrame({'code': members}).to_csv(members_file, index=False)
            print(f"  成分股已保存: {members_file}")

        return members

    # ──────────────────────────────────────────────────────
    # 日线数据
    # ──────────────────────────────────────────────────────

    def fetch_daily(self, members, months=None, incremental=False):
        """
        拉取日线数据

        Args:
            members: 成分股列表
            months: 指定月份列表 (YYYYMM)，None 则自动计算
            incremental: 是否增量模式（只更新最近缺失月份）
        """
        print(f"\n[2/3] 拉取日线数据 ({len(members)} 只股票)...")

        if not members:
            print("  ⚠️  成分股为空，跳过")
            return

        # 计算需要更新的月份
        if months is None:
            if incremental:
                # 增量：检查最近 3 个月
                months = self._get_missing_months(incremental_window=3)
            else:
                # 全量：最近 24 个月
                end_date = datetime.now()
                start_date = end_date - timedelta(days=730)  # 2 年
                months = self._get_month_list(start_date, end_date)

        if not months:
            print("  所有月份数据已存在，跳过")
            return

        print(f"  需要更新 {len(months)} 个月: {months[0]} ~ {months[-1]}")

        success_months = 0
        fail_months = []

        for mi, ym in enumerate(months):
            month_file = DAILY_DATA_DIR / ym[:4] / f"{ym}.csv"

            # 检查是否需要更新
            if month_file.exists() and not self.force:
                print(f"  [{mi+1}/{len(months)}] {ym}: 已存在，跳过")
                continue

            print(f"  [{mi+1}/{len(months)}] {ym}: 拉取中...", end='', flush=True)

            month_start = ym + '01'
            month_end_dt = datetime.strptime(ym, '%Y%m') + pd.DateOffset(months=1) - timedelta(days=1)
            # 当前月份不超出今天（避免查询未来日期导致 API 挂起）
            today = datetime.now()
            if month_end_dt > today:
                month_end_dt = today
            month_end = month_end_dt.strftime('%Y%m%d')

            month_data = []
            for i in range(0, len(members), BATCH_SIZE):
                batch = members[i:i+BATCH_SIZE]
                try:
                    df = self.retry_call(self.pro.daily,
                                         ts_code=','.join(batch),
                                         start_date=month_start,
                                         end_date=month_end)
                    if df is not None and not df.empty:
                        month_data.append(df)
                except Exception as e:
                    print(f"\n    批次 {i//BATCH_SIZE + 1} 失败: {e}")

            if month_data:
                month_df = pd.concat(month_data, ignore_index=True)
                month_file.parent.mkdir(parents=True, exist_ok=True)
                month_df.to_csv(month_file, index=False)
                print(f" OK ({len(month_df)} 条)")
                success_months += 1
            else:
                print(f" 空 (无数据)")
                fail_months.append(ym)

            # 更新状态文件
            self._save_status('daily', ym, success_months, len(months))

        print(f"\n  日线更新完成: 成功 {success_months}/{len(months)} 个月")
        if fail_months:
            print(f"  失败的月份: {fail_months}")
        print(f"  {self.rate_limiter.report()}")

    # ──────────────────────────────────────────────────────
    # 换手率数据
    # ──────────────────────────────────────────────────────

    def fetch_turnover(self, members, incremental=False):
        """使用 Tushare daily_basic 拉取换手率数据"""
        print(f"\n[3/3] 拉取换手率数据 ({len(members)} 只股票)...")

        if not members:
            print("  ⚠️  成分股为空，跳过")
            return

        if self.pro is None:
            self.connect()

        # 计算时间范围
        end_date = datetime.now()
        if incremental:
            start_date = end_date - timedelta(days=35)
        else:
            start_date = end_date - timedelta(days=730)

        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        print(f"  时间范围: {start_str} ~ {end_str}")

        # 按月拉取（避免单次返回数据过大）
        all_data = []
        months = self._get_month_list(start_date, end_date)
        total_rows = 0
        success_months = 0
        fail_months = 0

        for ym_str in months:
            month_start = datetime.strptime(ym_str, '%Y%m')
            # 计算月末
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, day=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)

            # 与请求范围取交集
            effective_start = max(month_start, start_date)
            effective_end = min(month_end, end_date)

            sd = effective_start.strftime('%Y%m%d')
            ed = effective_end.strftime('%Y%m%d')
            ym = effective_start.strftime('%Y%m')

            # 检查是否已有数据（增量模式跳过已存在的月份）
            year_dir = TURNOVER_DATA_DIR / sd[:4]
            month_file = year_dir / f"{ym}.csv"
            if not self.force and month_file.exists():
                continue

            try:
                self.rate_limiter.wait()
                df = self.pro.daily_basic(start_date=sd, end_date=ed,
                                          fields='ts_code,trade_date,turnover_rate')
                self.rate_limiter.record_call()

                if df is not None and not df.empty:
                    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
                    all_data.append(df)
                    total_rows += len(df)
                    success_months += 1
                    self.rate_limiter.on_success()
                else:
                    fail_months += 1
            except Exception as e:
                fail_months += 1
                if '每分钟' in str(e) or '频率' in str(e) or 'limit' in str(e).lower():
                    self.rate_limiter.on_rate_limit()
                    # 重试当前月份
                    try:
                        time.sleep(2)
                        df = self.pro.daily_basic(start_date=sd, end_date=ed,
                                                  fields='ts_code,trade_date,turnover_rate')
                        if df is not None and not df.empty:
                            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
                            all_data.append(df)
                            total_rows += len(df)
                            success_months += 1
                    except Exception:
                        pass

            print(f"    月份 {ym_str}: {'OK' if not self.force and month_file.exists() else 'fetched'} ({total_rows} rows so far)")

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            result['year_month'] = pd.to_datetime(result['trade_date'], format='%Y%m%d').dt.strftime('%Y%m')

            saved_months = 0
            for ym in sorted(result['year_month'].unique()):
                ym_data = result[result['year_month'] == ym].copy()
                year = ym[:4]
                month_file = TURNOVER_DATA_DIR / year / f"{ym}.csv"
                month_file.parent.mkdir(parents=True, exist_ok=True)
                ym_data.drop(columns=['year_month'], inplace=True)
                ym_data.to_csv(month_file, index=False)
                saved_months += 1

            print(f"\n  换手率更新完成: {total_rows} 条记录, 保存 {saved_months} 个月, "
                  f"成功 {success_months} 月/失败 {fail_months} 月")
        else:
            print("  换手率数据获取完成（无新增月份）")

        print(f"  Tushare {self.rate_limiter.report()}")

    # ──────────────────────────────────────────────────────
    # 辅助方法
    # ──────────────────────────────────────────────────────

    def _get_month_list(self, start_date, end_date):
        """生成月份列表"""
        months = []
        current = start_date.replace(day=1)
        while current <= end_date:
            months.append(current.strftime('%Y%m'))
            current = current + pd.DateOffset(months=1)
        return months

    def _get_missing_months(self, incremental_window=3):
        """检查最近 N 个月哪些缺失"""
        end_date = datetime.now()
        start_date = end_date - pd.DateOffset(months=incremental_window)
        all_months = self._get_month_list(start_date, end_date)

        missing = []
        for ym in all_months:
            month_file = DAILY_DATA_DIR / ym[:4] / f"{ym}.csv"
            if not month_file.exists() or self.force:
                missing.append(ym)

        return missing

    def _save_status(self, data_type, ym, success, total):
        """保存拉取状态到 JSON 文件"""
        import json
        status = {}
        if STATUS_FILE.exists():
            try:
                status = json.loads(STATUS_FILE.read_text())
            except Exception:
                pass

        status[f'{data_type}_{ym}'] = {
            'success': success,
            'total': total,
            'timestamp': datetime.now().isoformat()
        }
        STATUS_FILE.write_text(json.dumps(status, indent=2))

    def run_full(self):
        """全量数据拉取"""
        print("=" * 60)
        print("A 股数据全量拉取")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        self.connect()
        members = self.fetch_members()

        if not members:
            print("\n⚠️  成分股获取失败，终止")
            return

        self.fetch_daily(members)
        self.fetch_turnover(members)

        print("\n" + "=" * 60)
        print("全量拉取完成")
        self._print_summary()
        print("=" * 60)

    def run_incremental(self):
        """增量数据更新"""
        print("=" * 60)
        print("A 股数据增量更新")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        self.connect()

        # 更新成分股
        members = self.fetch_members()
        if not members:
            print("\n⚠️  成分股获取失败，终止")
            return

        # 增量拉取日线
        self.fetch_daily(members, incremental=True)

        # 增量拉取换手率
        self.fetch_turnover(members, incremental=True)

        print("\n" + "=" * 60)
        print("增量更新完成")
        self._print_summary()
        print("=" * 60)

    def run_daily(self):
        """盘后增量（仅今日数据）"""
        print("=" * 60)
        print("A 股盘后增量更新")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        self.connect()
        members = self.fetch_members()

        if not members:
            print("\n⚠️  成分股获取失败，终止")
            return

        today_str = datetime.now().strftime('%Y%m%d')
        current_month = datetime.now().strftime('%Y%m')

        print(f"\n[日线] 拉取今日数据 {today_str}...")
        month_file = DAILY_DATA_DIR / current_month[:4] / f"{current_month}.csv"

        if month_file.exists() and not self.force:
            # 已有本月数据，检查是否包含今天
            existing = pd.read_csv(month_file)
            if today_str in existing['trade_date'].astype(str).values:
                print(f"  今日数据已存在，跳过")
                return
            # 追加今日数据
            print(f"  追加到已有月度文件...")

        today_data = []
        for i in range(0, len(members), BATCH_SIZE):
            batch = members[i:i+BATCH_SIZE]
            try:
                df = self.retry_call(self.pro.daily,
                                     ts_code=','.join(batch),
                                     start_date=today_str, end_date=today_str)
                if df is not None and not df.empty:
                    today_data.append(df)
            except Exception as e:
                print(f"  批次 {i//BATCH_SIZE + 1} 失败: {e}")

        if today_data:
            result = pd.concat(today_data, ignore_index=True)
            month_file.parent.mkdir(parents=True, exist_ok=True)

            if month_file.exists() and not self.force:
                existing = pd.read_csv(month_file)
                # 去重
                result = pd.concat([existing, result]).drop_duplicates(
                    subset=['ts_code', 'trade_date'], keep='last'
                )

            result.to_csv(month_file, index=False)
            print(f"  今日数据: {len(result)} 条")
        else:
            print(f"  今日无数据 (可能非交易日)")

        print("\n" + "=" * 60)
        print("盘后增量完成")
        print("=" * 60)

    def _print_summary(self):
        """打印数据摘要"""
        print("\n数据摘要:")

        # 日线
        daily_files = sorted(DAILY_DATA_DIR.rglob('*.csv'))
        if daily_files:
            total_rows = 0
            for f in daily_files:
                try:
                    total_rows += len(pd.read_csv(f))
                except Exception:
                    pass
            print(f"  日线数据: {len(daily_files)} 个文件, {total_rows} 条记录")

            # 检查最早和最晚日期
            first_f = daily_files[0]
            last_f = daily_files[-1]
            first_df = pd.read_csv(first_f)
            last_df = pd.read_csv(last_f)
            if 'trade_date' in first_df.columns:
                print(f"  时间范围: {first_df['trade_date'].min()} ~ {last_df['trade_date'].max()}")
        else:
            print("  日线数据: 无")

        # 换手率
        turnover_files = sorted(TURNOVER_DATA_DIR.rglob('*.csv'))
        if turnover_files:
            total_rows = 0
            for f in turnover_files:
                try:
                    total_rows += len(pd.read_csv(f))
                except Exception:
                    pass
            print(f"  换手率:   {len(turnover_files)} 个文件, {total_rows} 条记录")
        else:
            print("  换手率:   无")

        # 成分股
        members_file = DATA_DIR / 'index_members.csv'
        if members_file.exists():
            members = pd.read_csv(members_file)
            print(f"  成分股:   {len(members)} 只")


def main():
    parser = argparse.ArgumentParser(description="A 股数据可靠拉取脚本")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--full', action='store_true', help='全量拉取 2 年数据')
    mode.add_argument('--incremental', action='store_true', help='增量更新（最近缺失月份）')
    mode.add_argument('--daily', action='store_true', help='盘后增量（仅今日）')
    parser.add_argument('--force', action='store_true', help='强制重建')

    args = parser.parse_args()

    # 确保目录存在
    for d in [DATA_DIR, DAILY_DATA_DIR, TURNOVER_DATA_DIR, FACTORS_DIR, BACKUPS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    fetcher = CnDataFetcher(force=args.force)

    if args.full:
        fetcher.run_full()
    elif args.incremental:
        fetcher.run_incremental()
    elif args.daily:
        fetcher.run_daily()


if __name__ == '__main__':
    main()
