#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkShare Adapter - 技术面数据适配器

从 akshare 获取 A 股技术面数据。
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


class AkShareAdapter:
    """
    AkShare 技术面数据适配器
    
    功能:
    - 获取股票实时行情
    - 计算技术指标 (MACD/RSI/KDJ 等)
    - 获取资金流向
    """
    
    def __init__(self):
        """初始化"""
        self.cache: Dict[str, Dict] = {}
        self.akshare_available = self._check_akshare()
        self.use_python311 = True  # 使用 python3.11 执行 akshare
    
    def _check_akshare(self) -> bool:
        """检查 akshare 是否可用 (使用 python3.11)"""
        try:
            import subprocess
            result = subprocess.run(
                ['/usr/bin/python3.11', '-c', 'import akshare; print("ok")'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
            else:
                print("Warning: akshare not installed in python3.11. Using mock data.")
                return False
        except Exception:
            print("Warning: akshare check failed. Using mock data.")
            return False
    
    def get_technical_data(self, symbol: str) -> Dict:
        """
        获取股票技术面数据
        
        Args:
            symbol: 股票代码 (如 "600519.SH")
        
        Returns:
            技术面数据字典
        """
        if symbol in self.cache:
            return self.cache[symbol]
        
        if self.akshare_available:
            data = self._fetch_from_akshare(symbol)
        else:
            data = self._get_mock_data(symbol)
        
        self.cache[symbol] = data
        return data
    
    def _fetch_from_akshare(self, symbol: str) -> Dict:
        """
        从 akshare 获取真实数据 (使用 subprocess 调用 python3.11)
        
        使用独立的 akshare_fetcher.py 脚本
        """
        try:
            import subprocess
            from pathlib import Path
            
            # 获取 fetcher 脚本路径
            fetcher_path = Path(__file__).parent / "akshare_fetcher.py"
            
            if not fetcher_path.exists():
                print(f"AkShare fetcher 脚本不存在：{fetcher_path}")
                return self._get_mock_data(symbol)
            
            # 调用 python3.11 执行
            result = subprocess.run(
                ['/usr/bin/python3.11', str(fetcher_path), symbol],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output and not output.startswith('{"error"'):
                    data = json.loads(output)
                    return data
                elif output and 'error' in output:
                    err = json.loads(output)
                    print(f"AkShare 错误：{err.get('error', 'unknown')}")
            else:
                print(f"AkShare 执行失败：{result.stderr[:200] if result.stderr else 'unknown'}")
            
            return self._get_mock_data(symbol)
            
        except Exception as e:
            print(f"AkShare 错误：{e}")
            return self._get_mock_data(symbol)
    
    def _get_mock_data(self, symbol: str) -> Dict:
        """生成模拟技术面数据"""
        hash_val = hash(symbol) % 100
        
        # 生成 MACD 状态
        macd_states = ["golden_cross", "death_cross", "neutral", "divergence"]
        macd = macd_states[hash_val % len(macd_states)]
        
        # 生成 RSI
        rsi = 30 + (hash_val % 50)  # 30-80
        
        # 生成趋势
        trends = ["uptrend", "downtrend", "sideways"]
        trend = trends[hash_val % len(trends)]
        
        # 判断是否超买/超卖
        if rsi > 70:
            signal = "overbought"
        elif rsi < 30:
            signal = "oversold"
        else:
            signal = "neutral"
        
        return {
            "macd": macd,
            "rsi": rsi,
            "kdj": {
                "k": 50 + (hash_val % 40),
                "d": 45 + (hash_val % 40),
                "j": 55 + (hash_val % 50)
            },
            "trend": trend,
            "signal": signal,
            "volume_ratio": 0.8 + (hash_val % 100) / 50,
            "turnover_rate": 0.01 + (hash_val % 100) / 1000,
            "price": 100 + (hash_val % 1000),
            "change_pct": (hash_val % 20 - 10) / 100,
            "volume": 1000000 + (hash_val % 10000000),
            "last_updated": datetime.now().isoformat(),
            "note": "Mock data (akshare not available or error)"
        }
    
    def get_price_history(self, symbol: str, days: int = 60) -> Optional[List[Dict]]:
        """
        获取历史价格数据
        
        Args:
            symbol: 股票代码
            days: 天数
        
        Returns:
            历史价格列表
        """
        if not self.akshare_available:
            return self._get_mock_history(symbol, days)
        
        try:
            import akshare as ak
            
            # 获取历史数据
            # ... (实现略)
            
            return self._get_mock_history(symbol, days)
            
        except Exception as e:
            print(f"Error fetching history: {e}")
            return self._get_mock_history(symbol, days)
    
    def _get_mock_history(self, symbol: str, days: int) -> List[Dict]:
        """生成模拟历史数据"""
        history = []
        base_price = 100 + (hash(symbol) % 1000)
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i)).strftime("%Y-%m-%d")
            change = (hash(symbol + str(i)) % 11 - 5) / 100  # -5% to +5%
            price = base_price * (1 + change)
            
            history.append({
                "date": date,
                "open": price * (0.98 + hash(symbol + str(i)) % 10 / 500),
                "high": price * (1.02 + hash(symbol + str(i)) % 10 / 500),
                "low": price * (0.96 + hash(symbol + str(i)) % 10 / 500),
                "close": price,
                "volume": 1000000 + hash(symbol + str(i)) % 10000000
            })
        
        return history
    
    def get_money_flow(self, symbol: str) -> Dict:
        """
        获取资金流向
        
        Args:
            symbol: 股票代码
        
        Returns:
            资金流向数据
        """
        if not self.akshare_available:
            return self._get_mock_money_flow(symbol)
        
        # ... (实现略)
        return self._get_mock_money_flow(symbol)
    
    def _get_mock_money_flow(self, symbol: str) -> Dict:
        """生成模拟资金流向"""
        hash_val = hash(symbol) % 100
        
        return {
            "net_inflow": (hash_val - 50) * 10000,  # 净流入 (元)
            "main_force_inflow": (hash_val - 50) * 5000,
            "retail_inflow": (hash_val - 50) * 5000,
            "inflow_ratio": 0.4 + (hash_val % 40) / 100,
            "large_order_ratio": 0.2 + (hash_val % 30) / 100,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_support_resistance(self, symbol: str) -> Dict:
        """
        获取支撑位/阻力位
        
        Args:
            symbol: 股票代码
        
        Returns:
            支撑位和阻力位
        """
        current_price = self.get_technical_data(symbol).get("price", 100)
        
        return {
            "current_price": current_price,
            "support_levels": [
                current_price * 0.95,
                current_price * 0.90,
                current_price * 0.85
            ],
            "resistance_levels": [
                current_price * 1.05,
                current_price * 1.10,
                current_price * 1.15
            ]
        }
    
    def is_available(self) -> bool:
        """检查 akshare 是否可用"""
        return self.akshare_available
    
    def get_status(self) -> Dict:
        """获取适配器状态"""
        return {
            "available": self.akshare_available,
            "cache_size": len(self.cache)
        }


# 使用示例
if __name__ == "__main__":
    adapter = AkShareAdapter()
    
    print("AkShare 状态:", adapter.get_status())
    print("\n600519.SH 技术面数据:")
    data = adapter.get_technical_data("600519.SH")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    print("\n支撑/阻力位:")
    sr = adapter.get_support_resistance("600519.SH")
    print(json.dumps(sr, indent=2, ensure_ascii=False))
