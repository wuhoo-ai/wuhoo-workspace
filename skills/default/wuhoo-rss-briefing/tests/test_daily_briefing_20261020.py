# -*- coding: utf-8 -*-
"""2026-10-20 回归：
1) NOISE 发售句式通捕扩展 — "，首发价 N 元" 尾注句式（VGN×天美限定款机械键盘占产业 TOP5）
2) NOISE BBC Business 约会生活方式特稿（'fed up of swiping' 占财经 TOP2）
3) 防误伤 — 正常事件稿含"首发/价"不误命中；真新闻含 singles 语境不误命中
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import is_noise, entity_key


# ── 三星×台积电×HBM 五源合并 ──────────────────────

def test_samsung_hbm_tsmc_traditional():
    assert entity_key("韓媒：三星應輝達要求　下一代HBM基礎晶粒採台積電3奈米", "") == "samsung_hbm_tsmc"

def test_samsung_hbm_tsmc_simplified():
    assert entity_key("三星将采用台积电 3nm 工艺为英伟达生产下一代 HBM 基底裸片", "") == "samsung_hbm_tsmc"

def test_samsung_hbm_tsmc_gelonghui():
    assert entity_key("三星据悉将采用台积电3纳米工艺为英伟达生产下一代HBM基底裸片", "") == "samsung_hbm_tsmc"

def test_samsung_hbm_tsmc_english_tsmc():
    assert entity_key("Samsung to use TSMC process for Nvidia next-gen HBM base die", "") == "samsung_hbm_tsmc"

def test_samsung_phone_no_hbm_anchor():
    assert entity_key("三星Galaxy S26 Ultra 发布，搭载自研芯片", "") != "samsung_hbm_tsmc"

def test_hynix_hbm_no_samsung_anchor():
    assert entity_key("SK海力士HBM4明年量产，供货英伟达与台积电合作先进封装", "") != "samsung_hbm_tsmc"

def test_samsung_hbm_no_tsmc_anchor():
    assert entity_key("三星向英伟达供应下一代HBM4E内存，自家晶圆厂生产", "") != "samsung_hbm_tsmc"


# ── 首发价句式通捕 ──────────────────────

def test_vgn_keyboard_launch_noise():
    assert is_noise("VGN 联合腾讯天美工作室推出 V98Pro V4 TiMi 限定款机械键盘：带有小云仔发声键帽按钮，首发价 419 元")

def test_first_sale_price_variant_spacing():
    # 数字与"元"之间空格/小数容错
    assert is_noise("某某新品现已开售 首发价1299.9 元 起")

def test_real_event_not_caught():
    # 真事件稿不写"首发价 N 元"尾注句式
    assert not is_noise("英伟达发布下一代 GPU 架构，定价面向数据中心市场")
    assert not is_noise("台积电 3nm 制程获日本经产省批准量产")

def test_summary_truncated_no_false_positive():
    # "首发"单独出现不触发（须与"价 N 元"组合）
    assert not is_noise("小米 18 系列全球首发，雷军出席发布会")


# ── BBC 约会生活方式特稿 ──────────────────────

def test_bbc_dating_soft_news_noise():
    assert is_noise("'I'm fed up of swiping': Why singles now want to meet IRL")

def test_dating_lower_case_matched():
    # is_noise 内部 lower()，模式全小写
    assert is_noise("Why SINGLES NOW WANT TO MEET in real life, says BBC")

def test_normal_market_news_not_caught():
    assert not is_noise("IMF 警告日本可能需要更快加息，全球债市再添压力")
