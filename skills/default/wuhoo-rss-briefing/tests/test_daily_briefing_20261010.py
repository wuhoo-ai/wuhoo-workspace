"""2026-10-10 回归：OpenAI 解雇泄密事件公开信后续并入、中欧贸易缓和实体合并、诺奖文学奖/导购/配件噪声。"""
import importlib.util
import pathlib
import io
import contextlib

SPEC_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "daily_briefing.py"
spec = importlib.util.spec_from_file_location("daily_briefing_20261010", SPEC_PATH)
mod = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(mod)

entity_key = mod.entity_key
is_noise = mod.is_noise


class TestOpenAIFiringsDisputeMerge:
    """09-22 解雇泄密事件的 10-09 公开信反驳后续报道须并入同组（拆占科技TOP3+财经TOP4 两榜）。"""

    def test_engadget_open_letter(self):
        assert entity_key(
            "Fired OpenAI safety researchers dispute their dismissals in open letter",
            "Three OpenAI researchers said their firings may have a 'chilling' effect on employees.",
        ) == "openai_data_leak_firings"

    def test_bbc_let_go(self):
        assert entity_key(
            "Fired OpenAI researchers say they were let go for 'prioritising safety'",
            "The AI firm instead claims the researchers were fired for mishandling sensitive information.",
        ) == "openai_data_leak_firings"

    def test_techcrunch_misconduct(self):
        assert entity_key(
            "Fired OpenAI safety researchers dispute misconduct claims, warn of chilling effect",
            "Three fired OpenAI safety researchers dispute allegations of mishandling sensitive",
        ) == "openai_data_leak_firings"

    def test_original_bbc_fires(self):
        assert entity_key(
            "OpenAI fires workers for mishandling sensitive information", ""
        ) == "openai_data_leak_firings"

    def test_robinson_stays_separate(self):
        """辞职死谏是独立事件，规则在前抢先。"""
        assert entity_key(
            "OpenAI safety veteran David Robinson resigns saying the culture is broken", ""
        ) == "openai_robinson_resign"

    def test_wildfire_not_merged(self):
        assert entity_key("Wildfires force evacuation in Los Angeles this summer", "") is None

    def test_trump_fires_fed_not_merged(self):
        assert entity_key("Trump fires Federal Reserve officer Lisa Cook", "") is None


class TestEuChinaTradeDeescalation:
    """10-08/09 中欧贸易争端缓和（电动车出口限制）3 源拆占宏观 TOP4-5 → 合并。"""

    def test_dw_envoy(self):
        assert entity_key("EU envoy in China to avert trade war", "") == "eu_china_trade_deescalation"

    def test_nyt_step_back(self):
        assert entity_key(
            "China and Europe Step Back From Trade War With Limits on Chinese Car Exports", ""
        ) == "eu_china_trade_deescalation"

    def test_guardra_minerals(self):
        assert entity_key(
            "EU 'pulling out all stops' with minerals projects as it tries to avert China trade war", ""
        ) == "eu_china_trade_deescalation"

    def test_chinese_variant(self):
        assert entity_key("中欧贸易战缓和 双方同意限制中国电动车出口", "") == "eu_china_trade_deescalation"

    def test_us_canada_stays_separate(self):
        assert entity_key("US-Canada trade war escalates with dairy import ban", "") == "us_canada_trade_war"

    def test_eu_china_summit_no_trigger(self):
        assert entity_key("中欧领导人会晤讨论气候合作", "") is None

    def test_tariff_ruling_no_trigger(self):
        """终裁报道无 avert/step back/出口限制 缓和锚点不并（不同事件）。"""
        assert entity_key("欧盟对华电动车关税终裁", "") is None


class TestNoise20261010:
    def test_nobel_literature(self):
        assert is_noise("2026 年诺贝尔文学奖揭晓：加拿大作家安妮 · 卡森获奖".lower())
        assert is_noise("Nobel Prize in Literature goes to Canada's Anne Carson".lower())

    def test_nobel_literature_anti(self):
        assert not is_noise("安妮卡森新诗集在中国出版发行".lower())

    def test_alphacool_cooling_block(self):
        assert is_noise("Alphacool 带来多款 GPU 单槽冷头，支持 NVIDIA、AMD 专业显卡".lower())

    def test_double11_promo(self):
        assert is_noise("真正的制热无需电辅热：小米空调 11.11 强劲风 1.5 匹 1850 元，立式 3 匹 4119 元新低".lower())

    def test_double11_anti(self):
        assert not is_noise("双十一全网零售额创历史新高 各平台公布战报".lower())

    def test_zuck_image_problem(self):
        assert is_noise("Mark Zuckerberg has an image problem - so why is Meta's business booming?".lower())

    def test_earnings_anti(self):
        assert not is_noise("小米发布2026年第三季度财报营收增长".lower())


class TestOpenAIRevenueShortfall:
    """10-08 FT 独家：OpenAI 实际年化营收低于此前信号，HN 英文裸标题与 IT之家中文版拆占两榜。"""

    def test_hn_english(self):
        assert entity_key(
            "OpenAI annualised revenues $20B less than previously signalled", ""
        ) == "openai_revenue_shortfall"

    def test_itjia_chinese(self):
        assert entity_key(
            "OpenAI 年化营收被曝接近 500 亿美元，比预期少了约 200 亿", ""
        ) == "openai_revenue_shortfall"

    def test_ipo_stays_separate(self):
        assert entity_key("OpenAI to raise $30B at $500B valuation, IPO delayed", "") == "openai_ipo_delay"


class TestTrailerNoise:
    def test_altruists_trailer(self):
        assert is_noise("watch the trailer for 'the altruists,' netflix's show about the ftx scandal")

    def test_netflix_earnings_anti(self):
        assert not is_noise("netflix reports record quarterly revenue growth")


class TestMonthlyRoundupNoise:
    def test_announced_so_far(self):
        assert is_noise("everything amazon has announced so far in october 2026")

    def test_plain_news_anti(self):
        assert not is_noise("amazon announces new data center investment in ohio")
