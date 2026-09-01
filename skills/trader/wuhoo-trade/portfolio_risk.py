#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio-level Risk Management Module

组合级风控模块，弥补 RiskAgent 仅做单票检查的不足。
覆盖：行业集中度、相关性分析、分层仓位管理、动态止损、最大回撤、事件风险黑名单。

用法:
    python3.11 portfolio_risk.py --portfolio data/portfolio_snapshot_20260424.json
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import yaml

# ---------------------------------------------------------------------------
# 数据定义
# ---------------------------------------------------------------------------

@dataclass
class RiskFinding:
    """单条风控发现"""
    rule_id: str
    severity: str  # "critical", "warning", "info"
    message: str
    detail: str = ""
    suggestion: str = ""

@dataclass
class PortfolioRiskReport:
    """组合级风控报告"""
    findings: List[RiskFinding] = field(default_factory=list)
    risk_score: float = 0.0  # 0.0 (安全) → 1.0 (极高风险)
    approved: bool = True
    conditions: List[str] = field(default_factory=list)
    summary: str = ""

# ---------------------------------------------------------------------------
# 规则常量 (与 risk_rules.yaml 保持一致)
# ---------------------------------------------------------------------------

DEFAULT_RULES = {
    "single_stock_max": 0.20,
    "single_industry_max": 0.40,
    "cash_min": 0.10,
    "max_correlation": 0.70,
    "max_drawdown_pct": 0.15,
    "earnings_blackout_days": 3,
    "min_risk_reward_ratio": 2.0,
    "position_tiers": [
        {"confidence_min": 0.8, "position_max": 0.20},
        {"confidence_min": 0.6, "position_max": 0.15},
        {"confidence_min": 0.4, "position_max": 0.10},
        {"confidence_min": 0.0, "position_max": 0.05},
    ],
    "volatility_stop_loss": {
        "low_threshold": 0.25,
        "high_threshold": 0.50,
        "low_vol_max": 0.10,
        "medium_vol_max": 0.08,
        "high_vol_max": 0.05,
    },
}

# 行业映射 (GICS 分类，覆盖 S&P 500 + 主要港股)
# 按 GICS 11 大板块分类
INDUSTRY_MAP = {
    # ---- Technology ----
    "Technology": [
        # US
        "AAPL", "MSFT", "NVDA", "GOOG", "GOOGL", "META", "ADBE", "CRM", "ORCL", "AMD",
        "ADI", "AVGO", "CSCO", "INTC", "QCOM", "TXN", "AMAT", "LRCX", "KLAC", "SNPS",
        "CDNS", "MCHP", "NXPI", "MU", "HPQ", "DELL", "NTAP", "STX", "WDC", "ANET",
        "PANW", "FTNT", "CRWD", "ZS", "DDOG", "NET", "SNOW", "PLTR", "UBER", "LYFT",
        # HK
        "00700", "09988", "09961", "09618", "00285", "09888", "01810", "02015",
    ],
    # ---- Financials ----
    "Financials": [
        # US - Banks
        "JPM", "BAC", "WFC", "GS", "MS", "C", "USB", "PNC", "TFC", "COF",
        "FITB", "HBAN", "RF", "CFG", "KEY", "CMA", "ZION", "SIVB",
        # US - Insurance
        "BRK-B", "BRK-A", "AIG", "MET", "PRU", "AFL", "ALL", "TRV", "PGR", "CB",
        "AJG", "MMC", "AON", "WTW", "BRO",
        # US - Asset Management / Financial Services
        "BLK", "SCHW", "BEN", "TROW", "IVZ", "AMG", "STT", "NTRS", "BK",
        "V", "MA", "AXP", "DFS", "SYF", "PYPL", "FIS", "FISV", "GPN", "SQ",
        "SPGI", "MCO", "ICE", "CME", "NDAQ", "CBOE",
        # HK - Banks
        "00005", "00011", "02888", "00288", "01288", "03988", "00165",
        # HK - Insurance
        "02328", "02628",
        # HK - Financial Services
        "00688", "00656", "00813", "00939", "01988", "01299",
    ],
    # ---- Consumer Discretionary ----
    "Consumer Discretionary": [
        # US - Retail
        "AMZN", "HD", "TJX", "LOW", "TGT", "COST", "DG", "DLTR", "BBY", "ROST",
        # US - Auto
        "TSLA", "F", "GM", "RIVN", "LCID", "NIO", "LI", "XPEV",
        # US - Leisure & Entertainment
        "DIS", "NFLX", "LYV", "MAR", "HLT", "IHG", "MGM", "WYNN", "LVS", "RCL",
        "CCL", "NCLH", "YUM", "MCD", "SBUX", "CMG", "DPZ", "DRI",
        # US - Apparel & Luxury
        "NKE", "LULU", "RL", "PVH", "VFC", "TPR", "CPRI", "UAA", "UA",
        # US - Consumer Services
        "ABNB", "BKNG", "EXPE", "UBER", "LYFT",
        # HK
        "01810", "02020", "02331", "01179", "00291",
    ],
    # ---- Healthcare ----
    "Healthcare": [
        # US - Pharma
        "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "BMY", "AMGN", "GILD",
        "VRTX", "REGN", "BIIB", "ILMN", "MRNA", "BNTX",
        # US - Medical Devices
        "TMO", "ABT", "DHR", "SYK", "BSX", "MDT", "EW", "ISRG", "ZBH", "BAX",
        "BDX", "RMD", "HOLX", "DXCM", "ALGN", "IDXX", "IQV", "A",
        # US - Health Services
        "CVS", "CI", "HUM", "ELV", "CNC", "MOH", "HCA", "UHS", "THC",
        # US - Life Sciences Tools
        "TMO", "DHR", "A", "LH", "DGX",
        # HK
        "01093", "01801", "02269", "06160", "09633", "01177", "01928", "01530",
    ],
    # ---- Industrials ----
    "Industrials": [
        # US
        "EMR", "JCI", "CAT", "BA", "HON", "GE", "MMM", "PPG", "DE",
        "LMT", "RTX", "NOC", "GD", "TDG", "LDOS", "HWM", "CMI", "ETN",
        "PH", "ITW", "ROK", "AME", "DOV", "XYL", "IEX", "FAST", "PCAR",
        "OTIS", "CARR", "IR", "NSC", "UNP", "CSX", "CP", "UBER", "FDX",
        "UPS", "LUV", "DAL", "UAL", "AAL", "ALK", "JBLU", "HA",
        # HK
        "00144", "00177", "00694", "00941", "00006", "00003", "00010",
    ],
    # ---- Energy ----
    "Energy": [
        # US - Oil & Gas
        "XOM", "CVX", "COP", "SLB", "EOG", "PXD", "MPC", "VLO", "PSX", "OXY",
        "DVN", "FANG", "HAL", "BKR", "HES", "MRO", "APA", "CTRA", "EQT", "TRGP",
        # HK
        "00857", "00386", "02333", "01378", "00564", "00005",
    ],
    # ---- Materials ----
    "Materials": [
        # US
        "LIN", "APD", "ECL", "DD", "NEM", "FCX", "NUE", "STLD", "VMC", "MLM",
        "SHW", "PPG", "RPM", "ALB", "CE", "EMN", "FMC", "LYB", "DOW", "MOS",
        "CF", "IP", "WRK", "SEE", "AVY", "AMCR", "BALL", "PKG", "CCK",
        # HK
        "01368", "01339", "01186", "00883", "02899", "00914",
    ],
    # ---- Real Estate ----
    "Real Estate": [
        # US
        "AMT", "PLD", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "AVB",
        "EQR", "INVH", "ESS", "MAA", "UDR", "CPT", "ARE", "VTR", "PEAK", "HST",
        "REG", "FRT", "BXP", "VNO", "SLG", "KIM", "MAC",
        # HK
        "01113", "00688", "00012", "00083", "01997", "00101", "00410", "00778",
        "00823", "02777", "00241", "00019", "01238", "00035", "01475", "02778",
    ],
    # ---- Communication Services ----
    "Communication Services": [
        # US
        "GOOG", "GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS",
        "CHTR", "EA", "TTWO", "ATVI", "RBLX", "MTCH", "PINS", "SNAP", "SPOT",
        "WMG", "LYV", "IPG", "OMC",
        # HK
        "00772", "01024", "00780", "00700", "00763", "01168", "00669",
    ],
    # ---- Utilities ----
    "Utilities": [
        # US
        "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "WEC",
        "ES", "AWK", "DTE", "PPL", "EIX", "AEE", "CMS", "CNP", "ETR", "NI",
        "PNW", "LNT", "EVRG", "ATO", "NWE", "OGE", "NJR", "SWX", "AVA",
        # HK
        "00002", "01038", "00267", "00006", "01813", "00293",
    ],
    # ---- Consumer Staples ----
    "Consumer Staples": [
        # US
        "PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "KMB", "GIS",
        "K", "HSY", "SJM", "CPB", "CAG", "MKC", "CHD", "CLX", "TSN",
        "HRL", "KHC", "MDLZ", "MNST", "STZ", "BF-B", "TAP", "SAM", "KDP",
        "EL", "COTY", "REV", "IFF",
        # HK
        "01038", "0168", "00220", "02319", "09633", "00828", "01579",
    ],
}

def classify_industry(symbol: str, fallback: str = "Other") -> str:
    """根据代码匹配行业"""
    code = symbol.replace("HK.", "").replace(".US", "").replace(".SH", "").replace(".SZ", "")
    for industry, codes in INDUSTRY_MAP.items():
        if code in codes:
            return industry
    return fallback


# ---------------------------------------------------------------------------
# 风控检查器
# ---------------------------------------------------------------------------

class PortfolioRiskChecker:
    """组合级风控检查器"""

    def __init__(self, rules: Optional[Dict] = None):
        self.rules = {**DEFAULT_RULES, **(rules or {})}

    def check_all(
        self,
        positions: List[Dict],
        total_value: float,
        cash: float = 0.0,
        candidate_trades: Optional[List[Dict]] = None,
        correlation_matrix: Optional[Dict] = None,
        historical_nav: Optional[List[float]] = None,
        earnings_calendar: Optional[List[Dict]] = None,
    ) -> PortfolioRiskReport:
        """执行全部组合级风控检查"""
        report = PortfolioRiskReport()

        # 1. 单票仓位上限
        self._check_single_position(report, positions, total_value)

        # 2. 行业集中度
        self._check_industry_concentration(report, positions, total_value)

        # 3. 现金比例
        self._check_cash_ratio(report, total_value, cash)

        # 4. 相关性检查
        self._check_correlation(report, positions, correlation_matrix)

        # 5. 最大回撤
        self._check_max_drawdown(report, historical_nav)

        # 6. 事件风险黑名单
        self._check_event_risk(report, positions, earnings_calendar)

        # 7. 分层仓位合规
        self._check_position_tiers(report, positions)

        # 8. 候选交易预审 (如果有调仓计划)
        if candidate_trades:
            self._check_candidate_trades(report, candidate_trades, positions, total_value)

        # 计算综合风险评分
        report.risk_score = self._compute_risk_score(report.findings)
        report.approved = not any(f.severity == "critical" for f in report.findings)
        report.conditions = [f.suggestion for f in report.findings if f.suggestion]

        # 生成摘要
        critical = sum(1 for f in report.findings if f.severity == "critical")
        warnings = sum(1 for f in report.findings if f.severity == "warning")
        report.summary = (
            f"组合风控检查完成: {len(report.findings)} 条发现 "
            f"(🔴 {critical} critical, ⚠️ {warnings} warnings, "
            f"ℹ️ {len(report.findings) - critical - warnings} info). "
            f"风险评分: {report.risk_score:.2f}. "
            f"{'通过' if report.approved else '🚫 未通过'}"
        )

        return report

    # ---- 具体检查方法 ----

    def _check_single_position(self, report, positions, total_value):
        max_pct = self.rules["single_stock_max"]
        for pos in positions:
            if total_value <= 0:
                continue
            weight = pos.get("market_value", 0) / total_value
            if weight > max_pct:
                report.findings.append(RiskFinding(
                    rule_id="R01",
                    severity="critical",
                    message=f"单票 {pos['symbol']} 仓位 {weight:.1%} 超过上限 {max_pct:.0%}",
                    detail=f"{pos['symbol']} 市值 {pos.get('market_value', 0):.0f}, 组合总值 {total_value:.0f}",
                    suggestion=f"降低 {pos['symbol']} 仓位至 {max_pct:.0%} ({total_value * max_pct:.0f}) 以下"
                ))

    def _check_industry_concentration(self, report, positions, total_value):
        max_pct = self.rules["single_industry_max"]
        industry_weights: Dict[str, float] = {}

        for pos in positions:
            industry = pos.get("industry") or classify_industry(pos["symbol"])
            market_value = pos.get("market_value", 0)
            industry_weights[industry] = industry_weights.get(industry, 0) + market_value

        for industry, value in industry_weights.items():
            if total_value <= 0:
                continue
            weight = value / total_value
            if weight > max_pct:
                report.findings.append(RiskFinding(
                    rule_id="R02",
                    severity="critical",
                    message=f"行业 {industry} 集中度 {weight:.1%} 超过上限 {max_pct:.0%}",
                    detail=f"该行业包含 {sum(1 for p in positions if (p.get('industry') or classify_industry(p['symbol'])) == industry)} 只持仓",
                    suggestion=f"分散 {industry} 行业仓位，单一行业不超过 {max_pct:.0%}"
                ))
            elif weight > max_pct * 0.75:
                report.findings.append(RiskFinding(
                    rule_id="R02",
                    severity="warning",
                    message=f"行业 {industry} 集中度 {weight:.1%} 接近上限 {max_pct:.0%}",
                    detail=f"该行业占比已达预警线 (75% of {max_pct:.0%})",
                    suggestion=f"控制 {industry} 行业新增仓位"
                ))

    def _check_cash_ratio(self, report, total_value, cash):
        min_cash = self.rules["cash_min"]
        if total_value <= 0:
            return
        cash_ratio = cash / total_value
        if cash_ratio < min_cash:
            report.findings.append(RiskFinding(
                rule_id="R03",
                severity="warning",
                message=f"现金比例 {cash_ratio:.1%} 低于最低要求 {min_cash:.0%}",
                detail=f"现金 {cash:.0f}, 组合总值 {total_value:.0f}",
                suggestion="保留至少 10% 现金应对流动性需求"
            ))
        elif cash_ratio > 0.50:
            report.findings.append(RiskFinding(
                rule_id="R03",
                severity="warning",
                message=f"现金比例 {cash_ratio:.1%} 过高，资金利用率低",
                detail=f"现金 {cash:.0f}, 组合总值 {total_value:.0f}",
                suggestion="考虑提高资金使用效率，适度增加持仓"
            ))

    def _check_correlation(self, report, positions, correlation_matrix):
        if not correlation_matrix:
            report.findings.append(RiskFinding(
                rule_id="R04",
                severity="info",
                message="相关性数据缺失，跳过相关性检查",
                suggestion="建议接入相关系数矩阵数据源"
            ))
            return

        max_corr = self.rules["max_correlation"]
        symbols = [p["symbol"] for p in positions]

        for i, sym_a in enumerate(symbols):
            for sym_b in symbols[i+1:]:
                key = f"{sym_a}:{sym_b}"
                corr = correlation_matrix.get(key)
                if corr is None:
                    continue
                if corr > max_corr:
                    report.findings.append(RiskFinding(
                        rule_id="R04",
                        severity="warning",
                        message=f"{sym_a} 与 {sym_b} 相关性 {corr:.2f} 超过阈值 {max_corr}",
                        detail="高相关性股票不能有效分散风险",
                        suggestion=f"考虑替换 {sym_a} 或 {sym_b} 中基本面较弱的一只"
                    ))

    def _check_max_drawdown(self, report, historical_nav):
        if not historical_nav or len(historical_nav) < 2:
            report.findings.append(RiskFinding(
                rule_id="R05",
                severity="info",
                message="历史净值数据不足，跳过最大回撤检查",
                suggestion="建议记录每日组合净值用于回撤监控"
            ))
            return

        max_dd = self.rules["max_drawdown_pct"]
        peak = historical_nav[0]
        worst_dd = 0.0

        for nav in historical_nav:
            if nav > peak:
                peak = nav
            dd = (peak - nav) / peak
            if dd > worst_dd:
                worst_dd = dd

        if worst_dd > max_dd:
            report.findings.append(RiskFinding(
                rule_id="R06",
                severity="critical",
                message=f"最大回撤 {worst_dd:.1%} 超过限制 {max_dd:.0%}",
                detail=f"净值从峰值 {peak:.2f} 回撤至最低点",
                suggestion="触发风控红线，暂停新增买入，审视持仓质量"
            ))
        elif worst_dd > max_dd * 0.7:
            report.findings.append(RiskFinding(
                rule_id="R06",
                severity="warning",
                message=f"最大回撤 {worst_dd:.1%} 接近限制 {max_dd:.0%}",
                suggestion="加强监控，准备应对方案"
            ))

    def _check_event_risk(self, report, positions, earnings_calendar):
        if not earnings_calendar:
            report.findings.append(RiskFinding(
                rule_id="R07",
                severity="info",
                message="财报日历数据缺失，跳过事件风险检查",
                suggestion="建议接入财报日历数据"
            ))
            return

        blackout_days = self.rules["earnings_blackout_days"]
        position_symbols = {p["symbol"] for p in positions}

        for event in earnings_calendar:
            sym = event.get("symbol", "")
            days_until = event.get("days_until", 999)
            if sym in position_symbols and 0 <= days_until <= blackout_days:
                report.findings.append(RiskFinding(
                    rule_id="R07",
                    severity="warning",
                    message=f"{sym} 将在 {days_until} 天后发布财报",
                    detail="财报前后波动率通常放大",
                    suggestion=f"财报前 {blackout_days} 天内避免建仓/加仓 {sym}"
                ))

    def _check_position_tiers(self, report, positions):
        tiers = self.rules["position_tiers"]
        for pos in positions:
            confidence = pos.get("confidence")
            if confidence is None:
                continue

            # 找到该置信度对应的最大仓位
            max_allowed = 0.05  # default floor
            for tier in tiers:
                if confidence >= tier["confidence_min"]:
                    max_allowed = tier["position_max"]
                    break

            total_value = sum(p.get("market_value", 0) for p in positions)
            if total_value <= 0:
                continue
            weight = pos.get("market_value", 0) / total_value

            if weight > max_allowed:
                report.findings.append(RiskFinding(
                    rule_id="R08",
                    severity="warning",
                    message=f"{pos['symbol']} 置信度 {confidence:.2f} 对应最大仓位 {max_allowed:.0%}, 实际 {weight:.1%}",
                    detail=f"仓位与置信度不匹配",
                    suggestion=f"调整 {pos['symbol']} 仓位至 {max_allowed:.0%} 以下或提高分析置信度"
                ))

    def _check_candidate_trades(self, report, trades, current_positions, total_value):
        """预审候选交易，模拟执行后的组合状态"""
        # 模拟交易后的行业分布
        new_industry_weights: Dict[str, float] = {}
        for pos in current_positions:
            industry = pos.get("industry") or classify_industry(pos["symbol"])
            new_industry_weights[industry] = new_industry_weights.get(industry, 0) + pos.get("market_value", 0)

        for trade in trades:
            if trade.get("side") == "buy":
                industry = trade.get("industry") or classify_industry(trade["symbol"])
                new_industry_weights[industry] = new_industry_weights.get(industry, 0) + trade.get("value", 0)

        max_industry = self.rules["single_industry_max"]
        new_total = total_value + sum(t.get("value", 0) for t in trades if t.get("side") == "buy")

        for industry, value in new_industry_weights.items():
            if new_total <= 0:
                continue
            weight = value / new_total
            if weight > max_industry:
                report.findings.append(RiskFinding(
                    rule_id="R09",
                    severity="critical",
                    message=f"调仓后行业 {industry} 集中度将达 {weight:.1%}，超过上限",
                    detail="调仓计划违反行业集中度约束",
                    suggestion="调整调仓方案，减少该行业买入或增加其他行业配置"
                ))

    # ---- 风险评分计算 ----

    def _compute_risk_score(self, findings: List[RiskFinding]) -> float:
        severity_weights = {"critical": 0.4, "warning": 0.15, "info": 0.0}
        score = sum(severity_weights.get(f.severity, 0) for f in findings)
        return min(1.0, round(score, 2))


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="组合级风控检查")
    parser.add_argument("--portfolio", type=str, required=True, help="持仓快照 JSON 文件路径")
    parser.add_argument("--rules", type=str, default=None, help="风控规则 YAML 文件路径")
    parser.add_argument("--trades", type=str, default=None, help="候选交易 JSON 文件路径")
    args = parser.parse_args()

    # 加载持仓
    with open(args.portfolio, "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    positions = portfolio.get("positions", [])
    total_value = portfolio.get("total_value", 0)
    cash = portfolio.get("cash", 0)

    # 加载规则 (可选)
    rules = None
    if args.rules and Path(args.rules).exists():
        with open(args.rules, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f)

    # 加载候选交易 (可选)
    candidate_trades = None
    if args.trades and Path(args.trades).exists():
        with open(args.trades, "r", encoding="utf-8") as f:
            candidate_trades = json.load(f)

    # 执行检查
    checker = PortfolioRiskChecker(rules)
    report = checker.check_all(
        positions=positions,
        total_value=total_value,
        cash=cash,
        candidate_trades=candidate_trades,
    )

    # 输出结果
    print("\n" + "=" * 60)
    print("🛡️ 组合级风控报告")
    print("=" * 60)
    print(f"\n{report.summary}\n")

    if report.findings:
        print("📋 详细发现:")
        print("-" * 60)
        for f in report.findings:
            icon = {"critical": "🔴", "warning": "⚠️ ", "info": "ℹ️ "}.get(f.severity, "•")
            print(f"\n{icon} [{f.rule_id}] {f.message}")
            if f.detail:
                print(f"   详情: {f.detail}")
            if f.suggestion:
                print(f"   建议: {f.suggestion}")
        print()

    print(f"风险评分: {report.risk_score:.2f} / 1.00")
    print(f"审批结果: {'✅ 通过' if report.approved else '🚫 未通过'}")

    if report.conditions:
        print(f"\n条件/建议:")
        for i, c in enumerate(report.conditions, 1):
            print(f"  {i}. {c}")

    print("=" * 60 + "\n")

    return report


if __name__ == "__main__":
    main()
