# -*- coding: utf-8 -*-
"""2026-10-13 噪声回归：IT之家消费电子发售续八（熊猫显示器）/ 降价促销导购（N→M元箭头格式）
+ 实体合并：Meta 'Wonder Full' 新模型发布并入 meta_muse"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import NOISE_PATTERNS, entity_key


def _hit(text):
    tl = text.lower()
    return any(re.search(p, tl) for p in NOISE_PATTERNS)


def test_panda_monitor_noise():
    assert _hit("熊猫\"S24Q6A\"23.8 英寸显示器发售：2K 180Hz，599 元（国补后 521.1 元）")
    assert _hit("熊猫 推出 27英寸 4K 显示器 上架京东")


def test_panda_no_false_positive():
    # 大熊猫动物新闻不误伤（无产品词+发售动词组合）
    assert not _hit("旅美大熊猫回国引发全球关注，熊猫保护合作续约")
    # 熊猫电子品牌正常公司新闻不误伤（无发售动词）
    assert not _hit("熊猫电子宣布与云厂商达成战略合作")
    # 正常科技新闻措辞不误伤
    assert not _hit("消息称英伟达计划以 24GB 显存 GeForce RTX 5080 显卡取代现有 16GB 版本")


def test_arrow_price_promo_noise():
    # 'N → M 元' 箭头降价格式（探新低/直降各措辞变体全捕）
    assert _hit("UHD 162Hz / FHD 485Hz：华硕 ROG XG27UCGR 显示器 2499 → 1869 元探新低")
    assert _hit("8199 → 4499 元：小米电视 S Pro Mini LED 2026 京东 11.11 直降")
    assert _hit("腾达泰山 BE7200 Ultra 路由器 429 →244 元国补直降")
    # 正常新闻不用箭头格式，不误伤
    assert not _hit("最低工资标准从 2000 元上调至 2300 元，12 月起执行")
    assert not _hit("证监会召开座谈会：发展壮大耐心资本，推动加大分红回购力度")


def test_wonder_full_merges_into_meta_muse():
    # Verge 版标题无 muse 字样（Wonder Full 活动名）→ 并入 meta_muse 组
    assert entity_key("Meta has some Wonder Full new AI models",
                      "Meta is making up for lost time in the AI race.") == "meta_muse"
    # 中文版（含 Muse 字样）同组
    assert entity_key("Meta 发布 Muse Wonder 系列旗舰 AI 模型，对标 Anthropic 与 OpenAI",
                      "") == "meta_muse"
    # 封锁事件优先归 amazon_block（规则顺序）
    assert entity_key("Meta's AI agent Muse has been blocked from using Amazon.com",
                      "") == "meta_muse_amazon_block"
    # Wonderfull 单词（旅行平台名）不误并 —— 必须 wonder+空格+full 双词
    assert entity_key("Wonderfull adds AI itinerary planning for travelers",
                      "") is None
