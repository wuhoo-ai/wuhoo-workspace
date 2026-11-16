#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""WP7 评测与双轨 harness。
黄金集以 article_id 为键（稳定，跨 re-cluster；event_id 每日重置）。
子命令:
  build  — 从真实聚类采样 50 对(应合并/不应合并)，启发式预标注+证据，存 golden_set.json 供人工复核
  eval   — 对黄金集跑当前聚类决策，算去重 P/R/F1 + §10 指标，存 eval_report.json
  ab     — A轨(旧规则 daily_briefing) vs B轨(事件中心 intel brief) 同窗快照对比
黄金集标注为启发式预标注(needs_review=true)，正式盲评/微信切换需用户拍板(D3-A)。
"""
import argparse, json, os, re, sqlite3, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src")
DATA = os.path.join(HERE, "..", "data")
DB = "/home/admin/wuhoo-workspace/skills/default/wuhoo-news-rss/data/news.db"
GOLDEN = os.path.join(DATA, "golden_set.json")
REPORT = os.path.join(DATA, "eval_report.json")
sys.path.insert(0, SRC)
import event_center as ec


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def _zh(s):
    return bool(re.search(r"[\u4e00-\u9fff]", s or ""))


def _en(s):
    return bool(re.search(r"[A-Za-z]{4,}", s or "")) and not _zh(s)


def _company_prefix(title):
    """A股公司公告标题主语: 'X：...' 或 'X拟...' 的公司名 prefix。用于不同公司消歧。"""
    t = re.sub(r"<[^>]+>", "", title or "").strip()
    m = re.match(r"^([\u4e00-\u9fffA-Za-z0-9]{2,12})[：:]", t)
    if m:
        return m.group(1)
    m = re.match(r"^([\u4e00-\u9fff]{2,8})(拟|预计|首次|实控人|公告|半年|前三)", t)
    return m.group(1) if m else None


def _members(c, eid):
    return [dict(r) for r in c.execute(
        "SELECT a.id,a.title,a.feed_name,a.link FROM event_members em "
        "JOIN articles a ON em.article_id=a.id WHERE em.event_id=?", (eid,))]


def build(c):
    pairs = []
    seen = set()

    def add(a, b, label, kind, rationale):
        key = tuple(sorted((a["id"], b["id"])))
        if key in seen or a["id"] == b["id"]:
            return
        seen.add(key)
        pairs.append({
            "a_id": a["id"], "b_id": b["id"],
            "a_title": re.sub(r"<[^>]+>", "", a["title"] or "")[:80],
            "b_title": re.sub(r"<[^>]+>", "", b["title"] or "")[:80],
            "a_feed": a["feed_name"], "b_feed": b["feed_name"],
            "label": label, "kind": kind, "rationale": rationale,
            "needs_review": True,
        })

    # ---- 正对(应合并): 跨源同标题通稿 = ground truth 同故事(独立于聚类状态) ----
    # 规范化标题(去标点/空白/【】栏目前缀)后完全相同且来自不同feed → 必为同故事通稿。
    # 不依赖当前event成员，避免"guard已合并的必TP"循环论证；R(召回)才有真实意义。
    def _norm_title(t):
        t = re.sub(r"<[^>]+>", "", t or "")
        t = re.sub(r"^\s*[【\[][^】\]]*[】\]]\s*", "", t)
        return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", t).lower()

    pos_rows = list(c.execute("SELECT a.id,a.title,a.feed_name,a.link FROM articles a "
                              "JOIN article_vectors av ON a.id=av.article_id"))
    by_norm = {}
    for r in pos_rows:
        nt = _norm_title(r["title"])
        if len(nt) >= 8:  # 过短标题易碰撞，跳过
            by_norm.setdefault(nt, []).append(dict(r))
    groups = [g for g in by_norm.values() if len({m["feed_name"] for m in g}) >= 2]
    groups.sort(key=lambda g: -len({m["feed_name"] for m in g}))
    pos_added = 0
    for g in groups:
        if pos_added >= 25:
            break
        feeds = {}
        for m in g:
            feeds.setdefault(m["feed_name"], m)
        fl = list(feeds.values())
        if len(fl) < 2:
            continue
        a, b = fl[0], fl[1]
        why = "跨语言同标题通稿" if _en(a["title"]) != _en(b["title"]) else "跨源同标题通稿"
        add(a, b, "merge", "positive", f"{why}(ground truth, norm标题相同, 独立聚类)")
        pos_added += 1

    # ---- 负对1(不应合并): 不同公司主语的公告文章对(ground truth, 独立于聚类状态) ----
    # 用 ec.company_subject(需公司动作词)区分公司公告与媒体前缀(英媒/金融時報/外交部→None)。
    # 扫描窗口文章按公司核心分组，跨公司配对=应不合并。guard 正确则 TN，失败则 FP。
    neg_added = 0
    rows = list(c.execute("SELECT a.id,a.title,a.feed_name,a.link FROM articles a "
                          "JOIN article_vectors av ON a.id=av.article_id"))
    by_core = {}
    for r in rows:
        sj = ec.company_subject(r["title"])
        if sj:
            by_core.setdefault(sj[:2], dict(r))
    core_items = list(by_core.items())
    import random
    random.Random(42).shuffle(core_items)  # 确定性多样化：相邻核心配对，覆盖更多公司对
    for i in range(0, len(core_items) - 1, 2):
        if neg_added >= 10:
            break
        (ca, ma), (cb, mb) = core_items[i], core_items[i + 1]
        add(ma, mb, "no_merge", "neg_overmerge",
            f"不同公司({ca} vs {cb})公告，应不合并(ground truth, 独立聚类)")
        neg_added += 1

    # ---- 负对2(不应合并): 同实体不同故事(NVIDIA 跨事件 TN 候选) ----
    nv_events = list(c.execute(
        "SELECT DISTINCT e.event_id,e.label FROM events e "
        "JOIN event_entities ee ON e.event_id=ee.event_id "
        "JOIN entities en ON ee.entity_id=en.entity_id "
        "WHERE en.name LIKE '%NVIDIA%' OR en.name LIKE '%英伟达%' "
        "ORDER BY e.salience DESC LIMIT 8"))
    neg2 = 0
    for i in range(len(nv_events)):
        for j in range(i + 1, len(nv_events)):
            if neg2 >= 8:
                break
            ma = _members(c, nv_events[i]["event_id"])
            mb = _members(c, nv_events[j]["event_id"])
            if ma and mb:
                add(ma[0], mb[0], "no_merge", "neg_same_entity",
                    f"同NVIDIA实体不同故事: ev{nv_events[i]['event_id']}「{nv_events[i]['label'][:24]}」 vs ev{nv_events[j]['event_id']}「{nv_events[j]['label'][:24]}」")
                neg2 += 1

    # ---- 负对3(不应合并): 随机不同事件 ----
    import random
    random.seed(42)
    singles = list(c.execute("SELECT event_id FROM events WHERE n_indep_sources=1 ORDER BY salience DESC LIMIT 200"))
    neg3 = 0
    while neg3 < 7 and len(singles) >= 2:
        e1, e2 = random.sample(singles, 2)
        m1, m2 = _members(c, e1["event_id"]), _members(c, e2["event_id"])
        if m1 and m2:
            add(m1[0], m2[0], "no_merge", "neg_random", "随机不同事件(应不合并)")
            neg3 += 1

    os.makedirs(DATA, exist_ok=True)
    json.dump({"pairs": pairs, "n": len(pairs),
               "pos": sum(p["label"] == "merge" for p in pairs),
               "neg": sum(p["label"] == "no_merge" for p in pairs),
               "note": "启发式预标注 needs_review=true; 正式黄金集需人工复核(D3-A 盲评)"},
              open(GOLDEN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"build: {len(pairs)}对 (正{sum(p['label']=='merge' for p in pairs)}/负{sum(p['label']=='no_merge' for p in pairs)}) → {GOLDEN}")
    by_kind = collections.Counter(p["kind"] for p in pairs)
    print("  分布:", dict(by_kind))
    return pairs


def _event_of(c, aid):
    r = c.execute("SELECT event_id FROM event_members WHERE article_id=?", (aid,)).fetchone()
    return r["event_id"] if r else None


def evaluate(c, pairs=None):
    if pairs is None:
        pairs = json.load(open(GOLDEN, encoding="utf-8"))["pairs"]
    TP = FP = FN = TN = 0
    details = []
    for p in pairs:
        ea, eb = _event_of(c, p["a_id"]), _event_of(c, p["b_id"])
        merged = (ea is not None and ea == eb)
        gold = p["label"] == "merge"
        if gold and merged:
            TP += 1; verdict = "TP"
        elif (not gold) and merged:
            FP += 1; verdict = "FP"
        elif gold and not merged:
            FN += 1; verdict = "FN"
        else:
            TN += 1; verdict = "TN"
        details.append({**p, "ea": ea, "eb": eb, "merged": merged, "verdict": verdict})
    P = TP / (TP + FP) if (TP + FP) else 0.0
    R = TP / (TP + FN) if (TP + FN) else 0.0
    F1 = 2 * P * R / (P + R) if (P + R) else 0.0

    # §10 指标
    ev = c.execute("SELECT COUNT(*) n, SUM(n_indep_sources>=2) multi FROM events").fetchone()
    arts = c.execute("SELECT COUNT(*) n FROM article_vectors").fetchone()["n"]
    merge_rate = (arts - ev["n"]) / arts if arts else 0.0
    # 个人化命中率: TOP10 卡匹配 interest_profile 实体/主题占比
    hit = None
    cards_path = os.path.join(DATA, "cards_20261116.json")
    if os.path.exists(cards_path):
        cards = json.load(open(cards_path, encoding="utf-8"))
        cards = cards if isinstance(cards, list) else cards.get("cards", [])
        ip = {r["key"] for r in c.execute("SELECT key FROM interest_profile")}
        ents = {k.split(":", 1)[1] for k in ip if k.startswith("entity:")}
        topics = {k.split(":", 1)[1] for k in ip if k.startswith("topic:")}
        nhit = 0
        for cd in cards:
            pe = cd.get("primary_entities") or []
            tp = cd.get("topic") or ""
            if any(e in ents for e in pe) or tp in topics:
                nhit += 1
        hit = nhit / len(cards) if cards else 0.0
    report = {
        "dedup": {"TP": TP, "FP": FP, "FN": FN, "TN": TN,
                  "precision": round(P, 4), "recall": round(R, 4), "f1": round(F1, 4),
                  "target": "P>=0.85 R>=0.80 (WP3验收)",
                  "pass": P >= 0.85 and R >= 0.80},
        "metrics": {"events": ev["n"], "multi_source_events": ev["multi"],
                    "vectorized_articles": arts, "merge_rate": round(merge_rate, 4),
                    "personalization_hit_top10": round(hit, 4) if hit is not None else None},
        "fp_cases": [d for d in details if d["verdict"] == "FP"],
        "fn_cases": [d for d in details if d["verdict"] == "FN"],
        "details": details,
    }
    json.dump(report, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"eval: 去重 P={P:.3f} R={R:.3f} F1={F1:.3f} (TP{TP}/FP{FP}/FN{FN}/TN{TN})")
    print(f"  WP3验收 P>=0.85 R>=0.80: {'PASS' if report['dedup']['pass'] else 'FAIL'}")
    print(f"  合并率={merge_rate:.1%} 多源事件={ev['multi']} 个人化命中TOP10={hit}")
    if report["fp_cases"]:
        print(f"  过度合并FP {len(report['fp_cases'])}例:")
        for d in report["fp_cases"][:6]:
            print(f"    [{d['kind']}] {d['a_title'][:30]} || {d['b_title'][:30]}")
    if report["fn_cases"]:
        print(f"  欠合并FN {len(report['fn_cases'])}例:")
        for d in report["fn_cases"][:4]:
            print(f"    {d['a_title'][:30]} || {d['b_title'][:30]}")
    print(f"  → {REPORT}")
    return report


def ab_dashboard(c):
    """WP7 A/B 指标看板：A轨(原始流+标题去重基线) vs B轨(事件中心管线)。
    量化对比 重复度/信息源多样性/热点/个人化/品质 五维，渲染只读HTML发布到 /news/eval/，
    供用户盲评+拍板(D3-A)。A为重建基线(非旧简报实测)，定性盲评仍需用户。"""
    import intel
    WINDOW = 72
    rows = ec.window_articles(c, WINDOW)
    raw_n = len(rows)
    # A轨基线：原始文章流 + 规范化标题去重(旧规则模式，无语义事件聚类)
    titles = [ec.norm_title_key(r["title"]) for r in rows]
    uniq_titles = len(set(t for t in titles if t))
    naive_dup = 1 - uniq_titles / raw_n if raw_n else 0.0
    feeds_a = len({r["feed_name"] for r in rows})
    # B轨：事件中心
    rep = json.load(open(REPORT, encoding="utf-8")) if os.path.exists(REPORT) else {}
    dedup = rep.get("dedup", {})
    met = rep.get("metrics", {})
    ev_n = met.get("events", 0)
    merge_rate = met.get("merge_rate", 0.0)
    multi = met.get("multi_source_events", 0)
    pers = met.get("personalization_hit_top10")
    avg_indep = c.execute("SELECT AVG(n_indep_sources) a FROM events WHERE n_indep_sources>=2").fetchone()["a"] or 0
    n_ent = c.execute("SELECT COUNT(DISTINCT entity_id) n FROM event_entities").fetchone()["n"]
    top = ec.top_events(c, 10)
    # 品质：cards 数字核验率
    cards_path = os.path.join(DATA, "cards_20261116.json")
    verified_rate = None; n_cards = 0
    if os.path.exists(cards_path):
        cj = json.load(open(cards_path, encoding="utf-8"))
        cards = cj if isinstance(cj, list) else cj.get("cards", [])
        n_cards = len(cards)
        ok = sum(1 for cd in cards if cd.get("numbers_verified"))
        verified_rate = ok / n_cards if n_cards else 0.0
    semantic_gain = merge_rate - naive_dup
    ab = {
        "window_h": WINDOW, "raw_articles": raw_n,
        "A_baseline": {"mode": "原始流+标题去重(重建基线)", "unique_titles": uniq_titles,
                       "naive_dup_rate": round(naive_dup, 4), "feeds": feeds_a,
                       "semantic_dedup": False, "personalization": False, "numbers_verified": False},
        "B_event": {"mode": "事件中心管线", "events": ev_n, "merge_rate": round(merge_rate, 4),
                    "multi_source_events": multi, "avg_indep_sources": round(avg_indep, 2),
                    "distinct_entities": n_ent, "dedup_precision": dedup.get("precision"),
                    "dedup_recall": dedup.get("recall"), "dedup_f1": dedup.get("f1"),
                    "personalization_hit_top10": pers, "cards": n_cards,
                    "numbers_verified_rate": round(verified_rate, 4) if verified_rate is not None else None},
        "delta": {"semantic_dedup_gain": round(semantic_gain, 4),
                  "dup_rate_A_to_B": f"{naive_dup:.1%} → {merge_rate:.1%}"},
        "top10_hotspots": [{"event_id": r["event_id"], "salience": round(r["salience"], 2),
                            "n_indep": r["n_indep_sources"], "topic": r["topic"], "label": r["label"]} for r in top],
        "caveat": "A为重建基线(标题去重)非旧简报实测；50对黄金集启发式预标注needs_review；正式微信切换需用户盲评+拍板(D3-A)",
    }
    json.dump(ab, open(os.path.join(DATA, "ab_dashboard.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def pct(x):
        return f"{x:.1%}" if isinstance(x, (int, float)) else "—"
    top_rows = "".join(
        f'<tr><td>{i}</td><td>{intel._esc(r["label"][:50])}</td><td>{r["n_indep_sources"]}</td>'
        f'<td>{r["salience"]:.1f}</td><td>{intel._esc(r["topic"])}</td></tr>'
        for i, r in enumerate(top, 1))
    tbl_style = ('<style>table{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}'
                 'th,td{border:1px solid #e0e0e0;padding:6px 8px;text-align:left}'
                 'th{background:#f0f0f0}td:nth-child(2){color:#888}td:nth-child(3){color:#1a6b3a;font-weight:600}</style>')
    body = tbl_style + f'''
<div class="card"><h3>① 重复度（去重能力）</h3>
<table><tr><th>指标</th><th>A轨 基线</th><th>B轨 事件中心</th></tr>
<tr><td>窗口原始文章</td><td>{raw_n}</td><td>{raw_n}</td></tr>
<tr><td>去重后条目</td><td>{uniq_titles}(标题去重)</td><td>{ev_n}(语义事件)</td></tr>
<tr><td>重复去除率</td><td>{pct(naive_dup)}</td><td>{pct(merge_rate)}</td></tr>
<tr><td>语义去重增益</td><td>—</td><td>+{pct(semantic_gain)}</td></tr>
<tr><td>去重精度P / 召回R / F1</td><td>无评测</td><td>{dedup.get("precision","—")} / {dedup.get("recall","—")} / {dedup.get("f1","—")}</td></tr>
</table><p class="ents">B轨用向量+实体+标题同一性聚类，去除A轨标题去重抓不到的跨标题/跨语言/通稿语义重复。</p></div>
<div class="card"><h3>② 信息源多样性</h3>
<table><tr><th>指标</th><th>A轨</th><th>B轨</th></tr>
<tr><td>覆盖源数</td><td>{feeds_a}</td><td>{feeds_a}</td></tr>
<tr><td>多源 corroborated 事件</td><td>无事件概念</td><td>{multi}</td></tr>
<tr><td>多源事件平均独立源</td><td>—</td><td>{avg_indep:.2f}</td></tr>
<tr><td>覆盖实体数</td><td>—</td><td>{n_ent}</td></tr>
</table></div>
<div class="card"><h3>③ 热点追踪 TOP10（salience排序）</h3>
<table><tr><th>#</th><th>事件</th><th>独立源</th><th>S</th><th>主题</th></tr>{top_rows}</table>
<p class="ents">B轨 salience = 源权重×独立源数×velocity×burst×个人化兴趣，A轨仅时间序。</p></div>
<div class="card"><h3>④ 个人化 &amp; ⑤ 品质</h3>
<table><tr><th>指标</th><th>A轨</th><th>B轨</th></tr>
<tr><td>TOP10个人化命中</td><td>无</td><td>{pct(pers) if pers is not None else "—"}</td></tr>
<tr><td>四段卡数</td><td>无</td><td>{n_cards}</td></tr>
<tr><td>数字来源核验率</td><td>无</td><td>{pct(verified_rate) if verified_rate is not None else "—"}</td></tr>
</table></div>
<div class="card"><h3>⚠ 判读边界（诚实声明）</h3>
<p class="warn">{intel._esc(ab["caveat"])}</p>
<p class="ents">本看板为量化指标对比；简报定性品质(可读性/洞察/取舍)需用户盲评A/B实际正文后拍板。黄金集50对为启发式预标注，正式基准需人工复核。</p></div>
'''
    hpath = intel.write_html(os.path.join(intel.NEWS_WEB, "eval", "dashboard.html"),
                             "Wuhoo 新闻情报 A/B 指标看板", body)
    intel.publish_web()
    url = f"{intel.PUBLIC_BASE}/eval/dashboard.html"
    print("ab: A/B看板已生成")
    print(f"  A基线 标题去重率={naive_dup:.1%} | B事件 合并率={merge_rate:.1%} 语义增益=+{semantic_gain:.1%}")
    print(f"  B去重 P={dedup.get('precision')} R={dedup.get('recall')} F1={dedup.get('f1')} | 多源事件={multi} 平均独立源={avg_indep:.2f}")
    print(f"  个人化TOP10={pers} 数字核验率={verified_rate} 实体={n_ent}")
    print(f"  HTML: {hpath}")
    print(f"  公开链接: {url}")
    print(f"  JSON: {os.path.join(DATA, 'ab_dashboard.json')}")
    return ab


def _latest_a_brief():
    """从 A轨 cron 留档(d6d628cc68a1/*.md 全转录)提取最新规则简报正文。
    简报块=📰 Wuhoo RSS 资讯简报 ... 采集时间:行。取最后一次出现(末条=正文纪律)。只读。"""
    import glob
    adir = os.path.join(os.path.expanduser("~"), ".hermes/cron/output/d6d628cc68a1")
    files = sorted(glob.glob(os.path.join(adir, "*.md")), key=os.path.getmtime, reverse=True)
    for f in files[:5]:
        try:
            txt = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        ms = re.findall(r"(📰 Wuhoo RSS 资讯简报.*?采集时间:[^\n]*)", txt, re.DOTALL)
        if ms:
            return ms[-1].strip(), os.path.basename(f)
    return None, None


def blind_eval(c):
    """WP7 盲评归档页：A轨(规则引擎旧简报) vs B轨(事件中心新简报) 同日并排，
    供用户 2 周双轨观察期定性盲评(D3-A)。发布 /news/eval/blind.html。
    量化指标见 dashboard；本页供可读性/洞察/取舍/重复度主观判读。切换需用户拍板。"""
    import intel
    import glob
    a_text, a_src = _latest_a_brief()
    # B轨最新 brief_wechat
    bfiles = sorted(glob.glob(os.path.join(DATA, "brief_wechat_*.txt")), key=os.path.getmtime, reverse=True)
    b_text = open(bfiles[0], encoding="utf-8").read() if bfiles else "(B轨简报未产出)"
    b_stamp = ""
    m = re.search(r"brief_wechat_(\d{8})\.txt", bfiles[0]) if bfiles else None
    if m:
        s = m.group(1); b_stamp = f"{s[:4]}-{s[4:6]}-{s[6:]}"
    b_url = f"{intel.PUBLIC_BASE}/daily/{b_stamp}.html" if b_stamp else ""
    a_html = intel._esc(a_text or "(A轨留档未找到)").replace("\n", "<br>")
    b_html = intel._esc(b_text).replace("\n", "<br>")
    body = f'''
<style>.cols{{display:flex;gap:14px;flex-wrap:wrap}}.col{{flex:1;min-width:300px}}
.sample{{background:#fafafa;border:1px solid #e0e0e0;border-radius:8px;padding:12px;font-size:13px;line-height:1.7}}
.tag{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;margin-bottom:8px}}
.tagA{{background:#fde8e8;color:#a33}}.tagB{{background:#e8f5e9;color:#1a6b3a}}
.guide li{{margin:4px 0}}</style>
<div class="card"><h3>📋 双轨盲评说明（D3-A · 2周观察期）</h3>
<p>规则引擎(A轨)与事件中心(B轨)每日并行出两份简报。请连续观察约2周，按下列5维主观判读<b>新(B)是否≥旧(A)</b>，再拍板是否把微信推送切换到B轨。量化指标见 <a href="dashboard.html">A/B指标看板</a>。</p>
<ul class="guide">
<li><b>重复度</b>：同一事件是否多源重复刷屏？B轨语义聚类应更少重复。</li>
<li><b>信息源</b>：是否多源印证(≥2独立源)、来源可信多样？</li>
<li><b>热点</b>：头条是否真热点(salience=源权重×独立源×velocity×burst×兴趣)，而非仅时间序？</li>
<li><b>个人化</b>：是否贴合你的关注(投资/游戏/科技)？B轨 interest_profile 跨profile种子。</li>
<li><b>可读性/洞察</b>：B轨四段卡(事实/影响/分歧/下一步)+数字来源核验 vs A轨分类TOP5摘要。</li>
</ul>
<p class="ents">反馈调节(D3)：微信回复「多点X/少点X/这条没用」作用于B轨 interest_profile。A轨正则已冻结为fallback(只修bug不加规则)。</p></div>
<div class="cols">
<div class="col"><span class="tag tagA">样本 A · 规则引擎（旧 daily_briefing）</span>
<div class="sample">{a_html}</div>
<p class="ents">留档: {intel._esc(a_src or "—")} · 分类TOP5+关键词评分+噪声过滤+事件去重</p></div>
<div class="col"><span class="tag tagB">样本 B · 事件中心（新 intel brief）</span>
<div class="sample">{b_html}</div>
<p class="ents">微信摘要(≤4KB) · <a href="{b_url}">全量四段卡+≥2来源链接(只读)</a> · 数字来源核验</p></div>
</div>
<div class="card"><h3>⚠ 拍板边界</h3>
<p class="warn">本页为定性盲评材料。正式微信切换(B轨取代A轨推送)须用户观察期满后明确拍板(D3-A)；当前A轨仍推微信、B轨shadow只读链接，未切换。黄金集50对启发式预标注needs_review，量化PASS不替代人工盲评。</p></div>
'''
    hpath = intel.write_html(os.path.join(intel.NEWS_WEB, "eval", "blind.html"),
                             "Wuhoo 新闻情报 双轨盲评", body)
    intel.publish_web()
    url = f"{intel.PUBLIC_BASE}/eval/blind.html"
    print("blind: 双轨盲评页已生成")
    print(f"  A轨留档: {a_src} | 正文{len(a_text or '')}字")
    print(f"  B轨: {os.path.basename(bfiles[0]) if bfiles else '—'} | 全量 {b_url}")
    print(f"  HTML: {hpath}")
    print(f"  公开链接: {url}")
    return {"a_src": a_src, "b_url": b_url, "url": url}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "eval", "ab", "blind"])
    a = ap.parse_args()
    c = conn()
    if a.cmd == "build":
        build(c)
    elif a.cmd == "eval":
        evaluate(c)
    elif a.cmd == "ab":
        ab_dashboard(c)
    elif a.cmd == "blind":
        blind_eval(c)


if __name__ == "__main__":
    main()
