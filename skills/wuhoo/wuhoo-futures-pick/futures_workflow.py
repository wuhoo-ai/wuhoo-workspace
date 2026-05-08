#!/usr/bin/env python3
"""
futures_workflow.py — 期货全链路一键执行
选品 → 技术面 → 辩论 → 深度报告 → 调仓计划

用法:
  python3.11 futures_workflow.py                          # 全链路
  python3.11 futures_workflow.py --skip-debate             # 跳过辩论(快速模式)
  python3.11 futures_workflow.py --skip-trade              # 只分析不调仓
  python3.11 futures_workflow.py --date 2026-05-08
"""

import sys, os, json, time, subprocess, argparse
from pathlib import Path
from datetime import datetime

WORKSPACE = Path.home() / "wuhoo-workspace"
SKILLS_DIR = WORKSPACE / "skills" / "wuhoo"
PICK_DIR = SKILLS_DIR / "wuhoo-futures-pick"
TRADE_DIR = SKILLS_DIR / "wuhoo-futures-trade"

# Python venv (统一使用 hermes-agent venv)
VENV = "/home/admin/.hermes/hermes-agent/venv/bin/python3"

DATA_DIR = WORKSPACE / "data" / "futures"
FACTORS_DIR = DATA_DIR / "factors"
DEBATE_DIR = DATA_DIR / "debate"
DIAGNOSE_DIR = DATA_DIR / "diagnose"

STEPS = [
    "fetch_data",
    "factors",
    "pick",
    "technical",
    "debate",
    "report",
    "trade_plan",
]

def run(cmd: list, desc: str, timeout: int = 300) -> bool:
    """运行命令，打印进度"""
    print(f"\n{'='*60}")
    print(f"▶ {desc}")
    print(f"{'='*60}")
    print(f"   $ {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(PICK_DIR))
        out = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
        if out:
            for line in out.splitlines()[-30:]:
                print(f"   {line}")
        if result.returncode != 0:
            err = result.stderr[-500:]
            if err:
                print(f"   ⚠️ stderr: {err}")
            # 非致命错误继续
            if "行情权限" in result.stderr or "权限不足" in result.stdout:
                print(f"   ⚠️ 非致命: 数据权限不足")
                return True
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"   ⏱️ 超时 ({timeout}s)")
        return False


def update_data(date_str: str) -> bool:
    """双源更新日线"""
    ok = True

    # US: yfinance via hermes venv
    us_script = """
import yfinance as yf, pandas as pd
from pathlib import Path
DATA = Path.home() / 'wuhoo-workspace/data/futures/daily_kline/US'
for code, ticker, name in [('US.MESmain','ES=F','MES'),('US.MNQmain','NQ=F','MNQ'),('US.MGCmain','GC=F','MGC'),('US.SImain','SI=F','SI')]:
    df = yf.download(ticker, period='5d', progress=False)
    if not df.empty:
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0].lower() for c in df.columns]
        else: df.columns = [c.lower() for c in df.columns]
        dc = [c for c in df.columns if 'date' in c.lower()][0]
        df = df.rename(columns={dc:'trade_date','open':'open','high':'high','low':'low','close':'close','volume':'volume'})
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
        keep = ['trade_date','open','high','low','close','volume']
        existing = pd.read_csv(DATA/f'{code}.csv')
        merged = pd.concat([existing, df[keep]]).drop_duplicates('trade_date').sort_values('trade_date')
        merged.to_csv(DATA/f'{code}.csv', index=False)
        print(f'{code}: {len(merged)} rows, latest {merged[\"trade_date\"].iloc[-1]}')
print('US data updated')
"""
    cmd = [VENV, "-c", us_script]
    if not run(cmd, "US 期货数据更新 (yfinance)", timeout=120):
        ok = False

    # HK: Futu via AI-Trader venv
    cmd = [VENV, str(PICK_DIR / "fetch_futures_kline.py"), "--days", "252"]
    if not run(cmd, "HK 期货数据更新 (Futu)", timeout=120):
        ok = False

    return ok


def main():
    parser = argparse.ArgumentParser(description="期货全链路工作流")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--skip-fetch", action="store_true", help="跳过数据更新")
    parser.add_argument("--skip-debate", action="store_true", help="跳过辩论 (快速模式)")
    parser.add_argument("--skip-trade", action="store_true", help="跳过调仓计划")
    parser.add_argument("--execute", action="store_true", help="实际下单 (默认 dry-run)")
    args = parser.parse_args()

    date_str = args.date
    print(f"🚀 期货全链路工作流 — {date_str}")
    print(f"   {'⚠️ 实盘模式' if args.execute else '📋 模拟模式 (dry-run)'}")
    print(f"   跳过: {'数据更新' if args.skip_fetch else ''} "
          f"{'辩论' if args.skip_debate else ''} "
          f"{'交易' if args.skip_trade else ''}")

    start_time = time.time()
    failures = []

    # Step 1: 数据更新
    if not args.skip_fetch:
        if not update_data(date_str):
            failures.append("数据更新")

    # Step 2: 因子计算
    if not run([VENV, str(PICK_DIR / "futures_factors.py")], "因子计算", timeout=60):
        failures.append("因子计算")

    # Step 3: 选品
    pick_path = FACTORS_DIR / f"pick_result_{date_str}.csv"
    if not run([VENV, str(PICK_DIR / "futures_pick.py"), "--top-n", "3", "--direction", "both"],
               "品种选择", timeout=60):
        failures.append("选品")

    if not pick_path.exists():
        print(f"\n❌ 选品结果未生成，终止")
        return 1

    # 读取选品
    import pandas as pd
    picks = pd.read_csv(pick_path)
    codes = picks["code"].unique().tolist()
    print(f"\n   📋 选品: {len(codes)} 个 ({', '.join(codes)})")

    # Step 4: 技术面分析
    for code in codes:
        out_dir = DEBATE_DIR / date_str
        out_dir.mkdir(parents=True, exist_ok=True)
        tech_path = out_dir / f"tech_{code}.json"
        cmd = [VENV, str(PICK_DIR / "futures_technical.py"), "--code", code, "--json"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            # Extract JSON from output
            for line in result.stdout.splitlines():
                if line.strip().startswith("{"):
                    with open(tech_path, "w") as f:
                        f.write(line.strip())
                    print(f"   📊 {code}: 技术分析已保存")
                    break
        except Exception as e:
            print(f"   ⚠️ {code} 技术分析失败: {e}")

    # Step 5: 辩论 (可选)
    if not args.skip_debate:
        for code in codes:
            debate_path = DEBATE_DIR / date_str / f"debate_{code}.json"
            if debate_path.exists():
                print(f"   ⏭️ {code}: 辩论已存在")
                continue
            if not run([VENV, str(PICK_DIR / "futures_debate.py"),
                        "--date", date_str, "--code", code],
                       f"辩论: {code}", timeout=300):
                failures.append(f"辩论-{code}")
    else:
        print(f"\n   ⏭️ 辩论已跳过")

    # Step 6: 深度报告
    for code in codes:
        if not run([VENV, str(PICK_DIR / "futures_deep_analysis.py"),
                    "--code", code, "--date", date_str],
                   f"深度报告: {code}", timeout=60):
            failures.append(f"报告-{code}")

    # Step 7: 调仓计划
    if not args.skip_trade:
        cmd = [VENV, str(TRADE_DIR / "futures_trade.py"), "rebalance", "--date", date_str]
        if args.execute:
            cmd.append("--execute")
        if not run(cmd, "调仓计划", timeout=60):
            failures.append("调仓")

    elapsed = time.time() - start_time

    # 汇总
    print(f"\n{'='*60}")
    print(f"🏁 全链路完成 ({elapsed:.0f}s)")
    if failures:
        print(f"   ⚠️ 失败步骤: {', '.join(failures)}")
    else:
        print(f"   ✅ 全部成功")

    # 展示最终决策
    if picks is not None and not picks.empty:
        print(f"\n📊 最终决策:")
        for code in codes:
            report_path = DIAGNOSE_DIR / date_str / f"deep_{code}.json"
            if report_path.exists():
                with open(report_path) as f:
                    r = json.load(f)
                d = r.get("decision", {})
                print(f"   {d['decision']:5s} {code:<16s} "
                      f"置信度={d['confidence']:.0%}  "
                      f"技术={d.get('tech_score','?')}  "
                      f"辩论={d.get('debate_decision','?')}({d.get('debate_confidence','?')})  "
                      f"仓位={d.get('suggested_margin_pct','?')}%")

    print(f"\n📁 输出目录:")
    print(f"   因子/选品: {FACTORS_DIR}")
    print(f"   辩论:      {DEBATE_DIR / date_str}")
    print(f"   报告:      {DIAGNOSE_DIR / date_str}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
