# -*- coding: utf-8 -*-
"""2026-11-17 维护回归（小时级采集新基线首日）：
① ENTITY 新增 `triple_summit_shenzhen` — 中俄美深圳三方会晤官宣(见闻/观察者网/参考消息 hot35×3)
   与外交部表态后续波次(凤凰网/财联社×2/见闻实时/格隆汇 hot35×5)同一事件拆占 宏观TOP1+财经TOP4 两榜
   (10-10 多波次词形 + 09-30 跨分类拆榜教训)。
② NOISE 新增 美联储新闻例行审批/执法文书 — Mutual Federal Bancorp 申请获批 hot35 把 11-09 旧批文
   带进财经 TOP3（小时级回填使 fetched_at 窗口含旧 pub_date 条目）；FOMC statement 等真政策稿不误伤。
③ clean_summary 剥离 "本文来自微信公众号：X" byline — 虎嗅两篇代表(硅谷巨头打什么算盘/黄仁勋要回归)
   摘要实测只剩 byline 前缀。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from daily_briefing import entity_key, is_noise, clean_summary


# ── ① 三方会晤跨波次合并 ──

def test_三方会晤官宣与外交部表态合并():
    k1 = entity_key("习近平将同俄罗斯总统普京、美国总统特朗普举行中俄美元首会晤",
                    "外交部发言人宣布：11月19日，国家主席习近平将同俄罗斯总统普京、美国总")
    k2 = entity_key("外交部谈中俄美元首会晤：具有开创性意义",
                    "11月16日，外交部发言人毛宁主持例行记者会。总台央视记者提问：中方发布了中俄美")
    assert k1 == 'triple_summit_shenzhen'
    assert k2 == 'triple_summit_shenzhen'
    # 英文/分析波次
    k3 = entity_key("分析：特朗普与普京力推三方会晤 习近平心存顾虑", "")
    assert k3 == 'triple_summit_shenzhen'


def test_三方会晤防误并():
    # APEC 抵深稿无会晤锚（同深圳不同事件）
    assert entity_key("墨西哥总统辛鲍姆抵达深圳，将出席APEC领导人非正式会议",
                      "墨西哥总统辛鲍姆16日抵达深圳，将出席亚太经合组织领导人非正式会议") != 'triple_summit_shenzhen'
    assert entity_key("李家超将前往深圳 出席亚太经合组织领导人非正式会议及相关活动", "") != 'triple_summit_shenzhen'
    assert entity_key("首次主办APEC “深圳奇迹”还能延续吗？", "") != 'triple_summit_shenzhen'
    # 双边中俄会晤（无 美 锚，不同事件）
    assert entity_key("习近平同俄罗斯总统普京会晤 深化中俄全面战略协作", "") != 'triple_summit_shenzhen'
    # 中美双边通话（无 普京/三方/中俄美 锚）
    assert entity_key("习近平同美国总统特朗普通话 讨论经贸议题", "") != 'triple_summit_shenzhen'


# ── ② 美联储例行文书过滤 ──

def test_美联储审批执法文书命中():
    assert is_noise("Federal Reserve Board announces approval of two applications by "
                    "Mutual Federal Bancorp, MHC, and MFB Bancorp, Inc.")
    assert is_noise("Federal Reserve Board announces approval of application by The Bank of Nova Scotia")
    assert is_noise("Federal Reserve Board announces termination of enforcement actions with "
                    "Gardner Bancshares")
    assert is_noise("Federal Reserve Board issues enforcement action with former employee of "
                    "United Community Banks")


def test_美联储真政策稿不误伤():
    assert not is_noise("Federal Reserve issues FOMC statement")
    assert not is_noise("Minutes of the Board's discount rate meetings on August 17, September 9")
    assert not is_noise("Federal Reserve Board releases results of the 2025 Survey of Consumer "
                        "Finances, which provides a comprehensive picture of U.S. families")
    # 他源含 reserve 措辞的正常报道
    assert not is_noise("Fed holds rates steady as inflation cools, citing bank reserve data")


# ── ③ 公众号 byline 剥离 ──

def test_微信byline纯账号名置空():
    assert clean_summary("本文来自微信公众号：腾讯科技") == ''
    assert clean_summary("本文来自微信公众号：微信派") == ''


def test_微信byline后正文保留():
    s = clean_summary("本文来自微信公众号：远川研究所，作者：杨文，11月16日阿里巴巴与腾讯"
                      "在同一天发布了各自的新一代语言模型。")
    assert s.startswith("作者：杨文") or s.startswith("11月16日")
    assert '本文来自微信公众号' not in s


def test_正常摘要不误删():
    s = clean_summary("记者今日从微信官方获悉，公众号将上线新的创作分成机制。")
    assert s.startswith("记者今日")
