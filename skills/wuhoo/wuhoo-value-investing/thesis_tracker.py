#!/usr/bin/env python3.11
"""
thesis_tracker.py — 投资论文追踪系统
基于 ai-berkshire thesis-tracker skill 改编

功能:
  1. 记录每笔买入的原始论文（为什么买？什么价位？什么条件下卖？）
  2. 每次复盘时检查论文是否仍然成立
  3. 论文破裂时发出卖出信号

用法:
  python3.11 thesis_tracker.py add --code AAPL --market us --thesis "护城河宽且估值合理..." --buy-price 150
  python3.11 thesis_tracker.py check --code AAPL
  python3.11 thesis_tracker.py list
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
WS = HOME / "wuhoo-workspace"
DATA_DIR = WS / "data" / "value-investing"
TRACKER_FILE = DATA_DIR / "thesis_tracker.jsonl"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Core Functions ──────────────────────────────────────

def load_all():
    """Load all thesis entries."""
    entries = []
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return entries


def save_entry(entry):
    """Append a thesis entry."""
    with open(TRACKER_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def add_thesis(code, market, name, thesis_text, buy_price, buy_date=None, 
               sell_conditions=None, position_pct=None):
    """Record a new investment thesis."""
    entry = {
        "code": code,
        "market": market,
        "name": name or code,
        "thesis": thesis_text,
        "buy_price": buy_price,
        "buy_date": buy_date or datetime.now().strftime('%Y-%m-%d'),
        "sell_conditions": sell_conditions or [
            "买入逻辑发生根本性变化",
            "发现更好的投资机会（机会成本）",
            "估值严重高估（安全边际消失）",
            "管理层出现诚信问题"
        ],
        "position_pct": position_pct,
        "checks": [],
        "status": "active",
        "created_at": datetime.now().isoformat()
    }
    save_entry(entry)
    return entry


def check_thesis(code, market=None, current_price=None):
    """Check if thesis still holds."""
    entries = load_all()
    
    target = None
    for e in entries:
        if e['code'] == code and (market is None or e['market'] == market):
            target = e
            break
    
    if not target:
        return {"error": f"No thesis found for {code}"}
    
    # Build check report
    check = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "current_price": current_price,
        "thesis": target['thesis'],
        "buy_price": target['buy_price'],
        "pnl_pct": round((current_price - target['buy_price']) / target['buy_price'] * 100, 1) if current_price and target['buy_price'] else None,
        "thesis_intact": None,  # Needs LLM/human judgment
        "warnings": [],
        "sell_signals": []
    }
    
    # Automated checks
    if target.get('sell_conditions'):
        check['sell_conditions'] = target['sell_conditions']
    
    # Price trigger checks
    if current_price and target.get('buy_price'):
        pnl = (current_price - target['buy_price']) / target['buy_price']
        if pnl < -0.20:
            check['sell_signals'].append(f"⚠️ 亏损超过20% ({pnl*100:.1f}%)，止损触发")
        if pnl > 1.0:
            check['warnings'].append(f"📈 盈利超过100% ({pnl*100:.1f}%)，考虑止盈")
    
    # Update entry
    target['checks'].append(check)
    target['last_check'] = check['date']
    
    # Save updated entries
    with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    
    return {
        "code": code,
        "name": target.get('name', code),
        "thesis": target['thesis'],
        "buy_price": target['buy_price'],
        "buy_date": target['buy_date'],
        "latest_check": check
    }


def list_theses(status=None):
    """List all thesis entries."""
    entries = load_all()
    
    if status:
        entries = [e for e in entries if e.get('status') == status]
    
    return [{
        "code": e['code'],
        "name": e.get('name', ''),
        "market": e.get('market', ''),
        "buy_price": e['buy_price'],
        "buy_date": e['buy_date'],
        "status": e.get('status', 'active'),
        "last_check": e.get('last_check', 'never'),
        "thesis_summary": e.get('thesis', '')[:80]
    } for e in entries]


def close_thesis(code, market=None, reason=""):
    """Mark a thesis as closed (sold)."""
    entries = load_all()
    
    for e in entries:
        if e['code'] == code and (market is None or e['market'] == market):
            e['status'] = 'closed'
            e['closed_at'] = datetime.now().isoformat()
            e['close_reason'] = reason
            break
    
    with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    
    return {"status": "closed", "code": code, "reason": reason}


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='投资论文追踪系统')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # add
    p_add = subparsers.add_parser('add', help='记录买入论文')
    p_add.add_argument('--code', required=True, help='股票代码')
    p_add.add_argument('--market', required=True, choices=['cn', 'hk', 'us'], help='市场')
    p_add.add_argument('--name', help='股票名称')
    p_add.add_argument('--thesis', required=True, help='买入论文（为什么买？）')
    p_add.add_argument('--buy-price', type=float, required=True, help='买入价格')
    p_add.add_argument('--buy-date', help='买入日期')
    p_add.add_argument('--position-pct', type=float, help='仓位占比')
    
    # check
    p_check = subparsers.add_parser('check', help='检查论文是否成立')
    p_check.add_argument('--code', required=True, help='股票代码')
    p_check.add_argument('--market', help='市场')
    p_check.add_argument('--current-price', type=float, help='当前价格')
    
    # list
    p_list = subparsers.add_parser('list', help='列出所有论文')
    p_list.add_argument('--status', choices=['active', 'closed'], help='过滤状态')
    
    # close
    p_close = subparsers.add_parser('close', help='关闭论文（卖出）')
    p_close.add_argument('--code', required=True, help='股票代码')
    p_close.add_argument('--market', help='市场')
    p_close.add_argument('--reason', help='卖出原因')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        entry = add_thesis(args.code, args.market, args.name, 
                          args.thesis, args.buy_price, args.buy_date, 
                          position_pct=args.position_pct)
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    
    elif args.command == 'check':
        result = check_thesis(args.code, args.market, args.current_price)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == 'list':
        theses = list_theses(args.status)
        if theses:
            print(f"{'代码':<12} {'名称':<10} {'买入价':<8} {'状态':<8} {'最后检查'}")
            print("-" * 60)
            for t in theses:
                print(f"{t['code']:<12} {t['name']:<10} {t['buy_price']:<8} {t['status']:<8} {t['last_check']}")
            print(f"\n共 {len(theses)} 条论文")
        else:
            print("暂无投资论文记录")
    
    elif args.command == 'close':
        result = close_thesis(args.code, args.market, args.reason or '')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
