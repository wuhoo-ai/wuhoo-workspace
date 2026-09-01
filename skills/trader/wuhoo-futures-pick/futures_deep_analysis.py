#!/usr/bin/env python3
"""
futures_deep_analysis.py — 期货深度分析报告生成器 Phase 2.3
整合: 技术面 + 因子 + 辩论结果 → 结构化决策报告

用法:
  python3.11 futures_deep_analysis.py --code US.MNQmain --date 2026-05-08
  python3.11 futures_deep_analysis.py --code US.MNQmain --date 2026-05-08 --json

输出: ~/wuhoo-workspace/data/futures/diagnose/{date}/deep_{code}.md
      ~/wuhoo-workspace/data/futures/diagnose/{date}/deep_{code}.json
"""

import sys, json, argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

DATA_DIR = Path.home() / "wuhoo-workspace" / "data" / "futures"
FACTORS_DIR = DATA_DIR / "factors"
DEBATE_DIR = DATA_DIR / "debate"
DIAGNOSE_DIR = DATA_DIR / "diagnose"
CONTRACT_INFO_PATH = DATA_DIR / "contract_info.json"


def load_contract_info():
    with open(CONTRACT_INFO_PATH) as f:
        return json.load(f)


def load_factors(date_str: str, code: str) -> dict:
    path = FACTORS_DIR / f"factors_{date_str}.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    row = df[df["code"] == code]
    if row.empty:
        return {}
    result = {}
    for col in row.columns:
        v = row[col].iloc[0]
        if not pd.isna(v):
            result[col] = float(v) if isinstance(v, (np.floating, float)) else v
    return result


def load_debate(date_str: str, code: str) -> dict:
    path = DEBATE_DIR / date_str / f"debate_{code}.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def load_technical(date_str: str, code: str) -> dict:
    path = DEBATE_DIR / date_str / f"tech_{code}.json"
    if not path.exists():
        # Try generating on the fly
        return {}
    with open(path) as f:
        return json.load(f)


def generate_report(code: str, date_str: str) -> dict:
    """生成完整深度分析报告"""
    contracts = load_contract_info()
    info = contracts.get(code, {})
    name = info.get("name", code)
    market = info.get("market", "US")
    category = info.get("category", "期货")
    lot_size = info.get("lot_size", 1)
    long_margin = info.get("long_margin", 0)
    short_margin = info.get("short_margin", 0)
    margin_ccy = info.get("margin_currency", "USD")

    factors = load_factors(date_str, code)
    debate = load_debate(date_str, code)

    # 加载技术分析 (run futures_technical inline)
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from futures_technical import analyze as tech_analyze
        tech = tech_analyze(code)
    except Exception:
        tech = {"error": "技术分析不可用"}

    # 构建报告数据结构
    report = {
        "meta": {
            "code": code,
            "name": name,
            "market": market,
            "category": category,
            "date": date_str,
            "generated_at": datetime.now().isoformat(),
        },
        "contract_specs": {
            "lot_size": lot_size,
            "long_margin": long_margin,
            "short_margin": short_margin,
            "margin_currency": margin_ccy,
        },
        "market_data": {
            "close": factors.get("close"),
            "momentum_10d": factors.get("momentum_10d"),
            "momentum_20d": factors.get("momentum_20d"),
            "volatility_20d": factors.get("volatility_20d"),
            "volatility_60d": factors.get("volatility_60d"),
            "adx_14": factors.get("adx_14"),
            "volume_ratio": factors.get("volume_ratio"),
            "ma20_deviation": factors.get("ma20_deviation"),
            "sharpe_20d": factors.get("sharpe_20d"),
        },
        "factor_scores": {
            "long_score": factors.get("long_score"),
            "short_score": factors.get("short_score"),
        },
        "technical_analysis": tech,
        "debate": {
            "bull": debate.get("bull", {}),
            "bear": debate.get("bear", {}),
            "trader": debate.get("trader", {}),
            "risk": debate.get("risk", {}),
            "final_decision": debate.get("final_decision", "UNKNOWN"),
            "final_confidence": debate.get("final_confidence", 0),
        },
        "decision": synthesize_decision(tech, debate, factors),
    }

    return report


def synthesize_decision(tech: dict, debate: dict, factors: dict) -> dict:
    """综合技术面+辩论+因子 → 最终决策建议"""
    tech_score = tech.get("technical_score", {}).get("score", 5)
    tech_label = tech.get("technical_score", {}).get("label", "neutral")

    trader = debate.get("trader", {})
    risk = debate.get("risk", {})
    bull = debate.get("bull", {})
    bear = debate.get("bear", {})

    debate_decision = trader.get("decision", "HOLD")
    debate_confidence = trader.get("confidence", 0.5)
    risk_approved = risk.get("approved", True)

    long_score = factors.get("long_score", 0)
    short_score = factors.get("short_score", 0)

    # 综合评分
    signals = []
    weight = 0

    # 技术面信号
    if tech_score >= 7:
        signals.append({"source": "technical", "direction": "LONG", "strength": 1.0})
    elif tech_score >= 6:
        signals.append({"source": "technical", "direction": "LONG", "strength": 0.5})
    elif tech_score <= 3.5:
        signals.append({"source": "technical", "direction": "SHORT", "strength": 0.5})

    # 辩论信号
    if debate_decision == "BUY" and debate_confidence >= 0.65:
        signals.append({"source": "debate", "direction": "LONG", "strength": debate_confidence})
    elif debate_decision == "SELL" and debate_confidence >= 0.65:
        signals.append({"source": "debate", "direction": "SHORT", "strength": debate_confidence})

    # 因子信号
    if long_score and long_score >= 0.55:
        signals.append({"source": "factor", "direction": "LONG", "strength": 0.5})
    if short_score and short_score >= 0.55:
        signals.append({"source": "factor", "direction": "SHORT", "strength": 0.5})

    # 汇总
    long_weight = sum(s["strength"] for s in signals if s["direction"] == "LONG")
    short_weight = sum(s["strength"] for s in signals if s["direction"] == "SHORT")

    if not risk_approved:
        decision = "HOLD"
        confidence = 0.2
        reason = "风控未通过"
    elif long_weight > short_weight + 0.3:
        decision = "BUY"
        confidence = min(long_weight / (long_weight + short_weight + 0.3), 0.9)
        reason = f"多头信号占优 (L:{long_weight:.1f} vs S:{short_weight:.1f})"
    elif short_weight > long_weight + 0.3:
        decision = "SELL"
        confidence = min(short_weight / (long_weight + short_weight + 0.3), 0.9)
        reason = f"空头信号占优 (S:{short_weight:.1f} vs L:{long_weight:.1f})"
    else:
        decision = "HOLD"
        confidence = 0.4
        reason = f"信号矛盾 ({long_weight:.1f}/{short_weight:.1f})"

    # 建议仓位
    pos_pct = trader.get("position_pct", 0)
    if decision == "BUY":
        suggested_margin_pct = pos_pct if pos_pct > 0 else 10 if confidence > 0.7 else 5
    elif decision == "SELL":
        suggested_margin_pct = pos_pct if pos_pct > 0 else 8
    else:
        suggested_margin_pct = 0

    return {
        "decision": decision,
        "confidence": round(confidence, 2),
        "reason": reason,
        "signals": signals,
        "suggested_margin_pct": suggested_margin_pct,
        "tech_score": tech_score,
        "tech_label": tech_label,
        "debate_decision": debate_decision,
        "debate_confidence": debate_confidence,
        "risk_approved": risk_approved,
    }


def format_report(report: dict) -> str:
    """生成 Markdown 报告"""
    meta = report["meta"]
    specs = report["contract_specs"]
    mkt = report["market_data"]
    factors = report["factor_scores"]
    tech = report.get("technical_analysis", {})
    debate = report["debate"]
    decision = report["decision"]

    indicators = tech.get("indicators", {})
    tech_score = tech.get("technical_score", {})
    tp = tech.get("trade_params", {})

    md = []
    md.append(f"# 期货深度分析: {meta['name']} ({meta['code']})")
    md.append(f"\n**日期**: {meta['date']} | **市场**: {meta['market']} | **类别**: {meta['category']}")
    md.append(f"\n---")

    # 一、合约概况
    md.append(f"\n## 一、合约概况\n")
    md.append(f"| 参数 | 值 |")
    md.append(f"|------|----|")
    md.append(f"| 合约乘数 | {specs['lot_size']} |")
    md.append(f"| 做多保证金 | {specs['long_margin']:,.0f} {specs['margin_currency']} |")
    md.append(f"| 做空保证金 | {specs['short_margin']:,.0f} {specs['margin_currency']} |")
    md.append(f"| 当前价格 | {mkt.get('close', 'N/A')} |")

    # 二、技术面分析
    md.append(f"\n## 二、技术面分析\n")
    md.append(f"**综合评分: {tech_score.get('score', 'N/A')}/10 ({tech_score.get('label', 'N/A')})**\n")
    if tech_score.get("reasons"):
        for r in tech_score["reasons"]:
            md.append(f"- {r}")

    trend = indicators.get("trend", {})
    if trend:
        md.append(f"\n### 趋势")
        md.append(f"- 5日/20日/60日: {trend.get('trend_5d','?')}/{trend.get('trend_20d','?')}/{trend.get('trend_60d','?')}")
        md.append(f"- 均线排列: {trend.get('alignment','?')}")
        md.append(f"- 距MA20: {trend.get('pct_above_ma20','?'):+}%")

    md.append(f"\n### 技术指标")
    macd_data = indicators.get("macd", {})
    md.append(f"- MACD: {macd_data.get('state','?')} DIF={macd_data.get('dif','?')} DEA={macd_data.get('dea','?')}")
    md.append(f"- RSI: {indicators.get('rsi','?')}")
    md.append(f"- ADX: {indicators.get('adx_14','?')}")
    md.append(f"- ATR: {indicators.get('atr_14','?')} ({indicators.get('atr_pct','?')}%)")
    md.append(f"- 布林带: {indicators.get('bollinger',{}).get('price_position','?')}")

    sr = indicators.get("support_resistance", {})
    if sr:
        md.append(f"\n### 关键位")
        md.append(f"- 支撑: {sr.get('supports',[])}")
        md.append(f"- 阻力: {sr.get('resistances',[])}")

    vol = indicators.get("volume", {})
    if vol:
        md.append(f"\n### 成交量")
        md.append(f"- 趋势: {vol.get('volume_trend','?')}")
        md.append(f"- 量比: {vol.get('vol_ratio_vs_20d','?')}x")
        if vol.get("is_spike"):
            md.append(f"- ⚠️ 异常放量")

    # 三、因子评分
    md.append(f"\n## 三、因子评分\n")
    md.append(f"| 因子 | 值 |")
    md.append(f"|------|----|")
    for k, v in mkt.items():
        if v is not None:
            md.append(f"| {k} | {v:.4f}" if isinstance(v, float) else f"| {k} | {v}")
    md.append(f"| **做多得分** | **{factors.get('long_score','?'):.4f}** |" if factors.get('long_score') else "")
    md.append(f"| **做空得分** | **{factors.get('short_score','?'):.4f}** |" if factors.get('short_score') else "")

    # 四、多空辩论
    md.append(f"\n## 四、多空辩论\n")
    bull_data = debate.get("bull", {})
    bear_data = debate.get("bear", {})
    trader_data = debate.get("trader", {})
    risk_data = debate.get("risk", {})

    md.append(f"### 🐂 多头: {bull_data.get('recommendation','?')} (置信度 {bull_data.get('confidence','?')})")
    for pt in bull_data.get("key_points", [])[:3]:
        md.append(f"- {pt}")

    md.append(f"\n### 🐻 空头/风险: {bear_data.get('recommendation','?')} (置信度 {bear_data.get('confidence','?')})")
    for pt in bear_data.get("key_points", [])[:3]:
        md.append(f"- {pt}")

    md.append(f"\n### 📊 交易员: {trader_data.get('decision','?')} (置信度 {trader_data.get('confidence','?')})")
    md.append(f"- 建议仓位: {trader_data.get('position_pct','?')}%")
    md.append(f"- 入场价: {trader_data.get('entry_price','?')}")
    md.append(f"- 止损: {trader_data.get('stop_loss','?')}")

    md.append(f"\n### 🛡️ 风控: {'✅ 通过' if risk_data.get('approved') else '❌ 未通过'} ({risk_data.get('risk_level','?')})")

    # 五、综合决策
    md.append(f"\n---\n## 五、综合决策\n")
    md.append(f"**最终建议: {decision['decision']}** (置信度: {decision['confidence']:.0%})\n")
    md.append(f"**理由**: {decision['reason']}\n")
    if decision.get("suggested_margin_pct", 0) > 0:
        md.append(f"**建议仓位**: 保证金占权益 {decision['suggested_margin_pct']:.0f}%\n")

    md.append(f"\n### 信号来源")
    for sig in decision.get("signals", []):
        icon = "📈" if sig["direction"] == "LONG" else "📉"
        md.append(f"- {icon} {sig['source']}: {sig['direction']} (强度 {sig['strength']:.1f})")

    if decision.get("risk_approved") == False:
        md.append(f"\n⚠️ **风控未通过，建议观望**")

    md.append(f"\n---\n*报告生成: {meta['generated_at']}*")
    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="期货深度分析报告")
    parser.add_argument("--code", type=str, required=True)
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = generate_report(args.code, args.date)
    if "error" in report.get("technical_analysis", {}):
        print(f"⚠️ 技术分析不可用: {report['technical_analysis']['error']}")

    # 保存
    out_dir = DIAGNOSE_DIR / args.date
    out_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = out_dir / f"deep_{args.code}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    # Markdown
    md = format_report(report)
    md_path = out_dir / f"deep_{args.code}.md"
    with open(md_path, "w") as f:
        f.write(md)

    if args.json:
        print(json.dumps(report["decision"], indent=2, ensure_ascii=False))
    else:
        print(md)
        print(f"\n---")
        print(f"📄 报告已保存:")
        print(f"   JSON: {json_path}")
        print(f"   MD:   {md_path}")


if __name__ == "__main__":
    main()
