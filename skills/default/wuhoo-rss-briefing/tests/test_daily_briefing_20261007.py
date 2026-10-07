"""2026-10-07 实体合并回归：EmbeddingGemma 2 发布 / OpenAI 数学成果 / ChatGPT 欧盟水印 / 德国前情报局长被捕。"""
import importlib.util
import pathlib

SPEC_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "daily_briefing.py"
spec = importlib.util.spec_from_file_location("daily_briefing", SPEC_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

entity_key = mod.entity_key


class TestEmbeddingGemma:
    def test_hn_bare_title(self):
        assert entity_key('EmbeddingGemma 2: An open, lightweight multimodal embedding model', '') == 'embeddinggemma_2'

    def test_chinese_itjia(self):
        assert entity_key('谷歌推出 EmbeddingGemma 2：支持多模态、7.4 亿参数量化手机端运行只需 191MB 内存',
                          '之家 10 月 7 日消息，去年谷歌推出了 EmbeddingGemma') == 'embeddinggemma_2'

    def test_chinese_wscn(self):
        assert entity_key('谷歌发布EmbeddingGemma 2：7.4亿参数多模态嵌入模型，主打端侧隐私搜索',
                          '谷歌于周一推出EmbeddingGemma 2') == 'embeddinggemma_2'


class TestOpenAIMath:
    def test_blog_version(self):
        assert entity_key('Sharing AI progress in mathematics',
                          'OpenAI publishes new results on open problems in m') == 'openai_math_progress'

    def test_hn_version(self):
        assert entity_key('Sharing AI Progress in Mathematics',
                          'https://github.com/openai/math') == 'openai_math_progress'


class TestOpenAIWatermark:
    def test_verge(self):
        assert entity_key('OpenAI is adding text watermarking in ChatGPT and Codex',
                          'An invisible, machine-readable watermark in text o') == 'openai_eu_watermark'

    def test_itjia_chinese(self):
        assert entity_key('OpenAI 将在欧盟为 ChatGPT 和 Codex 文本输出添加隐形水印',
                          '之家 10 月 5 日消息，OpenAI 今日宣布') == 'openai_eu_watermark'

    def test_ars(self):
        assert entity_key("OpenAI will watermark ChatGPT outputs by default—but only in the EU", '') == 'openai_eu_watermark'


class TestGermanySpyArrest:
    def test_bbc_world(self):
        assert entity_key('Former German spy chief arrested for espionage and treason',
                          'August Hanning is accused of obtaining classified information for a foreign power') == 'germany_spy_arrest'

    def test_dw_allegations(self):
        assert entity_key('Germany shaken by espionage and treason allegations',
                          "The former head of Germany's foreign intelligence service, the BND, has been accu") == 'germany_spy_arrest'

    def test_dw_chinese(self):
        assert entity_key('为钱卖国？德国前情报局长被捕', '') == 'germany_spy_arrest'

    def test_hn(self):
        assert entity_key('Former German spy chief arrested for attempted treason',
                          'https://www.reuters.com/business/finance/former-german-spy-chief-detained-s') == 'germany_spy_arrest'

    # ---- 防误并 ----
    def test_spy_chief_warns_not_merged(self):
        # 现任局长警告俄冲突风险 —— 无逮捕语境，独立事件
        assert entity_key('Germany news: Spy chief warns Russia conflict risk growing',
                          'Moscow is already waging a "shadow war" against Eu') != 'germany_spy_arrest'

    def test_fbi_woman_spying_not_merged(self):
        # FBI 逮捕涉华女性线人 —— 无 spy chief/hanning 锚点
        assert entity_key('US: FBI arrests woman accused of spying for China',
                          'A California woman was arrested at Los Angeles International Airport') != 'germany_spy_arrest'

    def test_trump_spy_boss_taskforce_not_merged(self):
        # 特朗普任命情报头子主管 AI 工作组 —— 无逮捕词
        assert entity_key('Trump chooses top spy boss to run new AI taskforce',
                          'The US president said his national intelligence chief will lead') != 'germany_spy_arrest'

    def test_canam_spyder_not_merged(self):
        assert entity_key('How Trump’s Tariff War With Canada Ensnared the Can-Am Spyder',
                          'The Can-Am Spyder has a devoted fan base') != 'germany_spy_arrest'
