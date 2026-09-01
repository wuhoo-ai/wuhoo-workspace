#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""Wuhoo RSS 简报生成 v2 — 跨主题事件分组 → 分类 → 主题内去重"""
import sqlite3, re
from collections import defaultdict

DB = "/home/admin/wuhoo-workspace/skills/default/wuhoo-news-rss/data/news.db"

# ── 清洗 ──────────────────────────────────────────────
def clean_html(t):
    t = re.sub(r'<!--.*?-->', ' ', t, flags=re.DOTALL)
    t = re.sub(r'<[^>]+>', '', t)
    t = re.sub(r'</?[A-Za-z][^>]*$', '', t)  # 尾部未闭合标签片段 <spa
    t = re.sub(r'&nbsp;|&amp;|&lt;|&gt;|&quot;|&#\d+;', ' ', t)
    return t

def clean_title(t):
    t = clean_html(t).strip()
    t = re.sub(r'^IT之家\s*\d+\s*月\s*\d+\s*日\s*消息[，,]?', '', t).strip()
    t = re.sub(r'^36氪获悉[，,]?', '', t).strip()
    t = re.sub(r'^[\u4e00-\u9fff\w]+[\d]*月\d+日\|?', '', t).strip()
    t = t.split('|')[0].strip()
    return t

def clean_summary(s, feed_name=''):
    s = clean_html(s).strip()
    # HN: 评论链接形式
    s = re.split(r'Comments on Hacker News|Article URL:|Comments URL:', s)[0]
    s = re.sub(r'^你的器材不支持播放多媒体材料\s*Play video,?\s*', '', s)
    s = re.sub(r'^IT?之家\s*\d+\s*月\s*\d+\s*日\s*消息[，,]?', '', s)
    # BBC 中文 byline 结构 (仅该源)
    if 'bbc 中文' in feed_name.lower():
        s = re.split(r'Article Information', s)[0]
        s = re.sub(r'^图像来源[，,、\s]*', '', s)
        s = re.sub(r'^[A-Za-z][A-Za-z\s/&.\-]*?(?=\s*[0-9\u4e00-\u9fff])', '', s)
        s = re.sub(r'Published\s+.*?阅读时间:?\s*[\d\s]*分钟?', '', s, flags=re.I)
        s = re.sub(r'^\s*\d{4}年\d{1,2}月\d{1,2}日\s*阅读时间:?\s*[\d\s]*分钟?', '', s)  # 中文日期变体, 前导空格容错 (2026-08-31)
    s = s.split('|')[0].strip()
    s = re.sub(r'\s+', ' ', s).strip()
    if not re.search(r'[\u4e00-\u9fffA-Za-z0-9]', s):
        return ''
    return s[:50]

# ── Feed 级过滤 ───────────────────────────────────────
FEED_NOISE_RE = re.compile(r'arxiv|知乎日报', re.I)
SPORT_FEED_RE = re.compile(r'football|soccer|sport', re.I)
SA_LOW_RE = re.compile(r'q[12]\s*20\d\d|commentary|portfolio update|earnings call', re.I)

# ── 噪声模式 (全量, skill 2026-08-20 版) ───────────────
NOISE_PATTERNS = [
    'usb cheat', 'usbcheat', 'c64_music', 'discret 11', 'fabiensanglard',
    'martin galway', 'beans', 'gassy', 'cosmology with geometry',
    'rdp client', 'coding assistance', 'blender open', 'lambench',
    'ramen', 'cooking', 'serious eats', 'marty', 'marty pc',
 # 2026-08-27 新增 — 王室名人/自营晨报/消费软文
 '哈利和梅根', 'meghan', 'harry and meghan',
 '早餐FM', 'fm-radio', '早安之声', 'it早报',  # IT之家每日聚合栏目 (日更非事件, 同类早餐FM; 模式必须小写!)
 'plug-in solar', '10p coin', 'back to school', 'uniform costs',
    'mandelson', 'vetting scandal', 'ian collard', 'chief property',
    'white house correspondents', 'correspondents dinner',
    '持霰弹枪', '枪击', '安保区域', '安保人员', '加强安保',
    'evacuat', 'loud bangs', 'gunman', 'shooting',
    '白宫记者协会晚宴', '白宫记协晚宴', '白宫安全事件',
    '涉事枪手已被', '特朗普将举行新闻发布会', '特朗普：30分钟',
    '特朗普发帖', '特朗普说白宫',
    '特勤局不希望特朗普', '特朗普坚持要回去',
    '舒默.*白宫记者晚宴', '少数党领袖.*白宫',
    '张凌赫', '逐玉', '热播',
    'guardiola', 'fa cup', 'silverware', 'manchester city',
    'premier league', 'arsenal', 'celtic', 'ronnie o', 'snooker',
    'arxiv', 'ps5', '数毛社', 'digital foundry', 'predator',
    'deepseek', 'cohere', 'piloting ships', 'strait of hormuz',
    'fine-tuning', 'brief chatbot',
    '软银', 'battery', '电池', '魔兽世界', 'blizzard',
    'sloth', '树懒', 'jeanine pirro', 'booktok',
    '全国铁路预计发送旅客', '铁路发送旅客', '高速公路', '五一假期首日',
    '五一档新片票房', '五一档票房', '票房破', '票房榜',
    '广东进入强降雨', '雷雨大风', '暴雨预警',
    '高速公路充电量', '假期第二日', '4a级及以上景区',
    'arabic', 'العربية', 'الجزيرة',
    '广汽国际', '出口量同比增长',
    '义龙庆高速', '隧道',
    '苏州购房新政', '公积金贷款', '楼市新政',
    '多囊卵巢', '卵巢综合征', 'cell封面', '营养基因组', '遗传病', '维生素 ',
    '免疫治疗', 'immunotherapy', 'cancer patient', 'tumour',
    '学术霸凌', '学术生涯',
    '拱北口岸', '短途跨境', '返乡游', '反向旅行', '300元住五星',
    'labour mps', 'leadership speculation', 'australia news live',
    '卢秀燕', '斯威士兰', '国民党',
    '印尼统计局', 'cpi同比',
    'nazi', 'hitler',
    'giuliani', 'mayor',
    'legacy tax', 'inheritance tax',
    '豆包.*付费', 'app store.*付费',
    'graffiti', 'street art',
    'ukraine.*drone',
    'billam-smith', 'rozicki',
    'royal ascot', 'fantasy force', 'hidden gift',
    'hamilton.*leclerc', 'monaco grand prix', 'ferrari.*monaco',
    'prostate cancer screening',
    '沉迷白日夢', '白日梦',
    '王莉霞', '受賄金額',
    '深海迷航', '深岩银河', 'subnautica', 'deep rock galactic',
    '高考报名人数', '高考.*开考',
    'california primary election',
    '振华股份.*买入', '研报掘金',
    'sky sports football',
    'hamilton.*ferrari',
    'can hamilton beat',
    'vgn.*鼠标', '大师版.*鼠标', 'nordic 54l15',
    '哥倫比亞.*候選', '哥倫比亞.*總統',
    '鹅腿阿姨', '成本价.*块', '塌房', '清澈的愚蠢',
    '朱思码记', '西湖论功', '雍正', '断桥',
    '泰国.*公主', '泰国.*病逝', '公主.*病逝', '公主.*逝世',
    '王室.*公告', 'royal.*palace', '泰国王室', '宮務處',
    'thai princess', 'bajrakitiyabha', 'dies after years in coma',
    'king.*eldest daughter', 'thai king',
    '地震已造成', '地震.*死亡', '地震.*失踪', '地震.*受伤',
    'earthquake.*kill', 'earthquake.*dead', 'earthquake.*injured',
    '死亡.*地震', '强震', '洪水.*死亡', '台风.*袭击',
    '京东红包', '618.*红包', '双11', '猜拳', '赢红包', '抽奖',
    '网信办.*公[约約]', '自律公约',
    'bbc sport football', 'the guardian football', 'football rankings',
    'soccernews', 'football italia', 'world soccer talk',
    'world cup', 'confirmed lineups', 'heung-min son',
    '瞎扯', '知乎日报',
    '宏福苑', '火灾',
    '槍擊', '枪杀',
    'livestream in mexico', 'tiktok influencer', 'influencer shot',
    '敘利亞', '叙利亞', '爆炸',
    '交管台海', '陸委會', '海峽論壇', '饒慶鈴',
    '汉光', '漢光', '演习', '演習',
    'man united', 'man utd', 'chelsea', 'liverpool fc', 'transfer news', 'nba', 'nfl',
    'apple is getting this wrong',
    'hyrox', 'fitness craze',
    'full confidence',
    'lowest price',
    '晒表', '帝舵',
    'trainline', 'virgin atlantic',
    'money disagre', 'asking couples',  # BBC Business 街头采访软内容 (夫妻金钱分歧) 误入财经 TOP
    '班克斯|banksy', 'hitomi soga', '被迫嫁给美国士兵', 'business daily',
    '賈姬', '白頭海鵰', '白头海雕',
    '月经周期', '黄体期', '变丑', '躺在床上喝茶',
    'astrotourists', 'solar eclipse', '日食',
    'ceuta', 'migrant', 'asylum', '偷渡', '难民', 'farage', 'by-election', 'clacton',
    'phone calls to military bases', 'accidentally logged',  # HN 个人技术事故 (military 命中宏观政策误分)
    'grand theft auto', 'gta',  # GTA 预告/泄露/观看指南 (Engadget 游戏娱乐误入产业/公司, gta 覆盖 VI/6/6 数字变体)
    # 2026-08-31 新增 — 街头采访软内容/HN 泛评论/DW 栏目特稿挤占 TOP
    'spend too much on', 'central london shoppers',   # BBC Business 街头采访 (同类: money disagre/asking couples)
    'works better in the app',                        # HN 泛评论 (app vs web 争论, 非新闻事件)
    'dw users on life',                               # 德国之声系列特稿 (民众生活软内容, 非新闻事件)
]

def is_noise(text):
    tl = text.lower()
    for p in NOISE_PATTERNS:
        if re.search(p, tl):
            return True
    return False

# ── 四类关键词表 ──────────────────────────────────────
KEYWORDS = {
    '科技/AI': [
        '人工智能','大模型','llm','gpt','claude','openai','deepmind','gemini','anthropic',
        '英伟达','nvidia','gpu','芯片','chip','semiconductor','tsmc','台积电','intel','amd',
        '光刻','asml','hbm','制程','机器人','robot','具身智能','自动驾驶','量子','quantum',
        '算法','模型','软件','苹果','apple','微软','microsoft','谷歌','google','meta','facebook',
        '特斯拉','tesla','华为','huawei','高通','qualcomm','手机','smartphone','5g','6g',
        '操作系统','开源','open source','编程','代码','developer','云计算','cloud','数据中心',
        '服务器','dram','nand','晶圆','封装','专利','论文','研究','research','生成式','generative',
        '多模态','multimodal','推理','inference','agent','ai agent','神经网络','deep learning',
        '机器学习','transformer','数字人','脑机接口','vr','ar','元宇宙','metaverse','vision pro',
        'galaxy','iphone','android','windows','linux','浏览器','app','应用商店','开发者',
        '开源模型','权重','训练','算力','computing power','芯片出口','cybersecurity','网络安全',
        '数据泄露','data breach','chatgpt','copilot','sora','大语言模型','foundation model','基座模型',
        'cpo','共封装光学','海力士','hynix','sk hynix','hacker','黑客','漏洞','vulnerability',
        'exploit','后门','供应链攻击','零日',
    ],
    '财经/投资': [
        '股市','港股','美股','a股','上证','恒生','纳指','标普','道指','ipo','上市','财报',
        'earnings','营收','净利润','市值','估值','基金','etf','债券','bond','收益率','yield',
        '利率','降息','加息','美联储','fed','央行','黄金','gold','比特币','bitcoin','加密',
        'crypto','以太坊','大宗商品','原油','油价','oil','铜价','期货','futures','期权',
        '涨停','跌停','熔断','回购','buyback','分红','股息','券商','投行','投资者','investor',
        '熊市','牛市','流动性','liquidity','汇率','外汇','人民币','美元','日元','欧元',
        '非农','cpi','pmi','gdp','通胀','通缩','缩表','qe','交易','trading','对冲基金',
        'hedge fund','私募','公募','股东','套现','减持','增持','业绩','盈利','亏损',
        '股价','股票','stock','share','盈喜','盈警','配股','供股','上市首日','破发',
        'quantitative trading','量化','alpha','阿尔法','因子','回测','策略','做市',
        'invest','funding','融资','独角兽','指数','index fund','证券','securities','保证金',
    ],
    '宏观政策': [
        '关税','tariff','制裁','sanction','贸易战','trade war','外交','大使','外交部','白宫',
        '国会','参议院','众议院','法案','立法','监管','法规','政策','选举','election',
        '总统','总理','首相','内阁','政府','government','联合国','欧盟','eu','nato','北约',
        '谈判','协议','条约','签证','移民','immigration','战争','冲突','conflict','导弹',
        '核','nuclear','军事','military','国防','defense','军队','地缘','geopolitical',
        '台湾','台海','南海','东海','朝鲜','伊朗','iran','俄罗斯','russia','乌克兰','ukraine',
        '以色列','israel','巴勒斯坦','中东','中美','中欧','中俄','贸易','trade','出口管制',
        'export control','补贴','subsidy','反倾销','世贸','wto','imf','峰会','summit','g7','g20',
        '气候','climate','碳排放','碳中和','经济','economy',
        '增长','growth','衰退','recession','失业','就业','失业率','劳动力','通胀','inflation',
        '货币','货币政策','财政','fiscal','预算','budget','国债','赤字','贸易协议','贸易协定',
        'trade deal','trade talks','trade agreement','加拿大','canada','墨西哥','mexico',
    ],
    '产业/公司': [
        '收购','并购','acquisition','合并','merger','私有化','裁员','layoff','重组',
        'restructuring','供应链','supply chain','工厂','产能','订单','合作','partnership',
        '签约','投资','invest','融资','funding','子公司','分拆','spin-off','合资','建厂',
        '扩产','投产','量产','交付','销量','出货','市场份额','market share','竞争对手',
        '新产品','旗舰','迭代','生态','ecosystem','平台','platform','零售','电商',
        '跨境','amazon','亚马逊','temu','shein','抖音','快手','微信','支付宝','美团','滴滴',
        '字节','腾讯','阿里','百度','京东','小米','比亚迪','宁德时代','三星','samsung',
        '索尼','sony','任天堂','nintendo','迪士尼','disney','netflix','奈飞','spotify',
        'uber','airbnb','波音','boeing','空客','airbus','财年','guidance','营收指引',
        '预购','预售','门店','开业','旗舰店','新能源','光伏','风电','储能','创新药',
        'biotech','医疗器械','房地产','楼市','电动车','ev','solid state','代工','foundry','fab',
        '财報','營收','利潤','裁員','收購','併購',
    ],
}

def kw_hit_count(text, kws):
    n = 0
    for kw in kws:
        if re.fullmatch(r'[A-Za-z0-9 .\-/]+', kw):
            if re.search(r'\b' + re.escape(kw) + r'\b', text, re.I):
                n += 1
        else:
            if kw in text:
                n += 1
    return n

def classify(text, category_field):
    scores = {t: 0 for t in KEYWORDS}
    for t, kws in KEYWORDS.items():
        scores[t] = kw_hit_count(text, kws)
    # 特殊规则
    if re.search(r'\barm\b', text) and any(x in text for x in ['芯片','cpu','ip','licens','semi']):
        scores['科技/AI'] += 1
    if re.search(r'trump|特朗普', text) and any(x in text.lower() for x in ['pakistan','iran','negotiat','tariff','谈判','制裁']):
        scores['宏观政策'] += 2
    if re.search(r'trade deal|trade talks|trade agreement|贸易协议|贸易协定', text, re.I):
        scores['宏观政策'] += 3
    # database category 加权 (只信 财经/投资/ai)
    cm = {'财经': '财经/投资', '投资': '财经/投资', 'ai': '科技/AI'}
    if category_field in cm:
        scores[cm[category_field]] += 3
    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return None
    return best

# ── 事件去重 ──────────────────────────────────────────
def norm(t):
    return re.sub(r'[，,、；;：:。.·！!？?\"\'（）()\[\]【】]+', ' ', t).strip()

# 强实体事件规则 (仅跨源同一事件, 泛公司名不放这里避免过度合并)
ENTITY_KEYS = [
    (re.compile(r'(unitree|宇树).*(ipo|上市|首日|debut|surge|打新)|(ipo|上市|首日|debut).*(unitree|宇树)', re.I), 'unitree_ipo'),
    (re.compile(r'(shein|希音).*(ipo|上市|首日|debut|surge|打新|发售)|(ipo|上市|首日|debut|打新|发售).*(shein|希音)', re.I), 'shein_ipo'),
    (re.compile(r'taalas', re.I), 'amd_taalas'),
    (re.compile(r'hassabis|迪恩', re.I), 'hassabis_deepmind'),
    (re.compile(r'meta.*(fined|fine|罚|567)', re.I), 'meta_fined'),
    (re.compile(r'(trump|特朗普).*(vaccine|疫苗)|(vaccine|疫苗).*(trump|特朗普)', re.I), 'trump_vaccine'),
    (re.compile(r'astra|cyber capabilit', re.I), 'openai_astra'),
    (re.compile(r'数十国|dozens of countries', re.I), 'trump_tariff_china'),
    (re.compile(r'伊朗.*(外长|会谈|谈判|提议|阿拉格齐)', re.I), 'iran_diplomacy'),
    (re.compile(r'谷歌.*anthropic|google.*anthropic', re.I), 'google_anthropic'),
    (re.compile(r'超聚变', re.I), 'superfusion_ipo'),
    (re.compile(r'prime air|drone deliver', re.I), 'amazon_prime_air'),
    (re.compile(r'alexa.*(free|fire tv)|fire tv.*alexa', re.I), 'amazon_alexa_free'),
    # 2026-08-31: 沃什杰克逊霍尔首秀放鹰 (8/28-29 最大事件, 39条报道分散占据财经 TOP5 4条)
    (re.compile(r'(warsh|沃什).*(jackson hole|杰克逊霍尔)|(jackson hole|杰克逊霍尔).*(warsh|沃什)', re.I), 'warsh_jackson_hole'),
    # 2026-08-31: 冰岛欧盟公投 (HN+德国之声 两条同事件)
    (re.compile(r'(iceland|冰岛).*(eu|欧盟)|(eu|欧盟).*(iceland|冰岛)', re.I), 'iceland_eu'),
    # 2026-08-31: Anthropic 黑名单裁决 (HN+BBC Business 两条同事件)
    (re.compile(r'anthropic.*(blacklist|unlawful|retaliat|judge|ruling)|(blacklist|unlawful|retaliat|judge).*anthropic', re.I), 'anthropic_ruling'),
]

def entity_key(title, summary):
    combined = norm(f'{title} {summary}')
    for rx, key in ENTITY_KEYS:
        if rx.search(combined):
            return key
    return None

def group_events(articles):
    """全量事件分组: entity_key 优先, 否则 norm(title)[:40] 指纹"""
    groups = defaultdict(list)
    for a in articles:
        ek = entity_key(a['title'], a['summary'])
        key = ('e', ek) if ek else ('t', norm(a['title'])[:40])
        groups[key].append(a)
    return list(groups.values())

def pick_representative(group):
    """代表: hot 高优先, 同 hot 有日期优先; 返回 (rep, 唯一源数)"""
    srcs = set(a['feed_name'] for a in group)
    rep = sorted(group, key=lambda a: (a['hot_score'], bool(a['pub_date'])), reverse=True)[0]
    return rep, len(srcs)

# ── 主流程 ────────────────────────────────────────────
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("""
    SELECT id, feed_name, title, summary, link, author, pub_date, category, tags, hot_score
    FROM articles WHERE fetched_at >= datetime('now', '-48 hours')
    AND hot_score > 0
    ORDER BY hot_score DESC LIMIT 3000
""")
rows = cur.fetchall()
total_48h = conn.execute(
    "SELECT COUNT(*) FROM articles WHERE fetched_at >= datetime('now', '-48 hours')").fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT feed_name) FROM articles WHERE fetched_at >= datetime('now', '-48 hours')")
n_feeds = cur.fetchone()[0]
conn.close()

articles = []
for r in rows:
    title = clean_title(r['title'])
    summary = clean_summary(r['summary'] or '', r['feed_name'] or '')
    text = f"{title} {summary} {r['tags'] or ''}"
    feed = r['feed_name'] or ''
    if SPORT_FEED_RE.search(feed) or r['category'] == '足球':
        continue
    if FEED_NOISE_RE.search(feed):
        continue
    if 'seeking alpha' in feed.lower() and SA_LOW_RE.search(title.lower()):
        continue
    if not title:
        continue
    if is_noise(text):
        continue
    articles.append({
        'id': r['id'], 'feed_name': feed, 'title': title, 'summary': summary,
        'link': r['link'], 'pub_date': r['pub_date'] or '',
        'category': r['category'] or '', 'hot_score': r['hot_score'] or 0,
    })

# 1) 全量事件分组 (跨主题) → 代表文章
events = group_events(articles)
event_reps = []
for g in events:
    rep, nsrc = pick_representative(g)
    rep['nsrc'] = nsrc
    event_reps.append(rep)

# 2) 分类
topic_articles = {t: [] for t in KEYWORDS}
unmatched = 0
for a in event_reps:
    c = classify(f"{a['title']} {a['summary']}", a['category'])
    if c:
        topic_articles[c].append(a)
    else:
        unmatched += 1

# 3) 主题内二次去重 (title+summary 指纹, 防不同题同事件) + 排序
results = {}
for t in KEYWORDS:
    seen = set()
    merged = []
    for a in sorted(topic_articles[t], key=lambda x: (x['hot_score'], bool(x['pub_date'])), reverse=True):
        k = norm(a['title'] + ' ' + a['summary'])[:80]
        if k in seen:
            continue
        seen.add(k)
        merged.append(a)
    results[t] = merged[:5]

# ── 输出 ──────────────────────────────────────────────
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
print(f"📰 Wuhoo RSS 资讯简报 | {today}")
print("=" * 40)
print(f"数据采集: {n_feeds} 源 | 48 小时窗口 | 库内 {total_48h} 条")

for t in KEYWORDS:
    print()
    print(f"【{t}】共 {len(topic_articles[t])} 条(事件)，展示 TOP {len(results[t])}")
    if not results[t]:
        print("本时段无相关文章")
        continue
    for i, a in enumerate(results[t], 1):
        src_tag = f" [{a['nsrc']}源]" if a['nsrc'] > 1 else ""
        date_str = a['pub_date'][:10] if a['pub_date'] else ''
        print(f"{i}. {a['title']}{src_tag} — {a['feed_name']} | {date_str}")
        s = a['summary'] if a['summary'] else '(无摘要)'
        print(f"   {s}")
    print("─" * 32)

print()
print(f"统计: 48h 总 {total_48h} 条 / 过滤后 {len(articles)} 条 / 事件合并 {len(event_reps)} 条 / 未匹配 {unmatched} 条")
print(f"采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} CST")
