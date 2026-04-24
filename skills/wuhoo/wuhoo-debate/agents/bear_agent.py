#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bear Agent - 空头分析师

负责分析股票的风险，识别下跌理由。
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent


class BearAgent(BaseAgent):
    """
    空头分析师 Agent
    
    职责:
    - 分析因子数据、技术面、舆情、基本面的风险
    - 识别下跌理由和卖出信号
    - 反驳 Bull 的过度乐观观点
    """
    
    def __init__(
        self,
        prompt_path: Optional[str] = None,
        model: str = "qwen3.5-plus",
        api_key: Optional[str] = None
    ):
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent / "prompts" / "bear_analyst.md"
        
        super().__init__(
            name="bear",
            prompt_path=str(prompt_path),
            model=model,
            api_key=api_key
        )
    
    def analyze(
        self,
        symbol: str,
        factor_data: Optional[Dict] = None,
        technical_data: Optional[Dict] = None,
        sentiment_data: Optional[Dict] = None,
        fundamental_data: Optional[Dict] = None,
        bull_view: Optional[Dict] = None
    ) -> Dict:
        """
        分析股票，生成空头观点
        
        Args:
            symbol: 股票代码
            factor_data: 因子数据
            technical_data: 技术面数据
            sentiment_data: 舆情数据
            fundamental_data: 基本面数据
            bull_view: Bull Agent 观点 (用于反驳)
        
        Returns:
            Bear Agent 输出
        """
        input_text = self._build_input(
            symbol=symbol,
            factor_data=factor_data,
            technical_data=technical_data,
            sentiment_data=sentiment_data,
            fundamental_data=fundamental_data,
            bull_view=bull_view
        )
        
        response = self._call_llm(input_text)
        result = self._parse_json_output(response)
        
        result["symbol"] = symbol
        result["timestamp"] = datetime.now().isoformat()
        result["agent"] = "bear"
        
        return result
    
    def _build_input(
        self,
        symbol: str,
        factor_data: Optional[Dict],
        technical_data: Optional[Dict],
        sentiment_data: Optional[Dict],
        fundamental_data: Optional[Dict],
        bull_view: Optional[Dict]
    ) -> str:
        """构建输入文本"""
        lines = [f"请分析股票 {symbol} 的投资风险。\n"]
        
        # 如果有 Bull 观点，先列出
        if bull_view:
            lines.append("## Bull 的观点 (需要反驳)")
            lines.append(f"推荐：{bull_view.get('recommendation')}")
            lines.append(f"置信度：{bull_view.get('confidence')}")
            lines.append("看多理由:")
            for point in bull_view.get("bullish_points", []):
                lines.append(f"- [{point.get('category')}] {point.get('point')}")
                lines.append(f"  证据：{point.get('evidence')}")
            lines.append("")
        
        # 因子数据
        if factor_data:
            lines.append("## 因子数据 (QuantaAlpha)")
            lines.append(self._format_dict(factor_data))
            lines.append("")
        
        # 技术面数据
        if technical_data:
            lines.append("## 技术面数据")
            lines.append(self._format_dict(technical_data))
            lines.append("")
        
        # 舆情数据
        if sentiment_data:
            lines.append("## 舆情数据 (TrendRadar)")
            lines.append(self._format_dict(sentiment_data))
            lines.append("")
        
        # 基本面数据
        if fundamental_data:
            lines.append("## 基本面数据")
            lines.append(self._format_dict(fundamental_data))
            lines.append("")
        
        if bull_view:
            lines.append("请仔细分析 Bull 的观点，找出其中的漏洞或过度乐观的地方，并提供反面证据。")
        
        lines.append("请按照 Prompt 模板中的 JSON 格式输出你的分析结果。")
        
        return "\n".join(lines)
    
    def _format_dict(self, data: Dict, indent: int = 0) -> str:
        """格式化字典为字符串"""
        lines = []
        for key, value in data.items():
            prefix = "  " * indent
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._format_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}: {', '.join(map(str, value))}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        return "\n".join(lines)
    
    def analyze_risks(
        self,
        symbol: str,
        data: Dict
    ) -> Dict:
        """
        简化版：仅分析风险，不涉及 Bull 观点
        
        Args:
            symbol: 股票代码
            data: 综合数据
        
        Returns:
            Bear Agent 输出
        """
        return self.analyze(
            symbol=symbol,
            factor_data=data.get("factor_data"),
            technical_data=data.get("technical_data"),
            sentiment_data=data.get("sentiment_data"),
            fundamental_data=data.get("fundamental_data"),
            bull_view=None
        )


# 使用示例
if __name__ == "__main__":
    agent = BearAgent()
    
    bull_view = {
        "recommendation": "BUY",
        "confidence": 0.75,
        "bullish_points": [
            {"category": "factor", "point": "动量因子强势", "evidence": "评分 8.5/10"}
        ]
    }
    
    result = agent.analyze(
        symbol="600519.SH",
        factor_data={
            "momentum_score": 8.5,
            "volatility_score": 7.8  # 高波动率是风险
        },
        technical_data={
            "rsi": 78,  # 超买
            "macd": "divergence"  # 背离
        },
        bull_view=bull_view
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
