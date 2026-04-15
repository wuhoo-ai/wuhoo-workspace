#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美股选股与调仓流程 — 调试与验证脚本
====================================

验证 Workflow C 美股全链路:
1. 依赖检查 (futu, yfinance, talib 等)
2. 数据源验证 (yfinance 行情, Futu 模拟账户)
3. 选股与因子计算 (stock_pick.py --market us)
4. 多维度分析 (简化分析 + 因子验证)
5. 多空辩论 (快速辩论逻辑)
6. 风控检查 (risk_manager)
7. 交易执行验证 (Futu US 模拟下单，可选跳过)

用法:
    source workspace/agents/main/skills/stock-pick/venv/bin/activate
    python us_full_run.py                        # 完整验证 (跳过实际交易)
    python us_full_run.py --with-trades          # 包含实际模拟下单
    python us_full_run.py --top-n 5              # 只分析 Top 5
    python us_full_run.py --date 2026-04-14      # 指定日期
"""

import sys
import os
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# ===== 路径设置 =====
TRADE_DIR = Path(__file__).parent.resolve()
DEBATE_DIR = TRADE_DIR.parent / 'debate'
SKILL_PICK_DIR = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'skills' / 'stock-pick'
FACTORS_DIR = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'data' / 'stock-pick' / 'factors'

sys.path.insert(0, str(TRADE_DIR))
sys.path.insert(0, str(DEBATE_DIR))
sys.path.insert(0, str(SKILL_PICK_DIR))

# 加载环境变量
env_file = Path.home() / '.openclaw' / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                if key and key not in os.environ:
                    os.environ[key] = value.strip()

os.environ['FUTU_HOST'] = '127.0.0.1'
os.environ['FUTU_PORT'] = '11111'
os.environ['FUTU_ENV'] = 'SIMULATE'

# 输出目录
OUTPUT_DIR = TRADE_DIR / 'data' / 'us_full_run' / datetime.now().strftime('%Y-%m-%d')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(step: str, msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] [{step}] {msg}")


def save_json(filename: str, data):
    path = OUTPUT_DIR / filename
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return str(path)


def call_with_timeout(func, args=(), kwargs=None, timeout_sec=60):
    """跨平台超时调用"""
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


# ============================================================
# Step 0: 环境与依赖检查
# ============================================================
def step0_check_env():
    log("Step 0", "检查环境与依赖...")
    results = {}

    # Python 版本
    import sys
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    results['python'] = py_ver
    log("Step 0", f"  Python: {py_ver}")

    # futu
    try:
        import futu
        results['futu'] = futu.__version__
        log("Step 0", f"  futu: {futu.__version__} ✅")
    except ImportError:
        results['futu'] = 'MISSING'
        log("Step 0", f"  futu: ❌ 未安装")

    # yfinance
    try:
        import yfinance
        results['yfinance'] = yfinance.__version__
        log("Step 0", f"  yfinance: {yfinance.__version__} ✅")
    except ImportError:
        results['yfinance'] = 'MISSING'
        log("Step 0", f"  yfinance: ❌ 未安装")

    # talib
    try:
        import talib
        results['talib'] = talib.__version__
        log("Step 0", f"  talib: {talib.__version__} ✅")
    except ImportError:
        results['talib'] = 'MISSING'
        log("Step 0", f"  talib: ❌ 未安装 (非关键)")

    # pandas
    try:
        import pandas as pd
        results['pandas'] = pd.__version__
        log("Step 0", f"  pandas: {pd.__version__} ✅")
    except ImportError:
        results['pandas'] = 'MISSING'
        log("Step 0", f"  pandas: ❌ 未安装")

    # Futu OpenD 连通性
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        ret = sock.connect_ex(('127.0.0.1', 11111))
        sock.close()
        if ret == 0:
            results['futu_opend'] = 'CONNECTED'
            log("Step 0", f"  Futu OpenD (127.0.0.1:11111): ✅ 已连接")
        else:
            results['futu_opend'] = 'DISCONNECTED'
            log("Step 0", f"  Futu OpenD (127.0.0.1:11111): ❌ 未连接")
    except Exception as e:
        results['futu_opend'] = f'ERROR: {e}'
        log("Step 0", f"  Futu OpenD 检查失败: {e}")

    # 美股模拟账户连通性
    try:
        from futu import OpenUSTradeContext, TrdEnv
        trade_ctx = OpenUSTradeContext(host='127.0.0.1', port=11111)
        ret, data = trade_ctx.get_acc_list()
        if ret == 0:
            acc_list = data['acc_id'].tolist()
            us_acc = 18767293
            if us_acc in acc_list:
                results['us_account'] = f'ACC {us_acc} OK'
                log("Step 0", f"  美股模拟账户 ({us_acc}): ✅ 可用")
            else:
                results['us_account'] = f'ACC {us_acc} NOT FOUND, available: {acc_list}'
                log("Step 0", f"  美股模拟账户 ({us_acc}): ❌ 不可用, 可用账户: {acc_list}")
        else:
            results['us_account'] = f'ERROR: {data}'
            log("Step 0", f"  美股模拟账户: ❌ 获取失败")
        trade_ctx.close()
    except Exception as e:
        results['us_account'] = f'ERROR: {e}'
        log("Step 0", f"  美股模拟账户检查失败: {e}")

    # 检查成员股文件
    members_file = SKILL_PICK_DIR / 'data' / 'us_members.csv'
    if members_file.exists():
        import pandas as pd
        mdf = pd.read_csv(members_file)
        results['us_members'] = f'{len(mdf)} stocks'
        log("Step 0", f"  美股成员股: ✅ {len(mdf)} 只")
    else:
        results['us_members'] = 'MISSING'
        log("Step 0", f"  美股成员股: ❌ {members_file}")

    # 检查已有选股结果
    today = datetime.now().strftime('%Y%m%d')
    result_file = FACTORS_DIR / f"result_us_{today}.csv"
    if result_file.exists():
        import pandas as pd
        rdf = pd.read_csv(result_file)
        results['latest_result'] = f'{result_file.name} ({len(rdf)} stocks)'
        log("Step 0", f"  今日选股结果: ✅ {result_file.name} ({len(rdf)} 只)")
    else:
        # 找最近的
        existing = sorted(FACTORS_DIR.glob("result_us_*.csv"))
        if existing:
            latest = existing[-1]
            import pandas as pd
            rdf = pd.read_csv(latest)
            results['latest_result'] = f'{latest.name} ({len(rdf)} stocks)'
            log("Step 0", f"  最近选股结果: ⚠️ {latest.name} ({len(rdf)} 只，非今日)")
        else:
            results['latest_result'] = 'NONE'
            log("Step 0", f"  选股结果: ❌ 无历史结果")

    save_json("00_env_check.json", results)
    return results


# ============================================================
# Step 1: 美股选股
# ============================================================
def step1_select_stocks(top_n=10, target_date=None):
    log("Step 1", "美股选股...")

    date_str = target_date or datetime.now().strftime('%Y-%m-%d')
    date_file = date_str.replace('-', '')
    result_file = FACTORS_DIR / f"result_us_{date_file}.csv"

    # 如果已有结果，直接加载
    if result_file.exists():
        import pandas as pd
        df = pd.read_csv(result_file)
        log("Step 1", f"  加载已有结果: {result_file.name} ({len(df)} 只)")
        stocks = df.head(top_n).to_dict('records')
        save_json("01_selected_stocks.json", {
            "source": "existing",
            "file": str(result_file),
            "count": len(stocks),
            "stocks": stocks
        })
        return stocks

    # 需要运行选股
    log("Step 1", f"  结果文件不存在，运行选股脚本...")
    stock_pick_script = SKILL_PICK_DIR / 'stock_pick.py'
    if not stock_pick_script.exists():
        log("Step 1", f"  ❌ 选股脚本不存在: {stock_pick_script}")
        return []

    python_cmd = str(SKILL_PICK_DIR / 'venv' / 'bin' / 'python')
    cmd = [
        python_cmd, str(stock_pick_script),
        '--market', 'us',
        '--date', date_str
    ]

    log("Step 1", f"  执行: {' '.join(cmd)}")
    import subprocess
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=600  # 10 分钟超时 (yfinance 下载慢)
        )

        if proc.stdout:
            for line in proc.stdout.split('\n')[-20:]:  # 只打印最后 20 行
                if line.strip():
                    log("Step 1", f"    {line}")

        if proc.returncode != 0:
            log("Step 1", f"  ❌ 选股脚本执行失败 (exit code={proc.returncode})")
            if proc.stderr:
                for line in proc.stderr.split('\n')[-10:]:
                    if line.strip():
                        log("Step 1", f"    STDERR: {line}")
            return []

        # 加载结果
        if result_file.exists():
            import pandas as pd
            df = pd.read_csv(result_file)
            stocks = df.head(top_n).to_dict('records')
            log("Step 1", f"  ✅ 选股完成: {len(stocks)} 只 (从 {len(df)} 只候选)")
            save_json("01_selected_stocks.json", {
                "source": "fresh",
                "file": str(result_file),
                "count": len(stocks),
                "stocks": stocks
            })
            return stocks
        else:
            log("Step 1", f"  ❌ 选股脚本执行成功但结果文件未生成")
            return []

    except subprocess.TimeoutExpired:
        log("Step 1", f"  ❌ 选股执行超时 (10 分钟)")
        return []
    except Exception as e:
        log("Step 1", f"  ❌ 选股失败: {e}")
        import traceback
        traceback.print_exc()
        return []


# ============================================================
# Step 2: 多维度分析 (美股简化版 + 因子验证)
# ============================================================
def step2_analyze(stocks: List[Dict]):
    log("Step 2", "多维度分析 (美股简化版)...")

    if not stocks:
        log("Step 2", "  ❌ 无股票可分析")
        return []

    results = []
    for stock in stocks:
        code = stock.get('ts_code', stock.get('code', ''))
        name = stock.get('name', '')
        residual_vol = stock.get('residual_vol', 0)
        momentum_5d = stock.get('momentum_5d', 0)
        beta = stock.get('beta_20d', 0)
        momentum_10d = stock.get('momentum_10d', 0)
        turnover = stock.get('turnover_5d', 0)

        # 评分逻辑 (与 workflow_c_multi_market.py 一致)
        score = 5.0
        notes = []

        if residual_vol < 20:
            score += 1
            notes.append("低残差波动 ✅")
        elif residual_vol > 23:
            score -= 1
            notes.append("高残差波动 ⚠️")

        if momentum_5d > 3:
            score += 1
            notes.append("强势 5 日动量 ✅")
        elif momentum_5d < 1.5:
            notes.append("5 日动量疲软 ⚠️")

        if momentum_10d > 5:
            score -= 1
            notes.append("10 日涨幅过大，有回调风险 ⚠️")

        if 0.9 <= beta <= 1.3:
            score += 1
            notes.append("Beta 适中 ✅")
        elif beta > 1.4:
            notes.append("高 Beta 风险 ⚠️")

        if turnover > 15:
            score += 0.5
            notes.append("流动性充足 ✅")

        score = min(max(score, 0), 10)
        recommendation = "BUY" if score >= 7 else "HOLD"

        analysis = {
            "code": code,
            "name": name,
            "score": round(score, 1),
            "residual_vol": round(residual_vol, 2),
            "momentum_5d": round(momentum_5d, 2),
            "momentum_10d": round(momentum_10d, 2),
            "beta_20d": round(beta, 2),
            "turnover_5d": round(turnover, 2),
            "recommendation": recommendation,
            "notes": notes
        }
        results.append(analysis)
        log("Step 2", f"  {code} {name}: 评分={score:.1f}, {recommendation} | {', '.join(notes[:3])}")

    save_json("02_analysis.json", {"count": len(results), "results": results})
    return results


# ============================================================
# Step 3: 多空辩论 (快速辩论)
# ============================================================
def step3_debate(stocks: List[Dict]):
    log("Step 3", "多空辩论 (快速辩论)...")

    if not stocks:
        return []

    results = []
    for stock in stocks:
        code = stock.get('ts_code', stock.get('code', ''))
        name = stock.get('name', '')
        residual_vol = stock.get('residual_vol', 25)
        momentum_5d = stock.get('momentum_5d', 0)
        momentum_10d = stock.get('momentum_10d', 0)
        beta = stock.get('beta_20d', 1)

        # 多方观点
        bull_points = []
        bear_points = []

        if residual_vol < 20:
            bull_points.append("低残差波动率，风险调整后收益好")
        elif residual_vol > 23:
            bear_points.append("残差波动率偏高，个股风险大")

        if momentum_5d > 3:
            bull_points.append("5 日动量强劲，趋势向上")
        elif momentum_5d < 1.5:
            bear_points.append("5 日动量疲软，缺乏上涨动力")

        if momentum_10d > 5:
            bear_points.append("10 日涨幅过大，短期回调风险")

        if 0.9 <= beta <= 1.3:
            bull_points.append("Beta 适中，系统性风险可控")
        elif beta > 1.4:
            bear_points.append("Beta 偏高，市场波动放大风险")

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
        if residual_vol > 22:
            risk_factors.append("vol_high")
        if momentum_10d > 5:
            risk_factors.append("gain_large")
        if beta > 1.3:
            risk_factors.append("beta_high")

        if len(risk_factors) >= 2:
            risk_approval = "REJECT"
        elif len(risk_factors) == 1:
            risk_approval = "CONDITIONAL"
        else:
            risk_approval = "APPROVE"

        final_action = "reject" if risk_approval == "REJECT" else ("buy" if recommendation == "BUY" and confidence > 0.6 else "watch")

        debate = {
            "code": code,
            "name": name,
            "bull_points": bull_points,
            "bear_points": bear_points,
            "recommendation": recommendation,
            "confidence": round(confidence, 2),
            "risk_approval": risk_approval,
            "risk_factors": risk_factors,
            "final_action": final_action
        }
        results.append(debate)

        log("Step 3", f"  {code} {name}: {recommendation} (置信度{confidence:.0%}), 风控:{risk_approval}, 最终:{final_action}")
        if bull_points:
            log("Step 3", f"    多方: {'; '.join(bull_points)}")
        if bear_points:
            log("Step 3", f"    空方: {'; '.join(bear_points)}")

    save_json("03_debate.json", {"count": len(results), "results": results})
    return results


# ============================================================
# Step 4: 生成投资建议 + 价格获取
# ============================================================
def step4_recommendations(debate_results: List[Dict]):
    log("Step 4", "生成投资建议...")

    recommendations = []
    for d in debate_results:
        code = d.get('code', '')
        name = d.get('name', '')
        final_action = d.get('final_action', 'watch')

        # 映射动作
        if final_action == 'buy':
            action = 'BUY'
        elif final_action in ['reject', 'watch']:
            action = 'HOLD'
        else:
            action = 'HOLD'

        confidence = d.get('confidence', 0.5)
        reason = f"快速辩论: {d.get('recommendation')}, 风控:{d.get('risk_approval')}"

        rec = {
            "code": code,
            "name": name,
            "action": action,
            "confidence": confidence,
            "reason": reason,
            "bull_points": d.get('bull_points', []),
            "bear_points": d.get('bear_points', []),
            "risk_factors": d.get('risk_factors', [])
        }
        recommendations.append(rec)
        log("Step 4", f"  {code} {name}: {action} (置信度{confidence:.0%})")

    save_json("04_recommendations.json", {"count": len(recommendations), "results": recommendations})
    return recommendations


# ============================================================
# Step 5: 价格获取 (yfinance + Futu 对比)
# ============================================================
def step5_get_prices(recommendations: List[Dict]):
    log("Step 5", "获取实时价格...")

    for rec in recommendations:
        code = rec.get('code', '')
        symbol = code.replace('US.', '')

        # 方法 1: yfinance
        yf_price = None
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            yf_price = info.get('regularMarketPrice')
            if yf_price:
                yf_price = float(yf_price)
        except Exception as e:
            log("Step 5", f"  {code} yfinance 失败: {e}")

        # 方法 2: Futu 行情
        futu_price = None
        try:
            from futu import OpenQuoteContext
            quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
            ret, snapshot = quote_ctx.get_market_snapshot([code])
            quote_ctx.close()
            if ret == 0 and len(snapshot) > 0:
                futu_price = float(snapshot['last_price'].iloc[0])
                if futu_price <= 0:
                    futu_price = None
        except Exception as e:
            log("Step 5", f"  {code} Futu 行情失败: {e}")

        price = futu_price or yf_price or 0.0
        price_source = "Futu" if futu_price else ("yfinance" if yf_price else "N/A")

        name = rec.get('name', '')
        rec['price'] = price
        rec['price_source'] = price_source
        rec['yf_price'] = yf_price
        rec['futu_price'] = futu_price

        log("Step 5", f"  {code} {name}: ${price:.2f} (来源: {price_source})"
            if price > 0 else f"  {code} {name}: ❌ 无法获取价格")

    save_json("05_prices.json", recommendations)
    return recommendations


# ============================================================
# Step 6: 风控检查
# ============================================================
def step6_risk_check(recommendations: List[Dict]):
    log("Step 6", "风控检查...")

    try:
        from risk_manager import risk_check, get_position
    except ImportError as e:
        log("Step 6", f"  ❌ 风控模块不可用: {e}")
        return recommendations

    current_position = get_position()
    log("Step 6", f"  总资产: ${current_position['total_value']:,.2f}, 现金: ${current_position['cash']:,.2f}")
    log("Step 6", f"  持仓市值: ${current_position['total_market_value']:,.2f}, 持仓数: {len(current_position['positions'])}")

    for rec in recommendations:
        if rec.get('action') != 'BUY':
            continue

        code = rec.get('code', '')
        price = rec.get('price', 0)
        qty = 1  # 美股 1 股起

        order = {
            "code": code,
            "action": "BUY",
            "price": price,
            "quantity": qty,
            "position_ratio": rec.get('confidence', 0.5) * 0.1
        }

        result = risk_check(order, current_position)
        rec['risk_passed'] = result.get('passed', False)
        rec['risk_block_reason'] = result.get('block_reason', '')
        rec['risk_warnings'] = result.get('warnings', [])
        rec['risk_requires_confirmation'] = result.get('requires_confirmation', False)

        status = "✅ 通过" if result['passed'] else f"❌ {result.get('block_reason', '未知')}"
        log("Step 6", f"  {code}: {status}")
        for w in result.get('warnings', []):
            log("Step 6", f"    ⚠️ {w}")

    save_json("06_risk_check.json", recommendations)
    return recommendations


# ============================================================
# Step 7: 模拟交易执行 (可选)
# ============================================================
def step7_execute_trades(recommendations: List[Dict], with_trades: bool = False):
    log("Step 7", "交易执行..." if with_trades else "交易执行 (跳过)...")

    if not with_trades:
        buy_recs = [r for r in recommendations if r.get('action') == 'BUY' and r.get('risk_passed')]
        log("Step 7", f"  跳过实际交易 (使用 --with-trades 启用)")
        log("Step 7", f"  拟执行: {len(buy_recs)} 笔买入")
        save_json("07_trades_skipped.json", {
            "skipped": True,
            "pending_trades": [
                {"code": r['code'], "name": r['name'], "price": r.get('price', 0), "qty": 1}
                for r in buy_recs
            ]
        })
        return {"skipped": True}

    trade_results = []
    try:
        from futu import OpenUSTradeContext, OrderType, TrdSide, TrdEnv

        trade_ctx = OpenUSTradeContext(host='127.0.0.1', port=11111)

        # 解锁交易
        password = os.environ.get('FUTU_TRADING_PASSWORD', os.environ.get('FUTU_PASSWORD', ''))
        if password:
            trade_ctx.unlock_trade(password)

        acc_id = 18767293  # 美股模拟账户

        for rec in recommendations:
            if rec.get('action') != 'BUY' or not rec.get('risk_passed'):
                continue

            code = rec.get('code', '')
            name = rec.get('name', '')
            price = rec.get('price', 0)

            if not code or price <= 0:
                continue

            qty = 1
            order_price = round(price * 1.01, 2)  # 高 1% 确保成交

            log("Step 7", f"  下单: {name} ({code}) BUY {qty} @ ${order_price}")

            ret, data = trade_ctx.place_order(
                acc_id=acc_id,
                code=code,
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
                    "code": code,
                    "name": name,
                    "action": "BUY",
                    "price": order_price,
                    "qty": qty,
                    "order_id": order_id,
                    "status": "SUBMITTED"
                })
                log("Step 7", f"    ✅ 下单成功, 订单 ID: {order_id}")
            else:
                trade_results.append({
                    "code": code,
                    "name": name,
                    "action": "BUY",
                    "status": "FAILED",
                    "error": str(data) if len(str(data)) > 0 else "Unknown error"
                })
                log("Step 7", f"    ❌ 下单失败: {data}")

        trade_ctx.close()

    except Exception as e:
        log("Step 7", f"  ❌ 交易失败: {e}")
        import traceback
        traceback.print_exc()
        trade_results.append({"error": str(e)})

    save_json("07_trade_results.json", {"count": len(trade_results), "results": trade_results})
    return {"count": len(trade_results), "results": trade_results}


# ============================================================
# Step 8: 当前持仓查询
# ============================================================
def step8_check_position():
    log("Step 8", "查询美股模拟账户持仓...")

    try:
        from futu import OpenUSTradeContext, TrdEnv

        trade_ctx = OpenUSTradeContext(host='127.0.0.1', port=11111)
        password = os.environ.get('FUTU_TRADING_PASSWORD', os.environ.get('FUTU_PASSWORD', ''))
        if password:
            trade_ctx.unlock_trade(password)

        acc_id = 18767293  # 美股模拟账户

        # 查询持仓
        ret, data = trade_ctx.get_position_list(
            acc_id=acc_id,
            trd_env=TrdEnv.SIMULATE
        )

        if ret == 0 and len(data) > 0:
            positions = data.to_dict('records')
            log("Step 8", f"  当前持仓: {len(positions)} 只")
            for pos in positions:
                code = pos.get('code', 'N/A')
                name = pos.get('stock_name', 'N/A')
                qty = pos.get('qty', 0)
                cost = pos.get('cost_price', 0)
                market_val = pos.get('market_val', 0)
                pl = pos.get('pl_val', 0)
                pl_ratio = pos.get('pl_ratio', 0)
                log("Step 8", f"    {code} {name}: {qty} 股, 成本 ${cost:.2f}, 市值 ${market_val:,.2f}, 盈亏 ${pl:,.2f} ({pl_ratio:.2f}%)")

            save_json("08_positions.json", positions)
        else:
            log("Step 8", f"  无持仓")
            save_json("08_positions.json", [])

        # 查询账户资金
        ret, funds = trade_ctx.get_acc_cash(
            acc_id=acc_id,
            trd_env=TrdEnv.SIMULATE,
            currency='USD'
        )

        if ret == 0 and len(funds) > 0:
            cash_data = funds.iloc[0].to_dict()
            log("Step 8", f"  账户资金:")
            for k, v in cash_data.items():
                log("Step 8", f"    {k}: {v}")
            save_json("08_account_cash.json", {str(k): str(v) for k, v in cash_data.items()})

        # 查询未成交订单
        ret, orders = trade_ctx.get_order_list(
            acc_id=acc_id,
            trd_env=TrdEnv.SIMULATE
        )

        if ret == 0 and len(orders) > 0:
            order_list = orders.to_dict('records')
            log("Step 8", f"  未成交订单: {len(order_list)} 笔")
            save_json("08_pending_orders.json", order_list)
        else:
            log("Step 8", f"  无未成交订单")
            save_json("08_pending_orders.json", [])

        trade_ctx.close()

    except Exception as e:
        log("Step 8", f"  ❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        save_json("08_error.json", {"error": str(e)})


# ============================================================
# 汇总报告
# ============================================================
def generate_report(all_results: Dict):
    log("Report", "=" * 60)
    log("Report", "美股选股与调仓流程 — 验证报告")
    log("Report", "=" * 60)

    env = all_results.get('env', {})
    log("Report", f"\n环境:")
    log("Report", f"  Python: {env.get('python', 'N/A')}")
    log("Report", f"  futu: {env.get('futu', 'MISSING')}")
    log("Report", f"  yfinance: {env.get('yfinance', 'MISSING')}")
    log("Report", f"  Futu OpenD: {env.get('futu_opend', 'N/A')}")
    log("Report", f"  美股账户: {env.get('us_account', 'N/A')}")

    stocks = all_results.get('stocks', [])
    log("Report", f"\n选股: {len(stocks)} 只")
    for s in stocks:
        log("Report", f"  {s.get('ts_code', s.get('code'))} {s.get('name', '')}")

    analysis = all_results.get('analysis', [])
    log("Report", f"\n分析结果:")
    for a in analysis:
        log("Report", f"  {a['code']} {a['name']}: 评分={a['score']:.1f}, {a['recommendation']}")

    debates = all_results.get('debates', [])
    log("Report", f"\n辩论结果:")
    for d in debates:
        log("Report", f"  {d['code']} {d['name']}: {d['recommendation']} (置信度{d['confidence']:.0%}), 风控:{d['risk_approval']}, 最终:{d['final_action']}")

    recs = all_results.get('recommendations', [])
    buy_recs = [r for r in recs if r.get('action') == 'BUY']
    log("Report", f"\n投资建议: {len(recs)} 条, {len(buy_recs)} 条买入")

    log("Report", f"\n输出目录: {OUTPUT_DIR}")
    log("Report", "=" * 60)

    # 保存汇总
    save_json("99_report.json", all_results)


# ============================================================
# Main
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="美股选股与调仓流程 — 调试与验证")
    parser.add_argument("--top-n", type=int, default=10, help="选股数量")
    parser.add_argument("--date", type=str, default=None, help="日期 (YYYY-MM-DD)")
    parser.add_argument("--with-trades", action="store_true", help="启用实际模拟交易")
    args = parser.parse_args()

    print("=" * 60)
    print("美股选股与调仓流程 — 调试与验证")
    print(f"日期: {args.date or datetime.now().strftime('%Y-%m-%d')}")
    print(f"Top N: {args.top_n}")
    print(f"实际交易: {'是' if args.with_trades else '否'}")
    print(f"输出: {OUTPUT_DIR}")
    print("=" * 60)

    all_results = {}

    # Step 0: 环境检查
    all_results['env'] = step0_check_env()

    # Step 1: 选股
    stocks = step1_select_stocks(top_n=args.top_n, target_date=args.date)
    all_results['stocks'] = stocks

    if not stocks:
        log("WARN", "选股结果为空，终止流程")
        generate_report(all_results)
        return

    # Step 2: 分析
    analysis = step2_analyze(stocks)
    all_results['analysis'] = analysis

    # Step 3: 辩论
    debates = step3_debate(stocks)
    all_results['debates'] = debates

    # Step 4: 建议
    recs = step4_recommendations(debates)
    all_results['recommendations'] = recs

    # Step 5: 价格
    recs_with_prices = step5_get_prices(recs)
    all_results['recommendations'] = recs_with_prices

    # Step 6: 风控
    recs_with_risk = step6_risk_check(recs_with_prices)
    all_results['recommendations'] = recs_with_risk

    # Step 7: 交易
    trade_result = step7_execute_trades(recs_with_risk, with_trades=args.with_trades)
    all_results['trades'] = trade_result

    # Step 8: 当前持仓
    step8_check_position()

    # 汇总报告
    generate_report(all_results)


if __name__ == "__main__":
    main()
