#!/usr/bin/env python3
"""
xiaohongshu_collector.py — 小红书世界杯内容采集器 v1.0
=====================================================
三层采集架构:
  1. Brave Search API (site:xiaohongshu.com) — 关键词搜索
  2. web_extract — 提取帖子全文 (需 Agent 调用)
  3. 本地 JSON 缓存 — 供 sentiment_analyzer 读取

使用方式:
  # 采集指定球队的小红书讨论
  python3.11 xiaohongshu_collector.py --teams "Argentina,France,Brazil"
  
  # 采集世界杯通用关键词
  python3.11 xiaohongshu_collector.py --keywords "世界杯,伤病,预测"
  
  # 采集全部 48 队 (耗时较长)
  python3.11 xiaohongshu_collector.py --all
  
  # 输出路径
  python3.11 xiaohongshu_collector.py --teams "Argentina" -o /tmp/xhs.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

import requests

# 默认配置
DEFAULT_CACHE = Path(__file__).parent.parent / "data" / "xhs_sentiment_cache.json"
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# 小红书搜索模板 - Brave Search 不支持 site: 操作符，改用关键词定位
XHS_SEARCH_TEMPLATE = "xiaohongshu.com 世界杯 {query}"

# WC2026 48 支球队 (中文名映射)
TEAM_NAMES_ZH = {
    # UEFA
    "Spain": "西班牙", "France": "法国", "England": "英格兰", "Portugal": "葡萄牙",
    "Netherlands": "荷兰", "Germany": "德国", "Italy": "意大利", "Belgium": "比利时",
    "Croatia": "克罗地亚", "Denmark": "丹麦", "Switzerland": "瑞士", "Austria": "奥地利",
    "Norway": "挪威", "Sweden": "瑞典", "Poland": "波兰", "Ukraine": "乌克兰",
    "Serbia": "塞尔维亚", "Scotland": "苏格兰", "Czech Republic": "捷克",
    "Hungary": "匈牙利", "Wales": "威尔士", "Slovenia": "斯洛文尼亚",
    "Ireland": "爱尔兰", "Slovakia": "斯洛伐克",
    # CONMEBOL
    "Argentina": "阿根廷", "Brazil": "巴西", "Colombia": "哥伦比亚",
    "Ecuador": "厄瓜多尔", "Uruguay": "乌拉圭", "Paraguay": "巴拉圭",
    "Peru": "秘鲁", "Venezuela": "委内瑞拉", "Chile": "智利", "Bolivia": "玻利维亚",
    # CAF
    "Senegal": "塞内加尔", "Morocco": "摩洛哥", "Nigeria": "尼日利亚",
    "Algeria": "阿尔及利亚", "Egypt": "埃及", "Ivory Coast": "科特迪瓦",
    "DR Congo": "刚果民主共和国", "Tunisia": "突尼斯", "Cameroon": "喀麦隆",
    "Ghana": "加纳", "South Africa": "南非", "Cape Verde": "佛得角",
    # AFC
    "Japan": "日本", "South Korea": "韩国", "Iran": "伊朗", "Australia": "澳大利亚",
    "Uzbekistan": "乌兹别克斯坦", "Saudi Arabia": "沙特阿拉伯",
    "Iraq": "伊拉克", "Jordan": "约旦", "Qatar": "卡塔尔",
    # CONCACAF
    "Mexico": "墨西哥", "United States": "美国", "Canada": "加拿大",
    "Panama": "巴拿马", "Costa Rica": "哥斯达黎加", "Haiti": "海地",
    "Jamaica": "牙买加", "Curacao": "库拉索",
    # OFC
    "New Zealand": "新西兰",
}

# WC2026 专用搜索关键词 (中英文混合，覆盖主要讨论维度)
WC_KEYWORDS = [
    "世界杯", "World Cup 2026", "美加墨", "WC2026",
    "范志毅 世界杯", "谢晖 世界杯",
    "世界杯 预测", "世界杯 分析", "世界杯 前瞻",
    "世界杯 伤病", "世界杯 阵容", "世界杯 大名单",
    "世界杯 冷门", "世界杯 黑马",
]


def load_api_key() -> str:
    """加载 Brave API Key"""
    # 1. 环境变量
    key = os.environ.get("BRAVE_API_KEY", "")
    if key:
        return key
    # 2. Hermes .env
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("BRAVE_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def search_xiaohongshu(query: str, api_key: str, limit: int = 10) -> List[Dict]:
    """通过 Brave Search 搜索小红书内容"""
    full_query = XHS_SEARCH_TEMPLATE.format(query=query)
    
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    
    params = {
        "q": full_query,
        "count": min(limit, 20),
    }
    
    try:
        resp = requests.get(BRAVE_SEARCH_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "url": item.get("url", ""),
                "date": item.get("age", ""),
                "source": "xiaohongshu",
            })
        return results
    except Exception as e:
        print(f"  ⚠️ Brave Search 失败 ({query}): {e}", file=sys.stderr)
        return []


def collect_team_news(teams: List[str], api_key: str) -> Dict[str, List[Dict]]:
    """采集指定球队的小红书讨论"""
    results = {}
    
    for team in teams:
        zh_name = TEAM_NAMES_ZH.get(team, team)
        query = f"世界杯 {zh_name} {team}"
        
        print(f"  🔍 搜索: {team} ({zh_name})...", file=sys.stderr)
        items = search_xiaohongshu(query, api_key, limit=8)
        
        # 添加球队标记
        for item in items:
            item["team"] = team
        
        results[team] = items
        print(f"     → {len(items)} 条结果", file=sys.stderr)
        
        # 速率限制: 1 req/s (Brave free tier)
        time.sleep(1.2)
    
    return results


def collect_keywords(keywords: List[str], api_key: str) -> List[Dict]:
    """采集指定关键词的小红书内容"""
    results = []
    
    for kw in keywords:
        print(f"  🔍 搜索: {kw}...", file=sys.stderr)
        items = search_xiaohongshu(f"世界杯 {kw}", api_key, limit=5)
        for item in items:
            item["keyword"] = kw
        results.extend(items)
        print(f"     → {len(items)} 条结果", file=sys.stderr)
        time.sleep(1.2)
    
    return results


def build_cache(
    teams: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    all_teams: bool = False,
    api_key: Optional[str] = None,
) -> Dict:
    """构建小红书情感缓存"""
    if api_key is None:
        api_key = load_api_key()
    
    if not api_key:
        print("❌ 未找到 Brave API Key", file=sys.stderr)
        return {"error": "no_api_key", "collected_at": datetime.now().isoformat()}
    
    cache = {
        "version": "1.0",
        "collected_at": datetime.now().isoformat(),
        "source": "xiaohongshu (via Brave Search)",
        "team_news": {},
        "keyword_news": [],
        "summary": {},
    }
    
    # 采集球队新闻
    if all_teams:
        teams = list(TEAM_NAMES_ZH.keys())
    elif teams is None:
        # 默认: 仅搜索热门球队 (节省 API 配额)
        teams = [
            "Argentina", "France", "Spain", "Brazil", "England",
            "Germany", "Portugal", "Netherlands", "Japan", "South Korea",
        ]
    
    if teams:
        print(f"📱 采集 {len(teams)} 支球队的小红书讨论...", file=sys.stderr)
        cache["team_news"] = collect_team_news(teams, api_key)
    
    # 采集通用关键词
    if keywords is None:
        keywords = WC_KEYWORDS[:5]  # 默认取前5个通用关键词
    
    if keywords:
        print(f"📱 采集 {len(keywords)} 个通用关键词...", file=sys.stderr)
        cache["keyword_news"] = collect_keywords(keywords, api_key)
    
    # 生成摘要
    total_articles = sum(len(v) for v in cache["team_news"].values())
    total_articles += len(cache["keyword_news"])
    teams_with_data = sum(1 for v in cache["team_news"].values() if v)
    
    cache["summary"] = {
        "total_articles": total_articles,
        "teams_covered": list(cache["team_news"].keys()),
        "teams_with_data": teams_with_data,
        "keywords_used": keywords,
    }
    
    print(f"\n✅ 采集完成: {total_articles} 篇文章, {teams_with_data}/{len(teams)} 队有数据", file=sys.stderr)
    
    return cache


def main():
    parser = argparse.ArgumentParser(description="小红书世界杯内容采集器")
    parser.add_argument("--teams", type=str, help="逗号分隔的球队名 (如 'Argentina,France')")
    parser.add_argument("--keywords", type=str, help="逗号分隔的关键词 (如 '伤病,预测')")
    parser.add_argument("--all", action="store_true", help="采集全部 48 队")
    parser.add_argument("-o", "--output", type=str, help="输出 JSON 路径")
    
    args = parser.parse_args()
    
    # 解析参数
    teams = [t.strip() for t in args.teams.split(",")] if args.teams else None
    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else None
    
    # 构建缓存
    cache = build_cache(teams=teams, keywords=keywords, all_teams=args.all)
    
    # 输出
    output_path = Path(args.output) if args.output else DEFAULT_CACHE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    print(f"💾 缓存已保存: {output_path}", file=sys.stderr)
    
    # 输出 JSON 到 stdout (供管道使用)
    if not args.output:
        print(json.dumps(cache["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
# DEPRECATED v4.0 — removed due to low XHS URL hit rate (12%). Kept for reference.
# See v4.1 SKILL.md for current architecture.
