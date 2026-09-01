#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debate Protocol - 多空辩论协议

定义 Bull Agent 和 Bear Agent 之间的辩论流程和数据交换格式。
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path


class DebateConfig:
    """辩论配置"""
    def __init__(self):
        self.max_rounds = 2           # 最大辩论轮次
        self.timeout_seconds = 300    # 每轮超时 (秒)
        self.enable_rebuttal = True  # 是否启用反驳环节


class DebateRecord:
    """辩论记录"""
    def __init__(
        self,
        debate_id,
        symbol,
        timestamp,
        round_num,
        status,
        bull_view=None,
        bear_view=None,
        bull_rebuttal=None,
        consensus_points=None,
        disagreement_points=None,
        trader_decision=None,
        risk_approval=None,
        final_action=None
    ):
        self.debate_id = debate_id
        self.symbol = symbol
        self.timestamp = timestamp
        self.round = round_num
        self.status = status
        self.bull_view = bull_view
        self.bear_view = bear_view
        self.bull_rebuttal = bull_rebuttal
        self.consensus_points = consensus_points or []
        self.disagreement_points = disagreement_points or []
        self.trader_decision = trader_decision
        self.risk_approval = risk_approval
        self.final_action = final_action
    
    def to_dict(self):
        return {
            "debate_id": self.debate_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "round": self.round,
            "status": self.status,
            "bull_view": self.bull_view,
            "bear_view": self.bear_view,
            "bull_rebuttal": self.bull_rebuttal,
            "consensus_points": self.consensus_points,
            "disagreement_points": self.disagreement_points,
            "trader_decision": self.trader_decision,
            "risk_approval": self.risk_approval,
            "final_action": self.final_action
        }
    
    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)


class DebateProtocol:
    """
    多空辩论协议管理器
    
    辩论流程:
    1. Bull 先输出观点
    2. Bear 接收 Bull 观点 + 原始数据 → 输出反驳
    3. Bull 可选：接收 Bear 反驳 → 二次回应
    4. Trader 接收双方观点 → 综合决策
    5. Risk 独立审核 → 审批结果
    6. Portfolio Manager → 最终执行
    """
    
    def __init__(self, config=None, data_dir="data"):
        self.config = config or DebateConfig()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.current_debate = None

    @property
    def state(self) -> str:
        """当前辩论状态"""
        if self.current_debate is None:
            return "idle"
        return self.current_debate.status  # "ongoing" or "completed"
    
    def start_debate(self, symbol):
        """开始新的辩论"""
        debate_id = "debate_{}_{}".format(
            datetime.now().strftime('%Y%m%d_%H%M%S'),
            symbol.replace('.', '')
        )
        
        self.current_debate = DebateRecord(
            debate_id=debate_id,
            symbol=symbol,
            timestamp=datetime.now().isoformat(),
            round_num=1,
            status="ongoing"
        )
        
        print("[DebateProtocol] 开始辩论：{} for {}".format(debate_id, symbol))
        return self.current_debate
    
    def submit_bull_view(self, view):
        """提交 Bull Agent 观点"""
        if not self.current_debate:
            raise RuntimeError("No active debate. Call start_debate() first.")
        
        assert view.get("agent") == "bull", "View must be from Bull Agent"
        self.current_debate.bull_view = view
        print("[DebateProtocol] Bull 观点已提交：{}".format(view.get('recommendation')))
    
    def submit_bear_view(self, view):
        """提交 Bear Agent 观点"""
        if not self.current_debate:
            raise RuntimeError("No active debate. Call start_debate() first.")
        
        assert view.get("agent") == "bear", "View must be from Bear Agent"
        self.current_debate.bear_view = view
        print("[DebateProtocol] Bear 观点已提交：{}".format(view.get('recommendation')))
    
    def submit_bull_rebuttal(self, rebuttal):
        """提交 Bull 对 Bear 的反驳"""
        if not self.current_debate:
            raise RuntimeError("No active debate.")
        
        self.current_debate.bull_rebuttal = rebuttal
        self.current_debate.round += 1
        print("[DebateProtocol] Bull 反驳已提交 (Round {})".format(self.current_debate.round))
    
    def analyze_debate(self, llm_client=None):
        """分析辩论，提取共识和分歧点
        
        增强版：使用 LLM 分析双方观点，生成实质性共识和分歧，
        而非简单的硬编码规则匹配。
        """
        if not self.current_debate:
            raise RuntimeError("No active debate.")
        
        bull = self.current_debate.bull_view or {}
        bear = self.current_debate.bear_view or {}
        bull_rebuttal = self.current_debate.bull_rebuttal or {}
        
        # 方法1: LLM 驱动分析（优先）
        if llm_client:
            return self._llm_analyze_debate(llm_client, bull, bear, bull_rebuttal)
        
        # 方法2: 规则匹配（回退）
        return self._rule_based_analyze_debate(bull, bear)
    
    def _rule_based_analyze_debate(self, bull, bear):
        """规则驱动的共识/分歧分析（回退方案）"""
        consensus = []
        disagreement = []
        
        # 分析共识点
        bull_risks = bull.get("risks_identified", [])
        bear_risks = bear.get("risks_identified", [])
        
        # 检查双方是否都识别了相同风险
        if bull_risks and bear_risks:
            common_risks = set(bull_risks) & set(bear_risks)
            if common_risks:
                consensus.append(f"双方共同识别的风险: {', '.join(list(common_risks)[:3])}")
        
        # 双方都提到需要止损
        if bull.get("stop_loss") and bear.get("stop_loss"):
            consensus.append("双方都认同需要设置止损位以控制下行风险")
        
        # 置信度接近
        bull_conf = bull.get("confidence", 0)
        bear_conf = bear.get("confidence", 0)
        if abs(bull_conf - bear_conf) < 0.15:
            consensus.append(f"双方置信度接近 (Bull: {bull_conf:.2f}, Bear: {bear_conf:.2f})，表明市场存在不确定性")
        
        # 分析分歧点
        if bull.get("recommendation") != bear.get("recommendation"):
            disagreement.append(f"推荐方向根本分歧：Bull 推荐{bull.get('recommendation')} vs Bear 推荐{bear.get('recommendation')}")
        
        # 目标价分歧
        bull_target = bull.get("target_price", 0)
        bear_target = bear.get("target_price", 0)
        if bull_target and bear_target:
            diff_pct = abs(bull_target - bear_target) / ((bull_target + bear_target) / 2)
            if diff_pct > 0.10:
                disagreement.append(
                    f"目标价差异显著：Bull 目标 {bull_target} vs Bear 目标 {bear_target} "
                    f"(相对差异 {diff_pct:.1%})"
                )
        
        # 仓位建议分歧
        bull_pos = bull.get("position_suggestion", 0)
        bear_pos = bear.get("position_suggestion", 0)
        if bull_pos and bear_pos and abs(bull_pos - bear_pos) > 0.10:
            disagreement.append(
                f"仓位建议分歧：Bull 建议 {bull_pos:.0%} vs Bear 建议 {bear_pos:.0%}"
            )
        
        # Bull 看多理由与 Bear 看空理由的对立
        bull_points = bull.get("bullish_points", [])
        bear_points = bear.get("bearish_points", [])
        bull_categories = {p.get("category") for p in bull_points if p.get("category")}
        bear_categories = {p.get("category") for p in bear_points if p.get("category")}
        
        # 同一维度有不同结论
        overlapping_categories = bull_categories & bear_categories
        for cat in overlapping_categories:
            bull_point = next((p for p in bull_points if p.get("category") == cat), None)
            bear_point = next((p for p in bear_points if p.get("category") == cat), None)
            if bull_point and bear_point:
                disagreement.append(
                    f"[{cat}] 维度对立: Bull 认为'{bull_point.get('point')}' vs "
                    f"Bear 认为'{bear_point.get('point')}'"
                )
        
        # Bear 对 Bull 的反驳点
        for refutation in bear.get("bull_points_refuted", []):
            if refutation.get("rebuttal"):
                disagreement.append(
                    f"Bear 反驳 Bull: '{refutation.get('bull_point')}' → "
                    f"'{refutation.get('rebuttal')}'"
                )
        
        self.current_debate.consensus_points = consensus
        self.current_debate.disagreement_points = disagreement
        
        return {"consensus": consensus, "disagreement": disagreement}
    
    def _llm_analyze_debate(self, llm_client, bull, bear, bull_rebuttal):
        """使用 LLM 分析辩论，生成实质性共识和分歧"""
        try:
            prompt = f"""你是一位专业的投资分析师。请分析以下多空辩论，提取实质性的共识点和分歧点。

## Bull 观点
- 推荐: {bull.get('recommendation', 'N/A')}
- 置信度: {bull.get('confidence', 0):.2f}
- 看多理由:
{chr(10).join(f"  - [{p.get('category', 'general')}] {p.get('point', '')} (证据: {p.get('evidence', '')})" for p in bull.get('bullish_points', []))}
- 识别的风险: {', '.join(bull.get('risks_identified', [])) or '无'}

## Bear 观点
- 推荐: {bear.get('recommendation', 'N/A')}
- 置信度: {bear.get('confidence', 0):.2f}
- 看空理由:
{chr(10).join(f"  - [{p.get('category', 'general')}] {p.get('point', '')} (证据: {p.get('evidence', '')})" for p in bear.get('bearish_points', []))}
- 对 Bull 的反驳:
{chr(10).join(f"  - Bull: {r.get('bull_point', '')} → 反驳: {r.get('rebuttal', '')}" for r in bear.get('bull_points_refuted', []))}

## Bull 反驳轮
- 推荐: {bull_rebuttal.get('recommendation', 'N/A')}
- 置信度: {bull_rebuttal.get('confidence', 0):.2f}

请以 JSON 格式返回:
{{"consensus": ["共识点1", "共识点2", ...], "disagreement": ["分歧点1", "分歧点2", ...]}}

共识点应该是双方都认同的事实或判断，而非泛泛而谈。
分歧点应该是双方有实质对立的具体论点，而非推荐方向不同这种显而易见的结论。
每个点都应该具体、有信息量、对投资决策有参考价值。"""

            response = llm_client(prompt)
            import json
            result = json.loads(response)
            
            consensus = result.get("consensus", [])
            disagreement = result.get("disagreement", [])
            
            self.current_debate.consensus_points = consensus
            self.current_debate.disagreement_points = disagreement
            
            return {"consensus": consensus, "disagreement": disagreement}
        except Exception as e:
            print(f"  ⚠️ LLM 分析失败，回退到规则匹配: {e}")
            return self._rule_based_analyze_debate(bull, bear)
    
    def submit_trader_decision(self, decision):
        """提交 Trader Agent 决策"""
        if not self.current_debate:
            raise RuntimeError("No active debate.")
        
        assert decision.get("agent") == "trader", "Decision must be from Trader Agent"
        self.current_debate.trader_decision = decision
        print("[DebateProtocol] Trader 决策已提交：{}".format(decision.get('decision')))
    
    def submit_risk_approval(self, approval):
        """提交 Risk Agent 审批结果"""
        if not self.current_debate:
            raise RuntimeError("No active debate.")
        
        assert approval.get("agent") == "risk", "Approval must be from Risk Agent"
        self.current_debate.risk_approval = approval
        
        rec = approval.get("recommendation", "REJECT")
        print("[DebateProtocol] Risk 审批结果：{}".format(rec))
    
    def finalize(self, action, reason="", modified_action=None):
        """完成辩论"""
        if not self.current_debate:
            raise RuntimeError("No active debate.")
        
        self.current_debate.status = "completed"
        self.current_debate.final_action = {
            "action": action,
            "reason": reason,
            "modified_action": modified_action
        }
        
        self._save_debate_record()
        
        print("[DebateProtocol] 辩论完成：{}".format(self.current_debate.debate_id))
        
        record = self.current_debate
        self.current_debate = None
        return record
    
    def _save_debate_record(self):
        """保存辩论记录到文件"""
        if not self.current_debate:
            raise RuntimeError("No active debate.")
        
        filename = "{}.json".format(self.current_debate.debate_id)
        filepath = self.data_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.current_debate.to_json())
        
        print("[DebateProtocol] 辩论记录已保存：{}".format(filepath))
        return filepath
    
    def get_debate_summary(self, debate_id=None):
        """获取辩论摘要"""
        if debate_id:
            filepath = self.data_dir / "{}.json".format(debate_id)
            if not filepath.exists():
                return {"error": "Debate {} not found".format(debate_id)}
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        else:
            if not self.current_debate:
                return {"error": "No active debate"}
            return self.current_debate.to_dict()
