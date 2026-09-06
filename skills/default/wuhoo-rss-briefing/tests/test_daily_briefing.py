"""daily_briefing.py 事件合并/分类逻辑回归测试

daily_briefing.py 主流程在模块顶层无条件执行(无 __main__ 守卫, cron 直接 python3.11 调用),
无法直接 import 而不触发真实 DB 查询。本测试以源码 exec 方式加载定义段(主流程分隔符 '# ── 主流程' 之前),
对实体级合并规则做纯逻辑验证, 不依赖 DB。
"""
import re
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / 'scripts' / 'daily_briefing.py'
MAIN_SEP = '# ── 主流程'


def _load_defs():
    src = SCRIPT.read_text(encoding='utf-8')
    assert MAIN_SEP in src, '未找到主流程分隔符, 脚本结构可能已变'
    ns = {}
    exec(compile(src.split(MAIN_SEP)[0], str(SCRIPT), 'exec'), ns)
    return ns


NS = _load_defs()
entity_key = NS['entity_key']
group_events = NS['group_events']
classify = NS['classify']
is_noise = NS['is_noise']


def _art(title, summary='', feed='Hacker News', date='2026-09-02', cat='科技', hot=10):
    return {'title': title, 'summary': summary, 'feed_name': feed,
            'pub_date': date, 'category': cat, 'hot_score': hot}


class TestGemini38Flash:
    """2026-09-03: Gemini 3.8 Flash 发布 9行8源同事件必须合并为一条"""

    TITLES = [
        'Gemini 3.8 Flash and 3.8 Flash Cyber',
        '谷歌 Gemini 3.8 Flash 模型上线，适用软件工程、智能体任务等场景',
        'Introducing Gemini 3.8 Flash and 3.8 Flash Cyber',
        'Google releases Gemini 3.8 Flash, its third Flash model in six weeks',
        'Gemini 3.8，明日登场',
        '谷歌推出 Gemini 3.8 Flash Cyber 模型，内部已全面部署用于代码安全防护',
        '才三周Flash就换代！谷歌上新两款Gemini 3.8：编程与推理能力升级，网安模型瞄准自动修复',
    ]

    def test_all_map_to_same_key(self):
        keys = {entity_key(t, '') for t in self.TITLES}
        assert keys == {'gemini_38_flash'}, keys

    def test_no_false_positive(self):
        for t in ['Gemini 2.5 Pro 正式向公众开放', 'qwen3.8系模型不支持 re=max',
                  'NVIDIA launches new GPU', 'Gemini in Gmail rolling out',
                  '谷歌发布 Gemini 3 视觉模型']:
            assert entity_key(t, '') is None, t

    def test_zh_en_rows_merge_into_one_group(self):
        arts = [_art('Gemini 3.8 Flash and 3.8 Flash Cyber', feed='Hacker News', hot=17),
                _art('谷歌 Gemini 3.8 Flash 模型上线，适用软件工程、智能体任务等场景',
                     '谷歌上线 Gemini 3.8 Flash', feed='IT之家', hot=15)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 2


class TestEntityKeyRegressions:
    """既往文档化实体规则回归 (skill 2026-08-31/09-02)"""

    CASES = [
        # (title, expected_key)
        ('Introducing Claude Fable 5.1 and Claude Mythos 5.1', 'claude_fable_51'),
        ('Anthropic releases Claude Fable 5.1, coding gains', 'claude_fable_51'),
        ('库克发文告别苹果 CEO 一职：头衔会变，但对 Apple 社区的热爱永远不会改变', 'apple_ceo_transition'),
        ('Tim Cook final message as Apple CEO', 'apple_ceo_transition'),
        ('FTC accuses Amazon of running a secret ad surcharge scheme', 'ftc_amazon_surcharge'),
        ('FTC sues Amazon over secret ad surcharge scheme', 'ftc_amazon_surcharge'),
        ('Apple debuts new Mac mini / Studio on surging AI demand', 'apple_mac_ai_demand'),
        ('Netherlands moves billions in gold to London in crisis preparedness move', None),
        ('US-Canada trade war felt on both sides of the border', None),
        ('NVIDIA announces new datacenter GPU', None),
        ('英伟达发布新一代显卡驱动', None),
    ]

    def test_known_entity_keys(self):
        for title, expected in self.CASES:
            assert entity_key(title, '') == expected, (title, entity_key(title, ''))

    def test_bare_company_names_do_not_overmerge(self):
        arts = [_art('NVIDIA announces new datacenter GPU', feed='The Verge'),
                _art('英伟达发布新一代显卡驱动', feed='IT之家')]
        groups = group_events(arts)
        assert len(groups) == 2, '泛公司名裸词不得合并不同事件'


class TestAiServiceOutage:
    """2026-09-05: 09-04 ChatGPT/Claude/Grok/Gemini 四大 AI 服务同时宕机
    (Solidot 中文新闻版 + Ars "overlapping downtime" + HN Ask 版拆占科技/AI TOP5 两条 → 合并)"""

    CASES = [
        ('四大 AI 模型同时下线',
         '周四早晨 ChatGPT、Claude、Grok 和 Gemini 四大 AI 服务几乎在同一时间段内遭遇了严重故障', 'ai_service_outage'),
        ('Four major AI models suffer rare overlapping downtime',
         'Service interruptions hit ChatGPT, Claude, Grok, and Gemini practically simultaneously.', 'ai_service_outage'),
        ('Ask HN: Why were OpenAI, Claude, and Grok simultaneously down?', '', 'ai_service_outage'),
    ]

    def test_all_map_to_same_key(self):
        for title, summary, expected in self.CASES:
            assert entity_key(title, summary) == expected, title

    def test_merge_across_zh_en(self):
        arts = [_art(self.CASES[0][0], self.CASES[0][1], feed='Solidot 奇点资讯', date='2026-09-04', hot=19),
                _art(self.CASES[1][0], self.CASES[1][1], feed='Ars Technica', date='2026-09-03', hot=15),
                _art(self.CASES[2][0], self.CASES[2][1], feed='Hacker News', date='2026-09-03', hot=13)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 3, f'{len(groups)} 组'

    def test_no_false_positive(self):
        for t in ['OpenAI appoints new CTO', 'Netflix is down', 'Gemini in Gmail rolling out',
                  'Robinhood is not backing down after AMC CEO demands halt to stock tokens',
                  'Shutting down our public encrypted DNS']:  # HN Mullvad 无 AI 服务名
            assert entity_key(t, '') is None, t

    def test_gemini38_not_hijacked_by_outage_rule(self):
        # 前序规则先命中, 不得被宕机规则劫持
        assert entity_key('Gemini 3.8 Flash and 3.8 Flash Cyber', '') == 'gemini_38_flash'


class TestNoise20260905:
    """2026-09-05: 派早报 日更聚合栏目 (同类 IT早报/早餐FM) 过滤"""

    def test_paizaobao_digest_is_noise(self):
        assert is_noise('派早报：英伟达正式发布 DLSS 5、戴森发布智能电动牙刷 CameraJet 等')

    def test_regular_corp_news_not_noise(self):
        assert not is_noise('小米 18 Fold 中折叠手机拥有 1.2 米抗跌落能力，雷军称媲美直板旗舰')


class TestClassifyBasics:
    def test_finance_category_weight(self):
        c = classify('央行意外降息 25 个基点 人民币汇率走强', '财经')
        assert c == '财经/投资', c

    def test_trade_war_goes_macro(self):
        c = classify('US-Canada trade war is being felt on both sides of the border', '财经')
        assert c == '宏观政策', c

    def test_ai_launch_goes_tech(self):
        c = classify('谷歌 Gemini 3.8 Flash 模型上线，适用软件工程、智能体任务等场景', '科技')
        assert c == '科技/AI', c

    def test_unmatched_returns_none(self):
        assert classify('某地举办全民健身运动会开幕式', '综合') is None


class TestNoise20260906NflWordBoundary:
    """2026-09-06 严重修复: 裸词 'nfl' 子串命中 "co[nfl]ict", 所有含 conflict
    的战争/宏观英文报道被误滤 (BBC diesel hot=22 死于 "the Iran conflict")。
    缩写类噪声词必须词边界; 真 NFL 体育新闻仍须过滤。"""

    def test_conflict_article_not_noise(self):
        # BBC Business 柴油价历史新高原文摘要 — 此前被 'nfl' 子串误杀
        text = ('US diesel prices hit an all-time-high '
                'Fuel prices have soared since the Iran conflict began at the end of February')
        assert not is_noise(text), 'co[nfl]ict 不应命中 nfl 体育过滤'

    def test_iran_war_macro_article_not_noise(self):
        text = ('Iran War Helps to Drive U.S. Diesel Prices to New High '
                'Because of the war in Iran, the cost has exceeded its 2022 record')
        assert not is_noise(text)

    def test_real_nfl_sports_still_noise(self):
        assert is_noise('Chiefs edge Bills in NFL playoff thriller as Mahomes rallies late')
        assert is_noise('NBA Finals Game 7: Celtics crowned champions after overtime')

    def test_plain_word_nfl_unaffected(self):
        # 词边界修复不得影响同批其它体育词
        assert is_noise('Man United line up shock transfer move for Chelsea striker')
        assert not is_noise('UN calls for peaceful resolution of the conflict in the region')


class TestDieselRecord20260906:
    """2026-09-06: 美伊战争推高美国柴油价至历史新高 (BBC/NYT/FT/美联社 6条同事件
    此前关键词表无能源词全落未匹配) → diesel_record 实体级合并"""

    TITLES = [
        'US diesel prices hit an all-time-high',                                  # BBC hot=22
        'Iran War Helps to Drive U.S. Diesel Prices to New High',                 # NYT
        "Trump's Iran war sends US diesel prices to record high",                 # FT
        'US diesel prices hit a record high of $5.85 on average as the Iran war',  # AP
        'US diesel prices hit a record high, pushing up transportation costs',     # AP
        'Oil Jumps for Fourth Straight Day and Diesel Nears Record High',          # NYT 09-03
    ]

    def test_all_map_to_same_key(self):
        keys = {entity_key(t, '') for t in self.TITLES}
        assert keys == {'diesel_record'}, keys

    def test_no_false_positive(self):
        for t in ['Nvidia earnings hit a record high on AI demand', 'S&P 500 hits record close',
                  'Electric vehicle sales reach all-time high in China', '油价创年内新高 欧佩克考虑增产']:
            assert entity_key(t, '') is None, t

    def test_energy_price_classifies_macro(self):
        # 宏观表补能源词后, 无 category 加权的英文 diesel 报道归宏观政策
        c = classify('US diesel prices hit an all-time-high Fuel prices have soared', '综合')
        assert c == '宏观政策', c

    def test_bbc_business_diesel_goes_finance(self):
        # BBC Business category=财经 +3 加权 → 财经/投资 (简报实测 TOP1)
        c = classify('US diesel prices hit an all-time-high Fuel prices have soared', '财经')
        assert c == '财经/投资', c
