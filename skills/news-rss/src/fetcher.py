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
import sys
import time
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
             author, pub_date, fetched_at, category, tags, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def calc_hot_score(entry: dict, feed_cfg: dict, keywords: Optional[List[str]] = None) -> Tuple[float, List[str]]:
    """计算热点评分 + 检查告警关键词"""
    score = 0.0
    hit_keywords = []

    text = f"{entry['title']} {entry.get('summary', '')}"

    for kw in (keywords or []):
        if kw.lower() in text.lower():
            hit_keywords.append(kw)
            score += 5  # 每个关键词 +5 分

    # 多源覆盖加分（同一标题出现在多个源）
    # 这个在批量处理后计算

    return score, hit_keywords


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

    stats = {"total": 0, "new": 0, "dup": 0, "failed": 0}
    all_titles = []  # 用于多源覆盖评分

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
            all_titles.extend([e.get("title", "") for e in result["entries"]])
        else:
            stats["failed"] += 1

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

            # 热点评分（传入关键词列表）
            score, hit_keywords = calc_hot_score(parsed, result, keywords)

            # 多源覆盖加分
            title = parsed["title"]
            source_count = all_titles.count(title)
            if source_count > 1:
                score += (source_count - 1) * 10  # 多源覆盖，每个额外源 +10 分

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
