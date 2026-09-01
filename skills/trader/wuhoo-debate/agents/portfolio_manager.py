#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio Manager - 投资组合经理

最终审批层，负责：
- 大额交易用户确认
- 组合层面风险控制
- 与 AI-Trader 集成执行交易
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent


class PortfolioManager(BaseAgent):
    """
    投资组合经理
    
    职责:
    - 最终审批交易决策
    - 大额交易需要用户确认
    - 组合层面风险控制
    - 与 AI-Trader 集成
    """
    
    def __init__(
        self,
        prompt_path: Optional[str] = None,
        model: str = "qwen3.5-plus",
        api_key: Optional[str] = None
    ):
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent / "prompts" / "portfolio_manager.md"
        
        # 如果 Prompt 文件不存在，使用默认逻辑
        self.has_prompt = Path(prompt_path).exists() if prompt_path else False
        
        super().__init__(
            name="portfolio_manager",
            prompt_path=str(prompt_path) if self.has_prompt else "",
            model=model,
            api_key=api_key
        )
        
        # 组合状态
        self.portfolio_state = {
            "total_value": 100000,  # 总资金 10 万
            "cash": 50000,          # 现金 5 万
            "positions": {},        # 持仓
            "industry_exposure": {} # 行业暴露
        }
    
    def review_decision(
        self,
        symbol: str,
        trader_decision: Dict,
        risk_approval: Dict,
        debate_record: Optional[Dict] = None
    ) -> Dict:
        """
        审核交易决策
        
        Args:
            symbol: 股票代码
            trader_decision: Trader Agent 决策
            risk_approval: Risk Agent 审批
            debate_record: 完整辩论记录 (可选)
        
        Returns:
            最终审批结果
        """
        # 检查 Risk 审批
        if risk_approval.get("recommendation") == "REJECT":
            return self._create_result(
                symbol=symbol,
                action="reject",
                reason="Risk Agent 已拒绝交易",
                requires_user_approval=False
            )
        
        # 获取交易详情
        position_size = trader_decision.get("position_size", 0)
        decision = trader_decision.get("decision", "HOLD")
        
        # 计算实际仓位金额
        position_value = self.portfolio_state["total_value"] * position_size
        
        # 审批规则
        requires_user_approval = (
            position_size > 0.10 or  # 仓位>10%
            risk_approval.get("recommendation") == "CONDITIONAL" or  # 有条件通过
            position_value > 20000  # 金额>2 万
        )
        
        # 检查组合风险
        portfolio_check = self._check_portfolio_risk(symbol, position_size)
        
        if not portfolio_check["passed"]:
            return self._create_result(
                symbol=symbol,
                action="reject",
                reason="组合风险检查未通过：" + portfolio_check["reason"],
                requires_user_approval=False
            )
        
        # 生成审批结果
        if requires_user_approval:
            action = "pending_user_approval"
            reason = "大额交易/有条件通过，需要用户确认"
        else:
            action = "approve"
            reason = "审批通过，可以执行"
        
        return self._create_result(
            symbol=symbol,
            action=action,
            reason=reason,
            requires_user_approval=requires_user_approval,
            position_value=position_value
        )
    
    def _create_result(
        self,
        symbol: str,
        action: str,
        reason: str,
        requires_user_approval: bool = False,
        position_value: float = 0
    ) -> Dict:
        """创建审批结果"""
        return {
            "agent": "portfolio_manager",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "reason": reason,
            "requires_user_approval": requires_user_approval,
            "position_value": position_value,
            "portfolio_impact": self._calculate_portfolio_impact(symbol, position_value)
        }
    
    def _check_portfolio_risk(self, symbol: str, position_size: float) -> Dict:
        """检查组合风险"""
        # 检查单票集中度
        current_position = self.portfolio_state["positions"].get(symbol, 0)
        if current_position + position_size > 0.20:
            return {
                "passed": False,
                "reason": "单票仓位超过 20% 限制"
            }
        
        # 检查现金是否充足
        required_cash = self.portfolio_state["total_value"] * position_size
        if required_cash > self.portfolio_state["cash"]:
            return {
                "passed": False,
                "reason": "现金不足"
            }
        
        return {"passed": True, "reason": ""}
    
    def _calculate_portfolio_impact(self, symbol: str, position_value: float) -> Dict:
        """计算对组合的影响"""
        total = self.portfolio_state["total_value"]
        new_position = position_value / total if total > 0 else 0
        
        return {
            "new_position_pct": new_position,
            "remaining_cash_pct": (self.portfolio_state["cash"] - position_value) / total if total > 0 else 0,
            "current_positions": len(self.portfolio_state["positions"])
        }
    
    def update_portfolio(self, symbol: str, action: str, quantity: int, price: float):
        """
        更新组合状态
        
        Args:
            symbol: 股票代码
            action: buy/sell
            quantity: 数量
            price: 价格
        """
        value = quantity * price
        
        if action == "buy":
            self.portfolio_state["cash"] -= value
            current = self.portfolio_state["positions"].get(symbol, 0)
            self.portfolio_state["positions"][symbol] = current + value
        elif action == "sell":
            self.portfolio_state["cash"] += value
            current = self.portfolio_state["positions"].get(symbol, 0)
            self.portfolio_state["positions"][symbol] = max(0, current - value)
    
    def get_portfolio_summary(self) -> Dict:
        """获取组合摘要"""
        total_positions = sum(self.portfolio_state["positions"].values())
        
        return {
            "total_value": self.portfolio_state["total_value"],
            "cash": self.portfolio_state["cash"],
            "cash_pct": self.portfolio_state["cash"] / self.portfolio_state["total_value"],
            "positions_value": total_positions,
            "positions_count": len(self.portfolio_state["positions"]),
            "positions": self.portfolio_state["positions"]
        }
    
    def request_user_approval(self, debate_record: Dict) -> Dict:
        """
        生成用户确认请求
        
        Args:
            debate_record: 完整辩论记录
        
        Returns:
            用户确认请求数据
        """
        bull = debate_record.get("bull_view", {})
        bear = debate_record.get("bear_view", {})
        trader = debate_record.get("trader_decision", {})
        risk = debate_record.get("risk_approval", {})
        
        return {
            "type": "user_approval_request",
            "debate_id": debate_record.get("debate_id"),
            "symbol": debate_record.get("symbol"),
            "summary": {
                "bull_view": {
                    "recommendation": bull.get("recommendation"),
                    "confidence": bull.get("confidence"),
                    "key_points": bull.get("bullish_points", [])[:2]  # 前 2 个要点
                },
                "bear_view": {
                    "recommendation": bear.get("recommendation"),
                    "confidence": bear.get("confidence"),
                    "key_points": bear.get("bearish_points", [])[:2]
                },
                "trader_decision": {
                    "decision": trader.get("decision"),
                    "position_size": trader.get("position_size"),
                    "reasoning": trader.get("reasoning")
                },
                "risk_approval": {
                    "recommendation": risk.get("recommendation"),
                    "risk_score": risk.get("risk_score"),
                    "conditions": risk.get("conditions", [])
                }
            },
            "action_required": {
                "action": trader.get("action", {}).get("side"),
                "quantity": trader.get("action", {}).get("quantity"),
                "limit_price": trader.get("action", {}).get("limit_price"),
                "stop_loss": trader.get("action", {}).get("stop_loss")
            },
            "timestamp": datetime.now().isoformat()
        }


# 使用示例
if __name__ == "__main__":
    pm = PortfolioManager()
    
    # 模拟审批
    trader_decision = {
        "decision": "BUY",
        "position_size": 0.15,
        "action": {
            "side": "buy",
            "quantity": 100,
            "limit_price": 1380
        }
    }
    
    risk_approval = {
        "recommendation": "CONDITIONAL",
        "risk_score": 0.45,
        "conditions": ["降低仓位至 10%"]
    }
    
    result = pm.review_decision(
        symbol="600519.SH",
        trader_decision=trader_decision,
        risk_approval=risk_approval
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n组合摘要:")
    print(json.dumps(pm.get_portfolio_summary(), indent=2, ensure_ascii=False))
