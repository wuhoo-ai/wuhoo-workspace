#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow C 审计模块

功能:
- 数据来源追踪 (DATA_PROVENANCE)
- Fallback 检测 (FALLBACK_DETECTION)
- 内容验证 (CONTENT_VALIDATION)
- 跨步骤一致性检查 (CONSISTENCY_CHECK)
- 可靠性评分 (RELIABILITY_SCORE)

输出:
- 05_audit_report.json (结构化审计数据)
- audit_report.md (可读审计报告)
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class AlertLevel(Enum):
    CRITICAL = "CRITICAL"   # 数据不可用，结果不可信
    WARNING = "WARNING"     # 部分降级，结果需谨慎
    INFO = "INFO"           # 信息性提示
    PASS = "PASS"           # 通过审计


@dataclass
class Alert:
    level: str          # AlertLevel value
    dimension: str      # 审计维度
    rule: str           # 触发的规则
    message: str        # 人类可读描述
    detail: str = ""    # 额外详情


@dataclass
class StepRecord:
    step_name: str
    timestamp: str
    data: Dict = field(default_factory=dict)
    alerts: List[Dict] = field(default_factory=list)


@dataclass
class StockAuditEntry:
    code: str
    name: str
    alerts: List[Dict] = field(default_factory=list)
    data_quality: Dict = field(default_factory=dict)
    source_summary: Dict = field(default_factory=dict)
    consistency: Dict = field(default_factory=dict)
    reliability: float = 100.0
    is_reliable: bool = True
    step_records: Dict = field(default_factory=dict)


# 扣分规则
DEDUCTIONS = {
    "technical_degraded": 20,
    "fundamental_degraded": 20,
    "sentiment_degraded": 15,
    "factor_degraded": 10,
    "bull_points_empty": 10,
    "bear_points_empty": 10,
    "multi_dim_debate_conflict": 15,
    "reason_empty": 5,
    "news_sources_empty": 10,
    "step_error": 25,
    "final_action_error": 15,
}


class WorkflowAudit:
    """Workflow C 审计追踪器"""

    def __init__(self, date: str, market: str, output_dir: Optional[Path] = None):
        self.date = date
        self.market = market
        self.output_dir = output_dir
        self.step_records: Dict[str, StepRecord] = {}
        self.stock_audits: Dict[str, StockAuditEntry] = {}
        self.global_alerts: List[Alert] = []
        self._started_at = datetime.now().isoformat()

    # ─────────────────── Step Recording ───────────────────

    def record_step(self, step_name: str, data: Dict):
        """记录一个步骤的执行结果"""
        record = StepRecord(
            step_name=step_name,
            timestamp=datetime.now().isoformat(),
            data=data,
        )
        self.step_records[step_name] = record

        # 根据步骤类型执行特定审计
        if step_name == "stock_pick":
            self._audit_stock_pick(data)
        elif step_name == "multi_dimensional":
            self._audit_multi_dimensional(data)
        elif step_name == "debate":
            self._audit_debate(data)
        elif step_name == "recommendations":
            self._audit_recommendations(data)
        elif step_name == "daily_review":
            self._audit_daily_review(data)

    # ─────────────────── Per-Stock Audit ───────────────────

    def audit_stock(self, code: str, name: str,
                    multi_dim: Optional[Dict] = None,
                    debate: Optional[Dict] = None,
                    recommendation: Optional[Dict] = None):
        """对单只股票执行完整审计"""
        entry = StockAuditEntry(code=code, name=name)
        score = 100.0

        # 1. Fallback 检测
        self._check_fallbacks(entry, multi_dim, debate)

        # 2. 内容验证
        self._check_content(entry, debate, recommendation)

        # 3. 一致性检查
        self._check_consistency(entry, multi_dim, debate, recommendation)

        # 4. 计算可靠性评分
        score = self._calculate_score(entry)
        entry.reliability = score
        entry.is_reliable = score >= 60

        self.stock_audits[code] = entry
        return entry

    # ─────────────────── Audit: Stock Pick ───────────────────

    def _audit_stock_pick(self, data: Dict):
        stocks = data if isinstance(data, list) else data.get("stocks", [])
        if not stocks:
            self.global_alerts.append(Alert(
                level=AlertLevel.CRITICAL.value,
                dimension="DATA_PROVENANCE",
                rule="no_stocks_selected",
                message="选股结果为空"
            ))
        else:
            self.global_alerts.append(Alert(
                level=AlertLevel.INFO.value,
                dimension="DATA_PROVENANCE",
                rule="stocks_loaded",
                message=f"成功加载 {len(stocks)} 只候选股票"
            ))

    # ─────────────────── Audit: Multi-Dimensional ───────────────────

    def _audit_multi_dimensional(self, data: Dict):
        analysis_list = data if isinstance(data, list) else data.get("analysis", [])
        for item in analysis_list:
            code = item.get("code", "")
            if "error" in item:
                if code in self.stock_audits:
                    self.stock_audits[code].alerts.append({
                        "level": AlertLevel.CRITICAL.value,
                        "dimension": "FALLBACK_DETECTION",
                        "rule": "step_error",
                        "message": f"多维度分析失败: {item['error']}"
                    })

    # ─────────────────── Audit: Debate ───────────────────

    def _audit_debate(self, data: Dict):
        results = data if isinstance(data, list) else data.get("results", [])
        for item in results:
            code = item.get("code", "")
            if "error" in item:
                if code in self.stock_audits:
                    self.stock_audits[code].alerts.append({
                        "level": AlertLevel.CRITICAL.value,
                        "dimension": "FALLBACK_DETECTION",
                        "rule": "step_error",
                        "message": f"辩论执行失败: {item['error']}"
                    })

    # ─────────────────── Audit: Recommendations ───────────────────

    def _audit_recommendations(self, data: Dict):
        recs = data if isinstance(data, list) else data.get("recommendations", [])
        for item in recs:
            code = item.get("code", "")
            if item.get("recommendation") == "SKIP":
                if code in self.stock_audits:
                    self.stock_audits[code].alerts.append({
                        "level": AlertLevel.WARNING.value,
                        "dimension": "CONTENT_VALIDATION",
                        "rule": "skipped_stock",
                        "message": f"股票被跳过: {item.get('reason', '')}"
                    })

    # ─────────────────── Audit: Daily Review ───────────────────

    def _audit_daily_review(self, data: Dict):
        if not data or "error" in data:
            self.global_alerts.append(Alert(
                level=AlertLevel.WARNING.value,
                dimension="CONTENT_VALIDATION",
                rule="daily_review_failed",
                message=f"日度复盘失败: {data.get('error', 'unknown')}"
            ))
        else:
            self.global_alerts.append(Alert(
                level=AlertLevel.INFO.value,
                dimension="CONTENT_VALIDATION",
                rule="daily_review_complete",
                message="日度复盘完成"
            ))

    # ─────────────────── Fallback Detection ───────────────────

    def _check_fallbacks(self, entry: StockAuditEntry,
                         multi_dim: Optional[Dict],
                         debate: Optional[Dict]):
        """检测数据降级/fallback"""
        # 从多维度分析获取数据质量
        if multi_dim:
            dq = multi_dim.get("data_quality", "")
            if dq == "degraded":
                entry.alerts.append({
                    "level": AlertLevel.WARNING.value,
                    "dimension": "FALLBACK_DETECTION",
                    "rule": "data_degraded",
                    "message": "多维度分析使用降级数据"
                })
            sources = multi_dim.get("data_sources", {})
            if sources:
                entry.source_summary["multi_dim_sources"] = sources

        # 从辩论结果获取数据质量
        if debate:
            dq = debate.get("data_quality", {})
            overall = dq.get("overall", "unknown")
            entry.data_quality = dq

            if overall == "degraded":
                entry.alerts.append({
                    "level": AlertLevel.WARNING.value,
                    "dimension": "FALLBACK_DETECTION",
                    "rule": "debate_data_degraded",
                    "message": f"辩论使用降级数据: {dq.get('warning', '')}"
                })

            # 检查各维度是否降级
            for dim in ("factor", "technical", "fundamental", "sentiment"):
                source = dq.get(dim, "")
                if "mock" in str(source).lower():
                    entry.alerts.append({
                        "level": AlertLevel.CRITICAL.value,
                        "dimension": "FALLBACK_DETECTION",
                        "rule": f"{dim}_is_mock",
                        "message": f"{dim} 使用模拟数据，不可用于交易决策"
                    })

    # ─────────────────── Content Validation ───────────────────

    def _check_content(self, entry: StockAuditEntry,
                       debate: Optional[Dict],
                       recommendation: Optional[Dict]):
        """验证内容完整性"""
        if not debate:
            return

        # 辩论多方观点非空
        bull_points = debate.get("bull_key_points", [])
        bear_points = debate.get("bear_key_points", [])
        if not bull_points:
            entry.alerts.append({
                "level": AlertLevel.WARNING.value,
                "dimension": "CONTENT_VALIDATION",
                "rule": "bull_points_empty",
                "message": "多方观点为空，辩论不充分"
            })
        if not bear_points:
            entry.alerts.append({
                "level": AlertLevel.WARNING.value,
                "dimension": "CONTENT_VALIDATION",
                "rule": "bear_points_empty",
                "message": "空方观点为空，辩论不充分"
            })

        # 推荐理由非空
        if recommendation:
            reason = recommendation.get("reason", "")
            if not reason or len(reason.strip()) < 5:
                entry.alerts.append({
                    "level": AlertLevel.INFO.value,
                    "dimension": "CONTENT_VALIDATION",
                    "rule": "reason_too_short",
                    "message": "推荐理由过短或缺失"
                })

        # 新闻来源非空验证
        sent_summary = debate.get("sentiment_summary", {})
        if sent_summary:
            source = sent_summary.get("source", "")
            if source and source != "none":
                # 有来源但需要检查是否有新闻内容
                news_count = sent_summary.get("news_count", 0)
                if news_count == 0 and source != "combined":
                    entry.alerts.append({
                        "level": AlertLevel.INFO.value,
                        "dimension": "CONTENT_VALIDATION",
                        "rule": "no_news_items",
                        "message": f"舆情来源 {source} 无具体新闻条目"
                    })

    # ─────────────────── Consistency Check ───────────────────

    def _check_consistency(self, entry: StockAuditEntry,
                           multi_dim: Optional[Dict],
                           debate: Optional[Dict],
                           recommendation: Optional[Dict]):
        """跨步骤一致性检查"""
        if not multi_dim or not debate:
            return

        multi_rec = multi_dim.get("recommendation", "HOLD")
        final_action = debate.get("final_action", "")
        trader_decision = debate.get("trader_decision", "")

        consistency = {
            "multi_dim_recommendation": multi_rec,
            "debate_final_action": final_action,
            "trader_decision": trader_decision,
        }

        # 检查严重冲突
        conflicts = []
        if multi_rec == "BUY" and final_action in ("reject", "error"):
            conflicts.append("多维度建议买入但辩论拒绝")
        elif multi_rec == "SELL" and final_action == "execute":
            conflicts.append("多维度建议卖出但辩论执行")

        if conflicts:
            entry.alerts.append({
                "level": AlertLevel.WARNING.value,
                "dimension": "CONSISTENCY_CHECK",
                "rule": "multi_dim_debate_conflict",
                "message": "; ".join(conflicts)
            })
            consistency["has_conflict"] = True
            consistency["conflicts"] = conflicts
        else:
            consistency["has_conflict"] = False

        # 最终推荐与辩论结论一致性
        if recommendation:
            final_rec = recommendation.get("recommendation", "")
            consistency["final_recommendation"] = final_rec
            if final_rec == "BUY" and trader_decision not in ("BUY", "buy"):
                conflicts.append(f"最终推荐BUY但Trader决策为{trader_decision}")
            elif final_rec in ("REJECT", "SKIP") and trader_decision in ("BUY", "buy"):
                conflicts.append(f"最终推荐{final_rec}但Trader决策为BUY")

        entry.consistency = consistency

    # ─────────────────── Reliability Score ───────────────────

    def _calculate_score(self, entry: StockAuditEntry) -> float:
        """计算可靠性评分 (0-100)"""
        score = 100.0

        for alert in entry.alerts:
            rule = alert.get("rule", "")
            level = alert.get("level", "")

            if rule == "technical_degraded" or ("技术面" in alert.get("message", "") and "降级" in alert.get("message", "")):
                score -= DEDUCTIONS["technical_degraded"]
            elif rule == "fundamental_degraded" or ("基本面" in alert.get("message", "") and "降级" in alert.get("message", "")):
                score -= DEDUCTIONS["fundamental_degraded"]
            elif rule == "sentiment_degraded" or ("舆情" in alert.get("message", "") and "降级" in alert.get("message", "")):
                score -= DEDUCTIONS["sentiment_degraded"]
            elif rule == "factor_degraded":
                score -= DEDUCTIONS["factor_degraded"]
            elif rule == "bull_points_empty":
                score -= DEDUCTIONS["bull_points_empty"]
            elif rule == "bear_points_empty":
                score -= DEDUCTIONS["bear_points_empty"]
            elif rule == "multi_dim_debate_conflict":
                score -= DEDUCTIONS["multi_dim_debate_conflict"]
            elif rule == "reason_too_short":
                score -= DEDUCTIONS["reason_empty"]
            elif rule == "no_news_items" or "新闻" in alert.get("message", ""):
                score -= DEDUCTIONS["news_sources_empty"]
            elif rule == "step_error":
                score -= DEDUCTIONS["step_error"]
            elif rule == "final_action_error":
                score -= DEDUCTIONS["final_action_error"]
            elif "mock" in alert.get("message", "").lower():
                score -= 20  # 模拟数据直接扣 20

        # 额外检查数据质量
        dq = entry.data_quality
        if dq.get("overall") == "degraded":
            # 已经通过 alerts 扣分，不再重复
            pass
        elif dq.get("overall") == "good":
            # 优质数据加分
            score = min(100, score + 5)

        return max(0, min(100, round(score, 1)))

    # ─────────────────── Report Generation ───────────────────

    def generate_json_report(self) -> Dict:
        """生成 JSON 审计报告"""
        stock_entries = []
        for code, entry in sorted(self.stock_audits.items()):
            stock_entries.append({
                "code": entry.code,
                "name": entry.name,
                "reliability": entry.reliability,
                "is_reliable": entry.is_reliable,
                "alerts": entry.alerts,
                "data_quality": entry.data_quality,
                "source_summary": entry.source_summary,
                "consistency": entry.consistency,
            })

        # 全局统计
        total = len(stock_entries)
        reliable = sum(1 for e in stock_entries if e["is_reliable"])
        critical_alerts = sum(1 for e in stock_entries for a in e["alerts"] if a["level"] == "CRITICAL")
        warning_alerts = sum(1 for e in stock_entries for a in e["alerts"] if a["level"] == "WARNING")

        return {
            "audit_meta": {
                "date": self.date,
                "market": self.market,
                "generated_at": datetime.now().isoformat(),
                "started_at": self._started_at,
                "steps_recorded": list(self.step_records.keys()),
            },
            "summary": {
                "total_stocks": total,
                "reliable_count": reliable,
                "unreliable_count": total - reliable,
                "avg_reliability": round(sum(e["reliability"] for e in stock_entries) / max(total, 1), 1),
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "global_alerts": [asdict(a) if hasattr(a, '__dataclass_fields__') else a for a in self.global_alerts],
            },
            "stock_audits": stock_entries,
            "deduction_rules": DEDUCTIONS,
        }

    def generate_markdown_report(self) -> str:
        """生成 Markdown 审计报告"""
        json_report = self.generate_json_report()
        meta = json_report["audit_meta"]
        summary = json_report["summary"]

        lines = []
        lines.append("# Workflow C 审计报告")
        lines.append(f"\n**日期**: {meta['date']}  |  **市场**: {meta['market']}")
        lines.append(f"**生成时间**: {meta['generated_at']}")
        lines.append(f"**审计步骤**: {', '.join(meta['steps_recorded'])}")

        # 总体审计结论
        lines.append("\n## 总体审计结论")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 审计股票数 | {summary['total_stocks']} |")
        lines.append(f"| 可靠 | {summary['reliable_count']} |")
        lines.append(f"| 不可靠 | {summary['unreliable_count']} |")
        lines.append(f"| 平均可靠性 | {summary['avg_reliability']:.1f}/100 |")
        lines.append(f"| CRITICAL 告警 | {summary['critical_alerts']} |")
        lines.append(f"| WARNING 告警 | {summary['warning_alerts']} |")

        # 全局告警
        if summary["global_alerts"]:
            lines.append("\n## 全局告警")
            for alert in summary["global_alerts"]:
                level = alert.get("level", "INFO")
                icon = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵", "PASS": "🟢"}.get(level, "")
                lines.append(f"- {icon} **[{level}]** {alert.get('message', '')} ({alert.get('rule', '')})")

        # 逐股审计
        lines.append("\n## 逐股审计详情")
        for entry_data in json_report["stock_audits"]:
            code = entry_data["code"]
            name = entry_data["name"]
            reliability = entry_data["reliability"]
            is_reliable = entry_data["is_reliable"]
            alerts = entry_data["alerts"]

            status_icon = "✅" if is_reliable else "❌"
            lines.append(f"\n### {status_icon} {code} {name} (可靠性: {reliability:.1f}/100)")

            # 数据质量
            dq = entry_data.get("data_quality", {})
            if dq:
                lines.append(f"- **数据质量**: {dq.get('overall', 'unknown')}")
                if dq.get("warning"):
                    lines.append(f"  - ⚠️ {dq['warning']}")

            # 一致性
            cons = entry_data.get("consistency", {})
            if cons:
                lines.append(f"- **一致性**: {'有冲突' if cons.get('has_conflict') else '通过'}")
                if cons.get("conflicts"):
                    for c in cons["conflicts"]:
                        lines.append(f"  - ⚠️ {c}")

            # 告警
            if alerts:
                lines.append(f"- **告警** ({len(alerts)} 条):")
                for alert in alerts:
                    level = alert.get("level", "INFO")
                    icon = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}.get(level, "")
                    lines.append(f"  - {icon} **[{level}]** {alert.get('message', '')}")
            else:
                lines.append(f"- **告警**: 无")

        return "\n".join(lines)

    def save(self, output_path: Path):
        """保存 JSON 审计报告"""
        report = self.generate_json_report()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def save_markdown(self, output_path: Path):
        """保存 Markdown 审计报告"""
        md = self.generate_markdown_report()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)

    def get_reliability_score(self) -> float:
        """获取所有股票的平均可靠性评分"""
        if not self.stock_audits:
            return 0.0
        return sum(e.reliability for e in self.stock_audits.values()) / len(self.stock_audits)

    def is_all_reliable(self) -> bool:
        """检查所有股票是否都可靠"""
        return all(e.is_reliable for e in self.stock_audits.values()) if self.stock_audits else False

    def print_summary(self):
        """打印审计摘要到控制台"""
        report = self.generate_json_report()
        summary = report["summary"]

        print(f"\n{'='*60}")
        print(" 审计摘要")
        print(f"{'='*60}")
        print(f"  审计股票: {summary['total_stocks']}")
        print(f"  可靠: {summary['reliable_count']} | 不可靠: {summary['unreliable_count']}")
        print(f"  平均可靠性: {summary['avg_reliability']:.1f}/100")
        print(f"  CRITICAL: {summary['critical_alerts']} | WARNING: {summary['warning_alerts']}")

        # 逐股快速查看
        for entry_data in report["stock_audits"]:
            icon = "✅" if entry_data["is_reliable"] else "❌"
            print(f"  {icon} {entry_data['code']} {entry_data['name']}: {entry_data['reliability']:.1f}/100")
            for alert in entry_data["alerts"]:
                if alert["level"] in ("CRITICAL", "WARNING"):
                    print(f"     [{alert['level']}] {alert['message']}")
        print(f"{'='*60}")


if __name__ == "__main__":
    # 测试
    audit = WorkflowAudit(date="2026-04-07", market="CN")
    audit.global_alerts.append(Alert(
        level=AlertLevel.INFO.value,
        dimension="DATA_PROVENANCE",
        rule="test",
        message="测试全局告警"
    ))
    print(audit.generate_markdown_report())
