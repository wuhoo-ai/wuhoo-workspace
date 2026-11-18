#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""WP3 事件中心 — 向量聚类 + canonical 代表作 + salience 排序。
增量扩展 news.db（不动 articles/FTS5）。模型 fastembed multilingual-MiniLM 384d + numpy 暴力余弦。
阈值由 wp3_calibrate.py 实证校准（跨语短标题 cosine 低于方案假定，须实测设定）。
用法:
  python3.11 event_center.py init                 # 建事件表(增量)
  python3.11 event_center.py embed [--window 72]  # 嵌入窗口内未向量化文章
  python3.11 event_center.py cluster [--window 72]# 聚类+canonical+salience(窗口重建)
  python3.11 event_center.py top [--n 20]         # 打印 salience TOP
"""
import os, sys, sqlite3, json, math, re, time, argparse, html as _html
from datetime import datetime, timedelta
import numpy as np

HOME = os.path.expanduser("~")
DB = os.path.join(HOME, "wuhoo-workspace/skills/default/wuhoo-news-rss/data/news.db")
CONFIG = os.path.join(HOME, "wuhoo-workspace/skills/default/wuhoo-news-rss/feeds/config.yaml")
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
WINDOW_H = 72

# ---- 聚类阈值（wp3_calibrate.py 实证校准后设定；初始为方案假定值）----
COS_DIRECT = 0.82      # 校准:>不同事件inter_max0.81零假直接合并,≈同事件intra_p10(0.819)
COS_ENTITY = 0.75      # 校准:>共享实体p95=0.708拒同实体不同事件,<跨语同事件0.78抓跨语合并
HALF_LIFE_H = 12.0     # salience 时间衰减半衰期

DDL = """
CREATE TABLE IF NOT EXISTS events (
  event_id INTEGER PRIMARY KEY,
  label TEXT, topic TEXT,
  first_seen TEXT, last_seen TEXT,
  canonical_id INTEGER, salience REAL,
  n_indep_sources INTEGER, status TEXT DEFAULT 'active',
  canonical_hash TEXT
);
CREATE TABLE IF NOT EXISTS event_members (
  event_id INTEGER, article_id INTEGER, similarity REAL,
  PRIMARY KEY(event_id, article_id)
);
CREATE TABLE IF NOT EXISTS entities (
  entity_id INTEGER PRIMARY KEY, name TEXT UNIQUE, type TEXT, aliases TEXT
);
CREATE TABLE IF NOT EXISTS event_entities (event_id INTEGER, entity_id INTEGER, role TEXT);
CREATE TABLE IF NOT EXISTS event_facts (
  event_id INTEGER, claim TEXT, numbers TEXT, source_article_id INTEGER,
  verified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS article_vectors (article_id INTEGER PRIMARY KEY, emb BLOB, dim INTEGER, model TEXT);
CREATE TABLE IF NOT EXISTS interest_profile (
  key TEXT PRIMARY KEY, weight REAL, updated TEXT,
  source TEXT, origin_profile TEXT, expires TEXT
);
CREATE TABLE IF NOT EXISTS watchlist (
  id INTEGER PRIMARY KEY, kind TEXT, value TEXT,
  threshold REAL, alert_channel TEXT, enabled INTEGER, origin_profile TEXT
);
CREATE TABLE IF NOT EXISTS topic_burst (
  topic TEXT PRIMARY KEY, boost REAL, reason TEXT, expires_ts TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY, event_id INTEGER, kind TEXT,
  raw_text TEXT, ts TEXT, applied INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_events_salience ON events(salience DESC);
CREATE INDEX IF NOT EXISTS idx_events_lastseen ON events(last_seen);
CREATE INDEX IF NOT EXISTS idx_em_event ON event_members(event_id);
"""

# 通讯社通稿归并（独立源计数去 G5 灌水）：同稿源只计 1
WIRE_GROUPS = {
    "reuters": ["路透社", "路透", "reuters"],
    "ap": ["美联社", "ap news", "associated press"],
    "bloomberg": ["彭博", "bloomberg"],
    "afp": ["法新社", "afp"],
    "xinhua": ["新华社", "xinhua"],
}
TIER_BONUS = {"T0": 1.5, "T1": 1.2, "T2": 1.0, "T3": 0.8, "T4": 1.0}

# 实体别名归一（中英 → 规范名），用于 entity_overlap
# 2026-11-17 扩充: 人物(黄仁勋/Trump等, 跨语同事件归并的实体锚, P0-2) +
# A股持仓名(trader workflow_b 7只, P1-5 种子生效前提) +
# 美股持仓(trader workflow_d 2026-06-30: FITB/FAST/HBAN, 近期投资信息)。
ENTITY_ALIASES = {
    "英伟达": "NVIDIA", "nvidia": "NVIDIA", "nvda": "NVIDIA",
    "苹果": "APPLE", "apple": "APPLE", "aapl": "APPLE",
    "特斯拉": "TESLA", "tesla": "TESLA", "tsla": "TESLA",
    "微软": "MICROSOFT", "microsoft": "MICROSOFT", "msft": "MICROSOFT",
    "谷歌": "GOOGLE", "google": "GOOGLE", "googl": "GOOGLE", "goog": "GOOGLE",
    "亚马逊": "AMAZON", "amazon": "AMAZON", "amzn": "AMAZON",
    "脸书": "META", "facebook": "META",
    "openai": "OPENAI", "anthropic": "ANTHROPIC", "deepseek": "DEEPSEEK",
    "美联储": "FED", "fed": "FED", "央行": "PBOC",
    "台积电": "TSMC", "tsmc": "TSMC", "amd": "AMD", "英特尔": "INTEL", "intel": "INTEL",
    "比特币": "BTC", "bitcoin": "BTC", "btc": "BTC", "以太坊": "ETH", "ethereum": "ETH",
    "腾讯": "TENCENT", "阿里": "ALIBABA", "阿里巴巴": "ALIBABA", "百度": "BAIDU",
    "华为": "HUAWEI", "比亚迪": "BYD", "宁德时代": "CATL",
    # --- 人物（跨语同事件实体锚, 2026-11-17 P0-2）---
    "黄仁勋": "JENSEN_HUANG", "jensen huang": "JENSEN_HUANG", "詹森·黄": "JENSEN_HUANG",
    "特朗普": "TRUMP", "trump": "TRUMP", "川普": "TRUMP",
    "拜登": "BIDEN", "biden": "BIDEN",
    "普京": "PUTIN", "putin": "PUTIN",
    "鲍威尔": "POWELL", "powell": "POWELL",
    "马斯克": "MUSK", "elon musk": "MUSK", "musk": "MUSK",
    "奥特曼": "ALTMAN", "sam altman": "ALTMAN",
    "库克": "COOK", "tim cook": "COOK",
    # --- A股持仓名（trader workflow_b 种子, P1-5 修复）---
    "五粮液": "WULIANGYE", "贵州茅台": "MOUTAI", "茅台": "MOUTAI",
    "恒瑞医药": "HENGRUI", "中国平安": "PINGAN",
    "意华股份": "YIHUA", "中贝通信": "ZHONGBEI",
    # --- 美股持仓（trader workflow_d 2026-06-30, 近期投资信息）---
    "五三银行": "FITB", "fifth third": "FITB", "fitb": "FITB",
    "快扣": "FAST", "fastenal": "FAST",
    "亨廷顿银行": "HBAN", "huntington bancshares": "HBAN", "hban": "HBAN",
}
# 泛词停用（2026-11-17 实测扩充: 财经7天高频junk US/SZ/SH/TO/IN/OF/SAYS等来自
# 大写ticker正则误抓英文常用词/交易所代码, 污染实体重叠归并精度）
STOP_TICKERS = {"AI", "GPU", "CPU", "IPO", "CEO", "CFO", "GDP", "CPI", "PMI", "ETF",
                "API", "SDK", "LLM", "AGI", "USA", "USD", "EUR", "THE", "AND", "FOR",
                "NEW", "TOP", "ALL", "ONE", "OUT", "HOW", "WHY", "WHAT", "WITH",
                "US", "UK", "UN", "EU", "SH", "SZ", "HK", "TO", "IN", "OF", "ON",
                "AT", "BY", "IS", "IT", "AS", "BE", "DO", "GO", "NO", "SO", "UP",
                "IF", "OR", "AN", "AM", "PM", "FROM", "THAT", "THIS", "WILL",
                "HAS", "HAVE", "ARE", "WAS", "WERE", "NOT", "BUT", "CAN", "MAY",
                "ITS", "HIS", "HER", "THEM", "THEY", "THEN", "THAN", "WHEN",
                "WHERE", "WHICH", "WHO", "ALSO", "MORE", "MOST", "SOME", "SUCH",
                "ONLY", "OWN", "SAME", "TOO", "VERY", "JUST", "LIKE", "OVER",
                "AFTER", "BEFORE", "BETWEEN", "UNDER", "AGAIN", "EACH", "FEW",
                "BOTH", "ANY", "SAYS", "SAY", "SAID", "NEXT", "LAST", "FIRST",
                "SECOND", "THIRD", "BEST", "WORST", "BIG", "SMALL", "HIGH",
                "LOW", "LONG", "SHORT", "OPEN", "CLOSE", "FREE", "REAL", "TRUE",
                "FALSE", "NONE", "ELSE", "EVER", "NEVER", "ALWAYS", "OFTEN",
                "NVIDI", "WHOM", "WHOSE", "ABOUT", "INTO", "THROUGH",
                "DURING", "WITHOUT", "WITHIN", "ALONG", "FOLLOWING", "ACROSS",
                "BEHIND", "BEYOND", "PLUS", "MINUS", "VERSUS", "VIA", "PER"}

# 动态别名（P1-5）: interest_profile entity 键 + watchlist 启用值自动注册进实体抽取,
# 未来 sync-profiles/tune 新增种子无需改代码即生效。refresh_dynamic_aliases(conn) 刷新。
_DYNAMIC_ALIASES = {}


def canonical_entity(name):
    """名称→规范实体名: 静态别名 > 动态别名 > ASCII大写化 > CJK原样。
    sync-profiles 写 interest 键必须用本函数, 否则键名与抽取结果不匹配(宁德时代→CATL 教训)。"""
    n = (name or "").strip()
    if not n:
        return n
    if n.lower() in ENTITY_ALIASES:
        return ENTITY_ALIASES[n.lower()]
    if n.lower() in _DYNAMIC_ALIASES:
        return _DYNAMIC_ALIASES[n.lower()]
    return n.upper() if n.isascii() else n


def known_entity(name):
    n = (name or "").strip()
    return (n.lower() in ENTITY_ALIASES or n in ENTITY_ALIASES.values()
            or n.lower() in _DYNAMIC_ALIASES)


def refresh_dynamic_aliases(conn):
    """从 interest_profile(entity:键) + watchlist(enabled=1) 注册动态别名。
    规范名与 canonical_entity 一致, 保证 interest 键 ↔ 抽取结果 ↔ salience gain 三者对齐。"""
    global _DYNAMIC_ALIASES
    m = {}
    try:
        for r in conn.execute("SELECT key FROM interest_profile WHERE key LIKE 'entity:%'").fetchall():
            nm = r[0].split(":", 1)[1]
            canon = ENTITY_ALIASES.get(nm.lower(), nm.upper() if nm.isascii() else nm)
            m[nm.lower()] = canon
        for r in conn.execute("SELECT value FROM watchlist WHERE enabled=1").fetchall():
            nm = r[0]
            canon = ENTITY_ALIASES.get(nm.lower(), nm.upper() if nm.isascii() else nm)
            m[nm.lower()] = canon
    except sqlite3.OperationalError:
        pass
    _DYNAMIC_ALIASES = m
    return len(m)


def get_conn():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db(conn):
    conn.executescript(DDL)
    conn.commit()


class Embedder:
    _model = None

    @classmethod
    def model(cls):
        if cls._model is None:
            from fastembed import TextEmbedding
            cls._model = TextEmbedding(MODEL_NAME)
        return cls._model

    @classmethod
    def embed(cls, texts):
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        return np.array(list(cls.model().embed(texts)), dtype=np.float32)


def norm_rows(a):
    n = np.linalg.norm(a, axis=-1, keepdims=True)
    n[n == 0] = 1.0
    return a / n


_PREFIX_RE = re.compile(r"^(IT之家消息|IT之家|36氪获悉|36氪|快讯[:：]?|【[^】]*】|突发[:：]?|独家[:：]?)")
_PUNCT_RE = re.compile(r"[\s\W_]+", re.UNICODE)
_TAG_RE = re.compile(r"<[a-zA-Z/!][^>]*>")
_TAG_OPEN_RE = re.compile(r"<[a-zA-Z/!][^>]*$")
_WS_RE = re.compile(r"\s+")


def clean_text(s):
    """剥离HTML标签+反转义实体+折叠空白。RSS summary常含原始HTML(知乎class=meta等)，
    不清理会污染嵌入(同骨架→假高cosine)与实体抽取(class=meta→假META)。"""
    if not s:
        return ""
    s = _TAG_RE.sub(" ", s)
    s = _TAG_OPEN_RE.sub(" ", s)
    s = _html.unescape(s)
    return _WS_RE.sub(" ", s).strip()


def fingerprint(title):
    t = _PREFIX_RE.sub("", title or "")
    t = _PUNCT_RE.sub("", t)
    return t[:40]


def extract_entities(text):
    """轻量实体抽取：静态别名 + 动态别名(interest/watchlist种子, P1-5) + 大写 ticker（词边界，去停用）。返回 set。"""
    text = clean_text(text)
    if not text:
        return set()
    ents = set()
    low = text.lower()
    for alias, canon in ENTITY_ALIASES.items():
        if alias.isascii():
            if re.search(r"\b" + re.escape(alias) + r"\b", low):
                ents.add(canon)
        else:
            if alias in low:
                ents.add(canon)
    for alias, canon in _DYNAMIC_ALIASES.items():
        if alias in ENTITY_ALIASES:
            continue
        if alias.isascii():
            if re.search(r"\b" + re.escape(alias) + r"\b", low):
                ents.add(canon)
        else:
            if alias in low:
                ents.add(canon)
    for tok in re.findall(r"\b[A-Z]{2,5}\b", text):
        if tok not in STOP_TICKERS:
            ents.add(tok)
    return ents


# A股公司公告动作词（公司主语消歧用）。仅匹配"公司名+ corporate action"窄模式，
# 避免把"报道：称..." / "财联社X日电" 误判为公司主语。
_CORP_ACTION = r"(?:拟|预计|实控人|提议|公告|回购|持股|分红|增持|减持|中标|签约|业绩|净利|营收|半年|前三|季度|年度|员工持股)"

# 非公司主语前缀（国家/政府/媒体/人名/泛词），命中则不视为公司，避免 guard 误拦+黄金集误采。
_NON_COMPANY = (
    "韩国", "朝鲜", "美国", "中国", "日本", "英国", "法国", "德国", "俄罗斯", "印度", "巴西",
    "澳洲", "加拿大", "意大利", "西班牙", "荷兰", "瑞士", "瑞典", "挪威", "丹麦", "芬兰",
    "美联储", "央行", "财政部", "外交部", "商务部", "工信部", "证监会", "银保监", "国务院",
    "政府", "白宫", "克里姆林宫", "欧盟", "联合国", "世卫", "世贸", " IMF", "世界银行",
    "特朗普", "拜登", "普京", "吴清", "易会满", "郭树清", "潘功胜", "耶伦", "鲍威尔", "拉加德",
    "英媒", "美媒", "日媒", "韩媒", "法媒", "德媒", "俄媒", "港媒", "台媒", "外媒", "媒体",
    "记者", "编辑", "评论", "社评", "观察", "分析", "解读", "盘点", "汇总", "一览", "晚间",
    "早间", "午间", "重磅", "突发", "快讯", "独家", "深度", "世界", "全球", "全国", "全省",
    "全市", "A股", "港股", "美股", "沪深", "创业板", "科创板", "北交所", "新三板", "报道",
    "财联社", "新华社", "央视", "人民网", "环球时报", "环球网", "澎湃", "界面", "第一财经",
)


def company_subject(title):
    """提取 A股公司公告的公司主语（如'通威股份：拟推...员工持股'→通威股份）。
    非公告/无公司主语/非公司前缀(国家/政府/媒体/人名/泛词)返回 None。
    用于聚类'不同公司不通稿模板误并'的精度兜底。
    判据: '公司名：...'且冒号后含公司动作词，或'公司名+动作'无冒号；主语须非 _NON_COMPANY。"""
    t = clean_text(title or "")
    if not t:
        return None
    subj = None
    m = re.match(r"^([\u4e00-\u9fffA-Za-z0-9]{2,12})[：:](.+)$", t)
    if m and re.search(_CORP_ACTION, m.group(2)):
        subj = m.group(1)
    if subj is None:
        m = re.match(r"^([\u4e00-\u9fff]{2,10})" + _CORP_ACTION, t)
        if m:
            subj = m.group(1)
    if subj is None:
        return None
    if any(subj.startswith(nc) or nc.startswith(subj) for nc in _NON_COMPANY):
        return None
    return subj


def norm_title_key(title):
    """规范化标题键：去HTML/【】栏目前缀/标点空白，仅留CJK+字母数字并小写。
    跨源完全相同(长度≥8)=ground truth同故事通稿，用于聚类召回兜底(强制合并)。
    与 eval_golden._norm_title 同逻辑，保证黄金集正对与聚类规则一致。"""
    t = re.sub(r"<[^>]+>", "", title or "")
    t = re.sub(r"^\s*[【\[][^】\]]*[】\]]\s*", "", t)
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", t).lower()


def load_tier_map(conn):
    m = {}
    try:
        for r in conn.execute("SELECT feed_name, tier FROM feed_health"):
            m[r["feed_name"]] = r["tier"] or "T2"
    except sqlite3.OperationalError:
        pass
    return m


def load_feed_weights():
    try:
        import yaml
        cfg = yaml.safe_load(open(CONFIG, encoding="utf-8"))
        return cfg.get("feed_weights", {}) or {}
    except Exception:
        return {}


def wire_key(feed_name):
    low = (feed_name or "").lower()
    for key, pats in WIRE_GROUPS.items():
        if any(p in low for p in pats):
            return key
    return feed_name  # 非通讯社：源名即独立键


def now_local():
    return datetime.now()


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
    return None


def window_articles(conn, window_h=WINDOW_H):
    cutoff = (now_local() - timedelta(hours=window_h)).isoformat()
    rows = conn.execute(
        "SELECT id, feed_name, title, summary, content, link, category, tags, fetched_at, hash "
        "FROM articles WHERE fetched_at >= ? ORDER BY fetched_at ASC", (cutoff,)).fetchall()
    return rows


def embed_articles(conn, window_h=WINDOW_H, batch=256, verbose=True):
    """嵌入窗口内尚无向量的文章，存 article_vectors BLOB。幂等。"""
    init_db(conn)
    rows = window_articles(conn, window_h)
    have = {r[0] for r in conn.execute("SELECT article_id FROM article_vectors")}
    todo = [r for r in rows if r["id"] not in have]
    if verbose:
        print(f"窗口{window_h}h文章={len(rows)} 已有向量={len(have & {r['id'] for r in rows})} 待嵌入={len(todo)}")
    t0 = time.time()
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        texts = [clean_text(r["title"]) + " " + clean_text(r["summary"])[:300] for r in chunk]
        vecs = Embedder.embed(texts)
        conn.executemany(
            "INSERT OR REPLACE INTO article_vectors(article_id, emb, dim, model) VALUES(?,?,?,?)",
            [(r["id"], v.astype(np.float32).tobytes(), int(v.shape[0]), MODEL_NAME)
             for r, v in zip(chunk, vecs)])
        conn.commit()
        if verbose:
            print(f"  嵌入 {min(i+batch,len(todo))}/{len(todo)} ({round(time.time()-t0,1)}s)")
    return len(todo)


def load_vectors(conn, ids):
    """返回 (ids列表, 归一化向量矩阵)。全表加载+Python过滤(避免IN>999变量上限)。"""
    idset = set(ids)
    rows = conn.execute("SELECT article_id, emb FROM article_vectors").fetchall()
    m = {r["article_id"]: np.frombuffer(r["emb"], dtype=np.float32)
         for r in rows if r["article_id"] in idset}
    out_ids = [i for i in ids if i in m]
    mat = np.array([m[i] for i in out_ids], dtype=np.float32) if out_ids else np.zeros((0, 384), np.float32)
    return out_ids, norm_rows(mat)


def cluster(conn, window_h=WINDOW_H, cos_direct=COS_DIRECT, cos_entity=COS_ENTITY, verbose=True):
    """窗口重建聚类：按 fetched_at 升序增量并入事件（质心余弦 + 实体重叠）。
    2026-11-17: 动态别名刷新(P1-5) + top-K 候选扫描(P0-2, 修贪心单点漏并)。"""
    init_db(conn)
    refresh_dynamic_aliases(conn)
    rows = window_articles(conn, window_h)
    if not rows:
        print("窗口内无文章"); return 0
    ids = [r["id"] for r in rows]
    vids, vmat = load_vectors(conn, ids)
    if len(vids) < len(ids):
        if verbose:
            print(f"警告: {len(ids)-len(vids)} 篇缺向量，先跑 embed")
    id2row = {r["id"]: r for r in rows}
    vindex = {aid: k for k, aid in enumerate(vids)}
    tier_map = load_tier_map(conn)

    # 清空窗口内旧事件（重建；canonical_hash 保留供未来跨run匹配）
    cutoff = (now_local() - timedelta(hours=window_h)).isoformat()
    old_ev = [r[0] for r in conn.execute("SELECT event_id FROM events WHERE last_seen >= ?", (cutoff,))]
    if old_ev:
        # 根因修复: 子查询删除替代 IN 枚举。old_ev 可达数千 > SQLite 999 变量上限，
        # re-cluster(daily管线)必崩 too many SQL variables。子查询无变量上限，条件等价。
        conn.execute("DELETE FROM event_members WHERE event_id IN (SELECT event_id FROM events WHERE last_seen >= ?)", (cutoff,))
        conn.execute("DELETE FROM event_entities WHERE event_id IN (SELECT event_id FROM events WHERE last_seen >= ?)", (cutoff,))
        conn.execute("DELETE FROM events WHERE last_seen >= ?", (cutoff,))
        conn.commit()

    events = []   # dict: members(list aid), centroid(np), ents(set), first/last
    centroids = np.zeros((0, 384), np.float32)
    t0 = time.time()
    title2event = {}   # 规范化标题→事件index，召回兜底用
    for aid in vids:
        r = id2row[aid]
        v = vmat[vindex[aid]]
        ents = extract_entities((r["title"] or "") + " " + (r["summary"] or ""))
        subj = company_subject(r["title"])
        nt = norm_title_key(r["title"])
        merged = False
        best_j, best_sim = -1, -1.0
        # 召回兜底(§11): 跨源规范化标题完全相同(≥8字符)=ground truth同故事通稿，强制合并，
        # override cosine。同标题不同正文摘录会拉低cosine致欠合并(如国家统计局发布会格隆汇vs金十)。
        # 同标题→同company_subject，与下方精度guard不冲突。
        ti_j = title2event.get(nt) if len(nt) >= 8 else None
        if ti_j is not None:
            best_j, best_sim, merged = ti_j, 1.0, True
        elif len(events):
            # 2026-11-17 P0-2: top-K 候选扫描替代贪心 argmax 单点。
            # 实测 Jensen 英文簇间 cos=0.768(≥0.75+共享NVIDIA)却漏并: 最高cos候选无共享实体时
            # 旧逻辑直接新建事件。现依次试前8个(≥cos_entity)候选, 第一个通过路径+guard者并入。
            sims = centroids @ v
            order = np.argsort(-sims)
            for j in order[:8]:
                s = float(sims[j])
                if s < cos_entity:
                    break
                ok = s >= cos_direct or len(ents & events[j]["ents"]) >= 1
                if not ok:
                    continue
                # 精度兜底(§11 宁少并不错并): 不同公司主语的 A股公告，即使通稿模板 cosine 高也不合并。
                # 公司核心=主语前2汉字(品牌区分位)，同公司不同写法核心相同→不误拆(保护recall)；
                # 不同公司核心各异→拦截(跳过该候选继续试下一个)。仅双方都有具体公司主语才生效。
                if subj:
                    ev_subj = events[j]["subjects"]
                    if ev_subj and subj[:2] not in {x[:2] for x in ev_subj}:
                        continue
                best_j, best_sim, merged = int(j), s, True
                break
        if merged:
            ev = events[best_j]
            ev["members"].append(aid)
            ev["ents"] |= ents
            if subj:
                ev["subjects"].add(subj)
            ev["last"] = r["fetched_at"]
            n = len(ev["members"])
            ev["centroid"] = norm_rows((ev["centroid"] * (n - 1) + v)[None, :])[0]
            centroids[best_j] = ev["centroid"]
            ev["sims"][aid] = best_sim
            if len(nt) >= 8:
                title2event[nt] = best_j
        else:
            events.append({"members": [aid], "centroid": v.copy(), "ents": ents,
                           "subjects": {subj} if subj else set(),
                           "first": r["fetched_at"], "last": r["fetched_at"],
                           "sims": {aid: 1.0}})
            centroids = np.vstack([centroids, v[None, :]]) if len(centroids) else v[None, :]
            if len(nt) >= 8:
                title2event[nt] = len(events) - 1
    if verbose:
        print(f"聚类: {len(vids)}篇 → {len(events)}事件 ({round(time.time()-t0,1)}s), "
              f"合并率={round(100*(1-len(events)/max(1,len(vids))),1)}%")

    # 落库 events + event_members + canonical + n_indep + salience
    weights = load_feed_weights()
    vel = load_velocity_map(conn)
    bursts = load_bursts(conn)
    interest = load_interest(conn)
    now = now_local()
    n_multi = 0
    for ev in events:
        mem = ev["members"]
        canon_id = pick_canonical(id2row, mem, tier_map, weights)
        cr = id2row[canon_id]
        n_indep = len({wire_key(id2row[a]["feed_name"]) for a in mem})
        if len(mem) >= 2:
            n_multi += 1
        label = cr["title"]
        topic = cr["category"] or "综合"
        sal = compute_salience(cr, mem, id2row, n_indep, tier_map, weights, vel, bursts, interest, now)
        cur = conn.execute(
            "INSERT INTO events(label,topic,first_seen,last_seen,canonical_id,salience,n_indep_sources,status,canonical_hash) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (label, topic, ev["first"], ev["last"], canon_id, sal, n_indep, "active", cr["hash"]))
        eid = cur.lastrowid
        conn.executemany("INSERT INTO event_members(event_id,article_id,similarity) VALUES(?,?,?)",
                         [(eid, a, ev["sims"].get(a, 0.0)) for a in mem])
        # 事件实体
        for en in ev["ents"]:
            er = conn.execute("INSERT OR IGNORE INTO entities(name,type) VALUES(?,?)", (en, "auto"))
            ent_id = conn.execute("SELECT entity_id FROM entities WHERE name=?", (en,)).fetchone()[0]
            conn.execute("INSERT INTO event_entities(event_id,entity_id,role) VALUES(?,?,?)", (eid, ent_id, "mention"))
    conn.commit()
    if verbose:
        print(f"落库完成: 多源事件(≥2成员)={n_multi}, 阈值 direct={cos_direct} entity={cos_entity}")
    return len(events)


def number_density(text):
    if not text:
        return 0.0
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    return len(nums) / max(1, len(text) / 100.0)


def pick_canonical(id2row, members, tier_map, weights):
    best, best_score = members[0], -1
    for a in members:
        r = id2row[a]
        tier = tier_map.get(r["feed_name"], "T2")
        tb = TIER_BONUS.get(tier, 1.0)
        full = clean_text(r["content"] or r["summary"] or "")
        flen = min(1.0, len(full) / 800.0)
        nd = min(1.0, number_density(full) / 3.0)
        sw = float(weights.get(r["feed_name"], 3)) / 10.0
        score = tb * (0.4 + 0.3 * flen + 0.2 * nd + 0.1 * sw)
        if score > best_score:
            best_score, best = score, a
    return best


def load_velocity_map(conn):
    """T3 热榜 velocity：title指纹 → 最大 velocity。"""
    m = {}
    try:
        for r in conn.execute("SELECT title, velocity FROM velocity_signals"):
            fp = fingerprint(r["title"])
            if fp:
                m[fp] = max(m.get(fp, 0.0), float(r["velocity"] or 0))
    except sqlite3.OperationalError:
        pass
    return m


def load_bursts(conn):
    m = {}
    now = now_local().isoformat()
    try:
        for r in conn.execute("SELECT topic, boost, expires_ts FROM topic_burst"):
            if not r["expires_ts"] or r["expires_ts"] >= now:
                m[r["topic"]] = float(r["boost"] or 0)
    except sqlite3.OperationalError:
        pass
    return m


def load_interest(conn):
    m = {}
    now = now_local().isoformat()
    try:
        for r in conn.execute("SELECT key, weight, expires FROM interest_profile"):
            if not r["expires"] or r["expires"] >= now:
                m[r["key"]] = float(r["weight"] or 0)
    except sqlite3.OperationalError:
        pass
    return m


def compute_salience(canon_row, members, id2row, n_indep, tier_map, weights, vel, bursts, interest, now):
    # W_source: 簇内最高源权重
    w_source = max(float(weights.get(id2row[a]["feed_name"], 3)) for a in members)
    # V: T3 热榜速度（标题指纹匹配），normalize 到 [0,1] 增益
    v_raw = 0.0
    for a in members:
        fp = fingerprint(id2row[a]["title"])
        v_raw = max(v_raw, vel.get(fp, 0.0))
    V = 1.0 + min(1.0, v_raw / 4.0)   # velocity~3.4 → +0.85
    # D: 时间衰减
    last = parse_dt(canon_row["fetched_at"]) or now
    dt_h = max(0.0, (now - last).total_seconds() / 3600.0)
    D = math.exp(-dt_h / HALF_LIFE_H)
    # P: 兴趣匹配 + 热点boost（WP6 个人化前 interest 空 → 1）
    ents = extract_entities((canon_row["title"] or "") + " " + (canon_row["summary"] or ""))
    gain = 0.0
    for en in ents:
        gain += interest.get("entity:" + en, 0.0)
    gain += interest.get("topic:" + (canon_row["category"] or ""), 0.0)
    p_interest = min(2.0, max(0.3, 1.0 + gain))   # D3: 负gain允许demote(少点/没用), floor0.3防清零; gain=0→1保持无个人化基线
    burst = bursts.get(canon_row["category"] or "", 0.0)
    P = p_interest * (1.0 + burst)
    # B: tier_bonus
    tier = tier_map.get(canon_row["feed_name"], "T2")
    B = TIER_BONUS.get(tier, 1.0)
    S = w_source * (1.0 + math.log(1.0 + n_indep)) * V * D * P * B
    return round(S, 4)


def top_events(conn, n=20):
    return conn.execute(
        "SELECT event_id, label, topic, salience, n_indep_sources, canonical_id, last_seen "
        "FROM events WHERE status='active' ORDER BY salience DESC LIMIT ?", (n,)).fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["init", "embed", "cluster", "top", "run"])
    ap.add_argument("--window", type=int, default=WINDOW_H)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--cos-direct", type=float, default=COS_DIRECT)
    ap.add_argument("--cos-entity", type=float, default=COS_ENTITY)
    a = ap.parse_args()
    conn = get_conn()
    if a.cmd == "init":
        init_db(conn); print("事件表已建(增量)")
    elif a.cmd == "embed":
        embed_articles(conn, a.window)
    elif a.cmd == "cluster":
        cluster(conn, a.window, a.cos_direct, a.cos_entity)
    elif a.cmd == "run":
        init_db(conn); embed_articles(conn, a.window); cluster(conn, a.window, a.cos_direct, a.cos_entity)
    elif a.cmd == "top":
        for r in top_events(conn, a.n):
            print(f"[{r['event_id']}] S={r['salience']:.2f} N={r['n_indep_sources']} {r['topic']} | {r['label'][:60]}")
    conn.close()


if __name__ == "__main__":
    main()
