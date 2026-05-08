#!/usr/bin/env python3
"""
fetch_futures_kline.py — 期货日线数据批量获取 v2.0
Phase 0.2: 拉取 Phase 1 目标品种历史日线

数据源:
  US 期货 — yfinance (ES=F, NQ=F, GC=F, SI=F, 无配额限制)
  HK 期货 — Futu subscribe + get_cur_kline (使用实时订阅额度，非历史额度)

用法:
  python3.11 fetch_futures_kline.py                     # 拉取全部 7 个品种
  python3.11 fetch_futures_kline.py --code US.MESmain    # 单个品种
  python3.11 fetch_futures_kline.py --force              # 强制刷新

存储: ~/wuhoo-workspace/data/futures/daily_kline/{US,HK}/{CODE}.csv
meta: ~/wuhoo-workspace/data/futures/contract_info.json
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime

import pandas as pd

DATA_DIR = Path.home() / "wuhoo-workspace" / "data" / "futures" / "daily_kline"

# Phase 1 目标品种 (7 个) — 含数据源配置
TARGET_CONTRACTS = [
    # US 股指 — yfinance 数据源
    {"code": "US.MESmain", "name": "微型标普500", "market": "US", "lot_size": 5, "source": "yfinance", "yf_ticker": "ES=F"},
    {"code": "US.MNQmain", "name": "微型纳斯达克100", "market": "US", "lot_size": 2, "source": "yfinance", "yf_ticker": "NQ=F"},
    # US 贵金属 — yfinance 数据源
    {"code": "US.MGCmain", "name": "微黄金", "market": "US", "lot_size": 10, "source": "yfinance", "yf_ticker": "GC=F"},
    {"code": "US.SImain", "name": "白银", "market": "US", "lot_size": 5000, "source": "yfinance", "yf_ticker": "SI=F"},
    # HK 股指 — Futu subscribe + get_cur_kline
    {"code": "HK.MHImain", "name": "小恒指", "market": "HK", "lot_size": 10, "source": "futu"},
    {"code": "HK.MCHmain", "name": "小国指", "market": "HK", "lot_size": 10, "source": "futu"},
    {"code": "HK.HTImain", "name": "恒生科技指数", "market": "HK", "lot_size": 50, "source": "futu"},
]


def fetch_yfinance(ticker: str, period: str = "2y") -> pd.DataFrame:
    """通过 yfinance 获取期货日线"""
    import yfinance as yf

    df = yf.download(ticker, period=period, progress=False)
    if df.empty:
        return pd.DataFrame()

    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

    date_col = [c for c in df.columns if "date" in c.lower()][0]
    df = df.rename(columns={date_col: "trade_date"})

    col_map = {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}
    keep = ["trade_date"] + [v for k, v in col_map.items() if k in df.columns]
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
    return df[keep]


def fetch_futu(quote_ctx, code: str, num: int = 500) -> pd.DataFrame:
    """通过 Futu subscribe + get_cur_kline 获取 HK 期货日线"""
    from futu import SubType, KLType, AuType, RET_OK

    # 订阅 K_DAY
    ret_sub, _ = quote_ctx.subscribe([code], [SubType.K_DAY], subscribe_push=False)
    if ret_sub != RET_OK:
        print(f"      ⚠️ 订阅失败，尝试直接获取...")

    time.sleep(0.5)

    ret, data = quote_ctx.get_cur_kline(code, num=num, ktype=KLType.K_DAY, autype=AuType.NONE)
    if ret != RET_OK or data.empty:
        raise RuntimeError(f"get_cur_kline 失败: {data}")

    df = data.copy()
    col_map = {
        "time_key": "trade_date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
    }
    df = df.rename(columns=col_map)
    keep = ["trade_date", "open", "high", "low", "close", "volume"]
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
    return df[keep]


def main():
    parser = argparse.ArgumentParser(description="期货日线数据批量获取 v2.0")
    parser.add_argument("--code", type=str, help="单个品种代码")
    parser.add_argument("--force", action="store_true", help="强制重新拉取")
    args = parser.parse_args()

    targets = [c for c in TARGET_CONTRACTS if not args.code or c["code"] == args.code]
    if args.code and not targets:
        print(f"❌ 未找到品种: {args.code}")
        sys.exit(1)

    print(f"📊 期货日线数据获取 v2.0")
    print(f"   目标品种: {len(targets)} 个")
    print(f"   存储路径: {DATA_DIR}")
    print()

    # Futu 连接 (仅 HK 品种需要)
    quote_ctx = None
    has_hk = any(c["source"] == "futu" for c in targets)
    if has_hk:
        from futu import OpenQuoteContext
        quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
        time.sleep(0.5)

    success = 0
    skip = 0
    fail = 0

    for i, c in enumerate(targets):
        code = c["code"]
        market = c["market"]
        name = c["name"]
        output = DATA_DIR / market / f"{code}.csv"

        if output.exists() and not args.force:
            existing = pd.read_csv(output)
            last = existing["trade_date"].iloc[-1] if "trade_date" in existing.columns else "?"
            print(f"   ⏭️ [{i+1}/{len(targets)}] {code} ({name}) — 已有 {len(existing)} 条, 最新 {last}")
            skip += 1
            continue

        print(f"   📥 [{i+1}/{len(targets)}] {code} ({name}, {c['source']}) ...", end=" ", flush=True)

        try:
            if c["source"] == "yfinance":
                df = fetch_yfinance(c["yf_ticker"], period="2y")
            else:
                df = fetch_futu(quote_ctx, code)

            if df.empty:
                print("⚠️ 无数据")
                fail += 1
                continue

            output.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output, index=False)
            dr = f"{df['trade_date'].iloc[0]} → {df['trade_date'].iloc[-1]}"
            print(f"✅ {len(df)} 条 ({dr})")
            success += 1

        except Exception as e:
            print(f"❌ {e}")
            fail += 1

        if i < len(targets) - 1:
            time.sleep(0.3)

    if quote_ctx:
        quote_ctx.close()

    print(f"\n{'='*50}")
    print(f"✅ 成功: {success} | ⏭️ 跳过: {skip} | ❌ 失败: {fail}")

    # 保存合约元数据
    meta_path = DATA_DIR.parent / "contract_info.json"
    meta = {c["code"]: {"name": c["name"], "market": c["market"], "lot_size": c["lot_size"], "source": c["source"]}
            for c in TARGET_CONTRACTS}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"   合约元数据: {meta_path}")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
