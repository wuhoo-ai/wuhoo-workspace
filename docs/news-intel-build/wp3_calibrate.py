#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""WP3 阈值实证校准：用真实 news.db 72h 文章向量，测同事件 vs 不同事件 cosine 分布。
- 同语言同事件 ground-truth = 标题指纹分组(≥2成员) → intra 分布 → 定 COS_DIRECT。
- 跨语/跨指纹同事件难自动 ground-truth：用共享规范实体对作候选，测分布 + 抽样人工判读 → 定 COS_ENTITY。
输出 wp3_calibration.json + 控制台百分位 + 高cosine实体共享对样本(判读假合并风险)。
"""
import sys, os, json, itertools, random
import numpy as np
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "wuhoo-workspace/skills/default/wuhoo-news-intel/src"))
from event_center import (get_conn, fingerprint, extract_entities, norm_rows,
                          window_articles, load_vectors)

random.seed(42)
conn = get_conn()
rows = window_articles(conn, 72)
ids = [r["id"] for r in rows]
vids, mat = load_vectors(conn, ids)
id2row = {r["id"]: r for r in rows}
vindex = {a: i for i, a in enumerate(vids)}
print(f"校准样本: {len(vids)} 篇有向量")

# 指纹分组（同语言近重复 = 同事件 ground-truth）
groups = {}
for aid in vids:
    fp = fingerprint(id2row[aid]["title"])
    if fp:
        groups.setdefault(fp, []).append(aid)
multi = {k: v for k, v in groups.items() if len(v) >= 2}
print(f"指纹组={len(groups)} 多成员组(同事件候选)={len(multi)}")

intra = []
for k, v in multi.items():
    for a, b in itertools.combinations(v, 2):
        intra.append(float(mat[vindex[a]] @ mat[vindex[b]]))

# 不同事件：随机跨指纹对
inter = []
keys = [k for k in groups if len(groups[k]) >= 1]
for _ in range(4000):
    k1, k2 = random.sample(keys, 2)
    a = random.choice(groups[k1]); b = random.choice(groups[k2])
    inter.append(float(mat[vindex[a]] @ mat[vindex[b]]))

# 共享规范实体的跨指纹对（跨语同事件候选 + 同实体不同事件混入）
ent_map = {}
for aid in vids:
    r = id2row[aid]
    for en in extract_entities((r["title"] or "") + " " + (r["summary"] or "")):
        ent_map.setdefault(en, []).append(aid)
ent_pairs = []
seen = set()
for en, lst in ent_map.items():
    if len(lst) < 2:
        continue
    for a, b in itertools.combinations(lst[:40], 2):
        if fingerprint(id2row[a]["title"]) == fingerprint(id2row[b]["title"]):
            continue  # 排除同指纹(已在intra)
        key = (min(a, b), max(a, b))
        if key in seen:
            continue
        seen.add(key)
        s = float(mat[vindex[a]] @ mat[vindex[b]])
        ent_pairs.append((s, en, a, b))
ent_cos = [x[0] for x in ent_pairs]


def pct(x, p):
    return round(float(np.percentile(x, p)), 3) if x else None


report = {
    "n_vectors": len(vids),
    "n_intra_pairs": len(intra),
    "intra_same_event": {p: pct(intra, q) for p, q in
                         [("p1", 1), ("p5", 5), ("p10", 10), ("p25", 25), ("p50", 50), ("p90", 90)]},
    "n_inter_pairs": len(inter),
    "inter_diff_event": {p: pct(inter, q) for p, q in
                         [("p50", 50), ("p90", 90), ("p95", 95), ("p99", 99), ("max", 100)]},
    "n_entity_shared_pairs": len(ent_cos),
    "entity_shared": {p: pct(ent_cos, q) for p, q in
                      [("p50", 50), ("p75", 75), ("p90", 90), ("p95", 95), ("max", 100)]},
}
print("\n=== 同语言同事件 intra cosine ===")
print(json.dumps(report["intra_same_event"], ensure_ascii=False))
print("=== 不同事件 inter cosine ===")
print(json.dumps(report["inter_diff_event"], ensure_ascii=False))
print("=== 共享实体跨指纹对 cosine(混合同事件/同实体不同事件) ===")
print(json.dumps(report["entity_shared"], ensure_ascii=False))

# 高cosine实体共享对样本（人工判读：同事件 vs 同实体不同事件 → 假合并风险）
ent_pairs.sort(reverse=True)
print("\n=== TOP20 高cosine实体共享对(判读COS_ENTITY假合并风险) ===")
samples = []
for s, en, a, b in ent_pairs[:20]:
    ta = id2row[a]["title"][:55]; tb = id2row[b]["title"][:55]
    print(f"cos={s:.3f} [{en}] {ta} || {tb}")
    samples.append({"cos": round(s, 3), "entity": en, "a": ta, "b": tb})
report["top_entity_pairs"] = samples

# 推荐阈值
if intra and inter:
    rec_direct = max(0.80, pct(intra, 10))     # 覆盖90%同语言同事件
    rec_entity = round((pct(inter, 99) + pct(intra, 25)) / 2, 3) if intra else 0.70
    report["recommend"] = {"COS_DIRECT": round(rec_direct, 3), "COS_ENTITY_draft": rec_entity,
                           "note": "COS_ENTITY须结合TOP20判读:跨语同事件~0.78,同实体不同事件假合并风险定下限"}
    print("\n=== 推荐 ===")
    print(json.dumps(report["recommend"], ensure_ascii=False))

out = os.path.join(os.path.expanduser("~"), "wuhoo-workspace/docs/news-intel-build/wp3_calibration.json")
json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n已写 {out}")
conn.close()
