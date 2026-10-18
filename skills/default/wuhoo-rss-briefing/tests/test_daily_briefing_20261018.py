# -*- coding: utf-8 -*-
"""2026-10-18 回归：
1) NOISE — IT之家"现已在京东上架"发售句式通式 (倍思移动电源/讯飞词典笔占产业 TOP3-4)
2) NOISE — 括注国补到手价通式 (七彩虹橘宝R16新增配置占科技 TOP4)
3) NOISE — @RD观测 博主销量爆料 / 虎嗅"最担心的事情发生了"观点文
4) classify — 外交人员/使馆事件 → 宏观政策 (FT settlers attack diplomats 误占财经 TOP1)
5) SA_LOW_RE — busy week 周度前瞻栏目
6) clean_summary — 格隆汇 "格隆汇X月X日｜" byline 前缀剥离
7) 防误伤 — 真发布会/真新闻/正常 SA 财报标题不误命中
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import is_noise, classify, clean_summary, SA_LOW_RE, ENGADGET_GUIDE_RE


def test_engadget_alexa_faq_guide():
    assert ENGADGET_GUIDE_RE.search("What does the yellow light on your Alexa device mean and how do you clear it?")
    assert ENGADGET_GUIDE_RE.search("Common problems with Amazon Alexa and how to fix them")

def test_engadget_news_not_caught():
    assert not ENGADGET_GUIDE_RE.search("Amazon uses AI to monitor union risk in UK warehouses")


def test_gamepad_presale_variant_noise():
    assert is_noise("易速马 S05 Pro 手柄预售：TMR 摇杆，标配充电底座，到手价 219 元 "
                    "易速马 (EasySMX) 现已启动赤兔 S05 Pro 手柄的预售")

def test_presale_variant_not_caught_on_normal_news():
    assert not is_noise("某车企全新 SUV 开启预售，预售价 25.98 万元起，预计年底交付")


def test_ac_codename_leak_noise():
    assert is_noise("中国秦朝背景《刺客信条：命运》早期实机视频曝光：腾讯天美工作室群主导，起步阶段即被取消")

def test_ubi_financial_not_caught():
    assert not is_noise("育碧公布 2026 财年业绩：营收同比下降 8%，多款游戏延期")


# ── IT之家 发售句式通式 ──────────────────────

def test_baseus_powerbank_noise():
    assert is_noise("倍思推出 2026 新国标 45W 自带双线移动电源：2C+1A+1Lightning，20000mAh 电芯售 171 元 "
                    "倍思现已在京东上架 2026 新国标 45W 自带双线移动电源，该产品采用 2C+1A+1Lightning")

def test_iflytek_dict_pen_noise():
    assert is_noise("科大讯飞 AI 词典笔 X9 上架：内置 85 本词典、支持小初高 9 科知识查询，744 元 "
                    "科大讯飞现已在京东上架讯飞 AI 词典笔 X9，定价为 744 元，部分地区国补后低至 674.1 元")

def test_real_launch_not_caught():
    # 真发布会事件不用"现已在京东上架"流水句式
    assert not is_noise("小米18 Pro 发布会定档：搭载玄戒 O3 芯片，雷军官宣 10 月 26 日见")


# ── 国补括号价通式 ──────────────────────

def test_colorful_laptop_guobu_noise():
    assert is_noise("七彩虹橘宝 R16 游戏本新增 AMD R7 H 255 + 16G + 512G + RTX 5060 配置，9999 元（国补 8499.15 元）")

def test_guobu_normal_news_not_caught():
    # 正常政策新闻含"国补"但无括注到手价形态
    assert not is_noise("商务部：国庆期间家电国补政策带动消费增长 12%，各地追加补贴额度")


# ── 博主爆料 / 自媒体观点 ──────────────────────

def test_rd_observer_leak_noise():
    assert is_noise("曝小米 18 Fold 中折叠手机销量突破十万台：首搭玄戒 O3、后置徕卡三摄，10999 元起 "
                    "据长期关注国内手机市场份额的数码博主 @RD观测 爆料，截至 2026 年第 40 周")

def test_huxiu_opinion_noise():
    assert is_noise("百度，最担心的事情发生了 说实话，这些年用百度搜索，有时候挺考验技术的")


# ── 外交事件 classify → 宏观政策 ──────────────────────

def test_diplomat_attack_policy():
    text = ("Israeli settlers attack European diplomats in the West Bank "
            "Belgian foreign minister says his government will summon Israel's ambassador")
    assert classify(text, '财经') == '宏观政策'

def test_diplomat_rule_not_steal_market_news():
    # 正常市场稿无外交词，category=财经 加权保持
    assert classify("美国股市三大股指收涨，纳指反弹超1%，芯片指数七连跌终止", '财经') == '财经/投资'


# ── SA busy week 周度栏目 ──────────────────────

def test_sa_busy_week_filtered():
    assert SA_LOW_RE.search("Meta, Tesla Headline Earnings In Busy Week For Markets")

def test_sa_normal_earnings_not_filtered():
    assert not SA_LOW_RE.search("NVIDIA beats Q3 revenue estimates as data center demand surges")


# ── 格隆汇 byline 前缀 ──────────────────────

def test_gelonghui_byline_stripped():
    assert clean_summary("格隆汇10月17日｜摩根士丹利称，2027年，超大规模云厂商新增算力同比增 48%").startswith("摩根士丹利称")

def test_gelonghui_no_prefix_untouched():
    assert clean_summary("摩根士丹利称，2027年数据中心新增算力同比激增48%").startswith("摩根士丹利称")
