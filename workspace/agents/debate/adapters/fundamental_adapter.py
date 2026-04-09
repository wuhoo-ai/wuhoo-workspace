#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fundamental Adapter - 基本面数据适配器

数据优先级策略:
1. Tushare Pro API (最可靠，需要 token)
2. AkShare (免费，但可能限流)
3. Qlib 本地数据 (如果有)
4. 降级数据 (明确标注，不可用于交易决策)

更新：2026-03-23 - 重写为真实数据优先，明确标注降级
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class FundamentalAdapter:
    """
    基本面数据适配器
    
    数据源优先级:
    P0: Tushare Pro API (需要 token)
    P1: AkShare (免费，可能限流)
    P2: Qlib 本地数据
    P3: 降级数据 (明确标注 DATA_QUALITY=degraded)
    """
    
    def __init__(self):
        """初始化"""
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 3600  # 1 小时缓存（基本面数据变化慢）

        # 检测可用数据源
        self.ts_available = self._check_tushare()
        self.ak_available = self._check_akshare()
        self.qlib_available = self._check_qlib()
        self.futu_available = self._check_futu()

        # 数据源优先级
        self.data_priority = []
        if self.ts_available:
            self.data_priority.append("tushare")
        if self.futu_available:
            self.data_priority.append("futu")  # 富途优先级高于 AkShare
        if self.ak_available:
            self.data_priority.append("akshare")
        if self.qlib_available:
            self.data_priority.append("qlib")

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
    
    def _check_qlib(self) -> bool:
        """检查 Qlib 本地数据是否可用"""
        qlib_paths = [
            Path("/home/admin/.openclaw/workspace/agents/main/skills/quantaalpha-deep/data/qlib"),
            Path.home() / ".qlib/qlib_data/cn_data",
        ]
        
        for path in qlib_paths:
            if path.exists():
                print(f"[Fundamental] ✅ Qlib: {path}")
                self.qlib_path = path
                return True
        
        print("[Fundamental] ❌ Qlib: 未找到数据")
        return False
    
    def _check_futu(self) -> bool:
        """检查富途 OpenAPI 是否可用"""
        try:
            from futu import OpenQuoteContext
            import os
            host = os.environ.get('FUTU_HOST', '127.0.0.1')
            port = int(os.environ.get('FUTU_PORT', 11111))

            # 尝试连接
            quote_ctx = OpenQuoteContext(host=host, port=port)
            # 尝试获取一个港股行情
            ret, data = quote_ctx.get_market_snapshot('HK.00700')
            quote_ctx.close()

            if ret == 0:
                print("[Fundamental] ✅ 富途 OpenAPI: 已连接")
                return True
            else:
                print(f"[Fundamental] ⚠️ 富途 OpenAPI: 连接失败")
        except Exception as e:
            print(f"[Fundamental] ⚠️ 富途 OpenAPI: 检查失败 - {e}")

        print("[Fundamental] ❌ 富途 OpenAPI: 不可用")
        return False

    def get_fundamental_data(self, symbol: str) -> Dict:
        """
        获取基本面数据（带优先级和降级处理）
        
        Args:
            symbol: 股票代码 (如 "600519.SH")
        
        Returns:
            基本面数据字典，包含 data_quality 标识
        """
        # 检查缓存
        if symbol in self.cache:
            cached = self.cache[symbol]
            if self._is_cache_valid(cached):
                return cached["data"]
        
        # 按优先级获取数据
        data = None
        data_source = "none"
        data_quality = "degraded"
        
        for source in self.data_priority:
            try:
                if source == "tushare":
                    data = self._fetch_from_tushare(symbol)
                elif source == "futu":
                    data = self._fetch_from_futu(symbol)
                elif source == "akshare":
                    data = self._fetch_from_akshare(symbol)
                elif source == "qlib":
                    data = self._fetch_from_qlib(symbol)
                
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
        """从富途 OpenAPI 获取港股/美股基本面数据"""
        try:
            from futu import OpenQuoteContext
            import os

            host = os.environ.get('FUTU_HOST', '127.0.0.1')
            port = int(os.environ.get('FUTU_PORT', 11111))

            quote_ctx = OpenQuoteContext(host=host, port=port)
            ret, data = quote_ctx.get_market_snapshot(symbol)
            quote_ctx.close()

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
        """从 AkShare 获取基本面数据"""
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
    
    def _fetch_from_qlib(self, symbol: str) -> Optional[Dict]:
        """从 Qlib 获取基本面数据（有限）"""
        # Qlib 主要存储行情数据，基本面数据有限
        # 这里仅作为降级方案
        
        if not hasattr(self, 'qlib_path'):
            return None
        
        # 转换股票代码
        market, code = symbol.split(".")
        qlib_code = f"{market.lower()}{code}"
        
        feature_dir = self.qlib_path / "cn_data" / "features" / qlib_code
        if not feature_dir.exists():
            return None
        
        # Qlib 不包含 PE/PB 等基本面数据
        # 仅返回技术面相关数据
        return {
            "note": "Qlib 仅提供行情数据，不包含基本面指标",
            "qlib_available": True
        }
    
    def _get_degraded_data(self, symbol: str) -> Dict:
        """
        降级数据（当所有真实数据源都失败时使用）
        
        ⚠️ 明确标注为 degraded，不可用于真实交易决策
        """
        # 使用行业平均估值作为参考（基于 A 股整体数据）
        # 这些数据是合理的估计值，但不是真实数据
        
        # 基于股票代码生成可重复的"估计值"
        hash_val = hash(symbol) % 1000
        
        # A 股平均估值参考（2026 年）
        # 银行/金融：PE 5-8x, PB 0.5-1.0x
        # 消费/食品：PE 20-40x, PB 5-10x
        # 科技/电子：PE 25-50x, PB 3-8x
        # 医药：PE 25-45x, PB 4-9x
        
        # 根据股票代码前缀估计行业
        if symbol.startswith('600') or symbol.startswith('601'):
            # 沪市主板，可能是传统行业
            base_pe = 12 + (hash_val % 20)
            base_pb = 1.2 + (hash_val % 30) / 10
        elif symbol.startswith('300') or symbol.startswith('301'):
            # 创业板，可能是科技/成长
            base_pe = 25 + (hash_val % 30)
            base_pb = 3.0 + (hash_val % 50) / 10
        elif symbol.startswith('000') or symbol.startswith('002'):
            # 深市主板/中小板
            base_pe = 18 + (hash_val % 25)
            base_pb = 2.0 + (hash_val % 40) / 10
        else:
            base_pe = 20
            base_pb = 2.5
        
        return {
            "pe": float(base_pe),
            "pb": float(base_pb),
            "ps": float(base_pe / 3),  # 粗略估计
            "dv_ratio": float(1.0 + (hash_val % 40) / 10),  # 股息率
            "roe": float(0.08 + (hash_val % 20) / 100),  # ROE 8%-28%
            "revenue_growth": float(0.05 + (hash_val % 30) / 100),  # 营收增速 5%-35%
            "profit_margin": float(0.08 + (hash_val % 25) / 100),  # 净利率 8%-33%
            "debt_ratio": float(0.30 + (hash_val % 40) / 100),  # 负债率 30%-70%
            "turnover_rate": float(0.01 + (hash_val % 100) / 1000),  # 换手率 1%-11%
            "volume_ratio": float(0.8 + (hash_val % 100) / 100),  # 量比 0.8-1.8
            "note": "降级数据 - 基于行业平均估计，非真实数据",
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
            "qlib_available": self.qlib_available,
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
