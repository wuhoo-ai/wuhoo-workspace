# -*- coding: utf-8 -*-
"""2026-10-21 回归：
1) NOISE 国补促销句式通捕 — REDMI MiniLED 显示器 "国补后 2294 元" 占产业/公司 TOP4（旧 10-18 括注句式不覆盖无括号形）
2) photo_caption — BBC 中文 <img alt> 照片说明兜底（霍尔木兹轮船遇袭 hot11 (无摘要) 实测）
3) ENTITY tesla_spacex_merger — BBC/Verge/FT/TC/Ars/一财/IT之家 拆占两榜合并
4) ENTITY spacex_q3_earnings — 见闻/Verge/IT之家/NYT/TC/一财 Q3 财报拆榜合并
防误伤/防误并回归 4+ 例。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import is_noise, entity_key, photo_caption, clean_summary


# ── 1) NOISE 国补促销稿 ──────────────────────────────

def test_guobu_promo_title_noise():
    assert is_noise("电竞娱乐双旗舰：小米 REDMI MiniLED 显示器 G Pro 27U 2026 国补后 2294 元")

def test_guobu_promo_summary_noise():
    assert is_noise("京东 11.11 大促期间，按下方步骤下单，叠加 10% 国补后仅需 2294.1 元")

def test_jd_activity_box_noise():
    assert is_noise("【京东活动可能随时变更，需以实付款为准】小米 REDMI 显示器 G Pro 27U")

def test_guobu_policy_news_not_noise():
    # 真政策稿: 国补后接的不是 数字+元 到手价句式
    assert not is_noise("国补政策12月继续发放，单件补贴上限另定，家电行业销售额增长")

def test_guobu_word_far_from_price_not_noise():
    assert not is_noise("以旧换新国补资金已到账，消费者购买绿色智能产品迎来窗口期")


# ── 2) photo_caption 照片说明兜底 ────────────────────

BBC_HORMUZ_RAW = ('<div></div><div><div><img alt="一艘蓝色船身、白色上层建筑的油轮在疑似遭受袭击起火后，'
                  '被一艘较小船只喷洒水柱" height="1080" src="https://images.weserv.nl/?url=ichef.bbci.co.uk/x.png" '
                  'width="1920" /></div></div><section><strong id="article-byline">Article Information</strong>'
                  '<ul><li><span>Author, </span><span>约书亚·奇塔姆</span></li></ul></section>')

def test_photo_caption_extracts_alt():
    assert photo_caption(BBC_HORMUZ_RAW).startswith("一艘蓝色船身")

def test_photo_caption_latin_only_rejected():
    assert photo_caption('<img alt="Getty Images" src="x.jpg"/><p>abc</p>') == ''

def test_photo_caption_no_img():
    assert photo_caption('普通文本无图片') == ''

def test_bbc_hormuz_summary_empty_then_caption():
    # 正文剥离后为空 → 兜底链 video_caption→photo_caption 生效
    assert clean_summary(BBC_HORMUZ_RAW, "BBC 中文") == ''


# ── 3) ENTITY 特斯拉×SpaceX 合并 ─────────────────────

def test_merger_bbc():
    assert entity_key("Elon Musk says Tesla-SpaceX merger being considered",
                      "Musk says special committees within both companies") == "tesla_spacex_merger"

def test_merger_verge():
    assert entity_key("Tesla and SpaceX are discussing a possible merger, Musk says", "") == "tesla_spacex_merger"

def test_merger_ithome_lianyin_beats_earnings():
    # 标题含联姻 + 摘要含财报电话会 — merger 规则在前须抢先
    assert entity_key("地表最强科技联姻：马斯克称特斯拉与 SpaceX 合并“有很多好处”",
                      "在财报电话会上，全球首富埃隆马斯克表示") == "tesla_spacex_merger"

def test_merger_chinese_yicai():
    assert entity_key("马斯克称SpaceX和特斯拉已成立特别委员会，研究潜在合并", "") == "tesla_spacex_merger"

def test_stock_giveaway_not_merged():
    # 送股给全美儿童事件 — 无合并锚不并入
    assert entity_key("Elon Musk Says He Will Give a SpaceX Share to 'Every Kid in America'",
                      "Anthropic rival SpaceX earlier said it would form a public benefit fund") != "tesla_spacex_merger"

def test_starship_catch_not_merged():
    assert entity_key("SpaceX will try catching Starship and its booster for first time", "") != "tesla_spacex_merger"


# ── 4) ENTITY SpaceX Q3 财报 ─────────────────────────

def test_earnings_yidianwen():
    assert entity_key("SpaceX Q3 AI业务大爆发、收入暴增830%，利润碾压预期", "") == "spacex_q3_earnings"

def test_earnings_nyt():
    assert entity_key("SpaceX Swings to a Profit, as A.I. Business Grows", "") == "spacex_q3_earnings"

def test_earnings_ithome_netprofit():
    assert entity_key("SpaceX 2026 财年第三财季归母净利润 44.04 亿美元，同比扭亏为盈", "") == "spacex_q3_earnings"

def test_earnings_trillion_claim():
    assert entity_key("马斯克：SpaceX 可能在 2028 年实现 1 万亿美元营收",
                      "当地时间 10 月 20 日，埃隆马斯克在社交平台发文") == "spacex_q3_earnings"

def test_market_wrap_not_earnings():
    # 市场综述稿 (盘后SpaceX涨近7%) 无业绩锚
    assert entity_key("美伊“妥协方案”搅动市场，原油走V，道指冲高回落涨1%，盘后SpaceX涨近7%",
                      "伊朗与美国谈判的妥协方案传闻一度令油价大幅跳水") != "spacex_q3_earnings"

def test_robotics_startup_not_earnings():
    assert entity_key("SpaceX alum’s aviation startup, Reliable Robotics, lands $140M",
                      "Reliable Robotics extended its Series D round") != "spacex_q3_earnings"
