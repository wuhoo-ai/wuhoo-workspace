#!/usr/bin/env python3.11
"""
数据保鲜检查脚本 — 每日 cron 运行，检查所有数据源新鲜度。
输出 Markdown 报告到 stdout，由 cron job 投递。

用法:
  python3.11 check_data_freshness.py           # 完整检查
  python3.11 check_data_freshness.py --json    # JSON 输出（供程序消费）
  python3.11 check_data_freshness.py --quiet   # 仅输出有问题的项
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict

DATA_ROOT = Path.home() / 'wuhoo-workspace' / 'data'
NOW = datetime.now()
TODAY = NOW.strftime('%Y%m%d')

# ============================================================
# 保鲜阈值定义 (days)
# ============================================================
THRESHOLDS = {
    # (warning_days, critical_days, description)
    'daily_data_cn':      (5, 10, 'A股日线 (Tushare)'),
    'daily_data_hk':      (3, 7,  '港股日线 (Futu)'),
    'daily_data_us':      (3, 7,  '美股日线 (yfinance)'),
    'turnover_cn':        (5, 10, 'A股换手率 (efinance)'),
    'factors_cn':         (2, 5,  'A股因子/选股结果'),
    'factors_hk':         (2, 5,  '港股因子/选股结果'),
    'factors_us':         (2, 5,  '美股因子/选股结果'),
    'index_members_cn':   (30, 90, 'A股成分股列表'),
    'index_members_hk':   (30, 90, '港股成分股列表'),
    'index_members_us':   (7, 14,  'S&P500成分股'),
    'regime':             (2, 5,   '市场状态判定'),
    'futures_kline':      (7, 14,  '期货日线'),
}

# ============================================================
# 数据源检查函数
# ============================================================

def check_dir_latest(path: Path, glob_pattern: str = '*/*.csv') -> dict:
    """检查目录中最新的文件及其保鲜度"""
    if not path.exists():
        return {'status': 'missing', 'days_old': None, 'latest_file': None, 'file_count': 0}
    files = list(path.glob(glob_pattern))
    if not files:
        # Try without subdirs
        files = list(path.glob('*.csv'))
    if not files:
        return {'status': 'empty', 'days_old': None, 'latest_file': None, 'file_count': 0}
    
    latest = max(files, key=lambda p: p.stat().st_mtime)
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    days_old = (NOW - mtime).days
    hours_old = (NOW - mtime).total_seconds() / 3600
    
    return {
        'status': 'ok',
        'days_old': days_old,
        'hours_old': round(hours_old, 1),
        'latest_file': str(latest.relative_to(DATA_ROOT.parent)),
        'latest_mtime': mtime.isoformat(),
        'file_count': len(files),
    }


def check_monthly_csv(dir_path: Path, year: int, month: int) -> dict:
    """检查特定年月 CSV 的数据覆盖度"""
    f = dir_path / str(year) / f'{year}{month:02d}.csv'
    if not f.exists():
        return {'status': 'missing', 'rows': 0, 'stocks': 0}
    
    import pandas as pd
    try:
        df = pd.read_csv(f)
        # Detect date column
        date_col = None
        for col in ['trade_date', 'time_key', 'Date']:
            if col in df.columns:
                date_col = col
                break
        
        result = {
            'status': 'ok',
            'rows': len(df),
            'stocks': df['ts_code'].nunique() if 'ts_code' in df.columns else 0,
            'size_kb': round(f.stat().st_size / 1024, 1),
        }
        if date_col:
            try:
                # CN uses integer YYYYMMDD, HK uses time_key, US uses Date
                if date_col == 'trade_date':
                    # Integer format: 20260605
                    dates = pd.to_datetime(df[date_col].astype(str), format='%Y%m%d')
                else:
                    dates = pd.to_datetime(df[date_col])
                result['date_min'] = str(dates.min().date())
                result['date_max'] = str(dates.max().date())
            except Exception:
                pass
        return result
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def check_factors_freshness(factors_dir: Path, market: str) -> dict:
    """检查因子/选股结果保鲜度"""
    if not factors_dir.exists():
        return {'status': 'missing', 'days_old': None}
    
    prefix = f'result_{market}_'
    files = [f for f in factors_dir.glob(f'{prefix}*.csv')]
    if not files:
        # Also check factors_ prefix
        prefix2 = f'factors_{market}_'
        files = [f for f in factors_dir.glob(f'{prefix2}*.csv')]
    
    if not files:
        return {'status': 'empty', 'days_old': None}
    
    latest = max(files, key=lambda p: p.stat().st_mtime)
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    days_old = (NOW - mtime).days
    
    # Extract date from filename
    date_str = None
    for part in latest.stem.split('_'):
        if len(part) == 8 and part.isdigit() and part.startswith('202'):
            date_str = part
            break
    
    return {
        'status': 'ok',
        'days_old': days_old,
        'latest_file': latest.name,
        'data_date': date_str,
        'latest_mtime': mtime.isoformat(),
    }


def check_index_members(filepath: Path) -> dict:
    """检查成分股列表保鲜度"""
    if not filepath.exists():
        return {'status': 'missing', 'days_old': None}
    
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    days_old = (NOW - mtime).days
    
    import pandas as pd
    try:
        df = pd.read_csv(filepath)
        return {
            'status': 'ok',
            'days_old': days_old,
            'mtime': mtime.isoformat(),
            'stocks': len(df),
            'size_kb': round(filepath.stat().st_size / 1024, 1),
        }
    except Exception as e:
        return {'status': 'error', 'days_old': days_old, 'error': str(e)}


# ============================================================
# 状态判定
# ============================================================

def assess_freshness(days_old, status, warn_days, crit_days):
    """根据天数判定保鲜状态"""
    if status in ('missing', 'empty', 'error'):
        return 'critical'
    if days_old is None:
        return 'unknown'
    if days_old >= crit_days:
        return 'critical'
    if days_old >= warn_days:
        return 'warning'
    return 'ok'


def freshness_icon(level):
    return {'ok': '✅', 'warning': '🟡', 'critical': '🔴', 'unknown': '❓'}.get(level, '❓')


# ============================================================
# 主检查流程
# ============================================================

def run_all_checks():
    checks = OrderedDict()
    sp = DATA_ROOT / 'stock-pick'
    
    # 1. CN daily_data
    checks['A股日线'] = check_dir_latest(sp / 'daily_data')
    checks['A股日线']['threshold'] = THRESHOLDS['daily_data_cn']
    # Also check current month data
    checks['A股日线']['monthly'] = check_monthly_csv(sp / 'daily_data', NOW.year, NOW.month)
    
    # 2. HK daily_data
    checks['港股日线'] = check_dir_latest(sp / 'daily_data_hk')
    checks['港股日线']['threshold'] = THRESHOLDS['daily_data_hk']
    checks['港股日线']['monthly'] = check_monthly_csv(sp / 'daily_data_hk', NOW.year, NOW.month)
    
    # 3. US daily_data
    checks['美股日线'] = check_dir_latest(sp / 'daily_data_us')
    checks['美股日线']['threshold'] = THRESHOLDS['daily_data_us']
    checks['美股日线']['monthly'] = check_monthly_csv(sp / 'daily_data_us', NOW.year, NOW.month)
    
    # 4. CN turnover
    checks['A股换手率'] = check_dir_latest(sp / 'turnover_data')
    checks['A股换手率']['threshold'] = THRESHOLDS['turnover_cn']
    
    # 5. Factors (3 markets)
    factors_dir = sp / 'factors'
    for mkt, label in [('cn', 'A股因子'), ('hk', '港股因子'), ('us', '美股因子')]:
        checks[label] = check_factors_freshness(factors_dir, mkt)
        checks[label]['threshold'] = THRESHOLDS[f'factors_{mkt}']
    
    # 6. Index members
    checks['A股成分股'] = check_index_members(sp / 'index_members.csv')
    checks['A股成分股']['threshold'] = THRESHOLDS['index_members_cn']
    
    checks['港股成分股'] = check_index_members(sp / 'index_members_hk_top500.csv')
    checks['港股成分股']['threshold'] = THRESHOLDS['index_members_hk']
    
    checks['S&P500成分股'] = check_index_members(sp / 'index_members_us_top500.csv')
    checks['S&P500成分股']['threshold'] = THRESHOLDS['index_members_us']
    
    # 7. Regime
    regime_dir = DATA_ROOT / 'regime'
    regime_result = check_dir_latest(regime_dir, '*.json')
    regime_result['threshold'] = THRESHOLDS['regime']
    checks['市场状态'] = regime_result
    
    # 8. Futures kline
    fut_dir = DATA_ROOT / 'futures' / 'daily_kline'
    fut_result = check_dir_latest(fut_dir, '*/*.csv') if fut_dir.exists() else {'status': 'missing', 'days_old': None, 'file_count': 0}
    fut_result['threshold'] = THRESHOLDS['futures_kline']
    checks['期货日线'] = fut_result
    
    # 9. Assess all
    for name, result in checks.items():
        th = result.get('threshold', (7, 14, ''))
        result['level'] = assess_freshness(
            result.get('days_old'), 
            result.get('status', 'ok'),
            th[0], th[1]
        )
    
    return checks


def generate_markdown(checks):
    """生成 Markdown 报告"""
    lines = []
    lines.append(f"# 📊 数据保鲜检查报告")
    lines.append(f"**检查时间**: {NOW.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
    lines.append(f"**数据根目录**: `{DATA_ROOT}`")
    lines.append("")
    
    # Summary
    criticals = [name for name, r in checks.items() if r['level'] == 'critical']
    warnings = [name for name, r in checks.items() if r['level'] == 'warning']
    oks = [name for name, r in checks.items() if r['level'] == 'ok']
    
    if criticals:
        lines.append(f"## 🔴 严重过期 ({len(criticals)} 项)")
        lines.append("")
        for name in criticals:
            r = checks[name]
            th = r.get('threshold', (0, 0, ''))
            lines.append(f"- **{name}**: {r.get('days_old', '?')} 天未更新（阈值 {th[1]} 天）")
        lines.append("")
    
    if warnings:
        lines.append(f"## 🟡 接近过期 ({len(warnings)} 项)")
        lines.append("")
        for name in warnings:
            r = checks[name]
            th = r.get('threshold', (0, 0, ''))
            lines.append(f"- **{name}**: {r.get('days_old', '?')} 天未更新（阈值 {th[0]} 天）")
        lines.append("")
    
    # Detail table
    lines.append("## 全部数据源")
    lines.append("")
    lines.append("| 数据源 | 状态 | 天数 | 最新文件/日期 | 详情 |")
    lines.append("|--------|------|------|--------------|------|")
    
    for name, r in checks.items():
        icon = freshness_icon(r['level'])
        days = r.get('days_old')
        days_str = f"{days}d" if days is not None else "N/A"
        
        latest_info = r.get('latest_file', '') or r.get('latest_file', '')
        if 'monthly' in r and r['monthly'].get('date_max'):
            latest_info = f"数据至 {r['monthly']['date_max']}"
        elif 'data_date' in r and r['data_date']:
            latest_info = r['data_date']
        
        detail = ""
        if 'monthly' in r:
            m = r['monthly']
            detail = f"{m.get('stocks', '?')} 只, {m.get('rows', '?')} 行"
        elif 'stocks' in r:
            detail = f"{r['stocks']} 只"
        elif 'file_count' in r:
            detail = f"{r['file_count']} 文件"
        
        lines.append(f"| {name} | {icon} | {days_str} | {latest_info} | {detail} |")
    
    lines.append("")
    
    # Recommendations
    if criticals or warnings:
        lines.append("## 🛠️ 建议操作")
        lines.append("")
        for name in criticals:
            r = checks[name]
            if '期货' in name:
                lines.append(f"- **{name}**: 期货选品 cron 已暂停（上次更新 5/8），如需恢复请启用 cron 并运行选品脚本")
            elif '日线' in name:
                mkt = 'cn' if 'A股' in name else ('hk' if '港股' in name else 'us')
                lines.append(f"- **{name}**: 运行 `python3.11 update_all_data.py --market {mkt} --incremental`")
            elif '换手率' in name:
                lines.append(f"- **{name}**: 运行 CN 数据更新（含 efinance 换手率阶段）")
            elif '成分股' in name:
                if 'S&P500' in name:
                    lines.append(f"- **{name}**: S&P500 周更 cron 将自动刷新，或手动更新")
                else:
                    lines.append(f"- **{name}**: 考虑定期从数据源刷新成分股列表")
            elif '因子' in name:
                lines.append(f"- **{name}**: 确保对应市场日线数据已更新，然后运行选股")
            elif '市场状态' in name:
                lines.append(f"- **{name}**: 运行 `market_regime.py --market all --save`")
        lines.append("")
    
    if not criticals and not warnings:
        lines.append("✅ **所有数据源保鲜正常**")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='数据保鲜检查')
    parser.add_argument('--json', action='store_true', help='JSON 输出')
    parser.add_argument('--quiet', action='store_true', help='仅输出有问题的项')
    args = parser.parse_args()
    
    checks = run_all_checks()
    
    if args.json:
        # Clean up for JSON output
        clean = {}
        for name, r in checks.items():
            clean[name] = {k: v for k, v in r.items() if k != 'threshold'}
        print(json.dumps(clean, indent=2, ensure_ascii=False, default=str))
    else:
        report = generate_markdown(checks)
        
        if args.quiet:
            criticals = [name for name, r in checks.items() if r['level'] == 'critical']
            warnings = [name for name, r in checks.items() if r['level'] == 'warning']
            if not criticals and not warnings:
                print("✅ All data fresh")
                return
            # Print only the issue sections
            for line in report.split('\n'):
                if line.startswith('## 🔴') or line.startswith('## 🟡') or line.startswith('## 🛠️') or line.startswith('- **'):
                    print(line)
        else:
            print(report)


if __name__ == '__main__':
    main()
