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
clean_summary = NS['clean_summary']
clean_title = NS['clean_title']


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
        ('US-Canada trade war felt on both sides of the border', 'us_canada_trade_war'),  # 2026-09-10: 新增 us_canada_trade_war 规则后为合理命中 (原 None)
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


class TestNoise20260907:
    """2026-09-07: HN 成人/盗版八卦混入科技/AI TOP5; 米家/漫步者发售噪声
    模式扩展 预售 (小米破壁机 3 预售软文占产业/公司 TOP5 第3位漏网)"""

    def test_hn_adult_gossip_is_noise(self):
        t = "Adult Film Producer Unmasks Prolific 'John DOE' Torrent Pirate as Meta Executive"
        assert is_noise(t)

    def test_mijia_presale_is_noise(self):
        assert is_noise('首发 389 → 311 元：小米 1.5L 米家破壁机 3 预售，可拆刀座轻松洗')

    def test_normal_corp_news_not_noise(self):
        # 米家预售规则不得误伤普通车型/公司预售新闻 (长安启源不含 米家/漫步者)
        assert not is_noise('长安启源 Q06 新能源 SUV 预售：纯电 / 增程动力，14.79 万元起')
        assert not is_noise('Volkswagen to cut 100,000 jobs by end of decade')


class TestEntityKeyDotPreserved20260909:
    """2026-09-09 严重修复: entity_key 不再经 norm() (norm 会吞 ASCII 点号) —
    版本号类规则 (chatgpt_images_25 / gemini_38_flash, 含点号) 此前全部静默失效"""

    def test_chatgpt_images_25_merges_zh_en(self):
        for t in ['ChatGPT Images 2.5', 'Introducing ChatGPT Images 2.5',
                  'OpenAI 最强 AI 生图模型：ChatGPT Images 2.5 登场，延迟降低 50%',
                  'OpenAI发布ChatGPT Images 2.5：生成速度最高提升50%']:
            assert entity_key(t, '') == 'chatgpt_images_25', t

    def test_chatgpt_images_no_false_positive(self):
        for t in ['Introducing ChatGPT Images 3', 'OpenAI Images 2.5 更新',
                  'Gemini 2.5 Pro 正式向公众开放']:
            assert entity_key(t, '') is None, t

    def test_gemini38_still_merges_after_dot_fix(self):
        assert entity_key('Gemini 3.8 Flash and 3.8 Flash Cyber', '') == 'gemini_38_flash'


class TestOpenaiNavierStokes20260909:
    """2026-09-09: OpenAI 攻克 Navier-Stokes 千禧年难题 5 源同事件合并;
    英文官方标题无 openai 字样也须命中; Buckmaster 学术 PDF 不误并"""

    def test_english_official_and_cn_merge(self):
        for t in ['On the Navier–Stokes Millennium Prize Problem',
                  'OpenAI 宣布用 10000 个 AI 智能体 88 小时攻克千禧年大奖难题',
                  "What's going on with OpenAI and the Navier-Stokes controversy?",
                  'OpenAI内部模型88小时暴力攻克千禧年数学难题']:
            assert entity_key(t, '') == 'openai_navier_stokes', t

    def test_academic_pdf_not_merged(self):
        assert entity_key('Navier-Stokes – Tristan Buckmaster [pdf]', '') is None


class TestMetaMuseChineseBoundary20260909:
    """2026-09-09: '智能体Muse' 前为 CJK 字符无 \b 边界, 中文语境分支必须命中;
    Renoir Museum 等含 museum 子串不得误并"""

    def test_zh_en_merge(self):
        for t in ['Meta debuts its Muse AI agent', 'Meta bets on AI agent Muse to catch up',
                  'Meta推出个人AI智能体Muse，扎克伯格：个人AI助手是Meta最大的商业机遇',
                  'Introducing Muse: The World’s First Personal AI Agent Built for Everyone',
                  'Muse: Meta\'s personal AI agent, features and capabilities']:
            assert entity_key(t, '') == 'meta_muse', t

    def test_museum_not_merged(self):
        for t in ['Renoir Museum robbery: 2 paintings missing',
                  'Artworks stolen from Renoir Museum on French Riviera in latest heist']:
            assert entity_key(t, '') is None, t


class TestAstraTightened20260909:
    """2026-09-09: 裸 'astra' 把 GPT-6 Astra (现役旗舰名) 相关无关文章误并 → 需安全/推迟语境"""

    def test_bare_astra_mention_no_longer_merges(self):
        assert entity_key('GPT-6 Astra on robot arms', '') is None
        assert entity_key('GPT-6之后，算力暴涨的故事又讲得通了？', '9月3日GPT-6 Astra发布后') is None

    def test_astra_security_context_still_merges(self):
        for t in ['OpenAI to pause some work on AI model Astra',
                  'OpenAI delays Astra safety review after cyber incident',
                  'Responding to the next frontier of critical cyber capabilities']:
            assert entity_key(t, '') == 'openai_astra', t


class TestAfdSaxony20260909:
    """2026-09-09: 德国 AfD 萨安州选举 DW×3/FT/BBC×2/第一财经 9 源同事件合并"""

    def test_multi_source_merge(self):
        for t in ['Saxony-Anhalt: Far-right AfD secures huge lead in key vote',
                  'AfD wants to form a government in Saxony-Anhalt — but how?',
                  '德国选择党在萨安州议会选举中大幅领先',
                  'Far-right AfD surges to first place in German state election',
                  "Germany's far-right AfD set for big win in eastern state"]:
            assert entity_key(t, '') == 'afd_saxony_election', t

    def test_national_afd_news_not_merged(self):
        assert entity_key('AfD polls at record high nationwide', '') is None


class TestNoiseItHome20260909:
    """2026-09-09: IT之家消费电子发售(爱国者机箱/技嘉显示器/利民散热器)挤占产业/公司 TOP5"""

    def test_hardware_presale_is_noise(self):
        for t in ['爱国者星璨岚大岚双屏版机箱首销：配双 6 英寸面板，首发价 699 元',
                  '技嘉推出“GO27Q32”27 英寸显示器：2K 320Hz QD-OLED，2999 元',
                  '利民推出 AXP120-X77 下压式风冷散热器：77mm 高度，首发价 239 元']:
            assert is_noise(t), t

    def test_corp_news_not_noise(self):
        assert not is_noise('利民实业发布上半年财报 净利润同比增长 12%')



class TestAppleIphoneDuo20260910:
    """2026-09-10: Apple 发布首款折叠屏 iPhone Duo (HN 裸标题 hot30 + 各源中英文标题各异全不合并 → 实体级 key);
    'Duo' 字样本体 (Surface Duo / The Verge 历史盘点标题单独) 不得触发"""

    def test_all_map_to_same_key(self):
        for t in ['iPhone Duo',
                  'iPhone-Duo first look',
                  'Apple unveils its first foldable, the iPhone Duo',
                  '苹果推出首款折叠屏手机iPhone Duo',
                  '苹果新CEO发布首款折叠屏手机iPhone Duo，折叠后大小相当于护照',
                  "iPhone Duo hands-on: Apple's most exciting device in a decade",
                  'iPhone Duo vs Samsung Galaxy Z Fold 8: here\'s how they stack up']:
            assert entity_key(t, '') == 'iphone_duo_launch', t

    def test_duo_alone_not_merged(self):
        for t in ['The incomplete history of Duo devices',
                  'Surface Duo 2 gets final security update',
                  'Motorola teases new compact foldable Razr']:
            assert entity_key(t, '') is None, t

    def test_multi_source_merge(self):
        arts = [_art('iPhone Duo', feed='Hacker News', hot=30),
                _art('苹果推出首款折叠屏手机iPhone Duo', feed='纽约时报中文', hot=6),
                _art('Apple unveils its first foldable, the iPhone Duo', feed='TechCrunch', hot=6)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 3


class TestUsCanadaTradeWar20260910:
    """2026-09-10: 美加贸易战升级 (进口禁令 + 反制关税 + Bombardier 威胁) 8+ 源不合并 → 实体级 key;
    误并边界: Bank of Canada 词边界防 bans? 裸词; 以色列屯墾區/孟晚舟 中文远距离误并 (距离限 80)"""

    CASES = [
        ('US slaps import ban on Canadian alcohol and other goods', ''),
        ('US bans Canadian dairy, alcohol and motorcycles as trade war escalates', ''),
        ('US banning dairy products, most alcoholic beverages and motorcycles from Canada', ''),
        ('Canada Imposes New Tariffs on U.S. Goods After Trump’s Latest Levies', ''),
        ('Trump threatens to block Bombardier planes from US market', ''),
        ('加拿大200亿反制美国关税生效，卡尼称不寻求贸易战升级但要加速摆脱对美依赖', ''),
        ('美国调整对加拿大部分产品从价关税适用范围', ''),
        ('关税最终将让加拿大人和美国人付出多少代价？', ''),
        ('加拿大对美国发起贸易反击', '加拿大对美国采取了贸易反制措施，对一系列美国商品加征关税'),
    ]

    def test_all_map_to_same_key(self):
        for t, s in self.CASES:
            assert entity_key(t, s) == 'us_canada_trade_war', (t, entity_key(t, s))

    def test_false_positive_guards(self):
        # Bank of Canada 词边界 (bans? 裸词会命中 "Ban[k] of Canada")
        assert entity_key('Bank of Canada holds rates steady', '') is None
        # 以色列屯墾區: 加拿大+將禁止進口 但非美加贸易战 → 中文分支无裸 禁/进口
        assert entity_key('控種族清洗　英法加將禁止進口以色列屯墾區商品',
                          '英國 法國與加拿大今天表示 將禁止進口以色列在被占領的約旦河西岸所設屯墾區的商品') is None
        # 孟晚舟: 加拿大被捕 ≠ 贸易战, 远距离 关税/贸易战 不参与匹配
        assert entity_key('孟晚舟事件八年后，华为案在纽约开审',
                          '2018年 时任华为首席财务官孟晚舟 当时她在加拿大被捕 被指控窃取美国公司的商业机密') is None

    def test_multi_source_merge(self):
        arts = [_art('US slaps import ban on Canadian alcohol and other goods', feed='BBC Business', hot=14),
                _art('US bans Canadian dairy, alcohol and motorcycles as trade war escalates', feed='卫报国际', hot=6),
                _art('Canada Imposes New Tariffs on U.S. Goods After Trump’s Latest Levies', feed='NYT Business', hot=6)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 3


class TestMiamiAmazonCrash20260910:
    """2026-09-10: 迈阿密亚马逊货机坠毁 6 条 (BBC World/BBC Business/美联社×3) 同事件标题各异不合并"""

    def test_all_map_to_same_key(self):
        for t in ['Five killed as Amazon cargo plane crashes at Miami airport',
                  'Investigators begin work on why cargo plane overran Miami runway',
                  'What to know about the Amazon cargo plane crash in Miami that killed 5 workers',
                  'Control tower audio released from moments after Amazon cargo jet runway crash in Miami',
                  'Five killed in Miami plane crash were in two vehicles on ground, investigators say']:
            assert entity_key(t, '') == 'miami_amazon_crash', t

    def test_no_false_positive(self):
        for t in ['Miami crypto conference draws thousands to the beach',
                  'Cargo ship runs aground near Miami']:
            assert entity_key(t, '') is None, t

    def test_multi_source_merge(self):
        arts = [_art('Five killed as Amazon cargo plane crashes at Miami airport', feed='BBC World', hot=6),
                _art('What to know about the Amazon cargo plane crash in Miami that killed 5 workers', feed='美联社', hot=6)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 2


class TestNoise20260910:
    """2026-09-10: 九州风神散热器 / BBC Future 机器人小费特稿 / BBC 个人理财软文 噪声"""

    def test_new_noise_patterns(self):
        for t in ['九州风神推出 AN600 VC 下压式散热器：升级 VC 2.0 均热板底座，3 年质保，299 元',
                  '机器人开始索要小费，但钱到底进了谁的口袋？',
                  "I'm 27 and I've already written my will - here's why"]:
            assert is_noise(t), t

    def test_corp_news_not_noise(self):
        # 九州风神规则不得误伤公司业绩类新闻
        assert not is_noise('九州风神发布上半年业绩预告，海外营收同比增长 30%')


class TestSummaryPrefixCleanup20260910:
    """2026-09-10: clean_summary 通用前缀清理 — NYT中文署名+日期 / RFI 时间戳 不得占满 50 字窗口"""

    def test_nyt_author_date_prefix_stripped(self):
        s = clean_summary('KALLEY HUANG2026年9月10日周三，苹果首席执行官约翰·特纳斯介绍了折叠屏iPhone Duo。')
        assert s.startswith('苹果首席执行官'), s

    def test_rfi_timestamp_prefix_stripped(self):
        s = clean_summary('09/09/2026 - 20:54 在三星推出折叠屏手机七年后，苹果公司周三终于发布了首款折叠屏手机。')
        assert s.startswith('在三星') or s.startswith('在'), s


class TestRfiTitleSuffix20260910:
    """2026-09-10: RFI 标题尾部 '- RFI - 法国国际广播电台' 与来源名重复, clean_title 剥离"""

    def test_rfi_suffix_stripped(self):
        assert clean_title('马克龙在巴黎办国际空间峰会，美科技巨头抵制、德意总理缺席 - RFI - 法国国际广播电台') == \
            '马克龙在巴黎办国际空间峰会，美科技巨头抵制、德意总理缺席'
        assert clean_title('苹果新CEO发布首款折叠屏手机iPhone Duo - RFI - 法国国际广播电台') == \
            '苹果新CEO发布首款折叠屏手机iPhone Duo'


class TestSaLowSignal20260911:
    """2026-09-11: SA 会议 slideshow/transcript 自动材料 (hot 19 挤占财经 TOP2) 必须被 SA_LOW_RE 过滤"""

    SA = NS['SA_LOW_RE']

    def test_conference_slideshow_filtered(self):
        for t in ['First Quantum Minerals Ltd. (FM:CA) Presents at Jefferies Global Industrials Conference 2026 - Slideshow',
                  'First Quantum Minerals Ltd. (FM:CA) Presents at JPM Back to School - Slideshow',
                  'Beam Therapeutics Inc. (BEAM) Discusses Updated Phase 1/2 Data for BEAM-302 in Alpha-1 Antitrypsin Deficiency - Slideshow',
                  'Texas Ventures Acquisition III Corp (TVA) Plus Automation Inc., - M&A Call - Slideshow']:
            assert self.SA.search(t), t

    def test_legit_analysis_not_filtered(self):
        for t in ['Oracle Q1: 20x Earnings Is Too Cheap For 120% Cloud Growth',
                  'Nebius: Explosive Growth Meets A Stretched Valuation',
                  "Target's Turnaround Is Shaping Up Nicely, But The Rising Valuation Forces A Downgrade"]:
            assert not self.SA.search(t), t
