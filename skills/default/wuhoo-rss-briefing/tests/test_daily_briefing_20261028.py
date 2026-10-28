# -*- coding: utf-8 -*-
"""2026-10-28 维护回归：卢拉巴西大选逆转胜 30+ 源跨 财经TOP4+宏观TOP4 两榜拆占 → brazil_lula_election 实体级合并。"""
from daily_briefing import entity_key


# ── 合并命中 ─────────────────────────────────────────

def test_卢拉胜选中英文变体同事件():
    assert entity_key('卢拉逆袭吓坏巴西市场：股指跌超10%、部分个股跌60%', '') == 'brazil_lula_election'
    assert entity_key('Lula wins fourth term in dramatic Brazil election comeback', '') == 'brazil_lula_election'
    assert entity_key('Brazil elections: world leaders congratulate Lula on his win', '') == 'brazil_lula_election'
    assert entity_key("Brazil’s currency plunges most since 1999 after Lula’s surprise victory", '') == 'brazil_lula_election'


def test_繁体与赢得词形命中():
    # BBC 中文"第四次赢得大选"摘要为空，靠 赢得 词锚
    assert entity_key('巴西总统卢拉：北京在美国后院的"老朋友"第四次赢得大选', '') == 'brazil_lula_election'
    # 一财 承认胜选稿
    assert entity_key('巴西自由党主席承认卢拉赢得总统选举', '') == 'brazil_lula_election'
    # NYT 摘要 re-election 词形
    assert entity_key('Brazilian Markets Convulse After Unexpected Election Result',
                      "President Luiz Inácio Lula da Silva's re-election") == 'brazil_lula_election'


def test_衍生报道并入():
    # 祝贺稿（联合早报：锚"卢拉胜选"+中巴）
    assert entity_key('中国祝贺卢拉胜选', '愿持续推进中巴命运共同体建设，深化巴西合作') == 'brazil_lula_election'
    # 朝鲜日报 逆风翻盘
    assert entity_key('81岁卢拉，巴西选举逆风翻盘…中南美"亲特朗普右转"被踩下刹车', '') == 'brazil_lula_election'


# ── 防误并 ─────────────────────────────────────────

def test_博索纳罗出走独立事件不并():
    # 败方候选人拒交护照/逃亡美国 = 独立事件簇（无 lula 锚）
    assert entity_key('Brazil: defeated Flávio Bolsonaro ordered to surrender passport',
                      'Far-right senator banned from leaving country') != 'brazil_lula_election'
    assert entity_key('路透：小波索納洛拒交護照　巴西大選落敗後赴美',
                      '兩名消息人士表示，巴西參議員佛拉維歐．波索納洛在25日') != 'brazil_lula_election'


def test_meta员工抗议不并():
    # 另一事件：员工内部备忘录抗议干预巴西大选（无 lula 锚 + 无胜选语境）
    assert entity_key('Meta Employees Denounce Interference in Brazilian Elections', '') != 'brazil_lula_election'


def test_关税争执不误并():
    # lula+巴西 共现但无胜选语系 → 不命中（单字'赢'仍受三锚约束）
    assert entity_key('特朗普关税与卢拉争执升级 巴西威胁报复', '双方围绕贸易问题的对抗') != 'brazil_lula_election'
