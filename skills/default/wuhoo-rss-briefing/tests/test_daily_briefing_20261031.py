# -*- coding: utf-8 -*-
"""2026-10-31 维护回归：
① binance_hack — 币安 63 亿美元被盗(朝鲜黑客涉案)12+ feeds 25 篇多波次报道簇拆占 财经TOP1+TOP3；
   FT 标题无币安字样靠截断摘要 "attack on Binance" 命中；卫报朝鲜黑客资金专题独立不并；币安常规产品稿不并。
② 国家军购→宏观政策 — Ethiopia acquires fighter jets 摘要 "acquisition of the warplanes" 被产业表裸词
   'acquisition' 漏进 产业 TOP5(10-30 排除规则只挡语境+3，未挡表词，纯标题测试未覆盖摘要形态)；
   国防承包商财报语境守门不误吸；Globalstar M&A 归产业回归。"""
from daily_briefing import entity_key, classify


# ── ① binance_hack 命中(全部取 10-31 窗口内真实标题/摘要形态) ──

def test_binance_英文源命中():
    assert entity_key('Binance crypto exchange suspends trades over North Korea-linked hack', '') == 'binance_hack'
    assert entity_key('Crypto giant Binance attempting to recover $6.3bn stolen in hack linked to North Korea', '') == 'binance_hack'
    assert entity_key('Binance Hack Sends Crypto Stocks Tumbling', '') == 'binance_hack'
    assert entity_key('What we know about Binance\'s $6.3bn hack', '') == 'binance_hack'
    assert entity_key('Binance pauses withdrawals as hackers suspected of stealing billions in crypto', '') == 'binance_hack'
    assert entity_key('North Korean hackers blamed for stealing record $6.3B in Binance breach', '') == 'binance_hack'
    assert entity_key('Hackers steal $6.3 billion from Binance in record crypto heist', '') == 'binance_hack'
    assert entity_key('Binance hacked for an estimated $6.3 billion in record crypto theft', '') == 'binance_hack'
    assert entity_key('Binance-hacker-1029 – $5.6B stolen from Binance', '') == 'binance_hack'


def test_binance_ft标题无锚靠摘要命中():
    # FT "$6.3bn in 30 minutes: how the world's biggest heist unfolded" 标题无 binance，
    # 真实流水线文本 = clean_title + clean_summary[:50]
    assert entity_key('$6.3bn in 30 minutes: how the world’s biggest heist unfolded',
                      'North Korean hackers’ attack on Binance takes cryp') == 'binance_hack'


def test_binance_中文繁简命中():
    assert entity_key('币安多达 30 亿美元数字货币被盗', '') == 'binance_hack'
    assert entity_key('币安惊魂夜：40分钟内，63亿美元是如何被转走的？', '') == 'binance_hack'
    assert entity_key('63亿美元！币安遭“史上最大”黑客洗劫，暂停全部存储和提取功能，承诺将承担所有损失', '') == 'binance_hack'
    assert entity_key('币安遭黑客攻击：涉63亿美元 或为史上最大规模 朝鲜黑客组织被指涉案', '') == 'binance_hack'
    assert entity_key('最大加密盜竊之一波及63億美元　幣安證實遭複雜攻擊現多處漏洞', '') == 'binance_hack'


def test_binance_卫报朝鲜黑客专题独立不并():
    # 币安无锚——朝鲜黑客核资金流向为独立专题
    assert entity_key('How crypto hacking funds isolated North Korea’s nuclear programme',
                      'Cryptocurrency theft is estimated to generate half') != 'binance_hack'


def test_binance_常规产品稿不并():
    assert entity_key('Binance launches new yield product for stablecoin savers', '') != 'binance_hack'


# ── ② 国家军购 → 宏观政策 ──

def test_军购_埃塞俄比亚真实流水线文本归宏观():
    # 10-31 实测 combined 文本(标题+截断摘要)
    r = classify('Ethiopia acquires Russian fighter jets and air defence systems amid war in tigray the acquisition of the warplanes comes amid ongoin', '综合')
    assert r == '宏观政策'


def test_军购_国防承包商财报语境不拉宏观():
    # revenue 财报词守门
    r = classify('Lockheed says revenue rose 8% as it delivers more fighter jets and air defence systems to allies', '综合')
    assert r != '宏观政策'


def test_军购_装备词单独不触发():
    # 有装备词无购词 → 军购规则不加分 (措辞避开 military 等宏观表词，验证纯装备展示稿不被拉榜)
    r = classify('New air defence systems were showcased at the annual naval exhibition', '综合')
    assert r != '宏观政策'


def test_ma_globalstar仍归产业():
    # M&A 语境 +3 规则回归: 并购稿不受军购规则影响
    r = classify('ftc 批准亚马逊以 115 亿美元收购 globalstar，这笔交易为亚马逊的宽带卫星服务 amazon leo 扩容', '综合')
    assert r == '产业/公司'
