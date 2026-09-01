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
        risk_rules_path: Optional[str] = None,
        model: str = "deepseek-v4-pro",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        provider: str = "auto"
    ):
        import yaml
        
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent / "prompts" / "trader_decision.md"
        
        # 加载风控规则摘要
        risk_rules_summary = self._load_risk_rules_summary(risk_rules_path)
        
        # 读取 prompt 并注入风控规则
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_content = f.read()
        
        if risk_rules_summary:
            # 在 "## 决策原则" 之后注入风控规则约束
            risk_section = (
                "\n\n## 🔒 风控约束 (强制执行)\n"
                "以下风控规则必须严格遵守，违反将导致交易被拒绝：\n"
                f"{risk_rules_summary}\n"
            )
            # 注入到决策流程之后
            insert_marker = "## 输出要求"
            if insert_marker in prompt_content:
                prompt_content = prompt_content.replace(insert_marker, risk_section + insert_marker)
        
        # 写入临时 prompt 文件
        import tempfile
        temp_prompt = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8", dir=Path(prompt_path).parent)
        temp_prompt.write(prompt_content)
        temp_prompt.close()
        prompt_path = temp_prompt.name
        
        super().__init__(
            name="trader",
            prompt_path=str(prompt_path),
            model=model,
            api_key=api_key,
            api_base=api_base,
            provider=provider
        )
    
    @staticmethod
    def _load_risk_rules_summary(rules_path: Optional[str]) -> str:
        """加载风控规则并生成摘要"""
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "rules" / "risk_rules.yaml"
        
        path = Path(rules_path)
        if not path.exists():
            return ""
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f)
            
            lines = []
            
            # 仓位限制
            pl = rules.get("position_limits", {})
            lines.append(f"- 单票最大仓位: {pl.get('single_stock_max', 0.20)*100:.0f}%")
            lines.append(f"- 单行业最大仓位: {pl.get('single_industry_max', 0.40)*100:.0f}%")
            lines.append(f"- 最低现金比例: {pl.get('cash_min', 0.10)*100:.0f}%")
            
            # 分级仓位
            tiers = pl.get("tiers", [])
            if tiers:
                lines.append("- 分级仓位 (按置信度):")
                for t in tiers:
                    lines.append(f"  - 置信度≥{t['confidence_min']:.1f} → 最大仓位 {t['position_max']*100:.0f}%")
            
            # 止损
            sl = rules.get("stop_loss", {})
            lines.append(f"- 基础止损: {sl.get('base_stop_loss_pct', 0.08)*100:.0f}%")
            lines.append(f"- 绝对止损红线: {sl.get('hard_stop_loss_pct', 0.12)*100:.0f}%")
            
            # 风险收益比
            rr = rules.get("risk_reward", {})
            lines.append(f"- 最低风险收益比: {rr.get('min_ratio', 2.0):.1f}:1")
            lines.append(f"- 优选风险收益比: {rr.get('preferred_ratio', 3.0):.1f}:1")
            
            # 流动性
            liq = rules.get("liquidity", {})
            lines.append(f"- 最低日均成交: {liq.get('min_daily_turnover', 10000000):,.0f}")
            
            # 事件风险
            ev = rules.get("event_risk", {})
            lines.append(f"- 财报静默期: 财报前 {ev.get('earnings_blackout_days', 3)} 天限制交易")
            
            return "\n".join(lines)
        except Exception:
            return ""
    
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
            if isinstance(point, dict):
                lines.append(f"- [{point.get('category', '')}] {point.get('point', '')}")
                lines.append(f"  证据：{point.get('evidence', '')}")
                lines.append(f"  权重：{point.get('weight', 0):.1%}")
            else:
                lines.append(f"- {point}")
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
            if isinstance(point, dict):
                lines.append(f"- [{point.get('category', '')}] {point.get('point', '')}")
                lines.append(f"  证据：{point.get('evidence', '')}")
                lines.append(f"  权重：{point.get('weight', 0):.1%}")
            else:
                lines.append(f"- {point}")
        if bear_view.get("bull_points_refuted"):
            lines.append("对 Bull 的反驳:")
            for refutation in bear_view.get("bull_points_refuted", []):
                if isinstance(refutation, dict):
                    lines.append(f"- Bull: {refutation.get('bull_point', '')}")
                    lines.append(f"  反驳：{refutation.get('rebuttal', '')}")
                    lines.append(f"  证据：{refutation.get('evidence', '')}")
                else:
                    lines.append(f"- {refutation}")
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
        
        # 正确计算风险收益比 (RRR)
        if side == "buy":
            stop_loss_price = current_price * 0.92  # 8%止损
            take_profit_price = bull_target
            potential_profit = take_profit_price - current_price
            potential_loss = current_price - stop_loss_price
        else:
            stop_loss_price = current_price * 1.08
            take_profit_price = bear_target
            potential_profit = current_price - take_profit_price
            potential_loss = stop_loss_price - current_price
        
        # RRR = 潜在收益 / 潜在损失
        rrr = potential_profit / potential_loss if potential_loss > 0 else 0
        
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
                "stop_loss": stop_loss_price,
                "take_profit": take_profit_price
            },
            "reasoning": f"Bull 期望收益{bull_expected:.1%} vs Bear 期望收益{bear_expected:.1%}, RRR={rrr:.2f}",
            "bull_weight": bull_confidence / (bull_confidence + bear_confidence) if (bull_confidence + bear_confidence) > 0 else 0.5,
            "bear_weight": bear_confidence / (bull_confidence + bear_confidence) if (bull_confidence + bear_confidence) > 0 else 0.5,
            "risk_reward_ratio": round(rrr, 2),
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
