# -*- coding: utf-8 -*-
"""2026-10-30 维护回归：
① google_ai_ads_global — 谷歌 AI 搜索广告推向国际市场 TechCrunch/IT之家 中英拆占科技TOP4+TOP5；
② google_q3_earnings — Alphabet Q3 财报不及预期→创纪录暴跌 9 源簇拆占 财经TOP4+产业TOP1；
   市场综述稿(FT 美股大跌/见闻 美股指三连涨)与信用市场前瞻稿(CDS)为独立事件不并；
③ amazon_globalstar_deal — FCC 批准 Leo 收购 Globalstar Engadget/HN/Solidot 三源拆占产业TOP3+4；
④ NOISE — BBC 能源补贴 FAQ 问答体、DW "Living with" 贸易战软专题；卫报预算新闻不误伤。"""
from daily_briefing import entity_key, is_noise


# ── ① google_ai_ads_global ─────────────────────────

def test_ads_中英两版命中():
    assert entity_key('Google expands AI Search ads globally as core ad growth slows', '') == 'google_ai_ads_global'
    assert entity_key('核心广告业务增长放缓，谷歌将 AI 搜索广告推向国际市场', '') == 'google_ai_ads_global'


def test_ads_财报稿不被抢判():
    # 财报稿含"搜索广告疲态"但无国际语系 → 归 earnings
    assert entity_key('谷歌大跌！Q3业绩不及预期，自由现金流大幅下降，AI投入回报质疑加剧｜财报见闻',
                      '谷歌母公司Alphabet本季财报营收与盈利均未达预期，云业务强劲扩张难以掩盖搜索广告疲态与自由现金') == 'google_q3_earnings'


# ── ② google_q3_earnings ─────────────────────────

def test_earnings_多波次成员命中():
    assert entity_key('谷歌 2026Q3 财报暴露 AI 变现焦虑，股价盘后暴跌逾 7%', '') == 'google_q3_earnings'
    assert entity_key('谷歌创纪录暴跌？不，谷歌电话会：资本开支不及预期，盘后跌幅扩大', '') == 'google_q3_earnings'
    assert entity_key('谷歌美股盘后跌逾9%', '') == 'google_q3_earnings'
    assert entity_key('谷歌、微软发布财报', '') == 'google_q3_earnings'
    assert entity_key('谷歌 Alphabet 盘初跌超 13% 创其历史上最大单日跌幅', '') == 'google_q3_earnings'
    assert entity_key('Google value plunges by $500bn as AI fears rattle Wall Street', '') == 'google_q3_earnings'
    assert entity_key('Google Search is now less than half of Alphabet’s revenue', '') == 'google_q3_earnings'
    assert entity_key('Alphabet: Rocked By Cash Flows, But Don\'t Fret', '') == 'google_q3_earnings'


def test_earnings_市场综述稿不并():
    # FT 大盘综述 (Nasdaq/tech stocks) 独立市场事件
    assert entity_key('US tech stocks fall after earnings fuel AI spending concerns',
                      'Nasdaq 100 drops 1.4% after Google parent Alphabet') != 'google_q3_earnings'
    # 见闻 美联储决议综述 (含盘后谷歌大跌) 归 fed_rate_hold
    assert entity_key('美联储按兵不动，美股指三连涨，甲骨文大涨11%，盘后谷歌大跌10%、微软走强', '') == 'fed_rate_hold'
    # 见闻云服务股普跌综述
    assert entity_key('谷歌创纪录暴跌，美股指终结三连涨，云服务股普跌，盘后英特尔狂泻20%、亚马逊重挫', '') != 'google_q3_earnings'


# ── ⑤ amazon_device_launch (10 月硬件发布会) ─────────────────

def test_device_四源命中():
    assert entity_key('Amazon debuts the Alexa Photo Frame and Echo Time smart clock, plus other upgraded devices', '') == 'amazon_device_launch'
    assert entity_key('All the Amazon Echo devices announced today: Echo Time, Alexa Photo Frame and more', '') == 'amazon_device_launch'
    assert entity_key('Amazon turns its most capable smart speaker into a smart camera, too',
                      'The Echo Studio with Home Camera can see and under') == 'amazon_device_launch'
    assert entity_key('Kindle Paperwhite Signature Edition (2026) review: Updated in all the right places', '') == 'amazon_device_launch'


def test_device_旧alexa免费与globalstar稿不抢判():
    assert entity_key('Alexa is now free on Fire TV sticks and older Echo speakers', '') == 'amazon_alexa_free'
    assert entity_key('FCC clears Amazon Leo to acquire mobile-satellite operator Globalstar', '') == 'amazon_globalstar_deal'


# ── ⑥ classify 并购→产业 语境规则 ─────────────────

def test_classify_并购稿归产业():
    from daily_briefing import classify
    # 中文代表版: 财经泛词 交易+美元 平分被吞进财经 (10-30 Globalstar 实测)
    assert classify('FTC 批准亚马逊以 115 亿美元收购 Globalstar。这笔交易为亚马逊的宽带卫星服务 Am', '科技') == '产业/公司'
    assert classify('FCC clears Amazon Leo to acquire mobile-satellite operator Globalstar', '科技') == '产业/公司'


def test_classify_财报稿不被并购规则误吸():
    from daily_briefing import classify
    # 无 M&A 词族，category=财经 +3 保持财经归属
    assert classify('谷歌大跌！Q3业绩不及预期，自由现金流大幅下降，AI投入回报质疑加剧｜财报见闻', '财经') == '财经/投资'


def test_classify_军购稿不被acquire误吸产业():
    from daily_briefing import classify
    # Ethiopia acquires Russian fighter jets — 国家军购，军事语境排除 M&A 加权
    r = classify('Ethiopia acquires Russian fighter jets and air defence systems amid war in Tigray', '综合')
    assert r != '产业/公司'


def test_earnings_信用市场前瞻稿不并():
    assert entity_key('微软谷歌财报前信用市场拉响警报：CDS创新高，AI烧钱开始让债主不安', '') != 'google_q3_earnings'


def test_earnings_他司与无关谷歌稿不并():
    assert entity_key('英特尔 2026Q3 营收 165 亿美元超预期：数据中心业务暴增近 80% 创 15 年最强增长', '') != 'google_q3_earnings'
    assert entity_key('Google AI gets cagey when asked who won the 2020 elections', '') != 'google_q3_earnings'
    # Gemini 4 Carbon 发布稿仍归自身实体 (回归防抢判)
    assert entity_key('Google launches Gemini 4 Carbon with a ‘significant leap’ in cybersecurity', '') == 'gemini_4_carbon'


# ── ③ amazon_globalstar_deal ─────────────────────────

def test_globalstar_三源命中():
    assert entity_key('FCC clears Amazon Leo to acquire mobile-satellite operator Globalstar', '') == 'amazon_globalstar_deal'
    assert entity_key('US agency approves Amazon Leo’s $11.5B acquisition of Globalstar', '') == 'amazon_globalstar_deal'
    assert entity_key('FTC 批准亚马逊以 115 亿美元收购 Globalstar', '') == 'amazon_globalstar_deal'


def test_globalstar_宽带计划稿不并():
    # Solidot 年底推出宽带服务为 Amazon Leo 另一动态，题面与截断摘要均无 globalstar
    assert entity_key('亚马逊计划年底推出互联网宽带服务', '负责宽带卫星项目 Amazon Leo 的副总裁透露已制造') != 'amazon_globalstar_deal'


# ── ④ NOISE ─────────────────────────

def test_noise_能源补贴faq():
    assert is_noise('Will I get the £100 energy payment and when will I receive it?')


def test_noise_卫报预算新闻不误伤():
    assert not is_noise('Budget 2026: £100 energy payment for millions and rise in bank tax as watchdog warns')


def test_noise_dw贸易战特稿():
    assert is_noise('Living with the US-Canada trade war')
