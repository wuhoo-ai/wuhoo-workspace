"""2026-10-05 修复回归: OpenAI Robinson 辞职跨榜合并 / OpenAI 泄密解雇合并 / 埃塞提格雷收复机场 /
Verge Prime Day 导购 / IT之家单车型销量+消费电子发售 / BBC 中文解释性特稿"""
from test_daily_briefing import NS

entity_key = NS['entity_key']
is_noise = NS['is_noise']


class TestOpenaiRobinsonResign:
    """安全元老 David Robinson 辞职死谏: 见闻/TechCrunch/Verge/HN×2/格隆汇/一财/IT之家/虎嗅 不合并,
    拆占 科技/AI + 财经/投资 两榜"""

    TITLES = [
        'OpenAI「12朝元老」辞职死谏：试错的时代已崩坏！',
        'OpenAI safety employee resigns, claiming the company\u2019s \u2018culture is broken\u2019',
        'An OpenAI safety employee has quit and is sounding the alarm',
        'I Quit OpenAI Because Its Culture Is Broken',
        "OpenAI safety leader quits, warning AI company's culture is 'broken'",
        'OpenAI又一安全负责人离职',
    ]

    def test_all_map_to_same_key(self):
        for t in self.TITLES:
            assert entity_key(t, '') == 'openai_robinson_resign', t

    def test_gelonghui_robinson(self):
        assert entity_key('格隆汇10月3日｜OpenAI安全系统团队负责人David Robinson已从公司离职。', '') == 'openai_robinson_resign'
        assert entity_key('OpenAI安全系统团队负责人辞职', '据央视新闻，OpenAI安全系统团队负责人大卫·罗宾逊已辞职。') == 'openai_robinson_resign'

    def test_firings_not_merged_into_resign(self):
        # 解雇泄密是独立事件 (无 resign/quit/离职/辞职 词)
        assert entity_key("OpenAI fires workers for 'mishandling sensitive information'", '') != 'openai_robinson_resign'

    def test_dot_agent_not_merged(self):
        assert entity_key('OpenAI\u2019s Dot agent is enterprise software that can also order your dinner', '') is None


class TestOpenaiDataLeakFirings:
    """BBC Business 14 + Engadget 6 同事件 (解雇向外部安全评估组织泄密员工)"""

    def test_merge(self):
        assert entity_key("OpenAI fires workers for 'mishandling sensitive information'", '') == 'openai_data_leak_firings'
        assert entity_key('OpenAI fires three employees who allegedly shared info with an external AI safety group', '') == 'openai_data_leak_firings'

    def test_unrelated_fires_not_merged(self):
        assert entity_key('Fires break out at French schools as students protest nationwide', '') is None
        assert entity_key('Algeria introduces death penalty for arsonists after deadly wildfires', '') is None
        assert entity_key('NFL results: Maye fires Patriots past Bills', '') is None


class TestEthiopiaTigray:
    def test_merge(self):
        assert entity_key('Ethiopia government forces reclaim Tigray capital airport', '') == 'ethiopia_tigray'
        assert entity_key('Ethiopian rebel forces withdraw from Tigray regional capital', '') == 'ethiopia_tigray'

    def test_peace_analysis_not_merged(self):
        # DW 斡旋评论 (无军事进退词) 独立
        assert entity_key('Can anyone broker a new peace between Tigray and Ethiopia?', '') is None


class TestNoise20261005:
    def test_verge_prime_day_deal(self):
        assert is_noise('The MacBook Air M5 is $200 off for the first time in months Amazon\u2019s October Prime Day has effectively chopped')

    def test_byd_single_model_sales(self):
        assert is_noise('比亚迪秦 MAX 车型 9 月销量 12066 辆，上市 2 个月连续破万')

    def test_consumer_electronics_launches(self):
        assert is_noise('泰坦军团\u201cP2511G+\u201d24.5 英寸显示器发售：1080P 215Hz 超频，509 元')
        assert is_noise('QCY 推出 Crossky C70 耳夹式耳机：SQ5 欧姆原声单元、-54dB ENC 降噪深度，399 元')
        assert is_noise('华硕上架 2026 款无畏 16 锐龙版笔记本：R7 H 260 + 16G + 512G 售 5999 元')

    def test_bbc_explainer_column(self):
        assert is_noise('西班牙与中国愈走愈近，欧盟多方为何不满？')
        assert is_noise('Spain and China are cosying up - to the anger of many in the EU')

    def test_no_false_positive(self):
        # 华为旗舰/真新闻不受影响
        assert not is_noise('华为 Mate 90 Pro Max 性能解禁：搭载麒麟 9050 Pro')
        assert not is_noise('1100 亿美元超级并购：派拉蒙与华纳兄弟探索合并后将更名为\u201cSkydance\u201d')


    def test_honor_airpump_and_hopstar_psu(self):
        assert is_noise('荣耀推出 HONOR Life 充气泵 Lite：具备照明功能、标称"42 秒充满一条自行车胎"，248 元')
        assert is_noise('航嘉推出重火力 AX1000P 三叉戟白金全模组电源：7 年质保，759 元')

    def test_vision_gt_merge(self):
        assert entity_key('小米 Vision GT 十月入驻，GT 系列游戏将首次推出电车驾驶教学', '') == 'xiaomi_vision_gt'
        assert entity_key('小米 Vision GT 十月即将正式入驻 Gran Turismo 7，成为游戏史上的首台中国 Vision GT', '') == 'xiaomi_vision_gt'

    def test_mi5_classified_macro(self):
        classify = NS['classify']
        assert classify('军情五处警告：中国资助英国研究，成果交予北京间谍机关', '综合') == '宏观政策'
