# -*- coding: utf-8 -*-
"""2026-11-09 维护回归：
① NOISE 漫步者发售动词表补 '上架' + 通式 `上架[：:]\\s*限量` — "漫步者 W900NB 30 周年典藏版
   头戴蓝牙耳机上架：限量 3000 套，1159 元" (hot6 占产业/公司 TOP1，旧枚举动词表不覆盖
   冒号+限量+标价发售句式，品牌枚举追赶教训同 10-18 改句式通式)。
② NOISE `clearing his own name` — TechCrunch "He arrested a hacker, then spent 18 months
   clearing his own name. Now he's a cybersecurity VC." (hot9 占科技/AI TOP4，前特工筹基金
   人物特稿非新闻事件，同类 importance of failure/创始人深度解析)。
③ classify 武装打击词族扩军事行动措辞 — "美中央司令部成立特遣队，阻止伊朗通过陆路运输先进
   武器" (见闻11/一财3 全 category=财经，伊朗+武器 各计 1 分不敌 +3 被吞进 财经/投资 TOP4；
   地缘军事行动属宏观，格什姆岛语境反转同族)。防误伤: 游戏入库稿无行动语境、财报词守卫。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from daily_briefing import is_noise, classify


# ── ① 漫步者/上架限量发售句式 ──

def test_漫步者上架发售稿():
    assert is_noise('漫步者 W900NB 30 周年典藏版头戴蓝牙耳机上架：限量 3000 套，1159 元 漫步者 W900NB 30 周年典藏版头戴蓝牙耳机')


def test_冒号限量句式通捕其他品牌():
    # 品牌枚举外新品牌同句式照样捕 (冒号+限量=发售促销稿特征)
    assert is_noise('某新品牌机械键盘典藏版上架：限量 500 套，699 元')


def test_上架词正常新闻不误伤():
    # 无 冒号+限量 组合、非漫步者品牌 → 不触发
    assert not is_noise('小米汽车北京工厂新车上架首周订单破万，官方公布产能规划')
    # 漫步者财报真新闻 (品牌枚举只匹配发售动词表)
    assert not is_noise('漫步者三季度财报：营收同比增长 12%，净利润创年内新高')


# ── ② TechCrunch 人物特稿 ──

def test_人物经历特稿噪声():
    assert is_noise("He arrested a hacker, then spent 18 months clearing his own name. Now he's a "
                    "Stephen Ward, a former Secret Service agent and Home Depot CISO, is preparing")


def test_clearing正常措辞不误伤():
    assert not is_noise('Anthropic says it is clearing regulatory hurdles ahead of its IPO filing')


# ── ③ 军事行动→宏观政策 ──

def test_中央司令部特遣队归宏观():
    # 真实流水线文本形态: clean_title + clean_summary[:50]
    text = ('美中央司令部成立特遣队，阻止伊朗通过陆路运输先进武器 当地时间11月7日，美国中央司令部司令库珀下令'
            '成立一支名为"铁门"（Task Force Iron Gate）的特遣队，旨在配合美国政府正在开展')
    assert classify(text, '财经') == '宏观政策'


def test_伊朗武器运输英文稿归宏观():
    text = 'Pentagon blocks Iran weapons shipments US Central Command orders a new task force'
    assert classify(text, '财经') == '宏观政策'


def test_游戏入库稿不被军事行动词族拉走():
    # PS+ 游戏阵容稿: 无 成立特遣队/阻止 语境
    text = '索尼宣布《刺客信条》入列 PS+ 一档游戏库 本次一档会免游戏共三款，自 7 月 7 日起开放领取'
    assert classify(text, '科技') != '宏观政策'


def test_军工财报稿守卫不误拉宏观():
    # 财报词守卫: 防务承包商遇袭/武器订单财报稿仍落原分类
    text = 'Northrop遭空袭传闻后股价波动，公司回应：Q3 earnings 营收利润均超预期'
    assert classify(text, '财经') != '宏观政策'
