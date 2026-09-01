#!/usr/bin/env python3
"""批量辩论 — 从选股 CSV 直接注入因子数据，跳过 DataAggregator"""
import argparse, csv, json, os, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))

from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent

DATA_DIR = Path.home() / "wuhoo-workspace" / "data" / "debate"
DEEPSEEK_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL = "deepseek-v4-pro"

def fetch_names(codes):
    """从 Futu 获取股票名称"""
    from futu import OpenQuoteContext
    names = {}
    try:
        q = OpenQuoteContext('127.0.0.1', 11111)
        ret, data = q.get_market_snapshot(codes)
        q.close()
        if ret == 0:
            for _, row in data.iterrows():
                names[row['code']] = row.get('name', row['code'])
    except Exception as e:
        print(f"⚠️ 名称获取失败: {e}")
    return names

def simple_consensus(bull_view, bear_view):
    """简易共识/分歧分析"""
    bp = [p for p in bull_view.get("points", []) if isinstance(p, dict)]
    bep = [p for p in bear_view.get("points", []) if isinstance(p, dict)]
    consensus = []
    disagreement = []
    
    bull_cats = {p.get("category","") for p in bp}
    bear_cats = {p.get("category","") for p in bep}
    
    for cat in bull_cats & bear_cats:
        disagreement.append(f"分歧[{cat}]: 多空观点对立")
    for cat in bull_cats - bear_cats:
        consensus.append(f"Bull独有[{cat}]: 空方未反驳")
    for cat in bear_cats - bull_cats:
        consensus.append(f"Bear警告[{cat}]: 多方未覆盖")
    
    return consensus or ["信号混合"], disagreement or ["多空分歧"]

def load_picks(csv_path):
    picks = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            picks.append(dict(row))
    return picks

def run_debate_for_stock(pick, idx, total, names):
    symbol = pick.get("ts_code", pick.get("code", ""))
    name = names.get(symbol, pick.get("name", "N/A"))
    
    print(f"[{idx}/{total}] {symbol} {name} — 开始辩论...")
    
    factor_data = {
        "symbol": symbol, "name": name,
        "residual_vol": float(pick.get("residual_vol", pick.get("volatility", 0))),
        "volatility": float(pick.get("volatility", pick.get("residual_vol", 0))),
        "turnover_5d": float(pick.get("turnover_5d", 0)),
        "momentum_5d": float(pick.get("momentum_5d", 0)),
        "momentum_10d": float(pick.get("momentum_10d", 0)),
        "beta_20d": float(pick.get("beta_20d", 0)),
    }
    
    tech = {"summary": f"5d动量:{factor_data['momentum_5d']:.1f}% 10d动量:{factor_data['momentum_10d']:.1f}% 波动率:{factor_data['volatility']:.1f}%"}
    fund = {"name": name}
    
    try:
        k = {"model": MODEL, "api_base": DEEPSEEK_BASE, "api_key": DEEPSEEK_KEY, "provider": "openai"}
        bull = BullAgent(**k)
        bear = BearAgent(**k)
        trader = TraderAgent(**k)
        
        # Phase 1: Bull
        t0 = time.time()
        bull_view = bull.analyze(symbol=symbol, factor_data=factor_data, technical_data=tech, sentiment_data={}, fundamental_data=fund)
        t1 = time.time()
        print(f"  [{idx}/{total}] Bull: {bull_view.get('recommendation','?')} ({bull_view.get('confidence',0):.2f}) — {t1-t0:.1f}s")
        
        # Phase 2: Bear
        bear_view = bear.analyze(symbol=symbol, factor_data=factor_data, technical_data=tech, sentiment_data={}, fundamental_data=fund, bull_view=bull_view)
        t2 = time.time()
        print(f"  [{idx}/{total}] Bear: {bear_view.get('recommendation','?')} ({bear_view.get('confidence',0):.2f}) — {t2-t1:.1f}s")
        
        # Phase 3: Bull Rebuttal
        bull_rebuttal = bull.analyze_with_context(symbol=symbol, data={"factor_data": factor_data, "technical_data": tech, "sentiment_data": {}, "fundamental_data": fund}, bear_view=bear_view)
        t3 = time.time()
        print(f"  [{idx}/{total}] Rebuttal: {bull_rebuttal.get('recommendation','?')} — {t3-t2:.1f}s")
        
        # Phase 4: Consensus + Trader
        consensus, disagreement = simple_consensus(bull_rebuttal, bear_view)
        trader_decision = trader.make_decision(symbol=symbol, bull_view=bull_rebuttal, bear_view=bear_view, consensus_points=consensus, disagreement_points=disagreement)
        t4 = time.time()
        dec = trader_decision.get('decision', trader_decision.get('recommendation', '?'))
        print(f"  [{idx}/{total}] Trader: {dec} ({trader_decision.get('confidence',0):.2f}) — {t4-t3:.1f}s → 总{t4-t0:.1f}s")
        
        return {"symbol": symbol, "name": name, "bull": bull_view, "bear": bear_view, "bull_rebuttal": bull_rebuttal, "trader": trader_decision, "elapsed_s": round(t4-t0, 1)}
    except Exception as e:
        import traceback
        print(f"  [{idx}/{total}] ❌ ERROR: {e}")
        traceback.print_exc()
        return {"symbol": symbol, "name": name, "error": str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--market", default="hk")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    
    csv_path = Path.home() / "wuhoo-workspace" / "data" / "stock-pick" / "factors" / f"result_{args.market}_{args.date}.csv"
    if not csv_path.exists():
        print(f"❌ 选股文件不存在: {csv_path}")
        sys.exit(1)
    
    picks = load_picks(csv_path)
    print(f"📊 加载 {len(picks)} 只股票")
    
    if not DEEPSEEK_KEY:
        print("❌ DEEPSEEK_API_KEY 未设置")
        sys.exit(1)
    
    # 获取股票名称
    codes = [p.get("ts_code", p.get("code", "")) for p in picks]
    names = fetch_names(codes)
    print(f"📛 获取到 {len(names)} 个名称")
    
    # 输出目录
    out_dir = DATA_DIR / args.date / "deepseek"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    failures = []
    t_start = time.time()
    
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(run_debate_for_stock, pick, i+1, len(picks), names): pick
            for i, pick in enumerate(picks)
        }
        for f in as_completed(futures):
            try:
                r = f.result()
                results.append(r)
                if "error" in r:
                    failures.append(r)
                sym = r.get("symbol", "unknown").replace(".", "_")
                jpath = out_dir / f"debate_{sym}.json"
                with open(jpath, "w") as jf:
                    json.dump(r, jf, ensure_ascii=False, indent=2, default=str)
            except Exception as e:
                print(f"❌ Future error: {e}")
    
    elapsed = time.time() - t_start
    
    # 汇总 - Trader 返回 'decision' 字段
    buys = [r for r in results if r.get("trader", {}).get("decision") in ("BUY", "买入")]
    holds = [r for r in results if r.get("trader", {}).get("decision") in ("HOLD", "持有")]
    sells = [r for r in results if r.get("trader", {}).get("decision") in ("SELL", "卖出")]
    
    summary = {
        "date": args.date,
        "market": args.market,
        "total": len(results),
        "success": len(results) - len(failures),
        "failures": len(failures),
        "buys": len(buys),
        "holds": len(holds),
        "sells": len(sells),
        "elapsed_s": round(elapsed, 1),
        "results": results
    }
    
    spath = out_dir / "debate_summary.json"
    with open(spath, "w") as sf:
        json.dump(summary, sf, ensure_ascii=False, indent=2, default=str)
    
    # 打印汇总
    print(f"\n{'='*60}")
    print(f"📊 辩论汇总 — {args.date} ({args.market})")
    print(f"{'='*60}")
    print(f"总数: {len(results)} | 成功: {len(results)-len(failures)} | 失败: {len(failures)}")
    print(f"BUY: {len(buys)} | HOLD: {len(holds)} | SELL: {len(sells)}")
    print(f"耗时: {elapsed:.1f}s ({elapsed/len(picks):.1f}s/只)")
    print(f"\n📁 输出: {out_dir}")
    for r in results:
        t = r.get("trader", {})
        sym = r["symbol"]
        nm = r.get("name", "?")
        act = t.get("decision", t.get("recommendation", "ERROR"))
        conf = t.get("confidence", 0)
        err = r.get("error", "")
        flag = "✅" if not err else "❌"
        print(f"  {flag} {sym} {nm}: {act} (conf={conf}) {err[:60] if err else ''}")

if __name__ == "__main__":
    main()
