# -*- coding: utf-8 -*-
"""2026-10-14 摘要清洗回归：
1) HN 互链帖模板 "Main thread:"/"See also:" 剥离（仅 HN 源，防他源误删）—
   Gemini 4 Argon for Robotics (hot17) 占科技/AI TOP1 摘要只剩链接骨架
2) 华尔街见闻 blockquote "摘要 1 XXX" 框前缀剥离 —
   "如何看待当前中美科技股的背离" 占财经 TOP5 摘要混入栏目框字样
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import clean_summary, entity_key


HN_MAIN_THREAD_RAW = (
    '<p>Main thread: <i>Gemini 4 Argon</i> - '
    '<a href="https://news.ycombinator.com/item?id=50073879">'
    'https://news.ycombinator.com/item?id=50073879</a></p>\n'
    '<hr />\n<p>Comments URL: <a href="https://news.ycombinator.com/item?id=50073879">'
    'https://news.ycombinator.com/item?id=50073879</a></p>'
)

HN_SEE_ALSO_RAW = (
    '<p>See also: <i>Gemini 4 Argon for Robotics</i> - '
    '<a href="https://news.ycombinator.com/item?id=50074869">'
    'https://news.ycombinator.com/item?id=50074869</a></p>\n'
    '<hr />\n<p>Comments URL: <a href="https://news.ycombinator.com/item?id=50074869">'
    'https://news.ycombinator.com/item?id=50074869</a></p>'
)


def test_hn_main_thread_stripped():
    assert clean_summary(HN_MAIN_THREAD_RAW, 'Hacker News 100+') == ''


def test_hn_see_also_stripped():
    assert clean_summary(HN_SEE_ALSO_RAW, 'Hacker News 100+') == ''


def test_hn_real_summary_kept():
    # HN 有真实正文时保留（剥离发生在 Comments URL 之前，正文不受影响）
    s = clean_summary(
        '<p>Our newest model is built for robotics tasks.</p>\n<hr />\n'
        '<p>Article URL: <a href="https://example.com">https://example.com</a></p>',
        'Hacker News 100+')
    assert s == 'Our newest model is built for robotics tasks.'


def test_non_hn_main_thread_not_touched():
    # 非 HN 源正文含 "Main thread:" 措辞不误删 (clean_summary 尾部截 50 字，断前缀)
    s = clean_summary(
        'Researchers explained the Main thread: execution model in detail.',
        'Ars Technica')
    assert s.startswith('Researchers explained the Main thread')


def test_wsc_summary_frame_prefix():
    # 见闻 blockquote 摘要框: "摘要 1 正文" → 只留正文
    raw = ('<blockquote>\n<p style="text-align: justify;"><strong>摘要</strong></p>\n'
           '<p style="text-align: justify;"><strong>1&nbsp;</strong>中美科技股背离背后：'
           '基本面预期压制下的估值收敛</p></blockquote>')
    s = clean_summary(raw, '华尔街见闻')
    assert s.startswith('中美科技股背离背后：')
    assert '摘要' not in s


def test_normal_text_no_false_positive():
    # 普通正文不受影响
    s = clean_summary('要摘要地说，市场风格正在切换。', '虎嗅')
    assert s == '要摘要地说，市场风格正在切换。'


# ---- 2026-10-14 实体合并：库克卸任后访华/何立峰会见 (中央社/联合早报×2/凤凰网 拆榜教训) ----

def test_cook_china_visit_merges():
    assert entity_key('何立峰會見蘋果庫克  稱歡迎各國科企深化對中合作', '') == 'cook_china_visit'
    assert entity_key('何立峰见库克：落实好两国元首共识为跨国企业提供稳定预期', '') == 'cook_china_visit'
    assert entity_key('库克卸任苹果CEO后首次访华 现身广州探班咏春短片拍摄', '') == 'cook_china_visit'
    assert entity_key('卸任苹果CEO后首次访华，库克和苏炳添在广州喝早茶', '') == 'cook_china_visit'


def test_fed_governor_cook_not_merged():
    # 美联储理事 Cook (Lisa Cook) 与苹果库克同名不同人，英文分支无 tim cook/apple 锚不并
    assert entity_key(
        "Lawyer for Fed Governor Cook Denounces Trump's New Investigation",
        '') != 'cook_china_visit'


def test_cook_farewell_still_transition():
    # 换任告别信类稿件不被访华规则抢走
    assert entity_key('苹果CEO库克发布告别信 致全体员工', '') == 'apple_ceo_transition'
