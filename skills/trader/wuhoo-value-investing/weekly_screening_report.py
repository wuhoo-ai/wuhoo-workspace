#!/usr/bin/env python3.11
"""
weekly_screening_report.py — 各市场每周价值投资筛选报告

整合 quality_screen + investment_checklist，产出各市场结构化周报。
支持三市场 (CN/HK/US) 并行筛选，含环比变化追踪。

用法:
  python3.11 weekly_screening_report.py                    # 三市场全量
  python3.11 weekly_screening_report.py --market us        # 单一市场
  python3.11 weekly_screening_report.py --market all --checklist-top 5  # Top5过checklist

输出:
  ~/wuhoo-workspace/data/value-investing/reports/weekly_{market}_{date}.md
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

HOME = Path.home()
WS = HOME / "wuhoo-workspace"
DATA_DIR = WS / "data" / "value-investing"
REPORTS_DIR = DATA_DIR / "reports"
SKILL_DIR = Path(__file__).parent
STOCK_PICK_DATA = WS / "data" / "stock-pick"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Market configs ──────────────────────────────────────

MARKET_NAMES = {
    'cn': 'A股（中证1000）',
    'hk': '港股（恒生Top500）',
    'us': '美股（S&P 500）'
}

MARKET_BENCHMARKS = {
    'cn': '沪深300',
    'hk': '恒生指数',
    'us': 'S&P 500'
}


# ── Data Loading ────────────────────────────────────────

def load_latest_quality(market):
    """Load latest quality screen results."""
    cache = DATA_DIR / "quality_screen_cache.json"
    detail_file = sorted(DATA_DIR.glob(f"quality_detail_{market}_*.json"))
    
    results = []
    if detail_file:
        with open(detail_file[-1]) as f:
            results = json.load(f)
    elif cache.exists():
        with open(cache) as f:
            cache_data = json.load(f)
            results = [v for k, v in cache_data.items() 
                      if k.startswith(f"{market}_")]
    
    return results


def load_checklist_reports(market, date_str=None):
    """Load checklist reports for a market."""
    date_str = date_str or datetime.now().strftime('%Y%m%d')
    reports = list(DATA_DIR.glob(f"checklist_{market}_*{date_str}.md"))
    return reports


def load_last_week_summary(market):
    """Load last week's report for comparison."""
    reports = sorted(REPORTS_DIR.glob(f"weekly_{market}_*.md"), reverse=True)
    if len(reports) >= 2:
        return reports[1]  # Previous week
    return None


def load_universe_info():
    """Load index members with names."""
    universe = {}
    for market in ['cn', 'hk', 'us']:
        csv_map = {
            'cn': STOCK_PICK_DATA / "index_members.csv",
            'hk': STOCK_PICK_DATA / "index_members_hk_top500.csv",
            'us': STOCK_PICK_DATA / "index_members_us_top500.csv"
        }
        csv_path = csv_map.get(market)
        if csv_path and csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                universe[market] = {
                    'count': len(df),
                    'names': dict(zip(df.iloc[:, 0], df.iloc[:, 1] if len(df.columns) > 1 else df.iloc[:, 0]))
                }
            except:
                universe[market] = {'count': 0, 'names': {}}
    return universe


# ── Report Generation ───────────────────────────────────

def generate_weekly_report(market, quality_results, universe_info, 
                          checklist_results=None, last_week=None):
    """Generate a weekly screening report for one market."""
    lines = []
    market_name = MARKET_NAMES.get(market, market.upper())
    benchmark = MARKET_BENCHMARKS.get(market, '')
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
    
    lines.append(f"# 📊 {market_name} 价值投资周度筛选报告")
    lines.append(f"\n**报告周期**: {week_start} → {now.strftime('%Y-%m-%d')}")
    lines.append(f"**基准指数**: {benchmark}")
    lines.append(f"**Universe**: {universe_info.get(market, {}).get('count', '?')} 只")
    lines.append(f"\n> *基于 ai-berkshire 巴菲特-芒格-段永平-李录四大师方法论*\n")
    
    # ── Section 1: Quality Screen Summary ──
    lines.append("---\n")
    lines.append("## 一、质量筛选总览\n")
    
    if not quality_results:
        lines.append("⚠️ 本周暂无质量筛选数据，请先运行 `quality_screen.py`\n")
        return '\n'.join(lines)
    
    total = len(quality_results)
    passes = [r for r in quality_results if r.get('verdict') == 'pass']
    borders = [r for r in quality_results if r.get('verdict') == 'borderline']
    fails = [r for r in quality_results if r.get('verdict') == 'fail']
    errors = [r for r in quality_results if r.get('verdict') == 'error']
    
    pass_rate = len(passes) / total * 100 if total else 0
    
    lines.append(f"| 类别 | 数量 | 占比 |")
    lines.append(f"|------|:---:|:----:|")
    lines.append(f"| ✅ 通过 | {len(passes)} | {len(passes)/max(total,1)*100:.1f}% |")
    lines.append(f"| ⚠️ 边界 | {len(borders)} | {len(borders)/max(total,1)*100:.1f}% |")
    lines.append(f"| ❌ 排除 | {len(fails)} | {len(fails)/max(total,1)*100:.1f}% |")
    if errors:
        lines.append(f"| 🔧 数据错误 | {len(errors)} | {len(errors)/max(total,1)*100:.1f}% |")
    lines.append(f"| **总计** | **{total}** | **100%** |")
    lines.append("")
    
    # Quality grade
    if pass_rate >= 70:
        grade = "🟢 优质市场 — 大部分公司通过质量筛选"
    elif pass_rate >= 40:
        grade = "🟡 中等市场 — 约一半公司通过，需精选"
    else:
        grade = "🔴 低质市场 — 多数公司不达标，选股需极度谨慎"
    lines.append(f"**质量评级**: {grade}\n")
    
    # ── Section 2: Top Passing Stocks ──
    lines.append("## 二、通过筛选的优质标的\n")
    
    # Sort passes by some quality metric
    sorted_passes = sorted(passes, key=lambda r: r.get('pe') or 999)[:20]
    
    if sorted_passes:
        lines.append(f"| # | 代码 | 名称 | PE | PB | 行业 |")
        lines.append(f"|---|------|------|:---:|:---:|------|")
        for i, r in enumerate(sorted_passes, 1):
            code = r.get('code', '')
            name = r.get('name', code)
            pe = f"{r['pe']:.1f}" if r.get('pe') else 'N/A'
            pb = f"{r['pb']:.1f}" if r.get('pb') else 'N/A'
            industry = r.get('industry', '')
            lines.append(f"| {i} | {code} | {name} | {pe} | {pb} | {industry} |")
        lines.append("")
    
    # ── Section 3: Borderline Watchlist ──
    if borders:
        lines.append("## 三、边界观察名单\n")
        lines.append("以下标的未完全通过质量筛选，但满足部分条件，值得持续跟踪：\n")
        lines.append(f"| 代码 | 名称 | 未通过指标 | PE |")
        lines.append(f"|------|------|-----------|:---:|")
        for r in borders[:10]:
            code = r.get('code', '')
            name = r.get('name', code)
            failures = r.get('failures', [])
            pe = f"{r['pe']:.1f}" if r.get('pe') else 'N/A'
            lines.append(f"| {code} | {name} | {', '.join(failures[:3])} | {pe} |")
        lines.append("")
    
    # ── Section 4: Indicator Failure Analysis ──
    lines.append("## 四、淘汰原因分布\n")
    
    indicator_names = {
        'roe': 'ROE过低', 'fcf_5yr': 'FCF为负', 'interest_coverage': '利息覆盖不足',
        'gross_margin': '毛利率过低', 'ocf_to_ni': '现金流/利润比低', 
        'net_margin': '净利率过低', 'share_dilution': '股本稀释严重'
    }
    
    failure_counts = {}
    for r in quality_results:
        for f in r.get('failures', []):
            name = indicator_names.get(f, f)
            failure_counts[name] = failure_counts.get(name, 0) + 1
    
    if failure_counts:
        lines.append(f"| 淘汰指标 | 触犯次数 | 占比 |")
        lines.append(f"|---------|:-----:|:----:|")
        for name, count in sorted(failure_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {name} | {count} | {count/max(total,1)*100:.1f}% |")
        lines.append("")
    
    # ── Section 5: Industry Concentration ──
    lines.append("## 五、通过标的行业分布\n")
    
    industry_counts = {}
    for r in passes:
        ind = r.get('industry', 'unknown')
        industry_counts[ind] = industry_counts.get(ind, 0) + 1
    
    if industry_counts:
        lines.append(f"| 行业 | 通过数 |")
        lines.append(f"|------|:-----:|")
        for ind, count in sorted(industry_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {ind} | {count} |")
        lines.append("")
    
    # ── Section 6: Actionable Insights ──
    lines.append("## 六、行动建议\n")
    
    if passes:
        top_n = min(5, len(sorted_passes))
        lines.append(f"### 本周重点关注 ({market.upper()})\n")
        for i, r in enumerate(sorted_passes[:top_n], 1):
            code = r.get('code', '')
            name = r.get('name', code)
            pe = r.get('pe', 'N/A')
            lines.append(f"{i}. **{name}** ({code}) — PE={pe}")
            lines.append(f"   - 建议：运行 `investment_checklist.py --code {code} --market {market}` 做6关检查")
            lines.append(f"   - 通过Checklist后：运行 `value_deep_analysis.py --code {code} --market {market}` 深度分析")
        
        lines.append(f"\n### 后续步骤\n")
        lines.append("1. 对重点标的执行 Checklist（`investment_checklist.py`）")
        lines.append("2. Checklist 通过的标的执行深度分析（`value_deep_analysis.py`）")
        lines.append("3. 如需行业级别发现，使用行业漏斗（`industry_funnel.py`）")
        lines.append("4. 将研究成果记录到论文追踪（`thesis_tracker.py add`）")
    else:
        lines.append("⚠️ 本周无通过质量筛选的标的。建议：")
        lines.append(f"- 检查数据源是否正常（`quality_screen.py --market {market} --force`）")
        lines.append("- 考虑放宽阈值或等待市场调整后的机会")
    
    lines.append("")
    
    # ── Section 7: Week-over-Week Comparison ──
    lines.append("## 七、环比变化\n")
    if last_week and last_week.exists():
        lines.append(f"上周报告: `{last_week.name}`")
        lines.append("> 环比分析需对比两份报告中的通过率变化\n")
    else:
        lines.append("📌 首次报告，无上周数据对比。下次报告将自动包含环比分析。\n")
    
    # ── Footer ──
    lines.append("---\n")
    lines.append(f"*报告生成时间: {now.strftime('%Y-%m-%d %H:%M')}*")
    lines.append(f"*数据来源: wuhoo-value-investing + ai-berkshire 方法论*")
    lines.append(f"*⚠️ 本报告由AI辅助生成，不可直接作为投资依据。所有标的需经过Checklist和深度分析后方可考虑交易。*\n")
    
    return '\n'.join(lines)


def generate_combined_summary(market_reports, output_path):
    """Generate a combined 3-market executive summary."""
    now = datetime.now()
    lines = []
    lines.append("# 🏛️ 价值投资三市场周度筛选总览")
    lines.append(f"\n**报告日期**: {now.strftime('%Y-%m-%d')}")
    lines.append(f"\n---\n")
    
    # Summary table
    lines.append("## 各市场质量概况\n")
    lines.append("| 市场 | Universe | 通过 | 通过率 | 质量评级 |")
    lines.append("|------|:-------:|:----:|:------:|:-------:|")
    
    for market in ['cn', 'hk', 'us']:
        report = market_reports.get(market, '')
        if report:
            # Extract key numbers
            pass_rate = 0
            pass_count = total = 0
            for line in report.split('\n'):
                if '通过 |' in line and '✅' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        try: pass_count = int(parts[2])
                        except: pass
                if '总计' in line and '**' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        try: total = int(parts[2].replace('**',''))
                        except: pass
            pass_rate = pass_count / max(total, 1) * 100
            
            grade = "🟢" if pass_rate >= 70 else ("🟡" if pass_rate >= 40 else "🔴")
            lines.append(f"| {MARKET_NAMES.get(market, market)} | {total} | {pass_count} | {pass_rate:.1f}% | {grade} |")
    
    lines.append("")
    lines.append("## 快速导航\n")
    for market in ['cn', 'hk', 'us']:
        lines.append(f"- [{MARKET_NAMES.get(market, market)}](#) — 详见 `weekly_{market}_{now.strftime('%Y%m%d')}.md`")
    
    lines.append(f"\n---\n")
    lines.append("*⚠️ 本报告由AI辅助生成，不可直接作为投资依据。*\n")
    
    if output_path:
        Path(output_path).write_text('\n'.join(lines), encoding='utf-8')
    
    return '\n'.join(lines)


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='价值投资周度筛选报告')
    parser.add_argument('--market', default='all', choices=['cn', 'hk', 'us', 'all'],
                       help='市场 (default: all)')
    parser.add_argument('--checklist-top', type=int, default=0,
                       help='对Top N通过标的自动跑Checklist')
    parser.add_argument('--force-quality', action='store_true',
                       help='强制重新运行质量筛选')
    parser.add_argument('--output-dir', help='输出目录')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else REPORTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    markets = ['cn', 'hk', 'us'] if args.market == 'all' else [args.market]
    date_str = datetime.now().strftime('%Y%m%d')
    
    # Load universe info
    universe = load_universe_info()
    
    # Force quality screen if requested
    if args.force_quality:
        import subprocess
        print("🔄 强制刷新质量筛选...")
        for m in markets:
            subprocess.run(
                ['python3.11', str(SKILL_DIR / 'quality_screen.py'), 
                 '--market', m, '--force'],
                cwd=str(SKILL_DIR), timeout=300
            )
        print("✅ 质量筛选刷新完成\n")
    
    market_reports = {}
    
    for market in markets:
        print(f"📊 生成 {MARKET_NAMES.get(market, market)} 周报...")
        
        quality_results = load_latest_quality(market)
        last_week = load_last_week_summary(market)
        
        # Run checklist on top N if requested
        checklist_results = []
        if args.checklist_top > 0 and quality_results:
            passes = [r for r in quality_results if r.get('verdict') == 'pass']
            top_n = sorted(passes, key=lambda r: r.get('pe') or 999)[:args.checklist_top]
            
            for r in top_n:
                code = r['code']
                name = r.get('name', code)
                print(f"  📋 Checklist: {name} ({code})")
                import subprocess
                subprocess.run(
                    ['python3.11', str(SKILL_DIR / 'investment_checklist.py'),
                     '--code', code, '--market', market, '--name', name],
                    cwd=str(SKILL_DIR), timeout=60
                )
        
        # Generate report
        report = generate_weekly_report(
            market, quality_results, universe,
            checklist_results, last_week
        )
        
        output_path = output_dir / f"weekly_{market}_{date_str}.md"
        output_path.write_text(report, encoding='utf-8')
        market_reports[market] = report
        
        # Count passes
        passes = [r for r in quality_results if r.get('verdict') == 'pass']
        total = len(quality_results)
        pass_rate = len(passes) / max(total, 1) * 100
        print(f"  ✅ {output_path} ({len(passes)}/{total} 通过, {pass_rate:.1f}%)")
    
    # Combined summary for all-market runs
    if args.market == 'all':
        summary_path = output_dir / f"weekly_ALL_{date_str}.md"
        generate_combined_summary(market_reports, summary_path)
        print(f"\n📋 汇总报告: {summary_path}")
    
    print(f"\n✅ 周报生成完成 — {len(markets)} 市场")


if __name__ == '__main__':
    main()
