# 2026-10-25 回归: 四条 NOISE 补漏
# ①华尔街见闻观点栏目文 ②BBC Business 个人叙事 ③BBC 中文解释性特稿 ④IT之家'预热:'导购稿
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from daily_briefing import is_noise

LQ = '\u201c'  # 中文弯引号用码位写, 防写入通道转成 ASCII 引号破坏字符串
RQ = '\u201d'


def test_见闻观点栏目文被过滤():
    assert is_noise(f'从{LQ}稳赚不赔{RQ}到{LQ}两害相权{RQ}，ai投资逻辑彻底变了！')
    assert is_noise('从「稳赚不赔」到「两害相权」，AI投资逻辑彻底变了！')


def test_见闻观点句式不误伤正常新闻():
    # 正常报道不会写"投资逻辑彻底变"感叹句式
    assert not is_noise(f'日元汇率跌至四十年来最低 日本工薪家庭{LQ}睡不着{RQ}企业却{LQ}笑醒了{RQ}')
    assert not is_noise('华尔街见闻：科技股投资逻辑生变，机构转向盈利兑现')


def test_bbc个人叙事被过滤():
    assert is_noise("woman 'scared to turn heating on' due to oil cost")


def test_bbc个人叙事不误伤():
    assert not is_noise('oil prices surge as houthi attacks escalate, heating oil futures jump')


def test_bbc中文解释性特稿被过滤():
    assert is_noise('特朗普治下，美国经济的真实表现如何？')


def test_真实表现不误伤():
    # 正常数据新闻措辞不同
    assert not is_noise('美国9月就业数据公布，经济表现喜忧参半')


def test_预热导购稿被过滤():
    assert is_noise('小米 redmi book 2027 预热：外观焕新，16 英寸机型标配数字小键盘')
    assert is_noise('某品牌手机预热：搭载新一代旗舰芯片')


def test_预热不误伤真事件():
    # '预热'后无产品配置尾词的真新闻措辞
    assert not is_noise('访美预热：两国元首或将通话')
    assert not is_noise('G20峰会预热：多国领导人陆续抵达')


def test_bbc租房街访被过滤():
    assert is_noise("renting in london - 'i pay £2,000 for one bedroom'")


def test_租房不误伤():
    assert not is_noise('london rent prices hit record high as housing crisis deepens')


def test_dw_iso_byline_long_author_stripped():
    # 14 字符拉丁作者名超旧 12 上限 (Madelaine Pitt 实测残留吃满摘要窗)
    from daily_briefing import clean_summary
    s = clean_summary('<div><i>Madelaine Pitt<br />2026-10-23T11:35:18.185Z</i></div><div><small>法国警察的武器库比大多数欧盟国家都要大，这引发了广泛批评。</small></div>')
    assert s.startswith('法国警察'), s


def test_engadget_explainer_filtered():
    from daily_briefing import ENGADGET_GUIDE_RE
    assert ENGADGET_GUIDE_RE.search('What kind of cooling system do EV batteries use and how does it work?')
    # 真新闻带问号不受影响 (非 Engadget feed 亦不生效)
    assert not ENGADGET_GUIDE_RE.search('Anthropic Q3 revenue: can it justify a trillion-dollar valuation?')
