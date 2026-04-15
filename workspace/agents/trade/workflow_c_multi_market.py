#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow C - 多市场模拟交易全链路执行脚本 (整合美股完整因子)

支持市场:
- CN: A 股 (中证 1000) - 使用 Tushare 数据
- HK: 港股 (Top 500) - 使用富途数据
- US: 美股 (Top 500) - 使用 yfinance 数据 + 完整因子

因子配置:
- CN: 完整因子 (残差波动率 + 换手率 + 动量 + Beta)
- HK: 简化因子 (波动率 + 动量)
- US: 完整因子 (残差波动率 + 成交量 + 动量 + Beta) - 2026-03-27 升级

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
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# 添加路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# 加载环境变量 (从 ~/.openclaw/.env)
env_file = Path.home() / '.openclaw' / '.env'
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
        'acc_id': 18767299,  # 美股模拟账户
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
        self.output_dir = SCRIPT_DIR / "data" / "workflow_c" / f"{self.market}_{self.date}"
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

            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=300)

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
        
        市场差异:
        - CN: 简化分析 (直接使用选股因子)
        - HK: 使用 Debate DataAggregator
        - US: 简化分析 (美股数据源限制，使用因子数据)
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

        # A 股和美股使用简化分析 (数据源限制)
        if self.market.lower() in ['cn', 'us']:
            market_name = "A 股" if self.market.lower() == 'cn' else "美股"
            print(f"\n{market_name}市场：使用简化分析模式 (基于因子数据)")
            for stock in stocks_to_analyze:
                if self.market.lower() == 'us':
                    # 美股选股结果字段
                    code = stock.get('ts_code', stock.get('code', ''))
                    name = stock.get('name', '')
                    residual_vol = stock.get('residual_vol', 0)
                    momentum_5d = stock.get('momentum_5d', 0)
                    beta = stock.get('beta_20d', 0)
                    
                    # 简单评分
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
                else:
                    # A 股选股结果字段
                    code = stock.get('ts_code', stock.get('code', ''))
                    name = stock.get('name', '')
                    analysis = {
                        "code": code,
                        "name": name,
                        "score": stock.get('composite_score', 5.0),
                        "momentum_10d": stock.get('momentum_10d', 0),
                        "recommendation": "HOLD",
                        "timestamp": datetime.now().isoformat()
                    }
                
                analysis_results.append(analysis)
                if self.market.lower() == 'us':
                    print(f"  {code} {name}: 评分={analysis['score']:.1f}, 5 日动量={momentum_5d:.2f}%")
                else:
                    print(f"  {code} {name}: 10 日 ROC={stock.get('momentum_10d', 'N/A')}")
        else:
            # 港股使用 Debate DataAggregator
            try:
                debate_path = SCRIPT_DIR.parent / 'debate'
                sys.path.insert(0, str(debate_path))
                from adapters.data_aggregator import DataAggregator
                aggregator = DataAggregator()

                for i, stock in enumerate(stocks_to_analyze):
                    # 港股使用 ts_code 字段，A 股使用 code 字段
                    code = stock.get('ts_code', stock.get('code', ''))
                    name = stock.get('name', '')

                    print(f"\n[{i+1}/{len(stocks_to_analyze)}] 分析 {code} {name}...")

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
                import traceback
                print(f"分析出错：{e}")
                traceback.print_exc()

        result = {
            "success": True,
            "analyzed_count": len(analysis_results),
            "analysis_results": analysis_results,
            "market": self.market.lower(),
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
        
        市场差异:
        - CN: 简化辩论 (基于动量)
        - HK: 完整辩论模块 (run_full_debate)
        - US: 快速辩论分析 (基于因子，数据源限制)
        """
        print("\n" + "=" * 60)
        print("Step 3: 多空辩论")
        print("=" * 60)

        if not stocks:
            return {"error": "无股票可辩论"}

        # A 股和美股使用简化/快速辩论
        if self.market.lower() in ['cn', 'us']:
            market_name = "A 股" if self.market.lower() == 'cn' else "美股"
            print(f"{market_name}市场：使用快速辩论分析")
            
            debate_results = []
            for stock in stocks[:5]:  # 最多 5 只
                if self.market.lower() == 'us':
                    code = stock.get('ts_code', '')
                    name = stock.get('name', '')
                    residual_vol = stock.get('residual_vol', 25)
                    momentum_5d = stock.get('momentum_5d', 0)
                    momentum_10d = stock.get('momentum_10d', 0)
                    beta = stock.get('beta_20d', 1)
                    
                    # 快速多空分析
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
                    
                    # 综合判断
                    bull_score = len(bull_points)
                    bear_score = len(bear_points)
                    
                    if bull_score > bear_score:
                        recommendation = "BUY"
                        confidence = 0.5 + (bull_score - bear_score) * 0.1
                    elif bear_score > bull_score:
                        recommendation = "SELL"
                        confidence = 0.5 + (bear_score - bull_score) * 0.1
                    else:
                        recommendation = "HOLD"
                        confidence = 0.5
                    
                    # 风控检查
                    risk_factors = []
                    if residual_vol > 22: risk_factors.append("vol_high")
                    if momentum_10d > 5: risk_factors.append("gain_large")
                    if beta > 1.3: risk_factors.append("beta_high")
                    
                    if len(risk_factors) >= 2:
                        risk_approval = "REJECT"
                    elif len(risk_factors) == 1:
                        risk_approval = "CONDITIONAL"
                    else:
                        risk_approval = "APPROVE"
                    
                    final_action = "reject" if risk_approval == "REJECT" else ("buy" if recommendation == "BUY" and confidence > 0.6 else "watch")
                    
                    debate_results.append({
                        "code": code,
                        "name": name,
                        "bull_points": bull_points,
                        "bear_points": bear_points,
                        "recommendation": recommendation,
                        "confidence": round(confidence, 2),
                        "risk_approval": risk_approval,
                        "final_action": final_action,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"  {code} {name}: {recommendation} (置信度{confidence:.0%}), 风控:{risk_approval}, 最终:{final_action}")
                else:
                    # A 股简化辩论
                    code = stock.get('ts_code', '')
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
                "count": len(debate_results),
                "method": "quick_analysis" if self.market.lower() == 'us' else "simplified",
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 港股使用完整辩论模块
            try:
                debate_path = SCRIPT_DIR.parent / 'debate'
                sys.path.insert(0, str(debate_path))

                from run_debate import run_full_debate

                debate_results = []
                for stock in stocks[:3]:  # 限制数量
                    # 港股使用 ts_code 字段，A 股使用 code 字段
                    code = stock.get('ts_code', stock.get('code', ''))
                    name = stock.get('name', '')

                    print(f"\n辩论：{code} {name}...")

                    # 跨平台超时调用 (替代 signal.SIGALRM，兼容 Windows)
                    def _run_debate(_result, _exc):
                        try:
                            _result[0] = run_full_debate(code, name, use_real_data=True)
                        except Exception as e:
                            _exc[0] = e

                    debate_result = [None]
                    debate_exc = [None]
                    debate_thread = threading.Thread(target=_run_debate, args=(debate_result, debate_exc))
                    debate_thread.daemon = True
                    debate_thread.start()
                    debate_thread.join(timeout=90)  # 90 秒超时

                    if debate_thread.is_alive():
                        print(f"  ⚠️  辩论超时 (90s)，跳过")
                        debate_results.append({
                            "code": code,
                            "name": name,
                            "final_action": "timeout",
                            "error": "debate_timeout",
                            "timestamp": datetime.now().isoformat()
                        })
                    elif debate_exc[0] is not None:
                        print(f"  ❌  辩论失败：{debate_exc[0]}")
                        debate_results.append({
                            "code": code,
                            "name": name,
                            "final_action": "error",
                            "error": str(debate_exc[0]),
                            "timestamp": datetime.now().isoformat()
                        })
                    elif debate_result[0] is not None:
                        result = debate_result[0]
                        debate_results.append({
                            "code": code,
                            "name": name,
                            "bull_recommendation": result.get('bull_view', {}).get('recommendation'),
                            "bear_recommendation": result.get('bear_view', {}).get('recommendation'),
                            "trader_decision": result.get('trader_decision', {}).get('decision'),
                            "risk_approval": result.get('risk_approval', {}).get('recommendation'),
                            "final_action": result.get('final_action', {}).get('action'),
                            "bull_points": result.get('bull_view', {}).get('key_points', []),
                            "bear_points": result.get('bear_view', {}).get('key_points', []),
                            "consensus": result.get('consensus_points', []),
                            "disagreement": result.get('disagreement_points', []),
                            "timestamp": datetime.now().isoformat()
                        })

                        final = result.get('final_action', {})
                        if isinstance(final, dict):
                            print(f"  最终动作：{final.get('action', 'N/A')}")
                        else:
                            print(f"  最终动作：{final}")

                result = {
                    "success": True,
                    "debate_results": debate_results,
                    "count": len(debate_results),
                    "method": "full_debate",
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

        支持快速辩论 (美股) 和完整辩论 (港股) 格式
        """
        print("\n" + "=" * 60)
        print("Step 4: 生成投资建议")
        print("=" * 60)

        recommendations = []
        method = debate_results.get('method', 'unknown')

        for debate in debate_results.get('debate_results', []):
            code = debate.get('code', '')
            name = debate.get('name', '')

            # 根据辩论结果生成建议
            if method == 'quick_analysis':
                # 美股快速辩论格式
                action = debate.get('final_action', 'watch').upper()
                if action == 'BUY':
                    action = 'BUY'
                elif action in ['REJECT', 'WATCH']:
                    action = 'HOLD'
                confidence = debate.get('confidence', 0.5)
                reason = f"快速辩论：{debate.get('recommendation', 'N/A')}, 风控:{debate.get('risk_approval', 'N/A')}"
            elif method == 'full_debate':
                # 港股完整辩论格式
                risk_approval = debate.get('risk_approval', '')
                final_action = debate.get('final_action', '')
                trader_decision = debate.get('trader_decision', 'HOLD')

                # 风控否决则拒绝
                if risk_approval == 'REJECT':
                    action = 'REJECT'
                # 否则使用交易员决策
                elif trader_decision == 'BUY':
                    action = 'BUY'
                elif trader_decision == 'SELL':
                    action = 'SELL'
                else:
                    action = 'HOLD'

                confidence = 0.7  # 默认置信度
                reason = f"完整辩论：交易员决策={trader_decision}, 风控={risk_approval}, 动作={final_action}"
            else:
                # 其他格式 (包括简化辩论)
                if debate.get('risk_approval', {}).get('recommendation') == 'REJECT':
                    action = 'REJECT'
                elif debate.get('final_action') == 'reject':
                    action = 'REJECT'
                elif debate.get('recommendation') == 'BUY':
                    action = 'BUY'
                else:
                    action = 'HOLD'
                confidence = debate.get('confidence', 0.5)
                reason = f"辩论结果：{debate.get('final_action', 'N/A')}"

            rec = {
                "code": code,
                "name": name,
                "action": action,
                "confidence": confidence,
                "reason": reason,
                "bull_points": debate.get('bull_points', []),
                "bear_points": debate.get('bear_points', []),
                "timestamp": datetime.now().isoformat()
            }
            recommendations.append(rec)
            print(f"  {code} {name}: {action} (置信度{confidence:.0%})")

        result = {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations),
            "method": method,
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
        - 港股 (HK): OpenHKTradeContext, 账户 18767294, DAY 订单
        - 美股 (US): OpenUSTradeContext, 账户 18767299, DAY 订单
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
            # 使用配置的美股账户
            acc_id = self.config.get('acc_id')
            print(f"美股账户：{acc_id}")
            return self._execute_trades_direct(
                recommendations, trade_results,
                market='us',
                acc_id=acc_id,
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
            acc_id: 账户 ID (固定配置)
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
            print(f"\n使用美股交易接口，账户：{acc_id}")
        else:
            raise ValueError(f"不支持的市场：{market}")

        try:
            # 创建交易上下文
            trade_ctx = TradeContext(host='127.0.0.1', port=11111)

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
        根据市场获取价格（带超时和重试保护）

        Args:
            full_code: 富途格式代码 (SH.603220, HK.00700, US.AAPL)
            market: 市场 (cn/hk/us)

        Returns:
            价格
        """
        # ===== 港股：优先使用富途 API =====
        if market == 'hk':
            return self._get_price_with_futu(full_code, fallback=50.0)

        # ===== A 股：优先使用本地数据文件 =====
        elif market == 'cn':
            # 先尝试富途
            futu_price = self._get_price_with_futu(full_code, fallback=None)
            if futu_price is not None:
                print(f"  从富途获取价格：{futu_price}")
                return futu_price

            # 本地数据
            try:
                daily_data_file = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'data' / 'stock-pick' / 'daily_data' / '2026' / '202603.csv'
                if daily_data_file.exists():
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

    def _get_price_with_futu(self, full_code: str, fallback: float = None) -> float:
        """通过富途获取实时价格（带超时保护）"""
        result = [None]
        exception = [None]

        def _fetch():
            try:
                from futu import OpenQuoteContext
                quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
                ret, snapshot = quote_ctx.get_market_snapshot([full_code])
                quote_ctx.close()
                if ret == 0 and len(snapshot) > 0:
                    price = float(snapshot['last_price'].iloc[0])
                    if price > 0:
                        result[0] = price
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=_fetch)
        thread.daemon = True
        thread.start()
        thread.join(timeout=15)  # 15 秒超时

        if thread.is_alive():
            print(f"  富途价格获取超时 (15s)")
            return fallback if fallback is not None else 0.0

        if exception[0] is not None:
            print(f"  富途行情获取失败：{exception[0]}")
            return fallback if fallback is not None else 0.0

        if result[0] is not None:
            return result[0]

        return fallback if fallback is not None else 0.0

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
    parser.add_argument("--with-approval", action="store_true", help="启用人工审批 (大额交易)")
    parser.add_argument("--skip-review", action="store_true", help="跳过每日复盘")

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

    # Step 5: 风控检查 + 人工审批 + 交易执行
    if not args.skip_trades:
        print("\n" + "=" * 60)
        print("Step 5: 风控检查 + 人工审批 + 交易执行")
        print("=" * 60)

        try:
            from risk_manager import risk_check, get_position
            from approval_manager import send_trade_approval, wait_for_approval
        except ImportError as e:
            print(f"⚠️  风控/审批模块不可用：{e}")
            print("  跳过风控检查，直接执行交易")
            trades = handler.step5_execute_trades(recommendations)
            if trades.get('error'):
                print("Step 5 失败")
            handler.save_results()
            print("\n" + "=" * 60)
            print("Workflow C 执行完成")
            print("=" * 60)
            return

        # 获取当前持仓
        current_position = get_position()

        # 对每个推荐进行风控检查和审批
        approved_recommendations = []
        for rec in recommendations.get('recommendations', []):
            if rec.get('action') != 'BUY':
                continue

            # 构建订单
            order = {
                "code": rec.get('code', ''),
                "action": "BUY",
                "price": rec.get('price', 0),
                "quantity": 100,  # 默认数量
                "position_ratio": rec.get('confidence', 0.5) * 0.1  # 基于置信度估算仓位
            }

            # 风控检查
            risk_result = risk_check(order, current_position)
            print(f"\n风控检查 {rec.get('code')}: {'✅ 通过' if risk_result['passed'] else '❌ 阻止'}")

            if not risk_result['passed']:
                print(f"  阻止原因：{risk_result['block_reason']}")
                continue

            # 打印警告
            for warning in risk_result['warnings']:
                print(f"  ⚠️  警告：{warning}")

            # 大额交易确认
            if risk_result['requires_confirmation']:
                print(f"  ⚠️  大额交易，需要确认：{risk_result['confirmation_reason']}")

                if args.with_approval:
                    # 发送审批
                    approval_result = send_trade_approval(rec, args.market)
                    approval_id = approval_result.get('approval_id')

                    if approval_id:
                        print(f"  审批请求已发送：{approval_id}")
                        print(f"  等待用户确认...")

                        # 等待审批 (最多 5 分钟)
                        wait_result = wait_for_approval(approval_id, timeout_minutes=5)

                        if wait_result.get('status') == 'approved':
                            print(f"  ✅ 审批通过")
                            # 应用修改后的仓位
                            if wait_result.get('modified_position_ratio'):
                                rec['position_ratio'] = wait_result['modified_position_ratio']
                            approved_recommendations.append(rec)
                        elif wait_result.get('status') == 'rejected':
                            print(f"  ❌ 审批拒绝")
                        else:
                            print(f"  ⏰ 审批超时")
                    continue

            # 无需审批或已通过，加入执行列表
            approved_recommendations.append(rec)

        # 执行交易
        if approved_recommendations:
            # 更新推荐列表为审批通过的结果
            recommendations['recommendations'] = approved_recommendations
            trades = handler.step5_execute_trades(recommendations)
            if trades.get('error'):
                print("Step 5 失败")
        else:
            print("\n⚠️  无股票可交易 (全部未通过风控或审批)")

    # Step 6: 每日复盘报告
    if not args.skip_review:
        print("\n" + "=" * 60)
        print("Step 6: 生成每日复盘报告")
        print("=" * 60)

        try:
            from daily_review import generate_daily_review

            review_report = generate_daily_review(args.date)
            print(f"\n✅ 复盘报告已生成")
        except ImportError as e:
            print(f"\n⚠️  复盘模块不可用：{e}")
        except Exception as e:
            print(f"\n⚠️  复盘报告生成失败：{e}")

    # 保存结果
    handler.save_results()

    print("\n" + "=" * 60)
    print("Workflow C 执行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
