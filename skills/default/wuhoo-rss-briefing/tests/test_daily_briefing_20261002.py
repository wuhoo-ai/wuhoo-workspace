"""2026-10-02 修复回归: ai_slowdown 裸 warn 误并 / trump_ai_pledge 反向分支 / BMW 3系合并 / BBC 科普噪声"""
from test_daily_briefing import NS

entity_key = NS['entity_key']
is_noise = NS['is_noise']


class TestBriefing20261002:

    def test_guardian_optout_not_slowdown(self):
        # 卫报新闻行业版权稿不得被误并进 AI 放缓辩论事件
        assert entity_key(
            'Anthropic pushes for opt-out model for Australian content as ABC warns of \u2018cannibalisation\u2019 of news',
            'Maker of Claude claims AI could transform economy and society but warns news being cannibalised'
        ) != 'ai_slowdown_debate'

    def test_slowdown_still_merged(self):
        # 真·放缓辩论稿仍合并
        assert entity_key('Amodei calls for global AI slowdown', '') == 'ai_slowdown_debate'
        assert entity_key('AI巨头齐发声 呼吁放缓发展', '阿莫迪倡议获得多方响应') == 'ai_slowdown_debate'

    def test_trump_ai_pledge_reverse_branch(self):
        # CoinDesk 版锚点(White House)在 pledge 之后，须并入特朗普白宫 AI 协议事件
        assert entity_key(
            'OpenAI, Google and Meta pledge independent AI safety audits under voluntary White House deal',
            '') == 'trump_ai_pledge'
        assert entity_key('特朗普的\u201cAI自我监管\u201d意味着什么？老黄\u201c大获全胜\u201d', '') == 'trump_ai_pledge'
        # 防误并: 白宫与 AI/审计/承诺词无共现
        assert entity_key('White House announces new immigration enforcement plan', '') != 'trump_ai_pledge'
        assert entity_key('EU pushes new deal on migration quota', '') != 'trump_ai_pledge'

    def test_bmw_3series_ev_merged(self):
        assert entity_key(
            'BMW built the same car for gas and electric. The EV is $4,400 cheaper.',
            'The new BMW 3 Series shows just how quickly EVs have') == 'bmw_3series_ev_pricing'
        assert entity_key(
            'BMW reveals US 3 series pricing: The EV carries a hefty premium',
            'The 2027 BMW 330 starts at $49,900, the i3 50 xDrive') == 'bmw_3series_ev_pricing'
        # 防误并: 宝马其他事件（召回）不带 EV/纯电语境共现
        assert entity_key('BMW recalls 330,000 vehicles over software defect', '') != 'bmw_3series_ev_pricing'

    def test_bbc_science_feature_noise(self):
        assert is_noise('猫眼如何启发机器人的照相机技术发展')
        assert is_noise('貓眼為何會在黑暗中「發光」？')
        # 真新闻不误伤
        assert not is_noise('Meta 发布 Muse 智能体新版本')
