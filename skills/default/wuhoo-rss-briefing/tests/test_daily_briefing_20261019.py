# -*- coding: utf-8 -*-
"""2026-10-19 回归：
1) SA_LOW_RE — Seeking Alpha 自营播客栏目 "Wall Street Brunch"（无摘要占财经 TOP1）
2) ENGADGET_GUIDE_RE — "The reason your …" 解释体软文（Alexa always listening 占产业 TOP3）
3) NOISE — 华尔街见闻抽象市场观点栏目文 "若是反弹还没来"（误入科技/AI TOP5）
4) 防误伤 — 正常 SA 财报稿 / TechCrunch always-listening 真新闻 / 含"反弹"正常行情稿不误命中
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import is_noise, SA_LOW_RE, ENGADGET_GUIDE_RE


# ── SA Wall Street Brunch 播客栏目 ──────────────────────

def test_sa_wall_street_brunch_low():
    assert SA_LOW_RE.search("Wall Street Brunch: SpaceX, Tesla, Meta On The Earnings Card")
    assert SA_LOW_RE.search("Wall Street Brunch: Nvidia And Jackson Hole Vie For Market Sway")

def test_sa_normal_earnings_not_caught():
    assert not SA_LOW_RE.search("NVIDIA beats Q3 revenue estimates, guidance above consensus")
    assert not SA_LOW_RE.search("Apple raises dividend after record fiscal year")

def test_sa_earnings_call_still_low():
    # 既有规则不回退
    assert SA_LOW_RE.search("Tesla Q3 2026 earnings call: margins compress")


# ── Engadget "The reason your" 解释体 ──────────────────────

def test_engadget_reason_your_guide():
    assert ENGADGET_GUIDE_RE.search("The reason your Amazon Alexa devices are always listening")

def test_engadget_union_news_not_caught():
    assert not ENGADGET_GUIDE_RE.search("Amazon uses AI to monitor union risk in UK warehouses")

def test_techcrunch_always_listening_not_caught():
    # 非 Engadget feed 级生效 + 标题不以 the reason your 开头
    assert not ENGADGET_GUIDE_RE.search(
        "Apple Watch’s new AI features are normalizing the idea that technology is always listening")
    assert not ENGADGET_GUIDE_RE.search("Thanks to Siri Recaps, your Apple Watch is always listening")


# ── 华尔街见闻抽象观点栏目文 ──────────────────────

def test_wscn_vague_opinion_noise():
    assert is_noise("若是反弹还没来 AI产业趋势放缓，利率先于通胀开始回落")

def test_rebound_normal_news_not_caught():
    assert not is_noise("美股三大股指周五反弹，纳指涨超1%，AI板块领涨")
    assert not is_noise("A股午后反弹：券商板块异动拉升，两市成交破万亿")


# ── 私募名人直播观点稿 ──────────────────────

def test_linyuan_livestream_opinion_noise():
    assert is_noise("林园：现在是乌龟爬着，等牛市哪天爆发，看好AI大时代但不碰个股 "
                    "10月15日，林园在私募排排网直播中围绕市场、AI、医药消费等话题分享了自己的判断。 投资作业本课代")

def test_market_event_not_caught_by_linyuan():
    assert not is_noise("公募基金三季报披露：多只科技主题基金规模翻倍")
