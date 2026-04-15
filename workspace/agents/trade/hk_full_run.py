#!/usr/bin/env python3
"""
港股选股与持仓诊断 — 完整执行脚本
====================================
执行 Workflow C (选股→分析→辩论→建议) + Workflow D (持仓诊断→调仓信号)
留下详细过程指引供 OpenClaw 学习
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# ===== 路径设置 =====
TRADE_DIR = Path(__file__).parent.resolve()
DEBATE_DIR = TRADE_DIR.parent / 'debate'
sys.path.insert(0, str(DEBATE_DIR))
sys.path.insert(0, str(TRADE_DIR))

# 验证路径
assert (DEBATE_DIR / 'adapters').exists(), f"debate adapters 目录不存在: {DEBATE_DIR / 'adapters'}"

# 加载环境变量
env_file = Path.home() / '.openclaw' / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key.strip() and key.strip() not in os.environ:
                    os.environ[key.strip()] = value.strip()

OUTPUT_DIR = TRADE_DIR / 'data' / 'hk_full_run' / datetime.now().strftime('%Y-%m-%d')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def log(step, msg):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] [{step}] {msg}")

def save_json(filename, data):
    path = OUTPUT_DIR / filename
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(path)

# ============================================================
# Step 1: 港股选股结果加载
# ============================================================
def step1_load_stock_pick():
    log("Step 1", "加载港股选股结果...")
    import pandas as pd
    result_file = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'data' / 'stock-pick' / 'factors' / 'result_hk_20260414.csv'

    if not result_file.exists():
        log("Step 1", "ERROR: 选股结果文件不存在，需要先运行选股")
        return []

    df = pd.read_csv(result_file)
    stocks = df.to_dict('records')
    log("Step 1", f"加载 {len(stocks)} 只选股结果")

    for i, s in enumerate(stocks):
        log("Step 1", f"  {i+1}. {s['ts_code']} {s['name']} - 波动率:{s['volatility']:.2f}%, 5日动量:{s['momentum_5d']:.2f}%")

    save_json('01_selected_stocks.json', {
        'market': 'HK', 'date': datetime.now().strftime('%Y-%m-%d'),
        'count': len(stocks), 'stocks': stocks
    })
    return stocks

# ============================================================
# Step 2: 多维度分析 (快速版 — Futu 实时行情 + RSS 舆情 + 基本面)
# ============================================================
def step2_analyze_stocks(stocks):
    log("Step 2", "多维度分析选股结果...")

    # 确保路径正确
    debate_dir = Path(__file__).parent.parent / 'debate'
    if debate_dir not in sys.path:
        sys.path.insert(0, str(debate_dir))
    trade_dir = Path(__file__).parent
    if str(trade_dir) not in sys.path:
        sys.path.insert(0, str(trade_dir))

    from futu import OpenQuoteContext
    from adapters.news_rss_adapter import RSSNewsAdapter
    from adapters.data_aggregator import DataAggregator

    # 分析前 5 只
    to_analyze = stocks[:5]
    results = []

    # 一次性获取所有实时行情
    log("Step 2", "获取 Futu 实时行情快照...")
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    codes = [s['ts_code'] for s in to_analyze]
    ret, snapshot = quote_ctx.get_stock_quote(codes)

    rss_adapter = RSSNewsAdapter()
    aggregator = DataAggregator()

    for i, stock in enumerate(to_analyze):
        code = stock['ts_code']
        name = stock['name']
        log("Step 2", f"[{i+1}/{len(to_analyze)}] 分析 {code} {name}...")

        analysis = {
            'code': code, 'name': name,
            'volatility': stock['volatility'],
            'momentum_5d': stock['momentum_5d'],
            'momentum_10d': stock['momentum_10d'],
        }

        # 实时行情
        if ret == 0 and len(snapshot) > 0:
            row = snapshot[snapshot['code'] == code.replace('HK.', '')]
            if len(row) > 0:
                r = row.iloc[0]
                analysis['last_price'] = float(r.get('last_price', 0))
                analysis['open_price'] = float(r.get('open_price', 0))
                analysis['high_price'] = float(r.get('high_price', 0))
                analysis['low_price'] = float(r.get('low_price', 0))
                analysis['volume'] = int(r.get('volume', 0))
                analysis['turnover'] = float(r.get('turnover', 0))
                analysis['price_change_pct'] = float(r.get('price_change_pct', 0))
                analysis['pe_ratio'] = float(r.get('pe_ratio', 0)) if r.get('pe_ratio') else None
                analysis['pb_ratio'] = float(r.get('pb_ratio', 0)) if r.get('pb_ratio') else None
                log("Step 2", f"  价格: {analysis['last_price']:.2f}, 涨跌: {analysis['price_change_pct']:.2f}%, PE: {analysis.get('pe_ratio', 'N/A')}")

        # RSS 舆情 (快速搜索)
        try:
            sentiment = rss_adapter.get_sentiment_data(code, name)
            analysis['sentiment_score'] = sentiment.get('sentiment_score', 0)
            analysis['sentiment_label'] = sentiment.get('sentiment_label', 'neutral')
            analysis['news_count'] = sentiment.get('news_count', 0)
            log("Step 2", f"  舆情: {analysis['sentiment_label']} ({analysis['news_count']} 条, 评分 {analysis['sentiment_score']:.2f})")
        except Exception as e:
            log("Step 2", f"  舆情获取失败: {e}")
            analysis['sentiment_score'] = 0
            analysis['sentiment_label'] = 'unknown'
            analysis['news_count'] = 0

        # 技术面 (通过 DataAggregator 的 Futu K-line)
        try:
            tech_data = aggregator._get_futu_technical_data(code)
            analysis['technical_signal'] = tech_data.get('signal', 'neutral')
            analysis['macd'] = tech_data.get('macd_histogram', 0)
            analysis['rsi'] = tech_data.get('rsi', 50)
            analysis['trend'] = tech_data.get('trend', 'unknown')
            log("Step 2", f"  技术: signal={analysis['technical_signal']}, RSI={analysis['rsi']:.1f}, trend={analysis['trend']}")
        except Exception as e:
            log("Step 2", f"  技术面获取失败: {e}")
            analysis['technical_signal'] = 'error'
            analysis['rsi'] = 50
            analysis['trend'] = 'unknown'

        # 综合评分
        score = 5.0
        if analysis.get('price_change_pct', 0) > 0: score += 1
        if analysis.get('sentiment_score', 0) > 0: score += 1
        if analysis['technical_signal'] == 'buy': score += 1
        if analysis['volatility'] < 25: score += 1
        if analysis['momentum_5d'] > 5: score += 1
        analysis['composite_score'] = min(score, 10)

        results.append(analysis)

    quote_ctx.close()

    save_json('02_analysis_results.json', {
        'market': 'HK', 'count': len(results), 'results': results
    })

    log("Step 2", f"分析完成: {len(results)} 只股票")
    return results

# ============================================================
# Step 3: 多空辩论 (快速版)
# ============================================================
def step3_debate(analysis_results):
    log("Step 3", "快速多空辩论...")

    results = []
    for a in analysis_results:
        code = a['code']
        name = a['name']

        bull_points = []
        bear_points = []

        # 基于分析结果生成论点
        if a.get('price_change_pct', 0) > 2:
            bull_points.append(f"今日上涨 {a['price_change_pct']:.2f}%，势头强劲")
        elif a.get('price_change_pct', 0) < -2:
            bear_points.append(f"今日下跌 {abs(a['price_change_pct']):.2f}%，卖压较大")

        if a.get('sentiment_score', 0) > 0.2:
            bull_points.append(f"RSS 舆情偏正面 (评分 {a['sentiment_score']:.2f})")
        elif a.get('sentiment_score', 0) < -0.2:
            bear_points.append(f"RSS 舆情偏负面 (评分 {a['sentiment_score']:.2f})")

        if a.get('technical_signal') == 'buy':
            bull_points.append("技术面发出买入信号")
        elif a.get('technical_signal') == 'sell':
            bear_points.append("技术面发出卖出信号")

        if a.get('rsi', 50) > 70:
            bear_points.append(f"RSI {a['rsi']:.1f} 超买区域")
        elif a.get('rsi', 50) < 30:
            bull_points.append(f"RSI {a['rsi']:.1f} 超卖区域，可能反弹")

        if a.get('volatility', 30) < 25:
            bull_points.append(f"波动率 {a['volatility']:.1f}% 较低，风险可控")
        elif a.get('volatility', 30) > 30:
            bear_points.append(f"波动率 {a['volatility']:.1f}% 偏高")

        if a.get('momentum_5d', 0) > 5:
            bull_points.append(f"5 日动量 {a['momentum_5d']:.2f}% 强势")
        elif a.get('momentum_5d', 0) < 2:
            bear_points.append(f"5 日动量 {a['momentum_5d']:.2f}% 疲软")

        if not bull_points:
            bull_points.append("估值合理，具备持有价值")
        if not bear_points:
            bear_points.append("暂无明显风险因素")

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

        risk_approval = "APPROVE" if confidence > 0.6 else "CONDITIONAL"
        final_action = "buy" if recommendation == "BUY" and confidence > 0.6 else "watch"

        debate = {
            'code': code, 'name': name,
            'bull_points': bull_points,
            'bear_points': bear_points,
            'recommendation': recommendation,
            'confidence': round(min(confidence, 0.9), 2),
            'risk_approval': risk_approval,
            'final_action': final_action,
        }
        results.append(debate)

        log("Step 3", f"  {code} {name}: {recommendation} (置信度 {confidence:.0%}), 风控: {risk_approval}, 最终: {final_action}")
        log("Step 3", f"    看多: {bull_points}")
        log("Step 3", f"    看空: {bear_points}")

    save_json('03_debate_results.json', {
        'market': 'HK', 'method': 'quick_analysis',
        'count': len(results), 'debate_results': results
    })

    log("Step 3", f"辩论完成: {len(results)} 只股票")
    return results

# ============================================================
# Step 4: 投资建议生成
# ============================================================
def step4_recommendations(debate_results):
    log("Step 4", "生成投资建议...")

    recommendations = []
    for d in debate_results:
        action = 'BUY' if d['final_action'] == 'buy' else 'HOLD'
        rec = {
            'code': d['code'], 'name': d['name'],
            'action': action,
            'confidence': d['confidence'],
            'reason': f"辩论: {d['recommendation']}, 风控: {d['risk_approval']}",
            'bull_points': d['bull_points'],
            'bear_points': d['bear_points'],
        }
        recommendations.append(rec)
        log("Step 4", f"  {d['code']} {d['name']}: {action} (置信度 {d['confidence']:.0%})")

    save_json('04_recommendations.json', {
        'market': 'HK', 'count': len(recommendations),
        'recommendations': recommendations
    })

    log("Step 4", f"建议生成完成: {len(recommendations)} 只")
    return recommendations

# ============================================================
# Step 5: 港股持仓诊断 (Workflow D)
# ============================================================
def step5_portfolio_diagnosis():
    log("Step 5", "开始港股持仓诊断 (Workflow D)...")

    import subprocess
    from risk_manager import RiskManager
    from portfolio_metrics import (
        calculate_sharpe_ratio, calculate_hhi,
        calculate_concentration, calculate_max_drawdown_estimate
    )

    # 5a. 扫描持仓 — 使用 futu-api 脚本（避免 unlock 阻塞）
    log("Step 5", "5a. 扫描 OpenD 港股持仓...")

    # futu-api 脚本路径: ~/.openclaw/skills/futu-api/ (官方 skill)
    futu_script = Path.home() / '.openclaw' / 'skills' / 'futu-api' / 'scripts' / 'trade' / 'get_portfolio.py'
    # 使用 python3.11 而非 venv 的 python3.6
    python311 = '/usr/bin/python3.11'
    result = subprocess.run(
        [python311, str(futu_script), '--market', 'HK', '--acc-id', '18767294', '--json'],
        capture_output=True, text=True, timeout=30
    )

    log("Step 5", f"  subprocess returncode: {result.returncode}")
    log("Step 5", f"  stdout length: {len(result.stdout)}, stderr length: {len(result.stderr)}")
    if result.returncode != 0:
        log("Step 5", f"  stderr: {result.stderr[:500]}")

    positions = []
    funds = {}

    if result.returncode == 0 and result.stdout.strip():
        stdout = result.stdout.strip()
        start = stdout.find('{')
        if start >= 0:
            depth = 0
            end = -1
            for i in range(start, len(stdout)):
                if stdout[i] == '{': depth += 1
                elif stdout[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > start:
                data = json.loads(stdout[start:end])
                funds = data.get('funds', {})
                raw_positions = data.get('positions', [])
                for p in raw_positions:
                    positions.append({
                        'code': p.get('code', ''),
                        'name': p.get('name', ''),
                        'qty': int(p.get('qty', 0)),
                        'can_sell_qty': int(p.get('can_sell_qty', 0)),
                        'nominal_price': float(p.get('nominal_price', 0)),
                        'market_val': float(p.get('market_val', 0)),
                        'pl_ratio_avg_cost': float(p.get('pl_ratio_avg_cost', 0)),
                        'unrealized_pl': float(p.get('unrealized_pl', 0)),
                    })
                log("Step 5", f"  通过 futu-api 获取持仓: {len(positions)} 只")

    # 按市值排序
    positions.sort(key=lambda p: p['market_val'], reverse=True)

    total_assets = funds.get('total_assets', sum(p['market_val'] for p in positions) + funds.get('cash', 0))
    cash = funds.get('cash', 0)

    log("Step 5", f"  持仓: {len(positions)} 只, 总资产: {total_assets:,.2f}, 现金: {cash:,.2f}")
    for p in positions:
        log("Step 5", f"    {p['code']} {p['name']}: {p['qty']} 股 @ {p['nominal_price']:.2f}, 市值 {p['market_val']:,.2f}, 盈亏 {p['pl_ratio_avg_cost']:.1f}%")

    save_json('05a_portfolio_scan.json', {
        'market': 'HK', 'account': 18767294,
        'positions': positions, 'funds': funds,
        'total_assets': total_assets, 'cash': cash,
        'position_count': len(positions)
    })

    # 5b. 组合风险指标
    log("Step 5", "5b. 计算组合风险指标...")
    weights = [p['market_val'] / total_assets for p in positions] if total_assets > 0 else []
    pl_ratios = [p['pl_ratio_avg_cost'] / 100.0 for p in positions]

    sharpe = calculate_sharpe_ratio(pl_ratios, weights) if weights else 0
    hhi = calculate_hhi(weights) if weights else 0
    concentration = calculate_concentration(weights) if weights else {'top3': 0, 'top5': 0, 'top10': 0}
    max_drawdown = calculate_max_drawdown_estimate(positions) if positions else 0
    cash_ratio = cash / total_assets if total_assets > 0 else 0

    risk_metrics = {
        'sharpe_ratio': round(sharpe, 3),
        'hhi': round(hhi, 4),
        'max_single_weight': round(max(weights), 4) if weights else 0,
        'top3_concentration': round(concentration.get('top3', 0), 4),
        'top5_concentration': round(concentration.get('top5', 0), 4),
        'max_drawdown_estimate': round(max_drawdown, 4),
        'cash_ratio': round(cash_ratio, 4),
        'cash': round(cash, 2),
        'total_assets': round(total_assets, 2),
        'total_market_value': round(sum(p['market_val'] for p in positions), 2),
    }

    log("Step 5", f"  Sharpe: {sharpe:.3f}, HHI: {hhi:.4f}, 现金比率: {cash_ratio*100:.1f}%")
    log("Step 5", f"  最大单股权重: {risk_metrics['max_single_weight']*100:.1f}%, Top3 集中度: {risk_metrics['top3_concentration']*100:.1f}%")

    # 5c. 逐股风控检查
    log("Step 5", "5c. 逐股风控检查...")
    risk_mgr = RiskManager()
    risk_checks = {}
    violations = []

    for pos in positions:
        weight = pos['market_val'] / total_assets if total_assets > 0 else 0
        check = risk_mgr.check({
            'code': pos['code'], 'action': 'HOLD',
            'price': pos['nominal_price'], 'quantity': pos['qty'],
            'position_ratio': weight
        })
        check_dict = check.to_dict()
        risk_checks[pos['code']] = check_dict

        for check_name, detail in check_dict.get('checks', {}).items():
            if not detail.get('passed', True):
                violations.append({
                    'code': pos['code'], 'check': check_name,
                    'detail': detail
                })

    if violations:
        log("Step 5", f"  ⚠️ 发现 {len(violations)} 项风控违规:")
        for v in violations:
            log("Step 5", f"    {v['code']}: {v['check']} - {v['detail']}")
    else:
        log("Step 5", "  ✅ 无风控违规")

    save_json('05b_portfolio_risk.json', {
        'metrics': risk_metrics,
        'risk_checks': risk_checks,
        'violations': violations
    })

    # 5d. 逐股重评估 (使用实时数据快速评估)
    log("Step 5", "5d. 逐股重评估...")
    diagnoses = {}

    from adapters.news_rss_adapter import RSSNewsAdapter
    from adapters.data_aggregator import DataAggregator

    rss = RSSNewsAdapter()
    aggregator = DataAggregator()

    for pos in positions:
        code = pos['code']
        name = pos['name']
        log("Step 5", f"  重评估 {code} {name}...")

        diag = {
            'code': code, 'name': name,
            'market_val': pos['market_val'],
            'pl_ratio': pos['pl_ratio_avg_cost'],
        }

        # 技术面
        try:
            tech = aggregator._get_futu_technical_data(code)
            diag['technical_signal'] = tech.get('signal', 'neutral')
            diag['rsi'] = tech.get('rsi', 50)
            diag['trend'] = tech.get('trend', 'unknown')
            log("Step 5", f"    技术: {tech.get('signal', 'unknown')}, RSI={tech.get('rsi', 50):.1f}")
        except Exception as e:
            log("Step 5", f"    技术面获取失败: {e}")
            diag['technical_signal'] = 'error'
            diag['trend'] = 'unknown'

        # 舆情
        try:
            sent = rss.get_sentiment_data(code, name)
            diag['sentiment_score'] = sent.get('sentiment_score', 0)
            diag['sentiment_label'] = sent.get('sentiment_label', 'neutral')
            log("Step 5", f"    舆情: {sent.get('sentiment_label', 'unknown')} ({sent.get('news_count', 0)} 条)")
        except Exception as e:
            log("Step 5", f"    舆情获取失败: {e}")
            diag['sentiment_score'] = 0

        # 基本面 (Futu 降级数据)
        try:
            fund = aggregator._get_fundamental_data(code)
            diag['pe_ratio'] = fund.get('pe_ratio', 'N/A')
            diag['pb_ratio'] = fund.get('pb_ratio', 'N/A')
            log("Step 5", f"    基本面: PE={diag['pe_ratio']}, PB={diag['pb_ratio']}")
        except Exception as e:
            log("Step 5", f"    基本面获取失败: {e}")
            diag['pe_ratio'] = 'N/A'
            diag['pb_ratio'] = 'N/A'

        # 生成诊断决策
        decision = _generate_diagnosis_decision(diag, pos)
        diag['decision'] = decision
        diagnoses[code] = diag

    save_json('05c_stock_diagnoses.json', {
        'market': 'HK', 'count': len(diagnoses), 'diagnoses': diagnoses
    })

    # 5e. 生成调仓信号
    log("Step 5", "5e. 生成调仓信号...")
    signals = []
    signal_counts = {'HOLD': 0, 'ADD': 0, 'REDUCE': 0, 'CLEAR': 0}

    for code, diag in diagnoses.items():
        signal = diag['decision']
        signal_counts[signal] = signal_counts.get(signal, 0) + 1

        if signal == 'REDUCE' or signal == 'CLEAR':
            signals.append({
                'code': code, 'name': diag['name'],
                'action': 'SELL' if signal == 'CLEAR' else 'REDUCE',
                'current_weight': round(diag['market_val'] / total_assets, 4) if total_assets > 0 else 0,
                'reason': f"诊断决策: {signal}",
                'priority': 'HIGH' if signal == 'CLEAR' else 'MEDIUM'
            })
        elif signal == 'ADD':
            signals.append({
                'code': code, 'name': diag['name'],
                'action': 'BUY',
                'current_weight': round(diag['market_val'] / total_assets, 4) if total_assets > 0 else 0,
                'reason': f"诊断决策: {signal}",
                'priority': 'LOW'
            })

        log("Step 5", f"  {code} {diag['name']}: {signal}")

    save_json('05d_rebalancing_signals.json', {
        'market': 'HK', 'signals': signals,
        'signal_counts': signal_counts,
        'total_signals': len(signals)
    })

    return positions, risk_metrics, diagnoses, signals, signal_counts

def _generate_diagnosis_decision(diag, pos):
    """根据诊断结果生成 HOLD/ADD/REDUCE/CLEAR 信号"""
    pl = pos.get('pl_ratio_avg_cost', 0)
    signal = diag.get('technical_signal', 'neutral')
    sentiment = diag.get('sentiment_score', 0)
    trend = diag.get('trend', 'unknown')

    # 止损优先
    if pl < -15:
        return 'CLEAR'
    if pl < -8:
        return 'REDUCE'

    # 技术面 + 舆情综合
    sell_signals = 0
    buy_signals = 0

    if signal == 'sell': sell_signals += 2
    elif signal == 'buy': buy_signals += 2

    if sentiment < -0.3: sell_signals += 1
    elif sentiment > 0.3: buy_signals += 1

    if trend == 'down': sell_signals += 1
    elif trend == 'up': buy_signals += 1

    if pl < -3: sell_signals += 1
    elif pl > 5: buy_signals += 1

    if sell_signals >= 3:
        return 'CLEAR' if sell_signals >= 4 else 'REDUCE'
    elif buy_signals >= 3:
        return 'ADD'

    return 'HOLD'

# ============================================================
# Step 6: 生成完整报告
# ============================================================
def step6_generate_report(positions, risk_metrics, diagnoses, signals, signal_counts, analysis_results, debate_results, recommendations):
    log("Step 6", "生成完整审计报告...")

    report = []
    report.append("# 港股选股与模拟盘持仓调整 — 完整审计报告")
    report.append("")
    report.append(f"**执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**市场**: 港股 (HK)")
    report.append(f"**账户**: 18767294 (港股模拟盘)")
    report.append("")

    # 选股部分
    report.append("## 一、选股结果 (Workflow C Step 1)")
    report.append("")
    report.append("| 排名 | 代码 | 名称 | 波动率% | 5日动量% | 10日动量% |")
    report.append("|------|------|------|---------|----------|-----------|")
    import pandas as pd
    result_file = Path.home() / '.openclaw' / 'workspace' / 'agents' / 'main' / 'data' / 'stock-pick' / 'factors' / 'result_hk_20260414.csv'
    df = pd.read_csv(result_file)
    for i, (_, row) in enumerate(df.iterrows(), 1):
        report.append(f"| {i} | {row['ts_code']} | {row['name']} | {row['volatility']:.2f} | {row['momentum_5d']:.2f} | {row['momentum_10d']:.2f} |")
    report.append("")

    # 分析部分
    report.append("## 二、多维度分析 (Workflow C Step 2)")
    report.append("")
    report.append("| 代码 | 名称 | 价格 | 涨跌% | PE | RSI | 技术信号 | 舆情 | 综合评分 |")
    report.append("|------|------|------|-------|----|-----|----------|------|----------|")
    for a in analysis_results:
        report.append(f"| {a['code']} | {a['name']} | {a.get('last_price', 'N/A')} | {a.get('price_change_pct', 0):.2f}% | {a.get('pe_ratio', 'N/A')} | {a.get('rsi', 50):.1f} | {a.get('technical_signal', 'N/A')} | {a.get('sentiment_label', 'N/A')} | {a['composite_score']:.1f}/10 |")
    report.append("")

    # 辩论部分
    report.append("## 三、多空辩论 (Workflow C Step 3)")
    report.append("")
    for d in debate_results:
        report.append(f"### {d['code']} {d['name']}")
        report.append(f"- **建议**: {d['recommendation']} (置信度 {d['confidence']:.0%})")
        report.append(f"- **风控**: {d['risk_approval']}")
        report.append(f"- **看多**: {'; '.join(d['bull_points'])}")
        report.append(f"- **看空**: {'; '.join(d['bear_points'])}")
        report.append("")

    # 持仓诊断
    report.append("## 四、持仓诊断 (Workflow D)")
    report.append("")
    report.append("### 4.1 当前持仓概览")
    report.append("")
    report.append("| 代码 | 名称 | 数量 | 价格 | 市值 | 盈亏% |")
    report.append("|------|------|------|------|------|-------|")
    for p in positions:
        report.append(f"| {p['code']} | {p['name']} | {p['qty']} | {p['nominal_price']:.2f} | {p['market_val']:,.2f} | {p['pl_ratio_avg_cost']:.1f}% |")
    report.append("")

    report.append("### 4.2 组合风险指标")
    report.append("")
    report.append("| 指标 | 数值 | 说明 |")
    report.append("|------|------|------|")
    report.append(f"| Sharpe Ratio | {risk_metrics['sharpe_ratio']} | >1.0 良好 |")
    report.append(f"| HHI 集中度 | {risk_metrics['hhi']} | <0.15 分散 |")
    report.append(f"| 最大单股权重 | {risk_metrics['max_single_weight']*100:.1f}% | ≤20% |")
    report.append(f"| Top-3 集中度 | {risk_metrics['top3_concentration']*100:.1f}% | |")
    report.append(f"| 估算最大回撤 | {risk_metrics['max_drawdown_estimate']*100:.1f}% | |")
    report.append(f"| 现金比率 | {risk_metrics['cash_ratio']*100:.1f}% | ≥10% |")
    report.append("")

    report.append("### 4.3 逐股诊断与调仓信号")
    report.append("")
    report.append("| 代码 | 名称 | 市值 | 盈亏% | 技术信号 | RSI | 舆情 | 调仓信号 |")
    report.append("|------|------|------|-------|----------|-----|------|----------|")
    for code, diag in diagnoses.items():
        signal_emoji = {'HOLD': '🔵', 'ADD': '🟢', 'REDUCE': '🟡', 'CLEAR': '🔴'}.get(diag['decision'], '⚪')
        report.append(f"| {code} | {diag['name']} | {diag['market_val']:,.0f} | {diag['pl_ratio']:.1f}% | {diag.get('technical_signal', 'N/A')} | {diag.get('rsi', 50):.1f} | {diag.get('sentiment_label', 'N/A')} | {signal_emoji} {diag['decision']} |")
    report.append("")

    report.append("### 4.4 调仓信号汇总")
    report.append("")
    report.append(f"- HOLD (维持): {signal_counts.get('HOLD', 0)}")
    report.append(f"- ADD (加仓): {signal_counts.get('ADD', 0)}")
    report.append(f"- REDUCE (减仓): {signal_counts.get('REDUCE', 0)}")
    report.append(f"- CLEAR (清仓): {signal_counts.get('CLEAR', 0)}")
    report.append("")

    if signals:
        report.append("### 4.5 建议操作")
        report.append("")
        for s in sorted(signals, key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(x['priority'], 3)):
            report.append(f"- **{s['priority']}**: {s['code']} {s['name']} → {s['action']} — {s['reason']}")
        report.append("")

    # 投资建议
    report.append("## 五、投资建议 (Workflow C Step 4)")
    report.append("")
    for r in recommendations:
        report.append(f"- **{r['code']} {r['name']}**: {r['action']} (置信度 {r['confidence']:.0%})")
    report.append("")

    # 过程指引
    report.append("## 六、过程指引与学习要点")
    report.append("")
    report.append("### 6.1 执行链路")
    report.append("")
    report.append("```")
    report.append("选股 (stock-pick) → 多维度分析 (DataAggregator) → 多空辩论 → 投资建议")
    report.append("     ↓")
    report.append("持仓扫描 (Futu OpenD) → 组合风险 (portfolio_metrics) → 逐股诊断 → 调仓信号")
    report.append("```")
    report.append("")

    report.append("### 6.2 关键学习要点")
    report.append("")
    report.append("1. **选股逻辑**: 港股使用简化因子 (波动率 + 动量)，筛选低波动、高动量股票")
    report.append("2. **技术面计算**: 通过 Futu K-line 计算 MACD(12,26,9), RSI(14), KDJ(9,3,3), MA(5,10,20,60), 布林带(20,2)")
    report.append("3. **舆情权重**: RSS 舆情占 50% 权重，优先于 TrendRadar(30-40%) 和 WebSearch(20%)")
    report.append("4. **风控规则**: 单股≤20%, 现金≥10%, 单笔止损-8%, 总止损-15%")
    report.append("5. **调仓信号**: CLEAR(清仓) > REDUCE(减仓) > ADD(加仓) > HOLD(维持)")
    report.append("6. **降级策略**: 当数据源不可用时，使用行业特定估值估计而非 mock 数据")
    report.append("")

    report.append("### 6.3 输出文件")
    report.append("")
    report.append(f"所有数据存储在: `{OUTPUT_DIR}`")
    report.append("")
    for f in sorted(OUTPUT_DIR.glob('*.json')):
        report.append(f"- `{f.name}`")
    report.append("")

    report_text = "\n".join(report)

    md_path = OUTPUT_DIR / 'full_audit_report.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    # 保存完整 JSON 报告
    full_report = {
        'execution_time': datetime.now().isoformat(),
        'market': 'HK', 'account': 18767294,
        'workflow_c': {
            'selected_stocks': len(analysis_results),
            'analysis': analysis_results,
            'debate': debate_results,
            'recommendations': recommendations,
        },
        'workflow_d': {
            'positions': positions,
            'risk_metrics': risk_metrics,
            'diagnoses': diagnoses,
            'signals': signals,
            'signal_counts': signal_counts,
        }
    }
    save_json('full_audit_report.json', full_report)

    log("Step 6", f"报告已保存: {md_path}")
    return report_text


# ============================================================
# 主执行流程
# ============================================================
def main():
    print("=" * 70)
    print("港股选股与模拟盘持仓调整 — 完整执行")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Step 1: 选股
    stocks = step1_load_stock_pick()
    if not stocks:
        print("选股失败，终止执行")
        return

    # Step 2: 多维度分析
    analysis_results = step2_analyze_stocks(stocks)

    # Step 3: 多空辩论
    debate_results = step3_debate(analysis_results)

    # Step 4: 投资建议
    recommendations = step4_recommendations(debate_results)

    # Step 5: 持仓诊断
    positions, risk_metrics, diagnoses, signals, signal_counts = step5_portfolio_diagnosis()

    # Step 6: 完整报告
    report = step6_generate_report(
        positions, risk_metrics, diagnoses, signals, signal_counts,
        analysis_results, debate_results, recommendations
    )

    print("\n" + "=" * 70)
    print("执行完成!")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
