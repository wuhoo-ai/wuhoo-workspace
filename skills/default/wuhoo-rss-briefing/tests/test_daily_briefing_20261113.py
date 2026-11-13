# -*- coding: utf-8 -*-
"""2026-11-13 维护回归：
① ENTITY_KEYS 新增 huang_resign 独立建组 — 11-12 晚"黄仁勋辞职"事件高潮 (DW14/BBC Business14/
   BBC World14 "Jensen Huang resigns/quits as Nvidia CEO" + FT6 + 中央社 辭輝達執行長/離任/去職 +
   IT之家 即刻生效/临时CEO克雷斯/库克接任/市值失守 + 见闻 声明全文/离任震动AI + TechCrunch successor/
   interim + Engadget/Verge/卫报/BBC中文接替 + 虎嗅/凤凰/纽约时报中文 衍生稿 60+ 篇)。
   无规则时 BBC World14 与 DW14 独立拆占科技/AI TOP2-3 且视频简介残句顶替摘要。
   与"董事会准备罢免"(11-11 波次 huang_oust)、"婚外情丑闻认知"(huang_affair_scandal) 分事件建组
   (11-12 新波次独立建组教训 + 10-05 resign/firings 分开教训)；规则置于 huang_oust/scandal 之前。
   市场综述守卫: 见闻14 "黄仁勋辞职叠加油价走强…美债、黄金遭抛售" 行情稿排除 (09-15 Sacks 推文
   代表位决策同构)；防误并: Indonesia VP resigns 无人物锚、third affair→丑闻、Ousted CEO 讣告稿→罢免。
② NOISE 新增: 影视预告片宣传稿 (Ars "Netflix releases new trailer for Ray Gunn" hot6 占产业 TOP5,
   同类 watch the trailer)；卫报美国日更栏目 The Daily ("Thursday briefing: ..." 栏目聚合稿,
   同类 早餐FM/india news:/europe live)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from daily_briefing import entity_key, is_noise


def ek(title, summary=''):
    return entity_key(title, summary[:50])


# ── ① huang_resign 命中 ──

def test_resign英文主稿命中():
    assert ek("Jensen Huang resigns as Nvidia CEO",
              "Jensen Huang has resigned from his role as the head of Nvidia") == 'huang_resign'
    assert ek("Scandal-hit Nvidia CEO Jensen Huang quits, plunging AI chipmaking giant into crisis",
              "US lawmakers now want to question Huang") == 'huang_resign'  # 先于 scandal
    assert ek("Jensen Huang has resigned, what's next for Nvidia?",
              "The BBC's Samira Hussain reports from Wall Street") == 'huang_resign'
    assert ek("Jensen Huang resigns as Nvidia chief executive",
              "Shares in chipmaker slide after group sa") == 'huang_resign'
    assert ek("Jensen Huang is gone. Will the AI industry pay the price?",
              "Nvidia chief’s fall could unravel the we") == 'huang_resign'
    assert ek("Jensen Huang is out as NVIDIA CEO",
              "He has held the position since the compa") == 'huang_resign'
    assert ek("Nvidia CEO Jensen Huang resigns after reports of second affair deepened scandal",
              "") == 'huang_resign'  # oust+resign 双词语境归属辞职本身

def test_resign继任衍生稿命中():
    assert ek("Meet the contenders to succeed Jensen Huang",
              "From chief executives of rival companies") == 'huang_resign'
    assert ek("Who Is Colette Kress, the Interim Nvidia CEO Replacing Jensen Huang?",
              "Ms. Kress, the company’s chief financial") == 'huang_resign'
    assert ek("Trump floats Apple chairman Tim Cook as Jensen Huang’s successor",
              "In a post on Truth Social, President Tru") == 'huang_resign'  # cook 规则不抢先
    assert ek("Who could replace the departed Jensen Huang as Nvidia CEO?",
              "The search for a successor is on") == 'huang_resign'
    assert ek("‘It’s a mistake’: reactions from tech leaders on Jensen Huang’s resignation",
              "Nvidia announced this morning that Jense") == 'huang_resign'

def test_resign中文命中():
    assert ek("即刻生效！黄仁勋辞去英伟达总裁、首席执行官和董事会成员职务",
              "英伟达董事会今日宣布，黄仁勋辞去总裁、首席执行官及董事会成员职务，即刻生效") == 'huang_resign'
    assert ek("黄仁勋辞职后，特朗普呼吁苹果执行董事长库克接任英伟达 CEO",
              "黄仁勋离任英伟达 CEO 后，美国总统特朗普随即呼吁苹果执行董事长蒂姆") == 'huang_resign'
    assert ek("英伟达关于黄仁勋辞职及领导团队调整的声明全文",
              "英伟达董事会12日宣布，黄仁勋已辞去总裁、首席执行官及董事会成员职务") == 'huang_resign'
    assert ek("黄仁勋突然离任震动AI行业！英伟达大跌、新云与硬件承压、AMD大涨，Anthropic IPO受审视",
              "英伟达创始人、首席执行官黄仁勋突然离任，全球AI产业迎来重大领导层变局") == 'huang_resign'
    assert ek("黄仁勋辞任 CEO 后，英伟达任命执行副总裁兼首席财务官科莱特 · 克雷斯为临时首席执行官",
              "黄仁勋辞去总裁、首席执行官及董事会成员职务后，英伟达任命执行副总裁") == 'huang_resign'
    assert ek("黄仁勋辞任英伟达CEO，公司首席财务官克雷斯临时接任") == 'huang_resign'
    assert ek("特朗普回应黄仁勋辞职：能接替他的人只有库克",
              "当地时间11月12日，美国总统特朗普在") == 'huang_resign'
    assert ek("谁会接替黄仁勋，正式出任Nvidia执行长？") == 'huang_resign'
    assert ek("黄仁勋辞职后续：美国司法部对英伟达启动多项调查，包括反垄断调查",
              "据 Semafor 当地时间 11 月 12 日报道") == 'huang_resign'

def test_resign繁体命中():
    assert ek("黃仁勳辭輝達執行長　科技界憂創新領導力流失") == 'huang_resign'
    assert ek("黃仁勳辭執行長並退出董事會　AI巨擘輝達前景添變數") == 'huang_resign'
    assert ek("黃仁勳離任　衝擊全球AI產業與改變美晶片輸出政策") == 'huang_resign'
    assert ek("黃仁勳去職　美專家：輝達仍是AI產業支柱、不影響台積電",
              "「AI教父」黃仁勳身陷婚外情醜聞，今天辭去輝達執行長一職，並退出董事會") == 'huang_resign'


# ── ② 防误并/防误伤回归 ──

def test_resign无人物锚不命中():
    assert ek("Indonesia's vice president resigns amid signs ruling alliance is fraying",
              "Ma'ruf Amin's departure risks prolonging political deadlock") != 'huang_resign'

def test_resign市场综述守卫():
    # 见闻14 行情综述稿不得进辞职组 (若不排除，hot14+CJK 优先会夺组代表位顶替主事件标题)
    assert ek("黄仁勋辞职叠加油价走强，美股承压，英伟达市值一度跌破4万亿，美债、黄金遭抛售",
              "英伟达掌门人突然出局，叠加油价走强推高通胀预期，美国股市、债市、黄金和比特币同步") != 'huang_resign'

def test_resign丑闻波次不吞():
    assert ek("Jensen Huang was having a third affair, Reuters reports") == 'huang_affair_scandal'
    assert ek("Jensen Huang Said to Have Had Relationship With Nvidia Executive Who Reports to Him",
              "Mr. Huang, Nvidia’s chief executive, is already fa") == 'huang_affair_scandal'

def test_resign罢免波次不吞():
    assert ek("Nvidia board prepares to oust CEO Jensen Huang — reports",
              "Nvidia's board is reportedly preparing t") == 'huang_oust'
    assert ek("Jensen Huang, Nvidia’s Ousted CEO, Was the Face of the A.I. Boom Powering the",
              "Nvidia’s ousted leader was a unique rhet") == 'huang_oust'
    assert ek("Nvidia’s stock drops as board reportedly preps to oust CEO Jensen Huang",
              "As soon as Wednesday evening, Nvidia's board could") == 'huang_oust'
    assert ek("輝達11人董事會深夜討論黃仁勳去留　若過半同意即可撤職") != 'huang_resign'


# ── ③ NOISE 新增 ──

def test_noise预告片宣传稿():
    assert is_noise("Netflix releases new trailer for Ray Gunn It's hard being the only honest players")
    assert is_noise("watch the trailer for the new season")

def test_noise卫报thursday_briefing栏目():
    assert is_noise("Thursday briefing: What we do (and don’t) know about Alice Huang and the Nvidia scandal")

def test_noise不误伤正常trailer措辞():
    # 不含 "releases new trailer/new trailer for" 句式的事件稿不受影响
    assert not is_noise("Nvidia releases Q3 earnings as CEO resigns")


# ── ④ classify: resign 主事件归 科技/AI (Hassabis 08-09 FT category=财经 同构) ──

def test_resign主事件分类():
    from daily_briefing import classify
    assert classify("Scandal-hit Nvidia CEO Jensen Huang quits, plunging AI chipmaking giant into turmoil"
                    " US lawmakers now want to question Huang", '财经') == '科技/AI'
    # 行情综述稿不翻转 (resign 守卫排除, 无 entity 判定)
    assert classify("黄仁勋辞职叠加油价走强，美股承压，英伟达市值一度跌破4万亿，美债、黄金遭抛售"
                    " 英伟达掌门人突然出局，叠加油价走强推高通胀预期", '财经') != '科技/AI'
    # 丑闻组代表不受影响
    assert classify("Jensen Huang Said to Have Had Relationship With Nvidia Executive Who Reports to Him"
                    " Mr. Huang, Nvidia’s chief executive, is already fa", '财经') == '财经/投资'
