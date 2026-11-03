# -*- coding: utf-8 -*-
"""2026-11-03 维护回归：
① apple_q4_earnings — 苹果 2026 财年 Q4 财报跨分类拆榜：The Verge 英文 "Apple set an iPhone sales
   record" 占科技/AI TOP1 vs IT之家 "苹果最强第四财季 [3源]" 占产业 TOP2，FT/SA/见闻/凤凰网 10+ 源分散；
   防误并: iPhone Duo 交货延迟稿/MacBook Neo 订单稿/FT memory chip 稿无财报锚不并；
   抢判教训: "特努斯掌舵后首份财报"必须归 earnings 而非 apple_ceo_transition。
② meta_fourier_robot — Meta×傅利叶人形机器人原型 中英文拆散 (Engadget vs 见闻/IT之家)，
   须置于 meta_muse 系规则之前（IT之家标题含 "Muse 模型的物理化身"）。
③ kherson_ceasefire — 赫尔松/奥列什基停火结束 6-8 源同榜拆散 (DW11 宏观TOP1 + BBC中文 宏观TOP5)，
   专名强锚含繁体"赫松" (08-10 繁体教训)。
④ NOISE: 何处是底(见闻抽象观点稿占财经TOP5) / 弗拉维奥为何飞往美国(BBC中文人物解释特稿占宏观TOP2)
   / 翻盖功能机曝光(IT之家爆料稿占科技TOP3) / Europe live(卫报直播聚合栏目)。"""
from daily_briefing import entity_key, is_noise


# ── ① apple_q4_earnings ──

def test_苹果财报_英文verge命中():
    assert entity_key('Apple set an iPhone sales record even without a new standard iPhone',
                      'Apple had a record-breaking quarter for iPhone sal') == 'apple_q4_earnings'


def test_苹果财报_中文各源命中():
    assert entity_key('苹果 2026 财年归母净利润 1321.75 亿美元同比增长 18% 大中华区净销售额增长', '') == 'apple_q4_earnings'
    assert entity_key('苹果涨价后的首个财报：2026 财年第四财季 iPhone 营收暴增 17% 创纪录', '') == 'apple_q4_earnings'
    assert entity_key('苹果上季营收盈利均超预期，但毛利率收窄、在华业绩逊色 | 财报见闻', '') == 'apple_q4_earnings'
    assert entity_key('苹果最新财报：销售额符合预期，但中国市场表现疲软', '') == 'apple_q4_earnings'
    assert entity_key('苹果电话会：中国市场"有很大动能"，高管明确AI商业化路径', '') == 'apple_q4_earnings'
    assert entity_key('Apple Q4: Record Earnings, Broken Expectations - I am Downgrading', '') == 'apple_q4_earnings'


def test_苹果财报_不抢换任规则():
    # "特努斯掌舵后首份财报" 含特努斯，规则顺序必须让 earnings 先命中
    assert entity_key('苹果最强第四财季：特努斯掌舵后首份财报，交出创纪录成绩单',
                      '苹果 2026 财年第四财季营收') == 'apple_q4_earnings'


def test_苹果财报_防误并非财报稿():
    assert entity_key('苹果承认 iPhone Duo 折叠屏手机交货延迟，供货紧张何时缓解仍难以预测', '') == 'iphone_duo_launch'
    assert entity_key('拿下 17 万台订单：MacBook Neo 成为苹果瞄准教育市场的新王牌', '') != 'apple_q4_earnings'
    assert entity_key('Apple warns on rising costs from memory chip shortage', '') != 'apple_q4_earnings'
    assert entity_key("Apple's inventory surges 154% as memory chip costs climb", '') != 'apple_q4_earnings'
    assert entity_key('The Apple Watch Ultra 4 is $100 off, matching its best price to date', '') != 'apple_q4_earnings'


def test_苹果财报_不抢库克访华():
    assert entity_key('何立峰會見蘋果庫克 探討經貿合作', '') == 'cook_china_visit'


# ── ② meta_fourier_robot ──

def test_meta机器人_英文命中():
    assert entity_key('Meta reportedly built a humanoid robot prototype that can do household chores',
                      'A report said the company is already working on th') == 'meta_fourier_robot'


def test_meta机器人_中文含muse字样不抢判():
    assert entity_key('已进入第二版！傅里叶帮Meta研发机器人原型，打造"Muse物理化身"', '') == 'meta_fourier_robot'
    assert entity_key('消息称 Meta 与中国企业傅利叶打造人形机器人原型，号称 Muse 模型的物理化身', '') == 'meta_fourier_robot'


def test_meta机器人_防误并():
    assert entity_key("Meta's AI agent has been blocked from using Amazon.com",
                      'Amazon has blocked Meta Muse shopping agent') == 'meta_muse_amazon_block'
    assert entity_key("Coming in 2027: Apple's $1,000 home robot for FaceTime", '') != 'meta_fourier_robot'
    assert entity_key('Meta has some Wonder Full new AI models', '') == 'meta_muse'


# ── ③ kherson_ceasefire ──

def test_赫尔松停火_各源命中():
    assert entity_key('Ukraine: Oleshky ceasefire ends, Russian attacks continue',
                      'A US-brokered ceasefire in Ukraine') == 'kherson_ceasefire'
    assert entity_key('乌克兰赫尔松停火：从俄罗斯占领城市撤离的人说"我们从地狱回来了"', '') == 'kherson_ceasefire'
    assert entity_key('俄烏局部停火結束後　烏南城市赫松遭俄無人機攻擊', '') == 'kherson_ceasefire'
    assert entity_key('Kherson ceasefire ends', '') == 'kherson_ceasefire'
    assert entity_key('Russian strikes cut power to thousands in Ukraine as Kherson ceasefire', '') == 'kherson_ceasefire'


def test_赫尔松停火_无地名战线稿不并():
    assert entity_key('Ukraine war: front-line assault repelled in Donbas', 'Energy infrastructure hit') != 'kherson_ceasefire'


# ── ④ NOISE ──

def test_见闻抽象观点_何处是底():
    assert is_noise('何处是底 拐点的出现：海外科技巨头的投资回报再度受到市场的审视 美股正在等待一个明确的底部信号')


def test_bbc中文人物解释特稿_弗拉维奥():
    assert is_noise('弗拉维奥·博索纳罗：巴西前总统之子，败给卢拉后，为何飞往美国？ 弗拉维奥·博索纳罗离开巴西后，'
                    '在美国佛罗里达州走下飞机。')
    # 防误伤: 无"为何"句式的弗拉维奥真新闻
    assert not is_noise('弗拉维奥·博索纳罗宣布辞去参议员职务，专注总统竞选')


def test_it之家爆料体_翻盖功能机():
    assert is_noise('HMD 诺基亚 2360 Flip 翻盖功能机曝光：紫光展锐 T127 芯片，1.8 英寸外屏 '
                    '消息源 smashx_60 现已曝光了 HMD 旗下诺基亚 2360')
    # 防误伤: 正常诺基亚公司新闻无"功能机+曝光"组合
    assert not is_noise('诺基亚发布 2026 财年第三季度财报，营收同比增长 8%')


def test_卫报直播聚合栏目_europe_live():
    assert is_noise('Ikea among shops affected by fridge cyber-hacks – Europe live')


# ── ⑤ china_regulators_meeting (央行/证监会 11月2日座谈会) ──

def test_金融监管座谈会_各源命中():
    assert entity_key('金融监管部门将召开座谈会，A股将迎哪些利好？',
                      '央行、中国证监会将召集证券公司基金公司举行会议') == 'china_regulators_meeting'
    assert entity_key('金融管理部门明日将召开会议，研究推动支持资本市场工具使用', '') == 'china_regulators_meeting'
    assert entity_key('三部门增量政策释放稳市信号', '央行、金融监管总局、证监会等三部门召开座谈会') == 'china_regulators_meeting'
    assert entity_key('中国三大金融监管部门据报周一开会 研究稳定股市措施', '') == 'china_regulators_meeting'
    assert entity_key('央行等三部门优化资本市场支持工具，回购增持再贷款利率降至1%',
                      '中国人民银行会同金融监管总局、证监会等部门先后召开互换便利座谈会') == 'china_regulators_meeting'


def test_金融监管座谈会_防误并():
    # 市场反应稿/常规流动性操作稿无会议词不并 (独立事件)
    assert entity_key('午后拉升！沪指重上3600点，传媒掀涨停潮', '券商、金融科技爆发') != 'china_regulators_meeting'
    assert entity_key('央行出手稳市场！将开展第三次证券基金保险公司互换便利操作',
                      '参与机构数量和申报额度均有望超越前两批') != 'china_regulators_meeting'
    assert entity_key('央行发布第三季度货币政策执行报告', '') != 'china_regulators_meeting'
