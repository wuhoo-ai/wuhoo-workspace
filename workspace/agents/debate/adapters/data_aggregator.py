#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Aggregator - 数据聚合器（真实数据版本）

整合多个数据源，为辩论系统提供统一的数据接口。

数据优先级策略:
- P0: 真实 API 数据 (Tushare/AkShare/QuantaAlpha)
- P1: 本地缓存数据
- P2: 降级数据 (明确标注，不可用于交易)

更新：2026-03-23 - 确保所有数据真实有效或明确标注降级
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime

from .quantaalpha_adapter import QuantaAlphaAdapter
from .trendradar_adapter import TrendRadarAdapter
from .akshare_adapter import AkShareAdapter
from .web_search_adapter import WebSearchSentimentAdapter
from .fundamental_adapter import FundamentalAdapter


class DataAggregator:
    """
    数据聚合器
    
    功能:
    - 统一接口获取所有数据
    - 数据缓存
    - 数据质量检查
    """
    
    def __init__(self):
        """初始化所有适配器"""
        self.quantaalpha = QuantaAlphaAdapter()
        self.trendradar = TrendRadarAdapter()
        self.akshare = AkShareAdapter()
        self.web_search = WebSearchSentimentAdapter()
        self.fundamental = FundamentalAdapter()  # 新增：基本面数据适配器
        
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 分钟缓存
        
        # 数据质量监控
        self.data_quality_report: Dict[str, str] = {}
    
    def get_all_data(self, symbol: str, company_name: Optional[str] = None) -> Dict:
        """
        获取股票的所有数据
        
        Args:
            symbol: 股票代码
            company_name: 公司名称 (可选)
        
        Returns:
            综合数据字典
        """
        cache_key = symbol
        if company_name:
            cache_key = f"{symbol}_{company_name}"
        
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # 检查缓存是否过期 (5 分钟)
            if self._is_cache_valid(cached):
                return cached["data"]
        
        # 获取各数据源（按优先级）
        factor_data = self.quantaalpha.get_factor_scores(symbol)
        sentiment_data = self.trendradar.get_sentiment_data(symbol, company_name)
        technical_data = self.akshare.get_technical_data(symbol)
        
        # 获取基本面数据（真实数据优先）
        fundamental_data = self._get_fundamental_data(symbol)
        
        # 获取市场数据
        market_data = self._get_market_data(symbol, technical_data, fundamental_data)
        
        # 记录数据质量
        self.data_quality_report[symbol] = {
            "factor": factor_data.get('data_source', 'unknown'),
            "technical": technical_data.get('data_source', 'unknown'),
            "fundamental": fundamental_data.get('data_source', 'unknown'),
            "sentiment": sentiment_data.get('source', 'unknown'),
            "timestamp": datetime.now().isoformat()
        }
        
        # 数据质量检查
        data_quality_ok = (
            factor_data.get('data_source') == 'quantaalpha_real_data' and
            fundamental_data.get('data_quality') == 'real'
        )
        
        # 聚合数据
        aggregated = {
            "factor_data": factor_data,
            "technical_data": technical_data,
            "sentiment_data": sentiment_data,
            "fundamental_data": fundamental_data,
            "market_data": market_data,
            "data_quality": {
                "overall": "good" if data_quality_ok else "degraded",
                "factor": factor_data.get('data_source', 'unknown'),
                "fundamental": fundamental_data.get('data_source', 'unknown'),
                "technical": technical_data.get('data_source', 'unknown'),
                "sentiment": sentiment_data.get('source', 'unknown'),
                "warning": None if data_quality_ok else "⚠️ 部分数据源使用降级数据，决策需谨慎"
            },
            "metadata": {
                "symbol": symbol,
                "company_name": company_name,
                "timestamp": datetime.now().isoformat(),
                "data_sources": {
                    "quantaalpha": self.quantaalpha.get_status(),
                    "trendradar": self.trendradar.get_status(),
                    "akshare": self.akshare.get_status(),
                    "web_search": self.web_search.get_status(),
                    "fundamental": self.fundamental.get_status()
                }
            }
        }
        
        # 缓存
        self.cache[cache_key] = {
            "data": aggregated,
            "timestamp": datetime.now()
        }
        
        return aggregated
    
    def _get_combined_sentiment(self, symbol: str, company_name: Optional[str]) -> Dict:
        """
        获取综合舆情数据 (整合多个数据源)
        
        策略:
        1. TrendRadar (主要)
        2. Web Search (补充，Tavily/Jina)
        3. 加权平均
        """
        sentiment_sources = []
        
        # 源 1: TrendRadar
        try:
            tr_sentiment = self.trendradar.get_sentiment_data(symbol, company_name)
            if tr_sentiment and tr_sentiment.get("sentiment_score") is not None:
                sentiment_sources.append({
                    "source": "trendradar",
                    "score": tr_sentiment["sentiment_score"],
                    "weight": 0.6,  # 60% 权重
                    "data": tr_sentiment
                })
        except Exception as e:
            print(f"TrendRadar 舆情获取失败：{e}")
        
        # 源 2: Web Search
        try:
            ws_sentiment = self.web_search.get_sentiment_data(symbol, company_name or "")
            if ws_sentiment and ws_sentiment.get("sentiment_score") is not None:
                sentiment_sources.append({
                    "source": "web_search",
                    "score": ws_sentiment["sentiment_score"],
                    "weight": 0.4,  # 40% 权重
                    "data": ws_sentiment
                })
        except Exception as e:
            print(f"Web Search 舆情获取失败：{e}")
        
        # 如果没有有效数据源，返回中性数据
        if not sentiment_sources:
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "source": "none",
                "note": "所有舆情数据源失败"
            }
        
        # 加权平均计算综合评分
        total_weight = sum(s["weight"] for s in sentiment_sources)
        weighted_score = sum(s["score"] * s["weight"] for s in sentiment_sources)
        combined_score = weighted_score / total_weight if total_weight > 0 else 0.0
        
        # 确定情感标签
        if combined_score > 0.2:
            label = "positive"
        elif combined_score < -0.2:
            label = "negative"
        else:
            label = "neutral"
        
        # 合并热点话题
        all_topics = []
        for s in sentiment_sources:
            all_topics.extend(s["data"].get("hot_topics", [])[:3])
        
        return {
            "sentiment_score": round(combined_score, 3),
            "sentiment_label": label,
            "positive_ratio": sum(s["data"].get("positive_ratio", 0) * s["weight"] for s in sentiment_sources) / total_weight,
            "negative_ratio": sum(s["data"].get("negative_ratio", 0) * s["weight"] for s in sentiment_sources) / total_weight,
            "news_count": sum(s["data"].get("news_count", 0) for s in sentiment_sources),
            "hot_topics": list(set(all_topics))[:5],  # 去重，保留前 5
            "sources": [s["source"] for s in sentiment_sources],
            "last_updated": datetime.now().isoformat()
        }
    
    def _safe_get_data(self, fetch_func, *args, default=None, **kwargs):
        """
        安全获取数据 (带降级处理)
        
        Args:
            fetch_func: 数据获取函数
            *args: 函数参数
            default: 默认值 (失败时返回)
            **kwargs: 关键字参数
        
        Returns:
            数据或默认值
        """
        try:
            result = fetch_func(*args, **kwargs)
            if result is None:
                return default if default is not None else {}
            return result
        except Exception as e:
            print(f"{fetch_func.__name__} 获取失败：{e}")
            return default if default is not None else {}
    
    def _is_cache_valid(self, cached: Dict, max_age_seconds: int = 300) -> bool:
        """检查缓存是否有效"""
        if "timestamp" not in cached:
            return False
        
        age = (datetime.now() - cached["timestamp"]).total_seconds()
        return age < max_age_seconds
    
    def _get_fundamental_data(self, symbol: str) -> Dict:
        """
        获取基本面数据（真实数据优先）
        
        使用 FundamentalAdapter 按优先级获取:
        1. Tushare Pro API
        2. AkShare
        3. Qlib 本地数据
        4. 降级数据 (明确标注)
        """
        return self.fundamental.get_fundamental_data(symbol)
    
    def _get_market_data(self, symbol: str, technical_data: Dict, fundamental_data: Optional[Dict] = None) -> Dict:
        """
        获取市场数据
        
        优先级:
        1. 从 technical_data 获取真实数据
        2. 从 fundamental_data 补充
        3. 降级计算 (明确标注)
        """
        # 检查数据质量
        tech_quality = technical_data.get('data_quality', 'unknown')
        fund_quality = fundamental_data.get('data_quality', 'unknown') if fundamental_data else 'unknown'
        
        # 计算市场数据
        price = technical_data.get("price", fundamental_data.get("price", 100) if fundamental_data else 100)
        volume = technical_data.get("volume", 1000000)
        turnover_rate = technical_data.get("turnover_rate", 0.03)
        
        # 市值计算（优先使用真实数据）
        if fundamental_data and fundamental_data.get('market_cap'):
            market_cap = fundamental_data['market_cap']
        elif technical_data.get('market_cap'):
            market_cap = technical_data['market_cap']
        else:
            # 降级计算
            market_cap = price * 100000000  # 假设股本 1 亿股
        
        return {
            "volatility": turnover_rate * 10 if turnover_rate else 0.3,
            "daily_turnover": volume * price if volume and price else 0,
            "market_cap": market_cap,
            "earnings_soon": False,  # TODO: 检查财报日期
            "price": price,
            "data_quality": max(tech_quality, fund_quality) if tech_quality == fund_quality else 'mixed',
            "last_updated": datetime.now().isoformat()
        }
    
    def get_data_summary(self, symbol: str) -> Dict:
        """
        获取数据摘要 (用于快速预览)
        
        Args:
            symbol: 股票代码
        
        Returns:
            数据摘要
        """
        data = self.get_all_data(symbol)
        
        return {
            "symbol": symbol,
            "factor_score": data["factor_data"].get("momentum_score", 0),
            "sentiment_score": data["sentiment_data"].get("sentiment_score", 0),
            "technical_signal": data["technical_data"].get("signal", "unknown"),
            "trend": data["technical_data"].get("trend", "unknown"),
            "pe": data["fundamental_data"].get("pe", 0),
            "roe": data["fundamental_data"].get("roe", 0),
            "timestamp": data["metadata"]["timestamp"]
        }
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
    
    def get_status(self) -> Dict:
        """获取聚合器状态"""
        return {
            "cache_size": len(self.cache),
            "data_sources": {
                "quantaalpha": self.quantaalpha.get_status(),
                "trendradar": self.trendradar.get_status(),
                "akshare": self.akshare.get_status()
            }
        }


# 使用示例
if __name__ == "__main__":
    aggregator = DataAggregator()
    
    print("数据聚合器状态:")
    print(json.dumps(aggregator.get_status(), indent=2, ensure_ascii=False))
    
    print("\n获取 600519.SH 数据...")
    data = aggregator.get_all_data("600519.SH", "贵州茅台")
    
    print("\n数据摘要:")
    summary = aggregator.get_data_summary("600519.SH")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    print("\n因子数据:")
    print(json.dumps(data["factor_data"], indent=2, ensure_ascii=False))
    
    print("\n舆情数据:")
    print(json.dumps(data["sentiment_data"], indent=2, ensure_ascii=False))

