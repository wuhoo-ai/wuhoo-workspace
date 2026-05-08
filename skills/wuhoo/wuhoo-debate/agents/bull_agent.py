#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bull Agent - 多头分析师

负责分析股票的上涨理由，给出买入建议。
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent


class BullAgent(BaseAgent):
    """
    多头分析师 Agent
    
    职责:
    - 分析因子数据、技术面、舆情、基本面
    - 识别上涨理由和买入机会
    - 给出目标价、止损位和仓位建议
    """
    
    def __init__(
        self,
        prompt_path: Optional[str] = None,
        model: str = "deepseek-v4-pro",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        provider: str = "auto"
    ):
        # 默认 Prompt 路径
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent / "prompts" / "bull_analyst.md"
        
        super().__init__(
            name="bull",
            prompt_path=str(prompt_path),
            model=model,
            api_key=api_key,
            api_base=api_base,
            provider=provider
        )
    
    def analyze(
        self,
        symbol: str,
        factor_data: Optional[Dict] = None,
        technical_data: Optional[Dict] = None,
        sentiment_data: Optional[Dict] = None,
        fundamental_data: Optional[Dict] = None
    ) -> Dict:
        """
        分析股票，生成多头观点
        
        Args:
            symbol: 股票代码
            factor_data: 因子数据 (QuantaAlpha)
            technical_data: 技术面数据 (akshare)
            sentiment_data: 舆情数据 (TrendRadar)
            fundamental_data: 基本面数据
        
        Returns:
            Bull Agent 输出 (JSON 格式)
        """
        # 构建输入数据
        input_text = self._build_input(
            symbol=symbol,
            factor_data=factor_data,
            technical_data=technical_data,
            sentiment_data=sentiment_data,
            fundamental_data=fundamental_data
        )
        
        # 调用 LLM
        response = self._call_llm(input_text)
        
        # 解析输出
        result = self._parse_json_output(response)
        
        # 添加元数据
        result["symbol"] = symbol
        result["timestamp"] = datetime.now().isoformat()
        result["agent"] = "bull"
        
        return result
    
    def _build_input(
        self,
        symbol: str,
        factor_data: Optional[Dict],
        technical_data: Optional[Dict],
        sentiment_data: Optional[Dict],
        fundamental_data: Optional[Dict]
    ) -> str:
        """构建输入文本"""
        lines = [f"请分析股票 {symbol} 的投资机会。\n"]
        
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
    
    def analyze_with_context(
        self,
        symbol: str,
        data: Dict,
        bear_view: Optional[Dict] = None
    ) -> Dict:
        """
        带上下文的分析 (可选：接收 Bear 观点进行反驳)
        
        Args:
            symbol: 股票代码
            data: 综合数据
            bear_view: Bear Agent 观点 (可选，用于反驳)
        
        Returns:
            Bull Agent 输出
        """
        # 如果有 Bear 观点，构建反驳输入
        if bear_view:
            input_text = self._build_rebuttal_input(symbol, data, bear_view)
        else:
            input_text = self._build_input(
                symbol=symbol,
                factor_data=data.get("factor_data"),
                technical_data=data.get("technical_data"),
                sentiment_data=data.get("sentiment_data"),
                fundamental_data=data.get("fundamental_data")
            )
        
        response = self._call_llm(input_text, max_tokens=10000)
        
        # 带重试的 JSON 解析（Bull Rebuttal 也可能截断）
        max_retries = 2
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                result = self._parse_json_output(response)
                break
            except ValueError as e:
                last_error = e
                if attempt < max_retries:
                    import time as time_mod
                    time_mod.sleep(1)
                    response = self._call_llm(input_text, max_tokens=10000 + (attempt + 1) * 4000)
                continue
        else:
            result = {
                "recommendation": "HOLD",
                "confidence": 0.50,
                "target_price": 0,
                "time_horizon": "1M",
                "key_points": [f"JSON parse failed after {max_retries+1} attempts: {str(last_error)[:100]}"],
                "bullish_points": [],
                "bearish_points": [],
                "stop_loss": 0,
                "position_suggestion": 0.0,
            }
        
        result["symbol"] = symbol
        result["timestamp"] = datetime.now().isoformat()
        result["agent"] = "bull"
        
        return result
    
    def _build_rebuttal_input(
        self,
        symbol: str,
        data: Dict,
        bear_view: Dict
    ) -> str:
        """构建反驳输入"""
        lines = [f"请分析股票 {symbol}，并回应 Bear 的观点。\n"]
        
        # 原始数据
        lines.append("## 市场数据")
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"### {key}")
                lines.append(self._format_dict(value))
        lines.append("")
        
        # Bear 观点
        lines.append("## Bear 的观点")
        lines.append(f"推荐：{bear_view.get('recommendation')}")
        lines.append(f"置信度：{bear_view.get('confidence')}")
        lines.append("看空理由:")
        for point in bear_view.get("bearish_points", []):
            if isinstance(point, dict):
                lines.append(f"- {point.get('point', '')} (证据：{point.get('evidence', '')})")
            else:
                lines.append(f"- {point}")
        lines.append("")
        
        lines.append("请分析 Bear 的观点，指出其中的问题或过度悲观的地方，并坚持你的多头立场 (如果数据支持)。")
        lines.append("按照 JSON 格式输出，包含对 Bear 观点的反驳。")
        
        return "\n".join(lines)


# 使用示例
if __name__ == "__main__":
    # 需要设置 BAILIAN_API_KEY 环境变量
    agent = BullAgent()
    
    result = agent.analyze(
        symbol="600519.SH",
        factor_data={
            "momentum_score": 8.5,
            "volatility_score": 6.2,
            "turnover_score": 7.1
        },
        technical_data={
            "macd": "golden_cross",
            "rsi": 58,
            "trend": "uptrend"
        }
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
