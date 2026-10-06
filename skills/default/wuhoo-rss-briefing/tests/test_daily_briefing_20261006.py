"""2026-10-06 噪声回归：BBC 健康特稿/BBC 解释性特稿变体/CoinDesk 周度栏目/游戏停服/中央社劳工人物稿。"""
import importlib.util
import pathlib

SPEC_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "daily_briefing.py"
spec = importlib.util.spec_from_file_location("daily_briefing", SPEC_PATH)
NS = {}
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NS.update({k: getattr(mod, k) for k in dir(mod)})

is_noise = NS['is_noise']


class TestNoise20261006:
    def test_bbc_motion_sickness_explainer(self):
        # 实测占产业/公司 TOP1 (无摘要)
        assert is_noise('坐电动车更容易晕车？专家解释可能的原因和舒缓方法')

    def test_bbc_why_prepare_explainer(self):
        # 实测占宏观政策 TOP4 (无摘要)
        assert is_noise('加拿大为何要为（概率极小的）美国入侵做准备')

    def test_coindesk_week_ahead_column(self):
        # 周度前瞻栏目 (同类 早餐FM/会员早报/下周重磅日程)
        assert is_noise('Technicals signal bitcoin shift, Ethereum gears up for Glamsterdam: Crypto Week Ahead')

    def test_game_service_shutdown(self):
        # 游戏停服公告 (同类 gta/暗黑破坏神)
        assert is_noise('运营约 3 年，SE 跨平台游戏《最终幻想 7：永恒危机》将于 10 月 7 日停服')

    def test_cna_labor_activist(self):
        # 中央社社会新闻误入产业/公司
        assert is_noise('記錄勞權事件遭刪  中國自媒體人馮睿傳被拘')

    def test_box_office_entertainment(self):
        # 国庆档电影票房 (娱乐数据误入产业/公司, 旧 票房破/五一档票房 不覆盖)
        assert is_noise('连续 4 天单日破亿，2026 国庆档电影票房已超 7 亿')

    def test_no_false_positive(self):
        # 真新闻不受影响: 比亚迪出海/英伟达供应链/特斯拉财报措辞
        assert not is_noise('比亚迪 Racco 电动微型车将走出日本，率先登陆斯里兰卡、中国澳门')
        assert not is_noise('英伟达 RTX Spark 笔记本 OLED 屏幕供应商曝光：三星六款、LG 一款')
        assert not is_noise('OpenAI is adding text watermarking in ChatGPT and Codex')
        assert not is_noise('特斯拉第四季度财报下周公布，分析师预期交付量创纪录')
