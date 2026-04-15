#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fundamental Adapter - 基本面数据适配器

数据优先级策略:
1. Tushare Pro API (最可靠，需要 token) — 仅 A 股
2. Futu OpenAPI (US/HK/A 股通用)
3. AkShare (免费，仅 A 股)
4. Qlib 本地数据 (如果有)
5. 降级数据 (明确标注，不可用于交易决策)

更新：2026-03-23 - 重写为真实数据优先，明确标注降级
更新：2026-04-14 - 修复 Futu 连接生命周期（懒连接）+ 改进 US/HK 降级数据 + 删除 Qlib 引用
"""

import json
import os
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class FundamentalAdapter:
    """
    基本面数据适配器

    数据源优先级:
    P0: Tushare Pro API (需要 token, 仅 A 股)
    P1: Futu OpenAPI (US/HK/A 股通用，懒连接)
    P2: AkShare (免费，仅 A 股)
    P3: Qlib 本地数据
    P4: 降级数据 (明确标注 DATA_QUALITY=degraded)
    """

    def __init__(self):
        """初始化"""
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 3600  # 1 小时缓存（基本面数据变化慢）

        # Futu 懒连接：不在初始化时打开连接，需要时才创建
        self._futu_ctx = None

        # 检测可用数据源
        self.ts_available = self._check_tushare()
        self.ak_available = self._check_akshare()
        self.futu_importable = self._check_futu_importable()  # 仅检查库是否可导入

        # 数据源优先级（Futu 对所有市场都可用）
        self.data_priority = []
        if self.ts_available:
            self.data_priority.append("tushare")
        if self.futu_importable:
            self.data_priority.append("futu")
        if self.ak_available:
            self.data_priority.append("akshare")

        print(f"[Fundamental] 数据源优先级：{self.data_priority if self.data_priority else ['degraded']}")
    
    def _check_tushare(self) -> bool:
        """检查 Tushare 是否可用"""
        # 支持多种环境变量名
        ts_token = os.environ.get('TUSHARE_TOKEN', '') or os.environ.get('TS_TOKEN', '')
        if not ts_token:
            print("[Fundamental] ⚠️ Tushare: 未配置 TUSHARE_TOKEN 或 TS_TOKEN")
            return False
        
        try:
            # 使用环境变量传递 token（安全修复）
            code = "import tushare as ts, os; ts.set_token(os.environ.get('TUSHARE_TOKEN','')); pro = ts.pro_api(); print('ok')"
            env = os.environ.copy()
            env['TUSHARE_TOKEN'] = ts_token
            result = subprocess.run(
                ['/usr/bin/python3.11', '-c', code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=10,
                env=env
            )
            if result.returncode == 0 and 'ok' in result.stdout:
                print("[Fundamental] ✅ Tushare: 已安装并配置")
                return True
            else:
                print(f"[Fundamental] ⚠️ Tushare: 连接失败 - {result.stderr[:100] if result.stderr else 'unknown'}")
        except Exception as e:
            print(f"[Fundamental] ⚠️ Tushare: 检查失败 - {e}")
        
        print("[Fundamental] ❌ Tushare: 不可用")
        return False
    
    def _check_akshare(self) -> bool:
        """检查 AkShare 是否可用"""
        try:
            import subprocess
            # 简单测试导入 (兼容 python3.6)
            result = subprocess.run(
                ['/usr/bin/python3.11', '-c', 'import akshare; print("ok")'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=5
            )
            if result.returncode == 0:
                print("[Fundamental] ✅ AkShare: 已安装")
                return True
            else:
                print(f"[Fundamental] ⚠️ AkShare: 导入失败")
        except Exception as e:
            print(f"[Fundamental] ⚠️ AkShare: 检查失败 - {e}")
        
        print("[Fundamental] ❌ AkShare: 不可用")
        return False

    def _check_futu_importable(self) -> bool:
        """检查富途 OpenAPI 库是否可导入（不实际连接）"""
        try:
            from futu import OpenQuoteContext  # noqa: F401
            print("[Fundamental] ✅ 富途 OpenAPI: 库已安装")
            return True
        except ImportError:
            print("[Fundamental] ❌ 富途 OpenAPI: 库未安装")
            return False
        except Exception as e:
            print(f"[Fundamental] ⚠️ 富途 OpenAPI: 检查失败 - {e}")
            return False

    def _get_futu_context(self):
        """懒连接：获取 Futu 报价上下文（需要时才创建连接）"""
        if self._futu_ctx is None:
            try:
                from futu import OpenQuoteContext
                host = os.environ.get('FUTU_HOST', '127.0.0.1')
                port = int(os.environ.get('FUTU_PORT', 11111))
                self._futu_ctx = OpenQuoteContext(host=host, port=port)
                print("[Fundamental] ✅ 富途 OpenAPI: 已连接")
            except Exception as e:
                print(f"[Fundamental] ❌ 富途 OpenAPI: 连接失败 - {e}")
                self._futu_ctx = False  # 标记连接失败，避免重复尝试
        return self._futu_ctx if self._futu_ctx else None

    def get_fundamental_data(self, symbol: str) -> Dict:
        """
        获取基本面数据（带优先级和降级处理）
        
        Args:
            symbol: 股票代码 (如 "600519.SH" 或 "US.HD")
        
        Returns:
            基本面数据字典，包含 data_quality 标识
        """
        # 检查缓存
        if symbol in self.cache:
            cached = self.cache[symbol]
            if self._is_cache_valid(cached):
                return cached["data"]
        
        # 检测市场类型：美股/港股跳过 Tushare 和 AkShare（仅支持A股）
        sym_upper = symbol.upper()
        is_non_cn = sym_upper.startswith(('US.', 'HK.')) or (sym_upper.endswith('.US') or sym_upper.endswith('.HK'))
        
        # 非A股：重新排列数据源优先级
        if is_non_cn:
            active_sources = [s for s in self.data_priority if s == 'futu']
            if not active_sources:
                active_sources = ['futu'] if self.futu_importable else []
        else:
            active_sources = self.data_priority
        
        # 按优先级获取数据
        data = None
        data_source = "none"
        data_quality = "degraded"
        
        for source in active_sources:
            try:
                if source == "tushare":
                    data = self._fetch_from_tushare(symbol)
                elif source == "futu":
                    data = self._fetch_from_futu(symbol)
                elif source == "akshare":
                    data = self._fetch_from_akshare(symbol)

                if data and data.get('pe') is not None:
                    data_source = source
                    data_quality = "real"
                    print(f"[Fundamental] ✅ {symbol} 数据来自 {source}")
                    break
            except Exception as e:
                print(f"[Fundamental] ⚠️ {source} 失败：{e}")
                continue
        
        # 如果所有真实数据源都失败，使用降级数据
        if data is None:
            data = self._get_degraded_data(symbol)
            data_source = "degraded"
            data_quality = "degraded"
            print(f"[Fundamental] ⚠️ {symbol} 使用降级数据 (不可用于交易)")
        
        # 添加元数据
        data['data_source'] = data_source
        data['data_quality'] = data_quality
        data['last_updated'] = datetime.now().isoformat()
        
        # 缓存
        self.cache[symbol] = {
            "data": data,
            "timestamp": datetime.now()
        }
        
        return data
    
    def _fetch_from_tushare(self, symbol: str) -> Optional[Dict]:
        """从 Tushare Pro 获取基本面数据"""
        # 支持多种环境变量名
        ts_token = os.environ.get('TUSHARE_TOKEN', '') or os.environ.get('TS_TOKEN', '')
        if not ts_token:
            return None

        try:
            import subprocess
            from datetime import datetime

            # 使用环境变量传递参数，避免 f-string 注入（安全修复）
            today = datetime.now().strftime('%Y%m%d')
            code = '''
import tushare as ts
import json
import os
from datetime import datetime

ts.set_token(os.environ.get('TUSHARE_TOKEN', ''))
pro = ts.pro_api()
symbol = os.environ.get('SYMBOL', '')
today = os.environ.get('TODAY', '')

try:
    df = pro.daily_basic(ts_code=symbol, trade_date=today)

    if df.empty:
        df = pro.daily_basic(ts_code=symbol)

    if df.empty:
        print(json.dumps({"error": "no_data"}))
    else:
        row = df.iloc[0]
        result = {
            "pe": float(row.pe) if hasattr(row, 'pe') and row.pe not in [None, ''] else None,
            "pb": float(row.pb) if hasattr(row, 'pb') and row.pb not in [None, ''] else None,
            "ps": float(row.ps) if hasattr(row, 'ps') and row.ps not in [None, ''] else None,
            "dv_ratio": float(row.dv_ratio) if hasattr(row, 'dv_ratio') and row.dv_ratio not in [None, ''] else None,
            "turnover_rate": float(row.turnover_rate) / 100 if hasattr(row, 'turnover_rate') and row.turnover_rate not in [None, ''] else None,
            "volume_ratio": float(row.volume_ratio) if hasattr(row, 'volume_ratio') and row.volume_ratio not in [None, ''] else None,
            "total_mv": float(row.total_mv) if hasattr(row, 'total_mv') and row.total_mv not in [None, ''] else None,
        }
        print(json.dumps(result))
except Exception as e:
    print(json.dumps({"error": str(e)}))
'''
            env = os.environ.copy()
            env['TUSHARE_TOKEN'] = ts_token
            env['SYMBOL'] = symbol
            env['TODAY'] = today

            result = subprocess.run(
                ['/usr/bin/python3.11', '-c', code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=15,
                env=env
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output and not output.startswith('{"error"'):
                    data = json.loads(output)
                    data['data_source'] = 'tushare'
                    data['data_quality'] = 'real'
                    return data
                elif output and 'error' in output:
                    err = json.loads(output)
                    print(f"[Fundamental] Tushare 错误：{err.get('error', 'unknown')}")
        except Exception as e:
            print(f"[Fundamental] Tushare 错误：{e}")

        return None

    def _fetch_from_futu(self, symbol: str) -> Optional[Dict]:
        """从富途 OpenAPI 获取港股/美股基本面数据（使用懒连接）"""
        quote_ctx = self._get_futu_context()
        if quote_ctx is None:
            return None

        try:
            ret, data = quote_ctx.get_market_snapshot(symbol)

            if ret == 0 and len(data) > 0:
                row = data.iloc[0]
                result = {
                    "pe": float(row['pe']) if 'pe' in row and row['pe'] not in [None, '', 0] else None,
                    "pb": float(row['pb']) if 'pb' in row and row['pb'] not in [None, '', 0] else None,
                    "ps": float(row['ps']) if 'ps' in row and row['ps'] not in [None, '', 0] else None,
                    "price": float(row['last_price']) if 'last_price' in row else None,
                    "change_pct": float(row['change_pct']) / 100 if 'change_pct' in row else None,
                    "volume": int(row['volume']) if 'volume' in row else None,
                    "turnover_rate": float(row['turnover_rate']) / 100 if 'turnover_rate' in row else None,
                    "market_cap": float(row['market_cap']) if 'market_cap' in row else None,
                    "pe_ttm": float(row['pe_ttm']) if 'pe_ttm' in row and row['pe_ttm'] not in [None, '', 0] else None,
                }
                return result
        except Exception as e:
            print(f"[Fundamental] 富途错误：{e}")

        return None

    def _fetch_from_akshare(self, symbol: str) -> Optional[Dict]:
        """从 AkShare 获取基本面数据（仅支持A股）"""
        # 美股/港股：AkShare 不支持，直接返回
        sym_upper = symbol.upper()
        if sym_upper.startswith(('US.', 'HK.')) or sym_upper.endswith('.US') or sym_upper.endswith('.HK'):
            return None
        
        try:
            import subprocess

            # 转换股票代码格式
            ak_symbol = symbol.lower().replace(".", "")

            # 使用环境变量传递参数（安全修复）
            code = '''
import akshare as ak
import json
import os

try:
    df = ak.stock_zh_a_spot_em()
    ak_symbol = os.environ.get('AK_SYMBOL', '')
    stock = df[df['代码'] == ak_symbol]

    if stock.empty:
        print(json.dumps({"error": "not_found"}))
    else:
        row = stock.iloc[0]
        print(json.dumps({
            "pe": float(row['市盈率']) if '市盈率' in row and row['市盈率'] not in ['', '-', None] else None,
            "pb": float(row['市净率']) if '市净率' in row and row['市净率'] not in ['', '-', None] else None,
            "ps": float(row['市销率']) if '市销率' in row and row['市销率'] not in ['', '-', None] else None,
            "price": float(row['最新价']) if '最新价' in row else None,
            "change_pct": float(row['涨跌幅']) / 100 if '涨跌幅' in row else None,
            "volume": int(row['成交量']) if '成交量' in row else None,
            "turnover_rate": None,
            "market_cap": float(row['总市值']) if '总市值' in row else None,
        }))
except Exception as e:
    print(json.dumps({"error": str(e)}))
'''
            env = os.environ.copy()
            env['AK_SYMBOL'] = ak_symbol

            result = subprocess.run(
                ['/usr/bin/python3.11', '-c', code],
                capture_output=True, text=True, timeout=15,
                env=env
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output and not output.startswith('{"error"'):
                    data = json.loads(output)
                    return data
        except Exception as e:
            print(f"[Fundamental] AkShare 错误：{e}")

        return None

    def _get_degraded_data(self, symbol: str) -> Dict:
        """
        降级数据（当所有真实数据源都失败时使用）

        ⚠️ 明确标注为 degraded，不可用于真实交易决策

        支持市场识别：
        - A 股：根据代码前缀估计行业
        - 美股 (US.XXX)：使用美股平均估值
        - 港股 (HK.XXX)：使用港股平均估值
        """
        sym_upper = symbol.upper()
        is_us = sym_upper.startswith('US.')
        is_hk = sym_upper.startswith('HK.')

        # 提取裸代码用于行业判断
        bare = sym_upper.replace('US.', '').replace('HK.', '').replace('SH.', '').replace('SZ.', '')
        hash_val = hash(symbol) % 1000

        if is_us:
            # 美股平均估值（2026 年 S&P 500 参考）
            # 科技：PE 25-35x, PB 5-12x
            # 金融：PE 10-15x, PB 1-2x
            # 消费：PE 20-30x, PB 3-8x
            # 能源：PE 8-12x, PB 1-3x
            tech_tickers = ('AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'NFLX', 'ADBE', 'CRM', 'INTC', 'ORACLE', 'CSCO')
            finance_tickers = ('JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'BLK', 'AXP', 'V', 'MA')
            if bare in tech_tickers:
                base_pe = 28 + (hash_val % 10)
                base_pb = 6.0 + (hash_val % 60) / 10
            elif bare in finance_tickers:
                base_pe = 12 + (hash_val % 5)
                base_pb = 1.5 + (hash_val % 10) / 10
            else:
                # S&P 500 平均
                base_pe = 20 + (hash_val % 10)
                base_pb = 3.5 + (hash_val % 40) / 10
        elif is_hk:
            # 港股平均估值（恒生指数参考）
            # 科技（腾讯/阿里/美团）：PE 15-25x, PB 2-5x
            # 金融/地产：PE 5-10x, PB 0.5-1.5x
            # 消费：PE 15-25x, PB 2-5x
            hk_tech = ('00700', '09988', '03690', '09618', '01810', '09888', '09626')
            hk_finance = ('02318', '02628', '03988', '00939', '00941', '00388')
            if bare in hk_tech:
                base_pe = 18 + (hash_val % 10)
                base_pb = 3.0 + (hash_val % 30) / 10
            elif bare in hk_finance:
                base_pe = 7 + (hash_val % 5)
                base_pb = 0.8 + (hash_val % 10) / 10
            else:
                base_pe = 10 + (hash_val % 12)
                base_pb = 1.2 + (hash_val % 25) / 10
        elif bare.startswith('600') or bare.startswith('601'):
            base_pe = 12 + (hash_val % 20)
            base_pb = 1.2 + (hash_val % 30) / 10
        elif bare.startswith('300') or bare.startswith('301'):
            base_pe = 25 + (hash_val % 30)
            base_pb = 3.0 + (hash_val % 50) / 10
        elif bare.startswith('000') or bare.startswith('002'):
            base_pe = 18 + (hash_val % 25)
            base_pb = 2.0 + (hash_val % 40) / 10
        else:
            base_pe = 20
            base_pb = 2.5

        market_label = "美股" if is_us else "港股" if is_hk else "A股"

        return {
            "pe": float(base_pe),
            "pb": float(base_pb),
            "ps": float(base_pe / 3),
            "dv_ratio": float(1.0 + (hash_val % 40) / 10),
            "roe": float(0.08 + (hash_val % 20) / 100),
            "revenue_growth": float(0.05 + (hash_val % 30) / 100),
            "profit_margin": float(0.08 + (hash_val % 25) / 100),
            "debt_ratio": float(0.30 + (hash_val % 40) / 100),
            "turnover_rate": float(0.01 + (hash_val % 100) / 1000),
            "volume_ratio": float(0.8 + (hash_val % 100) / 100),
            "note": f"降级数据 — {market_label}行业平均估计，非真实数据",
            "warning": "⚠️ 数据质量：degraded - 不可用于真实交易决策"
        }
    
    def _is_cache_valid(self, cached: Dict, max_age_seconds: int = 3600) -> bool:
        """检查缓存是否有效"""
        if "timestamp" not in cached:
            return False
        
        age = (datetime.now() - cached["timestamp"]).total_seconds()
        return age < max_age_seconds
    
    def get_financial_statements(self, symbol: str, report_type: str = 'quarterly') -> Dict:
        """
        获取财务报表数据
        
        Args:
            symbol: 股票代码
            report_type: 报告类型 (quarterly/annual)
        
        Returns:
            财务报表数据
        """
        # TODO: 实现财务报表获取
        return {
            "symbol": symbol,
            "report_type": report_type,
            "data_source": "not_implemented",
            "note": "财务报表功能待实现"
        }
    
    def get_industry_comparison(self, symbol: str) -> Dict:
        """
        获取行业对比数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            行业对比数据
        """
        # TODO: 实现行业对比
        return {
            "symbol": symbol,
            "data_source": "not_implemented",
            "note": "行业对比功能待实现"
        }
    
    def get_status(self) -> Dict:
        """获取适配器状态"""
        return {
            "available_sources": self.data_priority,
            "tushare_available": self.ts_available,
            "akshare_available": self.ak_available,
            "futu_importable": self.futu_importable,
            "futu_connected": self._futu_ctx is not None and self._futu_ctx is not False,
            "cache_size": len(self.cache)
        }


# 使用示例
if __name__ == "__main__":
    adapter = FundamentalAdapter()
    
    print("\n" + "=" * 60)
    print("基本面数据适配器测试")
    print("=" * 60)
    
    print("\n适配器状态:")
    print(json.dumps(adapter.get_status(), indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("测试股票：600519.SH (贵州茅台)")
    print("=" * 60)
    
    data = adapter.get_fundamental_data("600519.SH")
    print("\n基本面数据:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("数据质量检查:")
    print(f"  数据源：{data.get('data_source')}")
    print(f"  数据质量：{data.get('data_quality')}")
    if data.get('data_quality') == 'degraded':
        print("  ⚠️ 警告：使用降级数据，不可用于交易决策")
    else:
        print("  ✅ 使用真实数据")
