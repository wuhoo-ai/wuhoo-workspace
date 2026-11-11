# -*- coding: utf-8 -*-
"""2026-11-11 维护回归：
① anthropic_q3_revenue 移除裸 valuation|估值 锚 + anthropic_ipo_pitch 扩 I.P.O. 点号变体/估值语境/
   三锚 lookahead 分支 — 当日 FT20 "targets valuation of up to $1.4tn in IPO" 被裸估值抢判进
   q3_revenue 组、撤稿稿(见闻热门12)走 ipo_pitch，同一 IPO 事件拆 [7源]+[1源] 两组占财经 TOP1+TOP4
   (09-30/10-04 拆榜教训家族)。10-16 q3 营收稿回归不受影响。
② ENTITY_KEYS 新增 australia_ai_law — BBC17 criminal penalties for rogue AI 稿此前被 openai_
   australia_hack 规则吞组(显示 [2源])、DW17 mandatory AI safeguards + 卫报6 mandatory reporting
   散占宏观 TOP2，两榜拆占；须置于 hack 规则之前(立法稿均带 "in wake of OpenAI hack" 状语)。
   防误伤: 09-25 入侵本体稿/Qantas 岗位稿。
③ ENTITY_KEYS 新增 uber_parking — TechCrunch6 SpotHero 后续稿 + Engadget6 同事件拆占产业 TOP3+4。
④ ENTITY_KEYS 新增 anthropic_workspace — Claude Sheets/Meetings/IT之家办公套件同场发布拆榜；
   Fable/Mythos 5.2 模型稿由前位 claude_fable_51 收编不误并。
⑤ ENGADGET_GUIDE_RE 扩 ^why…charging 科普解释体 (Why EV fast charging slows down after 80 percent
   占产业 TOP5)；Why Apple's M6 Chip 稿无 charging 不误伤。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from daily_briefing import entity_key, is_noise, ENGADGET_GUIDE_RE


def ek(title, summary=''):
    return entity_key(title, summary[:50])


# ── ① Anthropic IPO 簇合并 ──

def test_ipo主稿簇全命中():
    assert ek("Anthropic targets valuation of up to $1.4tn in IPO") == 'anthropic_ipo_pitch'
    assert ek("Anthropic Targets Valuation of Up to $1.4 Trillion for Blockbuster I.P.O.") == 'anthropic_ipo_pitch'
    assert ek("Anthropic將在美IPO　估值上看1.4兆美元") == 'anthropic_ipo_pitch'
    assert ek("冲击美国科技IPO融资纪录！Anthropic最高募资904亿美元、完全稀释估值1.4万亿美元") == 'anthropic_ipo_pitch'
    assert ek('冲击"史上最大 IPO"：消息称 Anthropic 下周四 / 五上市，估值预期遭遇市场降温') == 'anthropic_ipo_pitch'
    assert ek("Anthropic 发布 IPO 路演视频正式启动最高 643.5 亿美元募资计划，估值约在 1~1.4 万亿美元") == 'anthropic_ipo_pitch'
    assert ek("Anthropic 七名联合创始人拟在 IPO 中各套现 2.5 亿美元") == 'anthropic_ipo_pitch'
    assert ek("Anthropic's Giant IPO Will Tie It Closer to Nvidia",
              "The Claude maker plans to raise as much as $64bn in the offering") == 'anthropic_ipo_pitch'

def test_撤稿稿命中():
    assert ek("Anthropic招股文件刚发就撤！693亿美元融资细节意外泄露，英伟达、微软、台积电等集体押注260亿") == 'anthropic_ipo_pitch'

def test_q3营收稿回归():
    # 10-16 事件本簇仍归 q3_revenue
    assert ek("Anthropic Q3 营收 168 亿美元，向投资者披露财务数据") == 'anthropic_q3_revenue'
    assert ek("Anthropic tells investors quarterly revenue up 50% to $16.8bn ahead of IPO") == 'anthropic_q3_revenue'
    assert ek("Anthropic估值承压：收入增速放缓，部分投资者转向1.5万亿美元") == 'anthropic_q3_revenue'

def test_ipo防误并():
    # 虎嗅策略稿/Ars FTC 调查稿 无 IPO/招股锚
    assert ek("为什么Anthropic不做Personal AI", "虎嗅：分析其企业级产品策略选择") not in ('anthropic_ipo_pitch', 'anthropic_q3_revenue')
    assert ek("FTC probes Anthropic over AI claims", "regulators examine marketing") != 'anthropic_ipo_pitch'


# ── ② 澳大利亚 AI 立法 ──

def test_澳洲立法三源合并():
    assert ek("Australia considers criminal penalties for rogue AI in wake of OpenAI hack",
              "AI safety regulator will also be created after a review") == 'australia_ai_law'
    assert ek("Australia to introduce mandatory AI safeguards",
              "The Australian government's decision to establish a new office") == 'australia_ai_law'
    assert ek("Australia to introduce mandatory reporting after OpenAI hack to combat fraud") == 'australia_ai_law'

def test_入侵本体稿回归():
    # 09-25 入侵事件稿无立法语境词，仍归 hack 组
    assert ek("Anthony Albanese says OpenAI agent hacked Medicare") == 'openai_australia_hack'
    assert ek("OpenAI agent infiltrated Australian government websites, PM confirms") == 'openai_australia_hack'

def test_qantas岗位稿不误并():
    assert ek("Qantas to outsource 850 local jobs with most roles moving to India",
              "The Australian airline says") is None


# ── ③ Uber 停车服务 ──

def test_uber停车两源合并():
    assert ek("Uber launches parking service following SpotHero acquisition, with an eye on robotaxis") == 'uber_parking'
    assert ek("Uber is launching its own parking reservation service",
              "Uber Parking is the latest example of the company") == 'uber_parking'

def test_uber防误并():
    assert ek("Uber Eats expands grocery delivery to 200 new cities", "partnership with local retailers") is None


# ── ④ Claude 办公套件 ──

def test_办公套件簇合并():
    assert ek("Anthropic takes on Google and Microsoft with Claude Sheets",
              "The company also has a new whiteboard app.") == 'anthropic_workspace'
    assert ek("Anthropic launches Claude Meetings to turn workplace discussions into plans") == 'anthropic_workspace'
    assert ek("Anthropic 升级 AI 办公套件：从头脑风暴到数据看板，Claude 想承包团队协作全流程") == 'anthropic_workspace'

def test_fable模型稿回归():
    # 模型发布稿由前位 claude_fable_51 收编，不进办公套件组
    assert ek("Anthropic launches new Claude Fable and Mythos 5.2 models") == 'claude_fable_51'
    assert ek("为IPO预热！Anthropic发布最强旗舰模型，Fable 5.2多测试力压GPT-6 Astra，和Mythos 5.2均提速并降价") == 'claude_fable_51'


# ── ⑤ Engadget 科普句式 ──

def test_ev充电科普稿命中():
    assert ENGADGET_GUIDE_RE.search("Why EV fast charging slows down after 80 percent")

def test_m6分析稿不误伤():
    assert not ENGADGET_GUIDE_RE.search("Why Apple's M6 Chip Can't Hold Its Own Against Any NVIDIA GPU")
