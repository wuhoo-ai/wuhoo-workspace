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
    
    def analyze_debate(self):
        """分析辩论，提取共识和分歧点"""
        if not self.current_debate:
            raise RuntimeError("No active debate.")
        
        bull = self.current_debate.bull_view or {}
        bear = self.current_debate.bear_view or {}
        
        consensus = []
        disagreement = []
        
        # 分析共识点
        if bull.get("stop_loss") and bear.get("stop_loss"):
            consensus.append("双方都认同需要设置止损")
        
        bull_conf = bull.get("confidence", 0)
        bear_conf = bear.get("confidence", 0)
        if abs(bull_conf - bear_conf) < 0.15:
            consensus.append("双方置信度接近 (Bull: {:.2f}, Bear: {:.2f})".format(bull_conf, bear_conf))
        
        # 分析分歧点
        if bull.get("recommendation") != bear.get("recommendation"):
            disagreement.append("推荐方向分歧：Bull 推荐{}, Bear 推荐{}".format(
                bull.get('recommendation'), bear.get('recommendation')
            ))
        
        bull_target = bull.get("target_price", 0)
        bear_target = bear.get("target_price", 0)
        if bull_target and bear_target:
            diff_pct = abs(bull_target - bear_target) / ((bull_target + bear_target) / 2)
            if diff_pct > 0.15:
                disagreement.append("目标价分歧较大：Bull 目标{}, Bear 目标{} (差异{:.1%})".format(
                    bull_target, bear_target, diff_pct
                ))
        
        self.current_debate.consensus_points = consensus
        self.current_debate.disagreement_points = disagreement
        
        return {"consensus": consensus, "disagreement": disagreement}
    
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
