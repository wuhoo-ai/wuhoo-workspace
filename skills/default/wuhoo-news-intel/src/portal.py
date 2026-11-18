#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""门户生成器 — tophub 式分类情报门户（2026-11-17 用户拍板全推荐案）。

六区: A顶栏 / B今日总览 / C分类热点(13类×≤4卡+类目导读) / D兴趣深挖(持仓雷达+六段增强卡+全文深读)
     / E热榜交叉验证(榜中榜式) / F归档与工具。
知识档: 主体 L2(四段卡+导读) + 兴趣区 L3(六段+背景标注+Jina全文)。
单文件静态 HTML + 原生 JS(搜索/类目tab/展开收起/夜间模式), 移动优先, 无外部依赖。
铁律沿用: 数字只来自语料并经 verify_numbers; 背景段显式标注"模型知识,非当日报道";
         覆盖降级横幅; 预算/配额有界; 微信版不受影响(仍由 intel.py brief 产出 ≤4KB)。

CLI:
  portal.py build [--edition morning|evening] [--budget 90000] [--dry] [--no-llm]
  --dry    只打印分类/候选/兴趣/热榜匹配计划, 不调 LLM 不写 HTML
  --no-llm 从已存 portal JSON 重渲染 HTML(改样式/回滚验证用, 零 token)
"""
import os
import sys
import json
import re
import glob
import argparse
import difflib
import urllib.request
from datetime import datetime
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import event_center as ec
import synthesize as sy
import intel

DATA = intel.DATA
NEWS_WEB = intel.NEWS_WEB
SERVE_DIR = intel.SERVE_DIR
PUBLIC_BASE = intel.PUBLIC_BASE
WINDOW_H = 72
DEEP_PER_CAT = 4     # 每类目深度卡(四段LLM合成)数
DEEP_CAND = 6        # 送归并的头部候选池上限(限制传递闭包过并, 保住热度榜多样性)
CAND_PER_CAT = 40    # 每类目候选上限(动态上限最大40)
LIST_MIN = 8         # 每类目热度榜总条目下限(含深度卡)
LIST_MAX = 40        # 默认上限(被CAT_LIST_MAX按类目覆盖)
HEAT_RATIO = 0.25    # 热度榜纳入: sel >= 类目最高分×此比例
COLD_CAP = 5.0       # 类目最高分<此值=冷类目, 条目封顶LIST_MIN
# 动态上限(2026-11-18用户拍板A): 高量40/中量25/薄10。热度榜紧凑卡无LLM, 扩容零token增量。
CAT_LIST_MAX = {
    "finance": 40, "ai_tech": 40, "macro": 40, "us_stock": 40,
    "a_hk": 25, "commodity": 25, "pharma": 25, "new_energy": 25,
    "consumer": 25, "geopolitics": 25,
    "gaming": 10, "crypto": 10, "football": 10,
}
# 类目选择分加权(2026-11-18用户拍板B: 军工提权)
CAT_SALIENCE_MULT = {"geopolitics": 1.3}
ENHANCED_TOP = 3     # 兴趣深挖增强卡数
JINA_CAP = 6000      # 单篇全文抓取字符上限
JINA_TIMEOUT = 25
WEBROOT = "/news"    # 内部链接绝对前缀(index与portal归档共用, 修归档相对链接断裂)

# ---- 13 类目（2026-11-18用户拍板B: +美股/医药健康/地缘与军工/新能源与汽车/消费）: key, 显示名, floor ----
CATEGORIES = [
    ("finance",    "财经",         2.0),
    ("us_stock",   "美股",         2.0),
    ("a_hk",       "A股港股",      2.0),
    ("macro",      "宏观与政策",   2.0),
    ("geopolitics","地缘与军工",   1.5),
    ("ai_tech",    "AI与科技",     2.0),
    ("pharma",     "医药健康",     1.0),
    ("new_energy", "新能源与汽车", 1.0),
    ("consumer",   "消费",         1.0),
    ("commodity",  "商品期货",     0.5),
    ("crypto",     "加密",         0.5),
    ("gaming",     "游戏",         0.5),
    ("football",   "足球",         0.0),
]
CAT_NAME = {k: n for k, n, _ in CATEGORIES}
CAT_FLOOR = {k: f for k, _, f in CATEGORIES}

# 分类关键词优先级: crypto > commodity > new_energy > pharma > consumer > us_stock > a_hk
#   > geopolitics > macro > ai_tech > gaming > football > finance兜底
# sector类目(新能源/医药/消费)在a_hk前→持仓个股按主题归sector; 无sector关键词的持仓经实体兜底归a_hk。
CAT_PATTERNS = [
    ("crypto", re.compile(
        r"比特币|以太坊|\bBTC\b|\bETH\b|加密货币|加密资产|稳定币|USDT|USDC|Solana|\bSOL\b|XRP|瑞波|"
        r"狗狗币|币安|Coinbase|\bCOIN\b|数字资产|区块链|Bitcoin|Ethereum|Crypto|Cointelegraph|Decrypt|PANews|Odaily", re.I)),
    ("commodity", re.compile(
        r"原油|WTI|布伦特|Brent|黄金|金价|白银|铜价|铁矿石|螺纹钢|焦煤|焦炭|动力煤|天然气|"
        r"OPEC|欧佩克|大豆|豆粕|玉米|棕榈油|碳酸锂|多晶硅|工业硅|期货|大宗商品|COMEX|LME|"
        r"沪金|沪银|沪铜|现货黄金|伦敦金|贵金属|基本金属", re.I)),
    ("new_energy", re.compile(
        r"新能源|电动车|电动汽车|锂电|锂电池|动力电池|固态电池|充电桩|换电|氢能|光伏|风电|储能|"
        r"蔚来|小鹏|理想汽车|比亚迪|宁德时代|CATL|电池回收|汽车销量|新能源汽车|CnEVPost|InsideEVs|"
        r"锂价|电池级|整车|车企|交付量|钴|镍矿", re.I)),
    ("pharma", re.compile(
        r"医药|生物医药|疫苗|创新药|医保|集采|恒瑞|药明|CXO|制药|临床|FDA|抗癌|肿瘤|癌症|"
        r"基因|医疗|医院|药品|GLP-1|减肥药|司美格鲁肽|肠癌|筛查|诊断|疗法|药物|Endpoints|STAT News|"
        r"医疗器械|仿制药|原料药|中药|药企|生物制药|医保目录", re.I)),
    ("consumer", re.compile(
        r"消费|零售(?!销售)|电商|双十一|双11|茅台|五粮液|白酒|餐饮|旅游|免税|奢侈品|拼多多|京东|美团|"
        r"社零|消费复苏|消费品|啤酒|乳业|食品|饮料|家电|美妆|化妆品|黄金珠宝|消费券|"
        r"以旧换新|国补|服饰|品牌消费|餐饮旅游", re.I)),
    ("us_stock", re.compile(
        r"美股|纳斯达克|纳指|标普500|标普|道琼斯|道指|纽交所|NYSE|Nasdaq|S&P 500|Dow Jones|"
        r"华尔街|FITB|FAST|HBAN|Fifth Third|Fastenal|Huntington|摩根大通|高盛|摩根士丹利|美国银行|"
        r"花旗|富国|伯克希尔|巴菲特|中概股|金龙指数|ADR|美股持仓|罗素2000|恐慌指数|\bVIX\b|"
        r"美股IPO|纳斯达克IPO|华尔街日报|美股三大|美国股市", re.I)),
    ("a_hk", re.compile(
        r"A股|港股|沪指|上证|深证|深成指|创业板|科创板|北交所|北证|新股|申购|中签|恒生|恒指|"
        r"港交所|沪深|北向资金|南向资金|涨停|跌停|A50|富时中国|中国平安|意华股份|中贝通信|"
        r"A股三大指数|人民币中间价|上交所|深交所|沪深300|中证500|两融|融资融券|"
        r"港股通|红筹|H股|保荐|招股|聆讯|回购注销|国债逆回购", re.I)),
    ("geopolitics", re.compile(
        r"军工|国防|导弹|战机|战斗机|俄乌|北约|台海|南海|朝鲜|伊朗|以色列|制裁|军演|地缘|"
        r"普京|泽连斯基|金正恩|内塔尼亚胡|莫迪|安瓦尔|李在明|国事访问|双边|峰会|APEC|G20|外交|"
        r"国防部|军事|武器|核武|乌克兰|俄罗斯|加沙|哈马斯|真主党|胡塞|霍尔木兹|油轮|水雷|"
        r"关税|贸易战|中美经贸|中加|中欧|特朗普关税|驱逐|大使|领事|停火|国防预算|军费|阅兵|"
        r"航母|潜艇|边境|地缘政治|军事演习", re.I)),
    ("macro", re.compile(
        r"美联储|\bFed\b|央行|人民银行|利率|降息|加息|CPI|PPI|GDP|PMI|非农|就业报告|"
        r"财政部|国务院|发改委|政治局|LPR|MLF|逆回购|财政政策|货币政策|通胀|通缩|失业率|"
        r"国债收益率|美债|贝森特|鲍威尔|拉加德|植田和男|经济数据|零售销售|工业产出|贸易帐|"
        r"经常账户|财政赤字|政府关门|债务上限|日本央行|欧洲央行|英国央行|社融|M2|信贷|GDP增速", re.I)),
    ("ai_tech", re.compile(
        r"OpenAI|ChatGPT|GPT-|Claude|Gemini|大模型|人工智能|英伟达|NVIDIA|芯片|半导体|台积电|"
        r"GPU|机器人|自动驾驶|特斯拉|苹果|iPhone|谷歌|微软|\bMeta\b|量子|\bAI\b|Anthropic|DeepSeek|"
        r"算力|数据中心|Rubin|黄仁勋|Jensen|Product Hunt|HuggingFace|开源模型|智能体|"
        r"光刻|晶圆|HBM|封装|ASML|EDA|碳化硅|芯片制造", re.I)),
    ("gaming", re.compile(
        r"游戏|Steam|Unity|Godot|Blender|任天堂|PlayStation|PS5|Xbox|电竞|原神|王者荣耀|"
        r"独立游戏|guimei|皮影|shader|\brig\b|游戏引擎|虚幻引擎|Unreal|NBA 2K|GTA|Take-Two|"
        r"GameLook|IGN|机核|游戏葡萄|触乐|版号|手游|主机|掌机|Switch|游戏科学|黑神话", re.I)),
    ("football", re.compile(
        r"足球|英超|西甲|意甲|德甲|法甲|欧冠|欧联|世界杯|预选赛|国足|中超|转会|进球|点球|"
        r"红牌|黄牌|梅西|C罗|姆巴佩|哈兰德|贝林厄姆|阿森纳|曼城|利物浦|皇马|巴萨|拜仁|尤文|"
        r"国际米兰|AC米兰|热刺|切尔西|曼联|足总杯|国王杯|解放者杯|懂球帝|直播吧", re.I)),
]
A_HK_ENTS = {"CATL", "MOUTAI", "WULIANGYE", "PINGAN", "HENGRUI", "YIHUA", "ZHONGBEI"}

PLATFORM_NAME = {
    "ithome": "IT之家", "36kr": "36氪", "wallstreetcn-hot": "华尔街见闻",
    "bilibili-hot-search": "B站热搜", "github-trending-today": "GitHub趋势",
    "producthunt": "Product Hunt", "hackernews": "Hacker News", "juejin": "掘金",
    "v2ex": "V2EX", "solidot": "Solidot", "sputniknewscn": "卫星通讯社",
    "thepaper": "澎湃", "ifeng": "凤凰网", "tieba": "贴吧", "zhihu": "知乎",
    "weibo": "微博", "toutiao": "头条", "baidu": "百度", "douyin": "抖音",
}

DIGEST_SYSTEM = (
    "你是新闻类目编辑。给定某类目今日事件卡的标题与事实,写一段100-200字的类目导读:"
    "讲清今天这个领域发生了什么、主线是什么、值得注意的信号。中文完整展开,禁止名词堆叠,"
    "只使用给定材料内的事实,不编造数字。只输出导读正文,不要标题不要围栏。")
OVERVIEW_SYSTEM = (
    "你是情报主编。给定今日各类目的导读与头条标题,输出结构化今日总览,要求逻辑清晰、条目化、可读性强:"
    "mainline=一句话主线(今日最重要的跨类目脉络);points=3-5个条目,每条head为6-12字小标题、"
    "body为2-3句展开讲清是什么/为什么/关联;watch=一句话值得跟踪的信号。"
    "只使用给定材料,不编造数字,中文完整展开禁止名词堆叠。"
    '只输出一个JSON对象不要围栏: {"mainline":"...","points":[{"head":"...","body":"..."}],"watch":"..."}')
ENHANCED_SYSTEM = (
    "你是严谨的新闻知识合成器。铁律:"
    "①fact/impact/data/divergence/next_step 只允许使用给定来源材料内的事实,数字带单位且可溯源;"
    "②background 段允许用你的背景知识补充事件脉络(公司主业/历史背景/机制解释),"
    "但必须以'背景补充(模型知识,非当日报道):'开头,且不得包含具体数字/日期/价格等需溯源的事实;"
    "③禁止编造链接或来源名;④中文完整展开讲清是什么/为什么,简洁克制;"
    "⑤年份必须来自来源,来源只给月日时按参考日期年份理解。"
    "只输出一个JSON对象,不要markdown围栏: "
    '{"fact":"事实2-3句","background":"背景补充(模型知识,非当日报道):...",'
    '"impact":"影响:为什么重要","data":"关键数据:来源内数字带单位,无则空字符串",'
    '"divergence":"分歧/未核实,无则空字符串","next_step":"下一步关注"}')


def classify(ev, ents):
    """事件 → 13类目之一。关键词优先(sector在a_hk前), 持仓实体兜底a_hk, 再topic兜底。"""
    text = (ev["label"] or "") + " " + (ev["topic"] or "")
    for key, pat in CAT_PATTERNS:
        if pat.search(text):
            return key
    if ents & A_HK_ENTS:
        return "a_hk"
    topic = ev["topic"] or ""
    if topic in ("AI", "科技"):
        return "ai_tech"
    if topic == "游戏":
        return "gaming"
    if topic == "足球":
        return "football"
    if topic == "医药":
        return "pharma"
    if topic == "新能源":
        return "new_energy"
    if topic == "加密":
        return "crypto"
    if topic == "军工":
        return "geopolitics"
    return "finance"


def load_window(c):
    """72h窗口active事件 + 实体映射(批量) + 噪声过滤 + 分类。"""
    cutoff = (intel.now() - __import__("datetime").timedelta(hours=WINDOW_H)).isoformat()
    rows = c.execute(
        "SELECT event_id,label,topic,salience,n_indep_sources,canonical_id,last_seen "
        "FROM events WHERE status='active' AND last_seen>=? ORDER BY salience DESC",
        (cutoff,)).fetchall()
    eids = [r["event_id"] for r in rows]
    ent_map = defaultdict(set)
    for i in range(0, len(eids), 500):
        ch = eids[i:i + 500]
        qm = ",".join("?" * len(ch))
        for r in c.execute(
                f"SELECT ee.event_id, en.name FROM event_entities ee "
                f"JOIN entities en ON ee.entity_id=en.entity_id WHERE ee.event_id IN ({qm})", ch):
            ent_map[r["event_id"]].add(r["name"])
    keep = intel.interest_watch_entities(c)
    out, n_noise = [], 0
    for r in rows:
        if intel.is_noise_candidate(c, r, keep):
            n_noise += 1
            continue
        d = dict(r)
        d["ents"] = ent_map.get(r["event_id"], set())
        d["cat"] = classify(r, d["ents"])
        d["sel"] = intel.sel_score(r) * CAT_SALIENCE_MULT.get(d["cat"], 1.0)
        out.append(d)
    return out, keep, n_noise


def jina_fulltext(url):
    """Jina Reader 抓全文(免费,无key)。失败/空 → None, 调用方降级用摘要。"""
    try:
        req = urllib.request.Request("https://r.jina.ai/" + url,
                                     headers={"User-Agent": "wuhoo-portal/1.0"})
        with urllib.request.urlopen(req, timeout=JINA_TIMEOUT) as resp:
            txt = resp.read().decode("utf-8", "replace")
        txt = ec.clean_text(txt)
        if len(txt) < 200 or "CAPTCHA" in txt[:400] or "Just a moment" in txt[:400]:
            return None
        return txt[:JINA_CAP]
    except Exception:
        return None


class Budget:
    def __init__(self, limit):
        self.limit = limit
        self.tokens = 0
        self.quota = False
        self.calls = 0

    def ok(self):
        return not self.quota and self.tokens < self.limit

    def llm(self, system, user, max_tokens=600):
        if not self.ok():
            return None
        res = sy.call_qwen(system, user, max_tokens=max_tokens)
        self.calls += 1
        u = res.get("usage", {}) or {}
        self.tokens += u.get("total_tokens", 0) or 0
        if res.get("quota"):
            self.quota = True
            intel.log_ops("portal LLM 429 quota, 停止后续合成")
            return None
        if "error" in res:
            intel.log_ops(f"portal LLM 失败: {res['error']}")
            return None
        return res.get("content", "")


def dedup_heat(c, heat_evs, deep_evs, keep):
    """热度榜跨语/跨源去重(2026-11-18用户拍板E): 贪心非传递——按sel降序, 与已保留项
    (深度卡primary优先占位+已留heat)比对 same_story_rule, 命中则丢弃(避免中英同故事重复展示)。
    不做union-find传递闭包(防过并吞多样性)。返回(去重后list, 丢弃数)。"""
    if not heat_evs:
        return [], 0
    pool = list(deep_evs) + list(heat_evs)
    vids, mat = ec.load_vectors(c, [e["canonical_id"] for e in pool])
    vmap = {aid: mat[i] for i, aid in enumerate(vids)}
    ents = {e["event_id"]: intel.candidate_entities(c, e["event_id"]) for e in pool}
    strong = set(ec.ENTITY_ALIASES.values()) | keep

    def is_dup(a, b):
        va, vb = vmap.get(a["canonical_id"]), vmap.get(b["canonical_id"])
        cos = float(va @ vb) if va is not None and vb is not None else 0.0
        shared = ents[a["event_id"]] & ents[b["event_id"]]
        return intel.same_story_rule(a["topic"], b["topic"], shared, strong, cos)

    kept = list(deep_evs)
    out, ndup = [], 0
    for e in sorted(heat_evs, key=lambda x: -x["sel"]):
        if any(is_dup(e, k) for k in kept):
            ndup += 1
            continue
        out.append(e)
        kept.append(e)
    return out, ndup


def synthesize_category(c, evs, keep, budget):
    """单类目: 按热度定条目数N(8-动态上限40)→头部DEEP_CAND候选归并→前DEEP_PER_CAT组深度卡(LLM四段)
    +其余候选热度榜紧凑卡(无LLM, 不做全局传递归并, 保住多样性)→导读。
    2026-11-18: 归并仅限头部池——财报日同一主语(如NVIDIA)10+事件经union-find传递闭包会塌缩成
    1张巨卡吞空热度榜; 限定头部6候选归并出深度卡, 热度榜取剩余候选独立呈现。
    返回 {cards(深度), heat_list(紧凑), digest, merged, mode, n_total}。"""
    cat = evs[0]["cat"] if evs else "finance"
    list_max = CAT_LIST_MAX.get(cat, LIST_MAX)
    top_sel = evs[0]["sel"] if evs else 0.0
    n_heat = len([e for e in evs if e["sel"] >= top_sel * HEAT_RATIO])
    N = max(LIST_MIN, min(list_max, n_heat))
    if top_sel < COLD_CAP:
        N = min(N, LIST_MIN)
    N = min(N, len(evs), CAND_PER_CAT)
    cands = evs[:N]
    ev_by_id = {e["event_id"]: e for e in cands}
    rows = [c.execute(
        "SELECT event_id,label,topic,salience,n_indep_sources,canonical_id,last_seen "
        "FROM events WHERE event_id=?", (e["event_id"],)).fetchone() for e in cands]
    row_by_id = {r["event_id"]: r for r in rows if r}
    deep_rows = [row_by_id[e["event_id"]] for e in cands[:DEEP_CAND] if e["event_id"] in row_by_id]
    groups, mode, usage = intel.build_groups(c, deep_rows, keep)
    budget.tokens += usage.get("total_tokens", 0) or 0
    budget.calls += 1
    deep_groups = groups[:DEEP_PER_CAT]
    cards, merged = [], []
    for g in deep_groups:
        if not budget.ok():
            break
        primary = g[0]
        extra_eids = [ev["event_id"] for ev in g[1:]]
        extra_aids = []
        for eid in extra_eids:
            extra_aids += [r[0] for r in c.execute(
                "SELECT article_id FROM event_members WHERE event_id=?", (eid,))]
        cd = sy.synthesize_event(c, primary["event_id"], store=True,
                                 extra_ids=extra_aids or None,
                                 merged_from=[ev["event_id"] for ev in g] if extra_eids else None)
        budget.tokens += cd.get("usage", {}).get("total_tokens", 0) or 0
        budget.calls += 1
        if cd.get("quota"):
            budget.quota = True
        if extra_eids:
            merged.append({"primary": primary["event_id"], "merged": extra_eids})
        cards.append(cd)
    # 热度榜: 头部池未进深度卡的组 + 头部池之外的候选, 各自独立(无传递归并)
    used = {ev["event_id"] for g in deep_groups for ev in g}
    heat_evs = []
    for g in groups[DEEP_PER_CAT:]:
        e = ev_by_id.get(g[0]["event_id"])
        if e and e["event_id"] not in used:
            heat_evs.append(e)
    for e in cands[DEEP_CAND:]:
        if e["event_id"] not in used:
            heat_evs.append(e)
    # 跨语/跨源去重(用户拍板E): 与深度卡primary+已留heat比对same_story_rule, 贪心非传递
    heat_evs, n_heat_dup = dedup_heat(c, heat_evs, [g[0] for g in deep_groups], keep)
    heat_list = [compact_card_data(c, e, [row_by_id[e["event_id"]]])
                 for e in heat_evs if e["event_id"] in row_by_id]
    digest = ""
    if cards and budget.ok():
        lines = [f"- {cd.get('title','')}: {(cd.get('fact','') or '')[:120]}"
                 for cd in cards if not cd.get("error")]
        content = budget.llm(DIGEST_SYSTEM, "类目事件:\n" + "\n".join(lines), max_tokens=400)
        digest = (content or "").strip()
    return {"cards": cards, "heat_list": heat_list, "digest": digest,
            "merged": merged, "mode": mode, "heat_dup": n_heat_dup,
            "n_total": len(cards) + len(heat_list)}


def enhanced_card(c, ev, keep, budget):
    """兴趣深挖六段增强卡: 全文深读(Jina top2链接) + 背景段(标注) + 数字核验。"""
    ctx = sy.gather_context(c, ev["event_id"])
    if not ctx:
        return None
    links = sy.collect_links(ctx)
    fulltexts, fetched = [], []
    for l in links[:2]:
        if not budget.ok():
            break
        ft = jina_fulltext(l["url"])
        if ft:
            fulltexts.append(f"全文[{l['feed']}]: {ft}")
            fetched.append(l["url"])
    user = sy.build_user_prompt(ctx)
    if fulltexts:
        user = user.replace(sy.USER_TMPL, "") + "\n" + "\n".join(fulltexts)[:JINA_CAP * 2] + \
            '\n\n请输出六段JSON(字段值均中文字符串): {"fact":"事实2-3句",' \
            '"background":"背景补充(模型知识,非当日报道):公司主业/历史脉络/机制解释,不含具体数字日期价格",' \
            '"impact":"影响","data":"关键数据(来源内数字带单位,无则空)","divergence":"分歧/未核实(无则空)",' \
            '"next_step":"下一步关注"}'
    else:
        user = user.replace(sy.USER_TMPL, "") + \
            '\n\n请输出六段JSON: {"fact":"事实2-3句","background":"背景补充(模型知识,非当日报道):...",' \
            '"impact":"影响","data":"关键数据(无则空)","divergence":"分歧(无则空)","next_step":"下一步"}'
    content = budget.llm(ENHANCED_SYSTEM, user[:6000], max_tokens=900)
    if not content:
        return None
    card = sy.parse_json(content)
    corpus = ctx["corpus"] + "\n" + "\n".join(fulltexts)
    refdate = (ev["last_seen"] or "")[:10]
    unv = sy.verify_numbers(card.get("fact", ""), corpus, refdate) + \
        sy.verify_numbers(card.get("data", ""), corpus, refdate)
    bg = card.get("background", "") or ""
    if bg and not bg.startswith("背景补充"):
        bg = "背景补充(模型知识,非当日报道):" + bg
    return {
        "event_id": ev["event_id"], "title": ev["label"], "cat": ev["cat"],
        "salience": ev["salience"], "n_indep": ev["n_indep_sources"],
        "fact": card.get("fact", ""), "background": bg, "impact": card.get("impact", ""),
        "data": card.get("data", ""), "divergence": card.get("divergence", ""),
        "next_step": card.get("next_step", ""), "unverified_numbers": unv,
        "numbers_verified": not unv, "links": links[:6], "fulltext_fetched": fetched,
        "primary_entities": ctx["primary"][:8],
    }


def interest_zone(c, evs, keep, budget):
    """持仓雷达(无LLM) + 增强卡(top3) + watchlist命中流(无LLM)。"""
    ients = {r[0].split(":", 1)[1] for r in
             c.execute("SELECT key FROM interest_profile WHERE key LIKE 'entity:%'")}
    radar = {}
    for en in sorted(ients):
        hits = [e for e in evs if en in e["ents"]]
        hits.sort(key=lambda e: -e["sel"])
        radar[en] = [{"event_id": h["event_id"], "title": h["label"], "sel": round(h["sel"], 1),
                      "cat": h["cat"], "n_indep": h["n_indep_sources"]} for h in hits[:3]]
    # 增强卡候选: 命中interest实体 或 watchlist关键词
    wl = [r[0] for r in c.execute("SELECT value FROM watchlist WHERE enabled=1")]
    hit_evs = [e for e in evs if (e["ents"] & ients) or
               any(w.lower() in (e["label"] or "").lower() for w in wl)]
    hit_evs.sort(key=lambda e: -e["sel"])
    # 简单去重: 同primary实体组只取最高分(避免同一故事多张增强卡)
    seen_groups, picked = set(), []
    for e in hit_evs:
        gk = frozenset(e["ents"] & ients) or frozenset([e["event_id"]])
        if gk in seen_groups:
            continue
        seen_groups.add(gk)
        picked.append(e)
        if len(picked) >= ENHANCED_TOP:
            break
    enhanced = []
    for e in picked:
        if not budget.ok():
            break
        ec_card = enhanced_card(c, e, keep, budget)
        if ec_card:
            enhanced.append(ec_card)
    # watchlist 命中流
    cutoff = (intel.now() - __import__("datetime").timedelta(hours=WINDOW_H)).isoformat()
    wl_hits = []
    for w in wl:
        rows = c.execute(
            "SELECT title,feed_name,link,pub_date FROM articles "
            "WHERE fetched_at>=? AND title LIKE ? ORDER BY fetched_at DESC LIMIT 4",
            (cutoff, f"%{w}%")).fetchall()
        if rows:
            wl_hits.append({"keyword": w, "items": [dict(r) for r in rows]})
    return {"radar": radar, "enhanced": enhanced, "watchlist_hits": wl_hits,
            "interest_entities": sorted(ients)}


def hotlist_cross(c, evs):
    """velocity_signals × 事件匹配(榜中榜) + RSS盲区提醒。无LLM。"""
    vpath = os.path.join(DATA, "velocity_signals.json")
    try:
        v = json.load(open(vpath, encoding="utf-8"))
    except Exception:
        return {"computed_at": None, "matched": [], "blind": []}
    signals = v.get("signals", [])
    top = evs[:300]
    ent_index = defaultdict(list)
    fp_index = {}
    for e in top:
        for en in e["ents"]:
            ent_index[en].append(e)
        fp = ec.fingerprint(e["label"])
        if fp:
            fp_index.setdefault(fp, e)
    strong = set(ec.ENTITY_ALIASES.values())
    matched = defaultdict(lambda: {"event_id": None, "title": "", "sel": 0, "platforms": []})
    used = set()
    for s in signals:
        title = ec.clean_text(s.get("title", ""))
        if not title:
            continue
        sets = ec.extract_entities(title)
        cand = {}
        fp = ec.fingerprint(title)
        if fp and fp in fp_index:
            e = fp_index[fp]
            cand[e["event_id"]] = e
        for en in sets:
            for e in ent_index.get(en, []):
                cand[e["event_id"]] = e
        best, best_score = None, 0.0
        for e in cand.values():
            ratio = difflib.SequenceMatcher(None, title, ec.clean_text(e["label"])).ratio()
            shared_strong = len(sets & e["ents"] & strong)
            score = ratio + (0.15 if shared_strong >= 2 else 0.0)
            if score > best_score:
                best, best_score = e, score
        ok = best and (best_score >= 0.55 or
                       (best_score >= 0.40 and len(sets & best["ents"] & strong) >= 2))
        if ok:
            m = matched[best["event_id"]]
            m["event_id"] = best["event_id"]
            m["title"] = best["label"]
            m["sel"] = best["sel"]
            m["platforms"].append({
                "platform": PLATFORM_NAME.get(s.get("platform"), s.get("platform")),
                "best_rank": s.get("best_rank"), "latest_rank": s.get("latest_rank"),
                "rank_delta": s.get("rank_delta"), "url": s.get("url"),
                "velocity": s.get("velocity")})
            used.add(s.get("item_id"))
    matched_list = sorted(matched.values(), key=lambda m: -m["sel"])
    blind = [s for s in signals if s.get("item_id") not in used and (s.get("best_rank") or 99) <= 10]
    blind.sort(key=lambda s: -(s.get("velocity") or 0))
    blind = [{"title": s.get("title"), "platform": PLATFORM_NAME.get(s.get("platform"), s.get("platform")),
              "best_rank": s.get("best_rank"), "url": s.get("url")} for s in blind[:15]]
    return {"computed_at": v.get("computed_at"), "matched": matched_list, "blind": blind}


def archive_meta():
    """每日归档元数据(cards JSON) + 门户版次归档列表。"""
    dailies = sorted(glob.glob(os.path.join(NEWS_WEB, "daily", "*.html")), reverse=True)
    out = []
    for f in dailies[:60]:
        date = os.path.basename(f)[:-5]
        compact = date.replace("-", "")
        meta = {"date": date, "n_cards": None, "tokens": None, "top_cat": None}
        cj = os.path.join(DATA, f"cards_{compact}.json")
        if os.path.exists(cj):
            try:
                d = json.load(open(cj, encoding="utf-8"))
                meta["n_cards"] = len(d.get("cards", []))
                meta["tokens"] = d.get("total_tokens")
                cats = Counter(cd.get("topic") for cd in d.get("cards", []) if cd.get("topic"))
                meta["top_cat"] = cats.most_common(1)[0][0] if cats else None
            except Exception:
                pass
        out.append(meta)
    editions = sorted(glob.glob(os.path.join(NEWS_WEB, "portal", "*.html")), reverse=True)[:30]
    return {"dailies": out, "editions": [os.path.basename(f)[:-5] for f in editions]}


# ---------------- HTML 渲染 ----------------
CSS = """
:root{--bg:#f5f6f8;--card:#fff;--fg:#1a1a1a;--muted:#6b7280;--line:#e5e7eb;--accent:#c0392b;
--link:#2471a3;--chip:#eef2f7;--heat:#e74c3c;--bg-note:#fff8e1;--bg-note-fg:#8a6d3b}
[data-theme=dark]{--bg:#111418;--card:#1b1f26;--fg:#e6e6e6;--muted:#9aa4b2;--line:#2c333d;
--accent:#e74c3c;--link:#6cb2e8;--chip:#232a33;--heat:#e74c3c;--bg-note:#2a2416;--bg-note-fg:#d9b96c}
*{box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;margin:0;background:var(--bg);
color:var(--fg);line-height:1.7}
.wrap{max-width:1200px;margin:0 auto;padding:0 16px 48px}
@media(min-width:1500px){.wrap{max-width:1280px}nav{max-width:1280px}}
header{position:sticky;top:0;z-index:20;background:var(--card);border-bottom:1px solid var(--line);padding:8px 14px}
.topline{max-width:1200px;margin:0 auto;display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding-bottom:6px}
.datelabel{font-size:13px;color:var(--muted);display:inline-flex;align-items:center;gap:6px}
#dateSelect{min-height:44px;border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:14px;
background:var(--card);color:var(--fg);max-width:230px}
.hrow{max-width:1200px;margin:0 auto;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
h1{font-size:19px;margin:0;color:var(--accent);white-space:nowrap}
.badge{font-size:12px;padding:2px 8px;border-radius:10px;background:var(--chip);color:var(--muted)}
.badge.warn{background:#fdecea;color:#c0392b}
[data-theme=dark] .badge.warn{background:#3a2220;color:#f0a09a}
.spacer{flex:1}
button,.tab{min-height:44px;min-width:44px;border:1px solid var(--line);background:var(--card);
color:var(--fg);border-radius:8px;padding:8px 12px;font-size:14px;cursor:pointer}
#search{min-height:44px;border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:14px;
background:var(--card);color:var(--fg);width:180px}
nav{max-width:1200px;margin:8px auto 0;display:flex;gap:6px;overflow-x:auto;padding-bottom:4px;align-items:center}
.navbtn{flex:0 0 auto;font-size:16px;padding:8px 10px}
.tab{white-space:nowrap;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;text-align:center;flex:1 0 auto;font-size:13px}
.tab.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.page{display:none}
.page.active{display:block}
section{margin-top:22px;scroll-margin-top:160px}
h2{font-size:18px;border-left:4px solid var(--accent);padding-left:10px;margin:0 0 10px}
.digest{font-size:14px;color:var(--muted);background:var(--card);border:1px solid var(--line);
border-radius:8px;padding:10px 12px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:1fr;gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.card details{margin:0}
.card summary{list-style:none;cursor:pointer;padding:12px 14px;min-height:44px}
.card summary::-webkit-details-marker{display:none}
.ctitle{font-size:16px;font-weight:600;margin:0 0 4px}
.rank{color:var(--accent);font-weight:700;margin-right:4px}
.cfact{font-size:13px;color:var(--muted);margin:0 0 6px}
.meta{font-size:12px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.chip{background:var(--chip);border-radius:8px;padding:1px 7px;font-size:11px}
.hot{background:#fdecea;color:#c0392b;border-radius:8px;padding:1px 7px;font-size:11px}
[data-theme=dark] .hot{background:#3a2220;color:#f0a09a}
.heatbar{height:4px;background:var(--chip);border-radius:2px;margin:6px 0 0}
.heatbar i{display:block;height:4px;background:var(--heat);border-radius:2px}
.cbody{padding:0 14px 12px;border-top:1px solid var(--line);font-size:14px}
.cbody p{margin:8px 0}
.card.compact .cbody{font-size:13px}
.bg-note{background:var(--bg-note);color:var(--bg-note-fg);border-radius:8px;padding:8px 10px;font-size:13px}
.div{color:#b9770e}.warn{color:var(--accent)}
.links{font-size:13px;padding-left:18px;margin:6px 0}.links a{color:var(--link);word-break:break-all}
.links .chip{margin-left:6px}
.overview{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:14px}
.mainline{font-size:15px;font-weight:600;margin:0 0 10px}
.ovpoints{margin:0;padding-left:22px}
.ovpoints li{margin:8px 0;font-size:14px}
.ovpoints li b{color:var(--accent);margin-right:6px}
.watch{font-size:13px;color:var(--muted);margin:10px 0 0;border-top:1px dashed var(--line);padding-top:8px}
.ovtext{font-size:14px;margin:0}
.radar{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.tile h4{margin:0 0 6px;font-size:14px}
.tile ul{margin:0;padding-left:16px;font-size:13px}
.tile a{color:var(--link)}
.empty{color:var(--muted);font-size:13px}
table.hot{width:100%;border-collapse:collapse;font-size:13px;background:var(--card)}
table.hot th,table.hot td{border:1px solid var(--line);padding:6px 8px;text-align:left}
.banner{background:#fdecea;color:#c0392b;border-radius:8px;padding:10px 12px;margin:12px 0;font-size:14px}
[data-theme=dark] .banner{background:#3a2220;color:#f0a09a}
footer{font-size:12px;color:var(--muted);margin-top:30px;text-align:center;border-top:1px solid var(--line);padding-top:14px}
a{color:var(--link)}
.archlist{font-size:13px;padding-left:18px}
"""

JS = """
(function(){
 var root=document.documentElement;
 var saved=localStorage.getItem('portal-theme');if(saved)root.setAttribute('data-theme',saved);
 var tb=document.getElementById('themeBtn');
 function tl(){tb.textContent=root.getAttribute('data-theme')==='dark'?'☀ 日间':'🌙 夜间';}tl();
 tb.onclick=function(){var n=root.getAttribute('data-theme')==='dark'?'light':'dark';
   root.setAttribute('data-theme',n);localStorage.setItem('portal-theme',n);tl();};
 var ds=document.getElementById('dateSelect');
 if(ds)ds.onchange=function(){if(ds.value)location.href=ds.value;};
 var pages=[].slice.call(document.querySelectorAll('.page'));
 var order=pages.map(function(p){return p.id;});
 var tabs=[].slice.call(document.querySelectorAll('.tab'));
 var cur='overview';
 var q=document.getElementById('search'),cnt=document.getElementById('searchCount');
 function applySearch(){
   var v=(q.value||'').trim().toLowerCase();var n=0;
   var active=document.querySelector('.page.active');if(!active)return;
   active.querySelectorAll('.card[data-search]').forEach(function(c){
     var hit=!v||c.getAttribute('data-search').indexOf(v)>=0;
     c.style.display=hit?'':'none';if(hit&&v)n++;});
   cnt.textContent=v?('命中 '+n+' 卡'):'';}
 function show(id){
   if(order.indexOf(id)<0)id='overview';cur=id;
   pages.forEach(function(p){p.classList.toggle('active',p.id===id);});
   tabs.forEach(function(t){t.classList.toggle('active',t.getAttribute('href')==='#'+id);});
   applySearch();window.scrollTo(0,0);}
 tabs.forEach(function(t){t.addEventListener('click',function(e){e.preventDefault();
   var id=t.getAttribute('href').slice(1);show(id);history.replaceState(null,'','#'+id);});});
 function step(d){var i=order.indexOf(cur);var j=(i+d+order.length)%order.length;
   show(order[j]);history.replaceState(null,'','#'+order[j]);}
 var pv=document.getElementById('prevPage'),nx=document.getElementById('nextPage');
 if(pv)pv.onclick=function(){step(-1);};if(nx)nx.onclick=function(){step(1);};
 document.addEventListener('keydown',function(e){
   if(e.target.tagName==='INPUT'||e.target.tagName==='SELECT')return;
   if(e.key==='ArrowLeft')step(-1);else if(e.key==='ArrowRight')step(1);});
 q.addEventListener('input',applySearch);
 document.getElementById('expandAll').onclick=function(){
   document.querySelectorAll('.page.active .card details').forEach(function(d){d.open=true;});};
 document.getElementById('collapseAll').onclick=function(){
   document.querySelectorAll('.page.active .card details').forEach(function(d){d.open=false;});};
 function route(){
   var h=location.hash.slice(1);
   if(!h){show('overview');return;}
   var el=document.getElementById(h);
   if(el){var sec=el.closest('.page');
     if(sec){show(sec.id);setTimeout(function(){el.scrollIntoView();},0);}else show('overview');}
   else if(order.indexOf(h)>=0)show(h);else show('overview');}
 window.addEventListener('hashchange',route);
 route();
})();
"""


def esc(s):
    return intel._esc(s)


def first_sentence(text, n=80):
    text = (text or "").strip()
    for sep in ("。", "；", ". "):
        i = text.find(sep)
        if 0 < i < n:
            return text[:i + 1]
    return text[:n] + ("…" if len(text) > n else "")


def heat_pct(sel, maxsel):
    return max(4, min(100, int(round(sel / maxsel * 100)))) if maxsel > 0 else 4


def compact_card_data(c, ev, group):
    """热度榜紧凑卡数据(无LLM): 代表作摘要 + 成员文章链接 + 实体/热度。group为归并组(DB rows)。"""
    eid = ev["event_id"]
    canon = c.execute("SELECT title,summary,content,link,feed_name,pub_date FROM articles WHERE id=?",
                      (ev["canonical_id"],)).fetchone()
    eids = [g["event_id"] for g in group]
    members = []
    for i in range(0, len(eids), 500):
        ch = eids[i:i + 500]
        qm = ",".join("?" * len(ch))
        members += c.execute(
            f"SELECT a.title,a.feed_name,a.link,a.pub_date FROM event_members m "
            f"JOIN articles a ON a.id=m.article_id WHERE m.event_id IN ({qm}) "
            f"ORDER BY m.similarity DESC", ch).fetchall()
    seen, ml = set(), []
    for a in ([canon] if canon else []) + members:
        u = a["link"] or ""
        if not u or "127.0.0.1" in u or "localhost" in u or u in seen:
            continue
        seen.add(u)
        ml.append({"title": a["title"], "feed": a["feed_name"], "url": u,
                   "pub_date": a["pub_date"] or ""})
    summ = ec.clean_text((canon["summary"] or canon["content"] or "") if canon else "")
    n_indep = len({ec.wire_key(m["feed_name"]) for m in members}) if members else ev["n_indep_sources"]
    return {"event_id": eid, "title": ev["label"], "cat": ev["cat"], "sel": ev["sel"],
            "n_indep": n_indep, "ents": sorted(ev["ents"])[:6],
            "summary": summ[:240], "lead": first_sentence(summ, 90),
            "members": ml[:8], "merged_from": eids if len(eids) > 1 else None,
            "canonical_feed": canon["feed_name"] if canon else ""}


def render_overview(ov):
    """结构化总览渲染: dict→主线+条目列表+关注; str(旧JSON/解析失败)→段落兜底。"""
    if isinstance(ov, dict) and not ov.get("_parse_failed"):
        ml = ov.get("mainline", "")
        pts = ov.get("points", []) or []
        watch = ov.get("watch", "")
        h = '<div class="overview">'
        if ml:
            h += f'<p class="mainline">📌 主线 · {esc(ml)}</p>'
        if pts:
            h += '<ol class="ovpoints">'
            for p in pts:
                if isinstance(p, dict):
                    h += f'<li><b>{esc(p.get("head",""))}</b><span>{esc(p.get("body",""))}</span></li>'
                else:
                    h += f'<li>{esc(str(p))}</li>'
            h += '</ol>'
        if watch:
            h += f'<p class="watch">👁 关注 · {esc(watch)}</p>'
        return h + '</div>'
    txt = str(ov or "").strip()
    if not txt:
        return ""
    return f'<div class="overview"><p class="ovtext">{esc(txt)}</p></div>'


def render_compact(item, idx, maxsel, hotmap):
    """热度榜紧凑卡(默认展开, 单列): 排名+标题+一句话+热度+实体+热榜徽章, 展开=摘要+成员链接。"""
    eid = item["event_id"]
    title = item.get("title", "")
    ents = item.get("ents", [])[:5]
    search = (title + " " + " ".join(ents) + " " + CAT_NAME.get(item.get("cat"), "")).lower()
    sel = item.get("sel", 0) or 0
    hots = hotmap.get(eid, [])
    hot_html = "".join(f'<span class="hot">{esc(h["platform"])} #{h["best_rank"]}</span>' for h in hots[:3])
    links = "".join(f'<li><a href="{esc(m["url"])}" rel="noopener">{esc(m["feed"])}</a>'
                    f'<span class="chip">{esc((m.get("pub_date") or "")[:10])}</span> {esc(m["title"][:60])}</li>'
                    for m in item.get("members", [])[:8])
    mf = ""
    if item.get("merged_from"):
        mf = f'<p class="meta">跨源归并自事件 {esc(", ".join(str(x) for x in item["merged_from"]))}</p>'
    summ = f'<p>{esc(item.get("summary",""))}</p>' if item.get("summary") else ""
    return f'''<article class="card compact" data-cat="{item.get('cat','')}" data-search="{esc(search)}" id="e{eid}">
<details open><summary>
<p class="ctitle"><span class="rank">#{idx}</span> {esc(title)}</p>
<p class="cfact">{esc(item.get("lead",""))}</p>
<div class="meta"><span class="chip">{item.get("n_indep",0)}独立源</span>
<span class="chip">S={sel:.1f}</span>{"".join(f'<span class="chip">{esc(e)}</span>' for e in ents[:4])}{hot_html}</div>
<div class="heatbar"><i style="width:{heat_pct(sel,maxsel)}%"></i></div>
</summary><div class="cbody">{summ}{mf}<ul class="links">{links}</ul></div></details></article>'''


def render_card(cd, idx, cat, maxsel, hotmap):
    eid = cd.get("event_id")
    title = cd.get("title", "")
    ents = cd.get("primary_entities", [])[:6]
    search = (title + " " + " ".join(ents) + " " + CAT_NAME.get(cat, "")).lower()
    sel = cd.get("salience", 0) or 0
    hots = hotmap.get(eid, [])
    hot_html = "".join(f'<span class="hot">{esc(h["platform"])} #{h["best_rank"]}</span>'
                       for h in hots[:3])
    links = "".join(f'<li><a href="{esc(l["url"])}" rel="noopener">{esc(l["feed"])}</a></li>'
                    for l in cd.get("links", [])[:6])
    if cd.get("error"):
        body = f'<p class="warn">合成失败: {esc(cd["error"])}</p>'
    else:
        div = f'<p class="div"><b>分歧/未核实：</b>{esc(cd["divergence"])}</p>' if cd.get("divergence") else ""
        unv = f'<p class="warn">⚠ 数字未核实：{esc(", ".join(cd["unverified_numbers"]))}</p>' if cd.get("unverified_numbers") else ""
        mf = ""
        if cd.get("merged_from"):
            mf = f'<p class="meta">跨源归并自事件 {esc(", ".join(str(x) for x in cd["merged_from"]))}（语料/链接取并集）</p>'
        body = (f'<p><b>事实：</b>{esc(cd.get("fact"))}</p>'
                f'<p><b>影响：</b>{esc(cd.get("impact"))}</p>{div}{unv}'
                f'<p><b>下一步关注：</b>{esc(cd.get("next_step"))}</p>{mf}'
                f'<ul class="links">{links}</ul>')
    return f'''<article class="card" data-cat="{cat}" data-search="{esc(search)}" id="e{eid}">
<details open><summary>
<p class="ctitle">{idx}. {esc(title)}</p>
<p class="cfact">{esc(first_sentence(cd.get("fact","")))}</p>
<div class="meta"><span class="chip">{cd.get("n_indep",0)}独立源</span>
<span class="chip">S={sel:.1f}</span>{"".join(f'<span class="chip">{esc(e)}</span>' for e in ents[:4])}{hot_html}</div>
<div class="heatbar"><i style="width:{heat_pct(sel,maxsel)}%"></i></div>
</summary><div class="cbody">{body}</div></details></article>'''


def render_enhanced(cd, idx):
    links = "".join(f'<li><a href="{esc(l["url"])}" rel="noopener">{esc(l["feed"])}</a></li>'
                    for l in cd.get("links", [])[:6])
    ft = f'<p class="meta">全文深读: {len(cd.get("fulltext_fetched",[]))} 篇（Jina）</p>' if cd.get("fulltext_fetched") else \
        '<p class="meta">全文抓取不可用，基于摘要合成</p>'
    unv = f'<p class="warn">⚠ 数字未核实：{esc(", ".join(cd["unverified_numbers"]))}</p>' if cd.get("unverified_numbers") else ""
    data = f'<p><b>关键数据：</b>{esc(cd["data"])}</p>' if cd.get("data") else ""
    div = f'<p class="div"><b>分歧/未核实：</b>{esc(cd["divergence"])}</p>' if cd.get("divergence") else ""
    search = (cd.get("title", "") + " " + " ".join(cd.get("primary_entities", []))).lower()
    return f'''<article class="card" data-search="{esc(search)}" id="x{cd['event_id']}">
<details open><summary>
<p class="ctitle">🔬 {idx}. {esc(cd['title'])}</p>
<div class="meta"><span class="chip">{CAT_NAME.get(cd.get('cat'),'')}</span>
<span class="chip">{cd.get('n_indep',0)}独立源</span><span class="chip">S={cd.get('salience',0):.1f}</span></div>
</summary><div class="cbody">
<p><b>事实：</b>{esc(cd.get('fact'))}</p>
<p class="bg-note">{esc(cd.get('background'))}</p>
<p><b>影响：</b>{esc(cd.get('impact'))}</p>{data}{div}{unv}
<p><b>下一步关注：</b>{esc(cd.get('next_step'))}</p>{ft}
<ul class="links">{links}</ul></div></details></article>'''


def render_html(data):
    meta = data["meta"]
    cov = meta.get("coverage")
    degraded = bool(cov and cov.get("ratio", 1) < intel.COVERAGE_MIN)
    hotmap = defaultdict(list)
    for m in data["hotlist"]["matched"]:
        hotmap[m["event_id"]] = m["platforms"]
    ed = meta["edition"]
    ed_name = "晨版" if ed == "morning" else "晚版"
    date = meta["date"]
    am = data["archive"]
    # 日期下拉: 门户版次优先, 无门户的日期回退每日简报
    ed_map = {}
    for e in am.get("editions", []):
        d, _, edn = e.rpartition("-")
        ed_map.setdefault(d, []).append((edn, f"{WEBROOT}/portal/{e}.html"))
    daily_dates = {d["date"] for d in am.get("dailies", [])}
    all_dates = sorted(set(list(ed_map.keys()) + list(daily_dates)), reverse=True)
    opts = ""
    for d in all_dates:
        if d in ed_map:
            for edn, url in sorted(ed_map[d]):
                nm = "晨版" if edn == "morning" else "晚版"
                sel = " selected" if (d == date and edn == ed) else ""
                opts += f'<option value="{esc(url)}"{sel}>{esc(d)} {nm}</option>'
        else:
            url = f"{WEBROOT}/daily/{d}.html"
            sel = " selected" if d == date else ""
            opts += f'<option value="{esc(url)}"{sel}>{esc(d)} 简报</option>'
    # 同日版次快捷切换
    ed_links = []
    for e, nm in (("morning", "晨版"), ("evening", "晚版")):
        if os.path.exists(os.path.join(NEWS_WEB, "portal", f"{date}-{e}.html")):
            cur = ' style="font-weight:700"' if e == ed else ""
            ed_links.append(f'<a href="{WEBROOT}/portal/{date}-{e}.html"{cur}>{nm}</a>')
    ed_html = " · ".join(ed_links) if ed_links else ed_name
    cov_badge = (f'<span class="badge warn">源覆盖 {cov["ok"]}/{cov["total"]} 降级</span>' if degraded
                 else (f'<span class="badge">源覆盖 {cov["ok"]}/{cov["total"]}</span>' if cov else ""))
    banners = ""
    if degraded:
        banners += (f'<div class="banner">⚠ 源覆盖降级 {cov["ok"]}/{cov["total"]}（{esc(cov.get("ts",""))}）。'
                    f'本期可能遗漏部分来源，管线已自动告警/重试，恢复后次期补全。</div>')
    if meta.get("quota_hit"):
        banners += '<div class="banner">⚠ 本期合成触及配额(429)，部分内容未生成。</div>'
    elif meta.get("partial"):
        banners += '<div class="banner">⚠ 本期合成达预算上限，部分类目/深挖未生成。</div>'

    tabs = '<a class="tab active" href="#overview">总览</a>'
    for k, n, _ in CATEGORIES:
        tabs += f'<a class="tab" href="#cat-{k}">{n}</a>'
    tabs += '<a class="tab" href="#interest">兴趣深挖</a><a class="tab" href="#hotlist">热榜交叉</a><a class="tab" href="#archive">归档</a>'

    # B 总览(结构化条目化) + 头条
    head_cards = ""
    top5 = data.get("headlines", [])
    if top5:
        maxsel = max((cd.get("salience", 0) or 0) for cd in top5) or 1
        head_cards = '<div class="grid">' + "".join(
            render_card(cd, i, cd.get("_cat", "finance"), maxsel, hotmap)
            for i, cd in enumerate(top5, 1)) + "</div>"
    overview = (f'<section id="overview" class="page active"><h2>今日总览 · {esc(date)} {ed_name}</h2>'
                + render_overview(data.get("overview", "")) + head_cards + "</section>")

    # C 分类(分页: 每类一页, 深度卡+热度榜, 单列默认展开)
    cats_html = ""
    for k, n, floor in CATEGORIES:
        block = data["categories"].get(k, {})
        cards = block.get("cards", [])
        heat = block.get("heat_list", [])
        digest = block.get("digest", "")
        total = len(cards) + len(heat)
        cats_html += f'<section id="cat-{k}" class="page"><h2>{n} <span class="badge">{total}条</span></h2>'
        if digest:
            cats_html += f'<div class="digest">{esc(digest)}</div>'
        if total:
            sels = [cd.get("salience", 0) or 0 for cd in cards] + [it.get("sel", 0) or 0 for it in heat]
            maxsel = max(sels) or 1
            cats_html += '<div class="grid">'
            cats_html += "".join(render_card(cd, i, k, maxsel, hotmap) for i, cd in enumerate(cards, 1))
            cats_html += "".join(render_compact(it, len(cards) + j, maxsel, hotmap)
                                 for j, it in enumerate(heat, 1))
            cats_html += "</div>"
        else:
            cats_html += f'<p class="empty">今日该类目无显著事件（72h窗口，选择分阈值 S≥{floor}）。</p>'
        cats_html += "</section>"

    # D 兴趣
    iz = data["interest"]
    radar = '<div class="radar">'
    for en, hits in iz["radar"].items():
        if hits:
            lis = "".join(f'<li><a href="#e{h["event_id"]}">{esc(h["title"][:42])}</a> '
                          f'<span class="chip">S={h["sel"]}</span></li>' for h in hits)
            radar += f'<div class="tile"><h4>{esc(en)} <span class="chip">{len(hits)}条</span></h4><ul>{lis}</ul></div>'
        else:
            radar += f'<div class="tile"><h4>{esc(en)}</h4><p class="empty">今日无新增</p></div>'
    radar += "</div>"
    enh = ""
    if iz["enhanced"]:
        enh = '<h3 style="font-size:16px;margin:18px 0 8px">增强深读卡（六段 · 背景段为模型知识标注）</h3><div class="grid">' + \
            "".join(render_enhanced(cd, i) for i, cd in enumerate(iz["enhanced"], 1)) + "</div>"
    wl = ""
    if iz["watchlist_hits"]:
        wl = '<h3 style="font-size:16px;margin:18px 0 8px">关注关键词命中流</h3>'
        for g in iz["watchlist_hits"]:
            lis = "".join(f'<li><a href="{esc(it["link"])}" rel="noopener">{esc(it["title"][:50])}</a> '
                          f'<span class="chip">{esc(it["feed_name"])}</span></li>' for it in g["items"])
            wl += f'<div class="tile" style="margin-bottom:8px"><h4>{esc(g["keyword"])}</h4><ul>{lis}</ul></div>'
    interest = f'<section id="interest" class="page"><h2>兴趣深挖 · 持仓雷达</h2>{radar}{enh}{wl}</section>'

    # E 热榜
    hl = data["hotlist"]
    hot_rows = ""
    for m in hl["matched"][:25]:
        plats = " ".join(f'<span class="hot">{esc(p["platform"])} #{p["best_rank"]}'
                         f'{" ↑" + str(p["rank_delta"]) if p.get("rank_delta") else ""}</span>'
                         for p in m["platforms"][:5])
        hot_rows += (f'<tr><td><a href="#e{m["event_id"]}">{esc(m["title"][:46])}</a></td>'
                     f'<td>{plats}</td><td>{m["sel"]:.1f}</td></tr>')
    blind_rows = "".join(
        f'<li><a href="{esc(b["url"])}" rel="noopener">{esc(b["title"][:50])}</a> '
        f'<span class="chip">{esc(b["platform"])} #{b["best_rank"]}</span></li>' for b in hl["blind"])
    hotlist = f'<section id="hotlist" class="page"><h2>热榜交叉验证（榜中榜）</h2>'
    hotlist += f'<p class="meta">热榜数据截至 {esc(hl.get("computed_at") or "N/A")} · 匹配 {len(hl["matched"])} 事件</p>'
    if hot_rows:
        hotlist += ('<table class="hot"><tr><th>我们的事件</th><th>上榜平台/排名</th><th>选择分</th></tr>'
                    + hot_rows + "</table>")
    else:
        hotlist += '<p class="empty">本期无事件匹配到平台热榜。</p>'
    if blind_rows:
        hotlist += ('<h3 style="font-size:16px;margin:16px 0 8px">RSS 盲区提醒（热榜前列但未被我们的源覆盖）</h3>'
                    '<ul class="archlist">' + blind_rows + "</ul>")
    hotlist += "</section>"

    # F 归档
    arch_rows = ""
    for d in am["dailies"]:
        extra = ""
        if d.get("n_cards") is not None:
            extra = f' <span class="chip">{d["n_cards"]}卡</span>'
            if d.get("top_cat"):
                extra += f' <span class="chip">主类:{esc(d["top_cat"])}</span>'
        arch_rows += f'<li><a href="{WEBROOT}/daily/{d["date"]}.html">{d["date"]}</a>{extra}</li>'
    ed_rows = "".join(f'<li><a href="{WEBROOT}/portal/{e}.html">{e}</a></li>' for e in am["editions"])
    archive = f'''<section id="archive" class="page"><h2>归档与工具</h2>
<div class="grid"><div class="tile"><h4>📅 每日简报归档</h4><ul class="archlist">{arch_rows}</ul></div>
<div class="tile"><h4>🗂 门户版次归档</h4><ul class="archlist">{ed_rows}</ul>
<h4 style="margin-top:12px">📊 A/B 评测</h4><ul class="archlist">
<li><a href="{WEBROOT}/eval/dashboard.html">A/B 指标看板</a></li>
<li><a href="{WEBROOT}/eval/blind.html">双轨盲评（2周观察）</a></li></ul></div></div></section>'''

    gen = meta.get("generated_at", "")
    footer = (f'<footer>Wuhoo 情报门户 · {esc(date)} {ed_name} · 生成 {esc(gen)} CST · '
              f'模型 {esc(meta.get("model",""))} · 合成 {meta.get("tokens",0)} tokens / {meta.get("calls",0)} 调用 · '
              f'数字经来源核验 · 背景段为模型知识标注 · 只读<br>'
              f'数据每小时采集，门户每日晨/晚两版。类目分页(←→翻页)，卡片默认展开。反馈调节：多点X / 少点X / 这条没用。</footer>')

    return f'''<!DOCTYPE html><html lang="zh" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wuhoo 情报门户 · {esc(date)} {ed_name}</title><style>{CSS}</style></head><body>
<header>
<div class="topline"><label class="datelabel">📅 回看 <select id="dateSelect" aria-label="选择日期">{opts}</select></label>
<span class="badge">{esc(date)} {ed_name}</span>{cov_badge}
<span class="badge">数据截至 {esc(meta.get("data_asof",""))}</span>
<span class="badge">{ed_html}</span></div>
<div class="hrow"><h1>Wuhoo 情报门户</h1><span class="spacer"></span>
<input id="search" type="search" placeholder="搜索标题/实体…" aria-label="搜索">
<span id="searchCount" class="badge"></span>
<button id="expandAll" title="全部展开">展开</button>
<button id="collapseAll" title="全部收起">收起</button>
<button id="themeBtn">🌙 夜间</button></div>
<nav><button id="prevPage" class="navbtn" title="上一页(←)">←</button>{tabs}<button id="nextPage" class="navbtn" title="下一页(→)">→</button></nav>
</header>
<div class="wrap">{banners}{overview}{cats_html}{interest}{hotlist}{archive}{footer}</div>
<script>{JS}</script></body></html>'''


# ---------------- build 编排 ----------------
def build(edition="morning", budget_limit=90000, dry=False, no_llm=False):
    c = ec.get_conn()
    ec.refresh_dynamic_aliases(c)
    date = intel.now().strftime("%Y-%m-%d")
    if no_llm:
        # 从已存 JSON 重渲染(零token)
        pat = os.path.join(DATA, f"portal_{date.replace('-','')}_{edition}.json")
        if not os.path.exists(pat):
            cands = sorted(glob.glob(os.path.join(DATA, "portal_*.json")), reverse=True)
            if not cands:
                raise SystemExit("no-llm: 无已存 portal JSON")
            pat = cands[0]
        data = json.load(open(pat, encoding="utf-8"))
        html = render_html(data)
        _write_outputs(html, data, edition, date)
        print(f"no-llm 重渲染: {pat} → index.html ({len(html)}B)")
        c.close()
        return

    evs, keep, n_noise = load_window(c)
    by_cat = defaultdict(list)
    for e in evs:
        by_cat[e["cat"]].append(e)
    for k in by_cat:
        by_cat[k].sort(key=lambda e: -e["sel"])
    hl = hotlist_cross(c, evs)
    iz_plan = interest_zone(c, evs, keep, Budget(0))  # dry计划用budget0→不LLM, 仅radar/wl
    if dry:
        print(f"窗口事件={len(evs)} 噪声过滤={n_noise} 热榜匹配={len(hl['matched'])} 盲区={len(hl['blind'])}")
        for k, n, floor in CATEGORIES:
            pool = [e for e in by_cat.get(k, []) if e["sel"] >= floor]
            top_sel = pool[0]["sel"] if pool else 0
            n_heat = len([e for e in pool if e["sel"] >= top_sel * HEAT_RATIO])
            N = max(LIST_MIN, min(CAT_LIST_MAX.get(k, LIST_MAX), n_heat))
            if top_sel < COLD_CAP:
                N = min(N, LIST_MIN)
            N = min(N, len(pool), CAND_PER_CAT)
            print(f"  {n}: 总{len(by_cat.get(k,[]))} 过阈值{len(pool)} 热度条目N={N} (深度{DEEP_PER_CAT}+紧凑{max(0,N-DEEP_PER_CAT)})")
            for e in pool[:DEEP_PER_CAT]:
                print(f"    [{e['event_id']}] S={e['sel']:.1f} N={e['n_indep_sources']} {e['label'][:46]}")
        print(f"  兴趣雷达实体={len(iz_plan['radar'])} 增强卡候选={ENHANCED_TOP} watchlist命中组={len(iz_plan['watchlist_hits'])}")
        c.close()
        return

    budget = Budget(budget_limit)
    categories = {}
    for k, n, floor in CATEGORIES:
        pool = [e for e in by_cat.get(k, []) if e["sel"] >= floor]
        if not pool:
            categories[k] = {"cards": [], "heat_list": [], "digest": "", "merged": [], "mode": "empty", "n_total": 0}
            continue
        categories[k] = synthesize_category(c, pool, keep, budget)
        print(f"[{n}] {len(categories[k]['cards'])}深度卡+{len(categories[k]['heat_list'])}热度条 "
              f"导读{'有' if categories[k]['digest'] else '无'} 归并{len(categories[k]['merged'])}组 tokens累计={budget.tokens}")
    # 头条: 各类目首卡按选择分取top5
    headlines = []
    for k, _, _ in CATEGORIES:
        cs = categories[k]["cards"]
        if cs and not cs[0].get("error"):
            h = dict(cs[0]); h["_cat"] = k
            headlines.append(h)
    headlines.sort(key=lambda cd: -(cd.get("salience", 0) or 0))
    headlines = headlines[:5]
    overview = ""
    if budget.ok():
        lines = []
        for k, n, _ in CATEGORIES:
            dg = categories[k]["digest"]
            if dg:
                lines.append(f"{n}: {dg}")
        for h in headlines:
            lines.append(f"头条: {h.get('title','')}")
        content = budget.llm(OVERVIEW_SYSTEM, "\n".join(lines)[:4000], max_tokens=900)
        overview = ""
        if content:
            parsed = sy.parse_json(content)
            overview = content.strip() if parsed.get("_parse_failed") else parsed
    # 兴趣区(含LLM增强卡)
    iz = interest_zone(c, evs, keep, budget)
    archive = archive_meta()
    cov = intel.read_coverage()
    vts = hl.get("computed_at") or ""
    data = {
        "meta": {"date": date, "edition": edition, "model": sy.MODEL,
                 "generated_at": intel.now().strftime("%Y-%m-%d %H:%M"),
                 "data_asof": intel.now().strftime("%H:%M"),
                 "tokens": budget.tokens, "calls": budget.calls,
                 "quota_hit": budget.quota, "partial": not budget.ok() and not budget.quota,
                 "coverage": cov, "noise_filtered": n_noise, "window_events": len(evs),
                 "velocity_asof": vts},
        "overview": overview, "headlines": headlines, "categories": categories,
        "interest": iz, "hotlist": hl, "archive": archive,
    }
    jpath = os.path.join(DATA, f"portal_{date.replace('-','')}_{edition}.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, default=str)
    html = render_html(data)
    _write_outputs(html, data, edition, date)
    ncards = sum(len(v["cards"]) for v in categories.values())
    nheat = sum(len(v.get("heat_list", [])) for v in categories.values())
    print(f"\nportal build: {edition} {ncards}深度卡+{nheat}热度条+{len(iz['enhanced'])}增强卡 "
          f"tokens={budget.tokens}/{budget_limit} calls={budget.calls} quota={budget.quota}")
    print(f"  覆盖={cov['ratio'] if cov else 'N/A'} 噪声过滤={n_noise} 热榜匹配={len(hl['matched'])}")
    print(f"  JSON: {jpath}")
    print(f"  公开链接: {PUBLIC_BASE}/")
    c.close()


def _write_outputs(html, data, edition, date):
    os.makedirs(os.path.join(NEWS_WEB, "portal"), exist_ok=True)
    idx = os.path.join(NEWS_WEB, "index.html")
    with open(idx, "w", encoding="utf-8") as f:
        f.write(html)
    arch = os.path.join(NEWS_WEB, "portal", f"{date}-{edition}.html")
    with open(arch, "w", encoding="utf-8") as f:
        f.write(html)
    # 标记: publish_web 见此标记则用门户 index 而非旧归档索引(回滚=删标记)
    with open(os.path.join(NEWS_WEB, ".portal_index"), "w", encoding="utf-8") as f:
        f.write(f"{edition} {intel.now().isoformat()}\n")
    intel.publish_web()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("--edition", choices=["morning", "evening"], default="morning")
    ap.add_argument("--budget", type=int, default=120000)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    a = ap.parse_args()
    build(a.edition, a.budget, a.dry, a.no_llm)


if __name__ == "__main__":
    main()