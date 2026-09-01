"""TraderV2Agent — extends TraderAgent with quant stats injection."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from .trader_agent import TraderAgent


class TraderV2Agent(TraderAgent):
    """v2 Trader that includes quant stats in the decision context."""

    def __init__(self, **kwargs):
        if 'prompt_path' not in kwargs:
            kwargs['prompt_path'] = str(Path(__file__).parent.parent / 'prompts' / 'trader_v2.md')
        super().__init__(**kwargs)

    def make_decision(
        self,
        symbol: str,
        bull_view: Dict,
        bear_view: Dict,
        consensus_points: Optional[list] = None,
        disagreement_points: Optional[list] = None,
        quant_stats: Optional[Dict] = None,
    ) -> Dict:
        input_text = self._build_input_v2(
            symbol=symbol,
            bull_view=bull_view,
            bear_view=bear_view,
            consensus_points=consensus_points or [],
            disagreement_points=disagreement_points or [],
            quant_stats=quant_stats,
        )
        response = self._call_llm(input_text, max_tokens=16000)

        # JSON 解析重试（Trader v2 推理链长，容易非 JSON 输出）
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
                    response = self._call_llm(input_text, max_tokens=16000 + (attempt + 1) * 4000)
                continue
        else:
            result = {
                "decision": "HOLD",
                "P_up": 0.5,
                "edge": 0.0,
                "position_size": 0.0,
                "confidence": 0.3,
                "reasoning": f"JSON parse failed after {max_retries+1} attempts: {str(last_error)[:150]}",
                "bull_quality": 0,
                "bear_quality": 0,
            }

        result["symbol"] = symbol
        result["timestamp"] = datetime.now().isoformat()
        result["agent"] = "trader"
        return result

    def _build_input_v2(
        self, symbol, bull_view, bear_view,
        consensus_points, disagreement_points, quant_stats
    ):
        lines = [f"请基于统计底座+多空辩论，为股票 {symbol} 做出概率化交易决策。\n"]

        # ── Quant Stats (MUST come first — it's the anchor) ──
        if quant_stats:
            lines.append("## 📊 统计底座 (Pattern Backtest)")
            lines.append(f"5日胜率: {quant_stats.get('forward_5d_win_rate', 'N/A')}")
            lines.append(f"5日均收益: {quant_stats.get('forward_5d_avg_return', 'N/A')}%")
            lines.append(f"5日最大反弹: {quant_stats.get('forward_5d_max_up', 'N/A')}%")
            lines.append(f"5日最大下跌: {quant_stats.get('forward_5d_max_down', 'N/A')}%")
            lines.append(f"统计优势: {quant_stats.get('statistical_edge', 'N/A')} "
                         f"(edge={quant_stats.get('edge_magnitude', 'N/A')})")
            lines.append(f"样本量: {quant_stats.get('sample_size', 'N/A')} "
                         f"({quant_stats.get('sample_quality', 'N/A')} 质量)")
            lines.append(f"关键发现: {quant_stats.get('key_finding', '')}")
            if quant_stats.get('regime_note'):
                lines.append(f"市场状态细分: {quant_stats['regime_note']}")
            lines.append("")

        # ── Bull ──
        lines.append("## 🐂 Advocate Bull 观点")
        lines.append(f"推荐：{bull_view.get('recommendation')}")
        lines.append(f"置信度：{bull_view.get('confidence', 0):.2f}")
        lines.append("看多论点:")
        for point in bull_view.get("bullish_points", []):
            if isinstance(point, dict):
                lines.append(f"- [{point.get('category', '')}] {point.get('point', '')}")
                lines.append(f"  证据：{point.get('evidence', '')}")
                lines.append(f"  权重：{point.get('weight', 0):.0%}")
            else:
                lines.append(f"- {point}")
        if bull_view.get('statistical_upside'):
            lines.append(f"统计面支撑: {bull_view['statistical_upside']}")
        lines.append("")

        # ── Bear ──
        lines.append("## 🐻 Skeptic Bear 观点")
        lines.append(f"推荐：{bear_view.get('recommendation')}")
        lines.append(f"置信度：{bear_view.get('confidence', 0):.2f}")
        lines.append("核心风险:")
        for point in bear_view.get("bearish_points", []):
            if isinstance(point, dict):
                lines.append(f"- [{point.get('category', '')}] {point.get('point', '')}")
                lines.append(f"  证据：{point.get('evidence', '')}")
            else:
                lines.append(f"- {point}")
        if bear_view.get("bull_points_refuted"):
            lines.append("对 Bull 的逐条反驳:")
            for ref in bear_view.get("bull_points_refuted", []):
                if isinstance(ref, dict):
                    lines.append(f"- Bull论点: {ref.get('bull_point', '')}")
                    lines.append(f"  反驳: {ref.get('rebuttal', '')}")
                    lines.append(f"  判断: {ref.get('verdict', '')}")
        lines.append("")

        lines.append("请按照 trader_v2 prompt 的 5-step 决策框架，计算 P_up、edge、position，输出 JSON。")
        return "\n".join(lines)
