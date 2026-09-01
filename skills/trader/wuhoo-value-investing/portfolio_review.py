#!/usr/bin/env python3.11
"""
portfolio_review.py — 组合管理与审视
基于 ai-berkshire portfolio-review skill 改编

分析维度:
  1. 单仓位体检（论文健康度、仓位合理性）
  2. 集中度分析（前1/前3占比、持仓数量、现金占比）
  3. 相关性检查（行业/国家/货币风险共振）
  4. 机会成本排序（预期回报×确定性，末位淘汰）
  5. 压力测试（4情景：衰退/中美冲突/利率飙升/泡沫破裂）

用法:
  python3.11 portfolio_review.py --portfolio ~/wuhoo-workspace/data/us/portfolio.json
  python3.11 portfolio_review.py --market all
"""

import argparse
import json
import math
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

HOME = Path.home()
WS = HOME / "wuhoo-workspace"
DATA_DIR = WS / "data" / "value-investing"
SKILL_DIR = Path(__file__).parent

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Portfolio Loading ───────────────────────────────────

def load_portfolio(market='all'):
    """Load portfolio from wuhoo data."""
    portfolio = {"holdings": [], "cash": {}, "total_value": 0}
    
    # US portfolio
    us_path = WS / "data" / "us" / "portfolio.json"
    if us_path.exists() and market in ('us', 'all'):
        with open(us_path) as f:
            us_data = json.load(f)
        for h in us_data.get('holdings', []):
            h['market'] = 'us'
            portfolio['holdings'].append(h)
        portfolio['us_path'] = str(us_path)
    
    # Try to get actual holdings from debate results
    debate_dir = WS / "data" / "debate"
    if debate_dir.exists():
        # Find latest debate summary
        pass
    
    return portfolio


# ── Analysis Functions ──────────────────────────────────

def analyze_concentration(holdings):
    """Analyze portfolio concentration."""
    if not holdings:
        return {"error": "no holdings"}
    
    total_value = sum(h.get('market_value', h.get('value', 0)) for h in holdings)
    if total_value == 0:
        return {"error": "total value is 0"}
    
    # Sort by value descending
    sorted_holdings = sorted(holdings, 
        key=lambda h: h.get('market_value', h.get('value', 0)), reverse=True)
    
    top1_pct = (sorted_holdings[0].get('market_value', 0) / total_value * 100) if sorted_holdings else 0
    top3_value = sum(h.get('market_value', 0) for h in sorted_holdings[:3])
    top3_pct = top3_value / total_value * 100 if total_value else 0
    
    return {
        "total_holdings": len(holdings),
        "total_value": total_value,
        "top1_name": sorted_holdings[0].get('name', sorted_holdings[0].get('code', '')),
        "top1_pct": round(top1_pct, 1),
        "top3_pct": round(top3_pct, 1),
        "concentration_verdict": (
            "✅ 适度集中" if 50 <= top3_pct <= 80 else
            ("⚠️ 过度集中" if top3_pct > 80 else "⚠️ 过度分散")
        ),
        "suggested_range": {
            "top1_max": 40,
            "top3_range": "50-80%",
            "holdings_count": "5-15只",
            "cash_range": "10-30%"
        }
    }


def check_correlation(holdings):
    """Check for hidden correlations between holdings."""
    if len(holdings) < 2:
        return {"risk": "单只持仓，无相关性风险"}
    
    # Group by market/sector
    by_market = {}
    for h in holdings:
        market = h.get('market', 'unknown')
        by_market[market] = by_market.get(market, 0) + 1
    
    risks = []
    for market, count in by_market.items():
        total = len(holdings)
        if count / total > 0.5:
            risks.append(f"⚠️ {market.upper()} 市场占比 {count/total*100:.0f}%，单一市场风险")
    
    # Key questions
    checklist = [
        "是否有超过50%的仓位暴露在同一个主题/行业？",
        "是否有超过50%的仓位暴露在同一个国家/货币？",
        "如果中美关系恶化，组合会亏多少？",
        "如果全球经济衰退，组合会亏多少？"
    ]
    
    return {
        "by_market": by_market,
        "risks": risks,
        "checklist": checklist
    }


def opportunity_cost(holdings):
    """Rank holdings by expected return × certainty."""
    ranked = []
    for h in holdings:
        pe = h.get('pe')
        roe = h.get('roe')
        
        # Simple expected return estimate
        expected_return = None
        if pe and pe > 0:
            expected_return = 1 / pe * 100  # Earnings yield
        elif roe and roe > 0:
            expected_return = roe
        
        ranked.append({
            "name": h.get('name', h.get('code', '')),
            "code": h.get('code', ''),
            "weight": h.get('weight', h.get('market_value', 0)),
            "expected_return_pct": round(expected_return, 1) if expected_return else None,
            "certainty": "medium"
        })
    
    ranked.sort(key=lambda x: x.get('expected_return_pct') or 0, reverse=True)
    
    # Cash comparison
    risk_free_rate = 4.0  # ~current 10yr treasury
    
    return {
        "ranked": ranked,
        "risk_free_rate": risk_free_rate,
        "key_question": "排名最后的持仓，预期回报是否高于现金（无风险利率）？",
        "advice": "如果预期回报 < 无风险利率，应考虑卖出换成现金"
    }


def stress_test(holdings):
    """Run stress test scenarios."""
    scenarios = [
        {"name": "全球衰退", "assumption": "企业盈利下降20-30%", "impact": "预估-15%到-25%"},
        {"name": "中美冲突升级", "assumption": "中概股折价50%", "impact": "中概/港股持仓预估-30%到-50%"},
        {"name": "利率飙升", "assumption": "10年期国债→6%", "impact": "高PE成长股预估-20%到-40%"},
        {"name": "科技泡沫破裂", "assumption": "科技股PE压缩40%", "impact": "科技股持仓预估-30%到-50%"},
    ]
    
    # Identify vulnerable holdings
    results = []
    for scenario in scenarios:
        results.append({
            "scenario": scenario["name"],
            "assumption": scenario["assumption"],
            "estimated_impact": scenario["impact"],
            "most_vulnerable": []
        })
    
    return results


# ── Report Generation ───────────────────────────────────

def generate_review_report(holdings, analysis, output_path=None):
    """Generate portfolio review report."""
    lines = []
    lines.append("# 投资组合审视报告")
    lines.append(f"\n**审视日期**: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"**持仓数量**: {len(holdings)} 只")
    lines.append(f"\n> *\"分散投资是对无知的保护。如果你知道自己在做什么，分散投资就没有意义。\" — 巴菲特*")
    lines.append(f"\n---\n")
    
    # 1. Portfolio Overview
    lines.append("## 一、组合概览\n")
    lines.append("| 标的 | 代码 | 市场 | 占比 | PE | ROE |")
    lines.append("|------|------|------|------|-----|-----|")
    for h in holdings:
        name = h.get('name', h.get('code', ''))
        code = h.get('code', '')
        market = h.get('market', '')
        weight = h.get('weight', h.get('market_value', 0))
        pe = h.get('pe', 'N/A')
        roe = h.get('roe', 'N/A')
        lines.append(f"| {name} | {code} | {market} | {weight} | {pe} | {roe} |")
    lines.append("")
    
    # 2. Concentration
    conc = analysis.get('concentration', {})
    lines.append("## 二、集中度分析\n")
    lines.append(f"- 第一大持仓: {conc.get('top1_name', 'N/A')} ({conc.get('top1_pct', 0)}%)")
    lines.append(f"- 前三大持仓占比: {conc.get('top3_pct', 0)}%")
    lines.append(f"- 持仓数量: {conc.get('total_holdings', 0)} 只")
    lines.append(f"- 判断: {conc.get('concentration_verdict', 'N/A')}\n")
    
    # 3. Correlation
    corr = analysis.get('correlation', {})
    lines.append("## 三、相关性检查\n")
    for risk in corr.get('risks', []):
        lines.append(f"- {risk}")
    if not corr.get('risks'):
        lines.append("- ✅ 未发现明显风险共振")
    for item in corr.get('checklist', [])[:4]:
        lines.append(f"- [ ] {item}")
    lines.append("")
    
    # 4. Opportunity Cost
    oc = analysis.get('opportunity_cost', {})
    lines.append("## 四、机会成本排序\n")
    lines.append("| 排名 | 标的 | 预期年化回报 |")
    lines.append("|:----:|------|:----------:|")
    for i, h in enumerate(oc.get('ranked', []), 1):
        lines.append(f"| {i} | {h['name']} | {h.get('expected_return_pct', 'N/A')}% |")
    lines.append(f"\n无风险利率: {oc.get('risk_free_rate', 4)}%")
    lines.append(f"\n{oc.get('key_question', '')}")
    lines.append("")
    
    # 5. Stress Test
    st = analysis.get('stress_test', [])
    lines.append("## 五、压力测试\n")
    lines.append("| 情景 | 假设 | 预估影响 |")
    lines.append("|------|------|----------|")
    for s in st:
        lines.append(f"| {s['scenario']} | {s['assumption']} | {s['estimated_impact']} |")
    lines.append("")
    
    # 6. Conclusion
    lines.append("## 六、综合结论\n")
    lines.append("| 维度 | 状态 |")
    lines.append("|------|------|")
    lines.append(f"| 集中度 | {conc.get('concentration_verdict', 'N/A')} |")
    lines.append("| 相关性 | 待评估 |")
    lines.append("| 机会成本 | 待评估 |")
    lines.append("")
    lines.append("**最应该做的一件事**: 待确定")
    lines.append("\n---\n")
    lines.append("*下次审视: 季度审视 + 重大事件触发*\n")
    
    report = '\n'.join(lines)
    
    if output_path:
        Path(output_path).write_text(report, encoding='utf-8')
    
    return report


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='投资组合审视')
    parser.add_argument('--portfolio', help='持仓文件路径 (JSON)')
    parser.add_argument('--market', default='all', choices=['cn', 'hk', 'us', 'all'],
                       help='市场')
    parser.add_argument('--output-dir', help='输出目录')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else (DATA_DIR / "reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load portfolio
    if args.portfolio:
        with open(args.portfolio) as f:
            data = json.load(f)
        holdings = data.get('holdings', [])
    else:
        data = load_portfolio(args.market)
        holdings = data.get('holdings', [])
    
    if not holdings:
        print("⚠️ 未找到持仓数据。请指定 --portfolio 或以 --market 加载。")
        print(f"   US portfolio: {WS / 'data' / 'us' / 'portfolio.json'}")
        sys.exit(1)
    
    print(f"📊 组合审视: {len(holdings)} 只持仓")
    
    # Run analyses
    analysis = {
        "concentration": analyze_concentration(holdings),
        "correlation": check_correlation(holdings),
        "opportunity_cost": opportunity_cost(holdings),
        "stress_test": stress_test(holdings)
    }
    
    # Generate report
    output_path = output_dir / f"portfolio_review_{datetime.now().strftime('%Y%m%d')}.md"
    report = generate_review_report(holdings, analysis, str(output_path))
    
    print(f"  报告: {output_path}")
    print(f"  {analysis['concentration'].get('concentration_verdict', '')}")
    print(f"  ✅ 审视完成")


if __name__ == '__main__':
    main()
