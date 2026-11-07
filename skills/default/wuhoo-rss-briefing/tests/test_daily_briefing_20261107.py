# -*- coding: utf-8 -*-
"""2026-11-07 维护回归：
① ENTITY openai_125tn_funding — OpenAI 完成 110 亿美元首期新融资·估值 1.25 万亿美元
   (IT之家12/Verge12/TC9/见闻3×2 拆占 科技TOP5+财经TOP4 两榜；见闻"大金主踩刹车"后续稿无数字锚)。
   防误并: Anthropic IPO 估值下调稿、FT Anthropic IPO 稿（无 openai 锚）不并。
② ENTITY gemini_omni_12_flash — 谷歌 Gemini Omni 1.2 Flash 发布 (DeepMind/AI Blog 英文 + IT之家中文拆占科技榜)。
   防误并: Omni 1.1/其它模型稿不命中。
③ ENTITY dropbox_tigris — Dropbox 收购 Tigris Data (IT之家中文 TOP1 + TechCrunch 英文 TOP5 拆榜)。
   防误并: 单锚稿不并。
④ clean_summary — Google 博客图片卡 alt 垃圾 'Text "..." surroudned…' 置空走组内回填。"""
from daily_briefing import entity_key, clean_summary


# ── ① OpenAI 1.25 万亿估值融资簇 ──

def test_openai估值融资簇合并():
    assert entity_key('消息称 OpenAI 完成 110 亿美元首期新融资，估值 1.25 万亿美元',
                      '北京时间 11 月 7 日，据彭博社报道，知情人士称，OpenAI 新一轮融资已完成大约 110 亿') == 'openai_125tn_funding'
    assert entity_key('OpenAI valued at $1.25 trillion, as rival Anthropic nears its IPO',
                      'OpenAI is now valued at $1.25 trillion in a new round of funding that ') == 'openai_125tn_funding'
    assert entity_key('OpenAI reportedly raises an additional $11 billion at a $1.25 trillion valuation',
                      'OpenAI has reportedly raised an additional $11 billion as part of a ') == 'openai_125tn_funding'
    # 见闻后续稿: 标题无数字锚, 靠 遇冷语系分支; "OpenAI新融资" CJK 邻接防 \b 失效
    assert entity_key('大金主踩刹车？OpenAI新融资被曝遇冷、软银大幅缩减投入，CFO称中选后数据中心投资不变',
                      'OpenAI正面临新一轮融资的重大挑战。在10月末传出OpenAI将') == 'openai_125tn_funding'
    assert entity_key('OpenAI新一轮融资缩水！报道：完成110亿美元首批融资，估值1.25万亿美元，软银、红杉参投',
                      'OpenAI在AI行业情绪降温的背景下完成新一轮融资的首期交割') == 'openai_125tn_funding'


def test_openai估值融资防误并():
    # Anthropic IPO 估值下调稿 — 无 openai 锚 (1.2万亿—1.3万亿 不是 1.25)
    assert entity_key('AI抛售潮冲击Anthropic IPO，潜在估值预期下调至1.2万亿—1.3万亿美元',
                      'Anthropic PBC的IPO计划正面临严峻考验。在科技股遭遇重挫、纳斯达克') != 'openai_125tn_funding'
    # FT Anthropic IPO 稿 — 无 openai 锚
    assert entity_key('Anthropic to press ahead with IPO targeting $1.5tn valuation',
                      'Claude maker intends to list before Thanksgiving despite ') != 'openai_125tn_funding'
    # 市场综述稿 — 无 openai
    assert entity_key('AI交易大撤退、美股创纪录"血洗"2.8万亿！纳指跌近6%、芯片指数狂泻超10%',
                      '美东时间11月5日周四，美股科技股遭遇猛烈抛售') != 'openai_125tn_funding'


# ── ② Gemini Omni 1.2 Flash ──

def test_gemini_omni合并():
    assert entity_key('Gemini Omni 1.2 Flash: Fast and cost-effective with longer clips', '') == 'gemini_omni_12_flash'
    assert entity_key('AI 视频模型卷出新高度：谷歌 Gemini Omni 1.2 Flash 发布，原生 15 秒生成、较 1.1 降价 30%',
                      'IT之家 11 月 6 日消息，谷歌正式推出 Gemini Omni 1.2 Flash 视频生成模') == 'gemini_omni_12_flash'


def test_gemini_omni防误并():
    # 旧版本 1.1 稿不命中
    assert entity_key('Gemini Omni 1.1 降价调整说明', '') != 'gemini_omni_12_flash'
    # 非 Omni 系列不命中
    assert entity_key('谷歌发布 Gemini 4 Carbon 网络安全模型', '') != 'gemini_omni_12_flash'
    # omnibus 子串防词边界破口
    assert entity_key('The omnibus 1.2 spending bill', '') != 'gemini_omni_12_flash'


# ── ③ Dropbox 收购 Tigris ──

def test_dropbox_tigris合并():
    assert entity_key('云存储服务提供商 Dropbox 计划收购 Tigris Data，拓展企业开发者 AI 存储服务',
                      'IT之家 11 月 5 日消息，云存储服务提供商 Dropbox 今日宣布计划收购分布式对象存储平台') == 'dropbox_tigris'
    assert entity_key('Dropbox acquires Tigris Data for $350M to bolster its AI infrastructure',
                      'The deal is expected to support the development of DBX Agent Cloud') == 'dropbox_tigris'


def test_dropbox_tigris防误并():
    assert entity_key('Dropbox 第三季度财报超预期，股价盘后上涨', '') != 'dropbox_tigris'
    assert entity_key('Tigris Data 完成新一轮融资布局向量检索', '') != 'dropbox_tigris'


# ── ④ Google 博客 alt 文本垃圾 ──

def test_google_alt文本置空():
    assert clean_summary('Text "Gemini Introducing Gemini Omni 1.2 Flash" surroudned by images of creators') == ''
    assert clean_summary('Text “智能体 Muse 正式上线” 配图说明') == ''


def test_clean_summary正常正文不误伤():
    s = clean_summary('研究人员调查了先进多模态模型如何评估面试、会议报告和英语口语能力测试中的语音，测试的模型包括了 Google 与 OpenAI 两家。')
    assert s.startswith('研究人员调查了')


# ── ⑤ NOISE Verge 消费对比导购 (2026-11-07) ──

def test_verge比价软文命中噪声():
    from daily_briefing import is_noise
    assert is_noise('kpop demon hunters on 4k blu-ray costs less than a month of netflix premium')
    assert is_noise('the album costs less than a month of netflix premium subscription')


def test_verge比价软文防误伤():
    from daily_briefing import is_noise
    # 正常企业订阅涨价新闻不命中
    assert not is_noise('Netflix 宣布美国区订阅价格上调 3%，流媒体三巨头集体涨价')
