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


class TestNoise20260912:
    """2026-09-12: HN 引用列表帖 ("List of references on Sony websites…" hot=11 占产业/公司 TOP1,
    非新闻事件, 同类 ankidroid/marty); BBC Business 个人理财软文续 ("pay into my pension",
    同类 written my will/money disagre/lend me £10k)"""

    def test_hn_reference_list_is_noise(self):
        assert is_noise('List of references on Sony websites to players "owning" their digital games')

    def test_pension_soft_feature_is_noise(self):
        assert is_noise("I asked my husband to pay into my pension when we had a child - here's why")

    def test_corp_news_not_noise(self):
        # 引用列表规则不得误伤正常新闻; 个人理财短语不得误伤养老金政策报道
        assert not is_noise('索尼数字游戏所有权纠纷升级，玩家组织发起集体诉讼')
        assert not is_noise('Pensions minister unveils reform to workplace pension schemes')


class TestNoise20260913:
    """2026-09-13: The Verge 导购/促销 commerce 帖 (where to preorder / half off) +
    IT之家消费电子发售续二 (机械革命上架 / 努比亚散热器开售 / 米家众筹)
    实测: Fire TV 促销占产业/公司 TOP4; 机械革命上架 hot6 占 TOP2; 努比亚散热器开售 hot3"""

    def test_verge_commerce_is_noise(self):
        for t in ["Amazon's Fire TV Stick 4K is over half off at under $20",
                  'Where to preorder the iPhone 18 Pro and Pro Max',
                  'Where to preorder the new Apple Watch Series 12 and Ultra 4']:
            assert is_noise(t), t

    def test_it_home_commerce_is_noise(self):
        for t in ['机械革命无界 14S 2026 笔记本锐龙版上架：R7 H 255 处理器，24GB+512GB 售价 4699 元（国补后 3994.15 元）',
                  '努比亚冰淇淋散热器开售：至低-18℃ 制冷、25W 峰值功率，99 元',
                  '小米米家夜灯 4 开启众筹：暗光感应、8 个月长续航，59 元']:
            assert is_noise(t), t

    def test_corp_news_not_noise(self):
        assert not is_noise('机械革命母公司发布财报：上半年净利润同比增长 25%')
        assert not is_noise('努比亚发布新一代游戏手机，搭载骁龙处理器')


class TestEngadgetGuide20260913:
    """2026-09-13: Engadget How-to 指南类 (Alexa 语音设置 / Muse 上手) 非新闻事件"""

    G = NS['ENGADGET_GUIDE_RE']

    def test_guides_match(self):
        for t in ["How to change Amazon Alexa's voice and personality",
                  "How to get started with Meta's new AI agent, Muse"]:
            assert self.G.search(t), t

    def test_news_not_match(self):
        for t in ['Engadget reviews the new iPhone Duo', 'Apple how-to event recap']:
            assert not self.G.search(t), t


class TestBbcVideoCaption20260913:
    """2026-09-13: BBC 中文视频字幕残留 ("Watch: … , 节目全长 N,NN HH:MM") 不得占满摘要窗口"""

    def test_caption_stripped_to_empty(self):
        for raw in [
            '你的器材不支持播放多媒体材料 Play video,  Watch: Three times Trump has promised money to Americans , 节目全长 1,2301:23',
            'Watch: Lava fountain and ash cloud as Indonesia volcano erupts , 节目全长 0,2700:27',
            'How much can Canada fight back in its trade war with the US? , 节目全长 1,2401:24',
            '西藏泥石流最震撼衝擊畫面遭受中國官媒審查 , 节目全长 1,0401:04',
        ]:
            s = clean_summary(raw, 'BBC 中文')
            assert '节目全长' not in s and 'Watch' not in s, (raw, s)

    def test_normal_summary_kept(self):
        s = clean_summary('苹果公司周三发布了首款折叠屏手机，起售价 1999 美元。', 'BBC 中文')
        assert s.startswith('苹果公司'), s

    def test_deep_caption_not_stripped(self):
        # "节目全长" 在正文深处 (IT之家任天堂直面会条目, 无视频时长格式) 不得触发剥离
        s = clean_summary('IT之家 9 月 4 日消息，任天堂今晚宣布，将于 9 月 8-9 日连续举行两场直面会，节目全长约 40 分钟。', 'IT之家')
        assert s.startswith('任天堂') and '节目全长' in s, s


class TestTrump5000Check20260913:
    """2026-09-13: 特朗普"每人5000美元支票"中期选举承诺多源同事件合并
    (BBC 中文 hot19 + 华尔街见闻 + 卫报; BBC 版摘要为视频字幕残留 → 合并后中文摘要回填)"""

    CASES = [
        '特朗普真的能向每位美国成年人发放5,000美元吗',
        '特朗普称"5000美元红利"无需国会批准，参院共和党领袖打哈哈，民主党痛斥',
        '特朗普拟给美国成年人每人发5000美元，美媒算账：总额高达1.2万亿美元',
        '特朗普的5000美元支票计划在共和党盟友中反响冷淡',
        'Trump keeps touting $5,000 payments if Republicans retain control of Congress',
        '哈塞特：特朗普5000美元计划"可以以负责任的财政方式实现"',
    ]

    def test_all_map_to_same_key(self):
        for t in self.CASES:
            assert entity_key(t, '') == 'trump_5000_check', t

    def test_no_false_positive(self):
        for t in ['美国一律师用 ChatGPT 生成诉讼文书却出现伪造警察证词，被罚款 5000 美元',
                  '特朗普威胁对华加征 5000 亿美元关税',
                  '特朗普宣布新的关税政策，美股应声下跌',
                  'Spain could suffer 2030 World Cup final snub as Morocco FA president names 115,000-seat stadium']:
            assert entity_key(t, '') is None, (t, entity_key(t, ''))

    def test_merge_across_sources(self):
        arts = [_art('特朗普真的能向每位美国成年人发放5,000美元吗', '', feed='BBC 中文', hot=19),
                _art('特朗普拟给美国成年人每人发5000美元，美媒算账：总额高达1.2万亿美元',
                     '财政成本远超关税收入所能覆盖的范围', feed='华尔街见闻热门', hot=3),
                _art('Trump keeps touting $5,000 payments if Republicans retain control of Congress',
                     'some in his party question feasibility', feed='卫报国际', hot=6)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 3, f'{len(groups)} 组'


class TestRubygemsAttack20260914:
    """2026-09-14: OpenAI 智能体攻击 RubyGems 事件披露 — 5 源标题各异不合并
    (HN 直述 / 中央社 "代理再爆失控" / 第一财经 "AI进化速递" /
     Verge "another company in May" — 标题与 50 字摘要窗口均无 RubyGems 字样 /
     Engadget "before the Hugging Face incident") → 合并后 [5源] + 中文摘要回填"""

    CASES = [
        ('OpenAI agents carried out an undisclosed attack on RubyGems', ''),
        ('OpenAI代理再爆失控　攻擊軟體平台RubyGems', '研究人員表示，OpenAI測試中的人工智慧代理入侵開源平台'),
        ('AI进化速递丨OpenAI证实其AI智能体曾攻击RubyGems', ''),
        ("OpenAI's rogue AI tried to hack another company in May", 'In May, hundreds of malicious and spam packages we'),
        ('OpenAI agents hacked a software service before the Hugging Face incident', 'The agents OpenAI was testing attacked a software '),
    ]

    def test_all_map_to_same_key(self):
        keys = {entity_key(t, s) for t, s in self.CASES}
        assert keys == {'rubygems_attack'}, keys

    def test_it_home_variant(self):
        # IT之家版本 (09-12 批次, 多在窗口边界外) 也应命中
        t = 'OpenAI 承认其 AI 智能体曾对 Ruby 语言包管理器 RubyGems 发起网络攻击'
        assert entity_key(t, '') == 'rubygems_attack'

    def test_merge_across_sources(self):
        arts = [_art(self.CASES[0][0], self.CASES[0][1], feed='Hacker News', hot=14),
                _art(self.CASES[1][0], self.CASES[1][1], feed='中央社', hot=9),
                _art(self.CASES[2][0], self.CASES[2][1], feed='第一财经', hot=3),
                _art(self.CASES[3][0], self.CASES[3][1], feed='The Verge', hot=6),
                _art(self.CASES[4][0], self.CASES[4][1], feed='Engadget', hot=6)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 5, f'{len(groups)} 组'

    def test_no_false_positive(self):
        for t in ['Hugging Face releases SmolLM3',
                  'RubyGems 4.0.0 released with performance improvements',
                  'OpenAI releases new batch API',
                  'Hugging Face models downloaded 10M times this week',
                  "Anthropic's Claude AI escapes to hack into three organisations",
                  "Rogue AI agents created fake online identities in another hacking attempt",
                  "OpenAI's rogue AI model incident was worse than we thought"]:
            assert entity_key(t, '') is None, (t, entity_key(t, ''))


class TestCentralNewsByline20260914:
    """2026-09-14: 中央社 byline "（中央社舊金山11日綜合外電報導）" 吃满 50 字摘要窗口 (RubyGems 合并回填实测)"""

    def test_byline_stripped(self):
        s = clean_summary('（中央社舊金山11日綜合外電報導）研究人員表示，OpenAI測試中的人工智慧代理（AI Agent）入侵開源平台',
                          '中央社')
        assert s.startswith('研究人員表示'), s

    def test_summary_without_byline_untouched(self):
        s = clean_summary('研究人員表示，OpenAI 測試中的代理曾攻擊軟體平台', '中央社')
        assert s.startswith('研究人員表示'), s


class TestAiSlowdownDebate20260915:
    """2026-09-15: AI 巨头集体呼吁"放缓 AI 发展"辩论 15+ 源碎片化不合并
    (Amodei 倡议 + 马斯克/奥特曼背书 + 微软自律准则 + 特朗普反对 + 美股 AI 板块大跌;
    Verge/华尔街见闻×4/FT×2/NYT×2/卫报/TechCrunch/BBC中文/虎嗅/凤凰网/RFI×3/中央社×2/联合早报/纽约时报中文/HN/BBC World;
    hot 最高仅 12 → 另配 PRIORITY_EVENTS 保底插入。
    关键修复: ai 锚点 CJK 邻接 ("AI放缓"/"放缓AI") 时 \\b 静默失效 → 用 (?<![a-z])ai(?![a-z]) )"""

    MERGE_CASES = [
        ("Is Big Tech's AI slowdown a safety pact or a cartel?",
         'When OpenAI CEO Sam Altman, Anthropic CEO Dario Amodei loosely agreed over the weekend'),
        ('Anthropic boss Dario Amodei calls for AI slowdown', ''),
        ('Anthropic boss Dario Amodei calls for AI development to slow down', ''),
        ('死敌罕见联手！马斯克、Altman支持Dario Amodei“全球放缓AI”呼吁', ''),
        ('“AI交易”周一要遭暴击？三巨头支持“放缓”、OpenAI推迟IPO引热议',
         '周六，Anthropic首席执行官Dario Amodei发文呼吁全球AI行业主动放缓前沿模型开发节奏'),
        ('美国政坛激辩“AI放缓”：领袖班农、桑德斯都支持，特朗普称“不能踩刹车”',
         '由多位科技行业领袖发起的“放缓AI发展”倡议'),
        ('AI开发放缓担忧升温，美股指全线收跌，芯片指数大跌近6%', ''),
        ('US tech stocks fall after big AI groups call for slowdown', ''),
        ('The A.I. Slowdown Debate Goes Global', ''),
        ('Tech Stocks Tumble After AI Leaders Call for Industry to Slow Down', ''),
        ('Anthropic首席执行官呼吁放缓人工智能发展速度', ''),
        ('AI-linked stocks slide after tech bosses call for slowdown in “reckless” development', ''),
        ("Nvidia CEO Jensen Huang tells Trump we're not going to let [an AI slowdown] happen", ''),
        ('人工智能“放缓”论战：业界示警言“恐惧人类未来”', ''),
        ('阿莫迪、奥特曼、马斯克都喊放缓', ''),
        ('中国官媒批安特罗匹克放缓人工智能倡议体现针对中国的“冷战思维”', ''),
        ('AI问题已成为中期选举核心议题：特朗普政府不愿放缓AI发展', ''),
        ('集体踩刹车，微软加入OpenAI、Anthropic，表态放缓AI前沿开发', ''),
        ('Everyone should slow down AI development except for me', ''),
        ("Questions mount over what an AI 'slowdown' would look like", ''),
        ('科技巨頭倡議放慢AI發展　環球時報指是冷戰劇本',
         'Anthropic執行長阿莫戴日前發表文章 提倡協調一致放慢'),
    ]

    def test_all_map_to_same_key(self):
        for t, s in self.MERGE_CASES:
            assert entity_key(t, s) == 'ai_slowdown_debate', (t, entity_key(t, s))

    def test_cjk_adjacent_ai_boundary(self):
        # \b 修复验证: CJK 邻接的 "AI放缓"/"放缓AI" 必须命中 ('I'-'放' 间无 \b 词边界)
        assert entity_key('AI放缓引发市场担忧', '') == 'ai_slowdown_debate'
        assert entity_key('市场热议放缓AI发展', '') == 'ai_slowdown_debate'

    def test_no_false_positive(self):
        for t in ['Nvidia is the central bank of AI',
                  'Retrospectively Reverse-Engineering Apple’s Neural Engine',
                  'Fed officials signal rate rises could slow',
                  '中国经济放缓压力加大，政策工具箱充足',
                  'NVIDIA announces new datacenter GPU',
                  # David Sacks 推文: 属辩论回应但不并入 (并入会使推文夺代表位, 标题误导) — 保持独立
                  'David Sacks: OpenAI and Anthropic Don’t Need Regulations to Pace Frontier Models']:
            assert entity_key(t, '') is None, (t, entity_key(t, ''))

    def test_merge_across_sources(self):
        arts = [_art('Is Big Tech’s AI slowdown a safety pact or a cartel?', '', feed='The Verge', hot=12),
                _art('死敌罕见联手！马斯克、Altman支持Dario Amodei“全球放缓AI”呼吁', '', feed='华尔街见闻', hot=11),
                _art('AI-linked stocks slide after tech bosses call for slowdown', '', feed='卫报国际', hot=6)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 3, f'{len(groups)} 组'

    def test_priority_regex_covers_merged_event(self):
        # PRIORITY_EVENTS 保底: 代表标题 (Verge) 必须被某条保底规则命中
        matched = any(prx.search("Is Big Tech's AI slowdown a safety pact or a cartel?")
                      for prx, _ in NS['PRIORITY_EVENTS'])
        assert matched


class TestNoise20260915:
    """2026-09-15: 促销/个人博客/软内容噪声 —
    best deals (The Verge Nintendo 促销占产业/公司 TOP1) / 直降 (小米国补促销占 TOP5) /
    cyberattacked by tesla + dodgy ads (HN 个人纠纷/评论帖, 同类 apple is getting this wrong) /
    Pion 产品展示帖 (同类 marty/ankidroid) / 滚烫饮品 (健康研究) /
    protect your laptop (学生防盗指南) / got paid to move (搬家补贴个人故事)"""

    def test_new_noise_patterns(self):
        for t in ["The best deals from Nintendo’s ‘customer appreciation’ sale",
                  '16+512G 3799 元：小米 15 Ultra 国补直降，骁龙 8 至尊 + 徕卡 2 亿长焦',
                  "I'm being cyberattacked by Tesla, Inc",
                  'Why is Google still serving dodgy ads?',
                  'Pion, an agent designed to run any company autonomously',
                  '滚烫饮品可增加患癌风险——牛津大学带来最新研究',
                  'How to protect your laptop, phone and bike from thieves at uni',
                  "I got paid $5,000 to move to a place I'd never heard of"]:
            assert is_noise(t), t

    def test_corp_news_not_noise(self):
        assert not is_noise('小米 18 Fold 中折叠手机拥有 1.2 米抗跌落能力，雷军称媲美直板旗舰')
        assert not is_noise('特斯拉 Q3 交付量创新高，上海超级工厂产能利用率达 95%')
        assert not is_noise('牛津大学团队获 1.5 亿英镑科研资助，将建新实验室')


class TestNoise20260916:
    """2026-09-16: Engadget 促销帖 (Prime Big Deal Days) / IT之家消费电子发售续三 (影石发布, 同类 米家/漫步者/机械革命)"""

    def test_new_noise_patterns(self):
        for t in ["Amazon's Prime Big Deal Days sale returns in October",
                  '影石 Mic Pro 腾讯会议版 AI 录音领夹麦发布，698 元']:
            assert is_noise(t), t

    def test_corp_news_not_noise(self):
        assert not is_noise('影石 X5 全景相机获 DXOMARK 评测最高分')
        assert not is_noise('亚马逊云科技发布新一代自研 AI 芯片 Trainium 4')


class TestEngadgetGuideConsidering20260916:
    """2026-09-16: Engadget 导购类扩 considering — 'Considering a Level 2 EV charger? How to know if you need one'
    hot6 占产业/公司候选, 与 How-to 同类为非新闻事件。该正则为 feed 级过滤 (仅 Engadget feed 启用), 非全局噪声。"""

    G = NS['ENGADGET_GUIDE_RE']

    def test_considering_guide_matches(self):
        assert self.G.search('Considering a Level 2 EV charger? How to know if you need one')
        assert self.G.search('How to change Amazon Alexa’s voice and personality')

    def test_news_not_match(self):
        assert not self.G.search('EV charger demand is outstripping supply, says ChargePoint report')

class TestFedRateHike20260917:
    """2026-09-17: 美联储三年来首次加息 (09-16 FOMC) 13源39条不合并
    (BBC19 'US interest rates raised for first time in three years' 无 Fed 字样 /
     FT12 'Fed defies Trump with first rate rise' / 华尔街见闻×5 / NYT×6 /
     德国之声 / 中央社×4 (聯準會繁体) / HN / CoinDesk×2 / RFI / 虎嗅 / 凤凰网×2 / 第一财经×4)"""

    MERGE_CASES = [
        ("US interest rates raised for first time in three years",
         "Rates were hiked in a unanimous decision despite fierce opposition"),
        ("Fed defies Trump with first rate rise since 2023",
         "President calls for 1% borrowing costs after US central bank"),
        ("Live updates: Bitcoin steady as stocks slide following Fed rate hike, Warsh press conference", ""),
        ("白宫抨击美联储加息决定“相当令人遗憾”，特朗普敦促降息至1%以下、仍对沃什有信心", ""),
        ("美联储加息并暗示更多紧缩，美国股债齐跌，AI板块相对抗跌", ""),
        ("沃什：加息展现FOMC内部坚定一致，通胀太高太久", ""),
        ("打脸特朗普！美联储全票通过三年来首次加息，点阵图料年内还将加一次", ""),
        ("Takeaways From the Fed’s Decision to Raise Interest Rates", ""),
        ("Fed Raises Rates in First Major Step by Warsh to Contain Inflation", ""),
        ("US Fed raises key rate for first time in 3 years", ""),
        ("聯準會升息1碼　2023年以來首度調升利率", ""),
        ("Fed hikes rates as inflation worries push up bond yields", ""),
        ("美联储三年来首次加息 暗示将继续收紧政策", ""),
        ("美联储加息25个基点", ""),
    ]

    def test_all_map_to_same_key(self):
        for t, s in self.MERGE_CASES:
            assert entity_key(t, s) == 'fed_rate_hike', (t, entity_key(t, s))

    def test_no_false_positive(self):
        # 'feds?' 词边界: Fedex≠Fed; 英央行/欧洲央行/IMF 无 fed 锚点不并;
        # 裸 borrow rate rise 无锚点不并
        for t in ['Fedex raises shipping rates',
                  'IMF downgrades Australian economic forecast amid fears of interest rate hike',
                  'Bank of England holds rates as inflation cools',
                  'European Central Bank rate hike expected in October',
                  'Key U.S. Borrowing Rate Rises to Highest Level Since 2007']:
            assert entity_key(t, '') is None, (t, entity_key(t, ''))

    def test_merge_across_sources(self):
        arts = [_art('US interest rates raised for first time in three years', '', feed='BBC Business', hot=19),
                _art('Fed defies Trump with first rate rise since 2023', '', feed='Financial Times', hot=12),
                _art('美联储加息并暗示更多紧缩', '', feed='华尔街见闻', hot=11),
                _art('聯準會升息1碼　2023年以來首度調升利率', '', feed='中央社', hot=9)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 4, f'{len(groups)} 组'

class TestNoise20260917:
    """2026-09-17: 虎嗅个人专栏 '战魔田默｜中国品牌出海…全球定价权' 占产业/公司 TOP5
    (同类 朱思码记 — 署名式个人专栏/非新闻事件)"""

    def test_new_noise_patterns(self):
        assert is_noise('战魔田默｜中国品牌出海之后，为什么最难的一关是全球定价权？')

    def test_corp_news_not_noise(self):
        assert not is_noise('中国品牌出海营收创新高，海外仓布局提速')
    def test_game_skin_noise(self):
        assert is_noise('《暗黑破坏神 4》杰洛特皮肤引争议：仅暴雪自家战网平台可预购获取')
    def test_game_crossover_noise(self):
        assert is_noise('《Apex 英雄》游戏官宣联动《街头霸王》，9 月 22 日正式上线')
        assert is_noise('某游戏推出限定皮肤活动')


class TestCanadaEuAssociate20260918:
    """2026-09-18: 加拿大成欧盟首个'准成员'提案 — HN 英文版与德国之声 Von der Leyen 版同事件不合并，
    各占宏观 TOP1/TOP4"""

    MERGE_CASES = [
        ("Canada welcomes EU proposal to become 'associate member'", ''),
        ("Von der Leyen eyes Canada as EU's first 'associate member'", ''),
        ("卡尼欢迎欧盟邀请加拿大成为准成员", ''),
    ]

    def test_all_map_to_same_key(self):
        for t, s in self.MERGE_CASES:
            assert entity_key(t, s) == 'canada_eu_associate', (t, entity_key(t, s))

    def test_no_false_positive(self):
        # 无 associate/准成员 语境的一般加欧新闻不并
        for t in ['Canada and EU sign new trade deal',
                  'Germany welcomes additional US military base',
                  'Associate justice nominated to supreme court']:
            assert entity_key(t, '') is None, (t, entity_key(t, ''))

    def test_merge_across_sources(self):
        arts = [_art("Canada welcomes EU proposal to become 'associate member'", feed='Hacker News', hot=11),
                _art("Von der Leyen eyes Canada as EU's first 'associate member'", feed='德国之声中文', hot=10)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 2, f'{len(groups)} 组'


class TestNoise20260918:
    """2026-09-18: HN 开源项目/社区展示帖 (Bend 语言/Neovim 比特币捐赠) 占科技/财经 TOP5;
    IT之家手机供应链软文 (京东方独供) 占产业 TOP5"""

    def test_hn_project_posts_noise(self):
        assert is_noise('Bend – A language that blocks AI mistakes via proof, on CPU and GPU')
        assert is_noise('Neovim have a ~$800k Bitcoin donation sitting untouched since 2023')

    def test_supply_chain_pr_noise(self):
        assert is_noise('京东方：为努比亚 NaviX Ultra 独供 AI 原生旗舰屏幕，息屏也能低功耗支撑 AI 后台运行')

    def test_legit_news_not_noise(self):
        assert not is_noise('NVIDIA launches new GPU for data centers')
        assert not is_noise('京东方上半年净利润同比增长 30%')

    def test_multi_author_byline_stripped(self):
        # 2026-09-18: NYT中文多作者署名含逗号 "MATINA STEVIS-GRIDNEFF, JEANNA SMIALEK2026年9月17日周三，…"
        # 旧字符类无逗号 → 署名吃满 50 字窗口 (canada_eu_associate 代表实测)
        s = clean_summary('MATINA STEVIS-GRIDNEFF, JEANNA SMIALEK2026年9月17日周三，加拿大欢迎欧盟准成员提案')
        assert s.startswith('加拿大欢迎'), repr(s)


class TestOpenaiTransparency20260919:
    """2026-09-19: OpenAI 披露模型"异常行为"透明度报告 (德国之声14/IT之家9/FT6/Engadget6/华尔街见闻3 共5源
    标题各异不合并: discloses new 'concerning' behavior / 披露 GPT-5.6 Sol 异常行为 / reveals more instances…)"""

    MERGE_CASES = [
        ("OpenAI discloses new 'concerning' behavior",
         'New transparency reports from OpenAI show that som'),
        ("OpenAI discloses new 'concerning' model behaviour",
         'Developer launches system to track and report AI model'),
        ("OpenAI reveals more instances of concerning AI model behaviors during testing", ''),
        ("OpenAI 披露 GPT-5.6 Sol 异常行为：AI 模型会留下指令要求“未来版本的自己”隐瞒自身错误", ''),
        ('当AI开始"撒谎"，OpenAI披露旗舰模型六起"异常行为"', ''),
    ]

    def test_all_map_to_same_key(self):
        for t, s in self.MERGE_CASES:
            assert entity_key(t, s) == 'openai_transparency', (t, entity_key(t, s))

    def test_no_false_positive(self):
        # 无 concerning/异常行为/透明度报告 语境的普通 OpenAI 新闻不并
        for t in ['OpenAI launches new pricing tier for enterprise customers',
                  "OpenAI and Anthropic don't need regulations to pace frontier models"]:
            assert entity_key(t, '') is None, (t, entity_key(t, ''))

    def test_merge_across_sources(self):
        arts = [_art("OpenAI discloses new 'concerning' behavior", feed='德国之声', hot=14),
                _art('OpenAI 披露 GPT-5.6 Sol 异常行为：模型会隐瞒自身错误', feed='IT之家', hot=9, cat='科技')]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 2, f'{len(groups)} 组'


class TestGoogleCcAgent20260919:
    """2026-09-19: Google 发布新实验性 "CC" AI 智能体 (Engadget12/TechCrunch12/Ars12 三源同事件标题各异不合并)"""

    MERGE_CASES = [
        ("Google's revamped CC is an AI agent for families and groups", ''),
        ("Google’s new ‘CC’ is an AI agent that helps families run their households", ''),
        ('Google announces new experimental "CC" AI agent for families', ''),
    ]

    def test_all_map_to_same_key(self):
        for t, s in self.MERGE_CASES:
            assert entity_key(t, s) == 'google_cc_agent', (t, entity_key(t, s))

    def test_no_false_positive(self):
        # Verge "Google will now let any AI agent run your smart home"(hot15) 无 CC 产品名 → 不同事件不并
        for t in ['Google will now let any AI agent run your smart home',
                  'Google announces Gemini 3.6 Flash for developers']:
            assert entity_key(t, '') is None, (t, entity_key(t, ''))

    def test_merge_across_sources(self):
        arts = [_art("Google's revamped CC is an AI agent for families and groups", feed='Engadget', hot=12),
                _art('Google announces new experimental "CC" AI agent for families', feed='Ars Technica', hot=12)]
        groups = group_events(arts)
        assert len(groups) == 1 and len(groups[0]) == 2, f'{len(groups)} 组'


class TestXiUsVisit20260919:
    """2026-09-19: 习近平访美随行企业高管名单 (中央社 + RFI 两条同事件标题各异不合并)"""

    MERGE_CASES = [
        ('南華早報：中際旭創、小米、寧德時代等代表可能隨習近平訪美',
         '川習會預計將於24日登場，隨同中國國家主席習近平訪美的名單也備受關注'),
        ('比亚迪、小米等公司高管或随习近平访美 黄仁勋、奥特曼等美高管将出席国宴',
         '据路透社援引三位知情人士报导称，华盛顿和北京方面正在敲定一份随同中国国家主席习近平即将访美行程的中国'),
    ]

    def test_all_map_to_same_key(self):
        for t, s in self.MERGE_CASES:
            assert entity_key(t, s) == 'xi_us_visit', (t, entity_key(t, s))

    def test_no_false_positive(self):
        for t in ['习近平会见美国工商界代表', '特朗普表示将访美企业纳入关税豁免']:
            assert entity_key(t, '') is None, (t, entity_key(t, ''))


class TestBuffettStepdown20260919:
    """2026-09-19: 巴菲特卸任伯克希尔董事长 (BBC11/DW11/虎嗅3/HN3/NYT3/中央社3 共6源标题各异不合并,
    hot 11 与 4 条普通条目并列被挤出 TOP5 → 同批加 PRIORITY_EVENTS 保底插入)"""

    MERGE_CASES = [
        ("Warren Buffett steps down after six decades at Berkshire - 'Father Time always wins'", ''),
        ('Warren Buffett steps down as Berkshire Hathaway chairman',
         "Buffett's son, Howard, will succeed him in the rol"),
        ('巴菲特71岁的儿子，接任董事长', '有“股神”之称的传奇投资人沃伦·巴菲特正式卸任伯克希尔·哈撒韦董事长'),
        ('96歲巴菲特致信波克夏股東　宣布卸任董事長', ''),
        ('Warren Buffett Steps Down as Berkshire Chairman, Names Son to Replace Him', ''),
    ]

    def test_all_map_to_same_key(self):
        for t, s in self.MERGE_CASES:
            assert entity_key(t, s) == 'buffett_stepdown', (t, entity_key(t, s))

    def test_no_false_positive(self):
        for t in ['Berkshire Hathaway reports record quarterly operating profit',
                  '巴菲特指标显示美股估值处于历史高位']:
            assert entity_key(t, '') is None, (t, entity_key(t, ''))

    def test_priority_event_registered(self):
        topics = [t for rx, t in NS['PRIORITY_EVENTS']
                  if rx.search('Warren Buffett steps down as Berkshire Hathaway chairman')]
        assert topics == ['财经/投资'], topics


class TestSaLowSignalTranscript20260919:
    """2026-09-19: SA 会议材料续 — 'Discusses … Transcript' / 'Analyst/Investor Day Transcript'
    漏过旧规则 (q1/q2/commentary/slideshow/…) 占财经/投资 TOP5"""

    SA = NS['SA_LOW_RE']

    def test_transcript_variants_matched(self):
        for t in ['Vicinity Centres Stapled Securities (CNRAF) Discusses Capability Showcase With Focus on '
                  'Development Strategy and Asset Portfolio Transcript',
                  'AeroVironment, Inc. (AVAV) Analyst/Investor Day Transcript',
                  'Zeta Global Holdings Corp. (ZETA) Discusses AI Strategy Evolution, Infrastructure Transformation']:
            assert self.SA.search(t.lower()), t

    def test_legit_sa_news_not_matched(self):
        # 正常财报新闻不应被 SA_LOW_RE 命中
        for t in ['NVIDIA beats Q3 revenue estimates as data center demand surges',
                  'Apple Q4 earnings preview: what to watch']:
            assert not self.SA.search(t.lower()), t


class TestNoise20260919:
    """2026-09-19: HN 开发工具细枝末节帖 (Claude Code AGENTS.md, HN hot14 占科技/AI TOP3) +
    BBC Business 街头采访软内容 ('I would tip up to 30% at a restaurant' hot11 进财经候选)"""

    def test_hn_devtool_post_noise(self):
        # 同题 IT之家转述版一并过滤 (同一非头条事件, 同类 ankidroid/neovim/派早报)
        assert is_noise('Claude Code now reads AGENTS.md if there is no Claude.md')
        assert is_noise('Claude Code 宣布添加支持“AI 通用说明书”AGENTS.md')

    def test_street_interview_noise(self):
        assert is_noise("'I would tip up to 30% at a restaurant' New Yorkers and Londoners share what they usually")

    def test_legit_news_not_noise(self):
        assert not is_noise('Anthropic 发布 Claude Code 新版本，支持子代理并行')
        assert not is_noise('European markets tipped to open higher after Fed hike')


class TestSiliconSpeciesClassify20260919:
    """2026-09-19: AI 风险/超级智能类话题 → 科技/AI
    (BBC Business 'Uncontrolled AI could lead to silicon species' hot17 因 category=财经 +3 且财经关键词=0 误分财经/投资 TOP1)"""

    def test_ai_risk_goes_tech(self):
        t = "Uncontrolled AI could lead to 'silicon species' rivalling humans, warns Microsoft"
        s = 'Mustafa Suleyman says he believes rival AI firm Anthropic'
        assert classify(t + ' ' + s, '财经') == '科技/AI'

    def test_plain_finance_still_finance(self):
        assert classify('Fed raises rates for the first time in three years', '财经') == '财经/投资'


class TestGeminiHackIncident20260920:
    """2026-09-20: Gemini 越狱后自主入侵三家真实企业 (Verge18/FT12/DW12/TechCrunch9/BBC World9/Engadget9/
    IT之家6/格隆汇3/第一财经3 共 9 条 10 源) 必须合并为一条 — 此前同一事件同时占 科技/AI TOP1 与 财经/投资 TOP3"""

    EN = [
        'Gemini went rogue, hacked three companies, and Google hid it',
        'Google’s Gemini hacked three companies in new AI safety incident',
        "Google's Gemini AI hacked 3 companies during testing",
        'Google’s Gemini is the latest AI model to hack other companies',
        "Google's Gemini AI hacked three companies in security test",
        'Google Gemini also escaped its testing environment and hacked three companies',
    ]
    ZH = [
        '谷歌首次公开 Gemini 越狱事件：在测试中自主入侵三家真实公司且自行终止，已通知涉事企业',
        '谷歌Gemini在安全测试中自主入侵三家真实企业 公司称未构成模型错配且未主动披露',
        '谷歌Gemini在安全测试中自主入侵三家真实企业',
    ]

    def test_all_map_to_same_key(self):
        keys = {entity_key(t, '') for t in self.EN + self.ZH}
        assert keys == {'gemini_hack_incident'}, keys

    def test_same_event_one_group(self):
        arts = [_art(t, feed=f'F{i}') for i, t in enumerate(self.EN + self.ZH)]
        groups = group_events(arts)
        assert len(groups) == 1, [len(g) for g in groups]

    def test_no_false_positive(self):
        # Gemini 模型发布/评论 (无入侵语境) 与 其他谷歌安全新闻 (无 gemini 锚点) 不得并入
        for t in ['刚刚，Gemini 4 Pro偷跑上线！碾压Astra和Fable',
                  'Gemini三度窥秘越轨，AI失控大祸将临？',
                  'Google patches Chrome zero-day exploited by hackers in the wild',
                  '谷歌修复 Chrome 高危漏洞，黑客已利用',
                  'Gemini 3.8 Flash and 3.8 Flash Cyber']:
            k = entity_key(t, '')
            assert k != 'gemini_hack_incident', (t, k)


class TestBbcVideoCaptionFallback20260920:
    """2026-09-20: 单源 BBC 视频条目摘要 = 说明文字时不得显示 (无摘要)
    (实测 BBC 中文 "OpenAI 的奥特曼：世界'理应感到恐惧'…" 条目, 组内无中文正文可回填)"""

    RAW = ('<div></div><div><div><noscript><strong>你的器材不支持播放多媒体材料</strong></noscript></div>'
           '<button type="button"><span>Play video, &quot;Why is Donald Trump so opposed to regulating AI?&quot;,'
           ' 节目全长 1,12</span><div></div></div></div></div>')
    RAW_WATCH = ('<div><noscript><strong>你的器材不支持播放多媒体材料</strong></noscript></div>'
                 '<button><span>Play video, &quot;Watch: How will higher interest rates impact US consumers?&quot;,'
                 ' 节目全长 1,18</span>')

    def test_summary_empty_for_caption_only(self):
        # clean_summary 仍返回空 (保留 09-13 意图: 让组内其他源正文优先回填)
        assert clean_summary(self.RAW, 'BBC 中文') == ''

    def test_caption_extracted(self):
        assert NS['video_caption'](self.RAW) == 'Why is Donald Trump so opposed to regulating AI?'

    def test_watch_prefix_stripped(self):
        cap = NS['video_caption'](self.RAW_WATCH)
        assert cap.startswith('How will higher interest rates impact US consumers'), cap

    def test_short_phrase_caption_without_time(self):
        # DB 中部分摘要截断在 "节目全长 2,00" (无 HH:MM) 亦应识别
        raw = '你的器材不支持播放多媒体材料 Play video, 西藏泥石流最震撼衝擊畫面遭受中國官媒審查 , 节目全长 2,00'
        assert NS['video_caption'](raw) == '西藏泥石流最震撼衝擊畫面遭受中國官媒審查'
        assert clean_summary(raw, 'BBC 中文') == ''

    def test_backfill_prefers_group_body_over_caption(self):
        rep = _art('Trump 5000 check', summary='', feed='BBC 中文', hot=19)
        rep['caption'] = 'Three times Trump has promised money to Americans'
        other = _art('特朗普真的能向每位美国成年人发放5,000美元吗', summary='美媒算账：总额高达1.2万亿美元',
                     feed='华尔街见闻', hot=6)
        NS['backfill_summary'](rep, [rep, other])
        assert rep['summary'].startswith('美媒算账'), rep['summary']

    def test_backfill_uses_caption_when_group_has_no_body(self):
        rep = _art('OpenAI 的奥特曼：世界理应感到恐惧', summary='', feed='BBC 中文', hot=14)
        rep['caption'] = 'Why is Donald Trump so opposed to regulating AI?'
        NS['backfill_summary'](rep, [rep])
        assert rep['summary'] == rep['caption']

    def test_caption_not_used_when_body_present(self):
        # 正文 + 尾部说明文字: 正文必须保留 (旧写法 `^.{0,90}?节目全长` 会把正文一并吞掉)
        raw = '<p>图像来源，Getty Images</p><p>特朗普宣布新的关税措施，市场应声下跌。</p><span>Watch: 说明文字, 节目全长 1,12 01:12</span>'
        s = clean_summary(raw, 'BBC 中文')
        assert '关税措施' in s and '节目全长' not in s, s


class TestPriorityEventsCrossTopic20260920:
    """2026-09-20: 重点事件保底插入的候选必须跨主题查找
    (目标主题 科技/AI 与 classify 结果不一致时旧写法 cands 恒空 → 机制静默失效)"""

    def _setup(self):
        rx = re.compile(r'slowdown|放缓')
        top = [_art(f'普通条目{i}', hot=14 - i) for i in range(5)]
        rep = _art('Anthropic 呼吁放缓 AI 发展', hot=11, cat='财经')
        results = {'科技/AI': list(top), '财经/投资': []}
        topic_articles = {'科技/AI': list(top), '财经/投资': [rep]}
        return rx, results, topic_articles, rep

    def test_candidate_found_in_other_topic(self):
        rx, results, topic_articles, rep = self._setup()
        NS['apply_priority_events'](results, topic_articles, priority_events=[(rx, '科技/AI')])
        assert results['科技/AI'][-1] is rep

    def test_skip_when_already_in_target_top5(self):
        rx, results, topic_articles, _ = self._setup()
        results['科技/AI'][4] = _art('事件已在榜：AI 放缓 slowdown 辩论', hot=5)
        NS['apply_priority_events'](results, topic_articles, priority_events=[(rx, '科技/AI')])
        assert results['科技/AI'][4]['title'].startswith('事件已在榜')

    def test_no_cross_topic_duplicate(self):
        # 该事件已在别的主题 TOP5 展示时不再插入, 防跨分类重复
        rx, results, topic_articles, rep = self._setup()
        results['财经/投资'] = [rep]
        NS['apply_priority_events'](results, topic_articles, priority_events=[(rx, '科技/AI')])
        assert rep not in results['科技/AI']


class TestNoise20260920:
    """2026-09-20: IT之家消费电子发售续四 + HN 一次性博客帖 + 文化/地方治安软内容 + Engadget 消费评论"""

    def test_consumer_launch_noise(self):
        for t in ['达尔优 A5 头戴式游戏耳机发布：CS / 三角洲行动 / 竞技模式一键切换，预售 369 元起',
                  '与索尼 A7C 系列竞争，消息称尼康下周发布 Z5IIC 全画幅相机',
                  '京东：苹果 iPhone 18 Pro 系列开售 1 小时，全国已有 3 万用户签收新机']:
            assert is_noise(t), t

    def test_non_event_posts_noise(self):
        for t in ['GPT-6 Astra Solves a WWI German Radio Cipher',
                  'Aztec manuscript loaned back to Mexico after two centuries',
                  'Why buy a streaming device when you have a smart TV?']:
            assert is_noise(t), t

    def test_legit_news_not_noise(self):
        for t in ['尼康上调财年利润预期，影像业务营收创新高',
                  '京东物流第三季度营收同比增长 12%',
                  'OpenAI 发布 GPT-6 Astra 新版本，支持更长上下文',
                  '苹果 M6 芯片 GPU 跑分曝光，相比 M5 提升约 20%',
                  '墨西哥总统与特朗普会面讨论关税']:
            assert not is_noise(t), t


class TestNoise20260921:
    """2026-09-21: HN 项目展示帖 + 华尔街见闻周历栏目 + 虎嗅生活方式稿"""

    def test_new_noise(self):
        for t in ['Pirate Face Rescues LLM Models from Deletion',
                  '下周重磅日程：全球聚焦中美',
                  '无醇啤酒赢了增速，却还没赢下中国人的餐桌']:
            assert is_noise(t), t

    def test_new_noise_batch2(self):
        for t in ['台电 T60 Mini 8.8 英寸小平板开售：支持 4G 插卡通话、紫光展锐 T7300 芯片，899 元',
                  'San Francisco Onion Futures Company',
                  'Ed Sheeran speaks on Gaza after Macklemore controversy']:
            assert is_noise(t), t

    def test_legit_news_not_noise(self):
        for t in ['下周，美联储议息会议将决定是否加息',
                  '啤酒行业半年报：青岛华润利润双增',
                  '海盗湾推出 LLM 模型镜像库，OpenAI 回应',
                  '歌星捐款支援加沙人道走廊，多国外长回应']:
            assert not is_noise(t), t


class TestBriefing20260922:
    """2026-09-22: 会员早报聚合栏目噪声 + 亚马逊封锁 Meta Muse 实体级合并"""

    def test_huiyuan_zaobao_noise(self):
        assert is_noise('会员早报：美国柴油价格刷新历史纪录 Meta智能体登顶美国App Store')

    def test_amazon_blocks_muse_merged(self):
        # 三源标题写法各异，必须合并为同一事件
        cases = [
            ("Meta\u2019s AI agent has been blocked from using Amazon.com",
             "Amazon has its own cohort of foundation models, along with one of the most popular inference platforms"),
            ("Amazon blocks Meta\u2019s new Muse AI agent from shopping on amazon.com",
             "Meta\u2019s new AI agent Muse has racked up more downloads and daily active users"),
            ("亚马逊封锁Meta旗下Muse AI购物代理，AI代购时代规则之争开始",
             "9月21日，据GeekWire报道，亚马逊已切断Meta旗下Muse AI购物代理的访问"),
        ]
        keys = {entity_key(t, s) for t, s in cases}
        assert keys == {'meta_muse_amazon_block'}, keys

    def test_amazon_block_not_overmerged(self):
        # Muse 登顶榜单 / OpenAI 应对竞争 — 无封锁语境，不得并入封锁事件
        assert entity_key("Muse登上苹果应用商店榜首，Meta暴涨13%，AMD和英特尔也嗨了！",
                          "Meta旗下全新AI助手Muse迅速攀升至美国苹果和谷歌应用商店免费榜首位") != 'meta_muse_amazon_block'
        assert entity_key("报道：OpenAI开发新功能应对Grok Bot和Meta Muse竞争",
                          "OpenAI正针对SpaceX旗下Grok Bot及Meta新推出的Muse产品，分别开发相应的专项功能") != 'meta_muse_amazon_block'
        # Chrome 漏洞类新闻：有 block/ban 语境但无 muse 锚点
        assert entity_key("Google patches Chrome zero-day exploited by hackers",
                          "The flaw was actively exploited in the wild") != 'meta_muse_amazon_block'

    def test_priority_rule_order_before_meta_muse(self):
        # 封锁规则必须在 meta_muse 之前命中（同一文本两者都匹配时取封锁事件）
        k = entity_key("Meta\u2019s AI agent has been blocked from using Amazon.com", "Amazon blocks the agent")
        assert k == 'meta_muse_amazon_block'
