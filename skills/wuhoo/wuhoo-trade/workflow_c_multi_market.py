#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow C - 多市场全链路执行脚本 (统一版)

支持市场:
- CN: A 股 (中证 1000) - 使用 Tushare 数据 + 简化分析
- HK: 港股 (Top 500) - 使用富途数据 + DataAggregator 完整分析
- US: 美股 (Top 500) - 使用 yfinance 数据 + 完整因子

流程:
1. 选股 → 2. 多维度分析 → 3. 多空辩论 →
4. 投资建议 → 5. 风控检查 → 6. 交易执行 → 7. 每日复盘

每个步骤均可独立跳过，便于回测和调试。

用法:
    source venv-futu/bin/activate
    python workflow_c_multi_market.py --market cn --date 2026-04-15
    python workflow_c_multi_market.py --market hk --date 2026-04-15 --skip-debate
    python workflow_c_multi_market.py --market us --date 2026-04-15 --skip-trades

跳过开关:
    --skip-select          跳过选股，读取已有选股结果
    --skip-analysis        跳过多维度分析
    --skip-debate          跳过辩论环节（观察无非结构化信息影响）
    --skip-trades          跳过交易执行（仅分析）
    --skip-review          跳过每日复盘
"""

import os
import sys
import json
import argparse
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# 添加路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# 加载环境变量 (从 ~/.hermes/.env)
env_file = Path.home() / '.hermes' / '.env'
if env_file.exists():
    print(f"加载环境变量：{env_file}")
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value
                    print(f"  {key}=***")

# 环境变量配置
os.environ['FUTU_HOST'] = '127.0.0.1'
os.environ['FUTU_PORT'] = '11111'
os.environ['FUTU_ENV'] = 'SIMULATE'

# 路径常量
STOCK_PICK_SCRIPT = Path.home() / 'wuhoo-workspace' / 'skills' / 'wuhoo' / 'wuhoo-stock-pick' / 'stock_pick.py'
STOCK_PICK_VENV = None  # 统一使用系统 python3.11
DEBATE_PATH = Path.home() / 'wuhoo-workspace' / 'skills' / 'wuhoo' / 'wuhoo-debate'
FACTORS_DIR = Path.home() / 'wuhoo-workspace' / 'data' / 'stock-pick' / 'factors'

# 市场配置
MARKET_CONFIG = {
    'cn': {
        'name': 'A 股 (中证 1000)',
        'gateway': 'Futu OpenAPI',
        'acc_id': 18767295,  # CN账户不存在，需使用REAL账户
        'time_in_force': 'DAY',
        'min_qty': 100,
        'price_premium': 0.0,
        'analysis_mode': 'simplified',
        'debate_mode': 'simplified',
    },
    'hk': {
        'name': '港股 (Top 500)',
        'gateway': 'Futu OpenAPI',
        'acc_id': 18767294,
        'time_in_force': 'DAY',
        'min_qty': 100,
        'price_premium': 0.01,
        'analysis_mode': 'full',
        'debate_mode': 'full',
    },
    'us': {
        'name': '美股 (Top 500)',
        'gateway': 'Futu OpenAPI',
        'acc_id': 18767296,
        'time_in_force': 'DAY',
        'min_qty': 1,
        'price_premium': 0.01,
        'analysis_mode': 'simplified',
        'debate_mode': 'quick',
    },
}


class WorkflowCHandler:
    """Workflow C 执行处理器（统一版，支持步骤级跳过）"""

    def __init__(self, market: str = "HK", date: str = None,
                 skip_select: bool = False, skip_analysis: bool = False,
                 skip_debate: bool = False, skip_trades: bool = False,
                 skip_review: bool = False, top_n: int = 10):
        self.market = market.lower()
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.top_n = top_n
        self.skip_flags = {
            'select': skip_select,
            'analysis': skip_analysis,
            'debate': skip_debate,
            'trades': skip_trades,
            'review': skip_review,
        }

        self.config = MARKET_CONFIG.get(self.market, {})
        self.results = {
            "workflow": "C",
            "market": self.market.upper(),
            "date": self.date,
            "skip_flags": self.skip_flags,
            "steps": {}
        }

        self.output_dir = SCRIPT_DIR / "data" / "workflow_c" / f"{self.market.upper()}_{self.date}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        skip_summary = ", ".join([k for k, v in self.skip_flags.items() if v]) or "无"
        print("=" * 60)
        print(f"Workflow C - {self.config.get('name', self.market.upper())} 全链路")
        print(f"日期：{self.date} | Top-N: {self.top_n}")
        print(f"跳过步骤：{skip_summary}")
        print("=" * 60)

    # ──────────────────────────────────────────────────────
    # 超时保护工具
    # ──────────────────────────────────────────────────────

    @staticmethod
    def _call_with_timeout(func, args=(), kwargs=None, timeout_sec=60):
        """跨平台超时调用 (兼容 Linux/Windows/macOS)"""
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

    # ──────────────────────────────────────────────────────
    # Step 1: 选股
    # ──────────────────────────────────────────────────────

    def step1_select_stocks(self, top_n: int = 10) -> Dict:
        """
        Step 1: 选股

        调用 stock_pick.py 进行选股。
        超时保护 (5 分钟)，结果验证。
        """
        print("\n" + "=" * 60)
        print(f"Step 1: 选股 ({self.market.upper()})")
        print("=" * 60)

        if not STOCK_PICK_SCRIPT.exists():
            error_msg = f"选股脚本不存在：{STOCK_PICK_SCRIPT}"
            print(f"❌ {error_msg}")
            result = {"success": False, "error": error_msg}
            self.results["steps"]["step1_select_stocks"] = result
            return result

        date_str = self.date.replace('-', '')
        result_file = FACTORS_DIR / f"result_{self.market}_{date_str}.csv"

        try:
            python_cmd = sys.executable
            if STOCK_PICK_VENV.parent.parent.exists():
                python_cmd = str(STOCK_PICK_VENV.parent.parent / 'bin' / 'python')

            cmd = [
                python_cmd,
                str(STOCK_PICK_SCRIPT),
                '--market', self.market,
                '--date', self.date,
                '--top-n', str(top_n),
            ]

            print(f"执行选股: {' '.join(cmd)}")
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=300
            )

            if proc.stdout:
                print(proc.stdout[-2000:])  # 只打印最后 2000 字符
            if proc.stderr:
                print(proc.stderr[-1000:])

            if proc.returncode != 0:
                error_msg = f"选股脚本执行失败 (exit code={proc.returncode})"
                print(f"❌ {error_msg}")
                result = {"success": False, "error": error_msg}
                self.results["steps"]["step1_select_stocks"] = result
                return result

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

            top_stocks = df.head(top_n)
            selected_list = top_stocks.to_dict('records')

            step_result = {
                "success": True,
                "market": self.market.upper(),
                "total_candidates": len(df),
                "selected_count": len(selected_list),
                "selected_stocks": selected_list,
                "top_n": top_n,
                "result_file": str(result_file),
                "timestamp": datetime.now().isoformat()
            }

            print(f"\n✅ 选股完成：{len(selected_list)} 只 (从 {len(df)} 只候选)")

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

        市场差异:
        - CN/US: 简化分析 (基于选股因子)
        - HK: 使用 Debate DataAggregator 完整分析
        """
        print("\n" + "=" * 60)
        print(f"Step 2: 多维度分析 ({self.market.upper()})")
        print("=" * 60)

        if not stocks:
            print("⚠️  无股票可分析")
            result = {"success": False, "error": "无股票可分析"}
            self.results["steps"]["step2_analyze"] = result
            return result

        analysis_mode = self.config.get('analysis_mode', 'simplified')

        # CN/US: 简化分析
        if analysis_mode == 'simplified':
            return self._analyze_simplified(stocks)

        # HK: 完整分析
        return self._analyze_full(stocks)

    def _analyze_simplified(self, stocks: List[Dict]) -> Dict:
        """简化分析 (CN/US)"""
        market_label = "A 股" if self.market == 'cn' else "美股"
        print(f"{market_label}市场：使用简化分析模式 (基于因子数据)")

        analysis_results = []
        for stock in stocks[:5]:
            code = stock.get('ts_code', stock.get('code', ''))
            name = stock.get('name', '')

            if self.market == 'us':
                residual_vol = stock.get('residual_vol', 25)
                momentum_5d = stock.get('momentum_5d', 0)
                beta = stock.get('beta_20d', 1)

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
                    "recommendation": "BUY" if score >= 7 else "HOLD",
                    "timestamp": datetime.now().isoformat()
                }
                print(f"  {code} {name}: 评分={analysis['score']:.1f}")
            else:
                analysis = {
                    "code": code,
                    "name": name,
                    "score": stock.get('composite_score', 5.0),
                    "momentum_10d": stock.get('momentum_10d', 0),
                    "recommendation": "HOLD",
                    "timestamp": datetime.now().isoformat()
                }
                print(f"  {code} {name}: 10 日 ROC={stock.get('momentum_10d', 'N/A')}")

            analysis_results.append(analysis)

        result = {
            "success": True,
            "analyzed_count": len(analysis_results),
            "analysis_results": analysis_results,
            "market": self.market,
            "method": "simplified",
            "timestamp": datetime.now().isoformat()
        }

        with open(self.output_dir / "02_analysis_results.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.results["steps"]["step2_analyze"] = result
        return result

    def _analyze_full(self, stocks: List[Dict]) -> Dict:
        """完整分析 (HK) - 使用 DataAggregator"""
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
        stocks_to_analyze = stocks[:5]

        print(f"分析股票数量：{len(stocks_to_analyze)}")

        for i, stock in enumerate(stocks_to_analyze):
            code = stock.get('ts_code', stock.get('code', ''))
            name = stock.get('name', '')

            print(f"\n[{i+1}/{len(stocks_to_analyze)}] 分析 {code} {name}...")

            try:
                data = self._call_with_timeout(
                    aggregator.get_all_data,
                    args=(code, name),
                    timeout_sec=60
                )

                if data is None:
                    print(f"  ⚠️  {code} 分析超时，跳过")
                    analysis_results.append({
                        "code": code, "name": name,
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
                print(f"  技术信号：{analysis['technical_signal']}")
                print(f"  数据质量：{analysis['data_quality']}")

            except TimeoutError:
                print(f"  ⚠️  {code} 分析超时 (60s)")
                analysis_results.append({
                    "code": code, "name": name,
                    "error": "analysis_timeout",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"  ❌  {code} 分析失败：{e}")
                analysis_results.append({
                    "code": code, "name": name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

        result = {
            "success": True,
            "analyzed_count": len(analysis_results),
            "analysis_results": analysis_results,
            "market": self.market,
            "method": "full",
            "timestamp": datetime.now().isoformat()
        }

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

        市场差异:
        - CN: 简化辩论 (基于动量)
        - HK: 完整辩论 (Bull/Bear/Trader/Risk)
        - US: 快速辩论 (基于因子评分)
        """
        print("\n" + "=" * 60)
        print(f"Step 3: 多空辩论 ({self.market.upper()})")
        print("=" * 60)

        if not stocks:
            return {"success": False, "error": "无股票可辩论"}

        debate_mode = self.config.get('debate_mode', 'simplified')

        if debate_mode == 'full':
            return self._debate_full(stocks)
        elif debate_mode == 'quick':
            return self._debate_quick(stocks)
        else:
            return self._debate_simplified(stocks)

    def _debate_simplified(self, stocks: List[Dict]) -> Dict:
        """简化辩论 (CN) - 基于动量判断"""
        print("A 股市场：使用简化辩论 (基于动量)")

        debate_results = []
        for stock in stocks[:5]:
            code = stock.get('ts_code', '')
            name = stock.get('name', '')
            momentum = stock.get('momentum_10d', 0)

            recommendation = "BUY" if momentum < -5 else "HOLD"

            debate_results.append({
                "code": code, "name": name,
                "recommendation": recommendation,
                "confidence": 0.5,
                "method": "simplified",
                "timestamp": datetime.now().isoformat()
            })
            print(f"  {code} {name}: {recommendation} (动量={momentum:.2f})")

        return self._save_debate_results(debate_results, method="simplified")

    def _debate_quick(self, stocks: List[Dict]) -> Dict:
        """快速辩论 (US) - 基于因子评分 + RiskAgent 风控"""
        print("美股市场：使用快速辩论分析 + RiskAgent 风控")
        
        # 导入 RiskAgent
        sys.path.insert(0, str(DEBATE_PATH))
        try:
            from agents.risk_agent import RiskAgent
            risk_agent = RiskAgent()
        except ImportError:
            risk_agent = None
            print("  ⚠️ RiskAgent 不可用，使用简化风控")
        
        debate_results = []
        for stock in stocks[:5]:
            code = stock.get('ts_code', '')
            name = stock.get('name', '')
            residual_vol = stock.get('residual_vol', 25)
            momentum_5d = stock.get('momentum_5d', 0)
            momentum_10d = stock.get('momentum_10d', 0)
            beta = stock.get('beta_20d', 1)
            current_price = stock.get('price', 100)  # 假设价格
            
            bull_points = []
            bear_points = []
            
            if residual_vol < 20:
                bull_points.append("低残差波动")
            elif residual_vol > 23:
                bear_points.append("波动率偏高")
                
            if momentum_5d > 3:
                bull_points.append("强势动量")
            elif momentum_5d < 1.5:
                bear_points.append("动量疲软")
                
            if momentum_10d > 5:
                bear_points.append("短期涨幅过大")
                
            if 0.9 <= beta <= 1.3:
                bull_points.append("Beta 适中")
            elif beta > 1.4:
                bear_points.append("高 Beta 风险")
            
            bull_score = len(bull_points)
            bear_score = len(bear_points)
            
            if bull_score > bear_score:
                recommendation = "BUY"
                confidence = 0.5 + (bull_score - bear_score) * 0.1
                target_price = current_price * (1 + momentum_5d / 100)  # 动量推算目标价
            elif bear_score > bull_score:
                recommendation = "SELL"
                confidence = 0.5 + (bear_score - bull_score) * 0.1
                target_price = current_price * (1 - momentum_5d / 100)
            else:
                recommendation = "HOLD"
                confidence = 0.5
                target_price = current_price
            
            # 构建交易决策 (供 RiskAgent 审核)
            stop_loss_price = current_price * 0.92  # 8%止损
            take_profit_price = target_price
            potential_profit = take_profit_price - current_price
            potential_loss = current_price - stop_loss_price
            rrr = potential_profit / potential_loss if potential_loss > 0 else 0
            
            trader_decision = {
                "decision": recommendation,
                "confidence": confidence,
                "position_size": min(0.15, confidence * 0.2),  # 最大15%仓位
                "risk_reward_ratio": rrr,
                "action": {
                    "side": "buy" if recommendation == "BUY" else "sell" if recommendation == "SELL" else "hold",
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price
                }
            }
            
            # RiskAgent 审核
            if risk_agent:
                market_data = {
                    "volatility": residual_vol / 100,  # 残差波动率作为波动率代理
                    "daily_turnover": stock.get('turnover', 100000000),  # 假设流动性充足
                }
                risk_approval = risk_agent.review(
                    symbol=code,
                    trader_decision=trader_decision,
                    market_data=market_data
                )
            else:
                # 简化版风控 (无RiskAgent时)
                risk_factors = []
                if residual_vol > 22: risk_factors.append("vol_high")
                if momentum_10d > 5: risk_factors.append("gain_large")
                if beta > 1.3: risk_factors.append("beta_high")
                
                if len(risk_factors) >= 2:
                    risk_approval = {"recommendation": "REJECT", "risk_score": 0.8}
                elif len(risk_factors) == 1:
                    risk_approval = {"recommendation": "CONDITIONAL", "risk_score": 0.5}
                else:
                    risk_approval = {"recommendation": "APPROVE", "risk_score": 0.2}
            
            # 最终动作 — 严格风控
            risk_rec = risk_approval.get("recommendation", "APPROVE")
            if risk_rec == "REJECT":
                final_action = "reject"
                print(f"    🔴 RiskAgent REJECT → 排除")
            elif risk_rec == "CONDITIONAL":
                # CONDITIONAL: 仅当散户风控也通过时才放行
                if recommendation == "BUY" and confidence > 0.7 and rrr >= 2.5:
                    final_action = "buy"
                    print(f"    🟡 RiskAgent CONDITIONAL → 收紧条件后放行 (conf>{0.7}, RRR>{2.5})")
                else:
                    final_action = "watch"
                    print(f"    🟡 RiskAgent CONDITIONAL → 转为观望 (conf={confidence:.0%}, RRR={rrr:.2f})")
            elif recommendation == "BUY" and confidence > 0.6 and rrr >= 2.0:
                final_action = "buy"
            else:
                final_action = "watch"
            
            debate_results.append({
                "code": code, "name": name,
                "bull_points": bull_points,
                "bear_points": bear_points,
                "recommendation": recommendation,
                "confidence": round(confidence, 2),
                "risk_approval": risk_approval.get("recommendation", "N/A"),
                "risk_score": risk_approval.get("risk_score", 0),
                "rrr": round(rrr, 2),
                "final_action": final_action,
                "method": "quick",
                "timestamp": datetime.now().isoformat()
            })
            print(f"  {code} {name}: {recommendation} (置信度{confidence:.0%}, RRR={rrr:.2f}), 风控:{risk_approval.get('recommendation')}")
        
        return self._save_debate_results(debate_results, method="quick")

    def _debate_full(self, stocks: List[Dict]) -> Dict:
        """完整辩论 (HK) - Bull/Bear/Trader/Risk"""
        sys.path.insert(0, str(DEBATE_PATH))

        try:
            from run_debate import run_full_debate
        except ImportError as e:
            error_msg = f"无法导入 run_full_debate: {e}"
            print(f"❌ {error_msg}")
            result = {"success": False, "error": error_msg, "debate_results": []}
            self.results["steps"]["step3_debate"] = result
            return result

        debate_results = []
        stocks_to_debate = stocks[:3]

        for stock in stocks_to_debate:
            code = stock.get('ts_code', stock.get('code', ''))
            name = stock.get('name', '')

            print(f"\n辩论：{code} {name}...")

            try:
                debate_result = self._call_with_timeout(
                    run_full_debate,
                    kwargs={"symbol": code, "company_name": name, "use_real_data": True},
                    timeout_sec=300
                )

                if debate_result is None:
                    print(f"  ⚠️  辩论超时 (300s)")
                    debate_results.append({
                        "code": code, "name": name,
                        "error": "debate_timeout", "final_action": "timeout",
                        "timestamp": datetime.now().isoformat()
                    })
                    continue

                debate_results.append({
                    "code": code, "name": name,
                    "bull_recommendation": debate_result.get('bull_view', {}).get('recommendation'),
                    "bear_recommendation": debate_result.get('bear_view', {}).get('recommendation'),
                    "trader_decision": debate_result.get('trader_decision', {}),
                    "risk_approval": debate_result.get('risk_approval', {}),
                    "final_action": debate_result.get('final_action', {}),
                    "bull_points": debate_result.get('bull_view', {}).get('bullish_points', []),
                    "bear_points": debate_result.get('bear_view', {}).get('bearish_points', []),
                    "consensus": debate_result.get('consensus_points', []),
                    "timestamp": datetime.now().isoformat()
                })

                final = debate_result.get('final_action', {})
                if isinstance(final, dict):
                    print(f"  最终动作：{final.get('action', 'N/A')}")
                else:
                    print(f"  最终动作：{final}")

            except TimeoutError:
                print(f"  ⚠️  辩论超时 (300s)")
                debate_results.append({
                    "code": code, "name": name,
                    "error": "debate_timeout", "final_action": "timeout",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"  ❌  辩论失败：{e}")
                debate_results.append({
                    "code": code, "name": name,
                    "error": str(e), "final_action": "error",
                    "timestamp": datetime.now().isoformat()
                })

        return self._save_debate_results(debate_results, method="full")

    def _save_debate_results(self, debate_results: List[Dict], method: str = "unknown") -> Dict:
        """保存辩论结果"""
        result = {
            "success": True,
            "debate_results": debate_results,
            "count": len(debate_results),
            "method": method,
            "timestamp": datetime.now().isoformat()
        }

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

        支持 full_debate / quick / simplified 三种辩论格式
        """
        print("\n" + "=" * 60)
        print("Step 4: 生成投资建议")
        print("=" * 60)

        recommendations = []
        method = debate_results.get('method', 'unknown')

        for debate in debate_results.get('debate_results', []):
            code = debate.get('code', '')
            name = debate.get('name', '')

            if method == 'quick':
                action = debate.get('final_action', 'watch').upper()
                if action in ['BUY']:
                    action = 'BUY'
                elif action in ['REJECT', 'WATCH']:
                    action = 'HOLD'
                confidence = debate.get('confidence', 0.5)
                reason = f"快速辩论：{debate.get('recommendation', 'N/A')}, 风控:{debate.get('risk_approval', 'N/A')}"

            elif method == 'full':
                risk_approval = debate.get('risk_approval', {})
                trader_decision = debate.get('trader_decision', {})

                if isinstance(risk_approval, dict) and risk_approval.get('recommendation') == 'REJECT':
                    action = 'REJECT'
                elif isinstance(trader_decision, dict) and trader_decision.get('decision') == 'BUY':
                    action = 'BUY'
                elif isinstance(trader_decision, dict) and trader_decision.get('decision') == 'SELL':
                    action = 'SELL'
                else:
                    action = 'HOLD'

                confidence = 0.7
                td = trader_decision.get('decision', 'N/A') if isinstance(trader_decision, dict) else 'N/A'
                ra = risk_approval.get('recommendation', 'N/A') if isinstance(risk_approval, dict) else 'N/A'
                reason = f"完整辩论：交易员决策={td}, 风控={ra}"

            else:
                # simplified
                rec = debate.get('recommendation', 'HOLD')
                action = 'BUY' if rec == 'BUY' else 'HOLD'
                confidence = debate.get('confidence', 0.5)
                reason = f"简化辩论：{rec}"

            recommendations.append({
                "code": code, "name": name,
                "action": action,
                "confidence": confidence,
                "reason": reason,
                "bull_points": debate.get('bull_points', []),
                "bear_points": debate.get('bear_points', []),
                "timestamp": datetime.now().isoformat()
            })
            print(f"  {code} {name}: {action} (置信度{confidence:.0%})")

        result = {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations),
            "method": method,
            "timestamp": datetime.now().isoformat()
        }

        with open(self.output_dir / "04_recommendations.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.results["steps"]["step4_recommendations"] = result
        return result

    # ──────────────────────────────────────────────────────
    # Step 5: 执行交易
    # ──────────────────────────────────────────────────────

    def step5_execute_trades(self, recommendations: Dict) -> Dict:
        """
        Step 5: 执行交易 (统一富途 OpenAPI)

        市场差异通过 MARKET_CONFIG 配置:
        - CN: acc_id=18767295, min_qty=100, DAY
        - HK: acc_id=18767294, min_qty=100, DAY
        - US: acc_id=18767296, min_qty=1, DAY
        """
        print("\n" + "=" * 60)
        print("Step 5: 执行交易")
        print("=" * 60)

        if self.skip_flags.get('trades'):
            print("⏭️  跳过交易执行 (--skip-trades)")
            result = {"success": True, "skipped": True, "reason": "skip-trades flag"}
            self.results["steps"]["step5_trades"] = result
            return result

        acc_id = self.config.get('acc_id')
        market_ctx = self.config.get('name', self.market.upper())
        print(f"市场：{market_ctx} | 账户：{acc_id}")

        return self._execute_trades_direct(recommendations, self.market, acc_id)

    def _execute_trades_direct(self, recommendations: Dict, market: str, acc_id: int) -> Dict:
        """统一交易执行方法"""
        if market == 'cn':
            from futu import OpenCNTradeContext as TradeContext, OrderType, TrdSide, TrdEnv
        elif market == 'hk':
            from futu import OpenHKTradeContext as TradeContext, OrderType, TrdSide, TrdEnv
        elif market == 'us':
            from futu import OpenUSTradeContext as TradeContext, OrderType, TrdSide, TrdEnv
        else:
            result = {"success": False, "error": f"不支持的市场：{market}"}
            self.results["steps"]["step5_trades"] = result
            return result

        trade_results = []

        try:
            trade_ctx = TradeContext(host='127.0.0.1', port=11111)
            password = os.environ.get('FUTU_TRADING_PASSWORD', os.environ.get('FUTU_PASSWORD', ''))
            trade_ctx.unlock_trade(password)

            min_qty = self.config.get('min_qty', 100)
            price_premium = self.config.get('price_premium', 0.0)
            time_in_force = self.config.get('time_in_force', 'DAY')

            for rec in recommendations.get('recommendations', []):
                if rec.get('action') != 'BUY':
                    continue

                code = rec.get('code', '')
                name = rec.get('name', '')
                if not code:
                    continue

                full_code = self._convert_code(code, market)
                order_price = self._get_price(full_code, market)

                qty = min_qty
                if price_premium > 0:
                    order_price = round(order_price * (1 + price_premium), 2)
                else:
                    order_price = round(order_price, 2)

                print(f"下单：{name} ({full_code}) BUY {qty} @ {order_price}")

                # ── 单笔风控检查 (risk_manager) ──
                try:
                    from risk_manager import risk_check
                    order_for_risk = {
                        'code': full_code, 'side': 'buy', 'price': order_price,
                        'qty': qty, 'amount': order_price * qty,
                    }
                    risk_result = risk_check(order_for_risk)
                    if risk_result.get('approved') == False:
                        print(f"  🔴 风控拒绝: {risk_result.get('reason', 'unknown')}")
                        trade_results.append({
                            "code": code, "name": name,
                            "status": "rejected_by_risk",
                            "reason": risk_result.get('reason', ''),
                        })
                        continue
                    elif risk_result.get('warning'):
                        print(f"  🟡 风控警告: {risk_result.get('warning')}")
                except ImportError:
                    pass  # risk_manager 不可用时跳过

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
                        "code": full_code, "name": name,
                        "action": "BUY", "price": order_price, "qty": qty,
                        "order_id": order_id, "status": "SUBMITTED"
                    })
                    print(f"  ✅ 下单成功，订单 ID: {order_id}")
                else:
                    trade_results.append({
                        "code": full_code, "name": name,
                        "action": "BUY", "status": "FAILED",
                        "error": str(data) if data is not None else "Unknown error"
                    })
                    print(f"  ❌ 下单失败：{data}")

            trade_ctx.close()

            result = {
                "success": True,
                "market": market.upper(),
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

    def _convert_code(self, code: str, market: str) -> str:
        """代码格式转换"""
        if not code:
            return ""

        # 已是富途格式
        if '.' in code and code.split('.')[0].upper() in ['SH', 'SZ', 'HK', 'US']:
            return code

        if market == 'cn':
            # A 股: 603220.SH -> SH.603220
            parts = code.split('.')
            if len(parts) == 2:
                exchange = parts[1].upper()
                stock_code = parts[0]
                return f"{exchange}.{stock_code}"
            return f"SH.{code}" if code.startswith('6') else f"SZ.{code}"

        elif market == 'hk':
            if code.startswith('HK.'):
                return code
            if '.HK' in code.upper():
                parts = code.upper().split('.HK')[0].split('.')
                return f"HK.{parts[0]}"
            if code.isdigit():
                return f"HK.{code.zfill(5)}"
            return f"HK.{code}"

        elif market == 'us':
            if code.startswith('US.'):
                return code
            if '.US' in code.upper():
                return f"US.{code.upper().split('.US')[0]}"
            return f"US.{code}"

        return code

    def _get_price(self, full_code: str, market: str) -> float:
        """获取当前价格 (富途快照)"""
        try:
            if market == 'cn':
                from futu import OpenQuoteContext
            elif market == 'hk':
                from futu import OpenQuoteContext
            else:
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

        # 从选股因子数据获取估计价格
        try:
            date_str = self.date.replace('-', '')
            factors_file = FACTORS_DIR / f"result_{self.market}_{date_str}.csv"
            if factors_file.exists():
                df = pd.read_csv(factors_file)
                raw_code = full_code.split('.')[-1]
                match = df[df['ts_code'].str.contains(raw_code, na=False)]
                if not match.empty:
                    est_price = match.iloc[0].get('close', 50.0)
                    if pd.notna(est_price) and float(est_price) > 0:
                        return float(est_price)
        except Exception:
            pass

        return 50.0  # fallback

    def save_results(self):
        """保存完整结果"""
        with open(self.output_dir / "workflow_results.json", 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n📁 结果已保存到：{self.output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Workflow C - 多市场全链路执行脚本 (统一版)")
    parser.add_argument("--market", type=str, default="hk", choices=['cn', 'hk', 'us'],
                        help="市场 (cn/hk/us)")
    parser.add_argument("--date", type=str, default=None, help="交易日期 (YYYY-MM-DD)")
    parser.add_argument("--top-n", type=int, default=10, help="选股数量")

    # 步骤级跳过开关
    parser.add_argument("--skip-select", action="store_true", help="跳过选股")
    parser.add_argument("--skip-analysis", action="store_true", help="跳过分析")
    parser.add_argument("--skip-debate", action="store_true", help="跳过辩论")
    parser.add_argument("--debate-file", type=str, default=None,
                        help="加载外部辩论结果JSON (来自 batch_debate.py 的 debate_summary.json)")
    parser.add_argument("--skip-trades", action="store_true", help="跳过交易")
    parser.add_argument("--skip-review", action="store_true", help="跳过复盘")

    args = parser.parse_args()

    handler = WorkflowCHandler(
        market=args.market,
        date=args.date,
        skip_select=args.skip_select,
        skip_analysis=args.skip_analysis,
        skip_debate=args.skip_debate,
        skip_trades=args.skip_trades,
        skip_review=args.skip_review,
        top_n=args.top_n,
    )

    # Step 1: 选股
    if handler.skip_flags['select']:
        print("\n⏭️  跳过选股，尝试读取已有结果...")
        result_file = handler.output_dir / "01_selected_stocks.json"
        if result_file.exists():
            stocks_data = json.load(open(result_file))
            print(f"  已加载选股结果：{stocks_data.get('selected_count', 0)} 只")
        else:
            # 尝试从 factors 目录加载
            date_str = args.date.replace('-', '') if args.date else datetime.now().strftime('%Y%m%d')
            factors_file = FACTORS_DIR / f"result_{args.market}_{date_str}.csv"
            if factors_file.exists():
                df = pd.read_csv(factors_file)
                stocks_data = {
                    "success": True,
                    "selected_stocks": df.head(args.top_n).to_dict('records'),
                    "selected_count": min(len(df), args.top_n),
                }
                print(f"  从 factors 加载：{stocks_data['selected_count']} 只")
            else:
                print("  ❌ 无可用选股结果，请先运行选股")
                handler.save_results()
                return
    else:
        stocks_data = handler.step1_select_stocks(top_n=args.top_n)
        if not stocks_data.get('success'):
            print("❌ Step 1 失败，终止流程")
            handler.save_results()
            return

    stocks = stocks_data.get('selected_stocks', [])
    if not stocks:
        print("⚠️  无选中股票，终止流程")
        handler.save_results()
        return

    # Step 2: 分析
    if handler.skip_flags['analysis']:
        print("\n⏭️  跳过分析")
        analysis = {"success": True, "skipped": True}
    else:
        analysis = handler.step2_analyze_stocks(stocks)
        if not analysis.get('success'):
            print("⚠️  Step 2 失败，继续执行")

    # Step 3: 辩论
    if handler.skip_flags['debate']:
        print("\n⏭️  跳过辩论 (--skip-debate)")
        debate = {"success": True, "skipped": True, "debate_results": []}

        # 尝试加载外部辩论结果 (--debate-file)
        if args.debate_file:
            debate_path = Path(args.debate_file)
            if debate_path.exists():
                print(f"📥 加载外部辩论结果: {debate_path}")
                try:
                    with open(debate_path, 'r', encoding='utf-8') as f:
                        external = json.load(f)
                    # batch_debate.py 产出的 debate_summary.json 格式:
                    # {"results": [{"symbol", "bull", "bear", "trader", ...}]}
                    debate_results = []
                    for r in external.get('results', []):
                        trader = r.get('trader', {})
                        decision = trader.get('decision', 'HOLD')
                        # Trader=SELL 的股票排除买入
                        code = r.get('symbol', '')
                        debate_results.append({
                            "code": code,
                            "name": r.get('name', ''),
                            "recommendation": "BUY" if decision == "BUY" else
                                            "SELL" if decision == "SELL" else "HOLD",
                            "confidence": trader.get('confidence', 0.5),
                            "trader_decision": decision,
                            "risk_reward_ratio": trader.get('risk_reward_ratio', 0),
                            "key_disagreement": trader.get('key_disagreement', ''),
                            "method": "external_batch_debate",
                        })
                    debate["debate_results"] = debate_results
                    debate["method"] = "external"
                    debate["source_file"] = str(debate_path)
                    print(f"  加载 {len(debate_results)} 条辩论结果")
                    # 统计
                    buys = sum(1 for d in debate_results if d['trader_decision'] == 'BUY')
                    sells = sum(1 for d in debate_results if d['trader_decision'] == 'SELL')
                    print(f"  BUY={buys}, SELL={sells} (SELL将在推荐阶段排除)")
                except Exception as e:
                    print(f"  ⚠️  加载辩论文件失败: {e}")
            else:
                print(f"  ⚠️  辩论文件不存在: {debate_path}")

        # 回退：如果没有外部辩论结果，将分析结果转为辩论结果
        if not debate.get("debate_results") and analysis.get('analysis_results'):
            debate_results = []
            for a in analysis['analysis_results']:
                debate_results.append({
                    "code": a.get('code', ''),
                    "name": a.get('name', ''),
                    "recommendation": a.get('recommendation', 'HOLD'),
                    "confidence": 0.5,
                })
            debate["debate_results"] = debate_results
            debate["method"] = "skipped_from_analysis"
    else:
        debate = handler.step3_debate(stocks)
        if not debate.get('success'):
            print("⚠️  Step 3 失败，继续执行")

    # Step 4: 投资建议
    recommendations = handler.step4_generate_recommendations(debate)
    if not recommendations.get('success'):
        print("⚠️  Step 4 失败")
        handler.save_results()
        return

    # ── Step 4.5: 组合级风控检查 (portfolio_risk) ──
    if not handler.skip_flags.get('trades'):
        print("\n" + "=" * 60)
        print("Step 4.5: 组合级风控检查")
        print("=" * 60)
        try:
            from portfolio_risk import PortfolioRiskChecker
            risk_checker = PortfolioRiskChecker()

            # 构建持仓快照 (模拟盘当前持仓 + 候选交易)
            positions = []
            for rec in recommendations.get('recommendations', []):
                if rec.get('action') == 'BUY':
                    positions.append({
                        'code': rec.get('code', ''),
                        'name': rec.get('name', ''),
                        'weight': rec.get('suggested_weight', 0.05),
                        'sector': rec.get('sector', 'Other'),
                    })

            total_value = 3_000_000  # ~$3M 组合总权益 (模拟盘)
            cash_ratio = 0.10  # 10% 现金保留

            risk_report = risk_checker.check_all(
                positions=positions,
                total_value=total_value,
                cash=total_value * cash_ratio,
                correlation_matrix=None,
                historical_nav=None,
                earnings_calendar=None,
                candidate_trades=[{'code': r['code'], 'side': 'buy', 'amount': r.get('suggested_weight', 0.05) * total_value}
                                  for r in recommendations.get('recommendations', [])
                                  if r.get('action') == 'BUY'],
            )

            print(f"  风控评分: {risk_report.risk_score:.2f} ({'✅ 通过' if risk_report.approved else '⚠️ 需审核'})")
            for finding in risk_report.findings:
                icon = {'critical': '🔴', 'warning': '🟡', 'info': '🔵'}.get(finding.severity, '⚪')
                print(f"  {icon} [{finding.rule_id}] {finding.message}")

            if not risk_report.approved:
                print("  ⚠️ 组合风控未通过，CONDITIONAL阻断 — 中止交易执行")
                handler.results["steps"]["step4.5_risk"] = {
                    "risk_score": risk_report.risk_score,
                    "approved": False,
                    "findings": [vars(f) for f in risk_report.findings],
                }
                handler.save_results()
                return
            else:
                handler.results["steps"]["step4.5_risk"] = {
                    "risk_score": risk_report.risk_score,
                    "approved": True,
                }

        except ImportError as e:
            print(f"  ⚠️ portfolio_risk 不可用: {e}，跳过组合风控")
        except Exception as e:
            print(f"  ⚠️ 组合风控检查异常: {e}，继续执行")

    # Step 5: 交易执行
    trades = handler.step5_execute_trades(recommendations)
    if not trades.get('success') and not trades.get('skipped'):
        print("⚠️  Step 5 失败")

    # 保存结果
    handler.save_results()

    # 审计摘要
    print("\n" + "=" * 60)
    print("审计摘要")
    print("=" * 60)
    for step_name, step_data in handler.results.get("steps", {}).items():
        status = 'SKIPPED' if step_data.get('skipped') else ('ERROR' if 'error' in step_data else 'OK')
        print(f"  {step_name}: {status}")
        if 'error' in step_data:
            print(f"    Error: {step_data['error']}")

    print("\n" + "=" * 60)
    print("Workflow C 执行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
