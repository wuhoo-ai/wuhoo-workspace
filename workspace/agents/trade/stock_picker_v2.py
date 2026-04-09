#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Picker V2 - 分批分块增量更新选股系统

功能:
1. 分批分块获取股票数据 (避免网络超时)
2. 增量更新 (只获取缺失/过期数据)
3. 数据充足性检查
4. 多因子筛选分析
5. 断点续传支持

用法:
    python stock_picker_v2.py --market cn --date 2026-03-31 --batch-size 50
"""

import os
import sys
import json
import time
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 配置
CONFIG = {
    "data_dir": "/home/admin/.openclaw/workspace/agents/trade/data/stock_cache",
    "output_dir": "/home/admin/.openclaw/workspace/agents/trade/data/workflow_c",
    "cache_days": 7,  # 缓存有效期 (天)
    "batch_size": 50,  # 每批处理股票数量
    "retry_times": 3,  # 重试次数
    "retry_delay": 2,  # 重试延迟 (秒)
    "request_delay": 0.5,  # 请求间隔 (秒)
    "min_history_days": 30,  # 最少历史数据天数
}

class StockDataCache:
    """股票数据缓存管理器"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get_cache_path(self, code: str) -> Path:
        """获取股票缓存文件路径"""
        return self.cache_dir / f"{code}.csv"
    
    def is_cache_valid(self, code: str, max_age_days: int = 7) -> bool:
        """检查缓存是否有效"""
        cache_path = self.get_cache_path(code)
        if not cache_path.exists():
            return False
        
        # 检查文件年龄
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age.days < max_age_days
    
    def load_cache(self, code: str) -> Optional[pd.DataFrame]:
        """加载缓存数据"""
        cache_path = self.get_cache_path(code)
        if not cache_path.exists():
            return None
        try:
            df = pd.read_csv(cache_path, parse_dates=['trade_date'])
            return df
        except Exception as e:
            print(f"  ⚠️ 加载缓存失败 {code}: {e}")
            return None
    
    def save_cache(self, code: str, df: pd.DataFrame):
        """保存缓存数据"""
        cache_path = self.get_cache_path(code)
        df.to_csv(cache_path, index=False)
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        files = list(self.cache_dir.glob("*.csv"))
        total_size = sum(f.stat().st_size for f in files)
        return {
            "stock_count": len(files),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "latest_update": max([f.stat().st_mtime for f in files]) if files else 0
        }


class DataFetcher:
    """数据获取器 (支持多数据源)"""
    
    def __init__(self):
        self.sources = []
        self._init_sources()
    
    def _init_sources(self):
        """初始化数据源"""
        # Tushare
        try:
            import tushare as ts
            token_file = Path.home() / '.openclaw' / '.env'
            token = None
            if token_file.exists():
                with open(token_file, 'r') as f:
                    for line in f:
                        if 'TUSHARE_TOKEN' in line:
                            token = line.split('=')[1].strip()
                            break
            
            if token:
                ts.set_token(token)
                self.pro = ts.pro_api()
                self.sources.append('tushare')
                print("✅ Tushare 数据源已初始化")
            else:
                print("⚠️ Tushare Token 未配置")
        except Exception as e:
            print(f"⚠️ Tushare 初始化失败：{e}")
        
        # Akshare
        try:
            import akshare as ak
            self.ak = ak
            self.sources.append('akshare')
            print("✅ Akshare 数据源已初始化")
        except Exception as e:
            print(f"⚠️ Akshare 初始化失败：{e}")
    
    def fetch_stock_data(self, code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取股票历史数据"""
        for source in self.sources:
            try:
                if source == 'tushare':
                    df = self._fetch_tushare(code, start_date, end_date)
                elif source == 'akshare':
                    df = self._fetch_akshare(code, start_date, end_date)
                
                if df is not None and len(df) > 0:
                    return df
            except Exception as e:
                print(f"  ⚠️ {source} 获取失败：{str(e)[:50]}")
                continue
        
        return None
    
    def _fetch_tushare(self, code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Tushare 获取数据"""
        # 转换代码格式
        if '.' not in code:
            if code.startswith('0') or code.startswith('3'):
                code = f"{code}.SZ"
            else:
                code = f"{code}.SH"
        
        ts_code = code
        start = start_date.replace('-', '')
        end = end_date.replace('-', '')
        
        df = self.pro.daily(ts_code=ts_code, start_date=start, end_date=end)
        if df is not None and len(df) > 0:
            df = df.sort_values('trade_date')
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            return df
        return None
    
    def _fetch_akshare(self, code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Akshare 获取数据"""
        df = self.ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', '')
        )
        if df is not None and len(df) > 0:
            df = df.rename(columns={
                '日期': 'trade_date',
                '收盘': 'close',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount'
            })
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            return df
        return None


class StockScreener:
    """股票筛选器"""
    
    def __init__(self):
        self.cache = StockDataCache(CONFIG["data_dir"])
        self.fetcher = DataFetcher()
    
    def get_stock_list(self, market: str = 'cn') -> List[str]:
        """获取股票列表"""
        if market == 'cn':
            # 中证 1000
            try:
                index_stocks = self.fetcher.ak.index_stock_cons_csindex(symbol="000852")
                if '成分券代码' in index_stocks.columns:
                    return index_stocks['成分券代码'].astype(str).tolist()
                elif 'code' in index_stocks.columns:
                    return index_stocks['code'].astype(str).tolist()
            except Exception as e:
                print(f"⚠️ 获取成分股失败：{e}")
            
            # 备用列表
            return [
                "000001", "000002", "000063", "000100", "000157",
                "000333", "000425", "000538", "000568", "000596",
                "000625", "000651", "000661", "000725", "000776",
                "000858", "000895", "000938", "000963", "000977"
            ]
        return []
    
    def calculate_factors(self, df: pd.DataFrame) -> Dict:
        """计算选股因子"""
        if len(df) < CONFIG["min_history_days"]:
            return None
        
        close = df['close'].values if 'close' in df.columns else df['收盘'].values
        volume = df['volume'].values if 'volume' in df.columns else df.get('成交量', pd.Series([1]*len(close))).values
        
        if len(close) < 20:
            return None
        
        # 1. 波动率因子 (20 日)
        volatility = np.std(close[-20:]) / np.mean(close[-20:]) * 100
        
        # 2. 动量因子
        momentum_5d = (close[-1] - close[-6]) / close[-6] * 100 if len(close) > 5 else 0
        momentum_10d = (close[-1] - close[-11]) / close[-11] * 100 if len(close) > 10 else 0
        momentum_20d = (close[-1] - close[-21]) / close[-21] * 100 if len(close) > 20 else 0
        
        # 3. 换手率因子
        avg_vol = np.mean(volume)
        turnover_5d = np.mean(volume[-5:]) / avg_vol if avg_vol > 0 else 1.0
        
        # 4. Beta 因子
        returns = np.diff(close) / close[:-1]
        beta = np.std(returns) * np.sqrt(252) * 100 if len(returns) > 0 else 0
        
        # 综合评分
        score = 0
        if volatility < 3: score += 3
        elif volatility < 5: score += 2
        elif volatility < 8: score += 1
        
        if momentum_5d > 0: score += 2
        if momentum_10d > 0: score += 2
        if momentum_20d > 0: score += 1
        
        if 0.5 < turnover_5d < 2.0: score += 2
        elif 0.3 < turnover_5d < 3.0: score += 1
        
        return {
            "volatility": round(float(volatility), 2),
            "momentum_5d": round(float(momentum_5d), 2),
            "momentum_10d": round(float(momentum_10d), 2),
            "momentum_20d": round(float(momentum_20d), 2),
            "turnover_ratio": round(float(turnover_5d), 2),
            "beta": round(float(beta), 2),
            "score": int(score),
            "latest_price": round(float(close[-1]), 2),
            "recommendation": "BUY" if score >= 7 else "HOLD" if score >= 4 else "SELL"
        }
    
    def process_batch(self, stock_list: List[str], target_date: str) -> Tuple[List[Dict], Dict]:
        """分批处理股票"""
        results = []
        stats = {"success": 0, "failed": 0, "cached": 0}
        
        end_date = datetime.strptime(target_date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=60)
        
        for i, code in enumerate(stock_list):
            # 检查缓存
            if self.cache.is_cache_valid(code, CONFIG["cache_days"]):
                cached_df = self.cache.load_cache(code)
                if cached_df is not None and len(cached_df) >= CONFIG["min_history_days"]:
                    factors = self.calculate_factors(cached_df)
                    if factors:
                        factors["ts_code"] = f"{code}.SZ" if code.startswith("0") else f"{code}.SH"
                        factors["name"] = code
                        results.append(factors)
                        stats["cached"] += 1
                        continue
            
            # 获取新数据
            for retry in range(CONFIG["retry_times"]):
                try:
                    df = self.fetcher.fetch_stock_data(
                        code,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d")
                    )
                    
                    if df is not None and len(df) >= CONFIG["min_history_days"]:
                        # 保存缓存
                        self.cache.save_cache(code, df)
                        
                        # 计算因子
                        factors = self.calculate_factors(df)
                        if factors:
                            factors["ts_code"] = f"{code}.SZ" if code.startswith("0") else f"{code}.SH"
                            factors["name"] = code
                            results.append(factors)
                            stats["success"] += 1
                        break
                    else:
                        stats["failed"] += 1
                        break
                        
                except Exception as e:
                    if retry < CONFIG["retry_times"] - 1:
                        time.sleep(CONFIG["retry_delay"] * (retry + 1))
                    else:
                        stats["failed"] += 1
                        print(f"  ⚠️ {code} 失败：{str(e)[:40]}")
            
            # 请求延迟
            if (i + 1) % 10 == 0:
                time.sleep(CONFIG["request_delay"] * 2)
            else:
                time.sleep(CONFIG["request_delay"])
            
            # 进度报告
            if (i + 1) % CONFIG["batch_size"] == 0:
                print(f"  进度：{i+1}/{len(stock_list)} (成功:{stats['success']}, 缓存:{stats['cached']}, 失败:{stats['failed']})")
        
        return results, stats
    
    def check_data_sufficiency(self, results: List[Dict]) -> Tuple[bool, str]:
        """检查数据充足性"""
        if len(results) < 10:
            return False, f"数据不足：仅 {len(results)} 只股票 (需要至少 10 只)"
        
        # 检查因子完整性
        valid_count = sum(1 for r in results if r.get('score') is not None)
        if valid_count < len(results) * 0.8:
            return False, f"因子数据不完整：{valid_count}/{len(results)}"
        
        return True, f"数据充足：{len(results)} 只股票，{valid_count} 只有效"
    
    def run(self, market: str = 'cn', target_date: str = None, batch_size: int = None):
        """执行选股流程"""
        batch_size = batch_size or CONFIG["batch_size"]
        target_date = target_date or datetime.now().strftime("%Y-%m-%d")
        
        print("=" * 70)
        print(f"Stock Picker V2 - {target_date} {market.upper()} 选股")
        print("=" * 70)
        
        # 步骤 1: 获取股票列表
        print(f"\n📋 步骤 1: 获取 {market.upper()} 股票列表...")
        stock_list = self.get_stock_list(market)
        print(f"✅ 股票池数量：{len(stock_list)}")
        
        # 步骤 2: 分批处理
        print(f"\n📈 步骤 2: 分批获取数据 (每批 {batch_size} 只)...")
        all_results = []
        total_stats = {"success": 0, "failed": 0, "cached": 0}
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(stock_list) + batch_size - 1) // batch_size
            
            print(f"\n  批次 {batch_num}/{total_batches}")
            print("  " + "-" * 50)
            
            results, stats = self.process_batch(batch, target_date)
            all_results.extend(results)
            
            for k in total_stats:
                total_stats[k] += stats[k]
            
            print(f"  批次完成：成功={stats['success']}, 缓存={stats['cached']}, 失败={stats['failed']}")
            
            # 批次间延迟
            if batch_num < total_batches:
                print(f"  休息 {CONFIG['request_delay']*5} 秒...")
                time.sleep(CONFIG["request_delay"] * 5)
        
        print(f"\n✅ 数据处理完成：成功={total_stats['success']}, 缓存={total_stats['cached']}, 失败={total_stats['failed']}")
        
        # 步骤 3: 数据充足性检查
        print(f"\n🔍 步骤 3: 数据充足性检查...")
        is_sufficient, message = self.check_data_sufficiency(all_results)
        if is_sufficient:
            print(f"✅ {message}")
        else:
            print(f"⚠️ {message}")
        
        # 步骤 4: 排序筛选
        print(f"\n📊 步骤 4: 排序筛选...")
        df_results = pd.DataFrame(all_results)
        df_sorted = df_results.sort_values(by='score', ascending=False)
        top_stocks = df_sorted.head(10).to_dict('records')
        
        print("\n🏆 TOP 10 选股结果:")
        print("-" * 95)
        print(f"{'排名':<4} {'代码':<14} {'名称':<10} {'价格':>8} {'波动率':>8} {'5 日动量':>10} {'10 日动量':>10} {'评分':>6} {'建议':>6}")
        print("-" * 95)
        for i, stock in enumerate(top_stocks, 1):
            print(f"{i:<4} {stock['ts_code']:<14} {stock['name']:<10} {stock['latest_price']:>8.2f} {stock['volatility']:>7.2f}% "
                  f"{stock['momentum_5d']:>9.2f}% {stock['momentum_10d']:>9.2f}% {stock['score']:>6} {stock['recommendation']:>6}")
        print("-" * 95)
        
        # 步骤 5: 保存结果
        print(f"\n💾 步骤 5: 保存结果...")
        output_dir = Path(CONFIG["output_dir"]) / f"CN_{target_date}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        result_data = {
            "task": "中证 1000 选股",
            "market": market.upper(),
            "date": target_date,
            "total_processed": len(all_results),
            "top_stocks": top_stocks,
            "all_results": df_sorted.to_dict('records'),
            "stats": total_stats,
            "data_sufficient": is_sufficient,
            "summary": {
                "buy_count": sum(1 for s in all_results if s.get('recommendation') == 'BUY'),
                "hold_count": sum(1 for s in all_results if s.get('recommendation') == 'HOLD'),
                "sell_count": sum(1 for s in all_results if s.get('recommendation') == 'SELL'),
                "avg_score": round(df_results['score'].mean(), 2) if len(df_results) > 0 else 0,
                "avg_volatility": round(df_results['volatility'].mean(), 2) if len(df_results) > 0 else 0,
                "avg_momentum_5d": round(df_results['momentum_5d'].mean(), 2) if len(df_results) > 0 else 0
            }
        }
        
        output_file = output_dir / "stock_pick_full.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 保存至：{output_file}")
        
        # 保存 CSV
        csv_file = output_dir / "stock_pick_full.csv"
        df_sorted.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"✅ CSV 保存至：{csv_file}")
        
        # 缓存统计
        cache_stats = self.cache.get_cache_stats()
        print(f"\n📦 缓存统计：{cache_stats['stock_count']} 只股票，{cache_stats['total_size_mb']}MB")
        
        print("\n" + "=" * 70)
        print("✅ 选股完成!")
        print("=" * 70)
        
        return result_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stock Picker V2")
    parser.add_argument("--market", type=str, default="cn", help="市场 (cn/hk/us)")
    parser.add_argument("--date", type=str, default=None, help="目标日期 (YYYY-MM-DD)")
    parser.add_argument("--batch-size", type=int, default=50, help="每批处理数量")
    
    args = parser.parse_args()
    
    screener = StockScreener()
    screener.run(
        market=args.market,
        target_date=args.date,
        batch_size=args.batch_size
    )
