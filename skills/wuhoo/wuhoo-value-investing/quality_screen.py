#!/usr/bin/env python3.11
"""
quality_screen.py — 价值投资质量预筛选
基于 ai-berkshire quality-screen skill 改编

对指数成分股执行7条去劣指标筛选，输出通过质量检查的股票池。
各市场独立阈值（A股放宽ROE至5%，港股地产/公用事业放宽负债率）。

用法:
  python3.11 quality_screen.py --market us --date 2026-06-29
  python3.11 quality_screen.py --market cn --force  # 强制全量刷新
  python3.11 quality_screen.py --market all          # 三市场全量

输出:
  ~/wuhoo-workspace/data/value-investing/quality_pass_{market}_{date}.csv
  ~/wuhoo-workspace/data/value-investing/quality_screen_cache.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
import yfinance as yf

# ── Paths ───────────────────────────────────────────────
HOME = Path.home()
WS = HOME / "wuhoo-workspace"
DATA_DIR = WS / "data" / "value-investing"
STOCK_PICK_DATA = WS / "data" / "stock-pick"
SKILL_DIR = Path(__file__).parent
CONFIG_DIR = SKILL_DIR / "configs"
CACHE_FILE = DATA_DIR / "quality_screen_cache.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Load config ─────────────────────────────────────────

def load_config():
    with open(CONFIG_DIR / "quality_thresholds.yaml", 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

# ── Helpers ─────────────────────────────────────────────

def load_universe(market, date_str):
    """Load index member list."""
    if market == 'us':
        csv_path = STOCK_PICK_DATA / "index_members_us_top500.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            codes = df['code'].tolist()
            names = dict(zip(df['code'], df.get('name', df['code'])))
            return codes, names
    
    elif market == 'hk':
        csv_path = STOCK_PICK_DATA / "index_members_hk_top500.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            codes = df['code'].tolist()
            names = dict(zip(df['code'], df.get('name', df['code'])))
            return codes, names
    
    elif market == 'cn':
        csv_path = STOCK_PICK_DATA / "index_members.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            codes = df['code'].tolist()
            names = dict(zip(df['code'], df.get('name', df['code'])))
            return codes, names
    
    return [], {}


def classify_industry(name, market_info):
    """Classify stock into industry group for exemption matching."""
    name_lower = (name or '').lower()
    industry_groups = CONFIG.get('industry_groups', {})
    
    for group, keywords in industry_groups.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return group
    return 'other'


def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ── Financial Data Fetching ─────────────────────────────

def fetch_us_financials(ticker, max_retries=2):
    """Fetch financial data for US stock via yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # ROE
        roe = info.get('returnOnEquity')
        if roe:
            roe = roe * 100
        
        # Financial statements
        try:
            cf = stock.cashflow
            bs = stock.balance_sheet
            inc = stock.income_stmt
            
            # FCF = Operating Cash Flow - CapEx
            if cf is not None and not cf.empty:
                ocf = cf.loc['Operating Cash Flow'] if 'Operating Cash Flow' in cf.index else cf.loc['Total Cash From Operating Activities']
                capex = cf.loc['Capital Expenditures'] if 'Capital Expenditures' in cf.index else pd.Series([0]*len(cf.columns), index=cf.columns)
                fcf = ocf - capex
            
            # Gross Margin
            if inc is not None and not inc.empty:
                revenue = inc.loc['Total Revenue']
                cogs = inc.loc['Cost Of Revenue'] if 'Cost Of Revenue' in inc.index else None
                if cogs is not None:
                    gross_margin = (revenue - cogs) / revenue * 100
                ni = inc.loc['Net Income']
                net_margin = ni / revenue * 100
        except:
            pass
        
        # Liabilities ratio
        total_debt = info.get('totalDebt', 0)
        total_assets = info.get('totalAssets', 1)
        liability_ratio = total_debt / total_assets * 100 if total_assets else 0
        
        # Interest coverage (from info)
        interest_coverage = None
        
        return {
            'roe': roe,
            'gross_margin': info.get('grossMargins', 0) * 100 if info.get('grossMargins') else None,
            'net_margin': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else None,
            'liability_ratio': liability_ratio,
            'interest_coverage': interest_coverage,
            'ocf_to_ni': None,
            'fcf_5yr': None,
            'share_dilution': None,
            'pe': info.get('trailingPE'),
            'pb': info.get('priceToBook'),
            'source': 'yfinance'
        }
    except Exception as e:
        return {'error': str(e), 'source': 'yfinance'}


def fetch_hk_financials(code, max_retries=2):
    """Fetch financial data for HK stock via yfinance."""
    # Convert HK.00700 → 0700.HK
    if code.startswith('HK.'):
        ticker = code[3:] + '.HK'
    else:
        ticker = code + '.HK'
    return fetch_us_financials(ticker)


def fetch_cn_financials(code, max_retries=2):
    """Fetch financial data for A-share via akshare."""
    try:
        import akshare as ak
        
        # Parse code format
        if '.' in code:
            symbol = code.split('.')[0]
        else:
            symbol = code
        
        # Get financial indicators
        df = ak.stock_financial_abstract(symbol=symbol)
        if df is None or df.empty:
            return {'error': 'akshare no data', 'source': 'akshare'}
        
        result = {'source': 'akshare'}
        
        # Extract indicators
        for _, row in df.iterrows():
            indicator = str(row.iloc[0])
            # Take the most recent year-end value
            for col in df.columns[1:]:
                if str(col).endswith('1231'):
                    val = row[col]
                    try:
                        val = float(val)
                    except:
                        continue
                    
                    if '净资产收益率' in indicator or 'ROE' in indicator:
                        result['roe'] = val
                    elif '毛利率' in indicator:
                        result['gross_margin'] = val
                    elif '净利率' in indicator:
                        result['net_margin'] = val
                    elif '资产负债率' in indicator:
                        result['liability_ratio'] = val
                    break
        
        # Get basic info
        try:
            info = ak.stock_individual_info_em(symbol=symbol)
            if info is not None and not info.empty:
                for _, row in info.iterrows():
                    if row['item'] == '市盈率-动态':
                        try:
                            result['pe'] = float(row['value'])
                        except:
                            pass
                    elif row['item'] == '市净率':
                        try:
                            result['pb'] = float(row['value'])
                        except:
                            pass
        except:
            pass
        
        return result
    except ImportError:
        return {'error': 'akshare not installed', 'source': 'akshare'}
    except Exception as e:
        return {'error': str(e), 'source': 'akshare'}


def fetch_financials(market, code, name):
    """Fetch financial data for a stock."""
    if market == 'us':
        return fetch_us_financials(code)
    elif market == 'hk':
        return fetch_hk_financials(code)
    elif market == 'cn':
        return fetch_cn_financials(code)
    return {'error': f'Unknown market: {market}'}


# ── Screening Logic ─────────────────────────────────────

def screen_stock(market, code, name, financials, thresholds, cache_entry=None):
    """
    Apply 7 quality indicators + 3 exemption rules.
    
    Returns:
        dict with pass/fail/exempt status for each indicator
    """
    th = thresholds
    industry = classify_industry(name, {})
    
    indicators = {}
    failures = []
    
    # 1. ROE
    roe = financials.get('roe')
    indicators['roe'] = {'value': roe, 'threshold': f"< {th['roe_10yr_avg']}%"}
    if roe is not None and roe < th['roe_10yr_avg']:
        # Check strategic investment exemption
        gm = financials.get('gross_margin')
        if gm is not None and gm > 30:
            indicators['roe']['exempt'] = 'strategic_investment'
        else:
            indicators['roe']['fail'] = True
            failures.append('roe')
    elif roe is not None:
        indicators['roe']['pass'] = True
    else:
        indicators['roe']['unknown'] = True
    
    # 2. FCF (skip if no data)
    fcf = financials.get('fcf_5yr')
    indicators['fcf_5yr'] = {'value': fcf, 'threshold': '< 0'}
    if fcf is not None and fcf < 0:
        indicators['fcf_5yr']['fail'] = True
        failures.append('fcf_5yr')
    elif fcf is not None:
        indicators['fcf_5yr']['pass'] = True
    
    # 3. Interest coverage (skip for financials)
    if 'financial' in industry:
        indicators['interest_coverage'] = {'skip': 'financial industry'}
    else:
        ic = financials.get('interest_coverage')
        indicators['interest_coverage'] = {'value': ic, 'threshold': '< 2x'}
        if ic is not None and ic < th['interest_coverage']:
            indicators['interest_coverage']['fail'] = True
            failures.append('interest_coverage')
        elif ic is not None:
            indicators['interest_coverage']['pass'] = True
    
    # 4. Gross Margin
    gm = financials.get('gross_margin')
    indicators['gross_margin'] = {'value': gm, 'threshold': f"< {th['gross_margin']}%"}
    if gm is not None and gm < th['gross_margin']:
        # Check high-turnover exemption
        roe_v = financials.get('roe')
        if roe_v is not None and roe_v > 20:
            indicators['gross_margin']['exempt'] = 'high_turnover'
        else:
            indicators['gross_margin']['fail'] = True
            failures.append('gross_margin')
    elif gm is not None:
        indicators['gross_margin']['pass'] = True
    
    # 5. OCF/NI
    ocf_ni = financials.get('ocf_to_ni')
    indicators['ocf_to_ni'] = {'value': ocf_ni, 'threshold': f"< {th['ocf_to_ni_5yr_avg']}"}
    if ocf_ni is not None and ocf_ni < th['ocf_to_ni_5yr_avg']:
        indicators['ocf_to_ni']['fail'] = True
        failures.append('ocf_to_ni')
    elif ocf_ni is not None:
        indicators['ocf_to_ni']['pass'] = True
    
    # 6. Net Margin
    nm = financials.get('net_margin')
    indicators['net_margin'] = {'value': nm, 'threshold': f"< {th['net_margin']}%"}
    if nm is not None and nm < th['net_margin']:
        # Check low-margin strategic exemption
        gm_v = financials.get('gross_margin')
        if gm_v is not None and gm_v > 30:
            indicators['net_margin']['exempt'] = 'low_margin_strategic'
        else:
            # Check high-turnover
            roe_v = financials.get('roe')
            if roe_v is not None and roe_v > 20:
                indicators['net_margin']['exempt'] = 'high_turnover'
            else:
                indicators['net_margin']['fail'] = True
                failures.append('net_margin')
    elif nm is not None:
        indicators['net_margin']['pass'] = True
    
    # 7. Share dilution
    dil = financials.get('share_dilution')
    indicators['share_dilution'] = {'value': dil, 'threshold': f"> {th['share_dilution_pct']}%"}
    if dil is not None and dil > th['share_dilution_pct']:
        indicators['share_dilution']['fail'] = True
        failures.append('share_dilution')
    elif dil is not None:
        indicators['share_dilution']['pass'] = True
    
    # Verdict
    fail_count = len(failures)
    if fail_count == 0:
        verdict = 'pass'
    elif fail_count <= 2:
        verdict = 'borderline'
    else:
        verdict = 'fail'
    
    return {
        'code': code,
        'name': name,
        'market': market,
        'industry': industry,
        'indicators': indicators,
        'failures': failures,
        'verdict': verdict,
        'pe': financials.get('pe'),
        'pb': financials.get('pb'),
        'source': financials.get('source', 'unknown')
    }


# ── Main Screen ─────────────────────────────────────────

def run_screen(market, date_str, force=False, sample_size=None):
    """
    Run quality screen for a market.
    
    Args:
        market: 'cn', 'hk', 'us', or 'all'
        date_str: YYYY-MM-DD
        force: force refresh, ignore cache
        sample_size: limit to N stocks (for testing)
    """
    cache = load_cache() if not force else {}
    cache_key = f"{market}_{date_str}"
    thresholds = CONFIG['markets'][market]['thresholds']
    
    codes, names = load_universe(market, date_str)
    if not codes:
        print(f"⚠️ {market}: no universe data found, skipping")
        return None
    
    if sample_size:
        codes = codes[:sample_size]
    
    total = len(codes)
    results = []
    pass_count = 0
    border_count = 0
    fail_count = 0
    
    print(f"\n{'='*60}")
    print(f"质量筛选: {CONFIG['markets'][market]['name']} ({total} 只)")
    print(f"{'='*60}")
    
    for i, code in enumerate(codes):
        name = names.get(code, code)
        
        # Check cache
        stock_key = f"{market}_{code}"
        if stock_key in cache and not force:
            cached = cache[stock_key]
            if cached.get('date') == date_str:
                results.append(cached)
                if cached['verdict'] == 'pass': pass_count += 1
                elif cached['verdict'] == 'borderline': border_count += 1
                else: fail_count += 1
                continue
        
        # Fetch financials (with rate limiting)
        if i > 0 and i % 20 == 0:
            time.sleep(2)  # Rate limit for yfinance
        
        financials = fetch_financials(market, code, name)
        
        if 'error' in financials:
            result = {
                'code': code, 'name': name, 'market': market,
                'verdict': 'error',
                'error': financials['error'],
                'source': financials.get('source', 'unknown')
            }
        else:
            result = screen_stock(market, code, name, financials, thresholds)
        
        result['date'] = date_str
        results.append(result)
        
        # Update cache
        cache[f"{market}_{code}"] = result
        
        if result['verdict'] == 'pass': pass_count += 1
        elif result['verdict'] == 'borderline': border_count += 1
        else: fail_count += 1
        
        # Progress
        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{total}] pass={pass_count} border={border_count} fail={fail_count}")
    
    save_cache(cache)
    
    # Summary
    print(f"\n  ✅ 通过: {pass_count} ({pass_count/total*100:.1f}%)")
    print(f"  ⚠️ 边界: {border_count} ({border_count/total*100:.1f}%)")
    print(f"  ❌ 排除: {fail_count} ({fail_count/total*100:.1f}%)")
    
    # Save CSV
    output_path = DATA_DIR / f"quality_pass_{market}_{date_str}.csv"
    pass_stocks = [r for r in results if r['verdict'] in ('pass', 'borderline')]
    
    if pass_stocks:
        df = pd.DataFrame([{
            'code': r['code'],
            'name': r['name'],
            'verdict': r['verdict'],
            'pe': r.get('pe'),
            'pb': r.get('pb'),
            'industry': r.get('industry', ''),
            'source': r.get('source', '')
        } for r in pass_stocks])
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n  通过池已保存: {output_path} ({len(pass_stocks)} 只)")
    
    # Save detailed JSON
    detail_path = DATA_DIR / f"quality_detail_{market}_{date_str}.json"
    # Simplify for JSON
    json_results = []
    for r in results:
        json_r = {k: v for k, v in r.items() if k != 'indicators'}
        json_r['indicator_summary'] = {}
        for k, v in r.get('indicators', {}).items():
            status = 'pass' if v.get('pass') else ('fail' if v.get('fail') else ('exempt' if v.get('exempt') else 'unknown'))
            json_r['indicator_summary'][k] = status
        json_results.append(json_r)
    
    with open(detail_path, 'w', encoding='utf-8') as f:
        json.dump(json_results, f, ensure_ascii=False, indent=2)
    print(f"  详细报告已保存: {detail_path}")
    
    return results


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='价值投资质量预筛选')
    parser.add_argument('--market', default='us', choices=['cn', 'hk', 'us', 'all'],
                       help='市场 (default: us)')
    parser.add_argument('--date', help='日期 YYYY-MM-DD (default: 今天)')
    parser.add_argument('--force', action='store_true', help='强制全量刷新，忽略缓存')
    parser.add_argument('--sample', type=int, help='仅测试前N只股票')
    parser.add_argument('--output-dir', help='输出目录 (default: data/value-investing/)')
    
    args = parser.parse_args()
    
    date_str = args.date or datetime.now().strftime('%Y-%m-%d')
    
    if args.output_dir:
        global DATA_DIR
        DATA_DIR = Path(args.output_dir)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    markets = ['cn', 'hk', 'us'] if args.market == 'all' else [args.market]
    
    all_results = {}
    for m in markets:
        result = run_screen(m, date_str, args.force, args.sample)
        all_results[m] = result
    
    # Overall summary
    print(f"\n{'='*60}")
    print("全市场汇总")
    print(f"{'='*60}")
    for m in markets:
        if all_results[m]:
            r = all_results[m]
            passes = sum(1 for x in r if x['verdict'] in ('pass', 'borderline'))
            total = len(r)
            print(f"  {m.upper()}: {passes}/{total} 通过 ({passes/total*100:.1f}%)")


if __name__ == '__main__':
    main()
