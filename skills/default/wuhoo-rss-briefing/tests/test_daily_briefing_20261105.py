# -*- coding: utf-8 -*-
"""2026-11-05 维护回归：
① NOISE IT之家发售句式续 — "微软 329 元 Xbox Nano 迷你手柄今日开售" hot9 占科技/AI TOP5
   （旧 现已在京东/天猫 句式不覆盖"今日开售"语序，同类 米家/漫步者/机械革命）。
② NOISE IT之家供应链爆料 — "苹果 HomePod mini 2 智能音箱确认配 2GB 内存" hot12 占科技/AI TOP2
   （MacRumors 未发布产品爆料，同类 功能机曝光/rd观测）。
③ NOISE BBC Business 生态软新闻 — "Mining giant joins fight to stop killer toad march"
   hot11 占财经 TOP5（同类 白头海雕/树懒 动物特稿）。
④ NOISE BBC 中文选举解释栏目 — "民调显示民主党将取得胜利，但预测还准确吗？" hot11 占宏观 TOP4
   （栏目名式问号特稿，同类 美国经济的真实表现/一文了解）。
⑤ ENTITY amd_q3_earnings — AMD Q3 财报簇 6+ 源拆占产业 TOP3+TOP5（IT之家前三季净利9/Solidot
   营收超英特尔9/Ars record quarter 9/HN outsell Intel 9/见闻营收超预期6/苏姿丰电话会 Venice12）。
   防误并: AMD 纯产品稿、英特尔/Arm 财报稿、高通数据中心稿、中期选举市场综述稿不并。"""
from daily_briefing import is_noise, entity_key


# ── ① 今日开售句式 ──

def test_今日开售命中噪声():
    assert is_noise('微软 329 元 xbox nano 迷你手柄今日开售：隐藏功能曝光，支持 wi-fi 直连云游戏平台')
    assert is_noise('红米新款平板今日首销 1299 元')
    assert is_noise('某品牌路由器今日上架')


def test_今日开售防误伤():
    # 无  今日+发售动词 句式的真新闻不命中（库内实测标题）
    assert not is_noise('高通押注数据中心，智能手机销量下滑')
    assert not is_noise('英伟达发布新一代机器人计算平台')


# ── ② 供应链爆料 ──

def test_确认配内存爆料命中():
    assert is_noise('由 sk 海力士提供：苹果 homepod mini 2 智能音箱确认配 2gb 内存')


def test_确认配内存爆料防误伤():
    assert not is_noise('sk 海力士发布全球首款 12 层 hbm4 内存')
    assert not is_noise('美光第三季度营收创历史新高')


# ── ③ 生态软新闻 ──

def test_killer_toad命中噪声():
    assert is_noise('mining giant joins fight to stop killer toad march across australia')
    assert is_noise('queensland battles the cane toad invasion')


def test_killer_toad防误伤():
    assert not is_noise('rio tinto posts record iron ore profit')
    assert not is_noise('australia cuts interest rate for the first time this year')


# ── ④ 选举解释栏目 ──

def test_预测还准确吗命中噪声():
    assert is_noise('美国中期选举：民调显示民主党将取得胜利，但预测还准确吗？')


def test_预测还准确吗防误伤():
    # 开票结果真新闻不命中（库内实测）
    assert not is_noise('民主党横扫国会！美股债齐涨，光通信与数据中心股下挫')
    assert not is_noise('美国中期选举日，芯片股三日大跌后反弹，纳指涨0.83%')


# ── ⑤ AMD 财报簇实体合并 ──

def test_amd财报簇命中():
    # 组内成员（DB 实测 title + clean_summary[:50] 形态）
    assert entity_key('AMD 苏姿丰官宣 EPYC Venice 处理器已赚钱出货，首批 OEM 整机第四财季上市',
                      '在 2026 财年第三财季（2026 年 6 月 28 日～2026 年 9 月 26 日）财报电话') == 'amd_q3_earnings'
    assert entity_key('AMD 2026 财年前三季度报归母净利润 61.08 亿美元，同比增长 116.29%', '') == 'amd_q3_earnings'
    assert entity_key('AMD 营收预计将首次超过英特尔',
                      'AMD 周二公布了 2026 财年第三季度财报，营收同比增长 45% 达到 134 亿美元') == 'amd_q3_earnings'
    assert entity_key("AMD's record quarter: Data center business doubles, while gaming craters", '') == 'amd_q3_earnings'
    assert entity_key('AMD expects to outsell Intel in Q4 for the first time in history', '') == 'amd_q3_earnings'
    assert entity_key('未步英特尔后尘！AMD Q3营收超预期增45%，数据中心收入近翻倍，Q4指引提速又新高｜财报见闻', '') == 'amd_q3_earnings'


def test_amd财报防误并():
    # AMD 纯产品发布稿无财报锚不并
    assert entity_key('AMD 正式发布 RX 9090 显卡，定位高端游戏市场', '') != 'amd_q3_earnings'
    # 英特尔/Arm 财报稿无 amd 锚不并（苏姿丰锚不在）
    assert entity_key('英特尔第三财季营收 135 亿美元，净利润同比转正', '') != 'amd_q3_earnings'
    assert entity_key('Arm 2027 财年第二财季营收 14.4 亿美元同比增长 27% 创 Q2 历史新高，GAAP 净利润 1.30 亿美元', '') != 'amd_q3_earnings'
    # 高通数据中心稿不含 amd 锚
    assert entity_key('Qualcomm is betting big on data centers as smartphone sales sink', '') != 'amd_q3_earnings'
    # 中期选举市场综述稿含 AMD 字样但无财报锚（10-30 google_q3 市场综述排除先例）
    assert entity_key('美国中期选举日，芯片股三日大跌后反弹，纳指涨0.83%，盘后AMD大涨近8%',
                      '美股在美国中期选举投票日迎来反弹，人工智能相关板块领涨，此前持续三日的科技股抛售势') != 'amd_q3_earnings'
    # 苏姿丰个人活动稿无财报锚不并
    assert entity_key('苏姿丰确认将出席 CES 主题演讲', '') != 'amd_q3_earnings'
