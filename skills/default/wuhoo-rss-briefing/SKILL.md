---
name: wuhoo-rss-briefing
description: "Generate multi-topic news briefing reports from the wuhoo-news-rss SQLite database. Handles topic classification, exclusion filtering, event dedup, and formatted output. Companion to wuhoo-news-rss."
tags: ["wuhoo"]
category: research
---

# Wuhoo RSS 简报生成

从 `wuhoo-news-rss` 的 SQLite 数据库中按自定义主题分类、去重、格式化生成多主题新闻简报。

> **依赖**: `wuhoo-news-rss` skill（数据库位于 `data/news.db`）
> **Python**: 必须使用 `/usr/bin/python3.11`

## 何时使用

- 需要按多个主题同时生成新闻简报（军事/科技/芯片/机器人/财经/政策）
- 需要去除噪声文章和跨源重复报道
- CLI `--top --json` 输出被截断时（用 SQLite 直查代替）

## 核心原则

1. **直接查库**: 用 `execute_code` 查询 SQLite，不依赖 `fetcher.py` CLI
2. **按热度排序**: `hot_score` 现已修复（v2.0），使用 `ORDER BY hot_score DESC, pub_date DESC` 获取真正热门的文章
3. **评分制分类**: 芯片 > 机器人 > 军事 > 财经 > 政策 > 科技（高优先级先匹配，避免重叠）。使用四大类关键词表打分（科技/AI、财经/投资、宏观政策、产业/公司）
4. **事件级去重**: 同事件多源报道合并，标题归一化去前缀后取前 50 字符做 dedup key
5. **Feed 权重已内置**: 高质量源（FT=10, 华尔街见闻=9）文章自然排序靠前，无需额外处理

## 分类流程

### Step 1: 查库

```python
import sqlite3, re
DB = "/home/admin/wuhoo-workspace/skills/default/wuhoo-news-rss/data/news.db"
cursor.execute("""
    SELECT id, feed_name, title, summary, link, author, pub_date, category, tags, hot_score
    FROM articles WHERE fetched_at >= datetime('now', '-48 hours')
    AND hot_score > 0
    ORDER BY hot_score DESC LIMIT 500
""")
# Clean HTML tags from summary/title
```

### Step 2: 优先级分类

```python
assigned = set()
topic_articles = {t: [] for t in topics}

for a in articles:
    if a['id'] in assigned: continue
    if is_chip(a): topic_articles["芯片"].append(a); assigned.add(a['id'])
    elif is_robot(a): topic_articles["机器人"].append(a); assigned.add(a['id'])
    elif is_military(a): topic_articles["军事"].append(a); assigned.add(a['id'])
    elif is_finance(a): topic_articles["财经/投资"].append(a); assigned.add(a['id'])
    elif is_policy(a): topic_articles["宏观政策"].append(a); assigned.add(a['id'])
    elif is_tech(a): topic_articles["科技"].append(a); assigned.add(a['id'])
```

### Step 3: 排除噪声（关键！必须维护）

这些是经过多次迭代积累的全面噪声模式，**按早返回原则**在分类前过滤：

```python
NOISE_PATTERNS = [
    # Hacker News 技术文章误分类 (miscategorized as 军事/科技)
    'usb cheat', 'usbcheat', 'c64_music', 'discret 11', 'fabiensanglard',
    'martin galway', 'beans', 'gassy', 'cosmology with geometry',
    'rdp client', 'coding assistance', 'blender open', 'lambench',
    'ramen', 'cooking', 'serious eats',
    # 机器人分类噪声
    'mandelson', 'vetting scandal', 'ian collard', 'chief property',
    # 白宫记者晚宴安全事件 (大量报道误入财经/宏观政策)
    'white house correspondents', 'correspondents dinner',
    '持霰弹枪', '枪击', '安保区域', '安保人员', '加强安保',
    'evacuat', 'loud bangs', 'gunman', 'shooting',
    '白宫记者协会晚宴', '白宫记协晚宴', '白宫安全事件',
    '涉事枪手已被', '特朗普将举行新闻发布会', '特朗普：30分钟',
    '特朗普发帖', '特朗普说白宫',
    '特勤局不希望特朗普', '特朗普坚持要回去',
    '舒默.*白宫记者晚宴', '少数党领袖.*白宫',
    # 娱乐新闻
    '张凌赫', '逐玉', '热播',
    # 体育新闻误入宏观政策
    'guardiola', 'fa cup', 'silverware', 'manchester city',
    'premier league', 'arsenal', 'celtic', 'ronnie o', 'snooker',
    # 芯片分类排除
    'arxiv', 'ps5', '数毛社', 'digital foundry', 'predator',
    'deepseek', 'cohere', 'piloting ships', 'strait of hormuz',
    'fine-tuning', 'brief chatbot',
    # 机器人分类排除
    '软银', 'battery', '电池', '魔兽世界', 'blizzard',
    # 科技分类排除
    'sloth', '树懒', 'jeanine pirro', 'booktok',
    # 2026-05-03 新增 — 通用噪声 (五一假期、交通、娱乐、非中文/英文内容)
    '全国铁路预计发送旅客', '铁路发送旅客', '高速公路', '五一假期首日',
    '五一档新片票房', '五一档票房', '票房破', '票房榜',
    '广东进入强降雨', '雷雨大风', '暴雨预警',
    '高速公路充电量', '假期第二日', '4a级及以上景区',
    'arabic', 'العربية', 'الجزيرة',
    '广汽国际', '出口量同比增长',
    '义龙庆高速', '隧道',
    '苏州购房新政', '公积金贷款', '楼市新政',
    # 2026-05-04 新增 — 医学/学术/旅游/政治误入
    '多囊卵巢', '卵巢综合征', 'cell封面', '营养基因组', '遗传病', '维生素 ',
    '免疫治疗', 'immunotherapy', 'cancer patient', 'tumour',
    '学术霸凌', '学术生涯',
    '拱北口岸', '短途跨境', '返乡游', '反向旅行', '300元住五星',
    'labour mps', 'leadership speculation', 'australia news live',
    '卢秀燕', '斯威士兰', '国民党',
    '印尼统计局', 'cpi同比',
    'nazi', 'hitler',
    'giuliani', 'mayor',
    'booktok', 'jeanine pirro',
    # 2026-05-04 新增 — 金融/科技分类细化
    'legacy tax', 'inheritance tax',  # 三星遗产税 → 财经
    '豆包.*付费', 'app store.*付费',   # 豆包付费 → 科技
    'graffiti', 'street art',         # 无关噪声
    'ukraine.*drone',                 # 已分类到宏观
    # 2026-06-03 新增 — 体育/游戏/政治/教育误入各板块
    'billam-smith', 'rozicki',            # 拳击新闻误入芯片 (Sky Sports)
    'royal ascot', 'fantasy force', 'hidden gift',  # 赛马误入财经 (Sky Sports)
    'hamilton.*leclerc', 'monaco grand prix', 'ferrari.*monaco',  # F1 误入科技 (Sky Sports)
    'prostate cancer screening',          # 医学误入机器人
    '沉迷白日夢', '白日梦',               # 心理/生活方式误入机器人
    '王莉霞', '受賄金額',                 # 政治腐败误入科技/AI
    '深海迷航', '深岩银河', 'subnautica', 'deep rock galactic',  # 游戏评测误入科技
    '高考报名人数', '高考.*开考',         # 教育新闻误入财经
    'california primary election',        # 政治选举误入科技
    '振华股份.*买入', '研报掘金',         # 券商研报误入科技 (应在财经)
    # 体育源本身 (Sky Sports Football 大量文章混入)
    'sky sports football',                # Sky Sports 足球频道全部为噪声
    'hamilton.*ferrari',                  # F1 Hamilton → Ferrari
    'can hamilton beat',                  # F1 标题
    # 游戏鼠标/外设 (含"芯片"关键词被误分)
    'vgn.*鼠标', '大师版.*鼠标', 'nordic 54l15',
    # 哥伦比亚选举 (含"川普"触发宏观政策后又因其他词进芯片)
    '哥倫比亞.*候選', '哥倫比亞.*總統',
    # 2026-06-12 新增 — 虎嗅生活方式/历史内容误入科技
    '鹅腿阿姨', '成本价.*块', '塌房', '清澈的愚蠢',
    '朱思码记', '西湖论功', '雍正', '断桥',
    # 2026-06-12 新增 — 皇家/公主讣告误入各版块
    '泰国.*公主', '泰国.*病逝', '公主.*病逝', '公主.*逝世',
    '王室.*公告', 'royal.*palace', '泰国王室', '宮務處',
    'thai princess', 'bajrakitiyabha', 'dies after years in coma',
    'king.*eldest daughter', 'thai king',
    # 2026-06-12 新增 — 自然灾害/news 误入产业
    '地震已造成', '地震.*死亡', '地震.*失踪', '地震.*受伤',
    'earthquake.*kill', 'earthquake.*dead', 'earthquake.*injured',
    '死亡.*地震', '强震', '洪水.*死亡', '台风.*袭击',
    # 2026-06-12 新增 — 促销/junk 内容误入科技
    '京东红包', '618.*红包', '双11', '猜拳', '赢红包', '抽奖',
    # 2026-06-12 新增 — 网信办公告误入科技 (应归宏观政策)
    '网信办.*公[约約]', '自律公约',
    # 2026-06-12 新增 — 体育源全量过滤 (BBC Sport/Sky Sports Football/Football Rankings等)
    'bbc sport football', 'the guardian football', 'football rankings',
    'soccernews', 'football italia', 'world soccer talk',
    'world cup', 'confirmed lineups', 'heung-min son',
    # 2026-08-08 新增 — 知乎日报/地方新闻/枪击爆炸/体育/军事演习误入
    '瞎扯', '知乎日报',                  # 知乎日报"瞎扯"栏目 hot_score=38 全场最高噪声！
    '宏福苑', '火灾',                    # 地方火灾
    '槍擊', '槍擊', '枪杀',              # 台湾/泰国枪击
    'livestream in mexico', 'tiktok influencer', 'influencer shot',  # 墨西哥网红被杀
    '敘利亞', '叙利亞', '爆炸',           # 叙利亚爆炸
    '交管台海', '陸委會', '陸委會', '海峽論壇', '饒慶鈴',  # 两岸政治口水
    '汉光', '漢光', '演习', '演習',       # 军事演习误入产业/公司 (BBC中文)
    'man united', 'man utd', 'chelsea', 'liverpool fc', 'transfer news', 'nba', 'nfl',
    'apple is getting this wrong',        # HN 泛技术评论
    # 2026-08-20 新增 — 健身/游戏/促销/生活方式/消费者监督误入各版块
    'hyrox', 'fitness craze',             # 德国健身热潮误入科技/AI (training 命中)
    'full confidence',                    # BBC中文 英国首相模拟游戏误入宏观政策
    'lowest price',                       # The Verge 促销误入产业/公司
    '晒表', '帝舵',                        # 硅谷腕表生活方式误入产业/公司
    'trainline', 'virgin atlantic',       # BBC 消费者监督新闻误入财经 (invest 命中)
    'money disagre', 'asking couples',    # BBC Business 街头采访软内容 (2026-08-22: 夫妻金钱分歧, money 命中财经 TOP)
    # 2026-08-27 新增 — 王室名人/自营晨报/消费软文
    '哈利和梅根', 'meghan', 'harry and meghan',    # 王室名人生活方式误入宏观政策 TOP1 (BBC 中文)
    '早餐FM', 'fm-radio', '早安之声',               # 华尔街见闻自营音频晨报 (非新闻事件, 重复日更)
    'plug-in solar', '10p coin',                  # BBC Business 消费软文误入财经 TOP
    # 2026-08-28 新增 — BBC Business 返校消费软文误入财经 TOP5
    'back to school', 'uniform costs',            # "How to save on uniform costs" 非财经事件
    # 2026-08-29 新增 — 知乎日报科普/游戏娱乐误入各版块
    'grand theft auto', 'gta',                    # GTA 预告/泄露/观看指南 (Engadget 游戏娱乐误入产业/公司, gta 覆盖 VI/6 数字变体)
]

def classify(text):
    for p in NOISE_PATTERNS:
        if p in text.lower(): return 'noise'
    # ... proceed with scoring
```

> **⚠️ 经验教训**: 每次发现新的误分类文章时，立即把关键词加入 NOISE_PATTERNS。
> 白宫记者晚宴事件是 2026-04-26 最大的噪声源，产生了 5+ 条误分类文章。

### Step 4: 事件去重

```python
def event_dedup(arts, key_fn=None):
    seen = set()
    result = []
    for a in arts:
        t = a['title']
        # Remove source prefixes
        t = re.sub(r'^[\u4e00-\u9fff\w]+[\d]*月\d+日\|?', '', t).strip()
        t = re.sub(r'^IT之家\s*\d+\s*月\s*\d+\s*日\s*消息[，,]?', '', t).strip()
        t = re.sub(r'^36氪获悉[，,]?', '', t).strip()
        key = key_fn(t) if key_fn else t[:25]
        if key not in seen:
            seen.add(key)
            result.append(a)
    return result

# 主题特定去重 key
chip_key: "英伟达"/"nvidia" -> "nvidia", "英特尔"/"intel" -> "intel"
military_key: "拦截"+"伊朗" -> "iran_intercept"
finance_key: "谷歌"+"anthropic" -> "google_anthropic", "超聚变" -> "superfusion_ipo"
policy_key: "伊朗"+"外长/会谈/谈判/提议/阿拉格齐" -> "iran_diplomacy"
robot_key: "特斯拉" -> "tesla"
```

## 关键词定义（完整）

详见 `wuhoo-news-rss` skill 的「主题分类简报生成」章节。

## 输出格式

```
📰 Wuhoo RSS 资讯简报 | YYYY-MM-DD
==================================================
数据采集: N源 | 新增M条 | 时间窗口: 48小时

【主题】（共X条，展示TOP10）
1. 标题 | 来源
   摘要（100字内）
...
（该主题不足10条，实际X条）
```

## 分类策略（评分制）

当前采用**评分制分类**而非简单优先级匹配：

```python
scores = {'军事':0, '科技':0, '芯片':0, '机器人':0, '财经':0, '宏观政策':0}

# 对每个主题的关键词计数
for kw in KEYWORDS['军事']:
    scores['军事'] += combined.count(kw)
# ... 其他主题同理

# 芯片特殊规则: 'arm' 需要搭配芯片相关词才计分
if 'arm' in combined and any(x in combined for x in ['芯片','cpu','ip','licens','semi']):
    scores['芯片'] += 1

# 数据库 category 字段加权（+3 分）
cm = {'科技':'科技', '财经':'财经', '投资':'财经', 'ai':'科技'}
c = cm.get(category_field, '')
if c: scores[c] += 3

# 宏观政策特殊规则: trump + 外交/关税/谈判 = +2
if 'trump' in combined and any(x in combined for x in ['pakistan','iran','negotiat','tariff','谈判','制裁']):
    scores['宏观政策'] += 2

best = max(scores, key=scores.get)
if scores[best] <= 0: return None  # 无匹配，跳过
return best
```

## 已知问题

- **event_key 中英混合规则必须双写中英文（2026-08-13）**：`re.search(r'trump', combined)` 无法命中中文标题"特朗普…"，导致 BBC 中文"特朗普撤回部分推荐儿童疫苗"与 BBC World "Trump signs order to limit childhood vaccines" 同事件不合并。修复：实体规则双写 `trump|特朗普`、`vaccine|疫苗`（同批补 hassabis 中文译名、meta 罚款中文）。
- **同题不同摘要版本去重（2026-08-13）**：BBC 中文同一条新闻被抓两次（摘要分别含"Published 2026年8月12日…"与"Published 4 分钟前…"），title 相同但 summary 不同，旧指纹 `t[:40]+s[:30]` 不去重。修复：event_dedup 两步走——第一步按 title[:40] 指纹合并（实体 key 优先），第二步再按 title+summary 指纹合并（防 AMD Taalas 型不同题同事件）。
- **噪声新增（2026-08-13）**：`班克斯|banksy`（街头艺术误入宏观政策）、`hitomi soga|被迫嫁给美国士兵`（朝鲜绑架个人故事）、`business daily`（BBC 播客栏目低信号）、`賈姬|白頭海鵰|白头海雕`（网红动物讣告误入产业）。
- **繁体关键词缺失导致事件不合并（2026-08-10）**：中央社"美國7月非農就業意外減少2.3萬人"与华尔街见闻简体版是同一事件，但 '非农'/'就业'/'失业' 简体词不匹配繁体 '非農'/'就業'/'失業'，event_key 实体规则失效 → 同一事件出现在两个分类。修复：KEYWORDS 与 event_key 规则同时补繁体变体（非農/就業/失業/匯率/黃金/產能/供應鏈），跨主题统一事件归属时用 hot 最高的版本。
- **华尔街见闻/RFI "标题 | 正文" 管道符混入（2026-08-10）**：部分源 title 字段 = "标题 | 当地时间…" 或 summary = "标题 | 正文"（第一财经俄制裁条目 pub_date 被污染成长文本）。修复：clean_title 取 '|' 前段，clean_summary 取 '|' 后段；pub_date 不符合 `^\d{4}-\d{2}-\d{2}` 视为空。
- **BBC 中文多媒体残留（2026-08-10）**：summary 以 `你的器材不支持播放多媒体材料 Play video, "…", 节目全长 2,25 02:25` 开头，占满 50 字窗口。clean_summary 补 `re.sub(r'^你的器材不支持播放多媒体材料\s*Play video,?\s*','',s)`。
- **Seeking Alpha 低信号批量内容（2026-08-10）**：`Alger Dynamic Opportunities Fund Q2 2026 Portfolio Update/Commentary`、`Alpha Teknova ... Earnings Call Transcript` 等基金季报/电话会纪要 hot_score 11 分且标题相似，混入财经 TOP。修复：feed 级过滤 seeking alpha 且含 `q[12] 20\d\d|commentary|portfolio update|earnings call` 直接排除。
- **OpenAI Astra 事件实体级 key（2026-08-10）**：OpenAI Blog 标题 "Responding to the next frontier of critical cyber capabilities" 与卫报 "OpenAI to pause some work on AI model Astra..." 同事件（Astra 安全评估延迟发布），纯标题指纹不去重且 HN 无日期条目占位。修复：event_key 加 `astra|cyber capabilit → openai_astra`，同 hot 时中文标题优先展示（IT之家版）。
- **event_key 必须做标点归一化（2026-08-09）**：同一事件在华尔街见闻"特朗普签署针对出生公民权的行政令 将严厉打击'生育旅游'"与凤凰网"…行政令，将严厉…"仅差逗号/空格，纯 title+summary 指纹不去重。修复：key 构建时 `re.sub(r'[，,、；;：:。.·\s]+',' ',t)` 统一标点后再拼接。
- **重点事件保底插入（2026-08-09 实现）**：Hassabis 卸任 DeepMind（FT 9分×2+卫报 9分，重大 AI 人事）被 hot_score 15-20 分的普通文章挤出科技/AI TOP5。实现 `PRIORITY_EVENTS = [(re.compile(r'hassabis|迪恩|Brin', re.I), '🔬 科技/AI')]`，TOP5 第 5 位被替换插入。注意：FT 此类文章 category='财经'，分类时财经 +3 会与科技/AI 竞争，需确认 classify 结果。
- **BBC 中文摘要"图像来源"前缀（2026-08-09）**：summary 以 `图像来源，Japan Maritime Self Defense Force...` 开头，占满 50 字截断窗口。修复：clean 后先 `re.sub(r'^图像来源[，,、\s]*','',s)` 再截断。
- **生活健康类高分噪声（2026-08-09）**：BBC 中文"月经周期：'黄体期变丑'说法真的存在吗？" hot_score 19 分（含 body 关键词），误入分类。NOISE_PATTERNS 补 `'月经周期','黄体期','变丑','躺在床上喝茶'`。
- **天文旅游误入产业/公司（2026-08-09）**：卫报"Spanish mountain village braces for astrotourists…solar eclipse" 因含 solar 命中新能源→产业。NOISE_PATTERNS 补 `'astrotourists','solar eclipse','日食'`。
- **东海/海洋地缘关键词缺失（2026-08-09）**：BBC 中文"东海开发：施压日本…" hot_score 19 分，因宏观政策表无"东海/钻探平台/海上自卫队"而落到未匹配。宏观政策表补 `'东海','石油钻探','钻探平台','海上自卫队','中间线','岛礁','领海','专属经济区','EEZ'`。
- **事件去重必须结合 title+summary (2026-08-08)**：纯 title 指纹会让"AMD 收购 Taalas"（HN 标题含英文名）与"AMD 收购将权重直接刻在芯片上的 AI 初创公司"（Solidot 标题用中文，英文名只在正文）成为两个事件。event_key 需用 `title + summary[:80]` 拼接。另有实体级 key：`taalas→amd_taalas`、`hassabis+ceo/chair→hassabis_deepmind`、`meta+fined/567/child→meta_fined`。
- **同分事件展示选有日期版本 (2026-08-08)**：去重组内排序 `(bool(pub_date), hot_score)` reverse，避免 HN 无日期条目压过有日期的中文源版本。重要事件可能因同分+日期序被 TOP5 截断（Hassabis 卸任 vs Meta Muse Code 同 15 分），需对重点事件（如 hassabis 人事变动）做保底插入。
- **体育源必须 feed 级过滤（2026-08-05）**：NOISE_PATTERNS 只匹配 title+summary+tags，但体育文章的 feed 名（BBC Sport Football / World Soccer Talk / The Guardian Football）不在这些字段中，导致大量足球文章（含 hot_score 11-19）混入科技/AI（标题含 "AI"、mailbag 等）。修复：主循环先判 `re.compile(r'football|soccer|sport', re.I).search(feed_name)` 或 `category=='足球'` 直接排除，再补标题级词（champions league/ronaldo/fifa/transfer gossip/mailbag/al-nassr）。
- **HTML 注释残留导致关键词误匹配（2026-08-05）**：朝鲜日报中文等源 summary 含未闭合 `<!--` 注释包住 `<audio ...>` 标签，`re.sub(r'<[^>]+>','')` 清不掉注释内标签，残留 "audio" 文本命中产业关键词 "audi"（奥迪）→ 军事新闻误入产业/公司。修复：clean() 先删注释 `re.sub(r'<!--.*?-->',' ',t,flags=re.DOTALL)` 再删标签。
- **英文关键词必须词边界匹配（2026-08-05）**：`kw in text` 简单包含匹配会让 'audi' 命中 'audio'、'pe' 命中 'people'。修复：纯 ASCII 关键词用 `re.compile(r'\b'+re.escape(kw)+r'\b')`，含中文关键词保持包含匹配。
- **48h 窗口文章超 2000 条时 SQL LIMIT 会截断**：2026-08-05 实测 48h 共 2094 条，LIMIT 2000 少算 94 条。底部统计应 `SELECT COUNT(*)` 全量，分类查询 LIMIT 2500+。
- **`hot_score` 已修复** (2026-07-03)：评分系统现为三层（Feed权重+关键词+多源覆盖），`ORDER BY hot_score DESC` 正常工作
- **词边界匹配**：中文关键词使用 `\b` regex 可能不完美（CJK 字符间无标准词边界）。英文关键词匹配准确
- CLI JSON 输出可能被截断，始终用 SQLite 直查
- 部分标题/摘要含 HTML 标签需用 `re.sub(r'<[^>]+>', '', text)` 清理
- Hacker News 文章摘要含 "Article URL:" 和 "Comments URL:" 后缀，需 `re.split` 截断
- **机器人/芯片主题文章量少**: 24小时内通常只有 2-15 条，不足10条时需如实说明
- **白宫安全事件是高频噪声源**: 涉及白宫/特朗普/枪击/安保/晚宴的报道量极大，必须严格过滤
- **通用新闻误入科技/AI**：无关键词匹配的通用新闻（交通/天气/娱乐/基建）可能被误分。需持续扩充 NOISE_PATTERNS。
- **阿拉伯语内容**：半岛电视台等源可能输出阿拉伯语文章，标题/摘要包含 `العربية`、`الجزيرة` 等，需过滤。
- **BBC 中文 summary byline 结构（2026-08-16）**：summary 常为 `图像来源，<credit> <导语> Article Information Author, <名> Role, <角色>` 或 `图像来源，<credit> <导语> Published X 分钟前 阅读时间: N 分钟`；且 summary 截断 500 字符时可能只剩 byline 无正文。clean_summary 顺序：先 cut 到 `Article Information` → strip `图像来源，`+拉丁 credit（`^[A-Za-z][A-Za-z\s/&.\-]*?(?=\s*[0-9\u4e00-\u9fff])`）→ strip `Published ... 阅读时间: ...`；结果无中英文数字内容则置空。
- **category 字段加权只信 财经/投资/ai（2026-08-16）**：`科技`（HN/虎嗅/Engadget/Ars）与 `综合` 标签过粗，加权会让无关键词文章误分（HN 气候/法院新闻进科技/AI）。评分仅 `财经/投资→财经/投资 +3`、`ai→科技/AI +3`。
- **arXiv 论文 feed 级过滤（2026-08-16）**：`arXiv 量化金融` 是论文非新闻，仅 feed_name 含 arxiv、标题不含，须 `FEED_NOISE_RE = re.compile(r'arxiv')` feed 级排除。
- **迁移/地方选举噪声（2026-08-16）**：Ceuta 移民潮（因 government 关键词）误入宏观政策、Nigel Farage 补选。NOISE 补 `ceuta/migrant/asylum/偷渡/难民/farage/by-election/clacton`。
- **多源合并 [N源] 用唯一 feed 计数（2026-08-16）**：event_dedup 按 event_key 分组后 `src_count` 取 `len(去重 feed_name)`，非 `len(组内文章数)`（BBC 中文同文被拉两次会使源数虚高）。实体级 key 需补 `数十国|dozens of countries → trump_tariff_china`。
- **Unitree 上市暴涨多源合并（2026-08-20）**：宇树 IPO 首日暴涨 600%，CoinDesk/BBC Business 英文标题与 IT之家/华尔街见闻/纽约时报中文中文标题前 40 字符不同，纯标题指纹不合并（8 源分散）。修复：entity_key 加 `unitree|宇树 → unitree_ipo`（高优先级放最前）。
- **IT之家 summary 前缀（2026-08-20）**：IT之家 summary 以 `之家 8 月 N 日消息，` 开头（标题前缀也出现在摘要），占摘要 50 字窗口 10 字。clean_summary 补 `re.sub(r'^之家\s*\d+\s*月\s*\d+\s*日\s*消息[，,]?', '', s)`。
- **IT之家 summary 前缀实为带 "IT"（2026-08-21 修正）**：实测原始为 `<p>IT之家 8 月 20 日消息，…`（clean_html 后 `IT之家` 开头），2026-08-20 记录的 `^之家` 不匹配。修复：`re.sub(r'^IT?之家\s*\d+\s*月\s*\d+\s*日\s*消息[，,]?', '', s)`。
- **HN summary 是 href 链接形式（2026-08-21）**：HN 摘要原始为 `<a href="...">Comments on Hacker News</a> | <a href="...">blog...`，clean_html 后残留 `Comments on Hacker News | https://...`，旧 `Article URL:/Comments URL:` 文本正则不匹配。修复：`re.split(r'Comments on Hacker News|Article URL:|Comments URL:', s)[0]`，剩余无正文则置空显示 (无摘要)。
- **必须先跨主题事件分组再分类（2026-08-21 流程修正）**：Unitree IPO 8+ 源（CoinDesk 12分/卫报 9分/BBC Business 6分/IT之家…）先分类后去重会分散到 科技/财经 多个分类各占 TOP 位、[N源] 失效（英伟达CPO 虎嗅vs华尔街见闻同理）。修复流程：全量分组（entity_key 强规则优先，否则 norm(title)[:40]）→ 每组选 hot 最高代表（nsrc=唯一 feed 数，`len(set(feed_name))`）→ 分类 → 主题内 title+summary[:80] 二次去重。**entity_key 只放强实体规则**（unitree IPO 需带 ipo/上市/首日/debut/surge/打新 上下文、taalas、hassabis、meta fined、trump vaccine、astra、数十国、伊朗外交、google-anthropic、超聚变、prime air|drone deliver、alexa free/fire tv）；**泛公司名规则（nvidia/intel/tesla 裸词）禁止**——会把同公司不同事件合并成一条。
- **标点归一化必须含 `！!？?` 与括号（2026-08-21）**：虎嗅"必须拿下CPO"与华尔街见闻"必须拿下CPO！"仅差感叹号，旧正则 `[，,、；;：:。.·\s]+` 不覆盖 → 同事件不合并。修复：norm 补 `！!？?"'（）()[]【】`。
- **HTML 实体残留（2026-08-21）**：华尔街见闻 summary 含 `&nbsp;Moderna…`，clean_html 需补 `re.sub(r'&nbsp;|&amp;|&lt;|&gt;|&quot;|&#\d+;',' ',t)`。
- **科技/AI 表补网络安全词（2026-08-21）**：TechCrunch 网络安全新闻 "fake crypto conference lure"（黑客诱饵）因科技表无 hacker/security 词，只命中财经 crypto → 误入财经/投资 TOP。科技表补 `cpo/共封装光学/海力士/hacker/黑客/漏洞/vulnerability/零日/后门` 等。
- **trade deal 类贸易新闻被 category 加权抢走（2026-08-21）**：BBC Business "Canada and US finalising a trade deal" category='财经' +3 压过宏观政策关键词分 → 美加贸易协议进财经/投资。修复：特殊规则 `trade deal|trade talks|trade agreement|贸易协议|贸易协定 → 宏观政策 +3`，宏观表补 `加拿大/canada/墨西哥/mexico`。
- **完整可复用脚本（2026-08-21）**：`scripts/daily_briefing.py` 整合以上全部修复 + NOISE_PATTERNS 全量 + 四类关键词表 + 跨主题分组 + TOP5 输出，cron 可直接运行 `python3.11 ~/.hermes/skills/wuhoo-rss-briefing/scripts/daily_briefing.py`（注意 cron 环境用裸命令名 python3.11，禁止绝对路径）。
- **HN 个人技术事故误入宏观政策（2026-08-23）**：HN "I accidentally logged hundreds of thousands of phone calls to military bases"（个人隐私/技术博客，非军事新闻）因标题含 military 命中宏观政策关键词表 TOP5。修复：NOISE_PATTERNS 补 `phone calls to military bases`、`accidentally logged`（HN 风格"意外记录"标题标记）。
- **Stratechery 源被 Cloudflare 反爬拦截（2026-08-23）**：`stratechery.com/feed/` 返回 403 + "Checking your browser..." JS 挑战页，feedparser 报 `junk after document element`。非临时故障，需浏览器 JS 执行才能绕过，暂不处理（低优先级源）。
- **Shein IPO 跨分类不合并（2026-08-25）**：卫报英文 "Fast-fashion giant Shein sets cut-price $27bn valuation for Hong Kong IPO" 进财经/投资，中央社繁体+IT之家简体版进产业/公司，8 源分散（同 Unitree 案例）。修复：ENTITY_KEYS 加 `(shein|希音).*(ipo|上市|首日|debut|surge|打新|发售)|(ipo|上市|首日|debut|打新|发售).*(shein|希音) → shein_ipo`。
- **主题内排序未按文档实现（2026-08-25）**：脚本 line 346 只按 `hot_score` 排序，无日期 HN 条目（GPT 5.6 降价/Munder Difflin）挤占科技/AI TOP5；skill 文档要求 `(bool(pub_date), hot_score)`。修复：`sorted(..., key=lambda x: (x['hot_score'], bool(x['pub_date'])), reverse=True)` 与 pick_representative 一致。
- **HN MartyPC 误入产业/公司（2026-08-25）**："MartyPC is a cross-platform emulator of early PCs written in Rust"（HN 复古模拟器项目展示）占产业/公司 TOP5 第 2 位。NOISE_PATTERNS 补 `marty|marty pc`。
- **沃什杰克逊霍尔事件必须实体级合并（2026-08-31）**：美联储新主席沃什 8/28 Jackson Hole 首秀放鹰（9月加息预期、黄金重挫3%、比特币跌破8万），39 条报道分散（华尔街见闻多角度 8 条 + FT/NYT/BBC/CoinDesk/虎嗅/格隆汇/第一财经/RFI/Seeking Alpha），无 entity_key 时财经 TOP5 被同一事件占 4 条。修复：ENTITY_KEYS 加 `(warsh|沃什).*(jackson hole|杰克逊霍尔)` 双向 → warsh_jackson_hole（合并后 [7源]）。同批加 iceland_eu（冰岛欧盟公投 HN+德国之声）与 anthropic_ruling（Anthropic 黑名单裁决 HN+BBC Business）两条规则；已同步 scripts/daily_briefing.py。
- **BBC 中文摘要日期变体（2026-08-31）**：日期在 `<time datetime="2026-08-26">` 标签内，clean_html 后为 `Published 2026年8月26日阅读时间: 3 分钟`，旧 `Published\s+...阅读时间` 正则依赖 "Published X 分钟前" 结构不匹配；且拉丁 credit 正则先删 "Published " 后字符串以**空格开头**，新正则须 `^\s*\d{4}年...` 容错前导空白。
- **街头采访/HN 泛评论/DW 特稿挤占 TOP（2026-08-31）**：BBC Business "What do you spend too much on?"（伦敦街头采访，同类 money disagre/asking couples）、HN "It works better in the app"（app vs web 泛评论）、德国之声 "DW users on life in Russia"（栏目特稿）分别挤占财经/科技/宏观 TOP5。NOISE_PATTERNS 补 `spend too much on|central london shoppers`、`works better in the app`、`dw users on life`。
- **NOISE_PATTERNS 模式必须全小写（2026-09-01）**：`is_noise` 先 `text.lower()` 再 `re.search(p, tl)`，含大写的模式（如 `IT早报`）对已小写文本静默失效（re 默认大小写敏感），导致过滤不生效。新增模式一律全小写（中文不受影响，仅拉丁字母注意）。已同步 scripts/daily_briefing.py。
- **IT早报 日更聚合栏目（2026-09-01）**：IT之家"IT早报 0830"标题聚合 5+ 条资讯（长鑫LPDDR6/小米折叠/华为三折叠…），hot_score 高（多关键词命中）挤占产业/公司 TOP5，非单一新闻事件。NOISE_PATTERNS 补 `it早报`（同类早餐FM/fm-radio）。已同步 scripts/daily_briefing.py。
- **summary 尾部未闭合标签片段（2026-08-25）**：IT之家 summary 残留 `<spa`（`<[^>]+>` 因无 `>` 匹配不掉）。clean_html 补 `re.sub(r'</?[A-Za-z][^>]*$', '', t)`。

## 版本

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.10 | 2026-08-31 | ENTITY_KEYS 加 warsh_jackson_hole（沃什杰克逊霍尔首秀放鹰 39 条报道未合并占满财经 TOP5）/iceland_eu（冰岛欧盟公投）/anthropic_ruling（Anthropic 黑名单裁决）；NOISE 补 spend too much on/works better in the app/dw users on life；BBC 中文摘要日期变体 `^\s*\d{4}年...阅读时间` 前缀清理（前导空格容错）；同步 scripts/daily_briefing.py |
| 1.9 | 2026-08-29 | 知乎日报 feed 级过滤（FEED_NOISE_RE 加知乎日报，科普文章"概率的本质"无日期误入财经 TOP5）；NOISE 补 gta/grand theft auto（GTA6 预告/泄露娱乐内容误入产业/公司 TOP5）；同步 scripts/daily_briefing.py |
| 1.8 | 2026-08-28 | NOISE 补 back to school/uniform costs（BBC Business 返校消费软文误入财经 TOP5）；同步 scripts/daily_briefing.py |
| 1.7 | 2026-08-27 | NOISE 补 哈利和梅根/meghan（王室名人误入宏观政策）、早餐FM/FM-Radio（见闻自营晨报）、plug-in solar/10p coin（BBC Business 消费软文误入财经）；同步 scripts/daily_briefing.py |
| 1.6 | 2026-08-25 | shein_ipo 实体 key（8源合并）；主题内排序改 (hot_score, bool(pub_date))；NOISE 补 marty；clean_html 补尾部未闭合标签清理 |
| 1.5 | 2026-08-21 | 流程修正：跨主题事件分组先于分类（entity_key 强规则+标题指纹），泛公司名禁止入 entity_key；norm 标点归一化补感叹号/括号；IT之家前缀修正 `^IT?之家`；HN href 形式摘要 split；&nbsp; 实体清理；科技表补 cpo/hacker/零日，宏观表补 trade deal 规则；新增可复用脚本 scripts/daily_briefing.py |
| 1.4 | 2026-07-03 | 适配 wuhoo-news-rss v2.0：更新排序策略（ORDER BY hot_score DESC），移除 hot_score=0 误报，更新 Step 1 SQL 过滤 hot_score>0 |
| 1.3 | 2026-06-12 | 新增噪声模式：虎嗅生活方式、皇家讣告、自然灾害、促销内容、网信办公告、体育源全量
