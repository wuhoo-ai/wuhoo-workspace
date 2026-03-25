#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trader Agent - 交易决策者

负责综合多空双方观点，做出最终交易决策。
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent


class TraderAgent(BaseAgent):
    """
    交易决策者 Agent
    
    职责:
    - 接收 Bull 和 Bear 的观点
    - 评估双方论点的说服力
    - 识别共识和分歧
    - 做出最终交易决策
    """
    
    def __init__(
        self,
        prompt_path: Optional[str] = None,
        model: str = "qwen3.5-plus",
        api_key: Optional[str] = None
    ):
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent / "prompts" / "trader_decision.md"
        
        super().__init__(
            name="trader",
            prompt_path=str(prompt_path),
            model=model,
            api_key=api_key
        )
    
    def make_decision(
        self,
        symbol: str,
        bull_view: Dict,
        bear_view: Dict,
        consensus_points: Optional[list] = None,
        disagreement_points: Optional[list] = None
    ) -> Dict:
        """
        基于多空辩论做出交易决策
        
        Args:
            symbol: 股票代码
            bull_view: Bull Agent 观点
            bear_view: Bear Agent 观点
            consensus_points: 共识点列表
            disagreement_points: 分歧点列表
        
        Returns:
            Trader Agent 决策
        """
        input_text = self._build_input(
            symbol=symbol,
            bull_view=bull_view,
            bear_view=bear_view,
            consensus_points=consensus_points or [],
            disagreement_points=disagreement_points or []
        )
        
        response = self._call_llm(input_text)
        result = self._parse_json_output(response)
        
        result["symbol"] = symbol
        result["timestamp"] = datetime.now().isoformat()
        result["agent"] = "trader"
        
        return result
    
    def _build_input(
        self,
        symbol: str,
        bull_view: Dict,
        bear_view: Dict,
        consensus_points: list,
        disagreement_points: list
    ) -> str:
        """构建输入文本"""
        lines = [f"请基于多空辩论，为股票 {symbol} 做出交易决策。\n"]
        
        # Bull 观点
        lines.append("## 🐂 Bull 观点")
        lines.append(f"推荐：{bull_view.get('recommendation')}")
        lines.append(f"置信度：{bull_view.get('confidence', 0):.2f}")
        lines.append(f"目标价：{bull_view.get('target_price')}")
        lines.append(f"止损位：{bull_view.get('stop_loss')}")
        lines.append(f"仓位建议：{bull_view.get('position_suggestion', 0):.1%}")
        lines.append("看多理由:")
        for point in bull_view.get("bullish_points", []):
            lines.append(f"- [{point.get('category')}] {point.get('point')}")
            lines.append(f"  证据：{point.get('evidence')}")
            lines.append(f"  权重：{point.get('weight', 0):.1%}")
        if bull_view.get("risks_identified"):
            lines.append("识别的风险:")
            for risk in bull_view.get("risks_identified"):
                lines.append(f"- {risk}")
        lines.append("")
        
        # Bear 观点
        lines.append("## 🐻 Bear 观点")
        lines.append(f"推荐：{bear_view.get('recommendation')}")
        lines.append(f"置信度：{bear_view.get('confidence', 0):.2f}")
        lines.append(f"目标价：{bear_view.get('target_price')}")
        lines.append(f"止损位：{bear_view.get('stop_loss')}")
        lines.append("看空理由:")
        for point in bear_view.get("bearish_points", []):
            lines.append(f"- [{point.get('category')}] {point.get('point')}")
            lines.append(f"  证据：{point.get('evidence')}")
            lines.append(f"  权重：{point.get('weight', 0):.1%}")
        if bear_view.get("bull_points_refuted"):
            lines.append("对 Bull 的反驳:")
            for refutation in bear_view.get("bull_points_refuted"):
                lines.append(f"- Bull: {refutation.get('bull_point')}")
                lines.append(f"  反驳：{refutation.get('rebuttal')}")
                lines.append(f"  证据：{refutation.get('evidence')}")
        lines.append("")
        
        # 共识和分歧
        if consensus_points:
            lines.append("## ✅ 共识点")
            for point in consensus_points:
                lines.append(f"- {point}")
            lines.append("")
        
        if disagreement_points:
            lines.append("## ⚔️ 分歧点")
            for point in disagreement_points:
                lines.append(f"- {point}")
            lines.append("")
        
        lines.append("请综合评估双方观点，做出理性的交易决策。")
        lines.append("按照 JSON 格式输出，包含决策理由、仓位大小、止损/止盈位。")
        
        return "\n".join(lines)
    
    def quick_decision(
        self,
        symbol: str,
        bull_confidence: float,
        bear_confidence: float,
        current_price: float,
        bull_target: float,
        bear_target: float
    ) -> Dict:
        """
        快速决策 (简化版，仅基于关键指标)
        
        Args:
            symbol: 股票代码
            bull_confidence: Bull 置信度
            bear_confidence: Bear 置信度
            current_price: 当前价格
            bull_target: Bull 目标价
            bear_target: Bear 目标价
        
        Returns:
            简化的交易决策
        """
        # 简单逻辑：比较置信度和风险收益比
        bull_upside = (bull_target - current_price) / current_price
        bear_downside = (current_price - bear_target) / current_price
        
        # 计算期望收益
        bull_expected = bull_confidence * bull_upside
        bear_expected = bear_confidence * bear_downside
        
        # 决策
        if bull_expected > bear_expected * 1.5:  # Bull 期望收益显著高于 Bear
            decision = "BUY"
            side = "buy"
            position = min(0.15, bull_confidence * 0.2)
        elif bear_expected > bull_expected * 1.5:  # Bear 期望收益显著高于 Bull
            decision = "SELL"
            side = "sell"
            position = 0  # A 股不能做空
        else:
            decision = "HOLD"
            side = "hold"
            position = 0
        
        return {
            "agent": "trader",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "confidence": max(bull_confidence, bear_confidence) if decision != "HOLD" else 0.5,
            "action": {
                "symbol": symbol,
                "side": side,
                "quantity": 0,
                "order_type": "market",
                "stop_loss": current_price * 0.92 if side == "buy" else current_price * 1.08,
                "take_profit": bull_target if side == "buy" else bear_target
            },
            "reasoning": f"Bull 期望收益{bull_expected:.1%} vs Bear 期望收益{bear_expected:.1%}",
            "bull_weight": bull_confidence / (bull_confidence + bear_confidence) if (bull_confidence + bear_confidence) > 0 else 0.5,
            "bear_weight": bear_confidence / (bull_confidence + bear_confidence) if (bull_confidence + bear_confidence) > 0 else 0.5,
            "risk_reward_ratio": bull_upside / (bear_downside + 0.01) if side == "buy" else bear_downside / (bull_upside + 0.01),
            "position_size": position
        }


# 使用示例
if __name__ == "__main__":
    agent = TraderAgent()
    
    bull_view = {
        "recommendation": "BUY",
        "confidence": 0.75,
        "target_price": 1500,
        "stop_loss": 1350,
        "position_suggestion": 0.15,
        "bullish_points": [
            {"category": "factor", "point": "动量因子强势", "evidence": "评分 8.5/10", "weight": 0.35}
        ]
    }
    
    bear_view = {
        "recommendation": "SELL",
        "confidence": 0.65,
        "target_price": 1200,
        "stop_loss": 1450,
        "bearish_points": [
            {"category": "technical", "point": "RSI 超买", "evidence": "RSI=78", "weight": 0.35}
        ],
        "bull_points_refuted": [
            {"bull_point": "动量因子强势", "rebuttal": "可能已见顶", "evidence": "历史数据"}
        ]
    }
    
    result = agent.make_decision(
        symbol="600519.SH",
        bull_view=bull_view,
        bear_view=bear_view,
        consensus_points=["双方都认同需要设置止损"],
        disagreement_points=["动量因子是否已见顶"]
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
