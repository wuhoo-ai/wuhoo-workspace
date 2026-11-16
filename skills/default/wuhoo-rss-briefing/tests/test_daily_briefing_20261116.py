# -*- coding: utf-8 -*-
"""2026-11-16 维护回归：
① NOISE 新增 卫报系播客节目推广稿 `[-–—]\\s*podcast\\b`
   ("Teen prodigy, Netflix star, prisoner: the story of Hong Kong dissident Joshua Wong – podcast"
   hot6 占产业/公司 TOP5——播客剧集 publicity 非新闻事件，同类 thursday briefing/business daily/
   watch the trailer；标题破折号+podcast 收尾为卫报/泰晤士节目固定格式，正文中段 "on the podcast"
   无破折号不误伤)。
② NOISE 新增 产品评测/分析师评论体 `\\breview:\\s|in-?depth review`
   (Engadget "Surface Laptop Ultra review: The most powerful Surface yet, but it still lags
   behind Apple" hot12 占科技/AI TOP4——单机评测评论性内容非事件本身；Seeking Alpha
   "Digi International Q4 Review: A Little Bump In The Road" 同族；尾随冒号限定，
   "under review"/"Court of review" 类正常措辞不误伤)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from daily_briefing import is_noise, SA_LOW_RE


# ── ③ SA ARK 系 ETF 日更评论栏目 ──

def test_sa_ark栏目命中():
    assert SA_LOW_RE.search("ARKF: Tech Trouble Via Microsoft & The FAA - Bitcoin's Plunge Adds Pressure")
    assert SA_LOW_RE.search("ARKK: Something Wicked This Way Comes")
    # 正常公司名稿件不误伤（ARK 前缀非栏目格式）
    assert not SA_LOW_RE.search("Nvidia beats Q3 revenue estimates as AI demand accelerates")


# ── ④ 京东京造配件发售稿 ──

def test_京造发售命中():
    assert is_noise("京东京造推出 130W 自带线车载充电器：2C + 1A 设计，99 元")
    assert is_noise("京东京造推出“铝膜复合水刺棉材质”全罩汽车车衣：可疏水防暴晒，189 元起")
    # 京东集团真新闻（并购/财报）不含 京造 不误伤
    assert not is_noise("京东完成对德国消费电子零售商 Ceconomy 收购要约，13.35 亿欧元获 59.8% 股本及投票权")
    assert not is_noise("京东集团第三季度营收超预期，京东物流分拆上市获批准")


# ── ① podcast 播客推广稿命中 ──

def test_podcast破折号后缀命中():
    assert is_noise("Teen prodigy, Netflix star, prisoner: the story of Hong Kong dissident "
                    "Joshua Wong – podcast")
    assert is_noise("Analysis: the week in tech — podcast")
    assert is_noise("The Intelligence — podcast: what next for the Ukraine talks")


# ── ② review: 评测体命中 ──

def test_review冒号体命中():
    assert is_noise("Surface Laptop Ultra review: The most powerful Surface yet, "
                    "but it still lags behind Apple")
    assert is_noise("Digi International Q4 Review: A Little Bump In The Road, "
                    "But The Pivot Is Still Promising")
    assert is_noise("Philips Hue Sync 2 in-depth review: ambilight for anyone")


# ── 防误伤回归 ──

def test_podcast正文中段不误伤():
    # 正常新闻提及 podcast（无破折号格式）不被过滤
    assert not is_noise("OpenAI CEO says regulations should not be written by podcast hosts")
    assert not is_noise("Anthropic 研究员在播客访谈中谈模型安全进展")


def test_review正常措辞不误伤():
    assert not is_noise("White House ethics office under review after Nvidia scandal")
    assert not is_noise("Court of review overturns AI copyright ruling")
    assert not is_noise("欧盟对 Meta 的反垄断审查进入第二轮 _review 程序")
    # 财报/事件稿含 review 无冒号格式
    assert not is_noise("Microsoft quarterly review day: Azure growth beats estimates without colon formatting")


# ── ⑤ ULA 火神火箭发射失败五源合并 (11-15 事件) ──
from daily_briefing import entity_key as _ek


def test_vulcan五源命中():
    assert _ek("ULA 成立 20 年来首次发射任务完全失败：火神火箭升空 10 分钟后出现异常，"
               "亚马逊 40 颗卫星损失", "") == 'ula_vulcan_failure'
    assert _ek("Vulcan rocket fails, destroying 40 Amazon Leo satellites", "") == 'ula_vulcan_failure'
    assert _ek("美“火神”火箭未能将亚马逊卫星送入预定轨道", "") == 'ula_vulcan_failure'
    assert _ek("Vulcan rocket fails during launch, dealing major blow to SpaceX competitors",
               "") == 'ula_vulcan_failure'


def test_vulcan防误并():
    # Pegula 含子串 ula——词界拦截；无火箭失败语系
    assert _ek("Andreeva eliminates Pegula to set WTA Finals title match with Svitolina", "") is None
    # 推迟发射无 fail/destroy 语系不并
    assert _ek("ULA delays Vulcan launch to next month after engine inspection", "") is None


# ── ⑥ microsoft_outage 中文语系变体 ──

def test_微软中文瘫痪变体命中():
    assert _ek("微软系统全球瘫痪：Outlook、Teams、Copilot受影响",
               "微软系统大规模中断，包括Teams、Outlook") == 'microsoft_outage'
    assert _ek("微軟系統全球癱瘓：Outlook及Teams受影響", "大面積連線問題") == 'microsoft_outage'
    # 裸"中断"决策稿不误并（微软中断对俄服务）
    assert _ek("微软中断对俄服务 董事会决议明年停止莫斯科业务", "") != 'microsoft_outage'


# ── ⑦ Verge 美元降价促销导购 ──

def test_美元off促销命中():
    assert is_noise("Fanttik's S1 Pro electric screwdriver is $40 off in the run-up to Black Friday")
    # 正常新闻 "$40 million aid" 无 off 不命中
    assert not is_noise("Senate passes $40 billion aid package for semiconductor makers")
