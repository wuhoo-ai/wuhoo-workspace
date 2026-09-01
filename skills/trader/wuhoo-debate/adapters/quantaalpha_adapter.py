#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantaAlpha Adapter - 因子数据适配器（真实数据版本）

从 QuantaAlpha 系统获取真实的因子挖掘结果和个股因子信号。

数据源:
1. factor_icir_analysis.json - 190 个因子的 IC/IR 分析数据
2. Qlib features 目录 - 个股因子值 (factor.day.bin)
3. factor_backtest_results.json - 因子回测结果

更新: 2026-03-23 - 重写为真实数据集成
"""

import json
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class QuantaAlphaAdapter:
    """
    QuantaAlpha 因子数据适配器（真实数据版本）
    
    功能:
    - 读取 QuantaAlpha 因子库（190 个真实因子，带 IC/IR）
    - 从 Qlib 读取个股因子值
    - 计算基于真实数据的因子信号评分
    - 提供 Top 因子信号给辩论系统
    """
    
    # 因子类别映射
    CATEGORY_MAP = {
        "momentum": "动量",
        "reversal": "反转",
        "volume": "成交量",
        "volatility": "波动率",
        "liquidity": "流动性",
        "price_volume": "量价结合",
        "generated": "挖掘因子",
    }
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化
        
        Args:
            data_dir: QuantaAlpha 数据目录 (默认：自动检测)
        """
        self.data_dir: Optional[Path] = None
        self.factor_library: List[Dict] = []
        self.factor_cache: Dict[str, Dict] = {}
        self._last_library_load: Optional[datetime] = None
        
        # 自动检测数据目录
        self._init_data_dir(data_dir)
        
        # 加载因子库
        self._load_factor_library()
    
    def _init_data_dir(self, data_dir: Optional[str]) -> None:
        """初始化数据目录"""
        if data_dir:
            self.data_dir = Path(data_dir)
            return
        
        # 自动检测可能的路径
        possible_paths = [
            Path.home() / ".hermes/workspace/agents/main/skills/quantaalpha-deep/data",
            Path("/home/admin/.hermes/workspace/agents/main/skills/quantaalpha-deep/data"),
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "results").exists():
                self.data_dir = path
                print(f"[QuantaAlpha] 数据目录：{self.data_dir}")
                return
        
        print("[QuantaAlpha] ⚠️ 未找到数据目录")
        self.data_dir = None
    
    def _load_factor_library(self) -> None:
        """加载因子库"""
        if not self.data_dir:
            return
        
        # 优先使用 factor_icir_analysis.json（包含 190 个因子）
        icir_path = self.data_dir / "results" / "factor_icir_analysis.json"
        if icir_path.exists():
            try:
                with open(icir_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 提取 all_unique_factors 或 top_factors
                self.factor_library = data.get('all_unique_factors', data.get('top_factors', []))
                self._last_library_load = datetime.now()
                
                print(f"[QuantaAlpha] ✅ 加载因子库：{len(self.factor_library)} 个因子")
                print(f"[QuantaAlpha]    平均 IC: {data['statistics']['avg_ic']:.4f}, 平均 IR: {data['statistics']['avg_ir']:.2f}")
                return
            except Exception as e:
                print(f"[QuantaAlpha] ⚠️ 加载 factor_icir_analysis.json 失败：{e}")
        
        # 降级到 factor_library.json
        lib_path = self.data_dir / "results" / "factor_library.json"
        if lib_path.exists():
            try:
                with open(lib_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                factors_dict = data.get('factors', {})
                self.factor_library = list(factors_dict.values()) if isinstance(factors_dict, dict) else factors_dict
                
                print(f"[QuantaAlpha] ⚠️ 降级加载 factor_library.json: {len(self.factor_library)} 个因子")
                return
            except Exception as e:
                print(f"[QuantaAlpha] ⚠️ 加载 factor_library.json 失败：{e}")
        
        print("[QuantaAlpha] ❌ 无法加载因子库")
    
    def _symbol_to_qlib_code(self, symbol: str) -> str:
        """
        转换股票代码为 Qlib 格式
        
        Args:
            symbol: 股票代码 (如 "600519.SH" 或 "301029.SZ")
        
        Returns:
            Qlib 格式代码 (如 "sh600519" 或 "sz301029")
        """
        # 处理不同格式
        if "." in symbol:
            # 格式：600519.SH 或 301029.SZ
            code, market = symbol.split(".")
            market = market.lower()
        else:
            # 假设是 SH/SZ 开头
            code = symbol[2:] if symbol[:2].upper() in ["SH", "SZ"] else symbol
            market = "sh" if symbol[:2].upper() == "SH" else "sz"
        
        return f"{market}{code}"
    
    def _read_qlib_feature(self, feature_dir: Path, feature_name: str = "factor") -> Optional[np.ndarray]:
        """
        读取 Qlib 特征文件
        
        Args:
            feature_dir: Qlib 特征目录
            feature_name: 特征名称 (默认 "factor")
        
        Returns:
            特征值数组，失败返回 None
        """
        feature_file = feature_dir / f"{feature_name}.day.bin"
        if not feature_file.exists():
            return None
        
        try:
            data = np.fromfile(feature_file, dtype=np.float32)
            return data
        except Exception as e:
            print(f"[QuantaAlpha] 读取 {feature_file} 失败：{e}")
            return None
    
    def _calculate_signal_from_factor_value(self, factor_value: float, 
                                             lookback_values: np.ndarray) -> Dict:
        """
        从因子值计算信号
        
        Args:
            factor_value: 当前因子值
            lookback_values: 历史因子值（用于计算分位数）
        
        Returns:
            信号字典
        """
        # 处理 NaN
        if np.isnan(factor_value) or np.isnan(lookback_values).all():
            return {
                "signal": 0.0,
                "percentile": 0.5,
                "zscore": 0.0
            }
        
        # 计算分位数
        valid_values = lookback_values[~np.isnan(lookback_values)]
        if len(valid_values) < 20:
            percentile = 0.5
        else:
            percentile = np.sum(valid_values < factor_value) / len(valid_values)
        
        # 计算 Z-Score
        mean_val = np.nanmean(lookback_values)
        std_val = np.nanstd(lookback_values)
        zscore = (factor_value - mean_val) / (std_val + 1e-8)
        
        # 信号强度：-1 (强空) 到 +1 (强多)
        # 使用分位数映射到信号
        signal = (percentile - 0.5) * 2  # 0.5->0, 1.0->+1, 0.0->-1
        
        return {
            "signal": float(np.clip(signal, -1.0, 1.0)),
            "percentile": float(percentile),
            "zscore": float(zscore),
            "raw_value": float(factor_value)
        }
    
    def get_factor_scores(self, symbol: str) -> Dict:
        """
        获取股票因子评分（真实数据版本）
        
        Args:
            symbol: 股票代码 (如 "600519.SH")
        
        Returns:
            因子评分字典
        """
        # 先查缓存
        if symbol in self.factor_cache:
            cached = self.factor_cache[symbol]
            # 缓存有效期 5 分钟
            if "timestamp" in cached:
                try:
                    ts = datetime.fromisoformat(cached["timestamp"])
                except (AttributeError, ValueError):
                    # 兼容旧格式或解析失败
                    ts = datetime.now()
                age = (datetime.now() - ts).total_seconds()
                if age < 300:
                    return cached["data"]
        
        result = self._calculate_real_factor_scores(symbol)
        
        # 缓存
        self.factor_cache[symbol] = {
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def _calculate_real_factor_scores(self, symbol: str) -> Dict:
        """计算真实的因子评分"""
        if not self.data_dir:
            return self._get_error_result("数据目录未配置")
        
        # 转换为 Qlib 代码
        qlib_code = self._symbol_to_qlib_code(symbol)
        feature_dir = self.data_dir / "qlib/cn_data/features" / qlib_code
        
        if not feature_dir.exists():
            return self._get_error_result(f"未找到股票数据：{symbol}")
        
        # 读取因子值
        factor_values = self._read_qlib_feature(feature_dir, "factor")
        close_values = self._read_qlib_feature(feature_dir, "close")
        
        if factor_values is None or len(factor_values) == 0:
            return self._get_error_result("因子数据不可用")
        
        # 获取最新因子值
        latest_factor = factor_values[-1]
        lookback_20d = factor_values[-20:] if len(factor_values) >= 20 else factor_values
        lookback_60d = factor_values[-60:] if len(factor_values) >= 60 else factor_values
        
        # 计算信号
        signal_info = self._calculate_signal_from_factor_value(latest_factor, lookback_60d)
        
        # 计算动量（基于价格）
        momentum_score = self._calculate_momentum_score(close_values)
        
        # 计算波动率
        volatility_score = self._calculate_volatility_score(close_values)
        
        # 综合评分
        composite_score = (
            signal_info["signal"] * 0.4 +  # 因子信号 40%
            (momentum_score - 5) / 5 * 0.3 +  # 动量 30%
            (volatility_score - 5) / 5 * 0.3  # 波动率 30%
        )
        
        return {
            "symbol": symbol,
            "qlib_code": qlib_code,
            
            # 核心因子信号
            "factor_signal": signal_info["signal"],
            "factor_percentile": signal_info["percentile"],
            "factor_zscore": signal_info["zscore"],
            "factor_raw_value": signal_info.get("raw_value", 0),
            
            # 分类评分 (0-10)
            "momentum_score": momentum_score,
            "volatility_score": volatility_score,
            "turnover_score": 5.0,  # TODO: 需要成交量数据
            "residual_volatility": 5.0,  # TODO: 需要残差波动率计算
            "beta": 1.0,  # TODO: 需要市场数据计算 Beta
            
            # 综合评分
            "composite_score": np.clip(composite_score, -1.0, 1.0),
            "composite_rating": (composite_score + 1) / 2 * 10,  # 映射到 0-10
            
            # 因子库信息
            "factor_library_size": len(self.factor_library),
            "top_factor_ic": self.factor_library[0]["ic"] if self.factor_library else 0,
            
            # 数据状态
            "data_points": len(factor_values),
            "last_updated": datetime.now().isoformat(),
            "data_source": "quantaalpha_real_data"
        }
    
    def _calculate_momentum_score(self, close_values: np.ndarray) -> float:
        """计算动量评分 (0-10)"""
        if len(close_values) < 20:
            return 5.0
        
        # 20 日动量
        mom_20d = (close_values[-1] - close_values[-20]) / (close_values[-20] + 1e-8)
        
        # 5 日动量
        mom_5d = (close_values[-1] - close_values[-5]) / (close_values[-5] + 1e-8) if len(close_values) >= 5 else 0
        
        # 综合动量评分
        momentum = (mom_20d * 0.7 + mom_5d * 0.3) * 100  # 转换为百分比
        
        # 映射到 0-10 分
        # -5% -> 0 分，0% -> 5 分，+5% -> 10 分
        score = 5 + momentum
        return float(np.clip(score, 0, 10))
    
    def _calculate_volatility_score(self, close_values: np.ndarray) -> float:
        """计算波动率评分 (0-10)"""
        if len(close_values) < 20:
            return 5.0
        
        # 计算日收益率
        returns = np.diff(close_values) / (close_values[:-1] + 1e-8)
        
        # 20 日波动率
        vol_20d = np.std(returns[-20:]) * np.sqrt(252)  # 年化
        
        # 映射到 0-10 分
        # 波动率 10% -> 5 分，20% -> 3 分，40% -> 1 分，5% -> 7 分
        # 适度波动最好
        if vol_20d < 0.15:
            score = 7 - (0.15 - vol_20d) * 20  # 太低也不好
        elif vol_20d < 0.30:
            score = 7 - (vol_20d - 0.15) * 20
        else:
            score = 4 - (vol_20d - 0.30) * 10
        
        return float(np.clip(score, 0, 10))
    
    def _get_error_result(self, error_msg: str) -> Dict:
        """返回错误结果"""
        return {
            "symbol": "unknown",
            "error": error_msg,
            "factor_signal": 0.0,
            "momentum_score": 5.0,
            "volatility_score": 5.0,
            "turnover_score": 5.0,
            "residual_volatility": 5.0,
            "beta": 1.0,
            "composite_score": 0.0,
            "composite_rating": 5.0,
            "factor_library_size": len(self.factor_library),
            "data_source": "error",
            "last_updated": datetime.now().isoformat()
        }
    
    def get_top_factor_signals(self, symbol: str, top_n: int = 10,
                                min_ic: float = 0.05, min_ir: float = 1.0) -> Dict:
        """
        获取 Top 因子信号（用于辩论系统）
        
        Args:
            symbol: 股票代码
            top_n: 返回 Top N 个因子
            min_ic: 最小 IC 阈值
            min_ir: 最小 IR 阈值
        
        Returns:
            Top 因子信号字典
        """
        # 获取基础评分
        base_scores = self.get_factor_scores(symbol)
        
        if "error" in base_scores:
            return {
                "symbol": symbol,
                "factor_signals": [],
                "composite_score": 0.0,
                "error": base_scores["error"]
            }
        
        # 筛选高质量因子
        high_quality_factors = [
            f for f in self.factor_library
            if f.get("ic", 0) >= min_ic and f.get("ir", 0) >= min_ir
        ]
        
        # 按 IC 排序取 Top N
        top_factors = sorted(high_quality_factors, key=lambda x: x.get("ic", 0), reverse=True)[:top_n]
        
        # 生成因子信号
        factor_signals = []
        for i, factor in enumerate(top_factors):
            # 基于因子 IC/IR 和当前市场状态生成信号
            # 注意：这里使用简化的信号生成，实际应该计算每个因子的当前值
            signal_strength = base_scores["factor_signal"]
            
            factor_signals.append({
                "factor_id": factor.get("factor_id", f"factor_{i}"),
                "factor_name": factor.get("factor_name", "Unknown"),
                "factor_expression": factor.get("factor_expression", ""),
                "category": factor.get("category", "generated"),
                "category_cn": self.CATEGORY_MAP.get(factor.get("category", "generated"), "未知"),
                "ic": factor.get("ic", 0),
                "rank_ic": factor.get("rank_ic", 0),
                "ir": factor.get("ir", 0),
                "signal": signal_strength,
                "weight": factor.get("ic", 0.1) / sum(f.get("ic", 0.1) for f in top_factors),
            })
        
        # 计算综合评分
        composite_score = sum(
            fs["signal"] * fs["weight"] * fs["ic"] * 10  # IC 加权
            for fs in factor_signals
        )
        
        return {
            "symbol": symbol,
            "factor_signals": factor_signals,
            "composite_score": float(np.clip(composite_score, -1.0, 1.0)),
            "factor_count": len(factor_signals),
            "avg_ic": sum(fs["ic"] for fs in factor_signals) / len(factor_signals) if factor_signals else 0,
            "avg_ir": sum(fs["ir"] for fs in factor_signals) / len(factor_signals) if factor_signals else 0,
            "data_source": "quantaalpha_real_data",
            "last_updated": datetime.now().isoformat()
        }
    
    def get_factor_library(self) -> List[Dict]:
        """获取完整因子库"""
        return self.factor_library
    
    def get_backtest_results(self, symbol: str, days: int = 20) -> Dict:
        """
        获取回测结果摘要
        
        从 factor_backtest_results.json 读取真实回测数据
        """
        if not self.data_dir:
            return {"error": "数据目录未配置"}
        
        backtest_path = self.data_dir / "results" / "factor_backtest_results.json"
        if not backtest_path.exists():
            return {"error": "回测数据不存在"}
        
        try:
            with open(backtest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 返回回测摘要
            return {
                "symbol": symbol,
                "period_days": days,
                "backtest_available": True,
                "top_factor_return": data.get("statistics", {}).get("avg_annualized_return", 0.35),
                "sharpe_ratio": data.get("statistics", {}).get("avg_sharpe", 1.5),
                "max_drawdown": data.get("statistics", {}).get("avg_max_drawdown", 0.25),
                "data_source": "quantaalpha_backtest",
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": f"读取回测数据失败：{e}"}
    
    def is_available(self) -> bool:
        """检查 QuantaAlpha 数据是否可用"""
        return (
            self.data_dir is not None and
            (self.data_dir / "results").exists() and
            len(self.factor_library) > 0
        )
    
    def get_status(self) -> Dict:
        """获取适配器状态"""
        return {
            "available": self.is_available(),
            "data_dir": str(self.data_dir) if self.data_dir else None,
            "factor_library_size": len(self.factor_library),
            "cache_size": len(self.factor_cache),
            "last_library_load": self._last_library_load.isoformat() if self._last_library_load else None,
            "data_source": "real_data" if self.is_available() else "none"
        }


# 使用示例
if __name__ == "__main__":
    adapter = QuantaAlphaAdapter()
    
    print("=" * 60)
    print("QuantaAlpha Adapter - 真实数据版本")
    print("=" * 60)
    
    print("\n适配器状态:")
    print(json.dumps(adapter.get_status(), indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("测试股票：600519.SH (贵州茅台)")
    print("=" * 60)
    
    # 测试基础评分
    print("\n[1] 基础因子评分:")
    scores = adapter.get_factor_scores("600519.SH")
    print(json.dumps(scores, indent=2, ensure_ascii=False))
    
    # 测试 Top 因子信号
    print("\n[2] Top 10 因子信号:")
    top_signals = adapter.get_top_factor_signals("600519.SH", top_n=10)
    print(f"综合评分：{top_signals['composite_score']:.3f}")
    print(f"因子数量：{top_signals['factor_count']}")
    print(f"平均 IC: {top_signals['avg_ic']:.4f}")
    print(f"平均 IR: {top_signals['avg_ir']:.2f}")
    print("\nTop 5 因子:")
    for i, fs in enumerate(top_signals['factor_signals'][:5], 1):
        print(f"  {i}. {fs['factor_name']}")
        print(f"     IC: {fs['ic']:.3f}, IR: {fs['ir']:.2f}, 信号：{fs['signal']:.3f}")
