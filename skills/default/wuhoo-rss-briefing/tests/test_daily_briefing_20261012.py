# -*- coding: utf-8 -*-
"""2026-10-12 噪声回归：集思录概念股一览表 / IT之家电源充电宝发售续七（长城/街电/闪极）"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import NOISE_PATTERNS


def _hit(text):
    tl = text.lower()
    return any(re.search(p, tl) for p in NOISE_PATTERNS)


def test_jisilu_stock_list_noise():
    assert _hit("重磅！！化工涨价概念股一览表！")
    assert _hit("稀土概念股一览表 附龙头名单")


def test_greatwall_psu_noise():
    assert _hit("长城推出 KING 1050W 氮化镓全模组钛金牌电源：10 年质保，1799 元")
    assert _hit("长城 电源 上架 京东")


def test_jiedian_shanji_powerbank_noise():
    assert _hit("街电推出 55W 挂包充电宝：2C 设计、10000mAh 电芯，273 元")
    assert _hit("闪极推出 Vision Mag 带屏磁吸充电宝：15W 无线充 + 20W 有线充")


def test_no_false_positive():
    # 长城汽车正常新闻不误伤（无电源/充电器产品词）
    assert not _hit("长城汽车9月销量突破13万辆，同比增长")
    # 概念股 一词单独不误伤正常板块新闻
    assert not _hit("半导体概念股集体大涨，机构看好Q4行情")
    # 正常新闻措辞不误伤
    assert not _hit("证监会召开座谈会：发展壮大耐心资本，推动加大分红回购力度")
