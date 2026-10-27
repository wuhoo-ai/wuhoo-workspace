# -*- coding: utf-8 -*-
"""2026-10-27 简报轮修复回归：NOISE 4 组 + 用户指标分类反转 + Anthropic 招股衍生稿合并 + SpaceX GPU 融资合并"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


# ── NOISE ──────────────────────────────────────────────

def test_bbc中文健康解释特稿观鸟被过滤():
    from daily_briefing import is_noise
    assert is_noise('观鸟如何重塑大脑，延缓认知衰退？ 一幅手绘风格插图显示两名人士')


def test_ai红利贩卖焦虑软文被过滤():
    from daily_briefing import is_noise
    assert is_noise('35 岁不会写代码？这波 AI 红利，可能就轮到你了')


def test_访谈观点稿被过滤():
    from daily_briefing import is_noise
    assert is_noise('SemiAnalysis创始人深度解析：AI投资还能撑多久？英伟达护城河还能守住吗？')
    assert is_noise('某机构创始人深度解析：市场底部到了吗')


def test_verge促销导购措辞被过滤():
    from daily_briefing import is_noise
    assert is_noise("Samsung's Switch 2-ready MicroSD Express card is on sale for less than $50")


# ── classify 反转 ──────────────────────────────────────

def test_netflix用户指标归产业不归宏观():
    from daily_briefing import classify
    t = ('Netflix 用户观看量下降，应用打开量下降 流媒体巨头 Netflix 正通过提高订阅费用去应对'
         '用户增长停滞。内部数据显示，Netflix 订户')
    assert classify(t, '科技') == '产业/公司'


def test_真宏观经济稿不受用户指标规则影响():
    from daily_briefing import classify
    t = '欧元区经济陷入衰退风险上升，欧盟委员会下调增长预期，通胀仍高于目标'
    assert classify(t, '综合') == '宏观政策'


# ── Anthropic 招股衍生稿合并 ────────────────────────────

def test_招股书生态打法衍生稿并入ipo事件():
    from daily_briefing import entity_key
    ek = entity_key('Anthropic 招股书披露生态打法：打造高粘性企业客户体系',
                    'Anthropic 正在打造一套跨产品生态，正是这类生态让亚马逊、优步等科技企业拥有极强的用户粘性，')
    assert ek == 'anthropic_ipo_pitch'


def test_q3营收稿仍归q3_revenue不被ipo抢判():
    # q3_revenue 规则在 ipo 之前，顺序保障
    from daily_briefing import entity_key
    ek = entity_key('Anthropic 第三季度营收达168亿美元，同比增长50%', '上半年净亏损…')
    assert ek == 'anthropic_q3_revenue'


def test_无关招股稿不误并():
    from daily_briefing import entity_key
    assert entity_key('某芯片公司招股书今日上市，募资 20 亿元', '') != 'anthropic_ipo_pitch'


# ── SpaceX GPU 融资合并 ────────────────────────────────

def test_spacex_gpu融资三变体同事件():
    from daily_briefing import entity_key
    assert entity_key('SpaceX 达成史上最大规模 GPU 融资安排，协议总额约 400 亿美元', '') == 'spacex_gpu_financing'
    assert entity_key('马斯克确认 SpaceX 完成 400 亿美元债务融资，用于购买 GPU', '') == 'spacex_gpu_financing'
    assert entity_key('SpaceX locks in $40B GPU financing deal with Apollo', '') == 'spacex_gpu_financing'


def test_spacex无关稿不误并():
    from daily_briefing import entity_key
    assert entity_key("Musk says SpaceX restricted Ukraine's Starlink connection as service resumed", '') != 'spacex_gpu_financing'
    assert entity_key('SpaceX: Ramping Up CapEx Risk', '') != 'spacex_gpu_financing'
    assert entity_key('Meta and SpaceX to Raise Billions More to Fund A.I. Ambitions', '') != 'spacex_gpu_financing'


def test_spacex财报稿仍归earnings():
    from daily_briefing import entity_key
    assert entity_key('SpaceX Q3 营收 145.8 亿美元，同比增长 161%', '') == 'spacex_q3_earnings'
