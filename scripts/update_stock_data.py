#!/usr/bin/env python3
"""
全市场股票数据定期更新脚本 (优化版)

数据源优先级:
- A股/港股: Tushare Pro (主) → Akshare (降级)
- 美股: yfinance (主) → Akshare (降级)

保存到: ~/wuhoo-workspace/data/

用法:
  python3.11 scripts/update_stock_data.py [--market cn|hk|us|all] [--days N]
"""

import argparse
import datetime
import os
import sys
import time
import warnings
import json
import requests
from pathlib import Path

warnings.filterwarnings("ignore")

# 数据根目录
DATA_ROOT = Path(os.path.expanduser("~/wuhoo-workspace/data"))

# Tushare 配置
def get_tushare_token():
    """从 .env 文件直接获取 Tushare Token（避免环境变量被脱敏）"""
    env_paths = [
        os.path.expanduser("~/.hermes/.env"),
        os.path.expanduser("~/.openclaw/.env"),
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TUSHARE_TOKEN=") and not line.startswith("#"):
                        token = line.split("=", 1)[1]
                        # 验证 token 长度（正常应为 56 位）
                        if len(token) >= 40:
                            return token
    return os.environ.get("TUSHARE_TOKEN", "")

def tushare_request(api_name, params=None, token=None):
    """直接调用 Tushare HTTP API，避免 SDK 兼容问题"""
    if token is None:
        token = get_tushare_token()
    if not token:
        raise ValueError("TUSHARE_TOKEN 未配置")
    
    url = "https://api.waditu.com"
    payload = {
        "api_name": api_name,
        "token": token,
        "params": params or {}
    }
    
    r = requests.post(url, json=payload, timeout=30)
    resp = r.json()
    
    if resp.get("code") != 0:
        raise Exception(f"Tushare {api_name} 失败: {resp.get('msg', '未知错误')}")
    
    return resp["data"]

def akshare_with_retry(func, *args, max_retries=3, delay=2, **kwargs):
    """Akshare 调用带重试和限流控制"""
    import akshare as ak
    
    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            if result is not None and len(result) > 0:
                return result
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg or "timeout" in error_msg.lower() or "限流" in error_msg:
                wait_time = delay * (attempt + 1)
                print(f"  ⚠ Akshare 请求失败 (尝试 {attempt+1}/{max_retries}): {error_msg[:60]}")
                print(f"  ⏳ 等待 {wait_time}s 后重试...")
                time.sleep(wait_time)
            else:
                raise
    
    print(f"  ❌ Akshare {func.__name__} 重试 {max_retries} 次后失败")
    return None

def get_stock_list_cn():
    """获取 A 股股票列表 (Tushare 优先)"""
    try:
        data = tushare_request("stock_basic", {
            "exchange": "",
            "list_status": "L",
            "fields": "ts_code,symbol,name,area,industry,list_date"
        })
        
        import pandas as pd
        df = pd.DataFrame(data["items"], columns=data["fields"])
        df.to_csv(DATA_ROOT / "cn/stock_info.csv", index=False, encoding="utf-8-sig")
        print(f"✓ A股股票列表 (Tushare): {len(df)} 只")
        return df
    except Exception as e:
        print(f"⚠ Tushare 获取A股列表失败: {e}")
        print("  降级使用 Akshare...")
        
        try:
            import akshare as ak
            df = akshare_with_retry(ak.stock_zh_a_spot_em)
            if df is not None:
                df.to_csv(DATA_ROOT / "cn/stock_info.csv", index=False, encoding="utf-8-sig")
                print(f"✓ A股股票列表 (Akshare): {len(df)} 只")
                return df
        except Exception as e2:
            print(f"❌ Akshare 获取A股列表也失败: {e2}")
            return None

def get_stock_list_hk():
    """获取港股股票列表"""
    try:
        data = tushare_request("hk_basic", {
            "list_status": "L",
            "fields": "ts_code,symbol,name,list_date"
        })
        
        import pandas as pd
        df = pd.DataFrame(data["items"], columns=data["fields"])
        df.to_csv(DATA_ROOT / "hk/stock_info.csv", index=False, encoding="utf-8-sig")
        print(f"✓ 港股股票列表 (Tushare): {len(df)} 只")
        return df
    except Exception as e:
        print(f"⚠ Tushare 获取港股列表失败: {e}")
        try:
            import akshare as ak
            df = akshare_with_retry(ak.stock_hk_spot_em)
            if df is not None:
                cols = [c for c in ["代码","名称","最新价","涨跌幅","成交量","成交额","市值","市盈率"] if c in df.columns]
                df[cols].to_csv(DATA_ROOT / "hk/stock_info.csv", index=False, encoding="utf-8-sig")
                print(f"✓ 港股股票列表 (Akshare): {len(df)} 只")
                return df
        except Exception as e2:
            print(f"❌ Akshare 获取港股列表也失败: {e2}")
            return None

def update_a_daily_tushare(daily_dir, days=30):
    """使用 Tushare 更新 A 股日线数据"""
    import pandas as pd
    import numpy as np
    
    today = datetime.datetime.now()
    start_date = (today - datetime.timedelta(days=days)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    
    # 获取股票列表
    stock_list_path = DATA_ROOT / "cn/stock_info.csv"
    if not stock_list_path.exists():
        print("❌ 股票列表不存在，先获取列表")
        get_stock_list_cn()
    
    stock_list = pd.read_csv(stock_list_path, dtype={"ts_code": str, "symbol": str})
    
    # Tushare 支持批量查询，优先按市场批量获取
    try:
        # 先尝试获取全市场交易日历
        cal_data = tushare_request("trade_cal", {
            "exchange": "SSE",
            "start_date": start_date,
            "end_date": end_date
        })
        cal_df = pd.DataFrame(cal_data["items"], columns=cal_data["fields"])
        trade_dates = cal_df[cal_df["is_open"] == 1]["cal_date"].tolist()
        print(f"  📅 交易日历: {len(trade_dates)} 个交易日")
    except Exception as e:
        print(f"  ⚠ 获取交易日历失败: {e}")
        trade_dates = None
    
    # 分批获取日线数据 (Tushare 单次最多 5000 条)
    all_data = []
    success = 0
    failed = 0
    
    # 按板块分批查询，避免单次数据量过大
    for i in range(0, len(stock_list), 100):
        batch = stock_list.iloc[i:i+100]
        codes = batch["ts_code"].tolist()
        code_str = ",".join(codes)
        
        try:
            data = tushare_request("daily", {
                "ts_code": code_str,
                "start_date": start_date,
                "end_date": end_date
            })
            
            if data["items"]:
                df = pd.DataFrame(data["items"], columns=data["fields"])
                all_data.append(df)
                success += len(codes)
                
                # 限流控制
                time.sleep(0.2)
        except Exception as e:
            print(f"  ⚠ 批次 {i//100+1} 失败: {str(e)[:80]}")
            failed += len(codes)
            time.sleep(1)
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        
        # 计算技术指标
        print("  📊 计算技术指标...")
        results = []
        for code, group in combined.groupby("ts_code"):
            group = group.sort_values("trade_date")
            
            group["MA_5"] = group["close"].rolling(5).mean()
            group["MA_10"] = group["close"].rolling(10).mean()
            group["MA_20"] = group["close"].rolling(20).mean()
            group["MA_60"] = group["close"].rolling(60).mean()
            
            group["EMA_5"] = group["close"].ewm(span=5).mean()
            group["EMA_10"] = group["close"].ewm(span=10).mean()
            group["EMA_20"] = group["close"].ewm(span=20).mean()
            
            # MACD
            ema12 = group["close"].ewm(span=12).mean()
            ema26 = group["close"].ewm(span=26).mean()
            group["DIF"] = ema12 - ema26
            group["DEA"] = group["DIF"].ewm(span=9).mean()
            group["MACD"] = 2 * (group["DIF"] - group["DEA"])
            
            # RSI
            delta = group["close"].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            group["RSI"] = 100 - (100 / (1 + rs))
            
            # ATR
            high_low = group["high"] - group["low"]
            high_close = abs(group["high"] - group["close"].shift(1))
            low_close = abs(group["low"] - group["close"].shift(1))
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            group["ATR"] = tr.rolling(14).mean()
            
            results.append(group)
        
        final = pd.concat(results, ignore_index=True)
        
        week_key = today.strftime("%Y%m%d")
        output_file = daily_dir / f"A_stock_daily_{week_key}.csv"
        final.to_csv(output_file, index=False)
        
        print(f"✓ A股日线 (Tushare): {success} 只成功, {failed} 只失败, {len(final)} 条记录")
        return True
    
    return False

def update_a_daily_akshare_fallback(daily_dir, days=30):
    """Akshare 降级方案 - 更新重点股票"""
    import pandas as pd
    import numpy as np
    import akshare as ak
    
    print("  🔄 使用 Akshare 降级更新重点股票...")
    
    today = datetime.datetime.now()
    start_date = (today - datetime.timedelta(days=days)).strftime("%Y%m%d")
    
    # 读取股票列表
    stock_list_path = DATA_ROOT / "cn/stock_info.csv"
    if not stock_list_path.exists():
        return False
    
    stock_list = pd.read_csv(stock_list_path)
    if "代码" in stock_list.columns:
        codes = stock_list["代码"].tolist()[:50]  # 重点 50 只
    elif "symbol" in stock_list.columns:
        codes = stock_list["symbol"].tolist()[:50]
    else:
        return False
    
    all_data = []
    success = 0
    
    for i, code in enumerate(codes):
        try:
            hist = akshare_with_retry(ak.stock_zh_a_hist, symbol=code, period="daily", adjust="qfq")
            if hist is not None and len(hist) > 0:
                hist = hist.tail(300)
                hist["stock_code"] = code
                all_data.append(hist)
                success += 1
                
                if (i + 1) % 10 == 0:
                    print(f"  进度: {i+1}/{len(codes)}")
                    time.sleep(1)
        except Exception as e:
            print(f"  ⚠ {code} 失败: {str(e)[:50]}")
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        week_key = today.strftime("%Y%m%d")
        output_file = daily_dir / f"A_stock_daily_akshare_{week_key}.csv"
        combined.to_csv(output_file, index=False)
        print(f"✓ A股日线 (Akshare降级): {success} 只股票")
        return True
    
    return False

def update_hk_daily(days=30):
    """更新港股日线"""
    import pandas as pd
    
    today = datetime.datetime.now()
    start_date = (today - datetime.timedelta(days=days)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    dest = DATA_ROOT / "hk/daily"
    dest.mkdir(parents=True, exist_ok=True)
    
    try:
        data = tushare_request("hk_daily", {
            "start_date": start_date,
            "end_date": end_date
        })
        
        if data["items"]:
            df = pd.DataFrame(data["items"], columns=data["fields"])
            output_file = dest / f"HK_stock_daily_{today.strftime('%Y%m%d')}.csv"
            df.to_csv(output_file, index=False)
            print(f"✓ 港股日线 (Tushare): {len(df)} 条记录")
            return True
    except Exception as e:
        print(f"⚠ Tushare 港股日线失败: {e}")
    
    # Akshare 降级
    try:
        import akshare as ak
        stock_list_path = DATA_ROOT / "hk/stock_info.csv"
        if stock_list_path.exists():
            stock_list = pd.read_csv(stock_list_path, dtype={"代码": str})
            codes = stock_list["代码"].tolist()[:30]
            
            all_data = []
            for code in codes:
                try:
                    hist = akshare_with_retry(ak.stock_hk_hist, symbol=code, period="daily", adjust="qfq")
                    if hist is not None:
                        hist["ts_code"] = code
                        all_data.append(hist)
                except:
                    pass
            
            if all_data:
                combined = pd.concat(all_data, ignore_index=True)
                output_file = dest / f"HK_stock_daily_akshare_{today.strftime('%Y%m%d')}.csv"
                combined.to_csv(output_file, index=False)
                print(f"✓ 港股日线 (Akshare降级): {len(combined)} 条记录")
                return True
    except Exception as e:
        print(f"⚠ Akshare 港股也失败: {e}")
    
    return False

def update_us_daily(days=30):
    """更新美股日线"""
    import pandas as pd
    
    today = datetime.datetime.now()
    dest = DATA_ROOT / "us/daily"
    dest.mkdir(parents=True, exist_ok=True)
    
    # 尝试获取美股列表
    stock_list_path = DATA_ROOT / "us/stock_info.csv"
    symbols = []
    
    if stock_list_path.exists():
        stock_list = pd.read_csv(stock_list_path)
        if "symbol" in stock_list.columns:
            symbols = stock_list["symbol"].tolist()[:100]
    
    # 默认关注列表
    if not symbols:
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "V"]
        print(f"  ℹ️ 使用默认美股列表: {len(symbols)} 只")
    
    try:
        import yfinance as yf
        
        all_data = []
        success = 0
        
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period=f"{days}d")
                if not hist.empty:
                    hist["symbol"] = sym
                    all_data.append(hist)
                    success += 1
                    time.sleep(0.5)  # yfinance 限流
            except:
                pass
        
        if all_data:
            combined = pd.concat(all_data)
            output_file = dest / f"US_stock_daily_{today.strftime('%Y%m%d')}.csv"
            combined.to_csv(output_file)
            print(f"✓ 美股日线 (yfinance): {success} 只股票, {len(combined)} 条记录")
            return True
    except Exception as e:
        print(f"⚠ yfinance 美股失败: {e}")
    
    return False

def main():
    parser = argparse.ArgumentParser(description="全市场股票数据更新")
    parser.add_argument("--market", choices=["cn", "hk", "us", "all"], default="all")
    parser.add_argument("--days", type=int, default=30, help="更新天数")
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"📊 全市场数据更新 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 确保目录存在
    for d in ["cn/daily", "cn/hourly", "hk/daily", "us/daily", "us/factors"]:
        (DATA_ROOT / d).mkdir(parents=True, exist_ok=True)
    
    token = get_tushare_token()
    if token:
        print(f"🔑 Tushare Token: {token[:8]}...{token[-4:]} (长度: {len(token)})")
    else:
        print("⚠ Tushare Token 未配置，将仅使用 Akshare")
    
    results = {"cn": False, "hk": False, "us": False}
    
    if args.market in ["cn", "all"]:
        print("\n🇨🇳 更新A股...")
        get_stock_list_cn()
        
        # Tushare 优先
        if token:
            results["cn"] = update_a_daily_tushare(DATA_ROOT / "cn/daily", args.days)
        
        # 失败则降级 Akshare
        if not results["cn"]:
            results["cn"] = update_a_daily_akshare_fallback(DATA_ROOT / "cn/daily", args.days)
    
    if args.market in ["hk", "all"]:
        print("\n🇭🇰 更新港股...")
        get_stock_list_hk()
        results["hk"] = update_hk_daily(args.days)
    
    if args.market in ["us", "all"]:
        print("\n🇺🇸 更新美股...")
        results["us"] = update_us_daily(args.days)
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📋 更新总结:")
    for market, ok in results.items():
        status = "✅ 成功" if ok else "❌ 失败"
        market_name = {"cn": "A股", "hk": "港股", "us": "美股"}[market]
        print(f"  {market_name}: {status}")
    
    # 生成 JSON 报告供 Cron 推送
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "results": results,
        "data_root": str(DATA_ROOT)
    }
    
    report_path = DATA_ROOT / "update_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 报告已保存: {report_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
