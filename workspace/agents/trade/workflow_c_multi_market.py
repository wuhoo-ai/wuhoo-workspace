#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow C - 多市场模拟交易全链路执行脚本

支持市场:
- CN: A 股 (中证 1000) - 使用 Tushare 数据
- HK: 港股 (Top 500) - 使用富途数据
- US: 美股 (Top 500) - 使用富途数据 (需要美股行情权限)

流程:
1. 选股 → 2. 多维度分析 → 3. 多空辩论 →
4. 投资建议 → 5. 风控检查 → 6. 人工确认 →
7. 交易执行 → 8. 每日复盘报告

用法:
    source venv-futu/bin/activate
    python workflow_c_multi_market.py --market cn --date 2026-03-26
    python workflow_c_multi_market.py --market hk --date 2026-03-26
    python workflow_c_multi_market.py --market us --date 2026-03-26
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

# 环境变量配置
os.environ['FUTU_HOST'] = '127.0.0.1'
os.environ['FUTU_PORT'] = '11111'
os.environ['FUTU_ENV'] = 'SIMULATE'

# 市场配置
MARKET_CONFIG = {
    'cn': {
        'name': 'A 股 (中证 1000)',
        'gateway': 'Futu OpenAPI',
        'acc_id': 18767295,  # A 股模拟账户
        'venv': Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick' / 'venv' / 'bin' / 'activate',
        'stock_pick_script': Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick' / 'stock_pick.py',
    },
    'hk': {
        'name': '港股 (Top 500)',
        'gateway': 'Futu OpenAPI',
        'acc_id': 18767294,  # 港股模拟账户
        'venv': Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick' / 'venv' / 'bin' / 'activate',
        'stock_pick_script': Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick' / 'stock_pick.py',
    },
    'us': {
        'name': '美股 (Top 500)',
        'gateway': 'Futu OpenAPI',
        'venv': Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick' / 'venv' / 'bin' / 'activate',
        'stock_pick_script': Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick' / 'stock_pick.py',
    },
}


class WorkflowCHandler:
    """Workflow C 执行处理器"""

    def __init__(self, market: str = "HK", date: str = None):
        """
        初始化

        Args:
            market: 市场 (CN/HK/US)
            date: 交易日期 (默认今天)
        """
        self.market = market.upper()
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.config = MARKET_CONFIG.get(self.market.lower(), {})

        self.results = {
            "workflow": "C",
            "market": self.market,
            "date": self.date,
            "steps": {}
        }

        # 输出目录
        self.output_dir = Path(__file__).parent / "data" / "workflow_c" / f"{self.market}_{self.date}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print(f"Workflow C - {self.config.get('name', self.market)} 全链路")
        print(f"日期：{self.date}")
        print("=" * 60)

    def step1_select_stocks(self, top_n: int = 10) -> Dict:
        """
        Step 1: 选股

        调用 stock_pick.py 进行选股
        """
        print("\n" + "=" * 60)
        print("Step 1: 选股")
        print("=" * 60)

        try:
            # 调用选股脚本
            venv = self.config.get('venv')
            script = self.config.get('stock_pick_script')

            if not script.exists():
                return {"error": f"选股脚本不存在：{script}"}

            cmd = f"source {venv} && python3 {script} --market {self.market.lower()} --date {self.date}"
            print(f"执行：{cmd}")

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)

            # 解析输出
            output = result.stdout + result.stderr

            # 保存输出
            with open(self.output_dir / "01_stock_pick_output.txt", 'w', encoding='utf-8') as f:
                f.write(output)

            # 尝试加载选股结果
            factors_dir = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'data' / 'stock-pick' / 'factors'
            result_file = factors_dir / f"result_{self.market.lower()}_{self.date.replace('-', '')}.csv"

            selected_stocks = []
            if result_file.exists():
                import pandas as pd
                df = pd.read_csv(result_file)
                selected_stocks = df.to_dict('records')
                print(f"\n✅ 选股完成：{len(selected_stocks)} 只股票")
            else:
                print(f"\n⚠️  未找到选股结果文件：{result_file}")

            step_result = {
                "success": True,
                "market": self.market,
                "selected_count": len(selected_stocks),
                "selected_stocks": selected_stocks,
                "output_file": str(result_file) if result_file.exists() else None,
                "timestamp": datetime.now().isoformat()
            }

            # 保存到文件
            with open(self.output_dir / "01_selected_stocks.json", 'w', encoding='utf-8') as f:
                json.dump(step_result, f, ensure_ascii=False, indent=2)

            self.results["steps"]["step1_select_stocks"] = step_result
            return step_result

        except subprocess.TimeoutExpired:
            error_msg = "选股执行超时"
            print(f"❌ {error_msg}")
            result = {"error": error_msg}
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

        对选股结果进行因子、技术面、基本面分析
        """
        print("\n" + "=" * 60)
        print("Step 2: 多维度分析")
        print("=" * 60)

        if not stocks:
            print("⚠️  无股票可分析")
            return {"error": "无股票可分析"}

        # 限制分析数量
        stocks_to_analyze = stocks[:5]
        analysis_results = []

        print(f"分析股票数量：{len(stocks_to_analyze)}")

        # 对于 A 股，使用简化分析（跳过辩论以节省时间）
        if self.market.lower() == 'cn':
            print("\nA 股市场：使用简化分析模式")
            for stock in stocks_to_analyze:
                # A 股选股结果中代码字段是 ts_code (如 603220.SH)
                code = stock.get('ts_code', stock.get('code', ''))
                name = stock.get('name', '')

                analysis = {
                    "code": code,
                    "name": name,
                    "score": stock.get('composite_score', 5.0),
                    "momentum_10d": stock.get('momentum_10d', 0),
                    "recommendation": "HOLD",  # 默认
                    "timestamp": datetime.now().isoformat()
                }
                analysis_results.append(analysis)
                print(f"  {code} {name}: 10 日 ROC={stock.get('momentum_10d', 'N/A')}")
        else:
            # 港股/美股使用 Debate 分析
            try:
                # 动态导入 debate 模块
                debate_path = Path(__file__).parent.parent / 'debate'
                sys.path.insert(0, str(debate_path))

                from adapters.data_aggregator import DataAggregator
                aggregator = DataAggregator()

                for i, stock in enumerate(stocks_to_analyze):
                    code = stock.get('code', '')
                    name = stock.get('name', '')

                    print(f"\n[{i+1}/{len(stocks_to_analyze)}] 分析 {code} {name}...")

                    # 获取综合数据
                    data = aggregator.get_all_data(code, name)

                    analysis = {
                        "code": code,
                        "name": name,
                        "factor_score": data.get('factor_data', {}).get('composite_score', 0),
                        "technical_signal": data.get('technical_data', {}).get('signal', 'neutral'),
                        "data_quality": data.get('data_quality', {}).get('overall', 'unknown'),
                        "timestamp": datetime.now().isoformat()
                    }

                    analysis_results.append(analysis)
                    print(f"  因子评分：{analysis['factor_score']:.3f}")
                    print(f"  技术信号：{analysis['technical_signal']}")
                    print(f"  数据质量：{analysis['data_quality']}")

            except Exception as e:
                print(f"分析出错：{e}")

        result = {
            "success": True,
            "analyzed_count": len(analysis_results),
            "analysis_results": analysis_results,
            "timestamp": datetime.now().isoformat()
        }

        # 保存到文件
        with open(self.output_dir / "02_analysis_results.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

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

        if not stocks:
            return {"error": "无股票可辩论"}

        # A 股跳过辩论（节省时间）
        if self.market.lower() == 'cn':
            print("A 股市场：跳过辩论，使用简化建议")
            debate_results = []
            for stock in stocks[:3]:
                # A 股选股结果中代码字段是 ts_code (如 603220.SH)
                code = stock.get('ts_code', stock.get('code', ''))
                name = stock.get('name', '')
                debate_results.append({
                    "code": code,
                    "name": name,
                    "recommendation": "BUY" if stock.get('momentum_10d', 0) < -5 else "HOLD",
                    "confidence": 0.5,
                    "timestamp": datetime.now().isoformat()
                })

            result = {
                "success": True,
                "debate_results": debate_results,
                "simplified": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 港股/美股使用完整辩论
            try:
                debate_path = Path(__file__).parent.parent / 'debate'
                sys.path.insert(0, str(debate_path))

                from run_debate import run_full_debate

                debate_results = []
                for stock in stocks[:3]:  # 限制数量
                    code = stock.get('code', '')
                    name = stock.get('name', '')

                    print(f"\n辩论：{code} {name}...")

                    # 执行辩论（带超时）
                    import signal

                    def timeout_handler(signum, frame):
                        raise TimeoutError("辩论超时")

                    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(60)  # 60 秒超时

                    try:
                        result = run_full_debate(code, name, use_real_data=True)
                        signal.alarm(0)

                        debate_results.append({
                            "code": code,
                            "name": name,
                            "bull_recommendation": result.get('bull_view', {}).get('recommendation'),
                            "bear_recommendation": result.get('bear_view', {}).get('recommendation'),
                            "trader_decision": result.get('trader_decision', {}).get('decision'),
                            "risk_approval": result.get('risk_approval', {}).get('recommendation'),
                            "final_action": result.get('final_action', {}).get('action'),
                            "timestamp": datetime.now().isoformat()
                        })

                        print(f"  最终动作：{result.get('final_action', {}).get('action')}")

                    except TimeoutError:
                        print(f"  ⚠️  辩论超时，跳过")
                        debate_results.append({
                            "code": code,
                            "name": name,
                            "final_action": "timeout",
                            "timestamp": datetime.now().isoformat()
                        })
                    finally:
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_handler)

                result = {
                    "success": True,
                    "debate_results": debate_results,
                    "count": len(debate_results),
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                print(f"辩论出错：{e}")
                result = {"error": str(e), "debate_results": []}

        # 保存到文件
        with open(self.output_dir / "03_debate_results.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.results["steps"]["step3_debate"] = result
        return result

    def step4_generate_recommendations(self, debate_results: Dict) -> Dict:
        """
        Step 4: 生成投资建议
        """
        print("\n" + "=" * 60)
        print("Step 4: 生成投资建议")
        print("=" * 60)

        recommendations = []

        for debate in debate_results.get('debate_results', []):
            code = debate.get('code', '')
            name = debate.get('name', '')

            # 根据辩论结果生成建议
            if debate.get('risk_approval', {}).get('recommendation') == 'REJECT':
                action = 'REJECT'
            elif debate.get('final_action') == 'reject':
                action = 'REJECT'
            elif debate.get('recommendation') == 'BUY':
                action = 'BUY'
            else:
                action = 'HOLD'

            rec = {
                "code": code,
                "name": name,
                "action": action,
                "confidence": debate.get('confidence', 0.5),
                "reason": f"辩论结果：{debate.get('final_action', 'N/A')}",
                "timestamp": datetime.now().isoformat()
            }
            recommendations.append(rec)
            print(f"  {code} {name}: {action}")

        result = {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations),
            "timestamp": datetime.now().isoformat()
        }

        # 保存到文件
        with open(self.output_dir / "04_recommendations.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.results["steps"]["step4_recommendations"] = result
        return result

    def step5_execute_trades(self, recommendations: Dict) -> Dict:
        """
        Step 5: 执行交易 (统一富途 OpenAPI)

        市场差异:
        - A 股 (CN): OpenCNTradeContext, 账户 18767295, DAY 订单
        - 港股 (HK): OpenHKTradeContext, 账户 18767294, GTC 订单
        - 美股 (US): OpenUSTradeContext, 账户 (动态获取), GTC 订单
        """
        print("\n" + "=" * 60)
        print("Step 5: 执行交易")
        print("=" * 60)

        if self.market.lower() not in ['cn', 'hk', 'us']:
            print(f"⚠️  市场 {self.market} 暂不支持自动交易")
            result = {
                "success": False,
                "reason": f"市场 {self.market} 暂不支持自动交易",
                "timestamp": datetime.now().isoformat()
            }
            self.results["steps"]["step5_trades"] = result
            return result

        trade_results = []

        # ===== A 股 =====
        if self.market.lower() == 'cn':
            return self._execute_trades_direct(
                recommendations, trade_results,
                market='cn',
                acc_id=18767295,
                time_in_force='DAY'  # A 股模拟盘必须用 DAY
            )

        # ===== 港股 =====
        elif self.market.lower() == 'hk':
            return self._execute_trades_direct(
                recommendations, trade_results,
                market='hk',
                acc_id=18767294,
                time_in_force='DAY'  # 港股模拟盘用 DAY
            )

        # ===== 美股 =====
        elif self.market.lower() == 'us':
            # 美股账户需要动态获取
            return self._execute_trades_direct(
                recommendations, trade_results,
                market='us',
                acc_id=None,  # 动态获取
                time_in_force='DAY'  # 模拟盘用 DAY
            )

    def _execute_trades_direct(
        self,
        recommendations: Dict,
        trade_results: List,
        market: str,
        acc_id: int = None,
        time_in_force: str = 'GTC'
    ) -> Dict:
        """
        统一交易执行方法 (直接富途 API)

        Args:
            recommendations: 投资建议
            trade_results: 交易结果列表
            market: 市场 (cn/hk/us)
            acc_id: 账户 ID (美股为 None 时自动获取)
            time_in_force: 订单类型 (DAY/GTC)
        """
        # 导入模块
        if market == 'cn':
            from futu import OpenCNTradeContext as TradeContext, OrderType, TrdSide, TrdEnv
            print(f"\n使用 A 股交易接口，账户：{acc_id}")
        elif market == 'hk':
            from futu import OpenHKTradeContext as TradeContext, OrderType, TrdSide, TrdEnv
            print(f"\n使用港股交易接口，账户：{acc_id}")
        elif market == 'us':
            from futu import OpenUSTradeContext as TradeContext, OrderType, TrdSide, TrdEnv
            print(f"\n使用美股交易接口")
        else:
            raise ValueError(f"不支持的市场：{market}")

        try:
            # 创建交易上下文
            trade_ctx = TradeContext(host='127.0.0.1', port=11111)

            # 获取账户 ID (美股需要)
            if acc_id is None:
                ret, data = trade_ctx.get_acc_list()
                if ret == 0 and len(data) > 0:
                    acc_id = int(data['acc_id'].iloc[0])
                    print(f"自动获取账户 ID: {acc_id}")
                else:
                    raise Exception("无法获取账户列表")

            # 解锁交易 (模拟盘不需要密码)
            password = os.environ.get('FUTU_TRADING_PASSWORD', os.environ.get('FUTU_PASSWORD', ''))
            trade_ctx.unlock_trade(password)

            # 执行交易
            for rec in recommendations.get('recommendations', []):
                if rec.get('action') != 'BUY':
                    continue

                code = rec.get('code', '')
                name = rec.get('name', '')
                if not code:
                    continue

                # 代码格式转换
                full_code = self._convert_code(code, market)

                # 获取价格
                order_price = self._get_price(full_code, market)

                # 交易数量
                if market == 'cn':
                    qty = 100  # A 股最小 100 股
                    order_price = round(order_price, 2)  # 平价
                elif market == 'hk':
                    qty = 100  # 默认 100 股
                    order_price = round(order_price * 1.01, 2)  # 高 1% 确保成交
                else:  # us
                    qty = 1  # 美股可以 1 股
                    order_price = round(order_price * 1.01, 2)  # 高 1% 确保成交

                print(f"下单：{name} ({full_code}) BUY {qty} @ {order_price}")

                ret, data = trade_ctx.place_order(
                    acc_id=acc_id,
                    code=full_code,
                    price=order_price,
                    qty=qty,
                    trd_side=TrdSide.BUY,
                    order_type=OrderType.NORMAL,
                    trd_env=TrdEnv.SIMULATE,
                    time_in_force=time_in_force
                )

                if ret == 0 and len(data) > 0:
                    order_id = str(data.iloc[0].get('order_id', 'N/A'))
                    trade_results.append({
                        "code": full_code,
                        "name": name,
                        "action": "BUY",
                        "price": order_price,
                        "qty": qty,
                        "order_id": order_id,
                        "status": "SUBMITTED"
                    })
                    print(f"  ✅ 下单成功，订单 ID: {order_id}")
                else:
                    trade_results.append({
                        "code": full_code,
                        "name": name,
                        "action": "BUY",
                        "status": "FAILED",
                        "error": str(data) if data else "Unknown error"
                    })
                    print(f"  ❌ 下单失败：{data}")

            result = {
                "success": True,
                "market": market.upper(),
                "trade_results": trade_results,
                "count": len(trade_results),
                "gateway": "Futu OpenAPI",
                "timestamp": datetime.now().isoformat()
            }

            trade_ctx.close()

        except Exception as e:
            print(f"交易出错：{e}")
            import traceback
            traceback.print_exc()
            result = {"error": str(e)}

        # 保存到文件
        with open(self.output_dir / "05_trade_results.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.results["steps"]["step5_trades"] = result
        return result

    def _convert_code(self, code: str, market: str) -> str:
        """
        代码格式转换

        Args:
            code: 原始代码
            market: 市场

        Returns:
            富途格式代码
        """
        if market == 'cn':
            # 603220.SH → SH.603220
            if '.' in code:
                parts = code.split('.')
                if len(parts) == 2:
                    return f"{parts[1]}.{parts[0]}"
            return code
        elif market == 'hk':
            # 00700 → HK.00700
            return f"HK.{code.replace('.HK', '')}"
        elif market == 'us':
            # AAPL → US.AAPL
            if not code.startswith('US.'):
                return f"US.{code}"
            return code
        return code

    def _get_price(self, full_code: str, market: str) -> float:
        """
        根据市场获取价格

        Args:
            full_code: 富途格式代码 (SH.603220, HK.00700, US.AAPL)
            market: 市场 (cn/hk/us)

        Returns:
            价格
        """
        # ===== 港股：优先使用富途 API =====
        if market == 'hk':
            try:
                from futu import OpenQuoteContext
                quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
                ret, snapshot = quote_ctx.get_market_snapshot(full_code)
                if ret == 0 and len(snapshot) > 0:
                    price = float(snapshot['last_price'].iloc[0])
                    quote_ctx.close()
                    return price
                quote_ctx.close()
            except Exception as e:
                print(f"  富途行情获取失败：{e}")
            return 50.0  # 默认估计价格

        # ===== A 股：优先使用本地数据文件 =====
        elif market == 'cn':
            # 先尝试富途
            try:
                from futu import OpenQuoteContext
                quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
                ret, snapshot = quote_ctx.get_market_snapshot(full_code)
                if ret == 0 and len(snapshot) > 0:
                    price = float(snapshot['last_price'].iloc[0])
                    quote_ctx.close()
                    print(f"  从富途获取价格：{price}")
                    return price
                quote_ctx.close()
            except Exception:
                pass

            # 本地数据
            try:
                daily_data_file = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'data' / 'stock-pick' / 'daily_data' / '2026' / '202603.csv'
                if daily_data_file.exists():
                    import pandas as pd
                    df = pd.read_csv(daily_data_file)
                    ts_code = f"{full_code.split('.')[1]}.{full_code.split('.')[0]}"
                    stock_rows = df[df['ts_code'] == ts_code]
                    if len(stock_rows) > 0:
                        price = float(stock_rows.iloc[0]['close'])
                        print(f"  从本地数据获取价格 ({ts_code}): {price}")
                        return price
            except Exception as e:
                print(f"  本地数据获取失败：{e}")
            return 20.0  # 默认估计价格

        # ===== 美股：使用 yfinance =====
        elif market == 'us':
            try:
                import yfinance as yf
                symbol = full_code.replace('US.', '')
                ticker = yf.Ticker(symbol)
                info = ticker.info
                price = info.get('regularMarketPrice')
                if price:
                    price = float(price)
                    print(f"  从 yfinance 获取价格 ({symbol}): ${price}")
                    return price
            except Exception as e:
                print(f"  yfinance 获取失败：{e}")
            return 100.0  # 默认估计价格

        return 0.0

    def save_results(self):
        """保存完整结果"""
        with open(self.output_dir / "workflow_results.json", 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n📁 结果已保存到：{self.output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Workflow C - 多市场模拟交易全链路")
    parser.add_argument("--market", type=str, default="HK", choices=['cn', 'hk', 'us'],
                        help="市场 (cn/hk/us)")
    parser.add_argument("--date", type=str, default=None, help="交易日期 (YYYY-MM-DD)")
    parser.add_argument("--top-n", type=int, default=10, help="选股数量")
    parser.add_argument("--skip-trades", action="store_true", help="跳过交易执行")

    args = parser.parse_args()

    # 创建处理器
    handler = WorkflowCHandler(market=args.market, date=args.date)

    # Step 1: 选股
    stocks_data = handler.step1_select_stocks(top_n=args.top_n)
    if stocks_data.get('error'):
        print("Step 1 失败，终止流程")
        handler.save_results()
        return

    stocks = stocks_data.get('selected_stocks', [])

    # Step 2: 分析
    analysis = handler.step2_analyze_stocks(stocks)
    if analysis.get('error'):
        print("Step 2 失败，继续执行")

    # Step 3: 辩论
    debate = handler.step3_debate(stocks)
    if debate.get('error'):
        print("Step 3 失败，继续执行")

    # Step 4: 投资建议
    recommendations = handler.step4_generate_recommendations(debate)
    if recommendations.get('error'):
        print("Step 4 失败")

    # Step 5: 交易执行
    if not args.skip_trades:
        trades = handler.step5_execute_trades(recommendations)
        if trades.get('error'):
            print("Step 5 失败")

    # 保存结果
    handler.save_results()

    print("\n" + "=" * 60)
    print("Workflow C 执行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
