# -*- coding: utf-8 -*-
"""2026-11-10 维护回归：
① ENTITY_KEYS 新增 huang_affair_scandal — 黄仁勋"疑似中国间谍婚外情"丑闻簇 40+ 篇 10+ 源无规则，
   BBC Business hot14 同事件 4 篇拆占财经 TOP2-5 四席 + 中央社 hot12 中文版拆占科技/AI TOP4
   (跨分类拆占两榜+同事件霸榜，同 10-04 g7_oil_release 教训)。双分支: 人物锚+丑闻语境词共现 /
   nvidia 锚+affair|间谍强词共现。守卫: 市场综述稿排除 (10-30 先例)；SK MOU 商务稿/日本间谍案/
   芯片出口漏洞线稿不并入。
② zelda_totk_remake 扩裸产品名强锚 时之笛|時之笛 — BBC 中文 hot11 评测"《时之笛》评测：任天堂的
   《萨尔达传说》重制版…" (词序倒装+繁体译名"萨尔达") 旧分支不覆盖，单源拆占产业 TOP1 且摘要为
   图片说明 (iphone_duo_launch 具体产品名直接锚定先例)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from daily_briefing import entity_key, is_noise


def ek(title, summary=''):
    return entity_key(title, summary[:50])


# ── ① 黄仁勋丑闻簇合并 ──

def test_bbc四篇同事件全命中():
    assert ek("Trump says FBI investigating Nvidia boss's affair with alleged Chinese spy") == 'huang_affair_scandal'
    assert ek("Nvidia shares tumble over investigation into Huang's affair with alleged Chinese spy") == 'huang_affair_scandal'
    assert ek("Zoe Kleinman: Nvidia CEO's affair will cause ripples across US and beyond") == 'huang_affair_scandal'
    assert ek("What do we know about Nvidia CEO's affair with a suspected Chinese spy?") == 'huang_affair_scandal'

def test_中央社繁体婚外情():
    assert ek("牽動全球AI命脈 黃仁勳爆婚外情調查凸顯接班危機") == 'huang_affair_scandal'

def test_道歉信备忘录():
    assert ek("Here's the full text of Jensen Huang's memo to Nvidia") == 'huang_affair_scandal'
    assert ek("英伟达黄仁勋道歉信全文：我对妻子不忠，伤害了家人，没有任何借口") == 'huang_affair_scandal'

def test_中文女间谍稿():
    assert ek("接近黄仁勋的女间谍由中国国安部招募") == 'huang_affair_scandal'
    assert ek("鲁比奥曾对黄仁勋与中国间谍的关系提出警告") == 'huang_affair_scandal'

def test_ft_allegations稿():
    assert ek("Trump says FBI is 'looking into' Nvidia's Jensen Huang",
              "US company has been rocked by allegations its chief executive had an affair") == 'huang_affair_scandal'

def test_tc_controversy稿():
    assert ek("Jensen Huang pulls out of ElevenLabs Summit amid Nvidia controversy",
              "The Nvidia CEO also pulled out of an Anthropic event earlier.") == 'huang_affair_scandal'

def test_dw_无人物锚spy_affair():
    # 分支②: nvidia 锚 + affair/spy 强词 (标题无 huang 字样)
    assert ek("Nvidia launches probe into alleged Chinese spy affair") == 'huang_affair_scandal'

def test_中方回应波次报道():
    assert ek("中国外交部回应黄仁勋婚外情风波：间谍论调纯属捕风捉影") == 'huang_affair_scandal'
    assert ek("涉嫌为中国刺探黄仁勋的黄乐何许人也？") == 'huang_affair_scandal'

def test_市场综述守卫():
    # 见闻每日市场综述提及风波但主体是行情 — 不并入 (10-30 市场综述排除先例)
    assert ek("美伊和谈信号重创原油，黄仁勋风波未阻AI交易回暖，纳指涨近3%，英伟达逆市跌超4%",
              "美伊核谈判取得进展的消息重创原油，油价大跌缓和通胀担忧") is None

def test_sk_mou商务稿不并():
    # 主体是三方 MOU 签署，"争议"仅顺带提及
    assert ek("輝達與SK電信等韓企簽MOU 未回應黃仁勳爭議",
              "輝達（NVIDIA）、SK電信及Rebellions三方今天在首爾簽署") is None

def test_芯片出口漏洞线稿不并():
    # Megaspeed/空办公室出口审查是另一调查线，无人物+丑闻共现
    assert ek("The US let Nvidia sell chips to an empty office in China",
              "Concerns are being raised that neither") is None
    assert ek("U.S. Commerce Dept. Inquiry Into Megaspeed Was Halted After Years",
              "An investigation into Megaspeed, a") is None

def test_日本间谍案他域不并():
    # 中央社日本制药员工间谍罪判决，无 huang/nvidia ceo 人物锚
    assert ek("日藥廠員工被控間諜罪遭判3年半 12月中旬出獄後料被遣返",
              "日本安斯泰來製藥（Astellas Pharma）一名60多歲日籍員工") is None

def test_火车脱轨出轨词不误伤():
    # "出軌"=脱轨 (中文交通新闻)，无锚点
    assert ek("埃及開羅以南火車追撞 數節車廂出軌至少7死112傷",
              "埃及衛生部表示，兩列客運列車今天在開羅以南約76公里處相撞") is None

def test_police_spy广告稿不并():
    assert ek("Ads in Popular Apps Give Police a Powerful Tool to Spy on Phones", "") is None


# ── ② 塞尔达时之笛评测合并 ──

def test_bbc中文时之笛评测():
    assert ek("《时之笛》评测：任天堂的《萨尔达传说》重制版是否能与原作媲美？",
              "这是新游戏的截图。角色林克穿着一套细节丰富的绿色服装") == 'zelda_totk_remake'

def test_繁体時之笛变体():
    assert ek("《薩爾達傳說 時之笛》重製版媒體評分為系列最高") == 'zelda_totk_remake'

def test_it之家旧分支仍命中():
    assert ek("《塞尔达传说：时之笛》重制版英国首发销量超《旷野之息》，登顶该国 2026 年实体游戏销量榜") == 'zelda_totk_remake'

def test_他游戏重制版不并():
    # 裸"重制"不收 — 其他游戏 remake 稿不误吸
    assert ek("最终幻想7 重制版 新增 DLC 公布", "Square Enix 宣布") is None
    assert ek("Resident Evil 4 remake sales cross 10 million", "") is None
