#!/usr/bin/env python3
"""
wuhoo-news-rss — RSS 资讯采集引擎
================================
功能：
  1. 从 RSSHub + 原生 RSS 源拉取资讯
  2. 去重存储到 SQLite (FTS5 全文搜索)
  3. 按类别/标签/关键词检索
  4. 热点新闻评分 + 关键词告警

使用方式：
  python3.11 fetcher.py              # 拉取所有源
  python3.11 fetcher.py --category AI # 只拉取 AI 类
  python3.11 fetcher.py --list        # 列出所有源状态
  python3.11 fetcher.py --search "量化交易"  # 搜索
  python3.11 fetcher.py --top 10      # 今日 TOP 10
  python3.11 fetcher.py --keywords "AI,英伟达"  # 关键词告警
"""

import sys
if sys.version_info < (3, 11):
    print(f"❌ Python {sys.version} 不受支持，需要 Python 3.11+")
    print(f"   请使用: /usr/bin/python3.11 {sys.argv[0]} {' '.join(sys.argv[1:])}")
    sys.exit(1)

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import feedparser
import sqlite3
import yaml

# 路径设置
SKILL_DIR = Path(__file__).parent.parent  # src/ 的父目录
CONFIG_PATH = SKILL_DIR / "feeds" / "config.yaml"
DATA_DIR = SKILL_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


# ============================================================
# 配置加载
# ============================================================
def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# SQLite 数据库
# ============================================================
def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 主表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_name   TEXT NOT NULL,
            source_url  TEXT NOT NULL,
            title       TEXT NOT NULL,
            summary     TEXT,
            content     TEXT,
            link        TEXT,
            author      TEXT,
            pub_date    TEXT,
            fetched_at  TEXT NOT NULL,
            category    TEXT NOT NULL,
            tags        TEXT,          -- JSON array
            hot_score   REAL DEFAULT 0,
            is_alert    INTEGER DEFAULT 0,
            alert_keywords TEXT,       -- 命中的告警关键词
            hash        TEXT UNIQUE    -- URL MD5 去重
        )
    """)

    # FTS5 全文搜索虚拟表
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
            title, summary, content,
            content=articles,
            content_rowid=id,
            tokenize='unicode61'
        )
    """)

    # 触发器：自动同步 FTS
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles
        BEGIN
            INSERT INTO articles_fts(rowid, title, summary, content)
            VALUES (new.id, new.title, new.summary, new.content);
        END
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles
        BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, summary, content)
            VALUES ('delete', old.id, old.title, old.summary, old.content);
        END
    """)

    conn.commit()
    return conn


def article_hash(link: str, title: str) -> str:
    """生成去重 hash"""
    text = link or title
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()


def insert_article(conn: sqlite3.Connection, article: dict) -> bool:
    """插入文章，返回是否是新文章"""
    try:
        conn.execute("""
            INSERT OR IGNORE INTO articles
            (feed_name, source_url, title, summary, content, link,
             author, pub_date, fetched_at, category, tags, hash,
             hot_score, is_alert, alert_keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article["feed_name"],
            article["source_url"],
            article["title"],
            article.get("summary", ""),
            article.get("content", ""),
            article.get("link", ""),
            article.get("author", ""),
            article.get("pub_date"),
            datetime.now().isoformat(),
            article["category"],
            json.dumps(article.get("tags", []), ensure_ascii=False),
            article["hash"],
            article.get("hot_score", 0),
            article.get("is_alert", 0),
            article.get("alert_keywords", ""),
        ))
        return conn.total_changes > 0  # 有变化 = 新文章
    except sqlite3.IntegrityError:
        return False  # 重复


# ============================================================
# RSS 拉取
# ============================================================
def fetch_feed(feed_cfg: dict, timeout: int = 30, retries: int = 3) -> Optional[dict]:
    """拉取单个 RSS 源"""
    url = feed_cfg["url"]
    name = feed_cfg["name"]

    for attempt in range(retries):
        try:
            headers = {"User-Agent": "wuhoo-news-rss/1.0 (+https://github.com/wuhoo/openclaw)"}
            result = feedparser.parse(url, request_headers=headers)

            if result.bozo and not result.entries:
                print(f"  ⚠️  {name}: 解析失败 ({result.bozo_exception})")
                return None

            return {
                "feed_name": name,
                "source_url": url,
                "category": feed_cfg.get("category", "综合"),
                "tags": feed_cfg.get("tags", []),
                "entries": result.entries,
                "feed_title": result.feed.get("title", name),
            }
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  ❌ {name}: 拉取失败 ({e})")
                return None

    return None


def parse_entry(entry: dict) -> dict:
    """解析 feedparser 条目为统一格式"""
    # 提取内容
    summary = ""
    content = ""

    if hasattr(entry, "summary"):
        summary = entry.summary
    elif hasattr(entry, "description"):
        summary = entry.description

    if hasattr(entry, "content") and entry.content:
        content = entry.content[0].get("value", "")

    # 提取时间
    pub_date = None
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        pub_date = time.strftime("%Y-%m-%d %H:%M:%S", entry.published_parsed)
    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        pub_date = time.strftime("%Y-%m-%d %H:%M:%S", entry.updated_parsed)

    # 提取作者
    author = ""
    if hasattr(entry, "author"):
        author = entry.author
    elif hasattr(entry, "dc_creator"):
        author = entry.dc_creator

    return {
        "title": entry.get("title", "无标题"),
        "link": entry.get("link", ""),
        "summary": summary[:500] if summary else "",
        "content": content[:2000] if content else "",
        "author": author,
        "pub_date": pub_date,
    }


# ============================================================
# 热点评分 & 关键词告警
# ============================================================

def load_alert_keywords(config: dict) -> List[str]:
    """从配置加载告警关键词"""
    keywords = config.get("alert_keywords", [])
    if not keywords:
        # 向后兼容：如果配置中没有，使用硬编码默认值
        return [
            "量化交易", "quantitative trading", "algo trading", "算法交易", "alpha", "阿尔法", "因子", "回测", "策略",
            "人工智能", "大模型", "LLM", "GPT", "Claude", "OpenAI", "deep learning", "transformer",
            "NVIDIA", "英伟达", "GPU", "芯片", "semiconductor", "chip",
            "跨境电商", "cross-border", "Amazon", "亚马逊", "SHEIN", "Temu", "TikTok Shop",
            "涨停", "跌停", "surge", "plunge", "熔断", "降息", "加息", "rate cut", "rate hike",
            "财报", "earnings", "revenue", "营收", "净利润", "net profit",
        ]
    return keywords


def load_feed_weights(config: dict) -> Dict[str, float]:
    """从配置加载 Feed 源权重（默认权重按类别分配）"""
    weights = config.get("feed_weights", {})
    if weights:
        return weights

    # 默认权重：按源质量和信号密度
    defaults = {
        # 财经核心源（高信号密度）
        "Financial Times": 10, "华尔街见闻": 9, "华尔街见闻热门": 9,
        "路透社国际": 9, "NYT Business": 8, "BBC Business": 8,
        "第一财经": 8, "格隆汇": 8, "凤凰网财经": 7, "联合早报": 7,
        # 科技/AI（中高信号）
        "IT之家": 7, "36氪": 7, "虎嗅": 7, "TechCrunch": 8,
        "The Verge": 8, "Ars Technica": 7, "Hacker News 100+": 6,
        "Hacker News": 5, "Solidot 奇点资讯": 5,
        "OpenAI Blog": 9, "HuggingFace Blog": 8, "arXiv AI 论文": 5,
        "雷锋网": 6, "少数派": 5, "Engadget": 6,
        # 综合新闻
        "BBC World": 7, "卫报国际": 7, "美联社": 8,
        "德国之声": 5, "半岛电视台": 4,
        # FeedX 国际中文
        "纽约时报中文": 7, "BBC 中文": 7, "日经中文网": 7,
        "中央社": 6, "德国之声中文": 5, "法国国际广播电台": 5,
        "朝鲜日报中文": 5, "俄罗斯卫星通讯社": 4,
        # 投资/量化
        "arXiv 量化金融": 4, "知乎日报": 3,
        # 足球（投资类简报中权重为0，仅在体育简报中使用）
        "BBC Sport Football": 0, "懂球帝早报": 0, "Sky Sports Football": 0,
        "The Guardian Football": 0, "SoccerNews": 0,
        "World Soccer Talk": 0, "Football Italia": 0,
        "Football Rankings": 0, "Breaking The Lines": 0,
        # 博客（低频低信号）
        "阮一峰": 4, "云风 BLOG": 2, "唐巧": 2,
        "B站排行榜": 2, "Telegram 频道": 2,
    }
    return defaults


# 扩展关键词表 (200+ keywords covering broader topics)
EXPANDED_KEYWORDS = [
    # ── 量化/交易 ──
    "量化交易", "quantitative trading", "algo trading", "算法交易", "alpha", "阿尔法",
    "因子", "回测", "策略", "高频交易", "HFT", "market making", "做市",
    # ── AI / 大模型 ──
    "人工智能", "大模型", "LLM", "GPT", "Claude", "OpenAI", "DeepMind", "Gemini",
    "transformer", "fine-tuning", "RLHF", "alignment", "agent", "AI agent",
    "deep learning", "machine learning", "神经网络", "推理", "inference",
    "foundation model", "基座模型", "多模态", "multimodal",
    # ── 半导体 / 芯片 ──
    "NVIDIA", "英伟达", "GPU", "芯片", "semiconductor", "chip", "HBM",
    "TSMC", "台积电", "Intel", "AMD", "光刻", "lithography", "ASML",
    "制程", "3nm", "2nm", "先进封装", "chiplet",
    # ── 电商 / 跨境 ──
    "跨境电商", "cross-border", "Amazon", "亚马逊", "SHEIN", "Temu", "TikTok Shop",
    "Shopify", "独立站", "DTC",
    # ── 市场 / 宏观 ──
    "涨停", "跌停", "surge", "plunge", "熔断", "降息", "加息", "rate cut", "rate hike",
    "IPO", "上市", "SPAC", "并购", "acquisition", "收购", "私有化",
    "通胀", "inflation", "CPI", "PPI", "GDP", "PMI", "非农",
    "美联储", "Fed", "ECB", "央行", "central bank", "缩表", "QE",
    "关税", "tariff", "制裁", "sanction", "贸易战", "trade war",
    # ── 公司 / 财报 ──
    "财报", "earnings", "revenue", "营收", "净利润", "net profit", "毛利率",
    "市值", "market cap", "估值", "valuation", "PE", "PB",
    "裁员", "layoff", "重组", "restructuring",
    # ── 科技 / 产业 ──
    "自动驾驶", "autonomous driving", "电动车", "EV", "Tesla", "特斯拉",
    "机器人", "robot", "具身智能", "embodied AI",
    "区块链", "blockchain", "crypto", "Bitcoin", "比特币", "Ethereum",
    "元宇宙", "metaverse", "AR", "VR", "Vision Pro",
    "量子计算", "quantum computing", "量子",
    "网络安全", "cybersecurity", "数据泄露", "data breach",
    # ── A股/港股/美股 个股 ──
    "腾讯", "阿里", "百度", "字节", "美团", "拼多多", "京东", "小米",
    "Apple", "苹果", "Microsoft", "微软", "Google", "谷歌", "Meta",
    "Amazon", "Netflix", "Tesla", "比亚迪", "宁德时代",
    # ── 行业热点 ──
    "新能源", "光伏", "solar", "风电", "储能", "电池",
    "创新药", "biotech", "CXO", "医疗器械",
    "房地产", "real estate", "楼市", "房价",
]


def calc_hot_score(entry: dict, feed_cfg: dict, keywords: Optional[List[str]] = None,
                   feed_weights: Optional[Dict[str, float]] = None) -> Tuple[float, List[str]]:
    """计算热点评分 + 检查告警关键词

    三层打分：
    1. Feed 源基础权重 (1-10) → 基础分
    2. 关键词增强 → 每个匹配 +3 分
    3. 多源覆盖 → fetch_all() 中额外处理
    """
    score = 0.0
    hit_keywords = []

    # 第 1 层：Feed 源基础权重
    feed_name = feed_cfg.get("name", "")
    if feed_weights:
        base_weight = feed_weights.get(feed_name, 3.0)  # 未配置默认 3 分
        score += base_weight

    # 第 2 层：关键词增强（使用扩展关键词表）
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    text = f"{title} {summary}".lower()

    all_kw = list(keywords or []) + EXPANDED_KEYWORDS
    # 去重
    seen_kw = set()
    for kw in all_kw:
        kw_lower = kw.lower()
        if kw_lower in seen_kw:
            continue
        seen_kw.add(kw_lower)
        # 使用词边界匹配，避免 PE 匹配到 "Ramos" 中的 "pe"
        pattern = re.compile(r'\b' + re.escape(kw_lower) + r'\b', re.IGNORECASE)
        if pattern.search(text):
            hit_keywords.append(kw)
            score += 3  # 每个关键词 +3 分

    return score, hit_keywords


def _fuzzy_normalize(title: str) -> str:
    """模糊归一化标题用于多源匹配"""
    t = title.lower().strip()
    # 去除常见源前缀
    t = re.sub(r'^(it之家\s*\d+\s*月\s*\d+\s*日\s*消息[，,]?)', '', t)
    t = re.sub(r'^36氪获悉[，,]?', '', t)
    t = re.sub(r'^\d+月\d+日\|?', '', t)
    # 去除标点符号差异
    t = re.sub(r'[：:，,。！!？?\s]+', ' ', t)
    # 取前 40 个字符作为指纹
    return t.strip()[:40]


# ============================================================
# 主流程
# ============================================================
def fetch_all(config: dict, conn: sqlite3.Connection, category_filter: Optional[str] = None):
    """拉取所有源"""
    feeds = config["feeds"]
    settings = config.get("settings", {})
    max_items = settings.get("max_items_per_feed", 50)
    timeout = settings.get("timeout_seconds", 30)
    retries = settings.get("retry_count", 3)
    keywords = load_alert_keywords(config)
    feed_weights = load_feed_weights(config)

    stats = {"total": 0, "new": 0, "dup": 0, "failed": 0}
    all_titles_raw = []  # 用于模糊多源覆盖评分

    # 第一遍：收集所有标题
    print(f"📡 开始拉取 {len(feeds)} 个 RSS 源...")
    feed_results = []

    for feed_cfg in feeds:
        if category_filter and feed_cfg.get("category") != category_filter:
            continue

        print(f"  🔄 {feed_cfg['name']} ({feed_cfg['category']})...", end=" ")
        result = fetch_feed(feed_cfg, timeout, retries)

        if result and result["entries"]:
            entries_count = len(result["entries"])
            print(f"✅ {entries_count} 条")
            feed_results.append(result)
            stats["total"] += entries_count
            all_titles_raw.extend([e.get("title", "") for e in result["entries"]])
        else:
            stats["failed"] += 1

    # 构建模糊标题计数器（用于多源覆盖判断）
    fuzzy_counter = Counter()
    for title in all_titles_raw:
        if title and title != "无标题":
            fuzzy_key = _fuzzy_normalize(title)
            if fuzzy_key:
                fuzzy_counter[fuzzy_key] += 1

    # 第二遍：存储 + 评分
    print(f"\n📦 存储到数据库...")

    for result in feed_results:
        for entry in result["entries"][:max_items]:
            parsed = parse_entry(entry)
            parsed["feed_name"] = result["feed_name"]
            parsed["source_url"] = result["source_url"]
            parsed["category"] = result["category"]
            parsed["tags"] = result["tags"]
            parsed["hash"] = article_hash(parsed["link"], parsed["title"])

            # 热点评分（三层：Feed权重 + 关键词增强 + 模糊多源覆盖）
            score, hit_keywords = calc_hot_score(parsed, result, keywords, feed_weights)

            # 模糊多源覆盖加分
            fuzzy_key = _fuzzy_normalize(parsed["title"])
            source_count = fuzzy_counter.get(fuzzy_key, 1)
            if source_count > 1:
                score += (source_count - 1) * 8  # 每个额外源 +8 分

            parsed["hot_score"] = score
            parsed["is_alert"] = 1 if hit_keywords else 0
            parsed["alert_keywords"] = ",".join(hit_keywords) if hit_keywords else ""

            is_new = insert_article(conn, parsed)
            if is_new:
                stats["new"] += 1
            else:
                stats["dup"] += 1

    conn.commit()
    return stats


def search_articles(conn: sqlite3.Connection, keyword: str, limit: int = 10,
                    category: Optional[str] = None, hours: Optional[int] = None):
    """搜索文章"""
    query = """
        SELECT a.*,
               (SELECT count(*) FROM articles a2 WHERE a2.title = a.title) as source_count
        FROM articles a
        WHERE a.title LIKE ? OR a.summary LIKE ?
    """
    params = [f"%{keyword}%", f"%{keyword}%"]

    if category:
        query += " AND a.category = ?"
        params.append(category)

    if hours:
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        query += " AND a.fetched_at > ?"
        params.append(cutoff)

    query += " ORDER BY a.hot_score DESC, a.fetched_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def fts_search(conn: sqlite3.Connection, query: str, limit: int = 10):
    """FTS5 全文搜索"""
    rows = conn.execute("""
        SELECT a.* FROM articles a
        JOIN articles_fts fts ON a.id = fts.rowid
        WHERE articles_fts MATCH ?
        ORDER BY rank LIMIT ?
    """, (query, limit)).fetchall()
    return [dict(r) for r in rows]


def top_articles(conn: sqlite3.Connection, n: int = 20, hours: int = 24,
                 category: Optional[str] = None):
    """获取热门文章"""
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    query = """
        SELECT * FROM articles
        WHERE fetched_at > ?
    """
    params = [cutoff]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY hot_score DESC, fetched_at DESC LIMIT ?"
    params.append(n)

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def list_feeds(config: dict, conn: sqlite3.Connection):
    """列出所有源状态"""
    feeds = config["feeds"]
    print(f"\n{'='*70}")
    print(f"RSS 源状态")
    print(f"{'='*70}")
    print(f"{'源名称':<20} {'类别':<8} {'文章数':>8} {'告警数':>8} {'状态':<6}")
    print(f"{'-'*70}")

    for feed in feeds:
        row = conn.execute(
            "SELECT count(*) as cnt, sum(is_alert) as alerts FROM articles WHERE feed_name = ?",
            (feed["name"],)
        ).fetchone()
        cnt = row["cnt"] if row else 0
        alerts = row["alerts"] if row and row["alerts"] else 0
        status = "✅" if cnt > 0 else "❌"
        print(f"{feed['name']:<20} {feed.get('category',''):<8} {cnt:>8} {alerts:>8} {status:<6}")


def format_article(article: dict) -> str:
    """格式化文章输出"""
    pub = (article.get("pub_date") or "")[:16]
    score = article.get("hot_score", 0)
    alert = "🔥" if article.get("is_alert") else ""
    source_count = article.get("source_count", 1)

    lines = [
        f"{alert} [{article['category']}] {article['title']}",
        f"   来源: {article['feed_name']} | 时间: {pub} | 热度: {score:.0f} | 覆盖: {source_count} 源",
    ]

    if article.get("alert_keywords"):
        lines.append(f"   关键词: {article['alert_keywords']}")

    if article.get("summary"):
        summary = article["summary"][:120].replace("\n", " ")
        lines.append(f"   摘要: {summary}...")

    if article.get("link"):
        lines.append(f"   链接: {article['link']}")

    lines.append("")
    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="wuhoo-news-rss 采集引擎")
    parser.add_argument("--fetch", action="store_true", help="拉取所有源")
    parser.add_argument("--category", type=str, help="按类别过滤 (AI/科技/财经/投资/跨境电商/综合)")
    parser.add_argument("--list", action="store_true", help="列出所有源状态")
    parser.add_argument("--search", type=str, help="关键词搜索")
    parser.add_argument("--top", type=int, nargs="?", const=20, help="热门文章 (默认 TOP 20)")
    parser.add_argument("--keywords", type=str, help="告警关键词 (逗号分隔)")
    parser.add_argument("--hours", type=int, default=24, help="时间范围 (小时, 默认 24)")
    parser.add_argument("--limit", type=int, default=10, help="返回条数 (默认 10)")
    parser.add_argument("--fts", type=str, help="FTS5 全文搜索")
    parser.add_argument("--db", type=str, help="数据库路径 (默认 data/news.db)")
    parser.add_argument("--json", action="store_true", help="JSON 输出模式 (供程序调用)")

    args = parser.parse_args()
    config = load_config()

    db_path = args.db or config.get("settings", {}).get("db_path", "data/news.db")
    if not os.path.isabs(db_path):
        db_path = str(SKILL_DIR / db_path)

    conn = init_db(db_path)

    try:
        if args.fetch:
            stats = fetch_all(config, conn, args.category)
            print(f"\n{'='*50}")
            print(f"📊 拉取完成")
            print(f"{'='*50}")
            print(f"  总条目:  {stats['total']}")
            print(f"  新增:    {stats['new']}")
            print(f"  重复:    {stats['dup']}")
            print(f"  失败:    {stats['failed']}")

        elif args.list:
            list_feeds(config, conn)

        elif args.search:
            results = search_articles(conn, args.search, args.limit, args.category, args.hours)
            if args.json:
                print(json.dumps({"query": args.search, "count": len(results), "articles": [dict(r) for r in results]}, ensure_ascii=False, indent=2))
            elif results:
                print(f"\n搜索结果: '{args.search}' ({len(results)} 条)\n")
                for r in results:
                    print(format_article(r))
            else:
                print(f"\n未找到匹配 '{args.search}' 的文章")

        elif args.fts:
            results = fts_search(conn, args.fts, args.limit)
            if args.json:
                print(json.dumps({"query": args.fts, "count": len(results), "articles": [dict(r) for r in results]}, ensure_ascii=False, indent=2))
            elif results:
                print(f"\nFTS 搜索: '{args.fts}' ({len(results)} 条)\n")
                for r in results:
                    print(format_article(r))
            else:
                print(f"\n未找到匹配 '{args.fts}' 的文章")

        elif args.top:
            results = top_articles(conn, args.top, args.hours, args.category)
            if args.json:
                print(json.dumps({"top": args.top, "hours": args.hours, "category": args.category, "count": len(results), "articles": [dict(r) for r in results]}, ensure_ascii=False, indent=2))
            else:
                cat_str = f" [{args.category}]" if args.category else ""
                print(f"\n🔥 热门{cat_str} (近 {args.hours} 小时, TOP {args.top})\n")
                for i, r in enumerate(results, 1):
                    print(f"  {i:2d}. {format_article(r)}")
                if not results:
                    print("  暂无数据，请先运行 --fetch")

        elif args.keywords:
            kws = [k.strip() for k in args.keywords.split(",")]
            results = []
            for kw in kws:
                r = search_articles(conn, kw, args.limit, hours=args.hours)
                results.extend(r)
            if results:
                print(f"\n🚨 关键词告警 ({', '.join(kws)})\n")
                for r in results:
                    print(format_article(r))
            else:
                print(f"\n✅ 无匹配关键词 '{args.keywords}' 的新资讯")

        else:
            parser.print_help()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
