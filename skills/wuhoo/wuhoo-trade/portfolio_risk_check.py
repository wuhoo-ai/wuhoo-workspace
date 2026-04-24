#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组合级风险检查工具

用法:
    python portfolio_risk_check.py --market us  # 检查美股持仓风险
    python portfolio_risk_check.py --market hk  # 检查港股持仓风险
    python portfolio_risk_check.py --market us --symbols AAPL,MSFT,NVDA  # 检查指定股票
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "wuhoo-trade"))
from portfolio_risk import (
    PortfolioRiskChecker,
    classify_industry,
    INDUSTRY_MAP,
)

# 添加 debate 路径用于 RiskAgent
sys.path.insert(0, str(Path(__file__).parent.parent / "wuhoo-debate"))
from agents.risk_agent import RiskAgent


def load_portfolio(market: str, data_dir: str = "data") -> dict:
    """加载持仓数据"""
    portfolio_file = Path(data_dir) / f"portfolio_{market.lower()}.json"
    if not portfolio_file.exists():
        print(f"⚠️  持仓文件不存在: {portfolio_file}")
        return None
    with open(portfolio_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_stock_pick_result(market: str, data_dir: str = "data") -> list:
    """加载最新选股结果"""
    import glob
    pattern = str(Path(data_dir) / f"stock_pick_{market.lower()}_*.json")
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        print(f"⚠️  未找到 {market} 选股结果")
        return []
    with open(files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("selected_stocks", data) if isinstance(data, dict) else data


def check_portfolio(market: str, portfolio: dict) -> dict:
    """对持仓进行全方位风险检查"""
    print(f"\n{'='*60}")
    print(f"🛡️  {market.upper()} 持仓风险检查")
    print(f"{'='*60}\n")
    
    holdings = portfolio.get("holdings", portfolio.get("positions", []))
    total_value = portfolio.get("total_value", 0)
    cash = portfolio.get("cash", 0)
    
    # 1. 组合级风控检查 (PortfolioRiskChecker)
    print("📊 组合风险评分...")
    checker = PortfolioRiskChecker()
    
    # 标准化 positions: 计算 weight
    positions = []
    for h in holdings:
        symbol = h.get("symbol", h.get("code", ""))
        market_value = h.get("market_value", 0)
        weight = h.get("weight", market_value / total_value) if total_value > 0 else 0
        positions.append({
            "symbol": symbol,
            "weight": weight,
            "market_value": market_value,
            "name": h.get("name", ""),
            "quantity": h.get("quantity", 0)
        })
    
    report = checker.check_all(positions, total_value, cash)
    print(f"   总风险评分: {report.risk_score:.2f}/1.0")
    print(f"   通过: {'✅' if report.approved else '🚫'}")
    print(f"   发现: {len(report.findings)} 条")
    for f in report.findings[:10]:
        print(f"   - [{f.severity}] {f.rule_id}: {f.message}")
    if report.conditions:
        print(f"   条件: {', '.join(report.conditions[:5])}")
    
    # 2. 行业集中度分析
    print("\n🏭 行业集中度分析...")
    by_industry = {}
    for p in positions:
        symbol = p.get("symbol", "")
        weight = p.get("weight", 0)
        industry = classify_industry(symbol)
        if industry not in by_industry:
            by_industry[industry] = {"weight": 0, "count": 0, "symbols": []}
        by_industry[industry]["weight"] += weight
        by_industry[industry]["count"] += 1
        by_industry[industry]["symbols"].append(symbol)
    
    for industry, info in sorted(by_industry.items(), key=lambda x: -x[1]["weight"]):
        weight = info["weight"]
        count = info["count"]
        bar = "█" * int(weight * 50)
        print(f"   {industry}: {weight*100:.1f}% ({count}只) {bar}")
    
    # 3. 现金比例
    print(f"\n💰 现金比例: ${cash:,.0f} / ${total_value:,.0f} = {cash/total_value*100:.1f}%" if total_value > 0 else "   无总价值数据")
    
    # 4. 行业映射覆盖率
    print("\n🗺️  行业映射覆盖率...")
    classified = 0
    unclassified = []
    for p in positions:
        symbol = p.get("symbol", "")
        if classify_industry(symbol) != "Other":
            classified += 1
        else:
            unclassified.append(symbol)
    
    coverage = classified / len(holdings) * 100 if holdings else 0
    print(f"   已分类: {classified}/{len(holdings)} = {coverage:.1f}%")
    if unclassified:
        print(f"   未分类: {', '.join(unclassified[:10])}{'...' if len(unclassified) > 10 else ''}")
    
    return {
        "market": market,
        "timestamp": datetime.now().isoformat(),
        "risk_score": report.risk_score,
        "approved": report.approved,
        "findings_count": len(report.findings),
        "findings": [
            {"rule_id": f.rule_id, "severity": f.severity, "message": f.message, "suggestion": f.suggestion}
            for f in report.findings
        ],
        "conditions": report.conditions,
        "by_industry": by_industry,
        "industry_coverage": {
            "total": len(holdings),
            "classified": classified,
            "coverage_pct": round(coverage, 1),
            "unclassified": unclassified[:20]
        }
    }


def main():
    parser = argparse.ArgumentParser(description="组合级风险检查")
    parser.add_argument("--market", choices=["us", "hk", "cn"], default="us", help="市场")
    parser.add_argument("--symbols", help="逗号分隔的股票代码 (可选)")
    parser.add_argument("--data-dir", default="data", help="数据目录")
    parser.add_argument("--output", help="输出报告文件路径")
    args = parser.parse_args()
    
    print(f"🔍 组合级风险检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载持仓
    portfolio = load_portfolio(args.market, args.data_dir)
    if not portfolio:
        print("尝试加载选股结果作为模拟持仓...")
        stocks = load_stock_pick_result(args.market, args.data_dir)
        if not stocks:
            print("❌ 无持仓数据也无选股结果")
            sys.exit(1)
        # 模拟等权持仓
        total_value = 100000
        weight = 1.0 / len(stocks)
        portfolio = {
            "total_value": total_value,
            "cash": 0,
            "holdings": [
                {"symbol": s.get("symbol", s) if isinstance(s, dict) else s, "weight": weight}
                for s in stocks
            ]
        }
        print(f"   模拟等权持仓: {len(stocks)} 只, 每只 {weight*100:.1f}%")
    
    # 执行检查
    report = check_portfolio(args.market, portfolio)
    
    # 保存报告
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(args.data_dir) / f"risk_check_{args.market}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n📄 报告已保存: {output_path}")
    
    # 总结
    print(f"\n{'='*60}")
    print("📋 检查总结")
    print(f"{'='*60}")
    print(f"市场: {report['market'].upper()}")
    print(f"风险评分: {report['risk_score']:.3f}/1.0")
    print(f"通过: {'✅' if report['approved'] else '🚫'}")
    print(f"发现数: {report['findings_count']}")
    print(f"行业覆盖率: {report['industry_coverage']['coverage_pct']}%")
    
    findings = report.get('findings', [])
    critical = [f for f in findings if f['severity'] == 'critical']
    if critical:
        print(f"🔴 Critical: {len(critical)} 条")
        for f in critical[:5]:
            print(f"   - {f['rule_id']}: {f['message']}")


if __name__ == "__main__":
    main()
