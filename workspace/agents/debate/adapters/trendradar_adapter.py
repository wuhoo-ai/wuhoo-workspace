#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrendRadar Adapter - 舆情数据适配器

从 TrendRadar 系统获取热点舆情数据。
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta


class TrendRadarAdapter:
    """
    TrendRadar 舆情数据适配器
    
    功能:
    - 获取热点舆情数据
    - 分析股票相关度
    - 计算情绪评分
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化
        
        Args:
            data_dir: TrendRadar 数据目录
        """
        if data_dir is None:
            possible_paths = [
                Path.home() / ".openclaw/data/trendradar",
                Path.home() / ".openclaw/workspace/projects/TrendRadar/output",
                Path("/home/admin/.openclaw/data/trendradar")
            ]
            
            for path in possible_paths:
                if path.exists():
                    self.data_dir = path
                    break
            else:
                self.data_dir = None
        
        self.cache: Dict[str, Dict] = {}
    
    def get_sentiment_data(self, symbol: str, company_name: Optional[str] = None) -> Dict:
        """
        获取股票舆情数据
        
        Args:
            symbol: 股票代码
            company_name: 公司名称 (可选，用于更精确匹配)
        
        Returns:
            舆情数据字典
        """
        cache_key = f"{symbol}_{company_name or 'unknown'}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 尝试从 TrendRadar 输出目录读取
        if self.data_dir:
            data = self._load_trendradar_data(symbol, company_name)
            if data:
                self.cache[cache_key] = data
                return data
        
        # 返回模拟数据
        data = self._get_mock_sentiment(symbol, company_name)
        self.cache[cache_key] = data
        return data
    
    def _load_trendradar_data(self, symbol: str, company_name: Optional[str]) -> Optional[Dict]:
        """从 TrendRadar 加载真实数据"""
        if not self.data_dir:
            return None
        
        # 查找最新的输出文件
        output_dir = self.data_dir
        json_files = list(output_dir.glob("*.json"))
        
        if not json_files:
            return None
        
        # 读取最新文件
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 提取与股票相关的舆情
            return self._extract_stock_sentiment(data, symbol, company_name)
        except Exception as e:
            print(f"Error loading TrendRadar data: {e}")
            return None
    
    def _extract_stock_sentiment(self, data: Dict, symbol: str, company_name: Optional[str]) -> Dict:
        """从 TrendRadar 数据提取股票舆情"""
        # 简化实现
        # 实际应该搜索与股票/公司相关的新闻和热点
        
        keywords_to_check = [symbol, company_name] if company_name else [symbol]
        
        # 模拟实现
        return {
            "sentiment_score": 0.4,
            "hot_topics": ["AI", "芯片", "科技"],
            "news_count": 15,
            "positive_ratio": 0.65,
            "negative_ratio": 0.20,
            "neutral_ratio": 0.15,
            "trending_rank": 8,
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_mock_sentiment(self, symbol: str, company_name: Optional[str]) -> Dict:
        """生成模拟舆情数据"""
        hash_val = hash(symbol) % 100
        
        # 基于股票代码生成热点话题
        topics_pool = ["AI", "芯片", "新能源", "跨境电商", "直播", "量化交易", "5G", "半导体"]
        selected_topics = [topics_pool[hash_val % len(topics_pool)], 
                          topics_pool[(hash_val + 3) % len(topics_pool)]]
        
        sentiment = (hash_val % 100 - 50) / 100  # -0.5 to +0.5
        
        return {
            "sentiment_score": sentiment,
            "hot_topics": selected_topics,
            "news_count": 5 + (hash_val % 20),
            "positive_ratio": 0.4 + (hash_val % 40) / 100,
            "negative_ratio": 0.2 + (hash_val % 30) / 100,
            "neutral_ratio": 0.2,
            "trending_rank": 1 + (hash_val % 20),
            "last_updated": datetime.now().isoformat(),
            "note": "Mock data (TrendRadar not fully integrated)"
        }
    
    def get_hot_topics(self, limit: int = 10) -> List[Dict]:
        """
        获取当前热点话题
        
        Args:
            limit: 返回数量限制
        
        Returns:
            热点话题列表
        """
        if not self.data_dir:
            return self._get_mock_hot_topics(limit)
        
        # 尝试从 TrendRadar 读取
        # ... (实现略)
        
        return self._get_mock_hot_topics(limit)
    
    def _get_mock_hot_topics(self, limit: int) -> List[Dict]:
        """生成模拟热点"""
        topics = [
            {"topic": "AI", "rank": 1, "heat": 95},
            {"topic": "芯片", "rank": 2, "heat": 88},
            {"topic": "量化交易", "rank": 3, "heat": 75},
            {"topic": "跨境电商", "rank": 4, "heat": 68},
            {"topic": "新能源", "rank": 5, "heat": 62},
            {"topic": "直播", "rank": 6, "heat": 55},
            {"topic": "5G", "rank": 7, "heat": 48},
            {"topic": "半导体", "rank": 8, "heat": 42},
        ]
        return topics[:limit]
    
    def analyze_sentiment_trend(self, symbol: str, days: int = 7) -> Dict:
        """
        分析舆情趋势
        
        Args:
            symbol: 股票代码
            days: 分析天数
        
        Returns:
            趋势分析结果
        """
        # 简化实现
        return {
            "symbol": symbol,
            "period_days": days,
            "trend": "improving" if hash(symbol) % 2 == 0 else "declining",
            "avg_sentiment": 0.3 + (hash(symbol) % 40) / 100,
            "volatility": 0.15,
            "peak_day": "2026-03-15",
            "peak_sentiment": 0.65
        }
    
    def is_available(self) -> bool:
        """检查 TrendRadar 数据是否可用"""
        return self.data_dir is not None and self.data_dir.exists()
    
    def get_status(self) -> Dict:
        """获取适配器状态"""
        return {
            "available": self.is_available(),
            "data_dir": str(self.data_dir) if self.data_dir else None,
            "cache_size": len(self.cache)
        }


# 使用示例
if __name__ == "__main__":
    adapter = TrendRadarAdapter()
    
    print("TrendRadar 状态:", adapter.get_status())
    print("\n热点话题:")
    topics = adapter.get_hot_topics(5)
    for topic in topics:
        print(f"  #{topic['rank']} {topic['topic']} (热度：{topic['heat']})")
    
    print("\n600519.SH 舆情数据:")
    sentiment = adapter.get_sentiment_data("600519.SH", "贵州茅台")
    print(json.dumps(sentiment, indent=2, ensure_ascii=False))
