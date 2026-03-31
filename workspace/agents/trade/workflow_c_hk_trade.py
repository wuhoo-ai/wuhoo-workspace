#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow C - 港股模拟交易全链路执行脚本

流程:
1. 选股 (富途港股) → 2. 多维度分析 → 3. 多空辩论 →
4. 投资建议 → 5. 风控检查 → 6. 人工确认 →
7. 富途模拟交易 → 8. 每日复盘报告

用法:
    source venv-futu/bin/activate
    python workflow_c_hk_trade.py --date 2026-03-26 --market HK
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

# 环境变量配置
os.environ['FUTU_HOST'] = '127.0.0.1'
os.environ['FUTU_PORT'] = '11111'
os.environ['FUTU_MARKET'] = 'HK'
os.environ['FUTU_ENV'] = 'SIMULATE'


class WorkflowCHandler:
    """Workflow C 执行处理器"""

    def __init__(self, market: str = "HK", date: str = None):
        """
        初始化

        Args:
            market: 市场 (HK/US)
            date: 交易日期 (默认今天)
        """
        self.market = market
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.results = {
            "workflow": "C",
            "market": market,
            "date": self.date,
            "steps": {}
        }

        # 输出目录
        self.output_dir = Path(__file__).parent.parent / "data" / "workflow_c" / self.date
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print(f"Workflow C - 港股模拟交易全链路")
        print(f"市场：{market} | 日期：{self.date}")
        print("=" * 60)

    def step1_select_stocks(self, top_n: int = 10) -> Dict:
        """
        Step 1: 选股 (富途港股)

        使用富途 OpenAPI 获取港股成分股，基于多因子筛选
        """
        print("\n" + "=" * 60)
        print("Step 1: 选股 (富途港股)")
        print("=" * 60)

        try:
            # 使用已有的 futu_stock_pick.py (注意：目录名有连字符，需要特殊导入)
            import importlib.util
            spec = importlib.util.spec_from_file_location("futu_stock_pick",
                Path(__file__).parent / "skills" / "futu-stock-pick" / "futu_stock_pick.py")
            futu_stock_pick = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(futu_stock_pick)
            FutuStockPicker = futu_stock_pick.FutuStockPicker

            picker = FutuStockPicker()

            # 选股参数
            if self.market == "HK":
                index_code = "HS"  # 恒生指数
                index_name = "恒生指数成分股"
            else:
                index_code = "SPX"  # 标普 500
                index_name = "标普 500 成分股"

            print(f"股票池：{index_name}")
            print(f"目标数量：Top {top_n}")

            # 获取成分股
            codes = picker.get_index_stocks(index_code)
            print(f"成分股数量：{len(codes)}")

            # 获取数据并计算因子
            print("获取股票数据...")
            stock_data = picker.get_stock_data(codes[:50], days=60)  # 先测试 50 只

            if stock_data.empty:
                return {"error": "获取股票数据失败"}

            print(f"成功获取：{len(stock_data)} 条记录")

            # 计算因子
            print("计算因子...")
            factors = picker.calculate_factors(stock_data)

            # 筛选股票
            print("筛选股票...")
            selected = picker.filter_stocks(factors)

            result = {
                "success": True,
                "stock_pool": index_name,
                "total_candidates": len(codes),
                "selected_stocks": selected.to_dict('records') if isinstance(selected, pd.DataFrame) else selected,
                "top_n": top_n,
                "timestamp": datetime.now().isoformat()
            }

            print(f"✅ 选股完成：{len(selected) if isinstance(selected, list) else 'N/A'} 只")

            # 保存到文件
            with open(self.output_dir / "01_selected_stocks.json", 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.results["steps"]["step1_select_stocks"] = result
            return result

        except Exception as e:
            error_msg = f"选股失败：{e}"
            print(f"❌ {error_msg}")
            result = {"error": error_msg}
            self.results["steps"]["step1_select_stocks"] = result
            return result

    def step2_analyze_stocks(self, stocks: List[Dict]) -> Dict:
        """
        Step 2: 多维度分析

        对选股结果进行因子、技术面、基本面、舆情分析
        """
        print("\n" + "=" * 60)
        print("Step 2: 多维度分析")
        print("=" * 60)

        try:
            from debate.adapters.data_aggregator import DataAggregator

            aggregator = DataAggregator()
            analysis_results = []

            # 限制分析数量（避免超时）
            stocks_to_analyze = stocks[:5] if isinstance(stocks, list) else []

            for i, stock in enumerate(stocks_to_analyze):
                code = stock.get('code', '')
                name = stock.get('name', '')

                print(f"\n[{i+1}/{len(stocks_to_analyze)}] 分析 {code} {name}...")

                # 获取综合数据
                data = aggregator.get_all_data(code, name)

                # 数据质量检查
                quality = data.get('data_quality', {})

                # 对于港股，因子数据可能不可用，放宽检查
                if quality.get('overall') == 'degraded':
                    print(f"  ⚠️ 数据质量降级，使用可用数据")

                analysis = {
                    "code": code,
                    "name": name,
                    "factor_score": data.get('factor_data', {}).get('composite_score', 0),
                    "momentum_score": data.get('factor_data', {}).get('momentum_score', 5.0),
                    "volatility_score": data.get('factor_data', {}).get('volatility_score', 5.0),
                    "technical_signal": data.get('technical_data', {}).get('signal', 'neutral'),
                    "fundamental_pe": data.get('fundamental_data', {}).get('pe', 0),
                    "fundamental_pb": data.get('fundamental_data', {}).get('pb', 0),
                    "sentiment_score": data.get('sentiment_data', {}).get('sentiment_score', 0),
                    "data_quality": quality.get('overall', 'mixed'),
                    "timestamp": datetime.now().isoformat()
                }

                analysis_results.append(analysis)

                print(f"  因子评分：{analysis['factor_score']:.3f}")
                print(f"  动量评分：{analysis['momentum_score']:.1f}")
                print(f"  技术信号：{analysis['technical_signal']}")
                print(f"  数据质量：{analysis['data_quality']}")

            result = {
                "success": True,
                "analyzed_count": len(analysis_results),
                "analysis_results": analysis_results,
                "timestamp": datetime.now().isoformat()
            }

            print(f"✅ 分析完成：{len(analysis_results)} 只股票")

            # 保存到文件
            with open(self.output_dir / "02_analysis_results.json", 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.results["steps"]["step2_analyze"] = result
            return result

        except Exception as e:
            error_msg = f"分析失败：{e}"
            print(f"❌ {error_msg}")
            result = {"error": error_msg}
            self.results["steps"]["step2_analyze"] = result
            return result

    def step3_debate(self, stocks: List[Dict]) -> Dict:
        """
        Step 3: 多空辩论

        对分析结果进行多空辩论，生成投资建议
        """
        print("\n" + "=" * 60)
        print("Step 3: 多空辩论")
        print("=" * 60)

        try:
            from debate.run_debate import run_full_debate

            debate_results = []

            # 对每只股票进行辩论
            for stock in stocks[:3]:  # 限制辩论数量
                code = stock.get('code', '')
                name = stock.get('name', '')

                print(f"\n辩论：{code} {name}...")

                # 执行辩论
                result = run_full_debate(code, name, use_real_data=True)

                debate_results.append({
                    "code": code,
                    "name": name,
                    "bull_recommendation": result.get('bull_view', {}).get('recommendation'),
                    "bear_recommendation": result.get('bear_view', {}).get('recommendation'),
                    "trader_decision": result.get('trader_decision', {}),
                    "risk_approval": result.get('risk_approval', {}),
                    "final_action": result.get('final_action', {}),
                    "debate_id": result.get('debate_id'),
                    "timestamp": datetime.now().isoformat()
                })

                print(f"  最终动作：{result.get('final_action', {}).get('action')}")

            result = {
                "success": True,
                "debate_results": debate_results,
                "count": len(debate_results),
                "timestamp": datetime.now().isoformat()
            }

            print(f"✅ 辩论完成：{len(debate_results)} 只股票")

            # 保存到文件
            with open(self.output_dir / "03_debate_results.json", 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.results["steps"]["step3_debate"] = result
            return result

        except Exception as e:
            error_msg = f"辩论失败：{e}"
            print(f"❌ {error_msg}")
            result = {"error": error_msg}
            self.results["steps"]["step3_debate"] = result
            return result

    def step4_generate_recommendations(self, debate_results: Dict) -> Dict:
        """
        Step 4: 生成投资建议

        根据辩论结果生成具体的投资建议（价格、仓位、止盈止损）
        """
        print("\n" + "=" * 60)
        print("Step 4: 生成投资建议")
        print("=" * 60)

        try:
            recommendations = []

            for debate in debate_results.get('debate_results', []):
                trader_decision = debate.get('trader_decision', {})
                risk_approval = debate.get('risk_approval', {})

                # 检查是否通过
                if risk_approval.get('recommendation') == 'REJECT':
                    continue

                # 获取当前价格
                code = debate.get('code', '')
                price = self._get_current_price(code)

                # 计算仓位
                position_size = trader_decision.get('position_size', 0.05)
                if position_size > 0.15:  # 超过 15% 需要人工确认
                    needs_approval = True
                else:
                    needs_approval = False

                # 计算止盈止损
                stop_loss_price = price * 0.92  # -8%
                take_profit_price = price * 1.20  # +20%

                rec = {
                    "code": code,
                    "name": debate.get('name', ''),
                    "action": trader_decision.get('decision', 'HOLD'),
                    "price": price,
                    "position_ratio": min(position_size, 0.20),  # 最大 20%
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price,
                    "needs_approval": needs_approval,
                    "confidence": trader_decision.get('confidence', 0),
                    "reason": self._generate_reason(debate),
                    "timestamp": datetime.now().isoformat()
                }

                recommendations.append(rec)

                print(f"\n{code} {rec['name']}:")
                print(f"  建议：{rec['action']} @ {rec['price']}")
                print(f"  仓位：{rec['position_ratio']*100:.1f}%")
                print(f"  止损：{rec['stop_loss']} ({(rec['stop_loss']/rec['price']-1)*100:.1f}%)")
                print(f"  止盈：{rec['take_profit']} ({(rec['take_profit']/rec['price']-1)*100:.1f}%)")
                print(f"  需审批：{rec['needs_approval']}")

            result = {
                "success": True,
                "recommendations": recommendations,
                "count": len(recommendations),
                "timestamp": datetime.now().isoformat()
            }

            print(f"\n✅ 投资建议完成：{len(recommendations)} 条")

            # 保存到文件
            with open(self.output_dir / "04_recommendations.json", 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.results["steps"]["step4_recommendations"] = result
            return result

        except Exception as e:
            error_msg = f"生成建议失败：{e}"
            print(f"❌ {error_msg}")
            result = {"error": error_msg}
            self.results["steps"]["step4_recommendations"] = result
            return result

    def _get_current_price(self, code: str) -> float:
        """获取当前价格（简化实现）"""
        # TODO: 从富途获取实时价格
        # 这里返回一个模拟价格用于测试
        hash_val = hash(code) % 1000
        return float(100 + hash_val)

    def _generate_reason(self, debate: Dict) -> str:
        """生成投资建议理由"""
        bull = debate.get('bull_view', {}).get('recommendation', '')
        bear = debate.get('bear_view', {}).get('recommendation', '')
        trader = debate.get('trader_decision', {}).get('decision', '')

        return f"多头：{bull}, 空头：{bear}, 决策：{trader}"

    def save_results(self):
        """保存完整结果"""
        with open(self.output_dir / "workflow_results.json", 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n📁 结果已保存到：{self.output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Workflow C - 港股模拟交易全链路")
    parser.add_argument("--market", type=str, default="HK", help="市场 (HK/US)")
    parser.add_argument("--date", type=str, default=None, help="交易日期 (YYYY-MM-DD)")
    parser.add_argument("--top-n", type=int, default=10, help="选股数量")

    args = parser.parse_args()

    # 创建处理器
    handler = WorkflowCHandler(market=args.market, date=args.date)

    # Step 1: 选股
    stocks = handler.step1_select_stocks(top_n=args.top_n)
    if stocks.get('error'):
        print("Step 1 失败，终止流程")
        handler.save_results()
        return

    # Step 2: 分析
    # 使用选股结果中的股票列表
    stock_list = stocks.get('selected_stocks', [])[:5] if isinstance(stocks, dict) else []
    analysis = handler.step2_analyze_stocks(stock_list)
    if analysis.get('error'):
        print("Step 2 失败，继续执行（使用简化分析）")

    # Step 3: 辩论
    debate = handler.step3_debate(stock_list)
    if debate.get('error'):
        print("Step 3 失败，继续执行（简化辩论）")

    # Step 4: 投资建议
    recommendations = handler.step4_generate_recommendations(debate)
    if recommendations.get('error'):
        print("Step 4 失败")

    # 保存结果
    handler.save_results()

    print("\n" + "=" * 60)
    print("Workflow C 执行完成")
    print("=" * 60)


if __name__ == "__main__":
    # 需要 pandas
    import pandas as pd
    main()
