# -*- coding: utf-8 -*-
"""2026-11-04 维护回归：
① NOISE 虎嗅观点罗列体栏目 "AI新物种组织治理十大冲突" hot9 占科技/AI TOP5（产业格局复盘非单一事件，
   同类 投资逻辑彻底变/何处是底）。
② NOISE DW 选举解释性栏目 "US midterm election: Why it's important and races to watch" hot11 占宏观 TOP5
   （blockquote 导语栏目体，同类 美国经济的真实表现/europe live）。
   防误伤回归: 选战/开票真新闻报道标题（Battle for US midterm elections heats up / 芯片股反弹中选日稿）不命中。"""
from daily_briefing import is_noise


# ── ① 虎嗅观点罗列体 ──

def test_虎嗅十大冲突命中噪声():
    assert is_noise('ai新物种组织治理十大冲突')


def test_虎嗅十大冲突防误伤():
    # 真事件稿不含罗列句式
    assert not is_noise('openai、谷歌、微软和 anthropic 联手推行 ai 数据抓取退出标准')


# ── ② DW 选举解释性栏目 ──

def test_dw选举解释栏目命中噪声():
    assert is_noise("us midterm election: why it's important and races to watch")
    # 排版撇号变体（’ 弯引号）
    assert is_noise("us midterm election: why it\u2019s important and races to watch")


def test_dw选举解释栏目防误伤():
    # 同期选战/开票真新闻（库内实测标题）不命中
    assert not is_noise('battle for us midterm elections heats up')
    assert not is_noise('trump makes final pitch to restive voters in midterms campaign')
    assert not is_noise('democrats are used to heartbreak in texas - could talarico turn the tide?')
    assert not is_noise('bond investors sit out \u2018most consequential\u2019 us midterm elections in years')
    assert not is_noise('美国中期选举日，芯片股三日大跌后反弹，纳指涨0.83%，盘后amd大涨近8%')
