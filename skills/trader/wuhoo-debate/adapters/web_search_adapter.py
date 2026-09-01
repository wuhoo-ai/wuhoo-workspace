#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Search 舆情适配器

使用 Tavily 或 Jina AI API 搜索实时舆情信息
作为 TrendRadar 的补充数据源
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path


class WebSearchSentimentAdapter:
    """
    基于 Web Search 的舆情适配器
    
    数据源:
    - Tavily AI (优先)
    - Jina AI Search (备选)
    """
    
    def __init__(
        self,
        tavily_api_key: Optional[str] = None,
        jina_api_key: Optional[str] = None,
        max_results: int = 10
    ):
        self.max_results = max_results
        
        # 加载 API Key
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.jina_api_key = jina_api_key or os.getenv("JINA_API_KEY")
        
        # 优先级：Tavily > Jina
        self.primary_source = "tavily" if self.tavily_api_key else "jina"
        
        # 缓存
        self.cache = {}
        self.cache_ttl = 600  # 10 分钟
    
    def get_sentiment_data(self, symbol: str, name: str) -> Dict[str, Any]:
        """
        获取舆情数据
        
        Args:
            symbol: 股票代码 (如 "301029.SZ")
            name: 股票名称 (如 "怡合达")
        
        Returns:
            舆情数据字典
        """
        cache_key = f"{symbol}_{name}"
        
        # 检查缓存
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]["data"]
        
        # 构建搜索查询
        queries = self._build_search_queries(symbol, name)
        
        # 获取搜索结果
        all_results = []
        for query in queries:
            results = self._search(query)
            if results:
                all_results.extend(results)
        
        # 分析情感
        sentiment_analysis = self._analyze_sentiment(all_results)
        
        # 构建返回数据
        sentiment_data = {
            "source": f"web_search ({self.primary_source})",
            "timestamp": datetime.now().isoformat(),
            "sentiment_score": sentiment_analysis["score"],
            "sentiment_label": sentiment_analysis["label"],
            "positive_ratio": sentiment_analysis["positive_ratio"],
            "negative_ratio": sentiment_analysis["negative_ratio"],
            "neutral_ratio": sentiment_analysis["neutral_ratio"],
            "news_count": len(all_results),
            "hot_topics": self._extract_hot_topics(all_results),
            "recent_news": self._format_recent_news(all_results[:5]),
            "search_queries": queries,
            "raw_results": all_results[:10]  # 保留前 10 条原始结果
        }
        
        # 更新缓存
        self.cache[cache_key] = {
            "data": sentiment_data,
            "timestamp": datetime.now()
        }
        
        return sentiment_data
    
    def _build_search_queries(self, symbol: str, name: str) -> List[str]:
        """构建搜索查询"""
        # 提取股票名称 (去除后缀)
        stock_name = name.split("(")[0].strip() if "(" in name else name
        
        queries = [
            f"{stock_name} 股票 最新新闻 2026",
            f"{stock_name} {symbol} 股价 分析",
            f"{stock_name} 财报 业绩 公告",
            f"{stock_name} 利好 利空 消息",
        ]
        
        return queries
    
    def _search(self, query: str) -> List[Dict[str, Any]]:
        """执行搜索"""
        if self.primary_source == "tavily":
            return self._search_tavily(query)
        else:
            return self._search_jina(query)
    
    def _search_tavily(self, query: str) -> List[Dict[str, Any]]:
        """使用 Tavily API 搜索"""
        url = "https://api.tavily.com/search"
        
        payload = {
            "query": query,
            "api_key": self.tavily_api_key,
            "max_results": self.max_results,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "days": 7  # 最近 7 天
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for result in data.get("results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "published_date": result.get("published_date", ""),
                    "source": "tavily"
                })
            
            return results
            
        except Exception as e:
            print(f"Tavily 搜索失败：{e}")
            return []
    
    def _search_jina(self, query: str) -> List[Dict[str, Any]]:
        """使用 Jina AI API 搜索"""
        url = "https://s.jina.ai/"
        
        headers = {
            "Authorization": f"Bearer {self.jina_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "q": query,
            "count": self.max_results,
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            search_results = data.get("data", []) or []
            for result in search_results:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("snippet", result.get("description", "")),
                    "published_date": result.get("date", result.get("published", "")),
                    "source": "jina"
                })
            
            return results
            
        except Exception as e:
            print(f"Jina 搜索失败：{e}")
            return []
    
    def _analyze_sentiment(self, results: List[Dict]) -> Dict[str, Any]:
        """
        分析搜索结果的情感倾向
        
        简化版：基于关键词匹配
        TODO: 使用 LLM 进行更准确的情感分析
        """
        positive_keywords = [
            "利好", "上涨", "突破", "增长", "超预期", "买入", "推荐",
            "业绩", "盈利", "创新高", "强势", "机会", "看好"
        ]
        
        negative_keywords = [
            "利空", "下跌", "跌破", "下滑", "不及预期", "卖出", "风险",
            "亏损", "新低", "弱势", "警惕", "担忧", "回调"
        ]
        
        positive_count = 0
        negative_count = 0
        
        for result in results:
            content = (result.get("title", "") + " " + result.get("content", "")).lower()
            
            for kw in positive_keywords:
                if kw in content:
                    positive_count += 1
                    break
            
            for kw in negative_keywords:
                if kw in content:
                    negative_count += 1
                    break
        
        total = positive_count + negative_count
        if total == 0:
            score = 0.0
            label = "neutral"
        else:
            score = (positive_count - negative_count) / total
            if score > 0.2:
                label = "positive"
            elif score < -0.2:
                label = "negative"
            else:
                label = "neutral"
        
        return {
            "score": round(score, 3),
            "label": label,
            "positive_ratio": round(positive_count / max(total, 1), 3),
            "negative_ratio": round(negative_count / max(total, 1), 3),
            "neutral_ratio": round(1 - positive_count / max(total, 1) - negative_count / max(total, 1), 3)
        }
    
    def _extract_hot_topics(self, results: List[Dict]) -> List[str]:
        """提取热点话题"""
        # 简化版：提取高频词
        # TODO: 使用更智能的话题提取
        topics = []
        
        for result in results[:5]:
            title = result.get("title", "")
            if len(title) > 10:
                topics.append(title[:50])
        
        return topics[:5]
    
    def _format_recent_news(self, results: List[Dict]) -> List[Dict]:
        """格式化最近新闻"""
        formatted = []
        
        for result in results:
            formatted.append({
                "title": result.get("title", ""),
                "source": result.get("source", ""),
                "url": result.get("url", ""),
                "published": result.get("published_date", "")
            })
        
        return formatted
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self.cache:
            return False
        
        cached = self.cache[cache_key]
        age = (datetime.now() - cached["timestamp"]).total_seconds()
        
        return age < self.cache_ttl
    
    def clear_cache(self):
        """清空缓存"""
        self.cache = {}
    
    def get_status(self) -> Dict[str, Any]:
        """获取适配器状态"""
        return {
            "primary_source": self.primary_source,
            "tavily_configured": bool(self.tavily_api_key),
            "jina_configured": bool(self.jina_api_key),
            "cache_size": len(self.cache),
            "max_results": self.max_results
        }


# 使用示例
if __name__ == "__main__":
    adapter = WebSearchSentimentAdapter()
    
    print("适配器状态:", adapter.get_status())
    print()
    
    sentiment = adapter.get_sentiment_data("301029.SZ", "怡合达")
    
    print("舆情评分:", sentiment["sentiment_score"])
    print("情感标签:", sentiment["sentiment_label"])
    print("新闻数量:", sentiment["news_count"])
    print("热点话题:")
    for topic in sentiment["hot_topics"]:
        print(f"  - {topic}")
