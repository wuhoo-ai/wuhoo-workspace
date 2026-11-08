# -*- coding: utf-8 -*-
"""2026-11-08 维护回归：
① NOISE 裸 '爆炸' 删除 — 实测静默杀死美军导弹击中伊朗格什姆岛全部 5 源报道簇
   ("格什姆岛传出爆炸声"/"据称，爆炸可能是美国空袭" 子串命中)。叙利亚目标由 叙利亞/叙利亞 覆盖。
② NOISE 通式 `^[a-z]{2,12} news:` — DW 国别版日更聚合栏目家族 ("Germany news: Son of Iran's
   last shah…" 占宏观 TOP4 实测)，泛化 'india news:' 单点规则；^ 锚 title 起点不误伤他源。
③ ENTITY gheshm_strikes — 格隆汇11/凤凰11/见闻/一财×2/见闻热门(特朗普证实稿) 同事件拆散。
   防误并: 击落无人机子事件 (11-05 MQM-170/11-06 MQ-1) 不并 (openai_robinson/leak 先例)。
④ classify 武装打击→宏观政策 +3 — 事件簇全 category=财经 被 +3 吞进财经后 hot11 掉榜；
   防误伤: 市场反应稿(布油暴跌万斯战事) 仍财经；财报词守卫。"""
from daily_briefing import entity_key, is_noise, classify


# ── ① 裸 '爆炸' 删除 ──

def test_爆炸词族不再静默杀遇袭报道():
    assert not is_noise('伊朗南部格什姆岛传出爆炸声，初步报告显示遭两枚导弹击中 据央视，伊朗方面消息，根据初步报告，7日凌晨两枚导弹击中了格什姆岛。伊朗官方尚未公布细节。据称，爆炸')
    assert not is_noise('伊朗南部格什姆岛传出爆炸声 伊朗南部格什姆岛传出爆炸声')
    assert not is_noise('基辅传出多次爆炸声 泽连斯基称遭导弹袭击')


def test_叙利亚爆炸目标保留():
    # 原 08-08 目标由地名词覆盖 (繁/混排/简体三种词形)
    assert is_noise('敘利亞首都大規模爆炸連環襲擊 死者過百')
    assert is_noise('叙利亚发生爆炸 多人伤亡')
    assert is_noise('叙利亞首都發生連環爆炸袭击')


# ── ② DW 国别版聚合栏目家族 ──

def test_dw_国别版聚合栏目():
    assert is_noise("Germany news: Son of Iran's last shah takes center stage in Frankfurt")
    assert is_noise("Germany news: Deportations on the decline Despite a decrease in overall deportations")
    assert is_noise('India news: protest turns violent in New Delhi')


def test_dw_正常新闻不误伤():
    assert not is_noise('Bomb threats disrupt several flights across Europe German police say')
    assert not is_noise("Trump says 'largely true' Iran war led to Republican midterm loss")
    # ^ 锚定 title 起点: 措辞出现在摘要正文中段不触发 (is_noise 文本=title+' '+summary)
    assert not is_noise('European shares join global sell-off as AI fears mount The germany news: anchor apology was')


# ── ③ ENTITY gheshm_strikes 合并 ──

def test_格什姆遇袭簇合并():
    assert entity_key('初步报告显示两枚导弹击中伊朗格什姆岛',
                      '据央视，伊朗方面消息，根据初步报告，7日凌晨两枚导弹击中了格什姆岛。伊朗官方尚未公布细节。据称，爆炸') == 'gheshm_strikes'
    assert entity_key('初步报告显示两枚导弹击中伊朗格什姆岛',
                      '总台记者7日自伊朗方面获悉，根据初步报告，当天凌晨两枚导弹击中了格什姆岛。伊朗官方尚未公布细节。据称') == 'gheshm_strikes'
    assert entity_key('伊朗南部格什姆岛传出爆炸声，初步报告显示遭两枚导弹击中',
                      '总台记者7日自伊朗方面获悉，根据初步报告，当天凌晨两枚导弹击中了格什姆岛。伊朗官方尚未公布细节。 据') == 'gheshm_strikes'
    assert entity_key('伊朗南部格什姆岛传出爆炸声', '伊朗南部格什姆岛传出爆炸声') == 'gheshm_strikes'
    # 见闻热门 特朗普证实稿: 标题 导弹击中格什姆 分支
    assert entity_key('美方对伊朗发动小规模打击！特朗普证实、伊朗称两枚导弹击中格什姆岛',
                      '特朗普称美方对伊朗实施"小型打击" 美国总统特朗普6日对媒体说，美方对伊朗实施了"小型打击"，摧毁伊') == 'gheshm_strikes'


def test_击落无人机子事件不误并():
    # 一财 11-05 击落稿 (摘要含 格什姆岛击落，击落不在打击词族)
    assert entity_key('伊朗称击落一架美军MQM-170无人机',
                      '据央视新闻，当地时间5日晚11时许，伊朗伊斯兰革命卫队表示，其在该国南部格什姆岛击落一架美军') != 'gheshm_strikes'
    assert entity_key('伊朗革命卫队称又击落一架美军MQ-1无人机',
                      '伊朗革命卫队称又击落一架美军MQ-1无人机') != 'gheshm_strikes'
    # 其他战线稿无格什姆锚
    assert entity_key('How Ukraine is adapting to Russia', "'s jet-powered drones explosions reported") != 'gheshm_strikes'


# ── ④ classify 武装打击归宏观 ──

def test_遇袭稿不再被category吞进财经():
    ct = '初步报告显示两枚导弹击中伊朗格什姆岛'
    cs = '据央视，伊朗方面消息，根据初步报告，7日凌晨两枚导弹击中了格什姆岛。伊朗官方尚未公布细节。据称，爆炸'
    assert classify(ct + ' ' + cs, '财经') == '宏观政策'


def test_市场反应稿不受影响():
    ct = '布油盘中暴跌10%，万斯直言输在伊朗战事，民主党领袖誓言阻止特朗普关税并推动停战'
    cs = '美东时间11月6日，布伦特原油盘中一度暴跌10%，市场对美伊冲突升级的定价迅速回吐'
    assert classify(ct + ' ' + cs, '财经') == '财经/投资'


def test_财报词守卫():
    ct = '防务承包商股价大涨：伊朗格什姆岛遭导弹击中，该公司营收利润双增'
    cs = '受中东局势推动，公司营收超预期，财报显示利润增长'
    assert classify(ct + ' ' + cs, '财经') == '财经/投资'
