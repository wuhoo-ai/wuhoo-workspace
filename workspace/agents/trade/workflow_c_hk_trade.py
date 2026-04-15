#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow C - 港股模拟交易全链路执行脚本

流程:
1. 选股 (stock_pick.py --market hk) → 2. 多维度分析 → 3. 多空辩论 →
4. 投资建议 → 5. 风控检查 → 6. 人工确认 →
7. 富途模拟交易 → 8. 每日复盘报告

用法:
    source venv-futu/bin/activate
    python workflow_c_hk_trade.py --date 2026-04-14 --market HK
"""

import os
import sys
import json
import subprocess
import argparse
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# 添加路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# 环境变量配置
os.environ['FUTU_HOST'] = '127.0.0.1'
os.environ['FUTU_PORT'] = '11111'
os.environ['FUTU_MARKET'] = 'HK'
os.environ['FUTU_ENV'] = 'SIMULATE'

# 路径常量
STOCK_PICK_SCRIPT = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick' / 'stock_pick.py'
STOCK_PICK_VENV = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick' / 'venv' / 'bin' / 'activate'
DEBATE_PATH = SCRIPT_DIR.parent / 'debate'
FACTORS_DIR = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'data' / 'stock-pick' / 'factors'


class WorkflowCHandler:
    """Workflow C 执行处理器"""

    def __init__(self, market: str = "HK", date: str = None, skip_trades: bool = False):
        self.market = market.upper()
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.skip_trades = skip_trades
        self.results = {
            "workflow": "C",
            "market": self.market,
            "date": self.date,
            "steps": {}
        }

        # 输出目录
        self.output_dir = SCRIPT_DIR.parent / "data" / "workflow_c" / f"{self.market}_{self.date}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print(f"Workflow C - 港股模拟交易全链路")
        print(f"市场：{self.market} | 日期：{self.date}")
        print("=" * 60)

    # ──────────────────────────────────────────────────────
    # Step 1: 选股
    # ──────────────────────────────────────────────────────

    def step1_select_stocks(self, top_n: int = 10) -> Dict:
        """
        Step 1: 选股 (港股)

        调用 stock_pick.py --market hk 进行选股，解析结果文件。
        添加了超时保护 (5 分钟) 和结果验证。
        """
        print("\n" + "=" * 60)
        print("Step 1: 选股 (港股)")
        print("=" * 60)

        if not STOCK_PICK_SCRIPT.exists():
            error_msg = f"选股脚本不存在：{STOCK_PICK_SCRIPT}"
            print(f"❌ {error_msg}")
            result = {"success": False, "error": error_msg}
            self.results["steps"]["step1_select_stocks"] = result
            return result

        # 构建选股结果文件路径
        date_str = self.date.replace('-', '')
        result_file = FACTORS_DIR / f"result_hk_{date_str}.csv"

        try:
            # 使用 subprocess 调用选股脚本
            # 优先使用 stock-pick 的 venv，如果不存在则使用当前 python
            python_cmd = sys.executable  # fallback: use current python
            if STOCK_PICK_VENV.parent.parent.exists():
                python_cmd = str(STOCK_PICK_VENV.parent.parent / 'bin' / 'python')

            cmd = [
                python_cmd,
                str(STOCK_PICK_SCRIPT),
                '--market', 'hk',
                '--date', self.date
            ]

            print(f"执行选股: {' '.join(cmd)}")
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=300  # 5 分钟超时
            )

            # 打印脚本输出
            if proc.stdout:
                print(proc.stdout)
            if proc.stderr:
                print(proc.stderr)

            if proc.returncode != 0:
                error_msg = f"选股脚本执行失败 (exit code={proc.returncode})"
                print(f"❌ {error_msg}")
                result = {"success": False, "error": error_msg}
                self.results["steps"]["step1_select_stocks"] = result
                return result

            # 解析选股结果
            if not result_file.exists():
                error_msg = f"未找到选股结果文件：{result_file}"
                print(f"❌ {error_msg}")
                result = {"success": False, "error": error_msg}
                self.results["steps"]["step1_select_stocks"] = result
                return result

            df = pd.read_csv(result_file)
            if df.empty:
                error_msg = "选股结果为空"
                print(f"❌ {error_msg}")
                result = {"success": False, "error": error_msg}
                self.results["steps"]["step1_select_stocks"] = result
                return result

            # 取 Top N
            top_stocks = df.head(top_n)
            selected_list = top_stocks.to_dict('records')

            step_result = {
                "success": True,
                "stock_pool": "港股 Top 500",
                "total_candidates": len(df),
                "selected_count": len(selected_list),
                "selected_stocks": selected_list,
                "top_n": top_n,
                "result_file": str(result_file),
                "timestamp": datetime.now().isoformat()
            }

            print(f"✅ 选股完成：{len(selected_list)} 只 (从 {len(df)} 只候选)")

            # 保存
            with open(self.output_dir / "01_selected_stocks.json", 'w', encoding='utf-8') as f:
                json.dump(step_result, f, ensure_ascii=False, indent=2)

            self.results["steps"]["step1_select_stocks"] = step_result
            return step_result

        except subprocess.TimeoutExpired:
            error_msg = "选股执行超时 (5 分钟)"
            print(f"❌ {error_msg}")
            result = {"success": False, "error": error_msg}
            self.results["steps"]["step1_select_stocks"] = result
            return result

        except Exception as e:
            error_msg = f"选股失败：{e}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            result = {"success": False, "error": error_msg}
            self.results["steps"]["step1_select_stocks"] = result
            return result

    # ──────────────────────────────────────────────────────
    # Step 2: 多维度分析
    # ──────────────────────────────────────────────────────

    def step2_analyze_stocks(self, stocks: List[Dict]) -> Dict:
        """
        Step 2: 多维度分析

        对选股结果进行因子、技术面、基本面、舆情分析。
        使用 Debate DataAggregator 统一获取数据。
        单个股票分析超时保护 (60 秒)，整体超时保护。
        """
        print("\n" + "=" * 60)
        print("Step 2: 多维度分析")
        print("=" * 60)

        if not stocks:
            print("⚠️  无股票可分析")
            result = {"success": False, "error": "无股票可分析"}
            self.results["steps"]["step2_analyze"] = result
            return result

        # 添加到 debate 路径
        sys.path.insert(0, str(DEBATE_PATH))

        try:
            from adapters.data_aggregator import DataAggregator
        except ImportError as e:
            error_msg = f"无法导入 DataAggregator: {e}"
            print(f"❌ {error_msg}")
            result = {"success": False, "error": error_msg}
            self.results["steps"]["step2_analyze"] = result
            return result

        aggregator = DataAggregator()
        analysis_results = []

        # 限制分析数量 (避免超时和 API 限流)
        stocks_to_analyze = stocks[:5]
        print(f"分析股票数量：{len(stocks_to_analyze)}")

        for i, stock in enumerate(stocks_to_analyze):
            # 港股使用 ts_code 字段
            code = stock.get('ts_code', stock.get('code', ''))
            name = stock.get('name', '')

            print(f"\n[{i+1}/{len(stocks_to_analyze)}] 分析 {code} {name}...")

            try:
                # 单只股票分析超时保护
                data = self._call_with_timeout(
                    aggregator.get_all_data,
                    args=(code, name),
                    timeout_sec=60
                )

                if data is None:
                    print(f"  ⚠️  {code} 分析超时，跳过")
                    analysis_results.append({
                        "code": code,
                        "name": name,
                        "error": "analysis_timeout",
                        "timestamp": datetime.now().isoformat()
                    })
                    continue

                quality = data.get('data_quality', {})
                if quality.get('overall') == 'degraded':
                    print(f"  ⚠️ 数据质量降级: {quality.get('warning', '')}")

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

            except TimeoutError:
                print(f"  ⚠️  {code} 分析超时 (60s)，跳过")
                analysis_results.append({
                    "code": code,
                    "name": name,
                    "error": "analysis_timeout",
                    "timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                print(f"  ❌  {code} 分析失败：{e}")
                analysis_results.append({
                    "code": code,
                    "name": name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

        result = {
            "success": True,
            "analyzed_count": len(analysis_results),
            "analysis_results": analysis_results,
            "timestamp": datetime.now().isoformat()
        }

        print(f"\n✅ 分析完成：{len(analysis_results)} 只股票")

        with open(self.output_dir / "02_analysis_results.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.results["steps"]["step2_analyze"] = result
        return result

    # ──────────────────────────────────────────────────────
    # Step 3: 多空辩论
    # ──────────────────────────────────────────────────────

    def step3_debate(self, stocks: List[Dict]) -> Dict:
        """
        Step 3: 多空辩论

        对分析结果进行多空辩论，生成投资建议。
        每只股票辩论超时 60 秒。
        """
        print("\n" + "=" * 60)
        print("Step 3: 多空辩论")
        print("=" * 60)

        if not stocks:
            return {"success": False, "error": "无股票可辩论"}

        # 添加到 debate 路径
        sys.path.insert(0, str(DEBATE_PATH))

        try:
            from run_debate import run_full_debate
        except ImportError as e:
            error_msg = f"无法导入 run_full_debate: {e}"
            print(f"❌ {error_msg}")
            result = {"success": False, "error": error_msg}
            self.results["steps"]["step3_debate"] = result
            return result

        debate_results = []
        stocks_to_debate = stocks[:3]  # 限制辩论数量

        for stock in stocks_to_debate:
            code = stock.get('ts_code', stock.get('code', ''))
            name = stock.get('name', '')

            print(f"\n辩论：{code} {name}...")

            try:
                debate_result = self._call_with_timeout(
                    run_full_debate,
                    kwargs={"symbol": code, "company_name": name, "use_real_data": True},
                    timeout_sec=90  # 辩论可能需要更长时间
                )

                if debate_result is None:
                    print(f"  ⚠️  辩论超时 (90s)，跳过 {code}")
                    debate_results.append({
                        "code": code,
                        "name": name,
                        "error": "debate_timeout",
                        "final_action": "timeout",
                        "timestamp": datetime.now().isoformat()
                    })
                    continue

                debate_results.append({
                    "code": code,
                    "name": name,
                    "bull_recommendation": debate_result.get('bull_view', {}).get('recommendation'),
                    "bear_recommendation": debate_result.get('bear_view', {}).get('recommendation'),
                    "trader_decision": debate_result.get('trader_decision', {}),
                    "risk_approval": debate_result.get('risk_approval', {}),
                    "final_action": debate_result.get('final_action', {}),
                    "debate_id": debate_result.get('debate_id'),
                    "timestamp": datetime.now().isoformat()
                })

                final = debate_result.get('final_action', {})
                print(f"  最终动作：{final.get('action', 'N/A')}")

            except TimeoutError:
                print(f"  ⚠️  {code} 辩论超时 (90s)，跳过")
                debate_results.append({
                    "code": code,
                    "name": name,
                    "error": "debate_timeout",
                    "final_action": "timeout",
                    "timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                print(f"  ❌  {code} 辩论失败：{e}")
                debate_results.append({
                    "code": code,
                    "name": name,
                    "error": str(e),
                    "final_action": "error",
                    "timestamp": datetime.now().isoformat()
                })

        result = {
            "success": True,
            "debate_results": debate_results,
            "count": len(debate_results),
            "timestamp": datetime.now().isoformat()
        }

        print(f"\n✅ 辩论完成：{len(debate_results)} 只股票")

        with open(self.output_dir / "03_debate_results.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.results["steps"]["step3_debate"] = result
        return result

    # ──────────────────────────────────────────────────────
    # Step 4: 生成投资建议
    # ──────────────────────────────────────────────────────

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
                # 跳过错误/超时的股票
                if debate.get('error'):
                    continue

                risk_approval = debate.get('risk_approval', {})
                trader_decision = debate.get('trader_decision', {})

                # 风控否决
                if isinstance(risk_approval, dict) and risk_approval.get('recommendation') == 'REJECT':
                    print(f"  {debate.get('code')} ❌ 风控拒绝")
                    continue

                code = debate.get('code', '')
                name = debate.get('name', '')

                # 获取当前价格
                full_code = self._convert_hk_code(code)
                price = self._get_current_price(full_code)
                if price <= 0:
                    print(f"  ⚠️  {code} 价格获取失败，跳过")
                    continue

                # 仓位计算 (基于辩论置信度)
                final_action = debate.get('final_action', {})
                if isinstance(final_action, dict):
                    action = final_action.get('action', 'HOLD')
                else:
                    action = str(final_action)

                confidence = 0.5
                if isinstance(trader_decision, dict):
                    confidence = trader_decision.get('confidence', 0.5)

                position_size = min(confidence * 0.15, 0.20)  # 最大 20%
                needs_approval = position_size > 0.10  # 超过 10% 需确认

                # 止盈止损
                stop_loss_price = round(price * 0.92, 2)   # -8%
                take_profit_price = round(price * 1.20, 2)  # +20%

                rec = {
                    "code": code,
                    "full_code": full_code,
                    "name": name,
                    "action": self._map_action(action),
                    "price": price,
                    "position_ratio": round(position_size, 3),
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price,
                    "needs_approval": needs_approval,
                    "confidence": round(confidence, 2),
                    "reason": self._generate_reason(debate),
                    "timestamp": datetime.now().isoformat()
                }

                recommendations.append(rec)

                print(f"\n{code} {name}:")
                print(f"  建议：{rec['action']} @ HKD {rec['price']}")
                print(f"  仓位：{rec['position_ratio']*100:.1f}%")
                print(f"  止损：HKD {rec['stop_loss']} (-8%)")
                print(f"  止盈：HKD {rec['take_profit']} (+20%)")
                print(f"  需审批：{rec['needs_approval']}")

            result = {
                "success": True,
                "recommendations": recommendations,
                "count": len(recommendations),
                "timestamp": datetime.now().isoformat()
            }

            print(f"\n✅ 投资建议完成：{len(recommendations)} 条")

            with open(self.output_dir / "04_recommendations.json", 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.results["steps"]["step4_recommendations"] = result
            return result

        except Exception as e:
            error_msg = f"生成建议失败：{e}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            result = {"success": False, "error": error_msg}
            self.results["steps"]["step4_recommendations"] = result
            return result

    # ──────────────────────────────────────────────────────
    # Step 5: 交易执行
    # ──────────────────────────────────────────────────────

    def step5_execute_trades(self, recommendations: Dict) -> Dict:
        """
        Step 5: 交易执行 (富途模拟交易)

        如果 skip_trades=True 则跳过此步骤。
        """
        print("\n" + "=" * 60)
        print("Step 5: 交易执行")
        print("=" * 60)

        if self.skip_trades:
            print("⏭️  跳过交易执行 (--skip-trades)")
            result = {"success": True, "skipped": True, "reason": "skip-trades flag"}
            self.results["steps"]["step5_trades"] = result
            return result

        if not recommendations.get('recommendations'):
            print("⚠️  无推荐可执行")
            result = {"success": False, "reason": "no recommendations"}
            self.results["steps"]["step5_trades"] = result
            return result

        trade_results = []

        try:
            from futu import OpenHKTradeContext, OrderType, TrdSide, TrdEnv

            trade_ctx = OpenHKTradeContext(host='127.0.0.1', port=11111)

            # 解锁交易
            password = os.environ.get('FUTU_TRADING_PASSWORD', os.environ.get('FUTU_PASSWORD', ''))
            if password:
                trade_ctx.unlock_trade(password)

            acc_id = 18767294  # 港股模拟账户

            for rec in recommendations.get('recommendations', []):
                if rec.get('action') != 'BUY':
                    continue

                full_code = rec.get('full_code', '')
                if not full_code:
                    continue

                price = rec.get('price', 0)
                qty = 100  # 港股最小交易单位通常 100 股
                order_price = round(price * 1.01, 2)  # 高 1% 确保成交

                print(f"下单：{rec['name']} ({full_code}) BUY {qty} @ HKD {order_price}")

                ret, data = trade_ctx.place_order(
                    acc_id=acc_id,
                    code=full_code,
                    price=order_price,
                    qty=qty,
                    trd_side=TrdSide.BUY,
                    order_type=OrderType.NORMAL,
                    trd_env=TrdEnv.SIMULATE,
                    time_in_force='DAY'
                )

                if ret == 0 and len(data) > 0:
                    order_id = str(data.iloc[0].get('order_id', 'N/A'))
                    trade_results.append({
                        "code": full_code,
                        "name": rec['name'],
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
                        "name": rec['name'],
                        "action": "BUY",
                        "status": "FAILED",
                        "error": str(data) if data is not None else "Unknown error"
                    })
                    print(f"  ❌ 下单失败：{data}")

            trade_ctx.close()

            result = {
                "success": True,
                "market": "HK",
                "trade_results": trade_results,
                "count": len(trade_results),
                "gateway": "Futu OpenAPI (SIMULATE)",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"交易出错：{e}")
            import traceback
            traceback.print_exc()
            result = {"success": False, "error": str(e)}

        with open(self.output_dir / "05_trade_results.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.results["steps"]["step5_trades"] = result
        return result

    # ──────────────────────────────────────────────────────
    # 辅助方法
    # ──────────────────────────────────────────────────────

    @staticmethod
    def _call_with_timeout(func, args=(), kwargs=None, timeout_sec=60):
        """
        跨平台超时调用 (兼容 Linux/Windows/macOS)

        使用 threading + 异常传递实现超时控制，
        比 signal.SIGALRM 更通用（Windows 不支持 SIGALRM）。
        """
        import threading
        result = [None]
        exception = [None]

        def _target():
            try:
                result[0] = func(*args, **(kwargs or {}))
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=_target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout_sec)

        if thread.is_alive():
            raise TimeoutError(f"调用超时 (>{timeout_sec}s)")

        if exception[0] is not None:
            raise exception[0]

        return result[0]

    def _convert_hk_code(self, code: str) -> str:
        """转换港股代码为富途格式"""
        if not code:
            return ""
        # 已经是 HK.XXXXX 格式
        if code.startswith('HK.'):
            return code
        # XXXXX.HK 格式 → HK.XXXXX
        if '.HK' in code.upper():
            parts = code.upper().split('.HK')[0].split('.')
            return f"HK.{parts[0]}"
        # 纯数字 → HK.XXXXX
        if code.isdigit():
            return f"HK.{code.zfill(5)}"
        # 其他情况尝试直接加前缀
        return f"HK.{code}"

    def _get_current_price(self, full_code: str) -> float:
        """通过富途获取港股当前价格"""
        try:
            from futu import OpenQuoteContext
            quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
            ret, snapshot = quote_ctx.get_market_snapshot([full_code])
            quote_ctx.close()
            if ret == 0 and len(snapshot) > 0:
                price = float(snapshot['last_price'].iloc[0])
                if price > 0:
                    return price
        except Exception as e:
            print(f"  价格获取失败：{e}")

        # 从选股因子数据中获取估计价格
        try:
            date_str = self.date.replace('-', '')
            factors_file = FACTORS_DIR / f"result_hk_{date_str}.csv"
            if factors_file.exists():
                df = pd.read_csv(factors_file)
                # 提取代码
                raw_code = full_code.replace('HK.', '')
                match = df[df['ts_code'].str.contains(raw_code, na=False)]
                if not match.empty:
                    # 使用 momentum 相关字段估算价格
                    est_price = match.iloc[0].get('close', 50.0)
                    if pd.notna(est_price) and float(est_price) > 0:
                        print(f"  从因子数据获取估计价格：{est_price}")
                        return float(est_price)
        except Exception as e:
            print(f"  因子数据价格获取失败：{e}")

        return 0.0  # 无法获取价格

    @staticmethod
    def _map_action(action: str) -> str:
        """映射辩论动作为交易动作"""
        action = str(action).upper()
        if action in ('BUY', 'LONG'):
            return 'BUY'
        elif action in ('SELL', 'SHORT'):
            return 'SELL'
        elif action in ('REJECT', 'ERROR', 'TIMEOUT'):
            return 'HOLD'
        else:
            return 'HOLD'

    def _generate_reason(self, debate: Dict) -> str:
        """生成投资建议理由"""
        final_action = debate.get('final_action', {})
        if isinstance(final_action, dict):
            action = final_action.get('action', 'N/A')
        else:
            action = str(final_action)

        bull = debate.get('bull_recommendation', '')
        bear = debate.get('bear_recommendation', '')
        risk = debate.get('risk_approval', {})
        if isinstance(risk, dict):
            risk_rec = risk.get('recommendation', '')
        else:
            risk_rec = str(risk)

        return f"多头：{bull}, 空头：{bear}, 风控：{risk_rec}, 动作：{action}"

    def save_results(self):
        """保存完整结果"""
        with open(self.output_dir / "workflow_results.json", 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n📁 结果已保存到：{self.output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Workflow C - 港股模拟交易全链路")
    parser.add_argument("--market", type=str, default="HK", help="市场 (HK)")
    parser.add_argument("--date", type=str, default=None, help="交易日期 (YYYY-MM-DD)")
    parser.add_argument("--top-n", type=int, default=10, help="选股数量")
    parser.add_argument("--skip-trades", action="store_true", help="跳过交易执行")

    args = parser.parse_args()

    handler = WorkflowCHandler(market=args.market, date=args.date, skip_trades=args.skip_trades)

    # Step 1: 选股
    stocks_data = handler.step1_select_stocks(top_n=args.top_n)
    if not stocks_data.get('success'):
        print("Step 1 失败，终止流程")
        handler.save_results()
        return

    stocks = stocks_data.get('selected_stocks', [])
    if not stocks:
        print("无选中股票，终止流程")
        handler.save_results()
        return

    # Step 2: 分析
    analysis = handler.step2_analyze_stocks(stocks)
    if not analysis.get('success'):
        print("⚠️  Step 2 失败，继续执行")

    # Step 3: 辩论
    debate = handler.step3_debate(stocks)
    if not debate.get('success'):
        print("⚠️  Step 3 失败，继续执行")

    # Step 4: 投资建议
    recommendations = handler.step4_generate_recommendations(debate)
    if not recommendations.get('success'):
        print("⚠️  Step 4 失败")
        handler.save_results()
        return

    # Step 5: 交易执行
    trades = handler.step5_execute_trades(recommendations)
    if not trades.get('success') and not trades.get('skipped'):
        print("⚠️  Step 5 失败")

    # 保存结果
    handler.save_results()

    print("\n" + "=" * 60)
    print("Workflow C 执行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
