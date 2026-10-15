# -*- coding: utf-8 -*-
"""2026-10-15 回归：
1) openai_bugging_arrest 实体合并 — OpenAI 沙特工程师会议室藏窃听录音设备事件
   BBC14×2/FT6×2/IT之家6×2/Solidot9/TC6/Verge6/Engadget6/Ars6 拆占 财经 TOP2+TOP4
2) trump_russia_diesel_deal 实体合并 — 特朗普美俄柴油协议后续簇
   BBC中文"拟进口柴油"+BBC中文"分析：油价降不下"+DW Merz+NYT 参议员 拆占 宏观 TOP2+TOP4
3) NOISE — BBC中文 AI翻译取代人类特稿 (占产业 TOP1)、NYT 欧洲电车爱恨交加特稿 (占产业 TOP3)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import entity_key, is_noise


# ── openai_bugging_arrest ──────────────────────────────

def test_bugging_bbc_charged():
    assert entity_key("Saudi man charged with planting 'sophisticated' recording device in OpenAI office",
                      "Prosecutors say the device, wrapped in toilet paper, was fou") == 'openai_bugging_arrest'

def test_bugging_bbc_explainer():
    assert entity_key("Toilet paper and secret recorders: What we know about the arrest of the Saudi OpenAI engineer",
                      "Abdulrahman Alfozan had worked for the AI giant for more tha") == 'openai_bugging_arrest'

def test_bugging_ft_ticket():
    assert entity_key("OpenAI employee accused of bugging office booked one-way ticket to Saudi Arabia",
                      "Newly unsealed court filings say Abdulrahman Alfozan, his wi") == 'openai_bugging_arrest'

def test_bugging_it_zhixun():
    assert entity_key("在高管会议室偷偷安装录音设备，OpenAI 一沙特籍工程师被 FBI 逮捕",
                      "之家 10 月 14 日消息，据路透社报道") == 'openai_bugging_arrest'

def test_bugging_solidot():
    assert entity_key("OpenAI 工程师因在高管会议室放置监听设备被捕",
                      "35 岁的沙特籍 OpenAI 工程师 Abdulrahman Alfo") == 'openai_bugging_arrest'

def test_bugging_engadget():
    assert entity_key("OpenAI says it found a 'sophisticated recording device' hidden in its offices",
                      "The company asked its AI models to figure out what the dev") == 'openai_bugging_arrest'

def test_bugging_no_false_guardian_toiletpaper():
    # 卫报 toilet paper 物价稿无 openai/alfozan 锚 → 不命中
    assert entity_key("Wiped out: US faces surging toilet paper prices amid trade war with Canada",
                      "Paper products among hardest-hit sectors after trade nego") is None

def test_bugging_no_false_openai_generic():
    # OpenAI 常规稿无录音设备语系 → 不命中
    assert entity_key("OpenAI releases GPT-6 with major reasoning gains",
                      "The new model tops benchmarks across math and coding tasks") is None


# ── trump_russia_diesel_deal ──────────────────────────

def test_diesel_bbc_backlash():
    assert entity_key("特朗普拟从俄罗斯进口柴油 反对声浪趋涨",
                      "自2月底美以与伊朗爆发战争以来全球燃料价格飙升。") == 'trump_russia_diesel_deal'

def test_diesel_bbc_analysis():
    assert entity_key("分析：美国中期选举前夕油价降不下，特朗普难题加剧",
                      "特朗普周五宣布与俄罗斯总统普京达成一项新的柴油协议。") == 'trump_russia_diesel_deal'

def test_diesel_dw_merz():
    assert entity_key("Merz: Trump Russia diesel deal 'out of question' for Europe",
                      "Chancellor Friedrich Merz has said that Donald Tru") == 'trump_russia_diesel_deal'

def test_diesel_nyt_senators():
    assert entity_key("Senators Urge Trump to Reverse Diesel Deal With Putin",
                      "Bipartisan group says agreement undermines energy sanctions") == 'trump_russia_diesel_deal'

def test_diesel_no_false_houthi_oil():
    # 中央社青年运动推升油价稿有 川普+油 无 diesel/柴油 → 不命中
    assert entity_key("川普稱青年運動企圖在美期中選舉前推升油價　批行徑惡劣",
                      "美伊戰爭引發的區域衝突擴大之際，美國總統川普發文指控葉門叛軍") is None

def test_diesel_no_false_record():
    # 柴油纪录稿无俄锚 → 归 diesel_record 不并本事件
    k = entity_key("Trump's Iran war sends US diesel prices to record high",
                   "The Iran conflict pushed American pump prices to new records")
    assert k == 'diesel_record'


# ── NOISE ─────────────────────────────────────────────

def test_noise_ai_translation_feature():
    assert is_noise("AI翻译：还有多久会完全取代人类？ 阿里埃拉·巴尔蒂专门从事法律翻译工作")

def test_noise_ev_ambivalence_feature():
    assert is_noise("欧洲为何对中国电动汽车爱恨交加 位于英国利兹的一家比亚迪展厅")

def test_noise_real_ev_tariff_news_kept():
    # 正常欧盟对华电车关税新闻不误伤
    assert not is_noise("欧盟宣布对中国进口电动汽车征收最终反补贴关税")


# ── netflix_layoffs_2026 ─────────────────────────────

def test_netflix_bbc_shed():
    assert entity_key("Netflix to shed 1,000 jobs in steepest cuts since 2022",
                      "The cuts equate to around 6% of the streaming gian") == 'netflix_layoffs_2026'

def test_netflix_it_zhixun():
    assert entity_key("2022 年以来最大一轮裁员：Netflix 宣布全球裁员约 6%，涉及约 1000 个岗位",
                      "据华尔街日报消息") == 'netflix_layoffs_2026'

def test_netflix_tc_lay_off():
    assert entity_key("Netflix to lay off 1,000 staff amid intensifying competition for user attention",
                      "Netflix said most of the cuts would affect its pro") == 'netflix_layoffs_2026'

def test_noise_it_home_launch_promo():
    assert is_noise("长安凯程 V919 荣耀版 8 方上市：限时 8.89 万元起，标配宁德时代电芯")
    assert is_noise("联想小新 27 元气版一体机上架：酷睿 5 处理器，10 月 16 日开售")
    # 正常联想集团新闻不误伤
    assert not is_noise("联想集团发布最新财报：营收利润双双创历史新高")

def test_noise_steam_weekly_chart_and_gossip():
    assert is_noise("Steam 新一周游戏销量榜公布：《AION 2》继续领跑全球榜首")
    assert is_noise("小米员工透露智能家庭屏曾拟命名 HomeView，但最终仅路由器被冠以 Home 之名")
    # Steam 平台正常新闻不误伤
    assert not is_noise("Valve 宣布 Steam Machine 将于明年春季发售")

def test_netflix_content_news_not_merged():
    # Netflix 内容/剧集稿无裁员锚 → 不命中
    assert entity_key("Netflix renews One Piece for season 3",
                      "The streaming giant confirmed the adventure series") is None

