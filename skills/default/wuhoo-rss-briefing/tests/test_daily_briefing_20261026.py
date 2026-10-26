# 2026-10-26 回归: SA_LOW_RE 季报措辞扩展
# 'Third Avenue Real Estate Value Fund Q3 2026 Portfolio Activity' 占财经 TOP1
# 旧规则 q[12] 只覆盖 Q1/Q2, Q3 季报漏网; portfolio update 不覆盖 'Portfolio Activity'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from daily_briefing import SA_LOW_RE


def test_q3季报被过滤():
    assert SA_LOW_RE.search('Third Avenue Real Estate Value Fund Q3 2026 Portfolio Activity')


def test_portfolio_activity措辞变体无年份也被过滤():
    assert SA_LOW_RE.search('Some Fund Portfolio Activity Summary')


def test_q4季报变体被过滤():
    assert SA_LOW_RE.search('Alpha Fund Q4 2026 Commentary')


def test_电商平台销售句式被过滤():
    from daily_briefing import is_noise
    assert is_noise('联想极光键盘 gk1077 lite 三模版上市 联想 (lenovo) 现已在电商平台销售极光键盘')


def test_正常报道不误伤电商平台措辞():
    from daily_briefing import is_noise
    # 政策/产业新闻谈"电商平台销售"不会用"现已在+距离6字内+销售"发售流水句式
    assert not is_noise('市场监管总局新规 电商平台销售食品需公示资质')


def test_running_list栏目观点特稿被过滤():
    from daily_briefing import is_noise
    assert is_noise("the ai graveyard: a running list of projects and startups that didn't make it")
    assert is_noise("I hope Apple's touchscreen MacBook takes some lessons from this Lenovo laptop")
    assert is_noise('谷歌 deepmind 高管：终身学习者将在 ai 职场中占据优势')


def test_自营店到货措辞被过滤():
    from daily_briefing import is_noise
    assert is_noise('戴尔推出ultrasharp焕新版4k显示器 戴尔京东自营店新上了两款 ultrasharp 显示器')


def test_旗舰店开业真新闻不误伤():
    from daily_briefing import is_noise
    # "开业/上线"不在到货动词表，品牌渠道扩张真新闻不受影响
    assert not is_noise('苹果印度官方旗舰店正式开业，库克出席剪彩仪式')


def test_正常财报新闻不被误伤():
    # Q3 后无 20xx 年份不命中
    assert not SA_LOW_RE.search('NVIDIA beats Q3 revenue estimates as data center demand surges')
    assert not SA_LOW_RE.search('Anthropic Q3 revenue up 50% ahead of IPO')
    assert not SA_LOW_RE.search('Tesla reports record Q3 deliveries')
