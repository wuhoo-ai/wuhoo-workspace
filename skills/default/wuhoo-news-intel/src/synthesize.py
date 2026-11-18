#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""WP4 合成与核验 — 逐事件四段卡 + 数字核验 + 链接引用 + 主体实体频次加权。

复用 event_center(clean_text/extract_entities/top_events/get_conn)。
LLM: token-plan qwen3.8-flash，关思考(结构化提取任务，省 token/降延迟)。
铁律: 只允许来源内事实 / 数字可溯源(否则标未核实) / 不编造链接 / 中文完整展开。

CLI:
  synthesize --top 30 [--out DIR] [--dry] [--budget 90000]
  dive --event 154 [--dry]
"""
import os
import sys
import json
import re
import time
import argparse
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import event_center as ec

BASE = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
# 2026-11-17 用户拍板: 生产模型 qwen4-max(效果优先档)。wire shape 与 qwen3.8 相同,
# reasoning_effort=none + thinking.disabled 实测 200 且无 reasoning tokens(探针验证)。
MODEL = "qwen4-max"
ENV_PATH = os.path.expanduser("~/.hermes/.env")
DATA_DIR = os.path.join(ec.HOME, "wuhoo-workspace/skills/default/wuhoo-news-intel/data")

SYSTEM = (
    "你是严谨的新闻事实合成器。铁律:"
    "①只允许使用给定来源材料内的事实,禁止编造任何来源外信息或背景;"
    "②每个数字必须能在来源材料中找到,并带单位(亿/万/%/美元/倍等);"
    "③禁止编造链接或来源名;"
    "④中文输出,完整展开讲清是什么/为什么,简洁克制,禁止名词堆叠;"
    "⑤严格区分'来源已证实的事实'与'推测/未核实',多源数字不一致须在 divergence 标注;"
    "⑥年份必须来自来源;来源只给月日未给年份时,按参考日期年份理解,严禁臆造2024等无关年份。"
    "只输出一个 JSON 对象,不要 markdown 围栏,不要额外解释。"
)

USER_TMPL = (
    '\n\n请基于以上来源材料输出 JSON(字段值均为中文字符串):'
    '{"fact":"事实:仅来源内已证实内容,数字带单位,2-3句讲清发生了什么",'
    '"impact":"影响:为什么重要,一句话",'
    '"divergence":"分歧/未核实:仅当多源数字或说法不一致时写,否则空字符串",'
    '"next_step":"下一步关注:接下来值得跟踪什么,一句话"}'
)


def load_key():
    k = os.environ.get("TOKEN_PLAN_API_KEY")
    if k:
        return k.strip()
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH, encoding="utf-8"):
            if line.startswith("TOKEN_PLAN_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


_KEY = None


def call_qwen(system, user, max_tokens=520, temperature=0.2):
    """关思考调用 qwen4-max(MODEL常量)。返回 {content,usage} 或 {error,quota}。
    429 退避重试(15/30/60s)后才标 quota——瞬时 RPM/TPM 限流不应停掉整个构建。"""
    global _KEY
    if _KEY is None:
        _KEY = load_key()
    if not _KEY:
        return {"error": "TOKEN_PLAN_API_KEY missing"}
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "reasoning_effort": "none",
        "extra_body": {"thinking": {"type": "disabled"}},
    }).encode("utf-8")
    req = urllib.request.Request(BASE + "/chat/completions", data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + _KEY,
    })
    last = None
    attempt = 0
    i429 = 0
    backoff_429 = (15, 30, 60)
    while attempt < 2:
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                r = json.loads(resp.read())
                return {
                    "content": r["choices"][0]["message"]["content"],
                    "usage": r.get("usage", {}),
                }
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code == 429:
                # 2026-11-18: 429 多为瞬时限流(门户v3构建实测), 先退避重试不消耗 attempt;
                # 连续失败才标 quota(真配额耗尽语义保留, Budget.quota 停止后续合成)。
                if i429 < len(backoff_429):
                    time.sleep(backoff_429[i429])
                    i429 += 1
                    continue
                return {"error": "429 quota/rate", "quota": True, "detail": body}
            last = {"error": f"HTTP {e.code}", "detail": body}
            if e.code < 500:
                return last
        except Exception as e:
            last = {"error": type(e).__name__ + ": " + str(e)[:200]}
        attempt += 1
    return last or {"error": "unknown"}


def parse_json(content):
    content = (content or "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{[\s\S]*\}", content)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {"fact": content, "impact": "", "divergence": "", "next_step": "", "_parse_failed": True}


# ---- 数字核验 ----
_NUM_RE = re.compile(
    r"\d[\d,]*\.?\d*\s*(?:%|％|亿|万|千|美元|元|美金|倍|个百分点|基点|bp|bps|GHz|MHz|nm|纳米|点|席|家|人|辆|台|艘|架|年|月|日|强|余|多)?"
)


def extract_numbers(text):
    return [m.group(0).strip() for m in _NUM_RE.finditer(text or "")]


def verify_numbers(fact, corpus, refdate=""):
    """事实中每个数字须能在来源语料匹配,否则列入未核实。
    日期 grounding: 参考日期(事件 last_seen 元数据)的年/月/日视为已证实,
    仅对日期词(年/月/日结尾)放行,不 whitewash 数量(如'16亿'仍须 corpus 匹配)。"""
    cn = (corpus or "").replace(",", "").replace("，", "").replace(" ", "")
    ry = rm = rd = None
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", refdate or "")
    if m:
        ry, rm, rd = m.group(1), str(int(m.group(2))), str(int(m.group(3)))
    unverified = []
    for raw in extract_numbers(fact):
        core = re.sub(r"[^\d.]", "", raw)
        if not core or core == ".":
            continue
        flat = raw.replace(",", "").replace(" ", "")
        if core in cn or flat in cn:
            continue
        # 浮点等价 (1.25 vs 1.250 / 365 vs 365.0)
        try:
            v = float(core)
            if any(abs(float(x) - v) < 1e-9 for x in re.findall(r"\d+\.?\d*", cn) if x):
                continue
        except ValueError:
            pass
        # 日期 grounding: 年/月/日 匹配参考日期 → 元数据已证实
        if raw.endswith("年") and len(core) == 4 and core == ry:
            continue
        if raw.endswith("月") and core == rm:
            continue
        if raw.endswith("日") and core == rd:
            continue
        unverified.append(raw)
    return unverified


def gather_context(conn, event_id, extra_ids=None):
    """extra_ids: brief 层同故事归并(P0-2)时并入的其他事件成员文章 id, 语料/实体/链接取并集。"""
    ev = conn.execute("SELECT * FROM events WHERE event_id=?", (event_id,)).fetchone()
    if not ev:
        return None
    members = conn.execute(
        "SELECT a.* FROM event_members m JOIN articles a ON a.id=m.article_id "
        "WHERE m.event_id=? ORDER BY m.similarity DESC", (event_id,)).fetchall()
    if extra_ids:
        have = {a["id"] for a in members}
        extra_rows = []
        for i in range(0, len(extra_ids), 500):
            ch = extra_ids[i:i + 500]
            qm = ",".join("?" * len(ch))
            extra_rows += conn.execute(f"SELECT * FROM articles WHERE id IN ({qm})", ch).fetchall()
        members = list(members) + [a for a in extra_rows if a["id"] not in have]
    if not members:
        return None
    canon = None
    if ev["canonical_id"]:
        canon = conn.execute("SELECT * FROM articles WHERE id=?", (ev["canonical_id"],)).fetchone()
    if canon is None:
        canon = members[0]
    ent_counter = Counter()
    corpus_parts = []
    for a in members:
        title = ec.clean_text(a["title"] or "")
        summ = ec.clean_text(a["summary"] or "")
        cont = ec.clean_text(a["content"] or "")
        ent_counter.update(ec.extract_entities(title + " " + summ))
        corpus_parts.append(title + " " + summ + " " + cont)
    canon_ents = ec.extract_entities(
        ec.clean_text(canon["title"] or "") + " " + ec.clean_text(canon["summary"] or ""))
    # 主体实体: ≥2 成员提及 或 出现在代表作 → 主体; 单源 incidental → 抑制(WP3 refinement)
    primary = sorted([e for e, c in ent_counter.items() if c >= 2 or e in canon_ents],
                     key=lambda e: -ent_counter[e])
    incidental = sorted([e for e, c in ent_counter.items() if c < 2 and e not in canon_ents])
    corpus = "\n".join(corpus_parts)
    return {"ev": ev, "members": members, "canon": canon,
            "primary": primary, "incidental": incidental, "corpus": corpus}


def build_user_prompt(ctx):
    ev, members, canon = ctx["ev"], ctx["members"], ctx["canon"]
    refdate = (ev["last_seen"] or "")[:10] or datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"事件: {ev['label']}",
        f"独立源数: {ev['n_indep_sources']}  主题: {ev['topic'] or '未分类'}",
        f"参考日期: {refdate}（来源未注明年份时按此年份理解，禁止臆造其他年份）",
        f"主体实体: {', '.join(ctx['primary'][:8]) or '无'}",
        "来源材料(标题|摘要):",
    ]
    budget = 2400
    used = 0
    for a in members:
        t = ec.clean_text(a["title"] or "")
        s = ec.clean_text(a["summary"] or "")[:180]
        seg = f"- [{a['feed_name']}] {t} | {s}"
        if used + len(seg) > budget:
            break
        lines.append(seg)
        used += len(seg)
    full = ec.clean_text(canon["content"] or canon["summary"] or "")[:700]
    if full:
        lines.append(f"代表作全文[{canon['feed_name']}]: {full}")
    return "\n".join(lines)[:3200] + USER_TMPL


def collect_links(ctx):
    canon, members = ctx["canon"], ctx["members"]
    urls, seen = [], set()
    order = ([canon] if canon else []) + [a for a in members if not canon or a["id"] != canon["id"]]
    for a in order:
        # link=文章 permalink(用户可达); 排除 localhost RSSHub feed(source_url 不可达)
        u = a["link"] or ""
        if not u or "127.0.0.1" in u or "localhost" in u:
            continue
        if u not in seen:
            seen.add(u)
            urls.append({"url": u, "feed": a["feed_name"]})
    return urls


def synthesize_event(conn, event_id, dry=False, store=True, extra_ids=None, merged_from=None):
    ctx = gather_context(conn, event_id, extra_ids=extra_ids)
    if not ctx:
        return {"event_id": event_id, "error": "no event/members"}
    ev, canon = ctx["ev"], ctx["canon"]
    user = build_user_prompt(ctx)
    # 归并卡(P0-2)独立源数按成员并集重算(通讯社归并); 未归并沿用事件落库值
    n_indep = (len({ec.wire_key(a["feed_name"]) for a in ctx["members"]})
               if extra_ids else ev["n_indep_sources"])
    base = {
        "event_id": event_id, "title": ev["label"], "topic": ev["topic"],
        "n_indep": n_indep, "salience": ev["salience"],
        "primary_entities": ctx["primary"][:8], "incidental_entities": ctx["incidental"][:8],
        "canonical_feed": canon["feed_name"], "links": collect_links(ctx),
    }
    if merged_from:
        base["merged_from"] = merged_from
    if dry:
        base["prompt_user"] = user
        base["dry"] = True
        return base
    res = call_qwen(SYSTEM, user)
    if "error" in res:
        base["error"] = res["error"]
        base["quota"] = res.get("quota", False)
        return base
    card = parse_json(res["content"])
    fact = card.get("fact", "") or ""
    refdate = (ev["last_seen"] or "")[:10] or datetime.now().strftime("%Y-%m-%d")
    unverified = verify_numbers(fact, ctx["corpus"], refdate=refdate)
    base.update({
        "fact": fact,
        "impact": card.get("impact", "") or "",
        "divergence": card.get("divergence", "") or "",
        "next_step": card.get("next_step", "") or "",
        "unverified_numbers": unverified,
        "numbers_verified": len(unverified) == 0,
        "parse_failed": card.get("_parse_failed", False),
        "usage": res.get("usage", {}),
    })
    if store and not base.get("parse_failed"):
        try:
            conn.execute(
                "INSERT INTO event_facts(event_id,claim,numbers,source_article_id,verified) VALUES(?,?,?,?,?)",
                (event_id, fact, json.dumps(unverified, ensure_ascii=False),
                 canon["id"], 1 if not unverified else 0))
            conn.commit()
        except Exception:
            pass
    return base


def format_card(c, idx):
    if c.get("error"):
        return f"{idx}. [event {c['event_id']}] 合成失败: {c['error']}"
    head = f"{idx}. 【{c['title']}】[{c['n_indep']}独立源] [{c['topic'] or '未分类'}]"
    lines = [head, f"   事实：{c['fact']}", f"   影响：{c['impact']}"]
    if c.get("divergence"):
        lines.append(f"   分歧/未核实：{c['divergence']}")
    if c.get("unverified_numbers"):
        lines.append(f"   ⚠数字未核实：{', '.join(c['unverified_numbers'])}")
    lines.append(f"   下一步关注：{c['next_step']}")
    links = " | ".join(l["url"] for l in c["links"][:4])
    lines.append(f"   来源：{links}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["synthesize", "dive"])
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--event", type=int)
    ap.add_argument("--out", default=DATA_DIR)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--budget", type=int, default=90000)
    a = ap.parse_args()
    conn = ec.get_conn()
    ec.refresh_dynamic_aliases(conn)
    os.makedirs(a.out, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")

    if a.cmd == "dive":
        if not a.event:
            raise SystemExit("dive 需 --event ID")
        c = synthesize_event(conn, a.event, dry=a.dry)
        print(json.dumps(c, ensure_ascii=False, indent=2))
        conn.close()
        return

    rows = ec.top_events(conn, a.top)
    cards, total_tokens, quota_hit = [], 0, False
    for i, r in enumerate(rows, 1):
        if total_tokens >= a.budget:
            print(f"[budget] 已达 {total_tokens} tokens,停止于第 {i} 条")
            break
        c = synthesize_event(conn, r["event_id"], dry=a.dry)
        cards.append(c)
        u = c.get("usage", {})
        total_tokens += u.get("total_tokens", 0) or 0
        if c.get("quota"):
            quota_hit = True
            print(f"[quota] 第 {i} 条 429,停止合成")
            break
        flag = "OK" if c.get("numbers_verified") else ("未核实:" + ",".join(c.get("unverified_numbers", [])) if not c.get("error") else "ERR:" + c["error"])
        print(f"[{i}/{len(rows)}] event {r['event_id']} N={r['n_indep_sources']} {flag} | {r['label'][:40]}")

    jpath = os.path.join(a.out, f"cards_{stamp}.json")
    tpath = os.path.join(a.out, f"cards_{stamp}.txt")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump({"date": stamp, "total_tokens": total_tokens, "quota_hit": quota_hit,
                   "n_cards": len(cards), "cards": cards}, f, ensure_ascii=False, indent=2)
    if not a.dry:
        with open(tpath, "w", encoding="utf-8") as f:
            f.write(f"📰 Wuhoo 事件简报四段卡 | {stamp} | {len(cards)}事件 | {total_tokens}tokens\n")
            f.write("=" * 48 + "\n\n")
            for i, c in enumerate(cards, 1):
                f.write(format_card(c, i) + "\n\n")
    ok = sum(1 for c in cards if c.get("numbers_verified"))
    err = sum(1 for c in cards if c.get("error"))
    print(f"\n合成完成: {len(cards)}卡 / 数字全核验 {ok} / 错误 {err} / tokens {total_tokens} / quota_hit {quota_hit}")
    print(f"JSON: {jpath}")
    if not a.dry:
        print(f"TEXT: {tpath}")
    conn.close()


if __name__ == "__main__":
    main()
