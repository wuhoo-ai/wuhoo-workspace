"""2026-10-03 修复回归: 裸'核'误分宏观 / BBC 情感软文 / 虎嗅出品栏目 / 第一人称投资叙事 / 车企月度销量榜合并"""
from test_daily_briefing import NS

entity_key = NS['entity_key']
is_noise = NS['is_noise']
classify = NS['classify']


class TestBriefing20261003:

    def test_bbc_relationship_ad_is_noise(self):
        # BBC 中文情感咨询软文不得进榜、不得靠"为核心"误分宏观
        assert is_noise('感情走下坡还有救吗？伴侣治疗师谈修复关系的要素 建设性的争吵——以尊重、好奇与善意为核心、着重共同解决问题是能强化关系的。')

    def test_bare_he_char_no_longer_misclassifies(self):
        # 裸'核'已删: 情感软文即使不过噪声闸，classify 也不再命中宏观
        assert classify('感情走下坡还有救吗？伴侣治疗师谈修复关系的要素 以尊重、好奇与善意为核心', '综合') != '宏观政策'
        # 核心PCE 财经稿不再被误加宏观分
        assert classify('Fed偏好通膨指標出爐 美8月核心PCE年增3%低於預期', '财经') != '宏观政策'

    def test_nuclear_news_still_policy(self):
        # 真·核新闻仍归宏观
        assert classify('Iran nuclear talks resume as IAEA inspectors visit enrichment site', '') == '宏观政策' or \
            classify('伊朗核协议谈判重启', '') == '宏观政策'

    def test_huxiu_signed_column_noise(self):
        assert is_noise('这次，字节枪口瞄准了谁？ 出品｜虎嗅黄青春频道作者｜商业消费主笔黄青春')
        # 防误伤: 无"出品｜"栏头的正常虎嗅稿不受影响
        assert not is_noise('特朗普的"AI自我监管"意味着什么？老黄"大获全胜" 9月30日特朗普与AI高管白宫会面')

    def test_first_person_investing_story_noise(self):
        assert is_noise('体验了Muse后，我清仓了Airbnb 在硅谷和华尔街，关于AI如何改变商业世界的讨论')
        assert is_noise('下载体验了 Muse 后，我清仓了 Airbnb，加仓了 Meta')
        # 防误伤: 正常机构持仓报道不含"我清仓"
        assert not is_noise('巴菲特清仓了苹果股票 伯克希尔第三季度减持')

    def test_bbc_gen_z_pension_story_noise(self):
        # BBC Business 个人叙事软文 (同类 pay into my pension)
        assert is_noise("'it could cost me \u00a310k but i need the money now': why gen z are opting out of pensions")
        # 防误伤: 制度性养老金新闻不受影响
        assert not is_noise('government announces reform of state pension age from 2027')

    def test_auto_monthly_sales_merged(self):
        # 榜单/汇总两条聚合稿合并为一个事件
        assert entity_key('2026 年 9 月汽车销量 / 交付榜出炉：比亚迪 46.36 万辆稳坐头把交椅', '') == 'china_auto_monthly_sales'
        assert entity_key('2026 年 9 月汽车销量 / 交付汇总（持续更新）：奇瑞超 29 万辆', '') == 'china_auto_monthly_sales'
        # 防误并: 单车企产销公告不合并、保留独立事件
        assert entity_key('比亚迪 9 月汽车销量 463561 辆同比增长 16.98%：今年累计销量 313 万辆', '') != 'china_auto_monthly_sales'
