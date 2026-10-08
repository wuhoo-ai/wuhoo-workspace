"""2026-10-08 回归：诺贝尔物理/化学奖实体合并、Surface Laptop Ultra 发布会合并、NOISE 新组。"""
import importlib.util
import pathlib

SPEC_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "daily_briefing.py"
spec = importlib.util.spec_from_file_location("daily_briefing", SPEC_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

entity_key = mod.entity_key
is_noise = mod.is_noise


class TestNobelPhysics:
    def test_huxiu(self):
        assert entity_key('他在南极造了座望远镜，拿了诺奖，自己却一次南极都没去过',
                          '今年的诺贝尔物理学奖，颁给了一个一辈子没做过实验的人') == 'nobel_physics_2026'

    def test_wscn(self):
        assert entity_key('Francis Halzen独揽2026年诺贝尔物理学奖：主导南极“冰立方”项目', '') == 'nobel_physics_2026'

    def test_dw_english(self):
        assert entity_key('Nobel Physics Prize goes to Francis Halzen for neutrino work', '') == 'nobel_physics_2026'

    def test_bbc_ghost_particles(self):
        assert entity_key("'Ghost particles' from space telescope wins physics Nobel",
                          'Belgian physicist Prof Francis Halzen has won') == 'nobel_physics_2026'

    def test_itjia(self):
        assert entity_key('2026 年诺贝尔物理学奖揭晓！34 年来首次单人获奖',
                          '之家 10 月 6 日消息，2026 年诺贝尔物理学奖正式揭晓') == 'nobel_physics_2026'

    def test_solidot(self):
        assert entity_key('2026 年诺贝尔物理奖授予了冰立方中微子天文台提出者 Francis Halzen', '') == 'nobel_physics_2026'

    def test_no_false_merge_economist_ai(self):
        # 诺奖经济学家背书 AI 就业预测 —— 非物理奖事件
        assert entity_key('10 年内预估仅 5%：诺奖经济学家背书，AI 不会大规模抢走你的饭碗',
                          '援引诺贝尔经济学奖得主达龙·阿西莫格鲁的预测') != 'nobel_physics_2026'

    def test_no_false_merge_peace(self):
        assert entity_key('特朗普自称解决了八场战争，暗示如果诺贝尔和平奖不授予他将是“一大失误”', '') != 'nobel_physics_2026'


class TestNobelChemistry:
    def test_wscn(self):
        assert entity_key('2026年诺贝尔化学奖揭晓：两位科学家破解生命手性之谜', '') == 'nobel_chemistry_2026'

    def test_dw(self):
        assert entity_key('Nobel Prize in Chemistry goes to Henri B. Kagan, Kenso Soai', '') == 'nobel_chemistry_2026'

    def test_rfi(self):
        assert entity_key('2026年诺贝尔化学奖揭晓 法国和日本科学家获奖 - RFI', '') == 'nobel_chemistry_2026'

    def test_cna_traditional(self):
        # 中央社繁体（若标题为繁体化[学學]容错）
        assert entity_key('瑞典皇家科学院宣布2026年諾貝爾化學獎', '') == 'nobel_chemistry_2026'

    def test_ars(self):
        assert entity_key('Chemistry Nobel goes to reactions like those that gave life a hand', '') == 'nobel_chemistry_2026'

    def test_no_false_merge_physics(self):
        assert entity_key('2026 年诺贝尔物理学奖揭晓！34 年来首次单人获奖', '') != 'nobel_chemistry_2026'


class TestSurfaceLaptopUltra:
    def test_itjia_price(self):
        assert entity_key('微软 Surface Laptop Ultra 售价公布：起价 21988 元',
                          '之家 10 月 8 日消息，微软中国商城今天上架') == 'surface_laptop_ultra'

    def test_techcrunch(self):
        assert entity_key('Microsoft releases new Nvidia-chip AI PCs with revamped Windows 11',
                          'Microsoft revealed the specs and price for its Surf') == 'surface_laptop_ultra'

    def test_verge_event(self):
        assert entity_key('Everything announced at Microsoft&#8217;s Surface Laptop Ultra event', '') == 'surface_laptop_ultra'

    def test_wscn(self):
        assert entity_key('微软携手英伟达发布Surface旗舰新机，同步推出“龙虾”个人助手Scout', '') == 'surface_laptop_ultra'

    def test_itjia_copilot(self):
        assert entity_key('GitHub Copilot 不再纯云端 AI 模型：Surface Laptop Ultra 本地推理吞吐量最高每秒 63 词元', '') == 'surface_laptop_ultra'

    def test_dell_not_merged(self):
        # 戴尔 XPS 16 配 RTX Spark —— 另一厂商独立公告，无微软锚点不并
        assert entity_key('戴尔推出 XPS 16 Creator Edition 笔记本：16 英寸触控屏、18 核 RTX Spark',
                          '戴尔今天（10 月 8 日）在 X 平台发布博文') != 'surface_laptop_ultra'


class TestNoise20261008:
    def test_bbb_chinese_social(self):
        assert is_noise('台北同志酒吧遭搜查 警员歧视言论惹争议') is True

    def test_pushkin_villa_feature(self):
        assert is_noise('普京黑海别墅：不怎么用的俄罗斯元首行宫为何要暗地重建？') is True

    def test_amazon_flat_buttocks(self):
        assert is_noise("How to find out if Amazon thinks you have 'flat buttocks'") is True

    def test_verge_percent_off(self):
        assert is_noise("Amazon's last-gen Kindle Paperwhite is 30 percent off") is True

    def test_huxiu_nobel_training_feature(self):
        assert is_noise('日本为何不断产生诺奖科学家？答案可能不在“培养”二字') is True

    def test_normal_news_not_filtered(self):
        # 正常关税百分比新闻不命中 percent off（动词式，无 off 尾）
        assert is_noise('Trump tariffs on China cut by 30 percent after Geneva talks') is False


    def test_verge_alexa_aux(self):
        assert is_noise('Alexa can\'t control the aux input on Amazon Echo speakers anymore') is True

    def test_cna_immigrant_rich_list(self):
        assert is_noise('富比世美國移民富豪榜出爐 馬斯克居冠、黃仁勳排第3') is True


class TestEmmysPrimeVideo:
    def test_itjia_chinese(self):
        assert entity_key('取代四大电视网"轮播模式"，亚马逊 Prime Video 拿下艾美奖全球独家直播权', '') == 'emmys_prime_video'

    def test_techcrunch(self):
        assert entity_key('Emmys will move from broadcast TV to Prime Video in 2027', '') == 'emmys_prime_video'

    def test_engadget(self):
        assert entity_key('The Emmy Awards are moving to Prime Video in 2027', '') == 'emmys_prime_video'


class TestEarningsClassify:
    def test_jetbrains_revenue_to_industry(self):
        c = mod.classify('JetBrains reports revenue growth, net financial loss for 2025', '科技')
        assert c == '产业/公司'

    def test_market_breadth_stays_finance(self):
        # 财经源市场稿（category=财经 +3）不被财报规则拉去产业/公司
        c = mod.classify('Global bonds sell-off, revenue growth expectations unchanged, stocks near record', '财经')
        assert c == '财经/投资'
