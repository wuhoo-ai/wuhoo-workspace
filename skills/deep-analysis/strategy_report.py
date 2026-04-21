#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow B - 单股深度分析与决策建议报告

流程:
输入股票代码 → 基本面分析 → 技术面分析 → 舆情分析 → 多空辩论 → 生成决策建议报告

报告章节:
1. 商业模式分析
2. 财务健康分析
3. 盈利能力分析
4. 估值分析
5. 技术面分析
6. 多空辩论
7. 决策建议

用法:
    python workflow_b_strategy_report.py --symbol 600519.SH
    python workflow_b_strategy_report.py --symbol 600519.SH --name 贵州茅台
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# 加载环境变量
env_file = Path.home() / '.openclaw' / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value

# 添加 debate 模块路径
debate_path = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'debate'
sys.path.insert(0, str(debate_path / 'adapters'))

from adapters.data_aggregator import DataAggregator


class WorkflowBHandler:
    """Workflow B 执行处理器"""

    def __init__(self, symbol: str, company_name: Optional[str] = None):
        self.symbol = symbol
        self.company_name = company_name
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 输出目录
        safe_symbol = symbol.replace('.', '_')
        self.output_dir = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'trade' / "data" / "workflow_b" / f"{safe_symbol}_{self.date}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 数据存储
        self.all_data: Dict = {}

        print("=" * 60)
        print("Workflow B - 单股深度分析")
        print(f"股票：{symbol}")
        if company_name:
            print(f"公司：{company_name}")
        print(f"日期：{self.date}")
        print("=" * 60)

    def step1_load_data(self) -> Dict:
        """Step 1: 加载全部数据（基本面 + 技术面 + 舆情）"""
        print("\n" + "=" * 60)
        print("Step 1: 加载数据")
        print("=" * 60)

        aggregator = DataAggregator()
        self.all_data = aggregator.get_all_data(self.symbol, self.company_name)

        quality = self.all_data.get('data_quality', {})
        print(f"  因子数据：{quality.get('factor', 'unknown')}")
        print(f"  技术面：{quality.get('technical', 'unknown')}")
        print(f"  基本面：{quality.get('fundamental', 'unknown')}")
        print(f"  舆情：{quality.get('sentiment', 'unknown')}")

        if quality.get('overall') == 'degraded':
            print(f"  ⚠️ {quality.get('warning', '')}")

        step_result = {
            "success": True,
            "data_quality": quality,
            "timestamp": datetime.now().isoformat()
        }

        with open(self.output_dir / "01_data_loaded.json", 'w', encoding='utf-8') as f:
            json.dump(step_result, f, ensure_ascii=False, indent=2)

        return step_result

    def step2_run_debate(self) -> Dict:
        """Step 2: 执行多空辩论"""
        print("\n" + "=" * 60)
        print("Step 2: 多空辩论")
        print("=" * 60)

        try:
            from run_debate import run_full_debate

            debate_result = run_full_debate(
                self.symbol,
                self.company_name,
                output_dir=str(self.output_dir),
                use_real_data=True
            )

            print(f"  最终动作：{debate_result.get('final_action', {}).get('action', 'unknown')}")

            self.all_data['debate_result'] = debate_result
            return debate_result

        except ImportError:
            print("  ⚠️ Debate 模块不可用，使用简化分析")
            return self._quick_debate_analysis()
        except Exception as e:
            print(f"  ⚠️ 辩论执行出错：{e}，使用简化分析")
            return self._quick_debate_analysis()

    def _quick_debate_analysis(self) -> Dict:
        """简化版多空分析（当完整辩论不可用时）"""
        fundamental = self.all_data.get('fundamental_data', {})
        technical = self.all_data.get('technical_data', {})
        sentiment = self.all_data.get('sentiment_data', {})

        pe = fundamental.get('pe', 0)
        roe = fundamental.get('roe', 0)
        rsi = technical.get('rsi', 50)
        trend = technical.get('trend', 'sideways')
        sentiment_score = sentiment.get('sentiment_score', 0)

        bull_points = []
        bear_points = []

        # 基本面多空点
        if pe and 0 < pe < 20:
            bull_points.append(f"市盈率 {pe:.1f}x，估值合理")
        elif pe and pe > 40:
            bear_points.append(f"市盈率 {pe:.1f}x，估值偏高")

        if roe and roe > 0.15:
            bull_points.append(f"ROE {roe:.1%}，盈利能力强")
        elif roe and roe < 0.05:
            bear_points.append(f"ROE {roe:.1%}，盈利能力弱")

        # 技术面多空点
        if trend == 'uptrend':
            bull_points.append("技术面处于上升趋势")
        elif trend == 'downtrend':
            bear_points.append("技术面处于下降趋势")

        if rsi < 30:
            bull_points.append(f"RSI {rsi:.1f}，超卖反弹机会")
        elif rsi > 70:
            bear_points.append(f"RSI {rsi:.1f}，超买回调风险")

        # 舆情多空点
        if sentiment_score > 0.2:
            bull_points.append("舆情偏正面")
        elif sentiment_score < -0.2:
            bear_points.append("舆情偏负面")

        # 综合判断
        bull_score = len(bull_points)
        bear_score = len(bear_points)

        if bull_score > bear_score:
            recommendation = "看多"
            confidence = 50 + (bull_score - bear_score) * 10
        elif bear_score > bull_score:
            recommendation = "看空"
            confidence = 50 + (bear_score - bull_score) * 10
        else:
            recommendation = "中性"
            confidence = 50

        return {
            "bull_points": bull_points,
            "bear_points": bear_points,
            "recommendation": recommendation,
            "confidence": min(max(confidence, 30), 90),
            "method": "quick_analysis",
            "final_action": {"action": "watch"},
            "trader_decision": {"decision": "HOLD"},
            "risk_approval": {"recommendation": "CONDITIONAL" if bull_score == bear_score else "APPROVE"},
            "data_quality": self.all_data.get('data_quality', {})
        }

    def step3_generate_report(self, debate_result: Dict) -> str:
        """Step 3: 生成决策建议报告"""
        print("\n" + "=" * 60)
        print("Step 3: 生成决策建议报告")
        print("=" * 60)

        fundamental = self.all_data.get('fundamental_data', {})
        technical = self.all_data.get('technical_data', {})
        sentiment = self.all_data.get('sentiment_data', {})
        factor = self.all_data.get('factor_data', {})

        # === 报告正文 ===
        report = f"""# 📊 个股深度分析报告

**股票代码**: {self.symbol}
**公司名称**: {self.company_name or '待确认'}
**分析日期**: {self.date}
**报告时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 一、商业模式分析

"""
        # 商业模式分析（基于行业推断）
        report += self._generate_business_model_section(fundamental)

        report += f"""
---

## 二、财务健康分析

"""
        report += self._generate_financial_health_section(fundamental)

        report += f"""
---

## 三、盈利能力分析

"""
        report += self._generate_profitability_section(fundamental)

        report += f"""
---

## 四、估值分析

"""
        report += self._generate_valuation_section(fundamental)

        report += f"""
---

## 五、技术面分析

"""
        report += self._generate_technical_section(technical)

        report += f"""
---

## 六、多空辩论

"""
        report += self._generate_debate_section(debate_result)

        report += f"""
---

## 七、决策建议

"""
        report += self._generate_recommendation_section(debate_result, fundamental, technical, sentiment)

        report += f"""
---

## ⚠️ 风险提示

1. 本报告基于量化数据和算法分析生成，仅供参考
2. 市场有风险，投资需谨慎
3. 历史表现不代表未来收益
4. 建议结合个人风险偏好和独立研究做出决策
5. 数据质量：{self.all_data.get('data_quality', {}).get('overall', 'unknown')}
   - 若使用降级数据，决策需更加谨慎

---

*报告由 Workflow B 自动生成*
"""

        # 保存报告
        report_file = self.output_dir / "decision_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n✅ 报告已保存：{report_file}")

        # 保存完整数据
        with open(self.output_dir / "all_data.json", 'w', encoding='utf-8') as f:
            json.dump(self.all_data, f, ensure_ascii=False, indent=2, default=str)

        return report

    def _generate_business_model_section(self, fundamental: Dict) -> str:
        """生成商业模式分析"""
        # 基于股票代码推断行业
        symbol = self.symbol
        industry_guess = self._guess_industry(symbol)

        data_quality = fundamental.get('data_quality', 'unknown')
        source_tag = "（真实数据）" if data_quality == 'real' else "（估计值，仅供参考）"

        revenue_growth = fundamental.get('revenue_growth')
        if revenue_growth is not None:
            growth_desc = f"营收增速 {revenue_growth:.1%}"
        else:
            growth_desc = "营收增速数据暂缺"

        return f"""### 行业定位

- **推断行业**: {industry_guess}
- **数据质量**: {data_quality} {source_tag}

### 业务特征

- {growth_desc}
- 毛利率：{f"{fundamental.get('profit_margin', 0) * 100:.1f}%" if fundamental.get('profit_margin') else "暂缺"}
- 负债率：{f"{fundamental.get('debt_ratio', 0) * 100:.1f}%" if fundamental.get('debt_ratio') else "暂缺"}

### 商业模式判断

基于行业特征，该公司的主要收入来源和盈利模式应围绕{industry_guess}展开。
建议结合公司年报和公告获取更详细的商业模式信息。"""

    def _generate_financial_health_section(self, fundamental: Dict) -> str:
        """生成财务健康分析"""
        data_quality = fundamental.get('data_quality', 'unknown')
        source_tag = "（真实数据）" if data_quality == 'real' else "（估计值）"

        debt_ratio = fundamental.get('debt_ratio')
        if debt_ratio is not None:
            if debt_ratio < 0.4:
                debt_assessment = "低负债，财务结构稳健"
            elif debt_ratio < 0.6:
                debt_assessment = "负债适中，财务风险可控"
            else:
                debt_assessment = "高负债，需关注偿债压力"
        else:
            debt_assessment = "负债率数据暂缺"

        # 构建表格行
        rows = []
        for key, label, fmt in [
            ('debt_ratio', '资产负债率', 'pct'),
            ('turnover_rate', '换手率', 'pct'),
            ('volume_ratio', '量比', 'dec2'),
            ('total_mv', '总市值（百万元）', 'mv'),
        ]:
            val = fundamental.get(key)
            if val is not None:
                if fmt == 'pct':
                    rows.append(f"| {label} | {val * 100:.1f}% |")
                elif fmt == 'dec2':
                    rows.append(f"| {label} | {val:.2f} |")
                elif fmt == 'mv':
                    rows.append(f"| {label} | {val / 1e6:.1f} 亿 |")

        table = "\n".join(rows) if rows else "| 指标 | 数据暂缺 |"

        return f"""### 财务指标 {source_tag}

| 指标 | 数值 |
|------|------|
{table}

### 财务健康评估

- **负债水平**: {debt_assessment}
- **流动性**: {'换手率较高，流动性好' if fundamental.get('turnover_rate', 0) > 0.03 else '换手率较低，流动性一般'}
- **总市值**: {f"{fundamental['total_mv'] / 1e6:.1f} 亿元" if fundamental.get('total_mv') else '暂缺'}

> 注：完整财务报表（资产负债表、现金流量表）需要接入 Tushare 财务接口获取，当前为基础指标。"""

    def _generate_profitability_section(self, fundamental: Dict) -> str:
        """生成盈利能力分析"""
        data_quality = fundamental.get('data_quality', 'unknown')
        source_tag = "（真实数据）" if data_quality == 'real' else "（估计值）"

        roe = fundamental.get('roe')
        profit_margin = fundamental.get('profit_margin')
        revenue_growth = fundamental.get('revenue_growth')

        if roe is not None:
            if roe > 0.20:
                roe_assessment = "优秀（ROE > 20%）"
            elif roe > 0.10:
                roe_assessment = "良好（ROE > 10%）"
            elif roe > 0.05:
                roe_assessment = "一般（ROE > 5%）"
            else:
                roe_assessment = "较弱（ROE < 5%）"
        else:
            roe_assessment = "数据暂缺"

        rows = []
        for key, label, fmt in [
            ('roe', 'ROE（净资产收益率）', 'pct'),
            ('profit_margin', '净利率', 'pct'),
            ('revenue_growth', '营收增速', 'pct'),
        ]:
            val = fundamental.get(key)
            if val is not None:
                if fmt == 'pct':
                    rows.append(f"| {label} | {val * 100:.1f}% |")

        table = "\n".join(rows) if rows else "| 指标 | 数据暂缺 |"

        return f"""### 盈利能力指标 {source_tag}

| 指标 | 数值 |
|------|------|
{table}

### 盈利能力评估

- **ROE 评价**: {roe_assessment}
- **盈利质量**: {'净利率较高，盈利质量好' if profit_margin and profit_margin > 0.15 else '净利率一般，需关注成本控制'}
- **成长性**: {'营收增长良好' if revenue_growth and revenue_growth > 0.1 else '营收增长放缓或数据暂缺'}

> ROE > 15% 为优秀标准，持续 5 年以上 ROE > 15% 的公司通常具有竞争优势。"""

    def _generate_valuation_section(self, fundamental: Dict) -> str:
        """生成估值分析"""
        data_quality = fundamental.get('data_quality', 'unknown')
        source_tag = "（真实数据）" if data_quality == 'real' else "（估计值）"

        pe = fundamental.get('pe')
        pb = fundamental.get('pb')
        ps = fundamental.get('ps')
        dv_ratio = fundamental.get('dv_ratio')

        if pe is not None:
            if pe < 10:
                pe_assessment = "低估（PE < 10x）"
            elif pe < 20:
                pe_assessment = "合理（PE 10-20x）"
            elif pe < 40:
                pe_assessment = "偏高（PE 20-40x）"
            else:
                pe_assessment = "高估（PE > 40x）"
        else:
            pe_assessment = "数据暂缺"

        rows = []
        for key, label, fmt in [
            ('pe', '市盈率（PE）', 'dec1'),
            ('pb', '市净率（PB）', 'dec2'),
            ('ps', '市销率（PS）', 'dec2'),
            ('dv_ratio', '股息率', 'pct'),
        ]:
            val = fundamental.get(key)
            if val is not None:
                if fmt == 'dec1':
                    rows.append(f"| {label} | {val:.1f}x |")
                elif fmt == 'dec2':
                    rows.append(f"| {label} | {val:.2f}x |")
                elif fmt == 'pct':
                    rows.append(f"| {label} | {val:.2f}% |")

        table = "\n".join(rows) if rows else "| 指标 | 数据暂缺 |"

        # 估值合理性判断
        valuation_notes = []
        if pe is not None and pb is not None:
            if pe > 30 and pb > 5:
                valuation_notes.append("PE 和 PB 双高，需关注增长是否可持续")
            elif pe < 15 and pb < 2:
                valuation_notes.append("PE 和 PB 双低，可能存在低估机会")
            if pe is not None and fundamental.get('roe', 0) > 0:
                peg = pe / (fundamental['roe'] * 100) if fundamental['roe'] > 0 else None
                if peg and peg < 1:
                    valuation_notes.append(f"PEG ≈ {peg:.1f} < 1，增长估值匹配")
                elif peg and peg > 2:
                    valuation_notes.append(f"PEG ≈ {peg:.1f} > 2，增长不足以支撑估值")

        valuation_str = "\n".join(f"- {n}" for n in valuation_notes) if valuation_notes else "- 数据不足以进行估值合理性判断"

        return f"""### 估值指标 {source_tag}

| 指标 | 数值 |
|------|------|
{table}

### 估值评估

- **PE 评价**: {pe_assessment}
- **估值合理性**: {valuation_str}

> PE 估值法：同行业 PE 对比更有参考价值。成长股可参考 PEG（PE/增速），价值股可参考 PB 和股息率。"""

    def _generate_technical_section(self, technical: Dict) -> str:
        """生成技术面分析"""
        data_quality = technical.get('data_quality', 'unknown')
        source_tag = "（真实数据）" if data_quality == 'real' else "（降级数据）"

        macd = technical.get('macd', 'unknown')
        rsi = technical.get('rsi', 50)
        trend = technical.get('trend', 'unknown')
        signal = technical.get('signal', 'neutral')
        price = technical.get('price', 0)
        change_pct = technical.get('change_pct', 0)

        # MACD 信号解释
        macd_map = {
            'golden_cross': '金叉（买入信号）',
            'death_cross': '死叉（卖出信号）',
            'bullish': '多头排列',
            'bearish': '空头排列',
        }
        macd_desc = macd_map.get(macd, '未知')

        # RSI 信号解释
        if rsi > 70:
            rsi_desc = '超买区域，注意回调风险'
        elif rsi > 50:
            rsi_desc = '中性偏强区域'
        elif rsi > 30:
            rsi_desc = '中性偏弱区域'
        else:
            rsi_desc = '超卖区域，关注反弹机会'

        # KDJ
        kdj = technical.get('kdj', {})
        kdj_str = f"K={kdj.get('k', 0):.1f}, D={kdj.get('d', 0):.1f}, J={kdj.get('j', 0):.1f}" if kdj else '暂缺'

        # 布林带
        boll_pos = technical.get('boll_position', 50)
        if boll_pos > 80:
            boll_desc = '接近上轨，超买风险'
        elif boll_pos > 60:
            boll_desc = '偏上区域，偏强'
        elif boll_pos > 40:
            boll_desc = '中轨附近，震荡'
        elif boll_pos > 20:
            boll_desc = '偏下区域，偏弱'
        else:
            boll_desc = '接近下轨，超卖关注反弹'

        return f"""### 技术指标 {source_tag}

| 指标 | 数值 | 信号 |
|------|------|------|
| 当前价格 | {price:.2f} | 涨跌幅 {change_pct:+.2f}% |
| MACD | {macd_desc} | {macd} |
| RSI(14) | {rsi:.1f} | {rsi_desc} |
| KDJ | {kdj_str} | - |
| 趋势 | {trend} | - |
| 布林带位置 | {boll_pos:.0f}% | {boll_desc} |
| 综合信号 | {signal} | - |

### 技术面评估

- **趋势方向**: {'上升趋势' if trend == 'uptrend' else '下降趋势' if trend == 'downtrend' else '横盘震荡'}
- **动能状态**: {'多头占优' if macd in ('golden_cross', 'bullish') else '空头占优' if macd in ('death_cross', 'bearish') else '动能不足'}
- **短期信号**: {rsi_desc}

> 技术分析仅反映历史价格走势，不构成投资建议。需结合基本面综合判断。"""

    def _generate_debate_section(self, debate_result: Dict) -> str:
        """生成多空辩论章节"""
        bull_points = debate_result.get('bull_points', [])
        bear_points = debate_result.get('bear_points', [])
        recommendation = debate_result.get('recommendation', '中性')
        confidence = debate_result.get('confidence', 50)
        method = debate_result.get('method', 'unknown')

        method_label = "完整辩论（Bull/Bear/Trader/Risk 四角色）" if method != 'quick_analysis' else "简化分析（基于因子数据）"

        # Bull 观点
        bull_str = "\n".join(f"- {p}" for p in bull_points) if bull_points else "- 暂无明确看多观点"
        bear_str = "\n".join(f"- {p}" for p in bear_points) if bear_points else "- 暂无明确看空观点"

        # Trader 决策
        trader = debate_result.get('trader_decision', {})
        trader_decision = trader.get('decision', 'HOLD')

        # Risk 审批
        risk = debate_result.get('risk_approval', {})
        risk_rec = risk.get('recommendation', 'N/A')

        return f"""### 辩论方式

{method_label}

### 看多观点 (Bull)

{bull_str}

### 看空观点 (Bear)

{bear_str}

### 辩论结果

| 维度 | 结果 |
|------|------|
| 综合推荐 | {recommendation} |
| 置信度 | {confidence}% |
| 交易员决策 | {trader_decision} |
| 风控审批 | {risk_rec} |"""

    def _generate_recommendation_section(self, debate_result: Dict, fundamental: Dict, technical: Dict, sentiment: Dict) -> str:
        """生成最终决策建议"""
        recommendation = debate_result.get('recommendation', '中性')
        confidence = debate_result.get('confidence', 50)
        trader_decision = debate_result.get('trader_decision', {}).get('decision', 'HOLD')
        risk_rec = debate_result.get('risk_approval', {}).get('recommendation', 'N/A')

        # 综合评分
        score = 5  # 基础分 5/10
        if recommendation == '看多':
            score += 2
        elif recommendation == '看空':
            score -= 2

        pe = fundamental.get('pe', 0)
        if pe and 0 < pe < 15:
            score += 1
        elif pe and pe > 40:
            score -= 1

        trend = technical.get('trend', 'sideways')
        if trend == 'uptrend':
            score += 1
        elif trend == 'downtrend':
            score -= 1

        sent_score = sentiment.get('sentiment_score', 0)
        if sent_score > 0.2:
            score += 0.5
        elif sent_score < -0.2:
            score -= 0.5

        score = max(1, min(10, score))

        # 动作建议
        if score >= 7:
            action = "BUY（买入）"
            action_desc = "综合评分较高，建议关注买入机会"
        elif score >= 5:
            action = "WATCH（观望）"
            action_desc = "综合评分中等，建议继续观望等待更好时机"
        else:
            action = "AVOID（回避）"
            action_desc = "综合评分较低，建议回避或减仓"

        # 风控提示
        risk_warnings = []
        if risk_rec == 'REJECT':
            risk_warnings.append("⚠️ 风控拒绝此交易")
        elif risk_rec == 'CONDITIONAL':
            risk_warnings.append("⚠️ 风控有条件通过，需满足特定条件")

        if confidence < 50:
            risk_warnings.append("置信度较低，建议谨慎")

        risk_str = "\n".join(f"- {w}" for w in risk_warnings) if risk_warnings else "- 无重大风控警告"

        return f"""### 综合评分

**得分**: {score:.1f} / 10

评分依据:
- 辩论推荐：{recommendation}（置信度 {confidence}%）
- 估值水平：PE {pe:.1f}x（{'低估' if pe and pe < 15 else '偏高' if pe and pe > 40 else '合理' if pe else '暂缺'}）
- 技术趋势：{trend}
- 舆情评分：{sent_score:+.2f}

### 最终建议

**建议动作**: **{action}**

{action_desc}

### 风控提示

{risk_str}

### 操作建议

| 项目 | 建议 |
|------|------|
| 仓位建议 | {'不超过总资金 10%' if score >= 7 else '暂不建仓' if score < 5 else '可小仓位试探（5% 以内）'} |
| 止损参考 | {'当前价格的 -8%' if technical.get('price') else '待确认'} |
| 止盈参考 | {'当前价格的 +20%' if technical.get('price') else '待确认'} |
| 观察周期 | 1-2 周 |

> **重要提示**：本建议由算法自动生成，不构成投资建议。投资有风险，决策需谨慎。"""

    def _guess_industry(self, symbol: str) -> str:
        """基于股票代码前缀推断行业"""
        if symbol.startswith('600') or symbol.startswith('601'):
            return '沪市主板（传统行业为主）'
        elif symbol.startswith('688'):
            return '科创板（科技创新）'
        elif symbol.startswith('000') or symbol.startswith('002'):
            return '深市主板/中小板'
        elif symbol.startswith('300') or symbol.startswith('301'):
            return '创业板（成长型）'
        elif symbol.startswith('8') or symbol.startswith('4'):
            return '北交所（专精特新）'
        elif 'HK' in symbol:
            return '港股'
        elif 'US' in symbol:
            return '美股'
        return '未知市场'

    def run(self) -> str:
        """运行完整 Workflow B"""
        # Step 1: 加载数据
        self.step1_load_data()

        # Step 2: 多空辩论
        debate_result = self.step2_run_debate()

        # Step 3: 生成报告
        report = self.step3_generate_report(debate_result)

        print("\n" + "=" * 60)
        print("Workflow B 执行完成")
        print(f"报告路径：{self.output_dir / 'decision_report.md'}")
        print("=" * 60)

        return report


def main():
    parser = argparse.ArgumentParser(description="Workflow B - 单股深度分析与决策建议报告")
    parser.add_argument("--symbol", type=str, required=True, help="股票代码（如 600519.SH）")
    parser.add_argument("--name", type=str, default=None, help="公司名称（可选）")

    args = parser.parse_args()

    handler = WorkflowBHandler(symbol=args.symbol, company_name=args.name)
    handler.run()


if __name__ == "__main__":
    main()
