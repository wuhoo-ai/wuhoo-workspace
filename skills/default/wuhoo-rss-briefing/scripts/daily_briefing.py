#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""Wuhoo RSS 简报生成 v2 — 跨主题事件分组 → 分类 → 主题内去重"""
import sqlite3, re
from collections import defaultdict
from datetime import datetime, timedelta

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
    t = re.sub(r'\s*-\s*RFI\s*-\s*法国国际广播电台\s*$', '', t).strip()  # 2026-09-10: RFI 标题尾部来源后缀与来源名重复
    return t

def _is_caption_phrase(pre):
    """2026-09-20: 判断 "节目全长" 之前的片段是否为视频说明文字 (而非正文)。

    说明文字特征: 单句短语、无句末标点 (句末标点只允许出现在末尾, 如问句标题
    "How much can Canada fight back…US?"), 且长度 ≤ 140 字。正文中的 "节目全长约 40 分钟"
    等用法不含 "N,NN HH:MM" 时长格式, 不会走到这里。
    """
    p = re.sub(r'^(?:你的器材不支持播放多媒体材料|Play video,?|Watch:)', ' ', pre).strip(' \t\r\n,，、;；:：\'"“”')
    if not p or len(p) > 140:
        return False
    body = p[:-1] if p[-1] in '。！!？?' else p
    return not re.search(r'[。！!？?]|\.\s|[?!]\s', body)


def clean_summary(s, feed_name=''):
    s = clean_html(s).strip()
    # HN: 评论链接形式
    s = re.split(r'Comments on Hacker News|Article URL:|Comments URL:', s)[0]
    s = re.sub(r'^你的器材不支持播放多媒体材料\s*Play video,?\s*', '', s)
    # 2026-09-13: BBC 视频说明文字 — "Watch: <caption> , 节目全长 N,NN HH:MM" 占满 50 字摘要窗口
    # (实测: 特朗普5000美元 BBC版 hot19 / 印尼火山 / 关税加拿大 / 西藏泥石流).
    # 2026-09-20 改锚点式: 旧写法 `^.{0,90}?节目全长...` 无差别从行首吞到时长处 — 若说明文字前有正文则正文一并丢失;
    # 现仅从 "你的器材不支持播放多媒体材料 / Play video / Watch:" 标记起删除, 且时长可缺失 (DB 中部分摘要截断在 "节目全长 2,00")。
    # 摘要若因此为空: 优先由同事件其他源正文回填, 仍无则用 video_caption() 兜底
    s = re.sub(r'(?:你的器材不支持播放多媒体材料|Play video,?|Watch:).{0,150}?节目全长\s*\d+,\d+\s*(?:\d{1,2}:\d{2})?\s*',
               ' ', s, flags=re.DOTALL)
    # 2026-09-20: 整条摘要就是一条视频说明 (caption + "节目全长 N,NN HH:MM", 前后无正文) → 返回空,
    # 交由主流程先做组内其他源正文回填 (2026-09-13 意图), 组内也无正文时才用 video_caption() 兜底。
    # 判定要点: 必须有 "节目全长 N,NN 时长" 格式 (正文里的 "节目全长约 40 分钟" 不触发) + 前置短语无句末标点。
    m_v = re.search(r'^(.*?)\s*节目全长\s*\d+,\d+\s*(?:\d{1,2}:\d{2})?\s*$', s, flags=re.DOTALL)
    if m_v and _is_caption_phrase(m_v.group(1)):
        return ''
    s = re.sub(r'^IT?之家\s*\d+\s*月\s*\d+\s*日\s*消息[，,]?', '', s)
    # BBC 中文 byline 结构 (仅该源)
    if 'bbc 中文' in feed_name.lower():
        s = re.split(r'Article Information', s)[0]
        s = re.sub(r'^图像来源[，,、\s]*', '', s)
        s = re.sub(r'^[A-Za-z][A-Za-z\s/&.\-]*?(?=\s*[0-9\u4e00-\u9fff])', '', s)
        s = re.sub(r'Published\s+.*?阅读时间:?\s*[\d\s]*分钟?', '', s, flags=re.I)
        s = re.sub(r'^\s*\d{4}年\d{1,2}月\d{1,2}日\s*阅读时间:?\s*[\d\s]*分钟?', '', s)  # 中文日期变体, 前导空格容错 (2026-08-31)
        if re.fullmatch(r'[A-Za-z\s/&.\-]{1,50}', s):
            s = ''  # 纯拉丁 byline/credit 残留 (如 "Getty Images"), 无正文 (2026-09-02)
    s = s.split('|')[0].strip()
    s = re.sub(r'\s+', ' ', s).strip()
    # 2026-09-10: 通用前缀清理 — NYT中文 "KALLEY HUANG2026年9月10日周三，..." 署名+前导日期 (iPhone Duo 代表回填实测);
    # RFI "09/09/2026 - 20:54 ..." 时间戳 (巴黎空间峰会条目实测)
    s = re.sub(r'^[A-Z][A-Za-z.\-\s,，]{1,40}(?=\d{4}年\d{1,2}月)', '', s)  # 2026-09-18: 补逗号 — 多作者署名 "MATINA STEVIS-GRIDNEFF, JEANNA SMIALEK2026年…" (canada_eu_associate 代表实测)
    s = re.sub(r'^\d{4}年\d{1,2}月\d{1,2}日(周|星期)?[一二三四五六日]?[，,\s]*', '', s)
    s = re.sub(r'^\d{2}/\d{2}/\d{4}\s*-\s*\d{1,2}:\d{2}\s*', '', s)
    # 2026-09-14: 中央社 byline 前缀 — "（中央社舊金山11日綜合外電報導）…" 吃满 50 字摘要窗口 (RubyGems 合并回填实测)
    s = re.sub(r'^（中央社[^）]{0,60}?）\s*', '', s)
    if not re.search(r'[\u4e00-\u9fffA-Za-z0-9]', s):
        return ''
    return s[:50]

def video_caption(raw):
    """2026-09-20: BBC 视频条目说明文字 — 当摘要其余内容被剥离干净时, 主流程用它兜底 (否则显示 (无摘要))。

    实测 BBC 中文视频条目 summary 整体 = "你的器材不支持播放多媒体材料 Play video, <caption> , 节目全长 N,NN HH:MM",
    clean_summary 剥离后为空; 组内若无其他源正文可回填, 展示为 (无摘要)。仅作兜底, 不参与正常摘要路径,
    以免说明文字顶掉同事件中文源的正文回填 (2026-09-13 的原始意图)。
    """
    s = clean_html(raw).strip()
    m = VIDEO_CAP_RE.search(s)
    if not m:
        return ''
    cap = re.sub(r'你的器材不支持播放多媒体材料|Play video,?|Watch:|图像来源[^\s]*?[,，、]\s*', ' ', m.group(1))
    cap = re.sub(r'[\u201c\u201d"\']', '', cap)
    cap = re.sub(r'\s+', ' ', cap).strip(' ,，、:：')
    if len(re.sub(r'[^A-Za-z0-9\u4e00-\u9fff]', '', cap)) < 5:
        return ''
    return cap[:50]

VIDEO_CAP_RE = re.compile(r'^(.*?)节目全长\s*\d+,\d+\s*(?:\d{1,2}:\d{2})?', re.DOTALL)

# ── Feed 级过滤 ───────────────────────────────────────
FEED_NOISE_RE = re.compile(r'arxiv|知乎日报', re.I)
SPORT_FEED_RE = re.compile(r'football|soccer|sport', re.I)
# 2026-09-19: 扩 transcript/discusses/analyst-investor day — 实测 'Vicinity Centres … Discusses Capability Showcase … Transcript'(hot11)
# 与 'AeroVironment … Analyst/Investor Day Transcript'(hot11) 漏过旧规则占财经/投资 TOP5
SA_LOW_RE = re.compile(r'q[12]\s*20\d\d|commentary|portfolio update|earnings call|presents at|slideshow|m&a call|\btranscript\b|discusses|analyst/investor day', re.I)  # 2026-09-11: 会议 slideshow/transcript 自动材料 (hot19 挤占财经 TOP2)
ENGADGET_GUIDE_RE = re.compile(r'^(how to|considering)\b', re.I)  # 2026-09-13: Engadget How-to 指南 (非新闻事件; 实测占产业/公司 TOP4); 2026-09-16 扩 considering ("Considering a Level 2 EV charger?…" 导购 hot6)

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
    # 2026-09-17 新增 — 虎嗅个人专栏 (同类 朱思码记; "战魔田默｜…全球定价权" 占产业/公司 TOP5, 非新闻事件)
    '战魔田默',
    # 2026-09-17 新增 — 游戏皮肤/预购争议 (同类 gta/深海迷航; "《暗黑破坏神 4》杰洛特皮肤引争议" 占产业/公司 TOP5)
    '暗黑破坏神', '杰洛特', '游戏皮肤',
    # 2026-09-17 续 — 游戏联动/皮肤公告 (同类; "《Apex 英雄》游戏官宣联动《街头霸王》" 递补占 TOP5,
    # 泛化规则: 游戏+联动/皮肤 组合; apex 需限定 '英雄' 防误伤公司名 Apex)
    '游戏.*(联动|皮肤)', '(联动|皮肤).*游戏', r'apex\s*英雄', '街头霸王',
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
    'man united', 'man utd', 'chelsea', 'liverpool fc', 'transfer news', r'\bnba\b', r'\bnfl\b',
    # 2026-09-06: 体育缩写必须词边界! 裸词 'nfl' 子串命中 "co[nfl]ict" → 所有含 conflict 的战争/宏观英文报道被误滤
    # (BBC Business 柴油价历史新高 hot=22 死于 "the Iran conflict"; 同批 nba 一并加边界)
    'adult film producer', 'torrent pirate',  # HN 成人/盗版八卦混入科技/AI TOP5 (2026-09-07)
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
    # 2026-09-02 新增 — BBC Business 家庭金钱软内容 / 消费省钱软文误入财经 TOP (同类: money disagre/plug-in solar)
    'lend me £10k', 'financial favourit', 'cheaper meals out', 'soft launches and late sittings',
    # 2026-09-02 新增 — IT之家消费电子发售挤占产业/公司 TOP (同类: vgn鼠标/外设; 米家冰箱/制冰机/漫步者音箱/HKC手柄)
    '米家.*(首销|发售|开售|预售|众筹)', '漫步者.*(首销|发售|开售|预售)', '猎弦', '绝梦',
    'ankidroid',                                      # HN 小众 App 捐赠链接政策变动 (低信号, 非新闻事件)
    # 2026-09-18 新增 — HN 开源项目/编程语言展示帖 (同类: marty/ankidroid/run any company autonomously;
    # "Bend – A language that blocks AI mistakes via proof" 占科技/AI TOP3、"Neovim have a ~$800k Bitcoin
    # donation sitting untouched since 2023" 占财经 TOP5, 均为社区话题非新闻事件)
    'blocks ai mistakes', 'neovim',
    # 2026-09-18 新增 — IT之家手机供应链软文 (京东方为努比亚新机型"独供"屏幕, 营销稿非独立事件, 同类 消费电子发售系列)
    '京东方.*(独供|供货)',
    'refund when using your credit card',             # BBC Business 信用卡退款科普 (category=财经 加权误入财经 TOP)
    'fortrea',                                        # Seeking Alpha 单股分析 (Fortrea Holdings 中盘CRO, 低信号)
    # 2026-09-05 新增 — 少数派"派早报"日更聚合栏目 (同类: IT早报/早餐FM/fm-radio, 每日多资讯打包非单一事件)
    '派早报',
    # 2026-09-09 新增 — IT之家消费电子发售挤占产业/公司 TOP (同类: 米家/漫步者/vgn; 实测 09-08 爱国者机箱首销/技嘉显示器上架/利民散热器首发价 占 TOP3-5)
    '爱国者.*(首销|开售|发售|上架|预售)', '技嘉.*(上架|首销|开售|发售|预售|显示器)',
    '利民.*(散热器|首发价|首销|上架)', '星璨岚',
    # 2026-09-10 新增 — IT之家消费电子发售续 (同类: 米家/漫步者/爱国者/技嘉/利民; 实测 09-08 九州风神散热器占产业/公司 TOP)
    '九州风神.*(散热器|散热|首销|开售|上架|发售|风扇|机箱|水冷)',
    # 2026-09-10 新增 — BBC Future 特稿 (机器人索要小费趋势文, 非新闻事件; 同类: dw users on life/月经周期)
    '索要小费',
    # 2026-09-10 新增 — BBC Business 个人理财软文 (同类: money disagre/lend me £10k/back to school; 实测 09-08 财经 TOP10 第6位)
    'written my will',
    # 2026-09-12 新增 — HN 引用列表/wiki 帖 (非新闻事件; 实测 "List of references on Sony websites…" hot11 占产业/公司 TOP1, 同类 ankidroid/marty)
    'list of references on',
    # 2026-09-12 新增 — BBC Business 个人理财软文续 (同类: written my will/money disagre; 实测 "I asked my husband to pay into my pension…" hot11)
    'pay into my pension',
    # 2026-09-13 新增 — The Verge 导购/促销 commerce 帖 (同类: lowest price/10p coin; "Where to preorder…" 导购 与 "over half off" 促销 非新闻事件)
    'where to preorder', 'half off',
    # 2026-09-13 新增 — IT之家消费电子发售续二 (同类: 米家/漫步者/爱国者/技嘉/利民/九州风神; 实测 机械革命笔记本上架 hot6 占产业/公司 TOP2、努比亚散热器开售 hot3 占 TOP5)
    '机械革命.*(上架|开售|首销|发售|预售)', '努比亚.*(散热器|开售|首销|上架|发售)',
    # 2026-09-15 新增 — The Verge 促销导购 commerce 续 (同类: where to preorder/half off/lowest price; 实测 "The best deals from Nintendo's…sale" hot9 占产业/公司 TOP1)
    'best deals',
    # 2026-09-15 新增 — IT之家消费电子促销 (实测 "小米 15 Ultra 国补直降" hot6 占产业/公司 TOP5; 同类 米家/漫步者/爱国者发售)
    '直降',
    # 2026-09-15 新增 — 个人博客/评论帖非新闻事件 (同类: apple is getting this wrong/works better in the app;
    # "I'm being cyberattacked by Tesla, Inc"(个人纠纷 blog) 与 "Why is Google still serving dodgy ads?"(评论帖) 各占科技/AI 14分档）
    'cyberattacked by tesla', 'dodgy ads',
    # 2026-09-15 新增 — HN 产品展示帖 (同类: marty 复古模拟器/ankidroid; "Pion, an agent designed to run any company autonomously" 占科技/AI 14分档)
    'run any company autonomously',
    # 2026-09-15 新增 — BBC 软内容: 健康研究/学生防盗指南/搬家补贴个人故事 (同类: 月经周期/back to school/plug-in solar;
    # 实测 "滚烫饮品可增加患癌风险" hot11 占科技/AI 候选、"How to protect your laptop…"/"I got paid $5,000 to move…" 占财经 11 分档)
    '滚烫饮品', 'protect your laptop', 'got paid .{0,12}to move',
    # 2026-09-16 新增 — Engadget 促销帖 (同类: best deals/where to preorder/half off; "Amazon's Prime Big Deal Days sale returns in October" hot6 占产业/公司候选)
    'big deal days',
    # 2026-09-16 新增 — IT之家消费电子发售续三 (同类: 米家/漫步者/机械革命/努比亚; 实测 "影石 Mic Pro 腾讯会议版…发布" hot6 占产业/公司候选)
    '影石.*(发布|开售|首销|上架|首发|众筹)',
    # 2026-09-19 新增 — HN 开发工具细枝末节帖 (非新闻事件, 同类 ankidroid/neovim/派早报;
    # 实测 'Claude Code now reads AGENTS.md if there is no Claude.md' HN hot14 占科技/AI TOP3)
    'agents\\.md',
    # 2026-09-19 新增 — BBC Business 街头采访软内容 (同类 money disagre/central london shoppers/spend too much on;
    # 实测 \"'I would tip up to 30% at a restaurant'\" hot11 进财经/投资候选)
    'tip up to',
    # 2026-09-20 新增 — IT之家消费电子发售续四 (同类 米家/漫步者/爱国者/技嘉/利民/九州风神/机械革命/努比亚/影石;
    # 实测 达尔优 A5 游戏耳机发布 hot6 占产业/公司 TOP4、尼康 Z5IIC 新机预告 hot3、京东 iPhone 18 Pro 开售签收稿 hot12 占科技/AI TOP5)
    '达尔优.*(发布|开售|首销|预售|上架|发售)',
    # 尼康规则限定产品词 (防误伤 "尼康发布财报" 类公司新闻)
    r'尼康.*(Z\d|相机|镜头|无反|微单).*(发布|开售|首销|预售|上架|发售)|尼康.*(发布|开售|首销|预售|上架|发售).*(相机|镜头|Z\d)',
    '京东.*(开售|首销|预售|开卖|签收新机)',
    # 2026-09-20 新增 — HN 一次性博客演示帖 (非新闻事件; 同类 marty/neovim/ankidroid/blocks ai mistakes;
    # 实测 'GPT-6 Astra Solves a WWI German Radio Cipher' hot14 占科技/AI TOP2 且无摘要)
    'radio cipher',
    # 2026-09-20 新增 — 文化/地方治安软内容 (实测 德国之声 'Aztec manuscript loaned back to Mexico after two centuries'
    # hot11 因 'mexico' 命中宏观政策表占宏观 TOP3; 卫报墨尔本烟草店纵火案为地方治安)
    'aztec', 'manuscript loaned',
    'tobacconist', 'firebomb',
    # 2026-09-20 新增 — Engadget 消费评论软文 (非新闻事件; 'Why buy a streaming device when you have a smart TV?')
    'why buy a streaming device',
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
        '伊朗战争','美伊','油价','石油','oil price','diesel','柴油','能源价格','霍尔木兹','燃料价格','fuel price',
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
    if re.search(r'trade deal|trade talks|trade agreement|贸易协议|贸易协定|trade war|贸易战', text, re.I):
        scores['宏观政策'] += 3
    # 2026-09-19: AI 风险/超级智能话题 → 科技/AI (BBC Business "Uncontrolled AI could lead to 'silicon species' rivalling humans"
    # 因 category=财经 +3 且财经关键词=0 被误分为财经/投资 TOP1; hot17)
    if re.search(r'silicon species|superintelligence|超级智能|超級智能|\bagi\b', text, re.I):
        scores['科技/AI'] += 3
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
    # 2026-09-09: 收紧 openai_astra — 原裸 'astra' 把任何提到 GPT-6 Astra (OpenAI 现役旗舰模型名) 的文章全并成 openai_astra 事件
    # (实测 09-08: robot 臂演示 HN20 + 算力暴涨市场文 华尔街见闻15 + 按效果收费定价文 华尔街见闻6 三篇无关文章误合并);
    # 语境词须双向 (真实标题 "pause some work on AI model Astra" 语境词在前)
    (re.compile(r'astra.*(cyber|secur|pause|delay|postpone|safet|推迟|延迟|安全|评估|暂停|搁置|审查)|(cyber|secur|pause|delay|postpone|safet|推迟|延迟|安全|评估|暂停|搁置|审查).*astra|cyber capabilit', re.I), 'openai_astra'),
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
    # 2026-09-02: Claude Fable 5.1 / Mythos 5.1 发布 (Anthropic 重大发布, HN+IT之家+Verge+TechCrunch+华尔街见闻 5源)
    (re.compile(r'(fable|mythos).*(anthropic|claude)|(anthropic|claude).*(fable|mythos)', re.I), 'claude_fable_51'),
    # 2026-09-02: 苹果 CEO 换任 库克→特努斯 (告别信/首份备忘录/身价, 8条报道, 实体级强规则避免被 TOP5 截断)
    (re.compile(r'(ternus|特努斯)|(tim cook|库克).*(final message|parting|告别|farewell|executive chair|最后一天)', re.I), 'apple_ceo_transition'),
    # 2026-09-02: 苹果提前发布 2026 款 Mac mini/Studio (AI 需求激增, IT之家+HN 同事件; IT之家标题为 "mini / Studio")
    (re.compile(r'(mac mini|mac studio|mini\s*/\s*studio)', re.I), 'apple_mac_ai_demand'),
    # 2026-09-02: FTC 起诉亚马逊广告乱收费 (TechCrunch+Verge+Engadget+Ars 4源同事件)
    (re.compile(r'(ftc.*amazon|amazon.*ftc).*(advert|surcharg|overcharg|rigging)', re.I), 'ftc_amazon_surcharge'),
    # 2026-09-03: Google 发布 Gemini 3.8 Flash/Flash Cyber (DeepMind 官方+HN+IT之家×2+Verge+Ars+华尔街见闻×2+第一财经 9行8源; 此前 HN 英文标题与中文源不合并拆占 TOP5 两条)
    (re.compile(r'gemini\s*3\.?\s*8', re.I), 'gemini_38_flash'),
    # 2026-09-05: ChatGPT/Claude/Grok/Gemini 四大 AI 服务同时宕机 (09-04 事件, Solidot+Ars Tech+HN 4源, 此前 Solidot 新闻版与 HN Ask 版拆占科技/AI TOP5 两条)
    (re.compile(r'(openai|chatgpt|claude|grok|gemini).*(simultaneously|同时|downtime|outage|宕机|下线|故障)|(simultaneously|同时|downtime|outage|宕机|下线|故障).*(openai|chatgpt|claude|grok|gemini)', re.I), 'ai_service_outage'),
    # 2026-09-06: 美伊战争推高美国柴油价至历史新高 (BBC hot22/NYT/FT/美联社 6源同事件, 此前关键词表无油价词全部落未匹配 640 条)
    (re.compile(r'diesel.*(record|all[- ]?time|new high|新高|纪录)|(record|all[- ]?time|new high|新高|纪录).*diesel', re.I), 'diesel_record'),
    # 2026-09-09: 德国 AfD 萨安州(萨克森-安哈尔特)选举大胜 (DW×3/FT/BBC World×2/第一财经 7源; 此前 DW 两条不同角度未合并各占宏观 TOP 3-4 位;
    # BBC World 标题以 "eastern state" 指代萨安州)
    (re.compile(r'(afd|德国选择党|极右).*(saxony|萨安|萨克森|eastern state|state election|州选)|(saxony|萨安|萨克森|eastern state|state election|州选).*(afd|极右|选择党)', re.I), 'afd_saxony_election'),
    # 2026-09-09: OpenAI 用 10000 智能体攻克 Navier-Stokes 千禧年大奖难题 (HN 22/OpenAI Blog 19/IT之家 12/Engadget 6/第一财经 3 同事件;
    # 旧规则要求 openai 上下文, HN/OpenAI Blog 官方标题无 "openai" 字样不命中→英文代表落未匹配池;
    # Engadget 标题以 controversy 指代; Buckmaster 学术 PDF 无 prize/millennium/千禧年 语境不合并; 语境词双向)
    (re.compile(r'(navier|stokes|纳维|斯托克斯).*(millennium|prize|千禧年|大奖难题|solved|solution|problem|解决|攻克|controversy|争议)|(millennium|prize|solved|solution|problem|controversy|千禧年|大奖难题).*(navier|stokes|纳维|斯托克斯)|千禧年', re.I), 'openai_navier_stokes'),
    # 2026-09-09: OpenAI ChatGPT Images 2.5 发布 (HN 14/IT之家 6/OpenAI Blog 3/华尔街见闻 3; 标题前缀 Introducing/发布/OpenAI发布 不同不合并)
    (re.compile(r'chatgpt\s*images\s*2\.?5', re.I), 'chatgpt_images_25'),
    # 2026-09-09: Meta 发布首个个人 AI 智能体 Muse (Meta官方/TechCrunch/Verge/Engadget/HN100+/IT之家/华尔街见闻 7源;
    # 中文标题 "智能体Muse" 前是 CJK 字符无 \b 边界需中文语境分支; \bmuse\b 防 Renoir Museum 误并)
    (re.compile(r'\bmuse\b.*(meta|agent)|(meta|agent).*\bmuse\b|(智能体|个人智能).*muse|muse.*(智能体|个人智能)', re.I), 'meta_muse'),
    # 2026-09-10: Apple 秋季发布会首款折叠屏 iPhone Duo (HN×2 hot30/TechCrunch×3/Verge/NYT中文/RFI/中央社×2/Engadget×3/Ars/华尔街见闻热门/B站/第一财经 12+源;
    # HN 裸标题 "iPhone Duo" 与各源指纹不同全不合并; iPhone Duo 为具体产品名 (非泛公司名, 48h 窗口内即该发布事件)
    (re.compile(r'iphone[\s\-]*duo', re.I), 'iphone_duo_launch'),
    # 2026-09-10: 美加贸易战升级 — 美对加酒类/乳制品/摩托车进口禁令 + 加方反制关税 + 特朗普威胁禁 Bombardier
    # (BBC14/卫报6/NYT6/美联社3/DW11 等 8+条标题各异不合并, BBC 版单独占宏观 TOP1 无 [N源];
    #  误并实测: "Bank of Canada"需词边界、卫报 Palestine"Canada...banning"跨句 135 字符误并→距离限 80、
    #  中央社以色列"加拿大...禁止进口...反制措施"→中文分支距离限 80 且去裸 '禁/进口'、
    #  孟晚舟"她在加拿大被捕"+"贸易战"远距离误并→限距修复)
    (re.compile(r'(canad|carney|卡尼).{0,120}(\bimports?\b|\bbans?\b|\btariffs?\b|trade war|retaliat|\bdairy\b|alcohol|motorcycl|bombardier|乳制品|摩托|庞巴迪|关税|贸易战|反制|红酒|葡萄酒|烈酒|啤酒|威士忌|酒类|酒類)|(\bimports?\b|\bbans?\b|\bbanning\b|\btariffs?\b|retaliat|\bdairy\b|alcohol|motorcycl|bombardier).{0,80}canad|(加拿大|卡尼).{0,80}(关税|贸易战|反制|乳制品|摩托|庞巴迪|红酒|葡萄酒|烈酒|啤酒|威士忌|酒类|酒類|酒精)|(关税|贸易战|反制).{0,80}加拿大|bombardier.*(trump|block|jets?|planes?)|(trump|block).*bombardier', re.I), 'us_canada_trade_war'),
    # 2026-09-10: 迈阿密亚马逊货机坠毁事故 (BBC World/BBC Business/美联社×3 共 6 条同事件标题各异不合并; 合并后 [3源])
    (re.compile(r'miami.*(cargo|plane|crash|jet|runway)|(cargo (plane|jet)).*(miami|crash|runway)', re.I), 'miami_amazon_crash'),
    # 2026-09-13: 特朗普"每人5000美元支票"中期选举承诺 (BBC 中文 hot19 + 华尔街见闻 + 格隆汇 + 卫报 同事件标题各异不合并;
    # BBC 版摘要为视频字幕残留 → 合并后 [N源] + 中文摘要回填。防误并: 数字前置禁接数字(115,000-seat 类子串)、后置禁接 亿/billion(5000亿美元关税为不同事件)、须含特朗普/trump 上下文(律师罚 5000 美元不合并);
    # 数字 '5,000' 经 entity 标点归一(逗号→空格)变 '5 000' → 模式写 5[,\s]?000 双格式容错)
    (re.compile(r'(trump|特朗普).{0,60}(?<!\d)(5[,\s]?000|五千)(?!\s*(?:亿|billion|trillion)).{0,15}(美元|支票|红利|发放|发钱|payments?|checks?|payouts?)|(?<!\d)(5[,\s]?000|五千)(?!\s*(?:亿|billion|trillion)).{0,15}(美元|支票|红利|发放|发钱|payments?|checks?|payouts?).{0,60}(trump|特朗普)', re.I), 'trump_5000_check'),
    # 2026-09-14: OpenAI 智能体攻击 RubyGems 事件披露 (HN14/中央社9/Engadget6/Verge6/第一财经3 共5源; 与 Hugging Face 事故同一调查线,
    # 各源标题差异极大: HN 直述 RubyGems / 中央社 "代理再爆失控" / 第一财经 "AI进化速递" / Engadget 以 "before the Hugging Face incident" 指代 /
    # Verge "rogue AI tried to hack another company in May" 标题与 50 字摘要窗口均无 RubyGems 字样 → 需 "another company" 分支;
    # Hugging Face 分支要求攻击语境 (防 HuggingFace Blog 常规内容误并); "another company" 分支要求 hack/attack 动词;
    # 简繁变体双写 (攻击|攻擊 / 承认|承認) — 第一财经简体版实测 "曾攻击RubyGems" 需简体词)
    (re.compile(r'(rubygems|ruby\s*语言包管理器).{0,60}(attack|attacked|hack|hacked|incident|入侵|攻擊|攻击|失控|承认|承認|undisclosed|breach|penetrat)'
                r'|(attack|attacked|hack|hacked|incident|入侵|攻擊|攻击|失控|承认|承認|breach|penetrat|undisclosed).{0,60}(rubygems)'
                r'|hugging\s*face.{0,30}(attack|attacked|hacked|incident|入侵|攻擊|攻击|breach)'
                r'|(attack|attacked|hacked|incident|入侵|攻擊|攻击|breach).{0,60}hugging\s*face'
                r'|(hack|hacked|attack|attacked|breach|入侵|攻擊|攻击).{0,40}another\s+(company|firm)', re.I), 'rubygems_attack'),
    # 2026-09-15: AI 巨头集体呼吁"放缓 AI 发展"辩论 (Amodei 倡议 + 马斯克/奥特曼背书 + 微软自律准则 + 特朗普反对 + 美股AI板块大跌;
    # 15+ 源碎片化: 英文台 slowdown 直述 / 中文源 放缓·刹车·警告 表述; hot 最高仅 12-14, 天然排名被 14+ 分条目挤出 TOP5)
    # 注: ai 锚点用 (?<![a-z])ai(?![a-z]) 而非 \b — CJK 邻接("AI放缓")时 \b 失效 (Python \w 含 CJK, 'I'-'放' 间无边界)
    # 距离限 55: 卫报 "AI-linked stocks slide after tech bosses call for slowdown" 实测距离 48 (40 会漏)
    (re.compile(r'(amodei|阿莫迪|安特罗匹克|anthropic|阿莫戴).{0,60}(slow ?down|slowdown|slow(?!\w)|放缓|放慢|减速|刹车|警告|warn)'
                r'|(slow ?down|slowdown|放缓|放慢|减速|刹车).{0,60}(amodei|阿莫迪|安特罗匹克|anthropic|阿莫戴)'
                r'|(slow ?down|slowdown|放缓|放慢|减速|刹车).{0,55}((?<![a-z])ai(?![a-z])|a\.i\.?|artificial intelligence|人工智能|前沿)'
                r'|((?<![a-z])ai(?![a-z])|a\.i\.?|artificial intelligence|人工智能).{0,55}(slow ?down|slowdown|放缓|放慢|减速|刹车)', re.I), 'ai_slowdown_debate'),
    # 2026-09-17: 美联储三年来首次加息 (09-16 FOMC, 三年来首次加息+暗示更多紧缩; BBC19/FT12/华尔街见闻×5/NYT×3/
    # 德国之声/中央社/HN/CoinDesk×2/RFI 约10源标题各异不合并, 财经 TOP5 第1+第5位被同事件拆开占据)
    # 锚点=美联储/联准会/Fed/Warsh+加息语境; 防误并: 'feds?' 词边界 (federal 不单独命中, 显式加 federal reserve);
    # 英澳/英央行不并 (无 fed 锚点; 'IMF...Australian...interest rate hike' 因 hike 非 raised 且无锚点不并);
    # BBC 版标题 'US interest rates raised for first time...' 无 Fed 字样 → 专列独立分支 (48h 窗口内唯一指该事件)
    (re.compile(r'(?:\bfeds?\b|federal reserve|美联储|聯準|联准会).{0,50}(?:rate hike|first rate (?:hike|rise|increase)|\bhikes? (?:the )?(?:key |interest )?rates?\b|raises? (?:the )?(?:key |interest )?rates?\b|interest rates? (?:were )?(?:raised|hiked)|rais\w*\s+interest\s+rates?|加息|升息|調升利率|调升利率)'
                r'|(?:rate hike|加息|升息).{0,50}(?:\bfeds?\b|federal reserve|美联储|聯準|联准会)'
                r'|(?:warsh|沃什).{0,40}(?:rate|加息|升息|hike)'
                r'|interest rates raised for (?:the )?first time', re.I), 'fed_rate_hike'),
    # 2026-09-18: 加拿大成欧盟首个"准成员"提案 (HN 英文标题 / 德国之声 "Von der Leyen eyes Canada..." 同事件标题各异不合并,
    # 各占宏观 TOP1/TOP4; 锚点须带 associate/准成员 语境防一般加欧新闻误并; von der leyen 标题用 "first associate member")
    (re.compile(r'(canad|carney|卡尼|加拿大).{0,80}(associate|quasi[- ]member|准成员)|(associate|quasi[- ]member|准成员).{0,80}(canad|carney|卡尼|加拿大)', re.I), 'canada_eu_associate'),
    # 2026-09-19: OpenAI 披露模型"异常行为"透明度报告 (德国之声14/IT之家9/FT6/Engadget6/华尔街见闻3 共5源标题各异不合并:
    # discloses new 'concerning' behavior / 披露 GPT-5.6 Sol 异常行为 / reveals more instances of concerning AI model behaviors;
    # 模糊防误并: 必须带 concerning/异常行为/隐瞒/六起/transparency report 语境, 不用泛 'behaviors' 裸词)
    (re.compile(r'openai.{0,70}(concerning|transparency report|異常行為|异常行为|令人擔憂|令人担忧|隱瞞|隐瞒|撒謊|撒谎|六起)', re.I), 'openai_transparency'),
    # 2026-09-19: Google 发布新实验性 "CC" AI 智能体 (Engadget12/TechCrunch12/Ars12 三源同事件标题各异不合并;
    # 必须带 \bcc\b 产品名 — Verge "Google will now let any AI agent run your smart home"(hot15) 属不同事件不并)
    (re.compile(r'(google|谷歌).{0,40}\bcc\b.{0,70}(ai agent|agent|famil|household|家庭|助手)|\bcc\b.{0,60}(ai agent|agent).{0,60}(famil|household|家庭)', re.I), 'google_cc_agent'),
    # 2026-09-19: 习近平访美随行企业高管名单 (中央社 + RFI 两条同事件: 中际旭创/小米/宁德时代/比亚迪 等随行, 川习会 09-24)
    (re.compile(r'(?:随|隨|随同|随行|高管|代表团|代表團|商界|陪).{0,40}[习習]近平.{0,20}(访|訪)美|[习習]近平.{0,20}(访|訪)美.{0,80}(高管|国宴|國宴|随行|隨行|名单|名單)', re.I), 'xi_us_visit'),
    # 2026-09-19: 巴菲特卸任伯克希尔董事长 (BBC11/DW11/虎嗅3/HN3/NYT3/中央社3 共6源标题各异不合并, 当日最大财经人事事件)
    (re.compile(r'(buffett|巴菲特).{0,60}(steps? down|stepping down|卸任|接任|chairman|董事長|董事长)|(chairman|董事長|董事长|卸任).{0,40}(buffett|巴菲特)', re.I), 'buffett_stepdown'),
    # 2026-09-20: Google Gemini 越狱后自主入侵三家真实企业事件 (Verge18/FT12/DW12/TechCrunch9/BBC World9/Engadget9/
    # IT之家6/格隆汇3/第一财经3/德国之声中文3 共10源标题各异不合并 → 同一事件同时占 科技/AI TOP1 与 财经/投资 TOP3,
    # [N源] 失效且跨分类重复; 锚点必须是 gemini (裸 google 会把 Chrome/Android 漏洞类新闻误并),
    # 中文源用 谷歌+入侵/越狱 窄分支兜底; 触发词仅取越狱/入侵/rogue/hack 语境,
    # 排除 "Gemini 4 Pro偷跑上线/碾压Astra和Fable"(模型发布, 无入侵语境) 与 "Gemini三度窥秘越轨"(DW 中文评论, 无入侵语境)
    (re.compile(r'gemini.{0,50}(rogue|hack|hacked|hacking|hacker|越狱|越獄|入侵|自主接入|escaped|逃逸|安全测试|安全測試|security test|testing environment)'
                r'|(rogue|hack|hacked|hacking|hacker|越狱|越獄|入侵|自主接入|escaped|逃逸).{0,50}gemini'
                r'|(谷歌|google).{0,25}(越狱|越獄|自主入侵|入侵三家|自主接入)', re.I), 'gemini_hack_incident'),
]

def entity_key(title, summary):
    # 2026-09-09: 实体匹配文本必须保留 ASCII 点号! norm() 把 '.' 替换成空格 → "ChatGPT Images 2.5" 变 "2 5",
    # chatgpt_images_25/gemini_38_flash 等版本号规则全部静默失效 (gemini 3.8 规则 09-03 起从未生效);
    # 其余标点 (，。、！？等) 照常归一
    raw = f'{title} {summary}'
    combined = re.sub(r'[，,、；;：:。·！!？?"\'（）()【】]+', ' ', raw).strip()
    for rx, key in ENTITY_KEYS:
        if rx.search(combined):
            return key
    return None

def backfill_summary(rep, group):
    """代表摘要为空时的回填 (2026-09-09 + 2026-09-20):

    ① 优先取组内有摘要成员 (中文标题优先, 再按 hot) — 解决 HN 英文无摘要版压过有摘要中文版;
    ② 组内都无摘要时退用视频说明文字 caption — 否则单源 BBC 视频条目显示 (无摘要)。
    """
    if rep.get('summary'):
        return
    cands = [a for a in group if a.get('summary')]
    if cands:
        rep['summary'] = sorted(cands, key=lambda a: (bool(re.search(r'[\u4e00-\u9fff]', a['title'])),
                                                      a['hot_score']), reverse=True)[0]['summary']
    elif rep.get('caption'):
        rep['summary'] = rep['caption']

def group_events(articles):
    """全量事件分组: entity_key 优先, 否则 norm(title)[:40] 指纹"""
    groups = defaultdict(list)
    for a in articles:
        ek = entity_key(a['title'], a['summary'])
        key = ('e', ek) if ek else ('t', norm(a['title'])[:40])
        groups[key].append(a)
    return list(groups.values())

def pick_representative(group):
    """代表: hot 高优先, 同 hot 有日期优先, 再同分中文标题优先; 返回 (rep, 唯一源数)"""
    srcs = set(a['feed_name'] for a in group)
    rep = sorted(group, key=lambda a: (a['hot_score'], bool(a['pub_date']),
                bool(re.search(r'[\u4e00-\u9fff]', a['title']))), reverse=True)[0]
    return rep, len(srcs)

# ── 重点事件保底 (2026-09-02 实现, 同 skill 文档 2026-08-09 Hassabis 案例) ──
# 大事件 hot 分不足时替换 TOP5 末位, 防止被截断 (如 苹果 CEO 换任 8条报道 hot 仅6)
# 2026-09-09: 收紧苹果规则 — 原裸 `(ternus|特努斯)` 会让换帅后一周的跟进旧闻(如 09-06 古尔曼"现在是特努斯时代")持续强制插入,
# 挤掉更新鲜的大事件; 改为要求换任语境词 (接替/卸任/换帅/告别/最后一天等)
PRIORITY_EVENTS = [
    (re.compile(r'(ternus|特努斯|tim cook|库克).*(final message|parting|告别|farewell|executive chair|最后一天|卸任|接任|接替|换帅|离任)|(卸任|接任|接替|换帅|离任).*(ternus|特努斯|tim cook|库克)', re.I), '科技/AI'),
    # 2026-09-15: AI 巨头集体呼吁"放缓AI发展"辩论 (Amodei 倡议 + 马斯克/奥特曼背书 + 微软自律准则 + 特朗普反对 + 美股AI板块大跌;
    # 15+ 源碎片化, 代表 hot 仅 12 → 天然排名被 14 分 HN 条目挤出 TOP5; 同类: 苹果 CEO 换任案例 2026-09-02)
    (re.compile(r'(amodei|阿莫迪|安特罗匹克|anthropic|阿莫戴).{0,60}(slow ?down|slowdown|slow(?!\w)|放缓|放慢|减速|刹车|警告|warn)'
                r'|(slow ?down|slowdown|放缓|放慢|减速|刹车).{0,55}((?<![a-z])ai(?![a-z])|a\.i\.?|人工智能|前沿)'
                r'|((?<![a-z])ai(?![a-z])|a\.i\.?|人工智能).{0,55}(slow ?down|slowdown|放缓|放慢|减速|刹车)', re.I), '科技/AI'),
    # 2026-09-19: 巴菲特卸任伯克希尔董事长 (6源合并后 hot 11, 与另外 4 条同为 11 分的普通条目竞争排第 6 位被 TOP5 截断;
    # 56 年任期终结为当日最大财经人事事件, 同类 2026-08-09 Hassabis 案例 / 2026-09-15 放缓辩论案例)
    (re.compile(r'(buffett|巴菲特).{0,60}(steps? down|stepping down|卸任|接任|chairman|董事長|董事长)|(chairman|董事長|董事长|卸任).{0,40}(buffett|巴菲特)', re.I), '财经/投资'),
]

def apply_priority_events(results, topic_articles, priority_events=None):
    """重点事件保底插入: 大事件 hot 分不足被 TOP5 截断时替换该主题末位 (内部替换, 无返回)。

    2026-09-20: ①候选改为跨主题查找 — 保底规则的目标主题(如 科技/AI)与 classify 实际判定的分类可能不一致
    (事件组代表若是 华尔街见闻/FT 等 category=财经 源, 会被 category +3 权重拉去 财经/投资), 旧写法
    cands 恒空 → 机制静默失效 (实测 09-20: AI 放缓辩论组 rep hot11 落在 财经/投资, 未被插入 科技/AI, 事件全天不显示);
    ②排除已出现在任一主题 TOP5 的事件, 防跨分类重复展示同一条。
    """
    for prx, ptopic in (priority_events if priority_events is not None else PRIORITY_EVENTS):
        if not results.get(ptopic):
            continue
        if any(prx.search(a['title'] + ' ' + a['summary']) for a in results[ptopic]):
            continue
        shown = {id(a) for t2 in results for a in results[t2]}
        cands = [a for t2 in topic_articles for a in topic_articles[t2]
                 if id(a) not in shown and prx.search(a['title'] + ' ' + a['summary'])]
        if cands:
            best = max(cands, key=lambda a: (a['hot_score'], bool(a['pub_date'])))
            results[ptopic][-1] = best

# ── 主流程 ────────────────────────────────────────────
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
# 2026-09-11: 窗口修复 — fetched_at 是 fetcher 用 datetime.now().isoformat() 写的本地 CST 字符串,
# 而 SQLite datetime('now') 是 UTC; 旧写法字符串比较使实际窗口 ≈56h。改用本地 cutoff 参数化查询, 精确 48h。
cutoff = (datetime.now() - timedelta(hours=48)).isoformat()
cur.execute("""
    SELECT id, feed_name, title, summary, link, author, pub_date, category, tags, hot_score
    FROM articles WHERE fetched_at >= ?
    AND hot_score > 0
    ORDER BY hot_score DESC LIMIT 3000
""", (cutoff,))
rows = cur.fetchall()
total_48h = conn.execute(
    "SELECT COUNT(*) FROM articles WHERE fetched_at >= ?", (cutoff,)).fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT feed_name) FROM articles WHERE fetched_at >= ?", (cutoff,))
n_feeds = cur.fetchone()[0]
# 2026-09-15: 新增数 = 当日 fetch 批次条数 (今日 00:00 起; 与 job prompt "新增 M 条" 口径一致)
today_start = datetime.now().strftime('%Y-%m-%dT00:00:00')
n_new = conn.execute("SELECT COUNT(*) FROM articles WHERE fetched_at >= ?", (today_start,)).fetchone()[0]
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
    if 'engadget' in feed.lower() and ENGADGET_GUIDE_RE.search(title):
        continue
    if not title:
        continue
    if is_noise(text):
        continue
    articles.append({
        'id': r['id'], 'feed_name': feed, 'title': title, 'summary': summary,
        'caption': video_caption(r['summary'] or ''),  # 2026-09-20: 视频说明文字兜底 (仅当摘要为空且组内无正文可回填时用)
        'link': r['link'], 'pub_date': r['pub_date'] or '',
        'category': r['category'] or '', 'hot_score': r['hot_score'] or 0,
    })

# 1) 全量事件分组 (跨主题) → 代表文章
events = group_events(articles)
event_reps = []
for g in events:
    rep, nsrc = pick_representative(g)
    rep['nsrc'] = nsrc
    # 2026-09-09: 摘要回填 — 代表无摘要时取组内有摘要成员 (中文优先, 再按 hot), 解决 HN 无摘要版压过有摘要中文版
    # 2026-09-20: 组内无成员有摘要时, 退用视频说明文字 caption (否则单源视频条目显示 (无摘要))
    backfill_summary(rep, g)
    event_reps.append((rep, g))

# 2) 分类
topic_articles = {t: [] for t in KEYWORDS}
unmatched = 0
for rep, g in event_reps:
    c = classify(f"{rep['title']} {rep['summary']}", rep['category'])
    if not c:
        # 2026-09-09: 代表分类失败时按 hot 序试组内其他成员 — 修复英文代表标题无关键词(如 HN "On the Navier–Stokes Millennium Prize Problem")
        # 但同事件中文版(IT之家含 AI 智能体/OpenAI 关键词)被丢进未匹配池的问题
        for m in sorted(g, key=lambda x: x['hot_score'], reverse=True):
            c = classify(f"{m['title']} {m['summary']}", m['category'])
            if c:
                break
    if c:
        topic_articles[c].append(rep)
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

# 重点事件保底插入: 大事件 hot 分不足被截断时替换 TOP5 末位 (候选跨主题查找, 见 apply_priority_events)
apply_priority_events(results, topic_articles)

# ── 输出 ──────────────────────────────────────────────
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
print(f"📰 Wuhoo RSS 资讯简报 | {today}")
print("=" * 40)
print(f"数据采集: {n_feeds} 源 | 新增 {n_new} 条 | 48 小时窗口（库内 {total_48h} 条）")

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
