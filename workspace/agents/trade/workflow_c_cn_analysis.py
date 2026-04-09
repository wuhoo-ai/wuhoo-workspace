#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow C A股版 - 完整全链路分析

完整流程:
1. 读取选股结果
2. 多维度分析 (技术面/基本面/舆情面)
3. 多空辩论
4. 投资建议生成
5. 风控检查
6. 生成综合报告
7. 日度复盘

跳过交易执行环节，仅做分析
"""
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# 路径配置
DEBATE_DIR = Path('/home/admin/.openclaw/workspace/agents/debate')
STOCK_PICK_DIR = Path('/home/admin/.openclaw/workspace/agents/main/skills/stock-pick')
TRADE_DIR = Path('/home/admin/.openclaw/workspace/agents/trade')
WORKFLOW_C_DIR = TRADE_DIR / 'data' / 'workflow_c' / 'CN_2026-04-07'
WORKFLOW_C_DIR.mkdir(parents=True, exist_ok=True)

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

sys.path.insert(0, str(DEBATE_DIR))
sys.path.insert(0, str(STOCK_PICK_DIR))
sys.path.insert(0, str(TRADE_DIR))

from run_debate import run_full_debate
from audit_module import WorkflowAudit


def load_selected_stocks():
    """读取选股结果"""
    result_file = Path('/home/admin/.openclaw/workspace/agents/main/data/stock-pick/factors/result_cn_20260407.csv')
    import pandas as pd
    df = pd.read_csv(result_file)
    stocks = []
    for _, row in df.iterrows():
        stocks.append({
            'code': row['ts_code'],
            'name': row['name'],
            'composite_score': row.get('composite_score', 0),
            'momentum_10d': row.get('momentum_10d', 0),
            'residual_vol': row.get('residual_vol', 0),
            'turnover_5d': row.get('turnover_5d', 0),
            'momentum_5d': row.get('momentum_5d', 0),
            'beta_20d': row.get('beta_20d', 0),
        })
    return stocks


def step2_multi_dimensional_analysis(stocks):
    """
    Step 2: 多维度分析
    对每只股票进行技术面、基本面、舆情面独立评分
    """
    print(f"\n{'='*70}")
    print("【Step 2】多维度分析（技术面/基本面/舆情面）")
    print(f"{'='*70}")

    # 导入 DataAggregator
    from adapters.data_aggregator import DataAggregator
    aggregator = DataAggregator()

    analysis_results = []
    for i, stock in enumerate(stocks):
        print(f"\n[{i+1}/{len(stocks)}] {stock['code']} {stock['name']}...")

        try:
            data = aggregator.get_all_data(stock['code'], stock['name'])

            tech = data.get('technical_data', {})
            fund = data.get('fundamental_data', {})
            sent = data.get('sentiment_data', {})
            factor = data.get('factor_data', {})
            dq = data.get('data_quality', {})

            # 技术面评分
            tech_score = 0
            tech_signals = []
            if tech.get('rsi') is not None:
                rsi = tech['rsi']
                if rsi < 30:
                    tech_score += 2; tech_signals.append(f"RSI超卖({rsi:.1f})")
                elif rsi > 70:
                    tech_score -= 1; tech_signals.append(f"RSI超买({rsi:.1f})")
                else:
                    tech_score += 1; tech_signals.append(f"RSI中性({rsi:.1f})")

            if tech.get('macd'):
                if tech['macd'] in ('golden_cross', 'bullish'):
                    tech_score += 1; tech_signals.append(f"MACD多头")
                elif tech['macd'] in ('death_cross', 'bearish'):
                    tech_score -= 1; tech_signals.append(f"MACD空头")

            if tech.get('trend') == 'uptrend':
                tech_score += 1; tech_signals.append("上升趋势")
            elif tech.get('trend') == 'downtrend':
                tech_score -= 1; tech_signals.append("下降趋势")

            tech_score = max(-3, min(3, tech_score))

            # 基本面评分
            fund_score = 0
            fund_signals = []
            if fund.get('pe_ttm') and 0 < fund['pe_ttm'] < 30:
                fund_score += 1; fund_signals.append(f"PE合理({fund['pe_ttm']:.1f})")
            elif fund.get('pe_ttm') and fund['pe_ttm'] > 50:
                fund_score -= 1; fund_signals.append(f"PE偏高({fund['pe_ttm']:.1f})")

            if fund.get('roe') and fund['roe'] > 15:
                fund_score += 1; fund_signals.append(f"ROE优秀({fund['roe']:.1f}%)")

            # 舆情面评分
            sent_score = 0
            sent_signals = []
            if sent.get('sentiment_score') is not None:
                ss = sent['sentiment_score']
                if ss > 0.2:
                    sent_score = 1; sent_signals.append(f"情绪正面({ss:.2f})")
                elif ss < -0.2:
                    sent_score = -1; sent_signals.append(f"情绪负面({ss:.2f})")
                else:
                    sent_score = 0; sent_signals.append(f"情绪中性({ss:.2f})")

            # 综合评分
            total_score = tech_score + fund_score + sent_score

            analysis = {
                'code': stock['code'],
                'name': stock['name'],
                'factor_score': stock['composite_score'],
                'technical_score': tech_score,
                'technical_signals': tech_signals,
                'fundamental_score': fund_score,
                'fundamental_signals': fund_signals,
                'sentiment_score': sent_score,
                'sentiment_signals': sent_signals,
                'total_score': total_score,
                'data_quality': dq.get('overall', 'unknown'),
                'data_sources': dq,
                'recommendation': 'BUY' if total_score >= 3 else ('SELL' if total_score <= -2 else 'HOLD'),
            }
            analysis_results.append(analysis)

            print(f"  技术面: {tech_score:+d} ({', '.join(tech_signals)})")
            print(f"  基本面: {fund_score:+d} ({', '.join(fund_signals) if fund_signals else '数据不足'})")
            print(f"  舆情面: {sent_score:+d} ({', '.join(sent_signals)})")
            print(f"  综合: {total_score:+d} -> {analysis['recommendation']}")
            print(f"  数据质量: {dq.get('overall', 'unknown')}")

        except Exception as e:
            print(f"  ❌ 分析失败: {e}")
            analysis_results.append({
                'code': stock['code'],
                'name': stock['name'],
                'error': str(e),
                'total_score': 0,
                'recommendation': 'HOLD'
            })

    # 保存多维度分析结果
    with open(WORKFLOW_C_DIR / '02_multi_dimensional_analysis.json', 'w', encoding='utf-8') as f:
        json.dump({
            'date': '2026-04-07',
            'market': 'CN',
            'analysis': analysis_results,
        }, f, ensure_ascii=False, indent=2)

    return analysis_results


def step3_debate(stocks, multi_dim_results):
    """
    Step 3: 多空辩论
    基于多维度分析结果进行辩论
    """
    print(f"\n{'='*70}")
    print("【Step 3】逐只运行多空辩论")
    print(f"{'='*70}")

    debate_results = []
    start_time = time.time()

    for i, stock in enumerate(stocks):
        elapsed = time.time() - start_time
        multi_dim = next((m for m in multi_dim_results if m.get('code') == stock['code']), None)
        rec = multi_dim.get('recommendation', 'HOLD') if multi_dim else 'HOLD'
        score = multi_dim.get('total_score', 0) if multi_dim else 0

        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(stocks)}] {stock['code']} {stock['name']} (多维评分:{score:+d}, 建议:{rec}) (已用时 {elapsed:.0f}s)")
        print(f"{'='*60}")

        try:
            result = run_full_debate(
                stock['code'],
                stock['name'],
                use_real_data=True,
                output_dir=str(WORKFLOW_C_DIR)
            )

            summary = {
                'code': stock['code'],
                'name': stock['name'],
                'multi_dim_score': score,
                'multi_dim_recommendation': rec,
                'debate_id': result.get('debate_id', ''),
                'bull_recommendation': result.get('bull_view', {}).get('recommendation', ''),
                'bull_confidence': result.get('bull_view', {}).get('confidence', 0),
                'bull_key_points': result.get('bull_view', {}).get('key_points', []),
                'bear_recommendation': result.get('bear_view', {}).get('recommendation', ''),
                'bear_confidence': result.get('bear_view', {}).get('confidence', 0),
                'bear_key_points': result.get('bear_view', {}).get('key_points', []),
                'consensus_points': result.get('consensus_points', []),
                'disagreement_points': result.get('disagreement_points', []),
                'trader_decision': result.get('trader_decision', {}).get('decision', ''),
                'trader_confidence': result.get('trader_decision', {}).get('confidence', 0),
                'trader_reasoning': result.get('trader_decision', {}).get('reasoning', ''),
                'trader_position': result.get('trader_decision', {}).get('position_size', 0),
                'risk_approved': result.get('risk_approval', {}).get('approved', False),
                'risk_score': result.get('risk_approval', {}).get('risk_score', 0),
                'risk_recommendation': result.get('risk_approval', {}).get('recommendation', ''),
                'risk_conditions': result.get('risk_approval', {}).get('conditions', []),
                'risk_warnings': result.get('risk_approval', {}).get('warnings', []),
                'final_action': result.get('final_action', {}).get('action', ''),
                'final_reason': result.get('final_action', {}).get('reason', ''),
                'data_quality': result.get('data_quality', {}),
                'sentiment_summary': result.get('sentiment_summary', {}),
                'timestamp': result.get('timestamp', ''),
            }
            debate_results.append(summary)

            print(f"  最终动作: {summary['final_action']}")
            print(f"  原因: {summary['final_reason']}")
            print(f"  数据质量: {summary.get('data_quality', {}).get('overall', 'unknown')}")

        except Exception as e:
            print(f"  ❌ 辩论失败: {e}")
            debate_results.append({
                'code': stock['code'],
                'name': stock['name'],
                'error': str(e),
                'final_action': 'error'
            })

    # 保存辩论汇总
    with open(WORKFLOW_C_DIR / '03_debate_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'date': '2026-04-07',
            'market': 'CN',
            'total_stocks': len(stocks),
            'results': debate_results,
            'execution_time_seconds': round(time.time() - start_time, 1)
        }, f, ensure_ascii=False, indent=2)

    return debate_results


def step4_generate_recommendations(stocks, multi_dim_results, debate_results):
    """
    Step 4: 投资建议生成
    综合多维度分析和辩论结果，生成最终投资建议
    """
    print(f"\n{'='*70}")
    print("【Step 4】生成投资建议")
    print(f"{'='*70}")

    recommendations = []
    for stock, multi_dim, debate in zip(stocks, multi_dim_results, debate_results):
        if debate.get('error'):
            recommendations.append({
                'code': stock['code'],
                'name': stock['name'],
                'recommendation': 'SKIP',
                'reason': f'辩论失败: {debate.get("error", "")}',
                'confidence': 0,
                'position_size': 0,
            })
            continue

        # 综合多维度分析和辩论结果
        final_action = debate.get('final_action', '')
        trader_decision = debate.get('trader_decision', '')
        trader_conf = debate.get('trader_confidence', 0)
        risk_rec = debate.get('risk_recommendation', '')
        multi_rec = multi_dim.get('recommendation', 'HOLD')

        # 决策逻辑
        if final_action in ('buy', 'execute') and trader_decision in ('BUY', 'buy'):
            recommendation = 'BUY'
            position = min(debate.get('trader_position', 0.05), 0.20)  # 单股上限 20%
        elif final_action in ('reject', 'modify') or risk_rec == 'REJECT':
            recommendation = 'REJECT'
            position = 0
        elif trader_decision in ('HOLD', 'watch') or final_action in ('hold', 'watch'):
            recommendation = 'WATCH'
            position = 0
        else:
            recommendation = 'WATCH'
            position = 0

        rec = {
            'code': stock['code'],
            'name': stock['name'],
            'recommendation': recommendation,
            'confidence': trader_conf,
            'position_size': position,
            'multi_dim_score': multi_dim.get('total_score', 0),
            'multi_dim_recommendation': multi_rec,
            'bull_view': debate.get('bull_recommendation', ''),
            'bear_view': debate.get('bear_recommendation', ''),
            'trader_reasoning': debate.get('trader_reasoning', ''),
            'risk_score': debate.get('risk_score', 0),
            'risk_conditions': debate.get('risk_conditions', []),
            'reason': debate.get('final_reason', ''),
        }
        recommendations.append(rec)

        print(f"  {stock['code']} {stock['name']}: {recommendation} (置信度: {trader_conf:.2f}, 仓位: {position:.1%})")

    # 保存推荐结果
    with open(WORKFLOW_C_DIR / '04_recommendations.json', 'w', encoding='utf-8') as f:
        json.dump({
            'date': '2026-04-07',
            'market': 'CN',
            'recommendations': recommendations,
        }, f, ensure_ascii=False, indent=2)

    return recommendations


def generate_report(stocks, multi_dim_results, debate_results, recommendations):
    """
    Step 5: 生成综合分析报告
    """
    print(f"\n{'='*70}")
    print("【Step 5】生成综合分析报告")
    print(f"{'='*70}")

    report = []
    report.append("# Workflow C A股分析报告")
    report.append(f"\n**日期**: 2026-04-07\n")
    report.append(f"**股票池**: 中证1000\n")
    report.append(f"**筛选逻辑**: 252日残差波动率 ≤ 50%分位 → 5日换手率 ≥ 50%分位 → 5日动量 ≥ 70%分位 → 20日Beta ≥ 70%分位 → 按10日动量排序Top10\n")

    # 统计
    buy_count = sum(1 for r in recommendations if r['recommendation'] == 'BUY')
    watch_count = sum(1 for r in recommendations if r['recommendation'] == 'WATCH')
    reject_count = sum(1 for r in recommendations if r['recommendation'] == 'REJECT')
    error_count = sum(1 for r in debate_results if r.get('error'))

    # 数据质量统计
    good_count = sum(1 for r in debate_results if r.get('data_quality', {}).get('overall') == 'good')
    degraded_count = sum(1 for r in debate_results if r.get('data_quality', {}).get('overall') == 'degraded')

    report.append("## 总体统计")
    report.append(f"| 分类 | 数量 |")
    report.append(f"|------|------|")
    report.append(f"| 总候选 | {len(stocks)} |")
    report.append(f"| 建议买入 | {buy_count} |")
    report.append(f"| 建议观望 | {watch_count} |")
    report.append(f"| 建议拒绝 | {reject_count} |")
    report.append(f"| 执行错误 | {error_count} |")
    report.append("")
    report.append("## 数据质量")
    report.append(f"| 质量等级 | 数量 |")
    report.append(f"|------|------|")
    report.append(f"| Good (真实数据) | {good_count} |")
    report.append(f"| Degraded (降级数据) | {degraded_count} |")

    # 多维度分析汇总
    report.append("\n## 多维度分析汇总\n")
    for m in multi_dim_results:
        if m.get('error'):
            continue
        report.append(f"### {m['code']} {m['name']}")
        report.append(f"- 技术面: {m.get('technical_score', 0):+d} ({', '.join(m.get('technical_signals', []))})")
        report.append(f"- 基本面: {m.get('fundamental_score', 0):+d} ({', '.join(m.get('fundamental_signals', []))})")
        report.append(f"- 舆情面: {m.get('sentiment_score', 0):+d} ({', '.join(m.get('sentiment_signals', []))})")
        report.append(f"- **综合: {m.get('total_score', 0):+d} → {m.get('recommendation', 'HOLD')}**")
        report.append("")

    # 逐股深度分析
    report.append("\n## 逐股深度分析\n")
    for stock, result, rec in zip(stocks, debate_results, recommendations):
        report.append(f"### {stock['code']} {stock['name']}")
        report.append(f"\n**选股因子**:")
        report.append(f"- 10日动量: {stock['momentum_10d']:.2f}%")
        report.append(f"- 252日残差波动率: {stock['residual_vol']:.4f}")
        report.append(f"- 5日换手率: {stock['turnover_5d']:.2f}%")
        report.append(f"- 5日动量: {stock['momentum_5d']:.2f}%")
        report.append(f"- 20日Beta: {stock['beta_20d']:.4f}")

        if result.get('error'):
            report.append(f"\n⚠️ **辩论失败**: {result['error']}")
            report.append("")
            continue

        dq = result.get('data_quality', {})
        report.append(f"\n**数据质量**: {dq.get('overall', 'unknown')}")
        if dq.get('warning'):
            report.append(f"- ⚠️ {dq['warning']}")

        report.append(f"\n**投资建议**: **{rec['recommendation']}** (置信度: {rec['confidence']:.2f}, 建议仓位: {rec['position_size']:.1%})")
        report.append(f"- 原因: {rec.get('reason', '')}")

        report.append(f"\n**辩论结果**:")
        report.append(f"- 多方: {result.get('bull_recommendation','')} (置信度:{result.get('bull_confidence',0):.2f})")
        report.append(f"- 空方: {result.get('bear_recommendation','')} (置信度:{result.get('bear_confidence',0):.2f})")

        if result.get('consensus_points'):
            report.append(f"\n**共识点**:")
            for pt in result['consensus_points']:
                report.append(f"- {pt}")

        if result.get('disagreement_points'):
            report.append(f"\n**分歧点**:")
            for pt in result['disagreement_points']:
                report.append(f"- {pt}")

        if rec.get('risk_conditions'):
            report.append(f"\n**风控条件**:")
            for cond in rec['risk_conditions']:
                report.append(f"- ⚠️ {cond}")
        if rec.get('risk_warnings'):
            for warn in rec.get('risk_warnings', []):
                report.append(f"- ⚠️ {warn}")

        report.append("")

    # 最终结论
    report.append("## 最终结论与建议")
    if buy_count > 0:
        report.append(f"\n有 {buy_count} 只股票通过辩论和风控，可以考虑介入。")
        for r in recommendations:
            if r['recommendation'] == 'BUY':
                report.append(f"- **{r['code']} {r['name']}**: 仓位 {r['position_size']:.1%}, {r.get('trader_reasoning', '')[:200]}")
    else:
        report.append("\n当前所有候选股均未通过多空辩论和风控审核。")
        report.append("\n**建议**: 等待更好的入场时机，或调整筛选因子权重。")

    report_path = WORKFLOW_C_DIR / 'workflow_analysis_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    print(f"报告已保存: {report_path}")


def step6_daily_review(stocks, recommendations):
    """
    Step 6: 日度复盘
    汇总当日所有分析结果
    """
    print(f"\n{'='*70}")
    print("【Step 6】日度复盘")
    print(f"{'='*70}")

    # 导入 daily_review
    sys.path.insert(0, str(TRADE_DIR))
    from daily_review import DailyReviewGenerator

    try:
        reviewer = DailyReviewGenerator(date='2026-04-07')
        review = reviewer.generate_report()

        # 保存复盘结果
        with open(WORKFLOW_C_DIR / '06_daily_review.json', 'w', encoding='utf-8') as f:
            json.dump(review, f, ensure_ascii=False, indent=2, default=str)

        print("日度复盘完成")
    except Exception as e:
        print(f"日度复盘生成失败: {e}")


def run_full_workflow():
    print("=" * 70)
    print("Workflow C - A股 (中证1000) 全链路分析")
    print(f"日期：2026-04-07")
    print(f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 初始化审计模块
    audit = WorkflowAudit(date='2026-04-07', market='CN', output_dir=WORKFLOW_C_DIR)

    # Step 1: 读取选股结果
    print("\n【Step 1】读取选股结果...")
    selected_stocks = load_selected_stocks()
    print(f"共选出 {len(selected_stocks)} 只股票")
    for i, s in enumerate(selected_stocks):
        print(f"  {i+1}. {s['code']} {s['name']} (综合得分: {s['composite_score']:.4f})")

    with open(WORKFLOW_C_DIR / '01_selected_stocks.json', 'w', encoding='utf-8') as f:
        json.dump({
            "date": "2026-04-07",
            "market": "CN",
            "universe": "中证1000",
            "selected_count": len(selected_stocks),
            "stocks": [{k: str(v) for k, v in s.items()} for s in selected_stocks]
        }, f, ensure_ascii=False, indent=2)

    audit.record_step("stock_pick", selected_stocks)

    # Step 2: 多维度分析
    multi_dim_results = step2_multi_dimensional_analysis(selected_stocks)
    audit.record_step("multi_dimensional", {
        "date": "2026-04-07",
        "market": "CN",
        "analysis": multi_dim_results,
    })

    # Step 3: 多空辩论
    debate_results = step3_debate(selected_stocks, multi_dim_results)
    audit.record_step("debate", {
        "date": "2026-04-07",
        "market": "CN",
        "total_stocks": len(selected_stocks),
        "results": debate_results,
    })

    # Step 4: 投资建议
    recommendations = step4_generate_recommendations(selected_stocks, multi_dim_results, debate_results)
    audit.record_step("recommendations", {
        "date": "2026-04-07",
        "market": "CN",
        "recommendations": recommendations,
    })

    # Step 5: 综合报告
    generate_report(selected_stocks, multi_dim_results, debate_results, recommendations)

    # Step 6: 日度复盘
    step6_daily_review(selected_stocks, recommendations)
    # 尝试加载日度复盘结果用于审计
    daily_review_path = WORKFLOW_C_DIR / '06_daily_review.json'
    if daily_review_path.exists():
        with open(daily_review_path, 'r', encoding='utf-8') as f:
            daily_review_data = json.load(f)
        audit.record_step("daily_review", daily_review_data)
    else:
        audit.record_step("daily_review", {"error": "日度复盘文件未生成"})

    # ─────────── 逐股审计 ───────────
    print(f"\n{'='*70}")
    print(" 执行逐股审计...")
    print(f"{'='*70}")
    for stock, multi_dim, debate, rec in zip(selected_stocks, multi_dim_results, debate_results, recommendations):
        entry = audit.audit_stock(
            code=stock['code'],
            name=stock['name'],
            multi_dim=multi_dim,
            debate=debate,
            recommendation=rec,
        )
        icon = "✅" if entry.is_reliable else "❌"
        print(f"  {icon} {stock['code']} {stock['name']}: 可靠性 {entry.reliability:.1f}/100 ({len(entry.alerts)} 条告警)")

    # ─────────── 保存审计报告 ───────────
    audit_json_path = WORKFLOW_C_DIR / '05_audit_report.json'
    audit_md_path = WORKFLOW_C_DIR / 'audit_report.md'

    audit.save(audit_json_path)
    audit.save_markdown(audit_md_path)
    audit.print_summary()

    print(f"\n 审计报告已保存:")
    print(f"  JSON: {audit_json_path}")
    print(f"  Markdown: {audit_md_path}")

    print(f"\n{'='*70}")
    print("Workflow C 执行完成")
    print(f"输出目录: {WORKFLOW_C_DIR}")
    print(f"{'='*70}")


if __name__ == '__main__':
    run_full_workflow()
