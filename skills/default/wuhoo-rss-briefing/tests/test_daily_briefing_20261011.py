# -*- coding: utf-8 -*-
"""2026-10-11 噪声回归：BBC中文成人产业特稿 / IT之家中兴监控上架导购"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import NOISE_PATTERNS


def _hit(text):
    tl = text.lower()
    return any(re.search(p, tl) for p in NOISE_PATTERNS)


def test_av_industry_feature_noise():
    assert _hit("台湾AV产业：中国资金涌入后发生了什么？")
    assert _hit("谁养大了台湾AV产业？台湾AV盛极而衰：中国市场如何催生这场成人片热潮？")


def test_zte_camera_listing_noise():
    assert _hit("中兴小兴看看 SC50D 监控上架：集成双 500 万像素摄像头云台，309 元")
    assert _hit("中兴 摄像头 上架 京东")


def test_pinnacle_case_noise():
    assert _hit("超频三 C3 T300 BK 海景房机箱发售：兼容 240mm 水冷，129 元")


def test_no_false_positive():
    # 公司新闻不误伤
    assert not _hit("中兴通讯发布第三季度财报，营收同比增长")
    # 含 AV 子串的常见词不误伤（如 have/behavior）
    assert not _hit("OpenAI releases new behavior benchmarks")
    assert not _hit("Germany sticks to Russia sanctions after Trump diesel deal")
