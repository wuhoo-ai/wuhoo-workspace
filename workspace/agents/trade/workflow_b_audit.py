#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow B 增强版 — 审计报告模块

审计维度:
1. 数据获取 (Data Acquisition) — akshare/Tushare/DataAggregator 可用性与完整性
2. 公开信息 (Public Info) — 网络搜索、公告、研报覆盖度
3. 定性分析 (Qualitative) — 商业模式/护城河/管理层分析深度
4. 定量分析 (Quantitative) — 财务数据覆盖度、趋势完整性
5. 估值分析 (Valuation) — DCF/相对估值 的假设合理性
6. 多空辩论 (Debate) — 多空观点质量与辩论充分性
7. 一致性校验 (Consistency) — 各环节结论是否自洽
8. 红旗检测 (Red Flags) — 财务异常、估值泡沫识别

用法:
    from workflow_b_audit import WorkflowBAudit
    audit = WorkflowBAudit(audit_context)
    result = audit.run()
    # result -> { reliability_score, alerts, audit_report }
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


# ============================================================
# 扣分规则
# ============================================================
DEDUCTION_RULES = {
    # 数据获取
    "akshare_unavailable": 15,
    "tushare_unavailable": 15,
    "data_aggregator_unavailable": 10,
    "no_financial_data": 20,
    "financial_data_incomplete": 10,
    # 公开信息
    "no_web_search": 15,
    "no_analyst_reports": 10,
    "no_recent_news": 10,
    # 定性分析
    "industry_unknown": 10,
    "no_moat_analysis": 10,
    "no_management_analysis": 5,
    # 定量分析
    "no_roe_data": 15,
    "no_cashflow_data": 10,
    "no_growth_data": 10,
    "data_periods_insufficient": 10,
    # 估值分析
    "dcf_unavailable": 10,
    "dcf_unreasonable_params": 10,
    "no_relative_valuation": 10,
    "no_historical_valuation": 10,
    # 多空辩论
    "debate_unavailable": 15,
    "bull_points_empty": 10,
    "bear_points_empty": 10,
    "debate_confidence_low": 10,
    # 一致性
    "fundamental_valuation_conflict": 15,
    "debate_valuation_conflict": 10,
    # 红旗
    "red_flags_ignored": 15,
    "extreme_valuation_ignored": 10,
}


class AuditAlert:
    """审计告警"""
    LEVEL_CRITICAL = "CRITICAL"   # 严重 — 数据不可用或结论严重不一致
    LEVEL_WARNING = "WARNING"      # 警告 — 数据降级或部分缺失
    LEVEL_INFO = "INFO"            # 信息 — 正常记录

    def __init__(self, level: str, dimension: str, rule: str, message: str, detail: str = ""):
        self.level = level
        self.dimension = dimension
        self.rule = rule
        self.message = message
        self.detail = detail

    def to_dict(self) -> Dict:
        return {
            "level": self.level,
            "dimension": self.dimension,
            "rule": self.rule,
            "message": self.message,
            "detail": self.detail
        }


class WorkflowBAudit:
    """Workflow B 增强版审计器"""

    def __init__(self, context: Dict):
        """
        context 包含:
        - symbol: 股票代码
        - name: 公司名称
        - date: 分析日期
        - akshare_data: akshare 获取的数据
        - factor_data: DataAggregator 因子数据
        - debate_data: 多空辩论结果
        - dcf_data: DCF 估值结果
        - financial_summary: 财务分析摘要
        - valuation_summary: 估值摘要
        - decision: 最终决策
        - web_search_results: 网络搜索结果（可选）
        - output_dir: 输出目录
        """
        self.ctx = context
        self.alerts: List[AuditAlert] = []
        self.scores: Dict[str, Dict] = {}
        self.start_time = datetime.now().isoformat()

    def run(self) -> Dict:
        """执行完整审计"""
        self._audit_data_acquisition()
        self._audit_public_info()
        self._audit_qualitative()
        self._audit_quantitative()
        self._audit_valuation()
        self._audit_debate()
        self._audit_consistency()
        self._audit_red_flags()

        reliability = self._calculate_reliability()
        report = self._build_report(reliability)

        return report

    # ============================================================
    # 1. 数据获取审计
    # ============================================================
    def _audit_data_acquisition(self):
        """审计数据获取环节"""
        dimension = "DATA_ACQUISITION"
        akshare = self.ctx.get("akshare_data", {})
        factor = self.ctx.get("factor_data", {})

        # akshare 可用性
        if akshare.get("available"):
            self._info(dimension, "akshare_available", "akshare 财务数据获取成功")
            self._record_score("akshare", 100, 0)

            # 检查数据完整性
            completeness = self._check_akshare_completeness(akshare)
            if completeness < 60:
                self._warn(dimension, "financial_data_incomplete",
                          f"akshare 数据完整性仅 {completeness:.0f}%，部分财务数据缺失")
                self._record_score("akshare", completeness,
                                  DEDUCTION_RULES["financial_data_incomplete"])
            else:
                self._record_score("akshare", completeness, 0)
        else:
            self._warn(dimension, "akshare_unavailable",
                      "akshare 不可用，无法获取完整财务数据")
            self._record_score("akshare", 0, DEDUCTION_RULES["akshare_unavailable"])

        # DataAggregator 可用性
        if factor.get("available") or factor.get("fundamental_data"):
            self._info(dimension, "data_aggregator_available", "DataAggregator 因子数据获取成功")
            self._record_score("data_aggregator", 100, 0)
        else:
            self._warn(dimension, "data_aggregator_unavailable",
                      "DataAggregator 不可用，技术面和舆情面数据缺失")
            self._record_score("data_aggregator", 0, DEDUCTION_RULES["data_aggregator_unavailable"])

        # 综合数据质量
        ak_score = self.scores.get("akshare", {}).get("score", 0)
        da_score = self.scores.get("data_aggregator", {}).get("score", 0)
        if ak_score > 0 or da_score > 0:
            overall = max(ak_score, da_score)
            self._info(dimension, "data_overall",
                      f"数据获取完成 — akshare {ak_score:.0f}% + DataAggregator {da_score:.0f}%")
        else:
            self._critical(dimension, "no_data", "所有数据源均不可用，分析结果不可靠")

    def _check_akshare_completeness(self, akshare: Dict) -> float:
        """检查 akshare 数据完整性"""
        total_fields = 0
        available_fields = 0

        checks = [
            ("basic", "基本信息"),
            ("indicators", "财务指标"),
            ("income", "利润表"),
            ("balance", "资产负债表"),
            ("cashflow", "现金流"),
            ("valuation_history", "估值历史"),
            ("holders", "股东信息"),
            ("dividend", "分红数据"),
        ]

        for key, label in checks:
            total_fields += 1
            data = akshare.get(key)
            if data:
                if isinstance(data, dict) and "error" not in data:
                    available_fields += 1
                elif isinstance(data, list) and len(data) > 0:
                    available_fields += 1

        return (available_fields / total_fields * 100) if total_fields > 0 else 0

    # ============================================================
    # 2. 公开信息审计
    # ============================================================
    def _audit_public_info(self):
        """审计公开信息获取"""
        dimension = "PUBLIC_INFO"
        web_results = self.ctx.get("web_search_results", [])
        has_analyst = self.ctx.get("has_analyst_reports", False)

        # 网络搜索
        if web_results:
            self._info(dimension, "web_search_complete",
                      f"网络搜索获取 {len(web_results)} 条结果")
            self._record_score("web_search", 100, 0)
        else:
            self._warn(dimension, "no_web_search",
                      "未执行网络搜索，缺少最新市场信息")
            self._record_score("web_search", 0, DEDUCTION_RULES["no_web_search"])

        # 研报覆盖
        if has_analyst:
            self._info(dimension, "analyst_reports_available", "有券商研报参考")
            self._record_score("analyst_reports", 100, 0)
        else:
            self._warn(dimension, "no_analyst_reports",
                      "缺少券商研报数据，盈利预测基于估算")
            self._record_score("analyst_reports", 50, DEDUCTION_RULES["no_analyst_reports"])

    # ============================================================
    # 3. 定性分析审计
    # ============================================================
    def _audit_qualitative(self):
        """审计定性分析环节"""
        dimension = "QUALITATIVE_ANALYSIS"
        akshare = self.ctx.get("akshare_data", {})
        basic = akshare.get("basic", {})
        industry = basic.get("industry", "")

        if industry and industry != "未知":
            self._info(dimension, "industry_identified",
                      f"行业识别成功：{industry}")
            self._record_score("industry", 100, 0)
        else:
            self._warn(dimension, "industry_unknown", "行业信息未知，商业模式分析受限")
            self._record_score("industry", 0, DEDUCTION_RULES["industry_unknown"])

        # 护城河分析
        moat_analysis = self.ctx.get("moat_analysis", {})
        if moat_analysis and moat_analysis.get("evidence"):
            evidence_count = len(moat_analysis.get("evidence", []))
            self._info(dimension, "moat_analysis_complete",
                      f"护城河分析完成 — {evidence_count} 条证据")
            self._record_score("moat", 100, 0)
        else:
            self._warn(dimension, "no_moat_analysis", "护城河分析数据不足")
            self._record_score("moat", 30, DEDUCTION_RULES["no_moat_analysis"])

        # 管理层分析
        management = self.ctx.get("management_analysis", "")
        if management and len(management) > 100:
            self._info(dimension, "management_analysis_complete", "管理层分析完成")
            self._record_score("management", 100, 0)
        else:
            self._info(dimension, "management_analysis_limited",
                      "管理层分析数据有限，基于间接推断")
            self._record_score("management", 60, DEDUCTION_RULES["no_management_analysis"])

    # ============================================================
    # 4. 定量分析审计
    # ============================================================
    def _audit_quantitative(self):
        """审计定量分析环节"""
        dimension = "QUANTITATIVE_ANALYSIS"
        akshare = self.ctx.get("akshare_data", {})
        indicators = akshare.get("indicators", [])
        income = akshare.get("income", [])
        cashflow = akshare.get("cashflow", [])

        # ROE 数据
        has_roe = any(ind.get("加权净资产收益率(%)") is not None for ind in indicators)
        if has_roe:
            self._info(dimension, "roe_data_available", "ROE 数据可用")
            self._record_score("roe", 100, 0)
        else:
            self._warn(dimension, "no_roe_data", "ROE 数据缺失")
            self._record_score("roe", 0, DEDUCTION_RULES["no_roe_data"])

        # 现金流数据
        if cashflow and len(cashflow) > 0:
            self._info(dimension, "cashflow_data_available",
                      f"现金流数据可用 — {len(cashflow)} 期")
            self._record_score("cashflow", 100, 0)
        else:
            self._warn(dimension, "no_cashflow_data", "现金流数据缺失")
            self._record_score("cashflow", 0, DEDUCTION_RULES["no_cashflow_data"])

        # 成长数据
        if income and len(income) >= 2:
            self._info(dimension, "growth_data_available",
                      f"成长性数据可用 — {len(income)} 期")
            self._record_score("growth", 100, 0)
        else:
            self._warn(dimension, "no_growth_data",
                      "历史利润数据不足（< 2 期），无法计算 CAGR")
            self._record_score("growth", 0, DEDUCTION_RULES["no_growth_data"])

        # 数据期数充足性
        period_count = len(indicators)
        if period_count >= 4:
            self._info(dimension, "data_periods_sufficient",
                      f"财务数据期数充足 — {period_count} 期")
            self._record_score("data_periods", 100, 0)
        elif period_count >= 2:
            self._info(dimension, "data_periods_minimal",
                      f"财务数据期数偏少 — {period_count} 期，建议 4 期以上")
            self._record_score("data_periods", 60, DEDUCTION_RULES["data_periods_insufficient"])
        else:
            self._warn(dimension, "data_periods_insufficient",
                      f"财务数据期数严重不足 — {period_count} 期")
            self._record_score("data_periods", 0, DEDUCTION_RULES["data_periods_insufficient"])

    # ============================================================
    # 5. 估值分析审计
    # ============================================================
    def _audit_valuation(self):
        """审计估值分析环节"""
        dimension = "VALUATION_ANALYSIS"
        dcf = self.ctx.get("dcf_data", {})
        valuation_summary = self.ctx.get("valuation_summary", {})

        # DCF 可用性
        if dcf.get("available"):
            self._info(dimension, "dcf_available", "三阶段 DCF 估值完成")
            self._record_score("dcf", 100, 0)

            # 检查 DCF 参数合理性
            scenarios = dcf.get("scenarios", {})
            if scenarios:
                # 检查乐观/悲观差异
                bear_value = scenarios.get("悲观", {}).get("value_per_share", 0)
                bull_value = scenarios.get("乐观", {}).get("value_per_share", 0)
                if bear_value > 0 and bull_value > 0:
                    spread = (bull_value - bear_value) / bear_value
                    if spread > 10:
                        self._warn(dimension, "dcf_unreasonable_params",
                                  f"DCF 乐观/悲观估值差异过大 ({spread:.0f}x)，参数假设可能不合理")
                        self._record_score("dcf_params", 50, DEDUCTION_RULES["dcf_unreasonable_params"])
                    else:
                        self._info(dimension, "dcf_params_reasonable",
                                  f"DCF 参数合理 — 乐观/悲观差异 {spread:.1f}x")
                        self._record_score("dcf_params", 100, 0)
        else:
            reason = dcf.get("reason", "未知")
            self._info(dimension, "dcf_unavailable",
                      f"DCF 估值不可用 — {reason}")
            self._record_score("dcf", 0, DEDUCTION_RULES["dcf_unavailable"])

        # 相对估值
        has_relative = valuation_summary.get("has_relative_valuation", False)
        has_historical = valuation_summary.get("has_historical_valuation", False)

        if has_relative:
            self._info(dimension, "relative_valuation_available", "相对估值完成")
            self._record_score("relative_valuation", 100, 0)
        else:
            self._warn(dimension, "no_relative_valuation", "缺少相对估值")
            self._record_score("relative_valuation", 0, DEDUCTION_RULES["no_relative_valuation"])

        if has_historical:
            self._info(dimension, "historical_valuation_available", "历史估值分位可用")
            self._record_score("historical_valuation", 100, 0)
        else:
            self._warn(dimension, "no_historical_valuation", "缺少历史估值分位")
            self._record_score("historical_valuation", 0, DEDUCTION_RULES["no_historical_valuation"])

    # ============================================================
    # 6. 多空辩论审计
    # ============================================================
    def _audit_debate(self):
        """审计多空辩论环节"""
        dimension = "DEBATE_QUALITY"
        debate = self.ctx.get("debate_data", {})

        if debate and debate.get("bull_points") is not None:
            method = debate.get("method", "unknown")
            if method == "quick_analysis":
                self._info(dimension, "debate_simplified",
                          "使用简化规则分析（非完整四角色辩论）")
                self._record_score("debate_method", 50, DEDUCTION_RULES["debate_unavailable"])
            else:
                self._info(dimension, "debate_full", "完整四角色辩论完成")
                self._record_score("debate_method", 100, 0)

            # 多空观点
            bull_points = debate.get("bull_points", [])
            bear_points = debate.get("bear_points", [])

            if bull_points and len(bull_points) > 0:
                self._info(dimension, "bull_points_available",
                          f"看多观点 {len(bull_points)} 条")
                self._record_score("bull_points", 100, 0)
            else:
                self._warn(dimension, "bull_points_empty", "缺少看多观点")
                self._record_score("bull_points", 0, DEDUCTION_RULES["bull_points_empty"])

            if bear_points and len(bear_points) > 0:
                self._info(dimension, "bear_points_available",
                          f"看空观点 {len(bear_points)} 条")
                self._record_score("bear_points", 100, 0)
            else:
                self._warn(dimension, "bear_points_empty", "缺少看空观点")
                self._record_score("bear_points", 0, DEDUCTION_RULES["bear_points_empty"])

            # 置信度
            confidence = debate.get("confidence", 50)
            if confidence < 40:
                self._warn(dimension, "debate_confidence_low",
                          f"辩论置信度仅 {confidence}%，结论可靠性低")
                self._record_score("debate_confidence", 30, DEDUCTION_RULES["debate_confidence_low"])
            elif confidence < 60:
                self._info(dimension, "debate_confidence_medium",
                          f"辩论置信度 {confidence}%，中等")
                self._record_score("debate_confidence", 60, 0)
            else:
                self._info(dimension, "debate_confidence_high",
                          f"辩论置信度 {confidence}%，较高")
                self._record_score("debate_confidence", 100, 0)
        else:
            self._critical(dimension, "debate_unavailable",
                          "多空辩论模块不可用")
            self._record_score("debate_method", 0, DEDUCTION_RULES["debate_unavailable"])

    # ============================================================
    # 7. 一致性校验
    # ============================================================
    def _audit_consistency(self):
        """审计各环节结论一致性"""
        dimension = "CONSISTENCY_CHECK"
        decision = self.ctx.get("decision", {})
        debate = self.ctx.get("debate_data", {})
        dcf = self.ctx.get("dcf_data", {})

        score = decision.get("score", 5)
        debate_rec = debate.get("recommendation", "")
        debate_conf = debate.get("confidence", 50)

        # 基本面 vs 估值
        dcf_available = dcf.get("available", False)
        if dcf_available:
            mos = dcf.get("margin_of_safety")
            if mos is not None:
                if mos > 20 and score < 4:
                    self._warn(dimension, "fundamental_valuation_conflict",
                              f"DCF 安全边际充足 ({mos:.1f}%) 但最终评分偏低 ({score:.1f}/10)")
                elif mos < -30 and score > 7:
                    self._warn(dimension, "fundamental_valuation_conflict",
                              f"当前价格远超内在价值 (溢价 {abs(mos):.1f}%) 但最终评分偏高 ({score:.1f}/10)")
                else:
                    self._info(dimension, "fundamental_valuation_consistent",
                              "基本面与估值结论一致")

        # 辩论 vs 估值
        if debate_rec == "看多" and dcf_available:
            mos = dcf.get("margin_of_safety")
            if mos is not None and mos < -30:
                self._warn(dimension, "debate_valuation_conflict",
                          f"辩论看多但当前价格溢价 {abs(mos):.1f}%")
            else:
                self._info(dimension, "debate_valuation_consistent",
                          "辩论结论与估值一致")

        self._record_score("consistency", 100, 0)

    # ============================================================
    # 8. 红旗检测
    # ============================================================
    def _audit_red_flags(self):
        """审计红旗信号"""
        dimension = "RED_FLAG_DETECTION"
        red_flags = self.ctx.get("red_flags", [])
        decision = self.ctx.get("decision", {})

        if red_flags:
            critical_flags = [f for f in red_flags if f.startswith("🔴")]
            warning_flags = [f for f in red_flags if f.startswith("🟡")]

            if critical_flags:
                self._warn(dimension, "critical_red_flags",
                          f"检测到 {len(critical_flags)} 个严重财务红旗信号")
            if warning_flags:
                self._info(dimension, "warning_red_flags",
                          f"检测到 {len(warning_flags)} 个中度财务红旗信号")

            # 检查决策是否充分考虑了红旗
            score = decision.get("score", 5)
            if len(critical_flags) >= 2 and score > 6:
                self._warn(dimension, "red_flags_ignored",
                          f"存在 {len(critical_flags)} 个严重红旗但最终评分 {score:.1f}/10 偏高，可能忽略了财务风险")
            else:
                self._info(dimension, "red_flags_considered", "红旗信号已在决策中考虑")
                self._record_score("red_flags", 100, 0)
        else:
            self._info(dimension, "no_red_flags", "未检测到财务红旗信号")
            self._record_score("red_flags", 100, 0)

        # 极端估值检查
        akshare = self.ctx.get("akshare_data", {})
        basic = akshare.get("basic", {})
        pe = basic.get("pe_ttm")
        pb = basic.get("pb")
        if pe and pe > 100:
            self._warn(dimension, "extreme_valuation_pe",
                      f"PE(TTM) {pe:.0f}x 极高，估值泡沫风险")
        if pb and pb > 10:
            self._warn(dimension, "extreme_valuation_pb",
                      f"PB {pb:.1f}x 极高，估值泡沫风险")

    # ============================================================
    # 计算可靠性得分
    # ============================================================
    def _calculate_reliability(self) -> Dict:
        """计算综合可靠性得分"""
        total_deduction = 0
        max_possible = 0
        deductions = {}

        for name, score_info in self.scores.items():
            deduction = score_info.get("deduction", 0)
            total_deduction += deduction
            max_possible += 100
            deductions[name] = {
                "score": score_info.get("score", 0),
                "deduction": deduction
            }

        if max_possible == 0:
            reliability = 0
        else:
            reliability = max(0, min(100, 100 - (total_deduction / max_possible) * 100))

        return {
            "reliability_score": round(reliability, 1),
            "total_deduction": round(total_deduction, 1),
            "max_possible": max_possible,
            "deductions": deductions
        }

    # ============================================================
    # 构建审计报告
    # ============================================================
    def _build_report(self, reliability: Dict) -> Dict:
        """构建完整审计报告"""
        critical_count = sum(1 for a in self.alerts if a.level == AuditAlert.LEVEL_CRITICAL)
        warning_count = sum(1 for a in self.alerts if a.level == AuditAlert.LEVEL_WARNING)
        info_count = sum(1 for a in self.alerts if a.level == AuditAlert.LEVEL_INFO)

        score = reliability["reliability_score"]
        if score >= 80:
            grade = "A — 高可靠性"
        elif score >= 60:
            grade = "B — 中等可靠性"
        elif score >= 40:
            grade = "C — 低可靠性"
        else:
            grade = "D — 不可靠"

        return {
            "audit_meta": {
                "symbol": self.ctx.get("symbol"),
                "name": self.ctx.get("name"),
                "date": self.ctx.get("date"),
                "generated_at": datetime.now().isoformat(),
                "started_at": self.start_time,
                "version": "2.0"
            },
            "reliability": {
                "score": score,
                "grade": grade,
                "total_deduction": reliability["total_deduction"],
                "max_possible": reliability["max_possible"],
                "dimension_scores": reliability["deductions"]
            },
            "summary": {
                "total_alerts": len(self.alerts),
                "critical_alerts": critical_count,
                "warning_alerts": warning_count,
                "info_alerts": info_count
            },
            "alerts": [a.to_dict() for a in self.alerts],
            "deduction_rules": DEDUCTION_RULES
        }

    # ============================================================
    # 工具方法
    # ============================================================
    def _critical(self, dimension: str, rule: str, message: str, detail: str = ""):
        self.alerts.append(AuditAlert(AuditAlert.LEVEL_CRITICAL, dimension, rule, message, detail))

    def _warn(self, dimension: str, rule: str, message: str, detail: str = ""):
        self.alerts.append(AuditAlert(AuditAlert.LEVEL_WARNING, dimension, rule, message, detail))

    def _info(self, dimension: str, rule: str, message: str, detail: str = ""):
        self.alerts.append(AuditAlert(AuditAlert.LEVEL_INFO, dimension, rule, message, detail))

    def _record_score(self, name: str, score: float, deduction: int):
        self.scores[name] = {"score": score, "deduction": deduction}

    # ============================================================
    # Markdown 报告生成
    # ============================================================
    def generate_markdown(self, audit_report: Dict) -> str:
        """生成 Markdown 格式的审计报告"""
        rel = audit_report["reliability"]
        summary = audit_report["summary"]
        alerts = audit_report["alerts"]

        report = []
        report.append(f"""## 🔍 审计报告

**可靠性得分**: **{rel['score']:.1f}/100** — {rel['grade']}
**总扣分**: {rel['total_deduction']:.1f} / {rel['max_possible']}
**告警统计**: 🔴 严重 {summary['critical_alerts']} | 🟡 警告 {summary['warning_alerts']} | 🔵 信息 {summary['info_alerts']}

---

### 维度得分明细

| 维度 | 得分 | 扣分 | 状态 |
|------|------|------|------|
""")
        for dim_name, dim_info in rel["dimension_scores"].items():
            score = dim_info["score"]
            deduction = dim_info["deduction"]
            if score >= 80:
                status = "✅"
            elif score >= 50:
                status = "🟡"
            else:
                status = "🔴"
            dim_label = self._dimension_label(dim_name)
            report.append(f"| {dim_label} | {score:.0f}% | -{deduction} | {status} |")

        report.append(f"""
---

### 告警详情

""")
        if alerts:
            for alert in alerts:
                if alert["level"] == "CRITICAL":
                    report.append(f"- 🔴 **{alert['dimension']}**: {alert['message']}")
                elif alert["level"] == "WARNING":
                    report.append(f"- 🟡 **{alert['dimension']}**: {alert['message']}")
                # INFO 不展示
        else:
            report.append("- 无告警")

        report.append("""
---

### 审计结论

""")
        if rel["score"] >= 80:
            report.append("✅ **数据充分、分析完整、结论可靠**。各维度数据质量良好，建议采信分析报告结论。")
        elif rel["score"] >= 60:
            report.append("🟡 **数据基本充分、分析较完整**。部分维度存在数据缺失或降级，建议结合独立研究交叉验证。")
        elif rel["score"] >= 40:
            report.append("🟠 **数据不足、分析有限**。多个关键维度数据缺失，分析结论可靠性较低，建议谨慎参考。")
        else:
            report.append("🔴 **数据严重不足、分析不可靠**。核心数据源不可用，分析结论仅供参考，不建议作为投资依据。")

        report.append("\n---\n")
        return "\n".join(report)

    def _dimension_label(self, name: str) -> str:
        labels = {
            "akshare": "akshare 财务数据",
            "data_aggregator": "DataAggregator 因子",
            "web_search": "网络搜索",
            "analyst_reports": "券商研报",
            "industry": "行业识别",
            "moat": "护城河分析",
            "management": "管理层分析",
            "roe": "ROE 数据",
            "cashflow": "现金流数据",
            "growth": "成长性数据",
            "data_periods": "数据期数",
            "dcf": "DCF 估值",
            "dcf_params": "DCF 参数",
            "relative_valuation": "相对估值",
            "historical_valuation": "历史估值分位",
            "debate_method": "辩论方法",
            "bull_points": "看多观点",
            "bear_points": "看空观点",
            "debate_confidence": "辩论置信度",
            "consistency": "一致性校验",
            "red_flags": "红旗检测",
        }
        return labels.get(name, name)


# ============================================================
# 便捷函数
# ============================================================

def build_audit_context(**kwargs) -> Dict:
    """构建审计上下文的便捷函数"""
    return {
        "symbol": kwargs.get("symbol", ""),
        "name": kwargs.get("name", ""),
        "date": kwargs.get("date", datetime.now().strftime("%Y-%m-%d")),
        "akshare_data": kwargs.get("akshare_data", {}),
        "factor_data": kwargs.get("factor_data", {}),
        "debate_data": kwargs.get("debate_data", {}),
        "dcf_data": kwargs.get("dcf_data", {}),
        "financial_summary": kwargs.get("financial_summary", {}),
        "valuation_summary": kwargs.get("valuation_summary", {}),
        "decision": kwargs.get("decision", {}),
        "web_search_results": kwargs.get("web_search_results", []),
        "has_analyst_reports": kwargs.get("has_analyst_reports", False),
        "moat_analysis": kwargs.get("moat_analysis", {}),
        "management_analysis": kwargs.get("management_analysis", ""),
        "red_flags": kwargs.get("red_flags", []),
        "output_dir": kwargs.get("output_dir"),
    }
