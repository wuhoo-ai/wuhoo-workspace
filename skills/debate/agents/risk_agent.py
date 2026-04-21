#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Risk Agent - 独立风控

负责独立审核交易计划，确保风险可控。
"""

import os
import yaml
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent


class RiskAgent(BaseAgent):
    """
    风险控制官 Agent
    
    职责:
    - 独立审核交易计划 (不受多空观点影响)
    - 检查止损、仓位、风险收益比等
    - 给出审批结果 (APPROVE/CONDITIONAL/REJECT)
    """
    
    def __init__(
        self,
        prompt_path: Optional[str] = None,
        rules_path: Optional[str] = None,
        model: str = "qwen3.5-plus",
        api_key: Optional[str] = None
    ):
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent / "prompts" / "risk_check.md"
        
        super().__init__(
            name="risk",
            prompt_path=str(prompt_path),
            model=model,
            api_key=api_key
        )
        
        # 加载风控规则
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "rules" / "risk_rules.yaml"
        
        self.rules = self._load_rules(str(rules_path))
    
    def _load_rules(self, rules_path: str) -> Dict:
        """加载风控规则"""
        path = Path(rules_path)
        if not path.exists():
            # 返回默认规则
            return self._get_default_rules()
        
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def _get_default_rules(self) -> Dict:
        """默认风控规则"""
        return {
            "position_limits": {
                "single_stock_max": 0.20,
                "single_industry_max": 0.40,
                "cash_min": 0.10
            },
            "stop_loss": {
                "max_stop_loss_pct": 0.08,
                "hard_stop_loss_pct": 0.10
            },
            "risk_reward": {
                "min_ratio": 2.0
            },
            "approval": {
                "auto_approve": {
                    "position_size_max": 0.05,
                    "risk_score_max": 0.40
                },
                "user_approval_required": [
                    "position_size > 0.10",
                    "risk_score > 0.60"
                ]
            }
        }
    
    def review(
        self,
        symbol: str,
        trader_decision: Dict,
        current_position: Optional[Dict] = None,
        market_data: Optional[Dict] = None
    ) -> Dict:
        """
        审核交易计划
        
        Args:
            symbol: 股票代码
            trader_decision: Trader Agent 决策
            current_position: 当前持仓 (可选)
            market_data: 市场数据 (可选)
        
        Returns:
            Risk Agent 审批结果
        """
        # 首先进行规则检查
        checks = self._perform_checks(
            trader_decision=trader_decision,
            current_position=current_position,
            market_data=market_data
        )
        
        # 计算风险评分
        risk_score = self._calculate_risk_score(checks)
        
        # 确定审批建议
        recommendation = self._determine_recommendation(checks, risk_score)
        
        # 构建审批结果
        result = {
            "agent": "risk",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "approved": recommendation != "REJECT",
            "conditions": self._generate_conditions(checks),
            "risk_score": round(risk_score, 2),
            "warnings": self._generate_warnings(checks, market_data),
            "checks": checks,
            "recommendation": recommendation
        }
        
        return result
    
    def _perform_checks(
        self,
        trader_decision: Dict,
        current_position: Optional[Dict],
        market_data: Optional[Dict]
    ) -> Dict:
        """执行各项检查"""
        action = trader_decision.get("action", {})
        position_size = trader_decision.get("position_size", 0)
        
        # 获取波动率数据
        volatility = None
        if market_data:
            volatility = market_data.get("volatility", market_data.get("volatility_20d"))
        
        # 止损检查 (动态调整)
        stop_loss_check = self._check_stop_loss(action, trader_decision, volatility)
        
        # 仓位检查
        position_check = self._check_position_size(position_size, current_position)
        
        # 风险收益比检查
        risk_reward_check = self._check_risk_reward(trader_decision)
        
        # 波动率检查
        volatility_check = self._check_volatility(market_data)
        
        # 流动性检查
        liquidity_check = self._check_liquidity(market_data)
        
        # 集中度检查
        concentration_check = self._check_concentration(current_position, market_data)
        
        return {
            "stop_loss": stop_loss_check,
            "position_size": position_check,
            "risk_reward": risk_reward_check,
            "volatility": volatility_check,
            "liquidity": liquidity_check,
            "concentration": concentration_check
        }
    
    def _check_stop_loss(self, action: Dict, decision: Dict, volatility: float = None) -> str:
        """
        止损检查 (支持动态调整)
        
        Args:
            action: 交易计划
            decision: Trader 决策
            volatility: 当前波动率 (可选)
        """
        stop_loss = action.get("stop_loss")
        side = action.get("side")
        
        if not stop_loss:
            return "fail"  # 没有止损位
        
        # 获取当前价格 (从止盈止损推算)
        take_profit = action.get("take_profit", 0)
        if side == "buy" and take_profit > 0:
            current_price = (stop_loss + take_profit) / 2
            stop_loss_pct = (current_price - stop_loss) / current_price
        else:
            stop_loss_pct = 0.08  # 默认假设
        
        # 动态止损：根据波动率调整
        max_allowed = self._get_dynamic_stop_loss_limit(volatility)
        hard_limit = self.rules.get("stop_loss", {}).get("hard_stop_loss_pct", 0.12)
        
        if stop_loss_pct > hard_limit:
            return "fail"
        elif stop_loss_pct > max_allowed:
            return "warn"
        
        return "pass"
    
    def _get_dynamic_stop_loss_limit(self, volatility: float = None) -> float:
        """
        根据波动率动态获取止损上限
        
        Args:
            volatility: 20 日年化波动率 (如 0.35 表示 35%)
        
        Returns:
            动态止损上限
        """
        vol_config = self.rules.get("stop_loss", {}).get("volatility_adjustment", {})
        
        if volatility is None:
            # 无波动率数据时使用基础值
            return self.rules.get("stop_loss", {}).get("base_stop_loss_pct", 0.08)
        
        low_threshold = vol_config.get("low_threshold", 0.25)
        high_threshold = vol_config.get("high_threshold", 0.50)
        
        if volatility < low_threshold:
            return vol_config.get("low_volatility", {}).get("stop_loss_max", 0.10)
        elif volatility > high_threshold:
            return vol_config.get("high_volatility", {}).get("stop_loss_max", 0.05)
        else:
            return vol_config.get("medium_volatility", {}).get("stop_loss_max", 0.08)
    
    def _check_position_size(self, position_size: float, current_position: Optional[Dict]) -> str:
        """仓位检查"""
        max_allowed = self.rules.get("position_limits", {}).get("single_stock_max", 0.20)
        
        if position_size > max_allowed:
            return "fail"
        elif position_size > max_allowed * 0.75:
            return "warn"
        else:
            return "pass"
    
    def _check_risk_reward(self, decision: Dict) -> str:
        """风险收益比检查"""
        ratio = decision.get("risk_reward_ratio", 0)
        min_required = self.rules.get("risk_reward", {}).get("min_ratio", 2.0)
        
        if ratio < 1.5:
            return "fail"
        elif ratio < min_required:
            return "warn"
        else:
            return "pass"
    
    def _check_volatility(self, market_data: Optional[Dict]) -> str:
        """波动率检查"""
        if not market_data:
            return "pass"  # 无数据时默认通过
        
        volatility = market_data.get("volatility", 0)
        high_threshold = self.rules.get("volatility", {}).get("high_threshold", 0.60)
        
        if volatility > high_threshold:
            return "warn"
        else:
            return "pass"
    
    def _check_liquidity(self, market_data: Optional[Dict]) -> str:
        """流动性检查"""
        if not market_data:
            return "pass"
        
        daily_turnover = market_data.get("daily_turnover", 0)
        min_required = self.rules.get("liquidity", {}).get("min_daily_turnover", 10000000)
        
        if daily_turnover < min_required * 0.5:
            return "fail"
        elif daily_turnover < min_required:
            return "warn"
        else:
            return "pass"
    
    def _check_concentration(self, current_position: Optional[Dict], market_data: Optional[Dict]) -> str:
        """集中度检查"""
        if not current_position:
            return "pass"
        
        # 简化实现：检查行业集中度
        industry_exposure = current_position.get("industry_exposure", 0)
        max_allowed = self.rules.get("concentration", {}).get("max_industry_exposure", 0.40)
        
        if industry_exposure > max_allowed:
            return "warn"
        else:
            return "pass"
    
    def _calculate_risk_score(self, checks: Dict) -> float:
        """计算风险评分"""
        weights = self.rules.get("risk_score_weights", {
            "stop_loss_distance": 0.20,
            "position_size": 0.25,
            "risk_reward": 0.20,
            "volatility": 0.15,
            "liquidity": 0.15,
            "concentration": 0.05
        })
        
        score = 0.0
        
        # 根据检查结果计算分数
        score_mapping = {"pass": 0.0, "warn": 0.5, "fail": 1.0}
        
        score += score_mapping.get(checks.get("stop_loss", "pass"), 0) * weights.get("stop_loss_distance", 0.20)
        score += score_mapping.get(checks.get("position_size", "pass"), 0) * weights.get("position_size", 0.25)
        score += score_mapping.get(checks.get("risk_reward", "pass"), 0) * weights.get("risk_reward", 0.20)
        score += score_mapping.get(checks.get("volatility", "pass"), 0) * weights.get("volatility", 0.15)
        score += score_mapping.get(checks.get("liquidity", "pass"), 0) * weights.get("liquidity", 0.15)
        score += score_mapping.get(checks.get("concentration", "pass"), 0) * weights.get("concentration", 0.05)
        
        return min(1.0, score)
    
    def _determine_recommendation(self, checks: Dict, risk_score: float) -> str:
        """确定审批建议"""
        # 有任何 fail → REJECT
        if any(v == "fail" for v in checks.values()):
            return "REJECT"
        
        # 风险评分过高 → REJECT
        if risk_score > 0.7:
            return "REJECT"
        
        # 有 warn 或风险评分中等 → CONDITIONAL
        if any(v == "warn" for v in checks.values()) or risk_score > 0.5:
            return "CONDITIONAL"
        
        # 自动审批条件
        auto_approve = self.rules.get("approval", {}).get("auto_approve", {})
        if risk_score <= auto_approve.get("risk_score_max", 0.4):
            return "APPROVE"
        
        return "CONDITIONAL"
    
    def _generate_conditions(self, checks: Dict) -> list:
        """生成条件列表"""
        conditions = []
        
        if checks.get("position_size") == "warn":
            conditions.append("建议降低仓位至 10% 以下")
        
        if checks.get("stop_loss") == "warn":
            conditions.append("建议收紧止损至 5% 以内")
        
        if checks.get("risk_reward") == "warn":
            conditions.append("风险收益比不足，建议重新评估")
        
        if checks.get("volatility") == "warn":
            conditions.append("近期波动率较高，建议降低仓位")
        
        return conditions
    
    def _generate_warnings(self, checks: Dict, market_data: Optional[Dict]) -> list:
        """生成警告列表"""
        warnings = []
        
        if checks.get("volatility") in ["warn", "fail"]:
            warnings.append("近期波动率有所上升")
        
        if checks.get("liquidity") in ["warn", "fail"]:
            warnings.append("流动性不足，可能存在交易困难")
        
        if market_data and market_data.get("earnings_soon"):
            warnings.append("接近财报发布日")
        
        return warnings


# 使用示例
if __name__ == "__main__":
    agent = RiskAgent()
    
    trader_decision = {
        "decision": "BUY",
        "confidence": 0.60,
        "position_size": 0.10,
        "risk_reward_ratio": 2.5,
        "action": {
            "side": "buy",
            "stop_loss": 1350,
            "take_profit": 1500
        }
    }
    
    result = agent.review(
        symbol="600519.SH",
        trader_decision=trader_decision,
        market_data={
            "volatility": 0.45,
            "daily_turnover": 50000000
        }
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
