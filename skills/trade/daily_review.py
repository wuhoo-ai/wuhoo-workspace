#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日复盘报告生成模块

功能:
1. 持仓汇总
2. 收益计算
3. 归因分析
4. 交易日志整理
5. 生成 Markdown 报告
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))


class DailyReviewGenerator:
    """每日复盘报告生成器"""

    def __init__(self, date: str = None):
        """
        初始化

        Args:
            date: 交易日期 (默认今天)
        """
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.data_dir = Path(__file__).parent / "data" / "workflow_c"
        self.output_dir = self.data_dir / f"REVIEW_{self.date}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 数据源路径
        self.position_file = Path.home() / '.hermes' / 'workspace' / 'projects' / 'AI-Trader' / 'data' / 'agent_data' / 'trade-agent' / 'position' / 'position.jsonl'
        self.log_dir = Path.home() / '.hermes' / 'workspace' / 'projects' / 'AI-Trader' / 'data' / 'agent_data' / 'trade-agent' / 'log'

    def generate_report(self) -> Dict:
        """
        生成每日复盘报告

        Returns:
            报告数据
        """
        print(f"\n{'='*60}")
        print(f"生成每日复盘报告 - {self.date}")
        print(f"{'='*60}")

        # 1. 收集 Workflow C 执行结果
        workflow_results = self._collect_workflow_results()

        # 2. 获取持仓数据
        position_data = self._get_position_data()

        # 3. 计算收益
        profit_data = self._calculate_profit(position_data)

        # 4. 归因分析
        attribution_data = self._attribution_analysis(workflow_results, position_data)

        # 5. 整理交易日志
        trade_log = self._collect_trade_log()

        # 6. 生成报告
        report = {
            "date": self.date,
            "generated_at": datetime.now().isoformat(),
            "workflow_summary": workflow_results,
            "position_summary": position_data,
            "profit_analysis": profit_data,
            "attribution_analysis": attribution_data,
            "trade_log": trade_log
        }

        # 7. 保存报告
        self._save_report(report)

        # 8. 生成 Markdown 格式
        markdown = self._generate_markdown(report)
        self._save_markdown(markdown)

        print(f"\n✅ 报告已保存到：{self.output_dir}")

        return report

    def _collect_workflow_results(self) -> Dict:
        """收集 Workflow C 执行结果"""
        results = {
            "executed": False,
            "market": None,
            "selected_count": 0,
            "analyzed_count": 0,
            "recommended_count": 0,
            "traded_count": 0,
            "details": {}
        }

        # 查找今日 Workflow C 结果
        date_str = self.date.replace("-", "")
        for market in ['cn', 'hk', 'us']:
            workflow_dir = self.data_dir / f"{market.upper()}_{self.date}"
            if not workflow_dir.exists():
                continue

            results["executed"] = True
            results["market"] = market.upper()

            # 读取选股结果
            stock_pick_file = workflow_dir / "01_selected_stocks.json"
            if stock_pick_file.exists():
                with open(stock_pick_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results["selected_count"] = data.get("selected_count", 0)

            # 读取分析结果
            analysis_file = workflow_dir / "02_analysis_results.json"
            if analysis_file.exists():
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results["analyzed_count"] = data.get("analyzed_count", 0)

            # 读取辩论结果
            debate_file = workflow_dir / "03_debate_results.json"
            if debate_file.exists():
                with open(debate_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results["debate_count"] = data.get("count", 0)

            # 读取推荐结果
            rec_file = workflow_dir / "04_recommendations.json"
            if rec_file.exists():
                with open(rec_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results["recommended_count"] = data.get("count", 0)

            # 读取交易结果
            trade_file = workflow_dir / "05_trade_results.json"
            if trade_file.exists():
                with open(trade_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results["traded_count"] = data.get("count", 0)
                    results["trade_details"] = data.get("trade_results", [])

        return results

    def _get_position_data(self) -> Dict:
        """获取持仓数据"""
        positions = []
        total_market_value = 0.0
        total_cost = 0.0

        if self.position_file.exists():
            try:
                with open(self.position_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            pos = json.loads(line)
                            if pos.get('qty', 0) > 0:
                                positions.append({
                                    "code": pos.get('code', ''),
                                    "name": pos.get('name', ''),
                                    "qty": pos.get('qty', 0),
                                    "avg_price": pos.get('avg_price', 0),
                                    "current_price": pos.get('current_price', 0),
                                    "cost_basis": pos.get('cost_basis', 0),
                                    "current_value": pos.get('current_value', 0),
                                    "profit": pos.get('profit', 0),
                                    "profit_ratio": pos.get('profit_ratio', 0)
                                })
                                total_market_value += pos.get('current_value', 0)
                                total_cost += pos.get('cost_basis', 0)
            except Exception as e:
                print(f"加载持仓文件失败：{e}")

        total_profit = total_market_value - total_cost if total_cost > 0 else 0
        total_profit_ratio = total_profit / total_cost * 100 if total_cost > 0 else 0

        return {
            "positions": positions,
            "total_market_value": round(total_market_value, 2),
            "total_cost": round(total_cost, 2),
            "total_profit": round(total_profit, 2),
            "total_profit_ratio": round(total_profit_ratio, 2),
            "position_count": len(positions)
        }

    def _calculate_profit(self, position_data: Dict) -> Dict:
        """计算收益"""
        # 简化版本：基于持仓数据计算
        return {
            "daily_profit": position_data.get("total_profit", 0),
            "daily_profit_ratio": position_data.get("total_profit_ratio", 0),
            "total_market_value": position_data.get("total_market_value", 0),
            "cash_estimate": 1000000 - position_data.get("total_market_value", 0),
            "note": "收益计算基于持仓数据，实际收益需考虑现金变动"
        }

    def _attribution_analysis(self, workflow_results: Dict, position_data: Dict) -> Dict:
        """归因分析"""
        attribution = {
            "stock_picking": "N/A",
            "timing": "N/A",
            "sector_allocation": "N/A",
            "notes": []
        }

        # 基于交易结果分析
        if workflow_results.get("trade_details"):
            trades = workflow_results["trade_details"]
            buy_count = sum(1 for t in trades if t.get("action") == "BUY")
            sell_count = sum(1 for t in trades if t.get("action") == "SELL")

            attribution["stock_picking"] = f"今日选出{workflow_results.get('selected_count', 0)}只股票，交易{len(trades)}笔"
            attribution["notes"].append(f"买入{buy_count}笔，卖出{sell_count}笔")

        # 基于持仓分析
        if position_data.get("positions"):
            sectors = defaultdict(int)
            for pos in position_data["positions"]:
                # 简化行业分类 (实际应用中需要行业数据)
                code = pos.get("code", "")
                if code.startswith("HK."):
                    sectors["港股"] += 1
                elif code.startswith("US."):
                    sectors["美股"] += 1
                else:
                    sectors["A 股"] += 1

            attribution["sector_allocation"] = dict(sectors)

        return attribution

    def _collect_trade_log(self) -> List[Dict]:
        """收集交易日志"""
        logs = []

        # 查找日志文件
        date_path = self.log_dir / self.date.replace("-", "")
        if date_path.exists():
            log_file = date_path / "log.jsonl"
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                logs.append(json.loads(line))
                except Exception as e:
                    print(f"加载日志文件失败：{e}")

        # 如果日志目录不存在，尝试从 workflow 结果中提取
        if not logs:
            workflow_dir = self.data_dir / f"logs_{self.date}"
            if workflow_dir.exists():
                for json_file in workflow_dir.glob("*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            logs.append({
                                "file": json_file.name,
                                "data": data
                            })
                    except:
                        pass

        return logs

    def _save_report(self, report: Dict):
        """保存 JSON 报告"""
        output_file = self.output_dir / "daily_review.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def _generate_markdown(self, report: Dict) -> str:
        """生成 Markdown 格式报告"""
        date = report.get("date", self.date)
        workflow = report.get("workflow_summary", {})
        position = report.get("position_summary", {})
        profit = report.get("profit_analysis", {})
        attribution = report.get("attribution_analysis", {})

        md = f"""# 📊 每日复盘报告

**日期**: {date}
**生成时间**: {report.get('generated_at', datetime.now().isoformat())}

---

## 📈 市场概览

| 指标 | 数值 |
|------|------|
| 总资产 | ¥{profit.get('total_market_value', 0):,.2f} |
| 持仓市值 | ¥{position.get('total_market_value', 0):,.2f} |
| 估算现金 | ¥{profit.get('cash_estimate', 0):,.2f} |
| 总收益 | ¥{profit.get('daily_profit', 0):,.2f} |
| 收益率 | {profit.get('daily_profit_ratio', 0):.2f}% |

---

## 📋 Workflow C 执行汇总

| 步骤 | 数量 |
|------|------|
| 选股 | {workflow.get('selected_count', 0)} 只 |
| 分析 | {workflow.get('analyzed_count', 0)} 只 |
| 推荐 | {workflow.get('recommended_count', 0)} 只 |
| 交易 | {workflow.get('traded_count', 0)} 笔 |

### 交易明细

"""
        # 添加交易明细
        trade_details = workflow.get("trade_details", [])
        if trade_details:
            md += "| 代码 | 名称 | 操作 | 价格 | 数量 | 状态 |\n"
            md += "|------|------|------|------|------|------|\n"
            for trade in trade_details:
                md += f"| {trade.get('code', 'N/A')} | {trade.get('name', 'N/A')} | {trade.get('action', 'N/A')} | {trade.get('price', 0):.2f} | {trade.get('qty', 0)} | {trade.get('status', 'N/A')} |\n"
        else:
            md += "*今日无交易*"

        md += f"""

---

## 💼 持仓汇总

**持仓数量**: {position.get('position_count', 0)} 只

| 代码 | 名称 | 数量 | 成本 | 现价 | 市值 | 盈亏 | 盈利率 |
|------|------|------|------|------|------|------|--------|
"""

        # 添加持仓明细
        positions = position.get("positions", [])
        if positions:
            for pos in positions:
                profit_sign = "+" if pos.get("profit", 0) >= 0 else ""
                md += f"| {pos.get('code', 'N/A')} | {pos.get('name', 'N/A')} | {pos.get('qty', 0)} | {pos.get('avg_price', 0):.2f} | {pos.get('current_price', 0):.2f} | {pos.get('current_value', 0):,.2f} | {profit_sign}{pos.get('profit', 0):,.2f} | {pos.get('profit_ratio', 0):.2f}% |\n"
        else:
            md += "*无持仓*"

        md += f"""

---

## 🔍 归因分析

- **选股贡献**: {attribution.get('stock_picking', 'N/A')}
- **行业配置**: {attribution.get('sector_allocation', 'N/A')}
- **择时贡献**: {attribution.get('timing', 'N/A')}

"""

        # 添加备注
        notes = attribution.get("notes", [])
        if notes:
            md += "\n".join([f"- {note}" for note in notes])
            md += "\n"

        md += f"""

---

## 📝 备注

{profit.get('note', '无')}

---

*报告由 Workflow C 自动生成*
"""

        return md

    def _save_markdown(self, markdown: str):
        """保存 Markdown 报告"""
        output_file = self.output_dir / "daily_review.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)


def generate_daily_review(date: str = None) -> Dict:
    """
    生成每日复盘报告 (Workflow C 调用)

    Args:
        date: 交易日期

    Returns:
        报告数据
    """
    generator = DailyReviewGenerator(date)
    return generator.generate_report()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='每日复盘报告生成器')
    parser.add_argument('--date', type=str, default=None, help='交易日期 (YYYY-MM-DD)')

    args = parser.parse_args()

    report = generate_daily_review(args.date)

    print("\n报告生成完成!")
    print(f"📁 输出目录：{DailyReviewGenerator(args.date).output_dir}")
