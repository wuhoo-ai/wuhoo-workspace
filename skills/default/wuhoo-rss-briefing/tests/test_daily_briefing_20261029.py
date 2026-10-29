# -*- coding: utf-8 -*-
"""2026-10-29 维护回归：
① fed_rate_hold — 美联储10月末按兵不动 NYT/FT/见闻/一财 跨源拆占 财经TOP1+TOP3 两榜；
② gemini_4_carbon — 谷歌发布网安专精模型 6 源不合并，且防 argon 泛分支抢判；
③ NOISE — BBC 中文"如何从五方面改变"解释性特稿连续两日占宏观 TOP。"""
from daily_briefing import entity_key, is_noise


# ── ① fed_rate_hold 合并命中 ─────────────────────────

def test_hold_英文两版命中():
    assert entity_key('Fed Holds Rates Steady Despite Lack of Progress on Inflation', '') == 'fed_rate_hold'
    assert entity_key('Fed holds fire on interest rates despite intensifying inflation', '') == 'fed_rate_hold'


def test_hold_中文按兵不动命中():
    assert entity_key('美联储按兵不动，美股指三连涨，甲骨文大涨11%，盘后谷歌大跌10%、微软走强', '') == 'fed_rate_hold'
    assert entity_key('美联储如期按兵不动，重现分歧但鹰派减少，库克等两票委支持加息', '') == 'fed_rate_hold'
    assert entity_key('美联储维持联邦基金利率3.75%-4.00%区间不变。', '') == 'fed_rate_hold'


def test_hold_反对票分支命中():
    # 第一财经快讯形态：决议+反对票，无"按兵不动"字样
    assert entity_key('美联储决议出现2张反对票 美联储政策决议投票结果为10票赞成、2票反对', '') == 'fed_rate_hold'


def test_hold_前瞻稿按兵不动无悬念并入():
    assert entity_key('今夜美联储"按兵不动"无悬念，市场选择"买入一切"（除了原油）', '') == 'fed_rate_hold'


# ── ① 防误并 ─────────────────────────────────────────

def test_hold_前夕市场综述不并():
    # "决议前夕…科技股反弹" = 决议前美股行情，独立事件
    assert entity_key('美联储决议前夕，AI热情驱动科技股反弹，CoreWeave涨8%，油价续跌，金价涨1%', '') != 'fed_rate_hold'


def test_hold_沃什削减会议次数不并():
    assert entity_key('美联储主席沃什：明年起削减议息会议次数', '') != 'fed_rate_hold'


def test_hold_决议前瞻公信力稿不并():
    assert entity_key('今夜美联储决议：通胀越烧越热，加息却按下暂停键？沃什迎来公信力大考', '') != 'fed_rate_hold'


def test_hold_加拿大央行加息无fed锚不并():
    assert entity_key('加拿大央行三年多来首次加息至2.5%', '此次加息符合市场预期') != 'fed_rate_hold'


def test_hold_置于加息规则前抢判():
    # "两票委支持加息"稿必须归 hold 组（新规则在前），不得被 fed_rate_hike 抢走
    k = entity_key('美联储如期按兵不动，重现分歧但鹰派减少，库克等两票委支持加息', '')
    assert k == 'fed_rate_hold' and k != 'fed_rate_hike'


# ── ② gemini_4_carbon 合并命中 ───────────────────────

def test_carbon_六源标题命中():
    assert entity_key('Google launches Gemini 4 Carbon with a ‘significant leap’ in cybersecurity', '') == 'gemini_4_carbon'
    assert entity_key('谷歌最强 AI 模型：Gemini 4 Carbon 登顶全球智能指数榜首，"专职"做网络安全', '') == 'gemini_4_carbon'
    assert entity_key('谷歌"网安高手"Gemini 4 Carbon登顶AI智能榜，漏洞检测得分88.2%，标准价持平Argon', '') == 'gemini_4_carbon'
    assert entity_key('Gemini 4 Carbon', '') == 'gemini_4_carbon'
    assert entity_key('Gemini 4 Carbon: Our next frontier model', '') == 'gemini_4_carbon'


def test_carbon_防argon抢判():
    # Ars 版 "Google announces Gemini 4 Carbon" 若被 argon announce 分支抢先则回归失败
    k = entity_key('Google announces Gemini 4 Carbon, its latest frontier AI model that you can', '')
    assert k == 'gemini_4_carbon' and k != 'gemini_4_argon'


def test_argon_旧规则不误捕carbon():
    # 独立验证 argon 分支文本不含 carbon 时仍正常
    assert entity_key('Gemini 4 Argon', '') == 'gemini_4_argon'


def test_carbon_无关carbon不并():
    assert entity_key('A Stationary Mean-Field Model for Carbon Market Stability Reserve', '') != 'gemini_4_carbon'
    assert entity_key('Kelp yeah: Underwater forest captures carbon', '') != 'gemini_4_carbon'


# ── ③ NOISE: BBC 中文解释性特稿 ──────────────────────

def test_noise_五方面盘点特稿():
    assert is_noise('特朗普重返白宫后，如何从五方面改变美国移民政策？')
    assert is_noise('如何從三個方面改變美國移民政策')  # 繁体变体


def test_noise_不误伤移民真新闻():
    assert not is_noise('美国南部各州将接收数万移民 联邦与州府争执移民安置')
    assert not is_noise('特朗普签署行政令收紧庇护资格 边境申请骤降六成')


def test_noise_一文了解科普栏目():
    assert is_noise('美国中期选举是什么？一文了解选举制度及重要性')
    assert is_noise('美联储是什么？一文读懂美国货币政策制定机制')
    # 防误伤：正常新闻正文措辞不含该栏目标记
    assert not is_noise('美联储决议出炉：维持利率不变 两点委反对')


# ── ④ israel_election_2026 合并命中 ──────────────────

def test_以色列选举_多波次命中():
    # DW 两阶段 (出口民调 / 持续开票) 原本各占宏观 TOP2+TOP5
    assert entity_key('Israel election: Anti-Netanyahu bloc ahead but without a majority', '') == 'israel_election_2026'
    assert entity_key('Israel election: Netanyahu-led bloc in slight lead as count continues', '') == 'israel_election_2026'
    # 中文源
    assert entity_key('出口民调显示内塔尼亚胡阵营未获议会多数，以色列组阁前景添变数', '') == 'israel_election_2026'
    assert entity_key('以色列议会选举投票结束', '以媒出口民调显示，现任总理内塔尼亚胡领导的右翼阵营未能过半') == 'israel_election_2026'
    # 英文其他源
    assert entity_key('No clear winner in Israeli parliamentary election, exit polls suggest', '') == 'israel_election_2026'
    assert entity_key("Watch: 'No clear winner' in Israel election - what happens now?", '') == 'israel_election_2026'
    # 分析稿属同事件衍生 (多波次词形覆盖先例)
    assert entity_key('Will elections in Israel change its Iran approach?', '') == 'israel_election_2026'


def test_以色列选举_防误并():
    # 军事/外交稿无选举语系不并
    assert entity_key('Israel strikes Houthi targets after rocket barrage on Eilat', '') != 'israel_election_2026'
    assert entity_key('Netanyahu visits border zone as ceasefire holds', '') != 'israel_election_2026'
