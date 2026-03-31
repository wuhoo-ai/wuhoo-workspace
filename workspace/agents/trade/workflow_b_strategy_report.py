#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow B - 投资策略报告生成

流程:
选股 → 分析 → 辩论 → 投资策略报告 → 用户审核

与 Workflow C 的区别:
- 不执行交易
- 生成详细的投资策略报告 (Markdown/PDF)
- 通过 DingTalk/WeChat 推送给用户审核
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


class WorkflowBHandler:
    """Workflow B 执行处理器"""

    def __init__(self, market: str = "HK", date: str = None):
        """
        初始化

        Args:
            market: 市场 (CN/HK/US)
            date: 交易日期
        """
        self.market = market.upper()
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.output_dir = Path(__file__).parent / "data" / "workflow_b" / f"{self.market}_{self.date}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print(f"Workflow B - {market.upper()} 投资策略报告")
        print(f"日期：{self.date}")
        print("=" * 60)

    def step1_select_stocks(self, top_n: int = 10) -> Dict:
        """Step 1: 选股"""
        print("\n" + "=" * 60)
        print("Step 1: 选股")
        print("=" * 60)

        # 调用选股脚本
        venv = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick' / 'venv' / 'bin' / 'activate'
        script = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick' / 'stock_pick.py'

        if not script.exists():
            return {"error": f"选股脚本不存在：{script}"}

        cmd = f"source {venv} && python3 {script} --market {self.market.lower()} --date {self.date}"
        print(f"执行：{cmd}")

        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=300)
        output = result.stdout + result.stderr

        # 保存输出
        with open(self.output_dir / "01_stock_pick_output.txt", 'w', encoding='utf-8') as f:
            f.write(output)

        # 加载选股结果
        factors_dir = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'data' / 'stock-pick' / 'factors'
        result_file = factors_dir / f"result_{self.market.lower()}_{self.date.replace('-', '')}.csv"

        selected_stocks = []
        if result_file.exists():
            import pandas as pd
            df = pd.read_csv(result_file)
            selected_stocks = df.to_dict('records')
            print(f"\n✅ 选股完成：{len(selected_stocks)} 只股票")
        else:
            print(f"\n⚠️  未找到选股结果文件")

        step_result = {
            "success": True,
            "selected_count": len(selected_stocks),
            "selected_stocks": selected_stocks,
            "timestamp": datetime.now().isoformat()
        }

        with open(self.output_dir / "01_selected_stocks.json", 'w', encoding='utf-8') as f:
            json.dump(step_result, f, ensure_ascii=False, indent=2)

        return step_result

    def step2_analyze_stocks(self, stocks: List[Dict]) -> Dict:
        """Step 2: 多维度分析"""
        print("\n" + "=" * 60)
        print("Step 2: 多维度分析")
        print("=" * 60)

        if not stocks:
            return {"error": "无股票可分析"}

        # 限制分析数量
        stocks_to_analyze = stocks[:5]
        analysis_results = []

        print(f"分析股票数量：{len(stocks_to_analyze)}")

        # 简化分析 (基于因子数据)
        for stock in stocks_to_analyze:
            code = stock.get('ts_code', stock.get('code', ''))
            name = stock.get('name', '')

            if self.market.lower() == 'us':
                residual_vol = stock.get('residual_vol', 0)
                momentum_5d = stock.get('momentum_5d', 0)
                beta = stock.get('beta_20d', 0)

                score = 5.0
                if residual_vol < 20: score += 1
                if momentum_5d > 2: score += 1
                if 0.9 <= beta <= 1.3: score += 1

                analysis = {
                    "code": code,
                    "name": name,
                    "score": min(score, 10),
                    "residual_vol": residual_vol,
                    "momentum_5d": momentum_5d,
                    "beta_20d": beta,
                    "recommendation": "BUY" if score >= 7 else "HOLD"
                }
                print(f"  {code} {name}: 评分={analysis['score']:.1f}")
            else:
                analysis = {
                    "code": code,
                    "name": name,
                    "score": stock.get('composite_score', 5.0),
                    "momentum_10d": stock.get('momentum_10d', 0),
                    "recommendation": "HOLD"
                }
                print(f"  {code} {name}: 10 日 ROC={stock.get('momentum_10d', 'N/A')}")

            analysis_results.append(analysis)

        result = {
            "success": True,
            "analyzed_count": len(analysis_results),
            "analysis_results": analysis_results,
            "timestamp": datetime.now().isoformat()
        }

        with open(self.output_dir / "02_analysis_results.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    def step3_debate(self, stocks: List[Dict]) -> Dict:
        """Step 3: 多空辩论"""
        print("\n" + "=" * 60)
        print("Step 3: 多空辩论")
        print("=" * 60)

        if not stocks:
            return {"error": "无股票可辩论"}

        debate_results = []

        for stock in stocks[:5]:
            code = stock.get('ts_code', stock.get('code', ''))
            name = stock.get('name', '')

            if self.market.lower() == 'us':
                residual_vol = stock.get('residual_vol', 25)
                momentum_5d = stock.get('momentum_5d', 0)
                momentum_10d = stock.get('momentum_10d', 0)
                beta = stock.get('beta_20d', 1)

                # 快速多空分析
                bull_points = []
                bear_points = []

                if residual_vol < 20:
                    bull_points.append("低残差波动率，股价相对稳定")
                elif residual_vol > 23:
                    bear_points.append("残差波动率偏高，风险较大")

                if momentum_5d > 3:
                    bull_points.append("5 日动量强劲，短期趋势向好")
                elif momentum_5d < 1.5:
                    bear_points.append("5 日动量疲软，缺乏上涨动力")

                if momentum_10d > 5:
                    bear_points.append("10 日涨幅较大，可能存在回调风险")
                elif momentum_10d < -5:
                    bull_points.append("10 日超跌，存在反弹机会")

                if 0.9 <= beta <= 1.3:
                    bull_points.append("Beta 系数适中，风险收益平衡")
                elif beta > 1.4:
                    bear_points.append("Beta 系数偏高，波动风险大")

                # 综合判断
                bull_score = len(bull_points)
                bear_score = len(bear_points)

                if bull_score > bear_score:
                    recommendation = "看多"
                    confidence = 50 + (bull_score - bear_score) * 15
                elif bear_score > bull_score:
                    recommendation = "看空"
                    confidence = 50 + (bear_score - bull_score) * 15
                else:
                    recommendation = "中性"
                    confidence = 50

                debate_results.append({
                    "code": code,
                    "name": name,
                    "bull_points": bull_points,
                    "bear_points": bear_points,
                    "recommendation": recommendation,
                    "confidence": min(max(confidence, 30), 90),
                    "timestamp": datetime.now().isoformat()
                })

                print(f"  {code} {name}: {recommendation} (置信度{confidence}%)")
            else:
                # HK 和 A 股使用简化辩论 (基于动量)
                momentum_10d = stock.get('momentum_10d', 0)

                bull_points = []
                bear_points = []

                if momentum_10d > 3:
                    bull_points.append("10 日动量强劲，短期趋势向好")
                elif momentum_10d < -3:
                    bear_points.append("10 日动量疲软，存在下跌压力")

                if momentum_10d > 8:
                    bear_points.append("短期涨幅较大，可能存在回调风险")
                elif momentum_10d < -8:
                    bull_points.append("短期超跌，存在反弹机会")

                # 综合判断
                bull_score = len(bull_points)
                bear_score = len(bear_points)

                if bull_score > bear_score:
                    recommendation = "看多"
                    confidence = 50 + (bull_score - bear_score) * 15
                elif bear_score > bull_score:
                    recommendation = "看空"
                    confidence = 50 + (bear_score - bull_score) * 15
                else:
                    recommendation = "中性"
                    confidence = 50

                debate_results.append({
                    "code": code,
                    "name": name,
                    "bull_points": bull_points,
                    "bear_points": bear_points,
                    "recommendation": recommendation,
                    "confidence": min(max(confidence, 30), 90),
                    "timestamp": datetime.now().isoformat()
                })

                print(f"  {code} {name}: {recommendation} (置信度{confidence}%)")

        result = {
            "success": True,
            "debate_results": debate_results,
            "method": "quick_analysis",
            "timestamp": datetime.now().isoformat()
        }

        with open(self.output_dir / "03_debate_results.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    def step4_generate_report(self, stocks: List[Dict], analysis: Dict, debate: Dict) -> str:
        """
        Step 4: 生成投资策略报告

        Returns:
            Markdown 格式报告
        """
        print("\n" + "=" * 60)
        print("Step 4: 生成投资策略报告")
        print("=" * 60)

        report = f"""# 📈 投资策略报告

**市场**: {self.market.upper()}
**日期**: {self.date}
**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 📋 执行摘要

本期共筛选出 **{len(stocks)}** 只候选股票，经分析辩论后，生成以下投资策略建议。

### 核心观点

"""
        # 汇总辩论结果
        debate_results = debate.get('debate_results', [])
        buy_count = sum(1 for d in debate_results if d.get('recommendation') == '看多')
        hold_count = sum(1 for d in debate_results if d.get('recommendation') == '中性')
        sell_count = sum(1 for d in debate_results if d.get('recommendation') == '看空')

        report += f"""
| 建议类型 | 数量 | 占比 |
|----------|------|------|
| 🟢 看多 | {buy_count} | {buy_count/len(debate_results)*100 if debate_results else 0:.1f}% |
| 🟡 中性 | {hold_count} | {hold_count/len(debate_results)*100 if debate_results else 0:.1f}% |
| 🔴 看空 | {sell_count} | {sell_count/len(debate_results)*100 if debate_results else 0:.1f}% |

---

## 📊 个股分析

"""
        # 详细分析每只股票
        for stock in stocks[:5]:
            code = stock.get('ts_code', stock.get('code', ''))
            name = stock.get('name', '')

            # 查找对应的辩论结果
            debate_item = next((d for d in debate_results if d.get('code') == code), None)

            report += f"""### {code} {name}

"""
            if debate_item:
                report += f"""**建议**: {debate_item.get('recommendation', '中性')}
**置信度**: {debate_item.get('confidence', 50)}%

**看多理由**:
"""
                for point in debate_item.get('bull_points', []):
                    report += f"- {point}\n"

                report += f"""
**看空理由**:
"""
                for point in debate_item.get('bear_points', []):
                    report += f"- {point}\n"
            else:
                report += "*暂无详细分析数据*\n"

            report += "\n---\n\n"

        report += f"""## ⚠️ 风险提示

1. 本报告基于量化因子分析生成，仅供参考
2. 市场有风险，投资需谨慎
3. 历史表现不代表未来收益
4. 建议结合个人风险偏好做出决策

---

## 📁 数据来源

- 选股数据：Stock-Pick Skill
- 分析数据：因子数据 + 简化分析
- 辩论结果：快速多空分析

---

*报告由 Workflow B 自动生成*
"""

        # 保存报告
        report_file = self.output_dir / "investment_strategy_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n✅ 报告已保存到：{report_file}")

        return report

    def step5_send_report(self, report: str) -> bool:
        """
        Step 5: 发送报告给用户

        Returns:
            是否发送成功
        """
        print("\n" + "=" * 60)
        print("Step 5: 发送报告")
        print("=" * 60)

        # 生成摘要消息
        summary = f"""【📈 投资策略报告】{self.date}

市场：{self.market.upper()}
候选股票：待筛选
报告已生成

请查看完整报告并确认是否执行交易。"""

        # 使用 notify.py 发送
        notify_script = Path.home() / '.openclaw' / 'scripts' / 'notify.py'
        if not notify_script.exists():
            print(f"notify.py 不存在：{notify_script}")
            return False

        try:
            result = subprocess.run(
                ["python3", str(notify_script), summary],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            if result.returncode == 0:
                print("✅ 报告推送成功")
                return True
            else:
                stderr = result.stderr.decode('utf-8') if result.stderr else ""
                print(f"❌ 推送失败：{stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ 发送超时")
            return False
        except Exception as e:
            print(f"❌ 发送异常：{e}")
            return False

    def run(self, top_n: int = 10) -> bool:
        """
        运行完整 Workflow B

        Returns:
            是否成功
        """
        # Step 1: 选股
        stocks_data = self.step1_select_stocks(top_n)
        if stocks_data.get('error'):
            print("Step 1 失败，终止流程")
            return False

        stocks = stocks_data.get('selected_stocks', [])

        # Step 2: 分析
        analysis = self.step2_analyze_stocks(stocks)
        if analysis.get('error'):
            print("Step 2 失败，继续执行")

        # Step 3: 辩论
        debate = self.step3_debate(stocks)
        if debate.get('error'):
            print("Step 3 失败，继续执行")

        # Step 4: 生成报告
        report = self.step4_generate_report(stocks, analysis, debate)

        # Step 5: 发送报告
        self.step5_send_report(report)

        print("\n" + "=" * 60)
        print("Workflow B 执行完成")
        print("=" * 60)

        return True


def main():
    parser = argparse.ArgumentParser(description="Workflow B - 投资策略报告生成")
    parser.add_argument("--market", type=str, default="HK", choices=['cn', 'hk', 'us'],
                        help="市场 (cn/hk/us)")
    parser.add_argument("--date", type=str, default=None, help="交易日期 (YYYY-MM-DD)")
    parser.add_argument("--top-n", type=int, default=10, help="选股数量")

    args = parser.parse_args()

    handler = WorkflowBHandler(market=args.market, date=args.date)
    success = handler.run(top_n=args.top_n)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
