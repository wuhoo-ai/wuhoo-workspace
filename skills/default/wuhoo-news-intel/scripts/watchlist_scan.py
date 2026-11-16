#!/usr/bin/env python3.11
# WP2 watchlist 巡检 — 精准关注告警(D1个人化种子, WP6跨profile富化)。
# 用 fetched_at 时间窗(pub_date不可靠), alert_log 去重, ticker优先, 限量防刷屏。
# --no-agent cron: 有新命中→打印告警文本(投递weixin); 无命中→空stdout(静默)。
# --dry-run: 只打印不写alert_log(测试用)。
import sqlite3, json, os, sys, datetime, argparse, re
import yaml
INTEL = "/home/admin/wuhoo-workspace/skills/default/wuhoo-news-intel"
NEWS_DB = "/home/admin/wuhoo-workspace/skills/default/wuhoo-news-rss/data/news.db"
WATCHLIST = os.path.join(INTEL, "data", "watchlist.yaml")

def ensure_table(c):
    c.execute("""CREATE TABLE IF NOT EXISTS alert_log(
        hash TEXT, grp TEXT, title TEXT, alerted_at TEXT,
        PRIMARY KEY(hash, grp))""")

def load_watchlist():
    with open(WATCHLIST) as f:
        wl = yaml.safe_load(f) or {}
    wl.setdefault("groups", [])
    # union DB watchlist（intel.py watch add / sync-profiles 跨profile写入），按 origin 分组
    try:
        c = sqlite3.connect(NEWS_DB); c.row_factory = sqlite3.Row
        rows = c.execute("SELECT kind,value,origin_profile FROM watchlist WHERE enabled=1").fetchall()
        c.close()
        by_origin = {}
        for r in rows:
            o = r["origin_profile"] or "default"
            g = by_origin.setdefault(o, {"name": f"DB-{o}", "tickers": [], "keywords": []})
            if r["kind"] == "ticker":
                g["tickers"].append(r["value"])
            else:
                g["keywords"].append(r["value"])
        for g in by_origin.values():
            if g["tickers"] or g["keywords"]:
                wl["groups"].append(g)
    except sqlite3.OperationalError:
        pass   # watchlist 表尚未建（WP5 前）→ 仅 YAML
    return wl

def scan(window_min, dry_run, max_alerts, quiet_hours):
    now = datetime.datetime.now()
    # 静默时段(默认23:00-08:00不推送, 避免夜间刷屏)
    if quiet_hours and (now.hour >= 23 or now.hour < 8):
        return ""
    wl = load_watchlist()
    c = sqlite3.connect(NEWS_DB)
    c.row_factory = sqlite3.Row
    ensure_table(c)
    cutoff = (now - datetime.timedelta(minutes=window_min)).strftime("%Y-%m-%dT%H:%M:%S")
    rows = c.execute("SELECT id,feed_name,title,summary,link,pub_date,fetched_at,category,hot_score,is_alert,alert_keywords,hash FROM articles WHERE fetched_at>=? ORDER BY hot_score DESC, fetched_at DESC", (cutoff,)).fetchall()
    alerted = set((r[0], r[1]) for r in c.execute("SELECT hash,grp FROM alert_log").fetchall())
    hits = []
    for r in rows:
        text = f"{r['title']} {r['summary'] or ''} {r['content'] if 'content' in r.keys() else ''}"
        text_l = text.lower()
        for g in wl.get("groups", []):
            gname = g["name"]
            matched = []
            # ticker 精确匹配: ASCII 词边界正则(\bETH\b 不匹配 method/metadata), 高优先
            for tk in g.get("tickers", []):
                if re.search(r'\b' + re.escape(tk) + r'\b', text, re.I):
                    matched.append(("ticker", tk))
            # 关键词: 含CJK→子串(正确匹配"A股市场"); 纯ASCII→词边界(OpenAI/CPI不匹配子串)
            for kw in g.get("keywords", []):
                if re.search(r'[\u4e00-\u9fff]', kw):
                    if kw in text:
                        matched.append(("kw", kw))
                else:
                    if re.search(r'\b' + re.escape(kw) + r'\b', text, re.I):
                        matched.append(("kw", kw))
            if not matched:
                continue
            if (r["hash"], gname) in alerted:
                continue
            has_ticker = any(m[0] == "ticker" for m in matched)
            priority = (2 if has_ticker else 0) + (1 if r["is_alert"] else 0) + min(1.0, (r["hot_score"] or 0) / 40.0)
            hits.append({"priority": priority, "grp": gname, "row": r,
                         "matched": [m[1] for m in matched][:4], "has_ticker": has_ticker})
    # 排序: ticker优先 + 热度, 限量
    hits.sort(key=lambda h: h["priority"], reverse=True)
    # 同一文章只告警一次(取最高优先组)
    seen_hash = set(); uniq = []
    for h in hits:
        if h["row"]["hash"] in seen_hash:
            continue
        seen_hash.add(h["row"]["hash"]); uniq.append(h)
    selected = uniq[:max_alerts]
    if not selected:
        c.close(); return ""
    lines = [f"🔔 关注巡检 | {now.strftime('%m-%d %H:%M')} | 新增{len(selected)}条(窗口{window_min}min,候选{len(uniq)})"]
    for h in selected:
        r = h["row"]
        pub = (r["pub_date"] or "")[:16]
        lines.append(f"\n[{h['grp']}] {r['title'][:70]}")
        lines.append(f"  来源:{r['feed_name']} | {pub} | 热度{r['hot_score'] or 0} | 匹配:{','.join(h['matched'])}")
        if r["link"]:
            lines.append(f"  {r['link']}")
        if not dry_run:
            c.execute("INSERT OR IGNORE INTO alert_log(hash,grp,title,alerted_at) VALUES(?,?,?,?)",
                      (r["hash"], h["grp"], r["title"], now.isoformat(timespec="seconds")))
    if not dry_run:
        c.commit()
    c.close()
    return "\n".join(lines)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=35, help="时间窗分钟(默认35,*/30cron重叠5min)")
    ap.add_argument("--max-alerts", type=int, default=3, help="单次最多告警条数(防刷屏)")
    ap.add_argument("--dry-run", action="store_true", help="只打印不写alert_log")
    ap.add_argument("--no-quiet", action="store_true", help="忽略静默时段(测试用)")
    a = ap.parse_args()
    out = scan(a.window, a.dry_run, a.max_alerts, quiet_hours=not a.no_quiet)
    if out:
        print(out)
    # 无命中→空stdout→cron静默
