#!/usr/bin/env python3.11
# WP2 速度信号提取 — GDELT 云端IP 429不可用，改用 TrendRadar rank_history。
# 读 TrendRadar output/news/*.db 的 news_items + rank_history，计算每条热度velocity，
# 写 news-intel/data/velocity_signals.json + news.db velocity_signals 表(供WP3 salience V因子)。
import sqlite3, glob, json, os, math, datetime
TR_OUT = "/home/admin/trendradar/output/news"
INTEL = "/home/admin/wuhoo-workspace/skills/default/wuhoo-news-intel"
NEWS_DB = "/home/admin/wuhoo-workspace/skills/default/wuhoo-news-rss/data/news.db"
now = datetime.datetime.now()

def latest_db():
    dbs = sorted(glob.glob(os.path.join(TR_OUT, "*.db")))
    return dbs[-1] if dbs else None

def compute():
    db = latest_db()
    if not db:
        return {"error": "no trendradar output db", "signals": []}
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    items = c.execute("SELECT * FROM news_items").fetchall()
    signals = []
    for it in items:
        nid = it["id"]
        hist = c.execute("SELECT rank, crawl_time, created_at FROM rank_history WHERE news_item_id=? ORDER BY created_at", (nid,)).fetchall()
        raw_ranks = [h["rank"] for h in hist]
        valid = [r for r in raw_ranks if r and r > 0]   # rank=0 是掉榜哨兵, 排除
        if not valid:
            continue
        crawl_count = it["crawl_count"] or len(valid)   # 列=在榜次数(掉榜不计)
        best_rank = min(valid)
        latest_raw = raw_ranks[-1] if raw_ranks else 0
        dropped = (latest_raw == 0)                     # 最新抓取掉榜
        latest_rank = valid[-1]
        first_rank = valid[0]
        rank_delta = first_rank - latest_rank           # 在榜期间排名改善(正=上升)
        persistence = crawl_count
        is_new = (persistence <= 1 and not dropped)
        # velocity: 排名靠前权重 + 上升奖励 + 持久奖励 + 新入榜burst; 掉榜衰减
        rank_w = max(0.0, (31 - best_rank) / 30.0)        # rank1→1.0, rank30→0.03
        rise_bonus = max(0.0, rank_delta) * 0.08
        persist_bonus = min(0.5, (persistence - 1) * 0.1)
        burst = 0.3 if (is_new and best_rank <= 10) else 0.0
        velocity = rank_w + rise_bonus + persist_bonus + burst
        if dropped:
            velocity *= 0.3                              # 掉榜→速度衰减
        velocity = round(velocity, 4)
        signals.append({
            "item_id": nid, "title": it["title"], "platform": it["platform_id"],
            "url": it["url"], "best_rank": best_rank, "latest_rank": latest_rank,
            "rank_delta": rank_delta, "crawl_count": crawl_count,
            "is_new": is_new, "velocity": velocity,
            "first_crawl": it["first_crawl_time"], "last_crawl": it["last_crawl_time"],
        })
    c.close()
    signals.sort(key=lambda s: s["velocity"], reverse=True)
    return {"computed_at": now.isoformat(timespec="seconds"), "source_db": os.path.basename(db),
            "total_items": len(signals), "signals": signals}

def write_table(signals):
    c = sqlite3.connect(NEWS_DB)
    c.execute("""CREATE TABLE IF NOT EXISTS velocity_signals(
        item_id INTEGER, title TEXT, platform TEXT, url TEXT,
        best_rank INTEGER, latest_rank INTEGER, rank_delta INTEGER,
        crawl_count INTEGER, is_new INTEGER, velocity REAL, computed_at TEXT)""")
    c.execute("DELETE FROM velocity_signals")
    c.executemany("INSERT INTO velocity_signals VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        [(s["item_id"], s["title"], s["platform"], s["url"], s["best_rank"], s["latest_rank"],
          s["rank_delta"], s["crawl_count"], int(s["is_new"]), s["velocity"], now.isoformat(timespec="seconds")) for s in signals])
    c.commit(); c.close()

if __name__ == "__main__":
    res = compute()
    os.makedirs(os.path.join(INTEL, "data"), exist_ok=True)
    with open(os.path.join(INTEL, "data", "velocity_signals.json"), "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    if res.get("signals"):
        write_table(res["signals"])
    print(f"velocity computed: {res.get('total_items',0)} items from {res.get('source_db')}")
    for s in res.get("signals", [])[:10]:
        print(f"  v={s['velocity']:.3f} [{s['platform']}] rank{s['best_rank']}→{s['latest_rank']} Δ{s['rank_delta']} crawl{s['crawl_count']} | {s['title'][:45]}")
