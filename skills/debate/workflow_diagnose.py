#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debate Agent — 独立持仓诊断入口

由 debate agent 触发，独立于 trade agent 执行持仓诊断。
流程：
1. 读取 trade agent 产出的 trade_results.json
2. 调用 wuhoo-trade-diagnose/diagnose.py 进行诊断
3. 输出独立审计报告到 ~/.hermes/data/workflow_d/

用法:
    python workflow_diagnose.py                    # 全市场诊断
    python workflow_diagnose.py --market HK         # 仅港股
    python workflow_diagnose.py --skip-re-eval      # 跳过 Workflow B 重评估
    python workflow_diagnose.py --top-n 5           # 仅前 5 只持仓
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# ============================================================
# 环境变量加载
# ============================================================
env_file = Path.home() / '.hermes' / '.env'
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

# ============================================================
# 路径设置
# ============================================================
DEBATE_DIR = Path(__file__).parent
TRADE_DIR = Path.home() / '.hermes' / 'workspace' / 'agents' / 'trade'
SKILL_DIR = Path.home() / '.hermes' / 'skills' / 'wuhoo-trade-diagnose'
DIAGNOSE_SCRIPT = SKILL_DIR / 'diagnose.py'

# 输出目录（独立于 trade agent）
OUTPUT_DIR = Path.home() / '.hermes' / 'data' / 'workflow_d'


def check_trade_results(trade_date: str = None) -> dict:
    """检查 trade agent 是否已完成当日交易，返回 trade_results.json"""
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")

    # 查找最近的交易结果
    trade_data_dir = TRADE_DIR / "data" / "workflow_c"
    if not trade_data_dir.exists():
        return {"found": False, "message": "trade agent 无交易数据目录"}

    # 搜索最近的结果
    for market in ["HK", "CN", "US"]:
        trade_dir = trade_data_dir / f"{market}_{trade_date}"
        results_file = trade_dir / "05_trade_results.json"
        if results_file.exists():
            with open(results_file, 'r') as f:
                data = json.load(f)
            return {
                "found": True,
                "market": market,
                "date": trade_date,
                "file": str(results_file),
                "data": data,
            }

    return {"found": False, "message": f"未找到 {trade_date} 的交易结果"}


def run_diagnose(
    market: str = "all",
    account_id: int = None,
    date: str = None,
    skip_re_eval: bool = False,
    top_n: int = None,
    json_only: bool = False,
) -> dict:
    """调用诊断 skill 执行诊断"""
    cmd = [sys.executable, str(DIAGNOSE_SCRIPT)]

    if market != "all":
        cmd.extend(["--market", market])
    if account_id:
        cmd.extend(["--account-id", str(account_id)])
    if date:
        cmd.extend(["--date", date])
    if skip_re_eval:
        cmd.append("--skip-re-eval")
    if top_n:
        cmd.extend(["--top-n", str(top_n)])
    if json_only:
        cmd.append("--json")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
    )

    output = {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

    # 保存独立审计报告
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = OUTPUT_DIR / f"debate_diagnose_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"独立审计报告已保存：{report_file}")
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Debate Agent — 独立持仓诊断",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全市场诊断
  python workflow_diagnose.py

  # 仅港股，跳过深度分析
  python workflow_diagnose.py --market HK --skip-re-eval

  # 指定日期，仅前 5 只持仓
  python workflow_diagnose.py --date 2026-04-15 --top-n 5

  # 先检查 trade 结果，再诊断
  python workflow_diagnose.py --check-trade-first
        """,
    )
    parser.add_argument(
        "--market", type=str, default="all",
        choices=["CN", "HK", "US", "all"],
        help="市场 (默认: all)",
    )
    parser.add_argument(
        "--account-id", type=int, default=None,
        help="富途账户 ID",
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="诊断日期 (YYYY-MM-DD, 默认: 今天)",
    )
    parser.add_argument(
        "--skip-re-eval", action="store_true",
        help="跳过 Workflow B 重评估",
    )
    parser.add_argument(
        "--top-n", type=int, default=None,
        help="最多诊断持仓数",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_only",
        help="仅输出 JSON",
    )
    parser.add_argument(
        "--check-trade-first", action="store_true",
        help="先检查 trade agent 是否已完成当日交易",
    )

    args = parser.parse_args()

    if args.check_trade_first:
        print("检查 trade agent 交易结果...")
        trade_result = check_trade_results(args.date)
        if trade_result["found"]:
            print(f"  找到交易结果：{trade_result['market']} / {trade_result['date']}")
            print(f"  文件：{trade_result['file']}")
        else:
            print(f"  警告：{trade_result['message']}")
            print("  继续执行诊断（可能无交易输入）")

    if not DIAGNOSE_SCRIPT.exists():
        print(f"错误：诊断脚本不存在：{DIAGNOSE_SCRIPT}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("Debate Agent — 独立持仓诊断")
    print(f"{'='*60}")
    print(f"市场：{args.market}")
    print(f"诊断日期：{args.date or '今天'}")
    print(f"跳过重评估：{args.skip_re_eval}")
    print(f"Top-N：{args.top_n or '全部'}")

    output = run_diagnose(
        market=args.market,
        account_id=args.account_id,
        date=args.date,
        skip_re_eval=args.skip_re_eval,
        top_n=args.top_n,
        json_only=args.json_only,
    )

    if args.json_only:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n诊断完成，返回码：{output['returncode']}")


if __name__ == "__main__":
    main()
