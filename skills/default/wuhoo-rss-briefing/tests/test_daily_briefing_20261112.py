# -*- coding: utf-8 -*-
"""2026-11-12 维护回归：
① huang_affair_scandal 扩词形 — NYT hot14 "Jensen Huang Said to Have Had Relationship With
   Nvidia Executive Who Reports to Him" 标题与截断摘要均无旧语境词，独立拆占财经 TOP3 与
   宏观 TOP2 [20源] 丑闻簇跨榜重复 (09-30/10-10 多波次词形覆盖教训)。补 relationship|suing|
   lawsuit|诉讼 波次词 + 人物锚中文 英伟达CEO 变体 (格隆汇警示稿) + C.E.O. 点号变体
   (NYT Spycraft 稿，09-09 点号保留先例)。
② ENTITY_KEYS 新增 huang_oust 独立建组 — 11-11 晚"董事会准备罢免黄仁勋"新波次
   (TechCrunch/Verge/DW/HN/见闻/格隆汇×2/NYT Allies/纽约时报中文治理+惩罚稿/CNN 能否生存)。
   与丑闻认知稿分事件 (10-05 OpenAI resign/firings 两事件分开教训)；置于 scandal 规则之前。
   防误并: APEC 随行稿、市场综述稿、券商降级稿、DLSS 产品稿、firewall 词边界均拦截。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from daily_briefing import entity_key, is_noise, PRIORITY_EVENTS


def ek(title, summary=''):
    return entity_key(title, summary[:50])


# ── ① 丑闻簇后续波次词形 ──

def test_scandal新词形命中():
    assert ek("Jensen Huang Said to Have Had Relationship With Nvidia Executive Who Reports to Him",
              "Mr. Huang, Nvidia’s chief executive, is already fa") == 'huang_affair_scandal'
    assert ek("NVIDIA shareholders are suing the company and CEO Jensen Huang",
              "The company's shares have plummeted in response to") == 'huang_affair_scandal'
    assert ek("｜市场消息：美国商务部此前曾就英伟达CEO婚外情一事收到警示。") == 'huang_affair_scandal'
    assert ek("Secrets, Chips and Spycraft: The Nvidia C.E.O. Scandal",
              "Despite knowing about the relationship between one") == 'huang_affair_scandal'


def test_scandal旧成员回归():
    assert ek("黄仁勋与疑似中国间谍婚外情：目前我们知道什么？") == 'huang_affair_scandal'
    assert ek("Nvidia launches probe into alleged Chinese spy affair") == 'huang_affair_scandal'
    assert ek("Nvidia CEO's alleged affair with Chinese spy has morphed into a Washington scandal") == 'huang_affair_scandal'


# ── ② 罢免波次独立建组 ──

def test_oust英文命中():
    assert ek("Nvidia's stock drops as board reportedly preps to oust CEO Jensen Huang",
              "As soon as Wednesday evening, Nvidia's board could") == 'huang_oust'
    assert ek("Nvidia is reportedly preparing to fire Jensen Huang",
              "Nvidia's board is preparing to dismiss CEO Jensen") == 'huang_oust'
    assert ek("Nvidia prepares to push out CEO Jensen Huang, reports") == 'huang_oust'
    assert ek("Nvidia Is Preparing to Oust Nvidia CEO Jensen Huang") == 'huang_oust'
    assert ek("Silicon Valley Tech Allies Support Jensen Huang",
              "Elon Musk and other Silicon Valley figures cast th") == 'huang_oust'


def test_oust中文命中():
    assert ek("突发！英伟达盘后跳水8%，董事会今天或罢免黄仁勋") == 'huang_oust'
    assert ek("AI相关股票盘后下挫 英伟达据报计划罢免黄仁勋") == 'huang_oust'
    assert ek("｜据哥伦比亚广播公司新闻记者在X平台上发布的消息，特朗普政府已获悉，英伟达董事会正准备很快罢免首席执行官黄仁勋。") == 'huang_oust'
    assert ek("CNN探討輝達失去黃仁勳能否生存　專家評估仍具優勢") == 'huang_oust'
    assert ek("顺从的董事会：黄仁勋危机考验英伟达公司治理") == 'huang_oust'


# ── 防误并 ──

def test_oust防误并():
    # APEC 随行独立事件 (无罢免词)
    assert ek("南早：馬斯克隨川普赴深圳APEC　黃仁勳有變數") is None
    assert ek("港媒：马斯克料随特朗普参加APEC 黄仁勋是否随行存疑") is None
    # 市场综述守卫
    assert ek("美CPI超预期叠加美联储放鹰，美债重挫，美股指承压，英伟达两日跌10%，黄金大跌") is None
    assert ek("英伟达继续大跌，两日市值蒸发4300亿美元，微软一度重夺全球第二") is None
    # 券商动作稿无罢免语境
    assert ek("Baird調降輝達股票評等至「中立」　目標價大砍60%") is None
    assert ek("美银之后，大摩也将英伟达移除“首选股”名单！") is None
    # 产品稿无人物锚
    assert ek("NVIDIA DLSS 4.5 has presets you should know about") is None
    # MOU 商务稿旧拦截
    assert ek("輝達與SK電信等韓企簽MOU　未回應黃仁勳爭議") is None
    # fire 词边界: firewall 不命中罢免波次
    assert ek("Nvidia CEO Jensen Huang explains new firewall feature") is None


# ── ③ Odessia 收购中英双版合并 + 灰熊噪声 + 罢免保底 ──

def test_odessia合并():
    assert ek("OpenAI 收购旅游初创公司 Odessia，探索 AI 旅行智能体业务") == 'openai_odessia_acq'
    assert ek("OpenAI acquires Odessia, travel startup created by Sonder founder",
              "OpenAI has not yet said what its plans are for the") == 'openai_odessia_acq'


def test_灰熊动物伤人噪声():
    assert is_noise("canada: 4 bears put down after killing mother, daughter authorities put down a female grizzly")
    assert not is_noise("european stocks rebound as investors weigh fed outlook inflation data")


def test_罢免保底规则命中():
    rx = [p for p, t in PRIORITY_EVENTS if t == '产业/公司' and 'huang' in p.pattern.lower() or '黄仁勋' in p.pattern][0]
    assert rx.search("Nvidia is reportedly preparing to fire Jensen Huang "
                     "Nvidia's board is preparing to dismiss CEO Jensen Huang")
    assert rx.search("突发！英伟达盘后跳水8%，董事会今天或罢免黄仁勋 黄仁勋相关")
    assert not rx.search("美CPI超预期叠加美联储放鹰，美债重挫，美股指承压，英伟达两日跌10% 黄金大跌 通胀")
