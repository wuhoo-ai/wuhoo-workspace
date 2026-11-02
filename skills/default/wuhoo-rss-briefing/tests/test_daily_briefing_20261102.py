# -*- coding: utf-8 -*-
"""2026-11-02 维护回归：
① apple_intelligence_china — 苹果 Apple 智能入华(与阿里合作集成千问，11月4日开放测试)
   见闻/联合早报/IT之家×2/一财/少数派 各写不同标题拆占 科技/AI TOP4-5、[N源]失效；
   防误并: 阿里千问自家模型稿无 Apple 锚不并；Apple 智能欧美功能/监管稿无中国锚不并。
② 京东双十一秒杀/红包导购稿 — "蹲点速抢 1.18 元京东无门槛红包…1 元秒杀" 占产业 TOP1
   (旧 11.11 模式要求促销词与 "11.11" 同窗共现，本例 11.11 在 50 字摘要窗外)。
③ Keychron 国行发售+标价促销稿句式。④ 虎嗅匿名访谈观点栏目(逼谁追共识)。
⑤ 重磅日程栏目措辞扩 本周|下周(11-02 "本周重磅日程" 占财经 TOP5)。"""
from daily_briefing import entity_key, is_noise


# ── ① apple_intelligence_china 命中(取 11-02 窗口内真实标题形态) ──

def test_apple智能入华_中文各源命中():
    assert entity_key('苹果官宣：Apple智能接入阿里千问，11月4日开放测试', '') == 'apple_intelligence_china'
    assert entity_key('阿里巴巴与苹果达成合作 将千问集成至苹果智能', '') == 'apple_intelligence_china'
    assert entity_key('阿里巴巴：苹果 Apple 智能国行用户可以自主选择是否开通千问集成功能', '') == 'apple_intelligence_china'
    assert entity_key('苹果 Apple 智能入华亮点：AirPods 实时翻译登场，戴上耳机跨语言聊天', '') == 'apple_intelligence_china'
    assert entity_key('一图流 | 一张图看懂中国版 Apple 智能', '') == 'apple_intelligence_china'


def test_apple智能入华_一财速递栏目靠摘要命中():
    # 一财 "AI进化速递丨" 聚合栏目稿，标题无中国锚靠截断摘要命中(多波次词形覆盖先例)
    assert entity_key('AI进化速递丨苹果官宣Apple智能接入阿里千问',
                      '①苹果官宣：阿里千问集成至Apple智能') == 'apple_intelligence_china'


def test_apple智能入华_英文alibaba锚命中():
    assert entity_key('Apple Intelligence to launch in China powered by Alibaba Qwen', '') == 'apple_intelligence_china'


def test_apple智能_千问自家稿无apple锚不并():
    assert entity_key('阿里千问发布新一代旗舰模型 Qwen3-Max，性能登顶开源榜', '') != 'apple_intelligence_china'


def test_apple智能_欧美功能稿无中国锚不并():
    # 第二锚点收紧教训：裸 登陆/接入 会把欧美功能稿吸进本事件
    assert entity_key('Apple Intelligence 将在欧盟受限，接入端侧模型', '') != 'apple_intelligence_china'
    assert entity_key('Apple Intelligence 登陆澳大利亚', '') != 'apple_intelligence_china'


def test_apple智能_不抢库克访华规则():
    # 何立峰会见库克稿无 Apple 智能产品锚，仍归 cook_china_visit
    assert entity_key('何立峰會見蘋果庫克 探討經貿合作', '') == 'cook_china_visit'


# ── ②③④⑤ NOISE ──

def test_京东秒杀红包导购():
    assert is_noise('【20:00~20:15】蹲点速抢 1.18 元京东无门槛红包，小米 55 寸电视 1 元秒杀 '
                    '全网 11.11 在 10 月 31 日 20:00 ~ 11 月 1 日开启超级秒杀狂促，整个 1')


def test_keychron_国行发售标价稿():
    assert is_noise('Keychron 三模键盘 K8 Ultra 8K 国行发售：原生 macOS 键位，721 元 '
                    'Keychron（渴创）现已开始在中国大陆电商平台销售 K8 Ultr')


def test_重磅日程_本周下周双措辞():
    assert is_noise('本周重磅日程：聚焦美国中选与中国重磅金融会议，非农、AMD和苹果财报齐至')
    assert is_noise('下周重磅日程：全球聚焦中美')


def test_虎嗅匿名访谈观点栏目():
    assert is_noise('一线投资人与创业者匿名访谈：到底是谁在逼谁追共识 '
                    '“VC 现在只投共识。”过去一段时间，我们和不少创业者聊过，这是很多人都会')


def test_防误伤_入华事件稿与非日程新闻():
    assert not is_noise('苹果 Apple 智能入华亮点：AirPods 实时翻译登场')
    assert not is_noise('市场聚焦下周非农数据与 AMD 财报 交易员保持观望')


# ── ⑥ Engadget 数字清单体 tips 栏目 (feed 级) ──

def test_engadget_数字清单tips():
    from daily_briefing import ENGADGET_GUIDE_RE
    assert ENGADGET_GUIDE_RE.search('5 Netflix tips we all wish we knew sooner')


def test_engadget_防误伤真新闻():
    from daily_briefing import ENGADGET_GUIDE_RE
    assert not ENGADGET_GUIDE_RE.search('Netflix reports record Q3 revenue as streaming growth continues')
    assert not ENGADGET_GUIDE_RE.search('10 people diagnosed after rare parasite outbreak in Vermont')


# ── ⑦ 虎嗅情绪化观点文 ──

def test_虎嗅停止赞美观点文():
    assert is_noise('请停止赞美技术的"无人化" 这几天看老干妈的风波，我想起一年前《纽约时报》关于亚马逊的一篇')
