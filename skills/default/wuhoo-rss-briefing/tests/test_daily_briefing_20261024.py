# 2026-10-24 回归: 第一财经上游 RSS 混入 PROBE 探针条目 (hot27 抢占财经 TOP1)
# DB 脏行已删除 (5 条), NOISE_PATTERNS 补 probe_i\d+ 防复发
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from daily_briefing import is_noise


def test_probe条目被过滤():
    # 实测污染条目原文 (清洗后小写形态)
    assert is_noise("probe_i116928_removed | probe removed")
    assert is_noise("ycprobe_i117594_removed | cleanup")


def test_probe单词新闻不误伤():
    # 正常新闻大量使用 probe (调查) 一词——词形后不接 _i+数字
    assert not is_noise("US justice department probes Trump's press pool boycott")
    assert not is_noise("Florida attorney general launches criminal probe into ChatGPT")
    assert not is_noise("NASA's Mars MAVEN probe is dead")
    assert not is_noise("德国警方调查莱比锡机场安全事件 probe 持续推进")
