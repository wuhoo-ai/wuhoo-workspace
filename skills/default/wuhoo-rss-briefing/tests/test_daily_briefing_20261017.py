# -*- coding: utf-8 -*-
"""2026-10-17 回归：
1) tesla_flying_car 实体合并 — 特斯拉飞行跑车展示 (BBC14 Watch 视频版 + 见闻热门6 中文版) 此前拆散
2) openai_eth_steal 实体合并 — OpenAI 智能体挪用他人钱包测试以太币 (Engadget12 + CoinDesk12)
   此前拆占 科技TOP+财经TOP 两榜且 CoinDesk 版无摘要
3) NOISE — Verge 一周评测特稿 / Show HN 项目帖 / AOC 显示器上架 / 保时捷Macan评测软文 /
   亚马逊雨林砍伐(裸amazon误命中产业) / BBC婚礼礼物街访 / 游戏娱乐(幕府将军2下架/动视COD子系列/永恒传说复刻) /
   勒卡雷文学特稿 / 苹果Sports小版本更新
4) 防误伤 — 保时捷Mission S概念车真发布 / 他品牌飞行汽车 / ETH币价稿 / 战争语境"现代战争" 均不误命中
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import entity_key, is_noise, classify


# ── tesla_flying_car ──────────────────────────────

def test_flying_car_bbc():
    assert entity_key("Watch: Did Tesla really just unveil a flying car?",
                      "Tesla CEO Elon Musk showcased the vehicle at a factory event") == 'tesla_flying_car'

def test_flying_car_jianwen():
    assert entity_key("特斯拉“飞行跑车”安全吗？马斯克：如果安全是首要目标，就别买",
                      "北京时间今天上午，一辆双座跑车在美国得克萨斯超级工厂亮相") == 'tesla_flying_car'

def test_flying_car_other_brand_excluded():
    # 小鹏汇天飞行汽车 — 无 tesla 锚不合并
    assert entity_key("小鹏汇天“陆地航母”飞行汽车完成载人试飞",
                      "分体式飞行汽车将在明年交付") != 'tesla_flying_car'

def test_tesla_non_flying_excluded():
    # 特斯拉其他发布稿无飞行锚不合并
    assert entity_key("特斯拉第三季度财报公布",
                      "营收同比增长12%") != 'tesla_flying_car'


# ── openai_eth_steal ──────────────────────────────

def test_eth_steal_engadget():
    assert entity_key("An OpenAI research agent 'stole' test Ethereum to finish a coding task",
                      "An OpenAI research model hit a nebulous milestone") == 'openai_eth_steal'

def test_eth_steal_coindesk():
    assert entity_key("An OpenAI agent ran out of Ethereum funds, and took from a wallet it did not own",
                      "") == 'openai_eth_steal'

def test_eth_price_excluded():
    # 以太坊币价稿 — 无 openai/盗取锚不合并
    assert entity_key("Ethereum climbs as ETF inflows accelerate",
                      "The second-largest crypto rose 4%") != 'openai_eth_steal'

def test_openai_no_ethereum_excluded():
    assert entity_key("OpenAI announces new pricing for Codex",
                      "The coding agent gets usage-based billing") != 'openai_eth_steal'


# ── NOISE ─────────────────────────────────────────

def test_noise_verge_week_review():
    assert is_noise("A week with RTX Spark: everything we’ve learned using Nvidia’s new laptops")

def test_noise_show_hn():
    assert is_noise("Show HN: Gemini 4 Argon plays StarCraft")

def test_noise_aoc_monitor_listing():
    assert is_noise("AOC 上架“AGP277QKM”27 英寸显示器：2K 425Hz QD-Mini LED、内置电源，3254 元")

def test_noise_porsche_review():
    assert is_noise("Porsche’s electric Macan Turbo is an automotive existential crisis")

def test_noise_amazon_deforestation():
    assert is_noise("Brazil: Amazon deforestation lowest in nearly 40 years")
    assert is_noise("Brazilian Amazon deforestation falls to lowest on record as pivotal vote looms")

def test_noise_wedding_present():
    assert is_noise("'I'd spend $1,000 on a wedding present'")

def test_noise_game_gossip():
    assert is_noise("差评如潮：世嘉暂时下架《全面战争：幕府将军 2》完全版，承认游戏体验未达到应有水平")
    assert is_noise("继《现代战争》《黑色行动》后：动视确认《使命召唤》将推出全新子系列，游戏开发工作已启动")
    assert is_noise("经典 JRPG《永恒传说》高清复刻版多平台发售，Steam 国区售价 138 元起")

def test_noise_le_carre_feature():
    assert is_noise("英國前情報首長談諜報小說大師勒卡雷：作品娛樂不寫實")

def test_noise_apple_sports_update():
    assert is_noise("灵动岛添新技能：苹果 Sports 升级，赛事中场休息自动触发“核心数据”")


# ── 防误伤 ────────────────────────────────────────

def test_porsche_mission_s_not_noise():
    assert not is_noise("保时捷发布 Mission S 概念车：定位高于 911，正开发新中置引擎超跑平台")

def test_war_context_not_noise():
    # 战争语境现代战争/黑色行动分析稿不被游戏模式误伤 (裸词已删除)
    assert not is_noise("乌克兰战场：现代战争中的无人机黑色行动")

def test_tesla_other_news_not_noise():
    assert not is_noise("特斯拉Q3交付量超预期，上海工厂满负荷运转")
