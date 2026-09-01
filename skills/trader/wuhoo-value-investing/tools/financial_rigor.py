#!/usr/bin/env python3.11
"""
financial_rigor.py — 金融数据精确计算工具
Adapted from ai-berkshire/tools/financial_rigor.py
零外部依赖（stdlib only：decimal, json, math, argparse）

核心功能：
  verify-market-cap   市值验算（股价 × 总股本 vs 报告市值）
  cross-validate      关键数据多源交叉验证
  verify-valuation    估值指标精确验算（PE/PB/ROE/FCF Yield）
  three-scenario      三情景估值（乐观/中性/悲观）
  reverse-dcf         反向DCF：当前股价隐含什么增长预期

设计原则：
  - 所有计算使用 decimal.Decimal（精确十进制），不用 float
  - 输出直接可嵌入报告附录
  - 偏差 >1% 标记 ⚠️，>5% 标记 ❌
"""

import argparse
import json
import math
import sys
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, DivisionByZero
from typing import Dict, Tuple, Optional

# ── helpers ─────────────────────────────────────────────

def _d(val, default=None):
    """Safe Decimal conversion."""
    if val is None or val == '' or val == 'N/A':
        if default is not None:
            return Decimal(str(default))
        return None
    try:
        return Decimal(str(val).replace(',', '').replace('%', '').strip())
    except (InvalidOperation, ValueError):
        if default is not None:
            return Decimal(str(default))
        return None


def _pct_diff(a: Decimal, b: Decimal) -> Decimal:
    """Percentage difference between two values."""
    if a == 0:
        return Decimal('100')
    return abs(a - b) / abs(a) * 100


def _fmt(v: Decimal, decimals: int = 2) -> str:
    """Format decimal to string with commas."""
    if v is None:
        return 'N/A'
    s = f"{v:,.{decimals}f}"
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s


def _fmt_pct(v: Decimal, decimals: int = 1) -> str:
    """Format as percentage string."""
    if v is None:
        return 'N/A'
    return f"{v:.{decimals}f}%"


# ── verify-market-cap ───────────────────────────────────

def verify_market_cap(price, shares_billion, reported_market_cap, currency='CNY'):
    """
    市值验算：股价 × 总股本 vs 报告市值
    
    Returns:
        dict with computed, reported, deviation_pct, verdict
    """
    p = _d(price)
    s = _d(shares_billion)
    r = _d(reported_market_cap)
    
    if p is None or s is None:
        return {"error": "价格或股本数据无效", "currency": currency}
    
    # 总股本单位：亿股，市值单位需要统一
    computed = p * s * Decimal('100000000')  # 股价 × 亿股 × 1亿
    
    result = {
        "currency": currency,
        "price": float(p),
        "shares_billion": float(s),
        "computed_market_cap": float(computed),
        "computed_market_cap_display": _fmt(computed / Decimal('100000000'), 2) + '亿',
    }
    
    if r is not None and r > 0:
        deviation = _pct_diff(computed, r)
        result["reported_market_cap"] = float(r)
        result["deviation_pct"] = float(round(deviation, 2))
        
        if deviation <= 1:
            result["verdict"] = "✅ 验证通过"
            result["status"] = "pass"
        elif deviation <= 5:
            result["verdict"] = f"⚠️ 偏差 {deviation:.1f}%，需排查原因"
            result["status"] = "warn"
        else:
            result["verdict"] = f"❌ 偏差 {deviation:.1f}%，数据可能错误"
            result["status"] = "fail"
    else:
        result["reported_market_cap"] = None
        result["verdict"] = "⚠️ 无报告市值可对比，仅输出计算值"
        result["status"] = "unverified"
    
    return result


# ── cross-validate ──────────────────────────────────────

def cross_validate(field_name, values_dict, unit=''):
    """
    多源数据交叉验证。
    
    Args:
        field_name: 字段名（如 '收入'）
        values_dict: {'来源1': 数值, '来源2': 数值}
        unit: 单位（如 '亿', '万'）
    
    Returns:
        dict with sources, deviation matrix, verdict
    """
    parsed = {}
    for src, val in values_dict.items():
        d = _d(val)
        if d is not None:
            parsed[src] = d
    
    if len(parsed) < 2:
        return {
            "field": field_name,
            "unit": unit,
            "error": f"有效数据源不足（{len(parsed)}个），需要至少2个",
            "status": "insufficient"
        }
    
    sources = list(parsed.keys())
    max_deviation = Decimal('0')
    max_pair = ('', '')
    
    deviations = []
    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            dev = _pct_diff(parsed[sources[i]], parsed[sources[j]])
            deviations.append({
                "source1": sources[i],
                "source2": sources[j],
                "value1": float(parsed[sources[i]]),
                "value2": float(parsed[sources[j]]),
                "deviation_pct": float(round(dev, 2))
            })
            if dev > max_deviation:
                max_deviation = dev
                max_pair = (sources[i], sources[j])
    
    result = {
        "field": field_name,
        "unit": unit,
        "sources": {s: float(v) for s, v in parsed.items()},
        "deviations": deviations,
        "max_deviation_pct": float(round(max_deviation, 2))
    }
    
    if max_deviation <= 1:
        result["verdict"] = "✅ 一致，取来源1数值"
        result["status"] = "pass"
        result["recommended_value"] = float(parsed[sources[0]])
    elif max_deviation <= 5:
        result["verdict"] = f"⚠️ 数据存在差异（最大{max_deviation:.1f}%），需说明原因"
        result["status"] = "warn"
        result["recommended_value"] = float(parsed[sources[0]])
    else:
        result["verdict"] = f"❌ 数据存在重大差异（最大{max_deviation:.1f}%），必须查原始财报核实"
        result["status"] = "fail"
        result["recommended_value"] = None
    
    return result


# ── verify-valuation ────────────────────────────────────

def verify_valuation(price, eps, bvps, fcf_per_share=None, dividend=None):
    """
    估值指标精确验算。
    
    Returns:
        dict with PE, PB, FCF Yield, Dividend Yield
    """
    p = _d(price)
    e = _d(eps)
    b = _d(bvps)
    f = _d(fcf_per_share)
    d = _d(dividend)
    
    if p is None or p <= 0:
        return {"error": "股价无效"}
    
    result = {"price": float(p)}
    
    # PE
    if e is not None and e > 0:
        pe = p / e
        result["pe"] = float(round(pe, 2))
        result["eps"] = float(e)
    else:
        result["pe"] = None
        result["pe_note"] = "EPS无效或为负"
    
    # PB
    if b is not None and b > 0:
        pb = p / b
        result["pb"] = float(round(pb, 2))
        result["bvps"] = float(b)
    else:
        result["pb"] = None
    
    # FCF Yield
    if f is not None and f > 0:
        fcf_yield = f / p * 100
        result["fcf_yield_pct"] = float(round(fcf_yield, 2))
        result["fcf_per_share"] = float(f)
    else:
        result["fcf_yield_pct"] = None
    
    # Dividend Yield
    if d is not None and d > 0:
        div_yield = d / p * 100
        result["dividend_yield_pct"] = float(round(div_yield, 2))
        result["dividend_per_share"] = float(d)
    else:
        result["dividend_yield_pct"] = None
    
    return result


# ── three-scenario ──────────────────────────────────────

def three_scenario(price, eps, shares_billion, growth_rates, pe_targets, years=3, currency='CNY'):
    """
    三情景估值（乐观/中性/悲观）。
    
    Args:
        price: 当前股价
        eps: 当前EPS
        shares_billion: 总股本（亿股）
        growth_rates: [乐观增速%, 中性增速%, 悲观增速%]
        pe_targets: [乐观PE, 中性PE, 悲观PE]
        years: 预测年限
        currency: 币种
    
    Returns:
        dict with three scenarios, margin of safety for each
    """
    p = _d(price)
    e = _d(eps)
    s = _d(shares_billion)
    
    if p is None or e is None or s is None:
        return {"error": "输入数据无效"}
    
    labels = ['乐观', '中性', '悲观']
    scenarios = []
    
    for i, label in enumerate(labels):
        g = _d(growth_rates[i]) / 100
        pe = _d(pe_targets[i])
        
        # Future EPS = current_EPS * (1 + growth)^years
        future_eps = e * (1 + g) ** years
        # Future price = future_EPS * target_PE
        future_price = future_eps * pe
        # Market cap in 亿
        future_mcap = future_price * s
        # Annualized return
        if p > 0:
            annual_return = ((future_price / p) ** (Decimal('1') / years) - 1) * 100
        else:
            annual_return = Decimal('0')
        
        # Margin of safety: (intrinsic_value - market_price) / intrinsic_value
        if future_price > 0:
            mos = (future_price - p) / future_price * 100
        else:
            mos = Decimal('-999')
        
        scenarios.append({
            "scenario": label,
            "growth_rate_pct": float(growth_rates[i]),
            "target_pe": float(pe_targets[i]),
            "future_eps": float(round(future_eps, 4)),
            "future_price": float(round(future_price, 2)),
            "future_market_cap_billion": float(round(future_mcap, 2)),
            "annual_return_pct": float(round(annual_return, 2)),
            "margin_of_safety_pct": float(round(mos, 2)),
        })
    
    # Scoring
    mos_values = [s["margin_of_safety_pct"] for s in scenarios]
    all_positive = all(m > 0 for m in mos_values)
    all_negative = all(m <= 0 for m in mos_values)
    optimism_mos = mos_values[0]  # 乐观情景安全边际
    
    if all_positive:
        score = 2.0
        score_note = "极度低估（三情景全正安全边际）"
    elif mos_values[1] > 0 and mos_values[2] > 0:
        score = 1.5
        score_note = "显著低估（中性和悲观正安全边际）"
    elif mos_values[0] > 0:
        score = 0.5
        score_note = "仅乐观情景正安全边际"
    elif all_negative and optimism_mos > -30:
        score = 0.0
        score_note = "接近合理价（乐观溢价<30%）"
    elif all_negative and -30 >= optimism_mos >= -100:
        score = -0.5
        score_note = "温和高估（乐观溢价30-100%）"
    else:
        score = -1.5
        score_note = "严重高估（乐观溢价>100%）"
    
    return {
        "currency": currency,
        "current_price": float(p),
        "current_eps": float(e),
        "shares_billion": float(s),
        "years": years,
        "scenarios": scenarios,
        "valuation_score": score,
        "valuation_score_note": score_note
    }


# ── reverse-dcf ─────────────────────────────────────────

def reverse_dcf(price, eps, shares_billion, discount_rate=10, terminal_growth=3, currency='CNY'):
    """
    反向DCF：当前股价隐含什么增长预期。
    
    简化模型：P = EPS × (1+g) / (r-g)  →  解出 g
    → g = (r × P/EPS - 1) / (P/EPS + 1)
    
    Returns:
        dict with implied_growth, comparison to analyst estimates
    """
    p = _d(price)
    e = _d(eps)
    
    if p is None or e is None or e <= 0:
        return {"error": "股价或EPS无效"}
    
    pe = p / e
    r = _d(discount_rate) / 100
    
    # 从 P/E = (1+g)/(r-g) 解 g
    # P/E * (r-g) = 1+g
    # P/E*r - P/E*g = 1+g
    # P/E*r - 1 = g + P/E*g
    # P/E*r - 1 = g(1 + P/E)
    # g = (P/E*r - 1) / (1 + P/E)
    
    numerator = pe * r - 1
    denominator = 1 + pe
    implied_g = numerator / denominator * 100
    
    result = {
        "currency": currency,
        "current_price": float(p),
        "current_eps": float(e),
        "current_pe": float(round(pe, 2)),
        "discount_rate_pct": discount_rate,
        "terminal_growth_pct": terminal_growth,
        "implied_growth_pct": float(round(implied_g, 2)),
    }
    
    # Interpretation
    if implied_g < 0:
        result["interpretation"] = f"市场预期负增长（{implied_g:.1f}%），极度悲观或公司正在萎缩"
    elif implied_g < 5:
        result["interpretation"] = f"市场预期低增长（{implied_g:.1f}%），估值保守"
    elif implied_g < 10:
        result["interpretation"] = f"市场预期中等增长（{implied_g:.1f}%）"
    elif implied_g < 20:
        result["interpretation"] = f"市场预期高增长（{implied_g:.1f}%），需验证是否合理"
    else:
        result["interpretation"] = f"市场预期极高增长（{implied_g:.1f}%），警惕估值泡沫"
    
    return result


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='金融数据精确计算工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # verify-market-cap
    p_mcap = subparsers.add_parser('verify-market-cap', help='市值验算')
    p_mcap.add_argument('--price', type=float, required=True, help='股价')
    p_mcap.add_argument('--shares', type=float, required=True, help='总股本（亿股）')
    p_mcap.add_argument('--reported', type=float, required=True, help='报告市值（亿）')
    p_mcap.add_argument('--currency', default='CNY', help='币种')
    
    # cross-validate
    p_cross = subparsers.add_parser('cross-validate', help='多源交叉验证')
    p_cross.add_argument('--field', required=True, help='字段名')
    p_cross.add_argument('--values', required=True, help='JSON: {"源1": 值, "源2": 值}')
    p_cross.add_argument('--unit', default='', help='单位')
    
    # verify-valuation
    p_val = subparsers.add_parser('verify-valuation', help='估值指标验算')
    p_val.add_argument('--price', type=float, required=True, help='股价')
    p_val.add_argument('--eps', type=float, required=True, help='每股收益')
    p_val.add_argument('--bvps', type=float, required=True, help='每股净资产')
    p_val.add_argument('--fcf-per-share', type=float, help='每股自由现金流')
    p_val.add_argument('--dividend', type=float, help='每股股息')
    
    # three-scenario
    p_ts = subparsers.add_parser('three-scenario', help='三情景估值')
    p_ts.add_argument('--price', type=float, required=True, help='当前股价')
    p_ts.add_argument('--eps', type=float, required=True, help='当前EPS')
    p_ts.add_argument('--shares', type=float, required=True, help='总股本（亿股）')
    p_ts.add_argument('--growth', type=float, nargs=3, required=True, help='乐观 中性 悲观 增速(%)')
    p_ts.add_argument('--pe', type=float, nargs=3, required=True, help='乐观 中性 悲观 PE')
    p_ts.add_argument('--years', type=int, default=3, help='预测年限')
    p_ts.add_argument('--currency', default='CNY', help='币种')
    
    # reverse-dcf
    p_rdcf = subparsers.add_parser('reverse-dcf', help='反向DCF')
    p_rdcf.add_argument('--price', type=float, required=True, help='股价')
    p_rdcf.add_argument('--eps', type=float, required=True, help='EPS')
    p_rdcf.add_argument('--shares', type=float, default=1, help='总股本（亿股）')
    p_rdcf.add_argument('--discount-rate', type=float, default=10, help='折现率(%)')
    p_rdcf.add_argument('--terminal-growth', type=float, default=3, help='永续增长率(%)')
    p_rdcf.add_argument('--currency', default='CNY', help='币种')
    
    args = parser.parse_args()
    
    if args.command == 'verify-market-cap':
        result = verify_market_cap(args.price, args.shares, args.reported, args.currency)
    elif args.command == 'cross-validate':
        values = json.loads(args.values)
        result = cross_validate(args.field, values, args.unit)
    elif args.command == 'verify-valuation':
        result = verify_valuation(args.price, args.eps, args.bvps, 
                                   args.fcf_per_share, args.dividend)
    elif args.command == 'three-scenario':
        result = three_scenario(args.price, args.eps, args.shares,
                                args.growth, args.pe, args.years, args.currency)
    elif args.command == 'reverse-dcf':
        result = reverse_dcf(args.price, args.eps, args.shares,
                             args.discount_rate, args.terminal_growth, args.currency)
    else:
        parser.print_help()
        sys.exit(1)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
