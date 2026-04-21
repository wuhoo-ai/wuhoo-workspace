#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow D — 持仓诊断与调仓建议

流程:
1. 扫描 OpenD 持仓 (futu-api get_portfolio)
2. 逐只股票重新评估 (调用 Workflow B)
3. 组合级风险分析 (risk_manager + portfolio_metrics)
4. 生成调仓建议 (hold/add/reduce/clear)
5. 输出 openD 调仓信号
6. 保存为行动指南 (供下次定时任务使用)

用法:
    python workflow_d_trade_diagnose.py
    python workflow_d_trade_diagnose.py --market HK
    python workflow_d_trade_diagnose.py --market CN --account-id 18767295
    python workflow_d_trade_diagnose.py --skip-re-eval
    python workflow_d_trade_diagnose.py --top-n 5 --json
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Python 版本检查
if sys.version_info < (3, 9):
    print(f"❌ Python {sys.version.split()[0]} 不支持，需要 Python 3.9+")
    print(f"   请使用: python3.11 {__file__}")
    sys.exit(1)

# ============================================================
# 环境变量加载
# ============================================================
env_file = Path.home() / '.openclaw' / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value

# ============================================================
# 路径设置
# ============================================================
TRADE_DIR = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'trade'
SKILL_DIR = Path(__file__).parent
FUTU_API_SCRIPTS = Path.home() / '.openclaw' / 'skills' / 'futu-api' / 'scripts'
sys.path.insert(0, str(TRADE_DIR))

# ============================================================
# 市场-账户映射 (与 workflow_c_multi_market.py 保持一致)
# ============================================================
MARKET_ACCOUNTS = {
    'CN': 18767295,
    'HK': 18767294,
    'US': 18767299,
}

# ============================================================
# 调仓信号常量
# ============================================================
SIGNAL_HOLD   = "HOLD"
SIGNAL_ADD    = "ADD"
SIGNAL_REDUCE = "REDUCE"
SIGNAL_CLEAR  = "CLEAR"
SIGNAL_SKIP   = "SKIP"  # 数据不足，跳过

ALL_SIGNALS = [SIGNAL_HOLD, SIGNAL_ADD, SIGNAL_REDUCE, SIGNAL_CLEAR, SIGNAL_SKIP]


def _normalize_code_for_workflow_b(code: str) -> Tuple[str, str]:
    """
    将 Futu 代码格式转换为 Workflow B 接受的格式。

    Futu 返回: SH.600519, SZ.000001, HK.00700, US.AAPL
    Workflow B 期望: 600519, 000001, 00700, US.AAPL

    同时返回市场类型标识，用于后续逻辑判断。

    Args:
        code: Futu 格式股票代码

    Returns:
        (normalized_code, market_type)
        market_type: 'A', 'HK', 'US'
    """
    if not code:
        return code, 'A'

    if code.startswith('SH.') or code.startswith('SZ.'):
        return code.split('.', 1)[1], 'A'
    elif code.startswith('HK.'):
        return code.split('.', 1)[1], 'HK'
    elif code.startswith('US.'):
        return code, 'US'
    else:
        # 已经是裸代码，尝试推断
        if code.startswith(('600', '601', '603', '605', '688', '000', '002', '300')):
            return code, 'A'
        return code, 'A'


class WorkflowDHandler:
    """Workflow D: 持仓诊断与调仓建议"""

    def __init__(
        self,
        market: str = "all",
        account_id: Optional[int] = None,
        date: Optional[str] = None,
        skip_re_eval: bool = False,
        top_n: Optional[int] = None,
    ):
        self.market = market.upper()
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.skip_re_eval = skip_re_eval
        self.top_n = top_n
        self.account_id = account_id

        # 输出目录
        self.output_dir = TRADE_DIR / "data" / "workflow_d" / self.date
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 结果容器
        self.portfolio_scan: Dict = {}
        self.stock_diagnoses: Dict = {}
        self.portfolio_risk: Dict = {}
        self.rebalancing_suggestions: Dict = {}
        self.rebalancing_signals: Dict = {}

        print("=" * 60)
        print(f"Workflow D — 持仓诊断与调仓建议")
        print(f"市场: {self.market}  日期: {self.date}")
        print(f"跳过重评估: {self.skip_re_eval}")
        print("=" * 60)

    # ============================================================
    # Step 1: 扫描 OpenD 持仓
    # ============================================================
    def step1_scan_portfolio(self) -> Dict:
        """调用 futu-api get_portfolio.py 获取持仓"""
        print(f"\n[Step 1] 扫描 OpenD 持仓...")

        positions = []
        funds_by_market = {}

        markets_to_scan = self._resolve_markets()

        for mkt in markets_to_scan:
            acc_id = self.account_id or MARKET_ACCOUNTS.get(mkt)
            if acc_id is None:
                print(f"  ⚠️  市场 {mkt}: 无可用账户 ID，跳过")
                continue

            print(f"  → 查询市场 {mkt} (账户 {acc_id})...")
            result = self._call_futu_get_portfolio(
                market=mkt, acc_id=acc_id
            )
            if result and result.get("positions") is not None:
                for pos in result["positions"]:
                    pos["_market"] = mkt
                    pos["_account_id"] = acc_id
                positions.extend(result["positions"])
                if result.get("funds"):
                    funds_by_market[mkt] = result["funds"]
                print(f"    ✅ {len(result['positions'])} 只持仓")
            elif result and result.get("error"):
                print(f"    ❌ 查询失败: {result['error']}")
            else:
                print(f"    ⚠️  无返回数据 (可能无持仓或 OpenD 未运行)")

        # 按市值降序
        positions.sort(key=lambda p: p.get("market_val", 0), reverse=True)

        # 限制数量
        if self.top_n and self.top_n > 0:
            positions = positions[:self.top_n]

        total_market_value = sum(p.get("market_val", 0) for p in positions)
        total_assets = sum(f.get("total_assets", 0) for f in funds_by_market.values())
        cash_by_market = {m: f.get("cash", 0) for m, f in funds_by_market.items()}

        self.portfolio_scan = {
            "scan_time": datetime.now().isoformat(),
            "market_filter": self.market,
            "markets_scanned": markets_to_scan,
            "total_positions": len(positions),
            "total_market_value": round(total_market_value, 2),
            "total_assets": round(total_assets, 2),
            "cash_by_market": cash_by_market,
            "positions": positions,
        }

        self._save("01_portfolio_scan.json", self.portfolio_scan)
        print(f"  ✅ 汇总: {len(positions)} 只持仓, "
              f"市值 {total_market_value:,.2f}, "
              f"总资产 {total_assets:,.2f}")

        return self.portfolio_scan

    # ============================================================
    # Step 2: 逐只股票重新评估 (Workflow B)
    # ============================================================
    def step2_re_evaluate_stocks(self) -> Dict:
        """对每只持仓调用 Workflow B 进行深度分析"""
        if self.skip_re_eval:
            print(f"\n[Step 2] 跳过 Workflow B 重评估 (--skip-re-eval)")
            self.stock_diagnoses = {
                "skipped": True,
                "reason": "--skip-re-eval 快速模式",
                "note": "仅做持仓扫描和基础风控，未进行逐股深度分析",
            }
            return self.stock_diagnoses

        print(f"\n[Step 2] 逐只股票重新评估 (Workflow B)...")

        positions = self.portfolio_scan.get("positions", [])
        if not positions:
            self.stock_diagnoses = {
                "skipped": True,
                "reason": "无持仓股票",
                "diagnoses": {},
            }
            return self.stock_diagnoses

        diagnoses = {}

        for i, pos in enumerate(positions):
            code = pos.get("code", "")
            name = pos.get("name", "")
            if not code:
                continue

            norm_code, mkt_type = _normalize_code_for_workflow_b(code)
            print(f"  [{i+1}/{len(positions)}] 分析 {code} {name} (→ {norm_code})...")

            try:
                diag_result = self._run_workflow_b(norm_code, name, mkt_type)
                diagnoses[code] = {
                    "name": name,
                    "market": pos.get("_market", ""),
                    "market_val": pos.get("market_val", 0),
                    "pl_ratio": pos.get("pl_ratio_avg_cost", 0),
                    "normalized_code": norm_code,
                    "workflow_b_result": diag_result,
                    "status": "success",
                }
                print(f"    ✅ 分析完成")
            except Exception as e:
                diagnoses[code] = {
                    "name": name,
                    "market": pos.get("_market", ""),
                    "normalized_code": norm_code,
                    "status": "error",
                    "error": str(e),
                }
                print(f"    ❌ 分析失败: {e}")

        success_count = sum(1 for d in diagnoses.values() if d["status"] == "success")
        error_count = sum(1 for d in diagnoses.values() if d["status"] == "error")

        self.stock_diagnoses = {
            "eval_time": datetime.now().isoformat(),
            "total_evaluated": success_count,
            "total_errors": error_count,
            "diagnoses": diagnoses,
        }

        self._save("02_stock_diagnoses.json", self.stock_diagnoses)
        print(f"  ✅ 重评估完成: {success_count} 成功, {error_count} 失败")

        return self.stock_diagnoses

    # ============================================================
    # Step 3: 组合级风险分析
    # ============================================================
    def step3_portfolio_risk_analysis(self) -> Dict:
        """组合级风险指标计算"""
        print(f"\n[Step 3] 组合级风险分析...")

        from portfolio_metrics import (
            calculate_sharpe_ratio,
            calculate_hhi,
            calculate_concentration,
            calculate_max_drawdown_estimate,
            calculate_sector_concentration,
            calculate_pl_distribution,
        )
        from risk_manager import RiskManager, RISK_CONFIG

        positions = self.portfolio_scan.get("positions", [])
        total_assets = self.portfolio_scan.get("total_assets", 0)
        total_market_value = self.portfolio_scan.get("total_market_value", 0)

        # 基础组合指标
        weights = []
        pl_ratios = []
        for pos in positions:
            mv = pos.get("market_val", 0)
            if total_assets > 0:
                weights.append(mv / total_assets)
            pl_ratios.append(pos.get("pl_ratio_avg_cost", 0) / 100.0)

        sharpe = calculate_sharpe_ratio(pl_ratios, weights)
        hhi = calculate_hhi(weights)
        concentration = calculate_concentration(weights)
        max_drawdown = calculate_max_drawdown_estimate(positions)
        sector_conc = calculate_sector_concentration(positions)
        pl_dist = calculate_pl_distribution(positions)

        # 逐股风控检查
        risk_mgr = RiskManager()
        # 注入 OpenD 实时持仓数据，替代本地文件读取
        risk_mgr.set_opend_data(self.portfolio_scan)
        risk_checks = {}
        for pos in positions:
            code = pos.get("code", "")
            mv = pos.get("market_val", 0)
            ratio = mv / total_assets if total_assets > 0 else 0
            check = risk_mgr.check({
                "code": code,
                "action": "HOLD",
                "price": pos.get("nominal_price", 0),
                "quantity": pos.get("qty", 0),
                "position_ratio": ratio,
            })
            risk_checks[code] = check.to_dict()

        # 现金比率
        cash_total = sum(self.portfolio_scan.get("cash_by_market", {}).values())
        cash_ratio = cash_total / total_assets if total_assets > 0 else 0

        # 收集违规
        violations = []
        for code, checks in risk_checks.items():
            for check_name, detail in checks.get("checks", {}).items():
                if not detail.get("passed", True):
                    violations.append({
                        "code": code,
                        "check": check_name,
                        "detail": detail,
                    })

        self.portfolio_risk = {
            "analysis_time": datetime.now().isoformat(),
            "metrics": {
                "sharpe_ratio": round(sharpe, 3),
                "hhi": round(hhi, 4),
                "max_single_weight": round(max(weights), 4) if weights else 0.0,
                "top3_concentration": concentration["top3"],
                "top5_concentration": concentration["top5"],
                "top10_concentration": concentration["top10"],
                "max_drawdown_estimate": max_drawdown,
                "cash_ratio": round(cash_ratio, 4),
                "cash_total": round(cash_total, 2),
                "total_assets": round(total_assets, 2),
                "total_market_value": round(total_market_value, 2),
            },
            "sector_concentration": sector_conc,
            "pl_distribution": pl_dist,
            "risk_checks": risk_checks,
            "risk_config": RISK_CONFIG,
            "violations": violations,
        }

        self._save("03_portfolio_risk.json", self.portfolio_risk)

        violation_count = len(violations)
        print(f"  ✅ 风险分析完成: Sharpe={sharpe:.3f}, "
              f"HHI={hhi:.4f}, 违规={violation_count}")

        return self.portfolio_risk

    # ============================================================
    # Step 4: 生成调仓建议
    # ============================================================
    def step4_generate_rebalancing_suggestions(self) -> Dict:
        """为每只持仓生成 HOLD/ADD/REDUCE/CLEAR 建议"""
        print(f"\n[Step 4] 生成调仓建议...")

        positions = self.portfolio_scan.get("positions", [])
        diagnoses = self.stock_diagnoses.get("diagnoses", {})
        violation_codes = {v["code"] for v in self.portfolio_risk.get("violations", [])}

        total_assets = self.portfolio_scan.get("total_assets", 1)

        suggestions = {}
        for pos in positions:
            code = pos.get("code", "")
            name = pos.get("name", "")
            pl_ratio = pos.get("pl_ratio_avg_cost", 0)
            market_val = pos.get("market_val", 0)
            weight = market_val / total_assets if total_assets > 0 else 0

            diag = diagnoses.get(code, {})
            diag_status = diag.get("status", "error")
            wb_signal = self._extract_workflow_b_decision(diag)
            has_violation = code in violation_codes
            data_quality = self._extract_workflow_b_data_quality(diag)

            signal, reason = self._determine_signal(
                code=code,
                pl_ratio=pl_ratio,
                weight=weight,
                diag_status=diag_status,
                wb_signal=wb_signal,
                has_violation=has_violation,
                data_quality=data_quality,
            )

            suggestions[code] = {
                "name": name,
                "market": pos.get("_market", ""),
                "current_weight": round(weight, 4),
                "market_val": round(market_val, 2),
                "pl_ratio": pl_ratio,
                "signal": signal,
                "reason": reason,
                "workflow_b_decision": wb_signal,
                "has_risk_violation": has_violation,
            }

        # 汇总统计
        signal_counts = {}
        for s in suggestions.values():
            sig = s["signal"]
            signal_counts[sig] = signal_counts.get(sig, 0) + 1

        self.rebalancing_suggestions = {
            "generated_at": datetime.now().isoformat(),
            "signal_counts": signal_counts,
            "suggestions": suggestions,
        }

        self._save("04_rebalancing_suggestions.json", self.rebalancing_suggestions)

        print(f"  ✅ 调仓建议完成: {signal_counts}")
        return self.rebalancing_suggestions

    # ============================================================
    # Step 5: 生成 openD 调仓信号
    # ============================================================
    def step5_generate_signals(self) -> Dict:
        """生成机器可读的 openD 调仓信号"""
        print(f"\n[Step 5] 生成 openD 调仓信号...")

        suggestions = self.rebalancing_suggestions.get("suggestions", {})
        signals_list = []

        for code, sug in suggestions.items():
            sig = sug["signal"]
            if sig in (SIGNAL_REDUCE, SIGNAL_CLEAR):
                signals_list.append({
                    "code": code,
                    "name": sug["name"],
                    "action": "SELL" if sig == SIGNAL_CLEAR else "REDUCE",
                    "current_weight": sug["current_weight"],
                    "target_weight": self._calculate_target_weight(sig, sug["current_weight"]),
                    "reason": sug["reason"],
                    "priority": "HIGH" if sig == SIGNAL_CLEAR else "MEDIUM",
                })
            elif sig == SIGNAL_ADD:
                signals_list.append({
                    "code": code,
                    "name": sug["name"],
                    "action": "BUY",
                    "current_weight": sug["current_weight"],
                    "target_weight": self._calculate_target_weight(sig, sug["current_weight"]),
                    "reason": sug["reason"],
                    "priority": "LOW",
                })

        self.rebalancing_signals = {
            "signals": signals_list,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "market": self.market,
                "date": self.date,
                "total_signals": len(signals_list),
                "high_priority": sum(1 for s in signals_list if s["priority"] == "HIGH"),
                "medium_priority": sum(1 for s in signals_list if s["priority"] == "MEDIUM"),
                "low_priority": sum(1 for s in signals_list if s["priority"] == "LOW"),
            },
        }

        self._save("05_rebalancing_signals.json", self.rebalancing_signals)
        print(f"  ✅ 信号生成完成: {len(signals_list)} 条信号")
        return self.rebalancing_signals

    # ============================================================
    # Step 6: 保存行动指南
    # ============================================================
    def step6_save_action_guide(self) -> str:
        """保存为下次定时任务的行动指南"""
        print(f"\n[Step 6] 保存行动指南...")

        action_guide = {
            "workflow": "D",
            "date": self.date,
            "market": self.market,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_positions": self.portfolio_scan.get("total_positions", 0),
                "total_assets": self.portfolio_scan.get("total_assets", 0),
                "sharpe_ratio": self.portfolio_risk.get("metrics", {}).get("sharpe_ratio"),
                "signal_counts": self.rebalancing_suggestions.get("signal_counts", {}),
            },
            "actions": self.rebalancing_signals.get("signals", []),
            "violations": self.portfolio_risk.get("violations", []),
            "next_steps": self._generate_next_steps(),
        }

        guide_path = self.output_dir / "action_guide.json"
        with open(guide_path, 'w', encoding='utf-8') as f:
            json.dump(action_guide, f, ensure_ascii=False, indent=2)

        print(f"  ✅ 行动指南已保存: {guide_path}")
        return str(guide_path)

    # ============================================================
    # Markdown 报告生成
    # ============================================================
    def generate_markdown_report(self) -> str:
        """生成人类可读的 Markdown 诊断报告"""
        print(f"\n生成 Markdown 报告...")

        ps = self.portfolio_scan
        metrics = self.portfolio_risk.get("metrics", {})
        violations = self.portfolio_risk.get("violations", [])
        suggestions = self.rebalancing_suggestions.get("suggestions", {})
        signal_counts = self.rebalancing_suggestions.get("signal_counts", {})

        lines = [
            "# 🩺 Workflow D — 持仓诊断报告",
            "",
            f"**日期**: {self.date}  |  **市场**: {self.market}",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 一、组合概览",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 持仓数量 | {ps.get('total_positions', 0)} |",
            f"| 持仓市值 | {ps.get('total_market_value', 0):,.2f} |",
            f"| 总资产 | {ps.get('total_assets', 0):,.2f} |",
        ]

        for mkt, cash in ps.get("cash_by_market", {}).items():
            lines.append(f"| {mkt} 现金 | {cash:,.2f} |")
        lines.append("")

        lines.extend([
            "## 二、组合风险指标",
            "",
            "| 指标 | 数值 | 说明 |",
            "|------|------|------|",
            f"| Sharpe Ratio | {metrics.get('sharpe_ratio', 'N/A')} | 风险调整后收益 |",
            f"| HHI 集中度 | {metrics.get('hhi', 'N/A')} | 越低越分散 |",
            f"| 最大单股权重 | {metrics.get('max_single_weight', 0)*100:.1f}% | 限制 20% |",
            f"| Top-3 集中度 | {metrics.get('top3_concentration', 0)*100:.1f}% | |",
            f"| Top-5 集中度 | {metrics.get('top5_concentration', 0)*100:.1f}% | |",
            f"| 估算最大回撤 | {metrics.get('max_drawdown_estimate', 0)*100:.1f}% | |",
            f"| 现金比率 | {metrics.get('cash_ratio', 0)*100:.1f}% | 最低 10% |",
            "",
        ])

        # 风控违规
        if violations:
            lines.append(f"### ⚠️ 风控违规 ({len(violations)} 项)")
            lines.append("")
            for v in violations:
                lines.append(
                    f"- **{v['code']}**: {v.get('check', '')} — "
                    f"{v.get('detail', {}).get('message', '')}"
                )
            lines.append("")
        else:
            lines.append("### ✅ 无风控违规")
            lines.append("")

        # 逐股诊断
        lines.extend([
            "## 三、逐股诊断",
            "",
            "| 代码 | 名称 | 市值 | 盈亏% | 信号 | 原因 |",
            "|------|------|------|-------|------|------|",
        ])

        for code, sug in suggestions.items():
            signal_emoji = {
                "HOLD": "🔵", "ADD": "🟢",
                "REDUCE": "🟡", "CLEAR": "🔴",
            }.get(sug["signal"], "⚪")
            reason_short = sug["reason"][:50] if len(sug["reason"]) > 50 else sug["reason"]
            lines.append(
                f"| {code} | {sug['name']} | "
                f"{sug['market_val']:,.0f} | "
                f"{sug['pl_ratio']:.1f}% | "
                f"{signal_emoji} {sug['signal']} | "
                f"{reason_short} |"
            )
        lines.append("")

        # 调仓信号汇总
        lines.extend([
            "## 四、调仓信号汇总",
            "",
            "| 信号 | 数量 | 说明 |",
            "|------|------|------|",
            f"| HOLD | {signal_counts.get('HOLD', 0)} | 维持现状 |",
            f"| ADD | {signal_counts.get('ADD', 0)} | 建议加仓 |",
            f"| REDUCE | {signal_counts.get('REDUCE', 0)} | 建议减仓 |",
            f"| CLEAR | {signal_counts.get('CLEAR', 0)} | 建议清仓 |",
            "",
            "---",
            "",
            f"*报告由 Workflow D 自动生成 | 输出目录: `{self.output_dir}`*",
        ])

        report_text = "\n".join(lines)
        report_path = self.output_dir / "workflow_d_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(f"  ✅ 报告已保存: {report_path}")
        return report_text

    # ============================================================
    # 内部辅助方法
    # ============================================================

    def _resolve_markets(self) -> List[str]:
        """解析市场参数"""
        if self.market == "ALL":
            return ["CN", "HK", "US"]
        return [self.market] if self.market in MARKET_ACCOUNTS else ["HK"]

    def _call_futu_get_portfolio(self, market: str, acc_id: int) -> Optional[Dict]:
        """调用 futu-api get_portfolio.py 获取持仓

        注意：futu 库的日志也输出到 stdout，需要从混合输出中提取 JSON 部分。
        使用花括号计数定位完整的 JSON 边界。
        """
        script = FUTU_API_SCRIPTS / "trade" / "get_portfolio.py"
        cmd = [
            sys.executable, str(script),
            "--market", market,
            "--acc-id", str(acc_id),
            "--json",
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                # futu 库的日志也输出到 stdout，需要提取 JSON 部分
                stdout = result.stdout.strip()
                start = stdout.find('{')
                if start < 0:
                    return {"error": "输出中无 JSON", "positions": [], "funds": {}}
                # 花括号计数定位完整 JSON
                depth = 0
                end = -1
                for i in range(start, len(stdout)):
                    if stdout[i] == '{':
                        depth += 1
                    elif stdout[i] == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end > start:
                    return json.loads(stdout[start:end])
                return {"error": "无法定位完整 JSON", "positions": [], "funds": {}}
            else:
                error_msg = result.stderr.strip() or result.stdout.strip() or "无输出"
                return {"error": error_msg, "positions": [], "funds": {}}
        except subprocess.TimeoutExpired:
            return {"error": "请求超时 (30s)", "positions": [], "funds": {}}
        except Exception as e:
            return {"error": str(e), "positions": [], "funds": {}}

    def _run_workflow_b(self, code: str, name: str, market_type: str) -> Dict:
        """
        调用 Workflow B 进行单股深度分析

        通过直接导入方式调用，避免 subprocess 开销。
        """
        sys.path.insert(0, str(SKILL_DIR.parent / 'wuhoo-stock-deep-analysis'))
        from deep_analysis import WorkflowBDeepHandler

        handler = WorkflowBDeepHandler(code=code, name=name)
        handler.run()

        # 读取合并数据
        all_data_path = handler.output_dir / "all_data.json"
        result = {
            "output_dir": str(handler.output_dir),
        }

        if all_data_path.exists():
            with open(all_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                result["all_data"] = data
                result["decision"] = data.get("decision", "UNKNOWN")
                result["audit_score"] = data.get("audit_score", 0)
        else:
            result["decision"] = "UNKNOWN"
            result["audit_score"] = 0
            result["note"] = "all_data.json 未生成"

        return result

    def _extract_workflow_b_decision(self, diag: Dict) -> str:
        """从 Workflow B 结果中提取决策信号"""
        if diag.get("status") != "success":
            return "UNKNOWN"
        wb = diag.get("workflow_b_result", {})
        return wb.get("decision", "UNKNOWN")

    def _extract_workflow_b_data_quality(self, diag: Dict) -> str:
        """从 Workflow B 结果中提取数据质量标识"""
        if diag.get("status") != "success":
            return "unknown"
        wb = diag.get("workflow_b_result", {})
        all_data = wb.get("all_data", {})
        dq = all_data.get("data_quality", {})
        return dq.get("overall", "unknown")

    def _determine_signal(
        self,
        code: str,
        pl_ratio: float,
        weight: float,
        diag_status: str,
        wb_signal: str,
        has_violation: bool,
        data_quality: str = "good",
    ) -> Tuple[str, str]:
        """
        决定调仓信号: (signal, reason)

        优先级: 数据质量 > 风控违规 > Workflow B 强烈信号 > 止损 > 正常评估
        """
        # 0. 数据质量检查优先 — 降级数据不可用于交易决策
        if data_quality == "degraded":
            return (SIGNAL_SKIP, "基本面数据降级（AkShare 超时/Tushare 无数据），无法可靠评估，建议跳过")

        # 1. 风控违规优先
        if has_violation:
            return (SIGNAL_REDUCE, "触发风控限制，建议减仓")

        # 2. Workflow B 强烈卖出
        if wb_signal in ("强烈卖出", "SELL", "STRONG_SELL"):
            return (SIGNAL_CLEAR, f"Workflow B 建议清仓: {wb_signal}")

        # 3. 止损触发
        if pl_ratio < -15.0:
            return (SIGNAL_CLEAR, f"亏损 {pl_ratio:.1f}%，超过 15% 总止损线")

        # 4. Workflow B 卖出
        if wb_signal in ("卖出", "SELL"):
            return (SIGNAL_REDUCE, f"Workflow B 建议卖出")

        # 5. 亏损预警
        if pl_ratio < -8.0:
            return (SIGNAL_REDUCE, f"亏损 {pl_ratio:.1f}%，接近 8% 单笔止损")

        # 6. Workflow B 强烈买入 + 低仓位
        if wb_signal in ("强烈买入", "STRONG_BUY") and weight < 0.10:
            return (SIGNAL_ADD, f"Workflow B 强烈买入，当前仓位 {weight*100:.1f}% 偏低")

        # 7. Workflow B 买入 + 低仓位
        if wb_signal in ("买入", "BUY") and weight < 0.05:
            return (SIGNAL_ADD, f"Workflow B 建议买入，当前仓位 {weight*100:.1f}% 偏低")

        # 8. Workflow B 建议持有（分析成功但信号中性）
        if wb_signal == "持有" and diag_status == "success":
            return (SIGNAL_HOLD, f"Workflow B 评估中性，估值合理，维持现状")

        # 9. 分析失败
        if diag_status == "error":
            return (SIGNAL_HOLD, "深度分析失败，维持观察")

        # 10. 默认
        return (SIGNAL_HOLD, "估值合理，无重大风险，维持现状")

    def _calculate_target_weight(self, signal: str, current_weight: float) -> float:
        """根据信号计算目标权重"""
        targets = {
            SIGNAL_CLEAR: 0.0,
            SIGNAL_REDUCE: max(0.0, current_weight * 0.5),
            SIGNAL_ADD: min(current_weight * 1.5, 0.20),  # 不超过单股 20%
            SIGNAL_HOLD: current_weight,
        }
        return round(targets.get(signal, current_weight), 4)

    def _generate_next_steps(self) -> List[Dict]:
        """生成下一步行动建议"""
        steps = []
        signals = self.rebalancing_signals.get("signals", [])
        high_priority = [s for s in signals if s["priority"] == "HIGH"]
        medium_priority = [s for s in signals if s["priority"] == "MEDIUM"]

        if high_priority:
            steps.append({
                "action": "处理高优先级清仓信号",
                "count": len(high_priority),
                "signals": [{"code": s["code"], "name": s["name"]} for s in high_priority],
            })

        if medium_priority:
            steps.append({
                "action": "评估中优先级减仓信号",
                "count": len(medium_priority),
                "signals": [{"code": s["code"], "name": s["name"]} for s in medium_priority],
            })

        steps.append({
            "action": "下次诊断时间",
            "suggestion": "建议 7 天后再次运行 Workflow D",
        })

        return steps

    def _save(self, filename: str, data: Dict):
        """保存 JSON 文件"""
        path = self.output_dir / filename
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ============================================================
    # 主执行方法
    # ============================================================
    def run(self) -> Dict:
        """执行完整 Workflow D 流程"""
        self.step1_scan_portfolio()
        self.step2_re_evaluate_stocks()
        self.step3_portfolio_risk_analysis()
        self.step4_generate_rebalancing_suggestions()
        self.step5_generate_signals()
        self.step6_save_action_guide()
        self.generate_markdown_report()

        print(f"\n{'='*60}")
        print(f"Workflow D 完成")
        print(f"输出目录: {self.output_dir}")
        print(f"{'='*60}")

        return {
            "portfolio_scan": self.portfolio_scan,
            "stock_diagnoses": self.stock_diagnoses,
            "portfolio_risk": self.portfolio_risk,
            "rebalancing_suggestions": self.rebalancing_suggestions,
            "rebalancing_signals": self.rebalancing_signals,
            "output_dir": str(self.output_dir),
        }


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Workflow D — 持仓诊断与调仓建议",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全市场诊断
  python workflow_d_trade_diagnose.py

  # 仅港股，跳过深度分析
  python workflow_d_trade_diagnose.py --market HK --skip-re-eval

  # A股指定账户，仅诊断前 5 只持仓
  python workflow_d_trade_diagnose.py --market CN --account-id 18767295 --top-n 5

  # 仅输出 JSON
  python workflow_d_trade_diagnose.py --market US --skip-re-eval --json
        """,
    )
    parser.add_argument(
        "--market", type=str, default="all",
        choices=["CN", "HK", "US", "all"],
        help="市场 (默认: all)",
    )
    parser.add_argument(
        "--account-id", type=int, default=None,
        help="富途账户 ID (默认: 自动检测)",
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="诊断日期 YYYY-MM-DD (默认: 今天)",
    )
    parser.add_argument(
        "--skip-re-eval", action="store_true",
        help="跳过 Workflow B 重评估 (快速模式)",
    )
    parser.add_argument(
        "--top-n", type=int, default=None,
        help="最多诊断持仓数 (默认: 全部)",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_only",
        help="仅输出 JSON",
    )

    args = parser.parse_args()

    handler = WorkflowDHandler(
        market=args.market,
        account_id=args.account_id,
        date=args.date,
        skip_re_eval=args.skip_re_eval,
        top_n=args.top_n,
    )
    result = handler.run()

    if args.json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
