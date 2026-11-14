# -*- coding: utf-8 -*-
"""2026-11-14 维护回归：
① ENTITY_KEYS 新增 microsoft_outage — 11-13 微软 M365/Outlook/Teams 全球宕机 (BBC Business×2/DW×4/
   IT之家×4/Ars/TC×2/NYT×3/Engadget×2/Solidot/HN×2/卫报/Verge/BBC World/一财 15+ 源 25 篇)。
   无规则时拆占 科技/AI TOP4 + 财经 TOP3 + 财经 TOP4 跨榜，BBC 同厂两篇霸榜、[N源] 失效。
   IT之家 hot12「Anthropic 连发多条故障通报：微软服务中断波及 Claude」为该事件衍生报道，
   规则必须置于 ai_service_outage 之前否则被 09-04 四大AI宕机组吞并 (10-01/10-22 抢判教训链)。
   防误并: 微软财报/产品稿无宕机语系不并；09-04 四大宕机簇无微软服务锚仍归旧组。
② NOISE 新增: BBC 中文解释性特稿变体「如何影响你的」("中美能源大战，如何影响你的帐单？" hot19
   占宏观 TOP1，摘要仅图片说明无正文，同类 美国经济的真实表现/预测还准确吗/如何从N方面)；
   虎嗅观点评论体「刷屏背后」(腾讯"裁员50%"谣言评论文 hot6 占产业 TOP5，同类 何处是底/
   若是反弹还没来/最担心的事情发生/投资逻辑彻底变)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from daily_briefing import entity_key, is_noise


def ek(title, summary=''):
    return entity_key(title, summary[:50])


# ── ① microsoft_outage 命中 ──

def test_outage英文主稿命中():
    assert ek("Microsoft 'deeply sorry' for global outage after almost 24 hours of disruption",
              "Experts say the event is a stark reminder of how") == 'microsoft_outage'
    assert ek("Why is Microsoft's outage lasting so long and will emails be lost?",
              "Microsoft says it is continuing to restore service") == 'microsoft_outage'
    assert ek("Microsoft rules out 'malicious activity' as cause for global outage",
              "A Microsoft outage disrupted Outlook and Teams wor") == 'microsoft_outage'
    assert ek("Outlook, Teams and More Microsoft Programs Disrupted by Outage",
              "") == 'microsoft_outage'
    assert ek("Microsoft’s global outage may be worse than Amazon's or CrowdStrike's, expert says",
              "") == 'microsoft_outage'
    assert ek("Ask HN: Microsoft/Azure Outage?", "") == 'microsoft_outage'
    assert ek("Microsoft’s latest email outage turned into a full-blown global cloud crisis",
              "") == 'microsoft_outage'
    assert ek("Multiple Microsoft 365 services are experiencing an outage",
              "") == 'microsoft_outage'


def test_outage中文稿命中():
    assert ek("微软云服务全球宕机", "") == 'microsoft_outage'
    assert ek("微软：没有迹象表明全美国航班停飞与 M365 服务宕机有关",
              "") == 'microsoft_outage'
    assert ek("大规模故障殃及全球多地多行业，微软确认主要软件服务恢复工作已取得进展",
              "") == 'microsoft_outage'
    assert ek("微软就全球服务中断道歉 称故障非网络攻击所致",
              "当地时间11月13日，微软公司就导致数百万用户受影响的全球性服务中断事件深表歉意") == 'microsoft_outage'


def test_outage衍生claude稿抢判防吞():
    # 规则顺序回归: claude+故障 同句若无 microsoft_outage 在前会被 ai_service_outage 吞并
    assert ek("Anthropic 连发多条故障通报：微软服务中断波及 Claude",
              "11月13日，微软多个云服务出现宕机") == 'microsoft_outage'


# ── ② microsoft_outage 防误并 ──

def test_微软财报产品稿不并():
    assert ek("Microsoft Q3 cloud revenue beats estimates as shares rise",
              "Azure grew 30 percent year over year") != 'microsoft_outage'
    assert ek("微软发布全新Surface笔记本 搭载自研芯片",
              "起售价 12888 元") != 'microsoft_outage'
    assert ek("Microsoft Teams gets new Copilot translation features",
              "The productivity app adds real-time captions") != 'microsoft_outage'


def test_四大ai宕机仍归旧组():
    # 09-04 事件无微软服务锚 → 不被 microsoft_outage 吞
    assert ek("OpenAI, Claude, Grok and Gemini suffer simultaneous downtime",
              "") != 'microsoft_outage'
    assert ek("四大 AI 模型服务同时下线", "ChatGPT 与 Claude 几乎同时出现") != 'microsoft_outage'


# ── ③ NOISE 命中与防误伤 ──

def test_bbc解释特稿噪声():
    assert is_noise("中美能源大战，如何影响你的帐单？ 一张经过处理的图片，左上角显示一台石油钻孔机")
    # 防误伤: 正常能源新闻标题不含该句式
    assert not is_noise("美国天然气出口禁令延长 欧洲能源价格再涨")


def test_虎嗅观点体噪声():
    assert is_noise("腾讯“裁员50%”刷屏背后，其实是时代的悲哀 腾讯内部用陆军海军比喻资源配置")
    # 防误伤: 含“刷屏”的正常事件稿
    assert not is_noise("iPhone 18 Pro 评测刷屏各大科技媒体")


def test_影视文化回顾特稿噪声():
    assert is_noise("“可惜你不是中国人”医生一句话，逼出了美国版《我不是药神》 2018年，《我不是药神》成了中国影坛的现象级爆款")
    # 防误伤: 医药行业正常新闻不含该电影名
    assert not is_noise("仿制药集采新规落地 慢性病患者药费下降四成")
