#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""WP5 Agent 原生层 intel.py — 14 子命令统一 CLI（方案 §7.1）。
复用 event_center(ec)/synthesize(sy)/velocity/watchlist_scan，不新建 MCP server（单 hub 铁律）。
深挖/检索复用 web_extract(agent 侧)/FTS5/向量；TrendRadar 热榜由 agent 经 MCP 补充。
用法: python3.11 intel.py <cmd> [args]
  fetch / audit / cluster / rank / brief / alert / search / timeline / dive /
  watch / profile / tune / sync-profiles / health
"""
import os, sys, json, sqlite3, argparse, subprocess, re, glob, math, html as _html
from datetime import datetime, timedelta
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))          # src/
INTEL = os.path.dirname(HERE)                               # wuhoo-news-intel/
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(INTEL, "scripts"))
import event_center as ec
import synthesize as sy

HOME = os.path.expanduser("~")
DB = ec.DB
DATA = os.path.join(INTEL, "data")
NEWS_WEB = os.path.join(HOME, "wuhoo-workspace/news-web")
# WP6: nginx serving root。/home/admin 是 700，nginx worker 无法 traverse 到 workspace，
# 故 publish-copy 到标准 web 根 /var/www/news（755，nginx 可读），不弱化 home 隔离。
SERVE_DIR = "/var/www/news"
PUBLIC_BASE = "https://wuhoo.shanavasa.click/news"
TR_OUT = os.path.join(HOME, "trendradar/output/news")
RSS_SRC = os.path.join(HOME, "wuhoo-workspace/skills/default/wuhoo-news-rss/src")
TRADE = os.path.join(HOME, "wuhoo-workspace/data/trade")
GUIMEI = os.path.join(HOME, "wuhoo-workspace/games/guimei/docs")
CATEGORIES = {"科技", "财经", "游戏", "宏观", "加密", "体育", "综合", "国际", "社会"}
PY = "python3.11"   # cron 安全：裸命令，不用绝对路径（lifecycle guard）


def conn():
    return ec.get_conn()


def now():
    return ec.now_local()


def chunked(seq, n=500):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def load_member_rows(c, aids):
    """分块加载文章行（避免 IN>999 变量上限），只取 salience 所需列。"""
    out = {}
    for ch in chunked(list(aids)):
        q = ",".join("?" * len(ch))
        for r in c.execute(
                f"SELECT id,feed_name,title,summary,content,fetched_at,category,hash,link "
                f"FROM articles WHERE id IN ({q})", ch):
            out[r["id"]] = r
    return out


def recompute_salience(c, verbose=False):
    """用当前 interest_profile/topic_burst/velocity 重算所有 active 事件 salience（不重聚类）。
    D3 调节即时生效路径：tune 写表 → recompute → 新 salience。复用 ec.compute_salience。"""
    tier_map = ec.load_tier_map(c)
    weights = ec.load_feed_weights()
    vel = ec.load_velocity_map(c)
    bursts = ec.load_bursts(c)
    interest = ec.load_interest(c)
    nw = now()
    evs = c.execute("SELECT event_id,canonical_id,n_indep_sources FROM events WHERE status='active'").fetchall()
    aids = {r[0] for r in c.execute("SELECT DISTINCT article_id FROM event_members")}
    id2row = load_member_rows(c, aids)
    mem_map = {}
    for r in c.execute("SELECT event_id,article_id FROM event_members"):
        mem_map.setdefault(r["event_id"], []).append(r["article_id"])
    n = 0
    for ev in evs:
        mem = mem_map.get(ev["event_id"], [])
        if not mem:
            continue
        canon = id2row.get(ev["canonical_id"]) or id2row.get(mem[0])
        if canon is None:
            continue
        sal = ec.compute_salience(canon, mem, id2row, ev["n_indep_sources"],
                                  tier_map, weights, vel, bursts, interest, nw)
        c.execute("UPDATE events SET salience=? WHERE event_id=?", (sal, ev["event_id"]))
        n += 1
    c.commit()
    if verbose:
        print(f"recompute salience: {n} 事件 (interest={len(interest)} bursts={len(bursts)})")
    return n


# ---------- 1. fetch ----------
def cmd_fetch(a):
    if a.feed:
        cmd = [PY, os.path.join(RSS_SRC, "fetcher.py"), "--fetch", "--feed", a.feed]
    else:
        cmd = ["bash", os.path.join(HOME, ".hermes/scripts/rss_hourly_fetch.sh")]
    if a.dry:
        print("[dry] " + " ".join(cmd)); return
    print("执行: " + " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=580)
    print(r.stdout[-2000:]);  print(r.stderr[-500:] if r.stderr else "", file=sys.stderr)


# ---------- 2. audit ----------
def cmd_audit(a):
    c = conn()
    rows = c.execute("SELECT feed_name,tier,status,last_check,items,note FROM feed_health ORDER BY tier,feed_name").fetchall()
    if not rows:
        print("feed_health 空，先跑 WP0 finalize"); return
    by = Counter(r["status"] for r in rows)
    print(f"源健康: 总{len(rows)} | " + " ".join(f"{k}={v}" for k, v in sorted(by.items())))
    bad = [r for r in rows if r["status"] not in ("ok",)]
    print(f"非 ok 源 {len(bad)}:")
    for r in bad[:30]:
        print(f"  [{r['tier']}] {r['feed_name']}: {r['status']} items={r['items']} {(r['note'] or '')[:50]}")
    tot = c.execute("SELECT COUNT(*) n, MAX(fetched_at) mx FROM articles").fetchone()
    print(f"articles 总{tot['n']} 最新入库 {tot['mx']}")
    c.close()


# ---------- 3. cluster ----------
def cmd_cluster(a):
    c = conn()
    ec.init_db(c)
    n_emb = ec.embed_articles(c, a.window, verbose=True)
    n_ev = ec.cluster(c, a.window, verbose=True)
    print(f"cluster 完成: 新嵌入{n_emb} 事件{n_ev}")
    c.close()


# ---------- 4. rank ----------
def cmd_rank(a):
    c = conn()
    if a.recompute:
        recompute_salience(c, verbose=True)
    rows = ec.top_events(c, a.n)
    print(f"salience TOP{len(rows)} (event_id 序号供微信深挖触发):")
    for i, r in enumerate(rows, 1):
        print(f"{i}. [{r['event_id']}] S={r['salience']:.2f} N={r['n_indep_sources']} {r['topic']} | {r['label'][:55]}")
    c.close()


# ---------- HTML 渲染 ----------
def _esc(s):
    return _html.escape(str(s or ""))


def render_card_html(c, idx):
    if c.get("error"):
        return f'<div class="card err"><h3>{idx}. {_esc(c.get("title"))}</h3><p>合成失败: {_esc(c["error"])}</p></div>'
    links = "".join(f'<li><a href="{_esc(l["url"])}" rel="noopener">{_esc(l["feed"])}</a></li>'
                    for l in c.get("links", [])[:6])
    div = f'<p class="div"><b>分歧/未核实：</b>{_esc(c["divergence"])}</p>' if c.get("divergence") else ""
    unv = f'<p class="warn">⚠ 数字未核实：{_esc(", ".join(c["unverified_numbers"]))}</p>' if c.get("unverified_numbers") else ""
    ents = ", ".join(c.get("primary_entities", [])[:6])
    return f'''<div class="card" id="e{c['event_id']}">
<h3>{idx}. {_esc(c['title'])} <span class="meta">[event {c['event_id']} · {c['n_indep']}独立源 · S={c.get('salience',0):.1f} · {_esc(c.get('topic'))}]</span></h3>
<p class="ents">主体：{_esc(ents)}</p>
<p><b>事实：</b>{_esc(c.get('fact'))}</p>
<p><b>影响：</b>{_esc(c.get('impact'))}</p>
{div}{unv}
<p><b>下一步关注：</b>{_esc(c.get('next_step'))}</p>
<ul class="links">{links}</ul></div>'''


def write_html(path, title, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)}</title><style>
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:760px;margin:0 auto;padding:16px;line-height:1.7;color:#1a1a1a;background:#fafafa}}
h1{{font-size:22px;border-bottom:2px solid #c0392b;padding-bottom:8px}}
.card{{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:14px 16px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.05)}}
.card h3{{font-size:17px;margin:0 0 8px}} .meta{{font-size:12px;color:#888;font-weight:normal}}
.ents{{font-size:13px;color:#555}} .div{{color:#b9770e}} .warn{{color:#c0392b}}
.links{{font-size:13px;padding-left:18px}} .links a{{color:#2471a3;word-break:break-all}}
.err{{border-color:#c0392b}} footer{{font-size:12px;color:#999;margin-top:24px;text-align:center}}
</style></head><body><h1>{_esc(title)}</h1>{body}
<footer>Wuhoo 新闻情报 · 生成 {now().strftime('%Y-%m-%d %H:%M')} CST · 只读 · 数字经来源核验</footer>
</body></html>'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path


def build_index_html():
    """归档索引 body：每日简报列表 + 事件深卡列表 + 说明。"""
    import glob
    dailies = sorted(glob.glob(os.path.join(NEWS_WEB, "daily", "*.html")), reverse=True)
    rows = "".join(f'<li><a href="daily/{os.path.basename(f)[:-5]}.html">{os.path.basename(f)[:-5]}</a></li>'
                   for f in dailies[:60])
    evs = sorted(glob.glob(os.path.join(NEWS_WEB, "event", "*.html")),
                 key=lambda p: int(os.path.basename(p)[:-5]) if os.path.basename(p)[:-5].isdigit() else 0,
                 reverse=True)
    evrows = "".join(f'<li><a href="event/{os.path.basename(f)[:-5]}.html">事件 {os.path.basename(f)[:-5]}</a></li>'
                     for f in evs[:30])
    return ('<div class="card"><h3>📊 A/B 评测</h3><ul class="links">'
            '<li><a href="eval/dashboard.html">A/B 指标看板 · 五维量化对比</a></li>'
            '<li><a href="eval/blind.html">双轨盲评 · A规则 vs B事件 同日并排(2周观察)</a></li></ul></div>'
            '<div class="card"><h3>📅 每日简报归档</h3><ul class="links">' + rows + '</ul></div>'
            '<div class="card"><h3>🔍 事件深卡</h3><ul class="links">' + evrows + '</ul></div>'
            '<div class="card"><h3>说明</h3><p>只读归档。每日简报含四段卡（事实/影响/分歧/下一步）+ ≥2 来源链接，'
            '数字经来源核验。微信简报为摘要，全量内容在此。反馈调节：多点X / 少点X / 这条没用。</p></div>')


def publish_web(verbose=True):
    """把 NEWS_WEB 静态产物同步到 nginx 可读 web 根 SERVE_DIR + 生成归档 index.html。
    幂等：每次全量 copy（文件小）。workspace NEWS_WEB 保留作 git 审计 canonical。"""
    import shutil, glob
    n = 0
    for sub in ("daily", "event", "eval"):
        dst = os.path.join(SERVE_DIR, sub)
        os.makedirs(dst, exist_ok=True)
        for f in glob.glob(os.path.join(NEWS_WEB, sub, "*.html")):
            shutil.copy2(f, os.path.join(dst, os.path.basename(f)))
            n += 1
    body = build_index_html()
    for root in (SERVE_DIR, NEWS_WEB):
        write_html(os.path.join(root, "index.html"), "Wuhoo 新闻情报归档", body)
    if verbose:
        print(f"publish_web: {n} HTML → {SERVE_DIR} (+index.html)")
    return n


def make_fallback(stamp):
    """D2 HTML 兜底：daily HTML 复制到 /tmp 短 ASCII 名（≤100KB），供微信媒体附件投递。
    /tmp 短 ASCII 名是已验证可靠的微信投递路径（区别于 scratch 探针）。返回 (path,size) 或 None。"""
    import shutil
    src = os.path.join(NEWS_WEB, "daily", f"{stamp}.html")
    if not os.path.exists(src):
        return None
    dst = f"/tmp/nb{stamp.replace('-', '')}.html"
    shutil.copy2(src, dst)
    return dst, os.path.getsize(dst)


# ---------- 5. brief ----------
def cmd_brief(a):
    c = conn()
    rows = ec.top_events(c, a.top)
    cards, tokens, quota = [], 0, False
    for i, r in enumerate(rows, 1):
        if tokens >= a.budget:
            print(f"[budget] 停止于第{i}条"); break
        cd = sy.synthesize_event(c, r["event_id"], store=True)
        cards.append(cd)
        tokens += cd.get("usage", {}).get("total_tokens", 0) or 0
        if cd.get("quota"):
            quota = True; print(f"[quota] 第{i}条429停止"); break
    stamp = a.date or now().strftime("%Y-%m-%d")
    compact = stamp.replace("-", "")
    os.makedirs(DATA, exist_ok=True)
    jpath = os.path.join(DATA, f"cards_{compact}.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump({"date": stamp, "total_tokens": tokens, "quota_hit": quota, "cards": cards}, f, ensure_ascii=False, indent=1)
    # 微信简报 ≤4KB：序号+标题+事实截断+1链接 + 全量内容链接(D2) + 反馈footer
    daily_url = f"{PUBLIC_BASE}/daily/{stamp}.html"
    wx = [f"📰 Wuhoo 简报 {stamp} (TOP{len(cards)})"]
    for i, cd in enumerate(cards, 1):
        if cd.get("error"):
            continue
        fact = (cd.get("fact") or "")[:90]
        link = cd["links"][0]["url"] if cd.get("links") else ""
        wx.append(f"\n{i}.【{cd['title'][:40]}】({cd['n_indep']}源)\n  {fact}\n  {link}")
    wx_body = "\n".join(wx)
    footer = f"\n\n📖 全量四段卡+来源: {daily_url}\n💬 回复序号深挖 | 多点X/少点X/这条没用 调节"
    wx_text = wx_body + footer
    if len(wx_text.encode("utf-8")) > 4000:
        keep = 4000 - len(footer.encode("utf-8")) - 20
        wx_text = wx_body.encode("utf-8")[:keep].decode("utf-8", "ignore") + "\n…" + footer
    wpath = os.path.join(DATA, f"brief_wechat_{compact}.txt")
    with open(wpath, "w", encoding="utf-8") as f:
        f.write(wx_text)
    # 全量 HTML（WP6 nginx /news/ 只读服务）
    body = "".join(render_card_html(cd, i) for i, cd in enumerate(cards, 1))
    hpath = write_html(os.path.join(NEWS_WEB, "daily", f"{stamp}.html"),
                       f"Wuhoo 新闻简报 {stamp}", body)
    publish_web()
    print(f"brief: {len(cards)}卡 tokens={tokens} quota={quota}")
    print(f"  微信({len(wx_text.encode('utf-8'))}B): {wpath}")
    print(f"  全量HTML: {hpath}")
    print(f"  公开链接: {daily_url}")
    print(f"  cards JSON: {jpath}")
    fb = make_fallback(stamp)
    if fb:
        ok = "≤100KB" if fb[1] <= 100 * 1024 else "⚠超100KB"
        print(f"  HTML兜底({fb[1]}B {ok}): {fb[0]}")
    if a.format in ("wechat", "all"):
        print("\n===== 微信简报正文 =====\n" + wx_text)
    c.close()


# ---------- 6. alert ----------
def cmd_alert(a):
    import watchlist_scan as ws
    out = ws.scan(a.window, a.dry_run, a.max_alerts, quiet_hours=not a.no_quiet)
    if out:
        print(out)
    else:
        print("(无新命中，静默)")


# ---------- 7. search ----------
def cmd_search(a):
    c = conn()
    q = a.query
    rows = []
    try:
        rows = c.execute(
            "SELECT a.id,a.title,a.feed_name,a.link,a.pub_date,a.fetched_at,a.summary "
            "FROM articles_fts f JOIN articles a ON a.id=f.rowid "
            "WHERE articles_fts MATCH ? ORDER BY rank LIMIT ?", (q, a.n)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    if not rows:   # FTS5 中文分词回退 LIKE
        like = f"%{q}%"
        rows = c.execute(
            "SELECT id,title,feed_name,link,pub_date,fetched_at,summary FROM articles "
            "WHERE title LIKE ? OR summary LIKE ? ORDER BY fetched_at DESC LIMIT ?",
            (like, like, a.n)).fetchall()
    print(f"search '{q}': {len(rows)} 命中 (FTS5{'+LIKE回退' if rows else ''})")
    for r in rows:
        print(f"  [{r['feed_name']}] {(r['title'] or '')[:60]} | {(r['fetched_at'] or '')[:16]}")
        if r["link"]:
            print(f"    {r['link']}")
    if a.vector and rows:
        try:
            import numpy as np
            qv = ec.norm_rows(ec.Embedder.embed([q]))[0]
            ids = [r["id"] for r in rows]
            vids, vmat = ec.load_vectors(c, ids)
            if len(vids):
                sims = vmat @ qv
                order = np.argsort(-sims)
                print("向量重排:")
                id2r = {r["id"]: r for r in rows}
                for k in order[:a.n]:
                    rr = id2r[vids[k]]
                    print(f"  cos={sims[k]:.3f} [{rr['feed_name']}] {(rr['title'] or '')[:55]}")
        except Exception as e:
            print(f"向量重排跳过: {e}")
    c.close()


# ---------- 8. timeline ----------
def cmd_timeline(a):
    c = conn()
    key = a.key
    if key.isdigit():
        eid = int(key)
        rows = c.execute(
            "SELECT a.title,a.feed_name,a.fetched_at,a.link,m.similarity FROM event_members m "
            "JOIN articles a ON a.id=m.article_id WHERE m.event_id=? ORDER BY a.fetched_at", (eid,)).fetchall()
        ev = c.execute("SELECT label,topic,first_seen,last_seen FROM events WHERE event_id=?", (eid,)).fetchone()
        print(f"事件 [{eid}] {ev['label'] if ev else ''} 时间线 ({len(rows)}成员):")
        for r in rows:
            print(f"  {(r['fetched_at'] or '')[:16]} [{r['feed_name']}] sim={r['similarity']:.2f} {(r['title'] or '')[:55]}")
    else:
        ent = c.execute("SELECT entity_id,name FROM entities WHERE name=? COLLATE NOCASE", (key,)).fetchone()
        if not ent:
            ent = c.execute("SELECT entity_id,name FROM entities WHERE name LIKE ?", (f"%{key}%",)).fetchone()
        if not ent:
            print(f"实体 '{key}' 未找到"); c.close(); return
        rows = c.execute(
            "SELECT e.event_id,e.label,e.topic,e.first_seen,e.last_seen,e.salience,e.n_indep_sources "
            "FROM event_entities ee JOIN events e ON e.event_id=ee.event_id "
            "WHERE ee.entity_id=? ORDER BY e.last_seen DESC LIMIT ?", (ent["entity_id"], a.n)).fetchall()
        print(f"实体 [{ent['name']}] 事件时间线 ({len(rows)}事件, 倒序):")
        for r in rows:
            print(f"  [{r['event_id']}] {(r['last_seen'] or '')[:16]} S={r['salience']:.1f} N={r['n_indep_sources']} {r['topic']} | {r['label'][:50]}")
    c.close()


# ---------- 9. dive ----------
def cmd_dive(a):
    c = conn()
    ctx = sy.gather_context(c, a.event)
    if not ctx:
        print(f"event {a.event} 无成员"); c.close(); return
    cd = sy.synthesize_event(c, a.event, store=True)
    print(json.dumps(cd, ensure_ascii=False, indent=1))
    # 簇内全文 + 链接（供 agent web_extract 深挖交叉核验）
    print("\n===== 簇内来源全文（agent 可 web_extract 深化）=====")
    for m in ctx["members"][:8]:
        full = ec.clean_text(m["content"] or m["summary"] or "")
        print(f"\n[{m['feed_name']}] {m['title']}\n  link: {m['link'] or '(无permalink)'}\n  {full[:400]}")
    if a.html:
        body = render_card_html(cd, 1)
        body += '<div class="card"><h3>簇内来源</h3><ul class="links">'
        for m in ctx["members"]:
            if m["link"] and "127.0.0.1" not in m["link"]:
                body += f'<li><a href="{_esc(m["link"])}">{_esc(m["feed_name"])}: {_esc((m["title"] or "")[:50])}</a></li>'
        body += "</ul></div>"
        p = write_html(os.path.join(NEWS_WEB, "event", f"{a.event}.html"),
                       f"深挖 · {cd.get('title','event '+str(a.event))}", body)
        publish_web(verbose=False)
        print(f"\n深挖网页: {p}")
        print(f"公开链接: {PUBLIC_BASE}/event/{a.event}.html")
    c.close()


# ---------- 10. watch ----------
def cmd_watch(a):
    c = conn()
    ec.init_db(c)
    if a.action == "add":
        if not a.value:
            raise SystemExit("watch add 需 --value")
        c.execute("INSERT INTO watchlist(kind,value,threshold,alert_channel,enabled,origin_profile) VALUES(?,?,?,?,1,?)",
                  (a.kind, a.value, a.threshold, a.channel, a.origin))
        c.commit()
        print(f"watch add: kind={a.kind} value={a.value} threshold={a.threshold} channel={a.channel}")
    elif a.action == "list":
        rows = c.execute("SELECT id,kind,value,threshold,alert_channel,enabled,origin_profile FROM watchlist ORDER BY id").fetchall()
        print(f"DB watchlist {len(rows)} 条:")
        for r in rows:
            print(f"  [{r['id']}] {r['kind']}={r['value']} thr={r['threshold']} ch={r['alert_channel']} en={r['enabled']} origin={r['origin_profile']}")
        print("(另有 watchlist.yaml groups 由 WP2 scanner 读取)")
    elif a.action == "remove":
        if a.id:
            c.execute("DELETE FROM watchlist WHERE id=?", (a.id,))
        elif a.value:
            c.execute("DELETE FROM watchlist WHERE value=?", (a.value,))
        else:
            raise SystemExit("watch remove 需 --id 或 --value")
        c.commit(); print("watch removed")
    c.close()


# ---------- 11. profile ----------
def cmd_profile(a):
    c = conn()
    ec.init_db(c)
    if a.action == "show":
        rows = c.execute("SELECT key,weight,source,origin_profile,expires,updated FROM interest_profile ORDER BY weight DESC").fetchall()
        print(f"interest_profile {len(rows)} 键:")
        for r in rows:
            print(f"  {r['key']} w={r['weight']:.2f} src={r['source']} origin={r['origin_profile']} exp={r['expires']}")
        bursts = c.execute("SELECT topic,boost,reason,expires_ts FROM topic_burst").fetchall()
        print(f"topic_burst {len(bursts)}:")
        for r in bursts:
            print(f"  {r['topic']} boost={r['boost']} exp={r['expires_ts']} {r['reason']}")
    elif a.action == "update":
        if not a.key:
            raise SystemExit("profile update 需 --key")
        exp = a.expires or (now() + timedelta(days=60)).isoformat()
        c.execute("INSERT INTO interest_profile(key,weight,updated,source,origin_profile,expires) VALUES(?,?,?,?,?,?) "
                  "ON CONFLICT(key) DO UPDATE SET weight=excluded.weight,updated=excluded.updated,source=excluded.source,expires=excluded.expires",
                  (a.key, a.weight, now().isoformat(), a.source or "manual", a.origin or "default", exp))
        c.commit(); print(f"profile update: {a.key} w={a.weight}")
    c.close()


# ---------- 12. tune (D3) ----------
def resolve_key(term):
    """自然语言词 → interest 键。实体别名→entity:CANON；类别→topic:CAT；否则 topic:raw。"""
    t = term.strip()
    al = ec.ENTITY_ALIASES
    if t.lower() in al:
        return "entity:" + al[t.lower()]
    if t in al.values():
        return "entity:" + t
    if t in CATEGORIES:
        return "topic:" + t
    return "topic:" + t


def adjust_interest(c, key, delta, source="tune"):
    r = c.execute("SELECT weight FROM interest_profile WHERE key=?", (key,)).fetchone()
    old = r["weight"] if r else 0.0
    new = round(old + delta, 3)
    exp = (now() + timedelta(days=60)).isoformat()
    c.execute("INSERT INTO interest_profile(key,weight,updated,source,origin_profile,expires) VALUES(?,?,?,?,?,?) "
              "ON CONFLICT(key) DO UPDATE SET weight=excluded.weight,updated=excluded.updated,source=excluded.source",
              (key, new, now().isoformat(), source, "default", exp))
    return old, new


def cmd_tune(a):
    c = conn()
    ec.init_db(c)
    text = a.text
    changes = []
    # 事件反馈（这条有用/没用）
    if a.event:
        if re.search(r"没用|不感兴趣|无关|不要", text):
            c.execute("INSERT INTO feedback(event_id,kind,raw_text,ts,applied) VALUES(?,?,?,?,1)",
                      (a.event, "not_useful", text, now().isoformat()))
            ev = c.execute("SELECT topic FROM events WHERE event_id=?", (a.event,)).fetchone()
            if ev:
                k = "topic:" + (ev["topic"] or "综合")
                o, n = adjust_interest(c, k, -0.1, "feedback")
                changes.append(f"feedback not_useful event{a.event}; {k} {o}→{n}")
        elif re.search(r"有用|不错|好|多来", text):
            c.execute("INSERT INTO feedback(event_id,kind,raw_text,ts,applied) VALUES(?,?,?,?,1)",
                      (a.event, "useful", text, now().isoformat()))
            ev = c.execute("SELECT topic FROM events WHERE event_id=?", (a.event,)).fetchone()
            if ev:
                k = "topic:" + (ev["topic"] or "综合")
                o, n = adjust_interest(c, k, +0.1, "feedback")
                changes.append(f"feedback useful event{a.event}; {k} {o}→{n}")
    # 多点/少点
    m = re.search(r"(?:多点|多推|多看|增加|加强)\s*([^\s,，。]+)", text)
    if m:
        k = resolve_key(m.group(1)); o, n = adjust_interest(c, k, +0.2)
        changes.append(f"多点 {k} {o}→{n}")
    m = re.search(r"(?:少点|少推|少看|减少|降低)\s*([^\s,，。]+)", text)
    if m:
        k = resolve_key(m.group(1)); o, n = adjust_interest(c, k, -0.3)
        changes.append(f"少点 {k} {o}→{n}")
    # 近期热点 boost（TTL 7天）
    m = re.search(r"([^\s,，。]+?)\s*(?:很热|是热点|热点|爆发|火了|最近很火)", text)
    if m:
        term = m.group(1)
        cat = term if term in CATEGORIES else (ec.ENTITY_ALIASES.get(term.lower(), term))
        exp = (now() + timedelta(days=7)).isoformat()
        c.execute("INSERT INTO topic_burst(topic,boost,reason,expires_ts) VALUES(?,?,?,?) "
                  "ON CONFLICT(topic) DO UPDATE SET boost=excluded.boost,reason=excluded.reason,expires_ts=excluded.expires_ts",
                  (cat, 0.5, text, exp))
        changes.append(f"topic_burst {cat} boost=0.5 TTL7天 exp={exp[:10]}")
    c.commit()
    if not changes:
        print(f"tune 未解析出调节意图: '{text}'（支持: 多点X/少点X/这条有用|没用 --event ID/X很热）")
        c.close(); return
    n = recompute_salience(c)
    print("tune 应用:")
    for ch in changes:
        print("  " + ch)
    print(f"即时生效: recompute {n} 事件 salience")
    for r in ec.top_events(c, 5):
        print(f"  TOP [{r['event_id']}] S={r['salience']:.2f} {r['topic']} | {r['label'][:40]}")
    c.close()


# ---------- 13. sync-profiles (D1, 跨 profile 只读) ----------
A_SHARE_SECTOR = {}   # 由报告头解析


def cmd_sync_profiles(a):
    c = conn()
    ec.init_db(c)
    exp = (now() + timedelta(days=60)).isoformat()   # 历史种子, 60天过期(WP6实时富化前)
    # --- trader: workflow_b 个股报告头(股票代码/公司名称/行业, 跳过数量) ---
    reports = sorted(glob.glob(os.path.join(TRADE, "workflow_b", "*", "decision_report.md")))
    seen_code = set(); trader_seeds = []
    for rp in reports:
        try:
            with open(rp, encoding="utf-8") as f:
                head = f.read(600)
        except Exception:
            continue
        code = re.search(r"股票代码\*{0,2}[:：]\s*(\d{6})", head)
        name = re.search(r"公司名称\*{0,2}[:：]\s*([^\n*]+)", head)
        sector = re.search(r"行业\*{0,2}[:：]\s*([^\n*]+)", head)
        if not code:
            continue
        cd = code.group(1)
        if cd in seen_code:
            continue
        seen_code.add(cd)
        nm = (name.group(1).strip() if name else cd)
        sec = (sector.group(1).strip() if sector else "A股")
        trader_seeds.append((cd, nm, sec))   # privacy: 只 ticker+名称+行业, 不写市值/PE/持仓数量
    # --- gamedev: guimei 技术栈关键词 ---
    tech = ["Unity", "URP", "Unreal", "Aseprite", "Blender", "像素", "骨骼动画", "rig", "shader",
            "Godot", "皮影", "独立游戏", "guimei", "游戏版号", "米哈游", "任天堂", "Steam"]
    found = set()
    for doc in ("INDEX.md", "DOCUMENT-MAP.md", "RETROSPECTIVE-2026-09.md", "research-engine-survey-2026-09-03.md"):
        p = os.path.join(GUIMEI, doc)
        if os.path.exists(p):
            try:
                txt = open(p, encoding="utf-8").read()
                for t in tech:
                    if t.lower() in txt.lower():
                        found.add(t)
            except Exception:
                pass
    # --- 应用（dry 只报告解析结果, 不写 DB）---
    added_interest, added_watch = [], []
    if not a.dry:
        for cd, nm, sec in trader_seeds:
            k = "entity:" + nm
            c.execute("INSERT INTO interest_profile(key,weight,updated,source,origin_profile,expires) VALUES(?,?,?,?,?,?) "
                      "ON CONFLICT(key) DO UPDATE SET weight=MAX(interest_profile.weight,excluded.weight),source=excluded.source,expires=excluded.expires",
                      (k, 0.3, now().isoformat(), "trader_workflow_b", "trader", exp))
            added_interest.append(f"{k}(w0.3,{sec})")
            c.execute("INSERT INTO watchlist(kind,value,threshold,alert_channel,enabled,origin_profile) VALUES(?,?,?,?,1,?)",
                      ("keyword", nm, "yellow", "weixin", "trader"))
            added_watch.append(nm)
        if found:
            c.execute("INSERT INTO interest_profile(key,weight,updated,source,origin_profile,expires) VALUES(?,?,?,?,?,?) "
                      "ON CONFLICT(key) DO UPDATE SET weight=MAX(interest_profile.weight,excluded.weight),source=excluded.source",
                      ("topic:游戏", 0.3, now().isoformat(), "gamedev_guimei", "gamedev", exp))
            added_interest.append("topic:游戏(w0.3,gamedev)")
            for t in sorted(found):
                c.execute("INSERT INTO watchlist(kind,value,threshold,alert_channel,enabled,origin_profile) VALUES(?,?,?,?,1,?)",
                          ("keyword", t, "yellow", "weixin", "gamedev"))
                added_watch.append(t)
        c.commit()
        n = recompute_salience(c)
    else:
        added_interest = [f"entity:{nm}(w0.3,{sec})" for cd, nm, sec in trader_seeds]
        if found:
            added_interest.append("topic:游戏(w0.3,gamedev)")
        added_watch = [nm for cd, nm, sec in trader_seeds] + sorted(found)
        n = 0
    print(f"sync-profiles (跨profile只读, privacy=仅ticker+名称+行业/技术词, 不含持仓数量/成本/盈亏):")
    print(f"  trader workflow_b 个股: {len(seen_code)} ({', '.join(sorted(seen_code))})")
    print(f"  interest_profile {'新增/更新' if not a.dry else '将写入'} {len(added_interest)}: {', '.join(added_interest[:12])}")
    print(f"  watchlist {'新增' if not a.dry else '将写入'} {len(added_watch)}: {', '.join(added_watch[:20])}")
    print(f"  gamedev 技术词命中: {', '.join(sorted(found))}")
    if a.dry:
        print("  [dry] 未写入 DB（仅报告解析结果）")
    else:
        print(f"  即时生效 recompute {n} 事件; 种子 expires={exp[:10]}(60天, WP6实时富化前)")
    c.close()


# ---------- 14. health ----------
def cmd_health(a):
    c = conn()
    def cnt(t):
        try:
            return c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except sqlite3.OperationalError:
            return -1
    print("=== 管线指标 ===")
    print(f"articles={cnt('articles')} events={cnt('events')} event_members={cnt('event_members')} vectors={cnt('article_vectors')}")
    print(f"entities={cnt('entities')} event_facts={cnt('event_facts')} feedback={cnt('feedback')} interest={cnt('interest_profile')} burst={cnt('topic_burst')}")
    fv = c.execute("SELECT SUM(verified) v, COUNT(*) n FROM event_facts").fetchone()
    if fv["n"]:
        print(f"event_facts 核验率: {fv['v']}/{fv['n']} ({100*fv['v']//fv['n']}%)")
    fh = c.execute("SELECT status,COUNT(*) n FROM feed_health GROUP BY status").fetchall()
    print("feed_health: " + " ".join(f"{r['status']}={r['n']}" for r in fh))
    vs = c.execute("SELECT MAX(computed_at) mx, COUNT(*) n FROM velocity_signals").fetchone()
    print(f"velocity_signals: {vs['n']} 条, 最新 {vs['mx']}")
    al = c.execute("SELECT MAX(alerted_at) mx, COUNT(*) n FROM alert_log").fetchone()
    print(f"alert_log: {al['n']} 条, 最新 {al['mx']}")
    mx = c.execute("SELECT MAX(fetched_at) FROM articles").fetchone()[0]
    print(f"最新入库: {mx}")
    c.close()
    print("=== 容器 ===")
    try:
        r = subprocess.run(["podman", "ps", "--format", "{{.Names}} {{.Status}} {{.Ports}}"],
                           capture_output=True, text=True, timeout=20)
        print(r.stdout.strip() or "(podman ps 空)")
    except Exception as e:
        print(f"podman ps 失败: {e}")
    print("=== 投递账本 ===")
    led = [os.path.join(HOME, ".hermes/cron/deliveries.db")] + glob.glob(os.path.join(HOME, "wuhoo-workspace/skills/default/*/data/deliveries.db"))
    led = [p for p in led if os.path.exists(p)]
    if led:
        try:
            lc = sqlite3.connect(led[0]); lc.row_factory = sqlite3.Row
            cols = [r[1] for r in lc.execute("PRAGMA table_info(deliveries)")]
            tcol = "ts" if "ts" in cols else ("created_at" if "created_at" in cols else (cols[0] if cols else None))
            r = lc.execute(f"SELECT COUNT(*) n, MAX({tcol}) mx FROM deliveries").fetchone()
            print(f"{led[0]}: {r['n']} 条, 最新 {r['mx']}")
            lc.close()
        except Exception as e:
            print(f"账本读取: {e}")
    else:
        print("(deliveries.db 未找到)")


def main():
    ap = argparse.ArgumentParser(description="WP5 Agent 原生新闻情报 CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch"); p.add_argument("--feed"); p.add_argument("--dry", action="store_true"); p.set_defaults(fn=cmd_fetch)
    p = sub.add_parser("audit"); p.set_defaults(fn=cmd_audit)
    p = sub.add_parser("cluster"); p.add_argument("--window", type=int, default=72); p.set_defaults(fn=cmd_cluster)
    p = sub.add_parser("rank"); p.add_argument("--n", type=int, default=20); p.add_argument("--recompute", action="store_true"); p.set_defaults(fn=cmd_rank)
    p = sub.add_parser("brief"); p.add_argument("--date"); p.add_argument("--top", type=int, default=15)
    p.add_argument("--format", choices=["wechat", "html", "web", "all"], default="all"); p.add_argument("--budget", type=int, default=60000); p.set_defaults(fn=cmd_brief)
    p = sub.add_parser("alert"); p.add_argument("--window", type=int, default=35); p.add_argument("--max-alerts", type=int, default=3)
    p.add_argument("--dry-run", action="store_true"); p.add_argument("--no-quiet", action="store_true"); p.set_defaults(fn=cmd_alert)
    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("--n", type=int, default=10); p.add_argument("--vector", action="store_true"); p.set_defaults(fn=cmd_search)
    p = sub.add_parser("timeline"); p.add_argument("key"); p.add_argument("--n", type=int, default=20); p.set_defaults(fn=cmd_timeline)
    p = sub.add_parser("dive"); p.add_argument("event", type=int); p.add_argument("--html", action="store_true"); p.set_defaults(fn=cmd_dive)
    p = sub.add_parser("watch"); p.add_argument("action", choices=["add", "list", "remove"])
    p.add_argument("--kind", default="keyword"); p.add_argument("--value"); p.add_argument("--threshold", default="yellow")
    p.add_argument("--channel", default="weixin"); p.add_argument("--origin", default="default"); p.add_argument("--id", type=int); p.set_defaults(fn=cmd_watch)
    p = sub.add_parser("profile"); p.add_argument("action", choices=["show", "update"])
    p.add_argument("--key"); p.add_argument("--weight", type=float, default=0.0); p.add_argument("--source"); p.add_argument("--origin"); p.add_argument("--expires"); p.set_defaults(fn=cmd_profile)
    p = sub.add_parser("tune"); p.add_argument("text"); p.add_argument("--event", type=int); p.set_defaults(fn=cmd_tune)
    p = sub.add_parser("sync-profiles"); p.add_argument("--dry", action="store_true"); p.set_defaults(fn=cmd_sync_profiles)
    p = sub.add_parser("health"); p.set_defaults(fn=cmd_health)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
