#!/usr/bin/env python3
"""
futures_debate.py — 期货多空辩论批量执行
Phase 3: 使用期货专用 prompts 对选品结果逐品种辩论

依赖: DeepSeek API (DEEPSEEK_API_KEY 环境变量)
用法:
  python3.11 futures_debate.py --date 2026-05-08
  python3.11 futures_debate.py --date 2026-05-08 --code US.MNQmain
"""

import sys, os, json, time, argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

DATA_DIR = Path.home() / "wuhoo-workspace" / "data" / "futures"
FACTORS_DIR = DATA_DIR / "factors"
DEBATE_DIR = DATA_DIR / "debate"
PROMPTS_DIR = Path(__file__).parent / "prompts"

# DeepSeek API config
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com/v1"
MODEL = "deepseek-v4-pro"
MAX_TOKENS = 8000
MAX_RETRIES = 3

if not DEEPSEEK_API_KEY:
    # Try loading from .env
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                DEEPSEEK_API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if not DEEPSEEK_API_KEY:
    print("❌ DEEPSEEK_API_KEY 未设置")
    sys.exit(1)

# ============================================================
# LLM 调用
# ============================================================

def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}_futures.md"
    if path.exists():
        return path.read_text()
    print(f"⚠️ Prompt 未找到: {path}")
    return ""

def call_llm(system_prompt: str, user_prompt: str) -> dict:
    """调用 DeepSeek API，带 3 次重试和 JSON 修复"""
    import urllib.request, urllib.error

    url = f"{DEEPSEEK_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    for attempt in range(MAX_RETRIES):
        token_budget = MAX_TOKENS + attempt * 2000
        payload = json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": token_budget,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read())
                content = result["choices"][0]["message"]["content"]

            # Try parse JSON
            # Strip markdown fences
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
                if content.endswith("```"):
                    content = content[:-3]

            parsed = json.loads(content)
            return parsed

        except (json.JSONDecodeError, KeyError) as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
                continue
            return {"error": f"JSON parse failed after {MAX_RETRIES} retries: {str(e)[:100]}",
                    "raw": content[:500]}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()[:300]
            if attempt < MAX_RETRIES - 1:
                time.sleep(3)
                continue
            return {"error": f"HTTP {e.code}: {err_body}"}

    return {"error": "max retries exceeded"}


# ============================================================
# 辩论流程
# ============================================================

def run_debate(code: str, name: str, technical: dict, factors: dict) -> dict:
    """对单个品种执行完整辩论"""
    prompt_bull = load_prompt("bull")
    prompt_bear = load_prompt("bear")
    prompt_trader = load_prompt("trader")
    prompt_risk = load_prompt("risk")

    data_context = json.dumps({
        "code": code,
        "name": name,
        "technical": technical,
        "factors": factors,
    }, ensure_ascii=False, indent=2, default=str)

    result = {"code": code, "name": name}

    # Step 1: Bull
    print(f"   🐂 Bull ...", end=" ", flush=True)
    bull_view = call_llm(prompt_bull, data_context)
    result["bull"] = bull_view
    print(f"{bull_view.get('recommendation','?')} c={bull_view.get('confidence','?')}")

    # Step 2: Bear (with bull context)
    print(f"   🐻 Bear ...", end=" ", flush=True)
    bear_context = data_context + "\n\n## 多头观点\n" + json.dumps(bull_view, ensure_ascii=False)
    bear_view = call_llm(prompt_bear, bear_context)
    result["bear"] = bear_view
    print(f"{bear_view.get('recommendation','?')} c={bear_view.get('confidence','?')}")

    # Step 3: Trader
    print(f"   📊 Trader ...", end=" ", flush=True)
    trader_context = json.dumps({
        "bull_view": bull_view,
        "bear_view": bear_view,
        "technical": {k: technical.get(k) for k in ["close","atr_14","support_resistance","adx_14"] if k in technical},
    }, ensure_ascii=False, indent=2, default=str)
    trader_decision = call_llm(prompt_trader, trader_context)
    result["trader"] = trader_decision
    print(f"{trader_decision.get('decision','?')} c={trader_decision.get('confidence','?')}")

    # Step 4: Risk
    print(f"   🛡️ Risk ...", end=" ", flush=True)
    risk_context = json.dumps({
        "trader_decision": trader_decision,
        "bull_view": bull_view,
        "bear_view": bear_view,
        "technical": technical,
    }, ensure_ascii=False, indent=2, default=str)
    risk_check = call_llm(prompt_risk, risk_context)
    result["risk"] = risk_check
    print(f"{'✅' if risk_check.get('approved') else '❌'} {risk_check.get('risk_level','?')}")

    # Final synthesis
    if risk_check.get("approved"):
        result["final_decision"] = trader_decision.get("decision", "HOLD")
        result["final_confidence"] = trader_decision.get("confidence", 0.5)
    else:
        result["final_decision"] = "HOLD"
        result["final_confidence"] = 0.3
        result["blocked"] = risk_check.get("block_reasons", [])

    return result


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--code", type=str, help="单品种辩论")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    # 加载选品结果
    pick_path = FACTORS_DIR / f"pick_result_{args.date}.csv"
    if not pick_path.exists():
        print(f"❌ 选品结果不存在: {pick_path}")
        sys.exit(1)
    picks = pd.read_csv(pick_path)
    if args.code:
        picks = picks[picks["code"] == args.code]
    if picks.empty:
        print("⚠️ 无候选品种")
        return

    # 加载因子数据
    factors_df = pd.read_csv(FACTORS_DIR / f"factors_{args.date}.csv")

    # 准备数据
    tasks = []
    for _, row in picks.iterrows():
        code = row["code"]
        # 加载技术分析 (如果文件存在)
        tech_path = DEBATE_DIR / args.date / f"tech_{code}.json"
        technical = {}
        if tech_path.exists():
            with open(tech_path) as f:
                technical = json.load(f)

        # 因子数据
        frow = factors_df[factors_df["code"] == code]
        factors = {}
        if not frow.empty:
            for col in frow.columns:
                v = frow[col].iloc[0]
                if not pd.isna(v):
                    factors[col] = v if isinstance(v, (int, float, str, bool)) else float(v)

        tasks.append((code, row["name"], technical, factors))

    print(f"📊 期货多空辩论 — {args.date}")
    print(f"   品种: {len(tasks)}  |  workers: {args.workers}  |  model: {MODEL}")
    print(f"   每品种 4 次 LLM 调用 (Bull→Bear→Trader→Risk)")
    print()

    # 执行
    results = []
    start = time.time()

    if len(tasks) == 1:
        # 单品种直接执行
        code, name, tech, fac = tasks[0]
        r = run_debate(code, name, tech, fac)
        results.append(r)
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_debate, c, n, t, f): c for c, n, t, f in tasks}
            for future in as_completed(futures):
                results.append(future.result())

    elapsed = time.time() - start

    # 汇总
    print(f"\n{'='*60}")
    print(f"📋 辩论汇总 ({len(results)} 品种, {elapsed:.0f}s)")

    summary = []
    for r in results:
        bull = r.get("bull", {})
        bear = r.get("bear", {})
        trader = r.get("trader", {})
        risk = r.get("risk", {})

        line = {
            "code": r["code"],
            "name": r["name"],
            "bull": f"{bull.get('recommendation','?')}({bull.get('confidence',0):.2f})",
            "bear": f"{bear.get('recommendation','?')}({bear.get('confidence',0):.2f})",
            "trader": f"{trader.get('decision','?')}({trader.get('confidence',0):.2f})",
            "risk": f"{'✅' if risk.get('approved') else '❌'} {risk.get('risk_level','?')}",
            "final": r.get("final_decision", "HOLD"),
        }
        summary.append(line)
        print(f"   {r['code']:<16s}  Bull={line['bull']:<15s} Bear={line['bear']:<15s} "
              f"Trader={line['trader']:<15s} Risk={line['risk']:<10s} → {line['final']}")

    # 保存
    out_dir = DEBATE_DIR / args.date
    out_dir.mkdir(parents=True, exist_ok=True)
    for r in results:
        path = out_dir / f"debate_{r['code']}.json"
        with open(path, "w") as f:
            json.dump(r, f, ensure_ascii=False, indent=2, default=str)

    # 汇总
    summary_path = out_dir / "debate_summary.json"
    with open(summary_path, "w") as f:
        json.dump({"date": args.date, "elapsed": round(elapsed, 0),
                    "results": results, "summary": summary}, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ 辩论结果已保存: {out_dir}/")
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
