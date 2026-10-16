# -*- coding: utf-8 -*-
"""2026-10-16 回归：
1) anthropic_q3_revenue 实体合并 — Anthropic Q3 营收/估值披露 4 源
   (见闻168亿11 + FT quarterly revenue 9 + IT之家营收达168亿 6 + 见闻估值承压1.5万亿 6)
   此前拆占 财经TOP4+科技TOP5 两榜
2) amazon_bee_launch 实体合并 — 亚马逊旗下 Bee 发布 AI 录音设备
   (TechCrunch9 + Engadget6 + IT之家3) 拆占产业 TOP1+TOP3
3) us_sept_ppi 实体合并 — 美国9月PPI同比涨6.3%
   (见闻11 + 中央社9) 拆占 财经候选+宏观TOP5
4) classify — 卫报 "Tech market sell-off deepens" hot15 误分科技/AI TOP1 → 财经/投资
5) classify — 间谍规则排除产品语境 (Solidot "Ledger硬件钱包被植入间谍芯片" 误入宏观 TOP4)
6) NOISE — BBC中文 康奈尔兄弟会性侵案 (宏观 TOP3) / TechCrunch Panos Panay 访谈特稿 (产业 TOP2)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import entity_key, is_noise, classify


# ── anthropic_q3_revenue ──────────────────────────────

def test_q3_jianwen_revenue():
    assert entity_key("报道：Anthropic Q3营收168亿美元，环比大涨46%，调整后盈利并实现正现金流",
                      "Anthropic向投资者披露，公司第三季度营收达168亿美元，并实现季度盈利") == 'anthropic_q3_revenue'

def test_q3_ft_english():
    assert entity_key("Anthropic tells investors quarterly revenue up 50% to $16.8bn ahead of IPO",
                      "The AI company's revenue growth and profitability claims ahead of IPO") == 'anthropic_q3_revenue'

def test_q3_itzhixun():
    assert entity_key("消息称 Anthropic 第三季度营收达 168 亿美元，已实现调整后盈利",
                      "IT之家 10 月 14 日消息，据 The Information 报道") == 'anthropic_q3_revenue'

def test_q3_valuation_pressure_not_slowdown():
    # "收入增速放缓" 财务语义 — 必须归营收事件而非 ai_slowdown_debate
    assert entity_key("Anthropic估值预期承压：收入增速放缓，部分投资者转向1.5万亿美元",
                      "华尔街对AI融资的态度正在出现微妙变化：银行仍愿意参与交易") == 'anthropic_q3_revenue'

def test_q3_personal_ai_opinion_excluded():
    # 虎嗅产品策略稿 — 无财务披露锚点不得并入
    ek = entity_key("为什么Anthropic不做Personal AI",
                    "不久前，9 月 29 日的 OpenAI DevDay 开发者日，舞台上飘出了几个圆滚滚的小气泡")
    assert ek != 'anthropic_q3_revenue'

def test_q3_eu_probe_excluded():
    # IT之家欧盟调查稿 — "营业额"不是营收锚点
    ek = entity_key("OpenAI 和 Anthropic 被欧盟调查，若认定违反 AI 法案最高罚全球 3% 营业额",
                    "欧盟委员会正在调查两家公司")
    assert ek != 'anthropic_q3_revenue'

def test_q3_ftc_probe_excluded():
    ek = entity_key("Report: FTC probes Anthropic, OpenAI after Trump dismissed AI fears as \u201choax\u201d",
                    "The FTC has opened an investigation")
    assert ek != 'anthropic_q3_revenue'

def test_slowdown_financial_growth_word_blocked():
    # 负向后顾双保险: 无 q3 锚的"增速放缓"财务稿也不得进放缓辩论
    ek = entity_key("某AI公司增速放缓，市场关注后续融资", "分析师认为行业整体投入趋于理性")
    assert ek != 'ai_slowdown_debate'

def test_slowdown_genuine_still_works():
    ek = entity_key("Anthropic CEO 呼吁全球放缓前沿AI开发", "Dario Amodei 周六发文")
    assert ek == 'ai_slowdown_debate'


# ── amazon_bee_launch ──────────────────────────────

def test_bee_techcrunch():
    assert entity_key("Amazon\u2019s Bee launches two new personal AI devices, starting at $75",
                      "Amazon-owned Bee has launched its first new AI devices") == 'amazon_bee_launch'

def test_bee_engadget():
    assert entity_key("Bee unveils two AI note-taking devices, its first new products since being acquired by Amazon",
                      "The Eclipse and Frontier are cheap and colorful") == 'amazon_bee_launch'

def test_bee_itzhixun():
    assert entity_key("亚马逊旗下 Bee 推出两款 AI 录音产品：可穿戴设备 Frontier、手机磁吸配件 Eclipse，74.99 美元起",
                      "IT之家 10 月 15 日消息") == 'amazon_bee_launch'

def test_bee_beetaloo_guard():
    # 卫报 Beetaloo (澳洲排放议题) — \bbee\b 词边界必须拦截子串
    ek = entity_key("Resources minister faces calls to correct her claim all Beetaloo emissions will be offset",
                    "Environment groups said the claim was misleading")
    assert ek != 'amazon_bee_launch'


# ── us_sept_ppi ──────────────────────────────

def test_ppi_jianwen():
    assert entity_key("通胀全面超预期！美国9月PPI同比上涨6.3%，创四年来最高纪录，核心涨幅扩大至5%",
                      "美国劳工统计局公布的生产者物价指数大幅攀升") == 'us_sept_ppi'

def test_ppi_cna_traditional():
    assert entity_key("美國9月PPI年增6.3%　創2022年底以來最大增幅",
                      "美國政府今天公布，9月生產者物價指數（PPI）年增6.3%") == 'us_sept_ppi'

def test_ppi_china_5pct_guard():
    # 中国9月PPI涨5.0% — 无 6.3 锚不得并入
    ek = entity_key("中国9月CPI同比涨幅扩大至0.9%，汽油价格上涨16.6%，PPI同比涨5.0%，AI算力需求带动电子制造提价",
                    "国家统计局今日公布")
    assert ek != 'us_sept_ppi'


# ── classify: sell-off → 财经/投资 ──────────────────────────────

def test_selloff_classified_finance():
    assert classify("Tech market sell-off deepens amid fears over US inflation and AI debt", '综合') == '财经/投资'

def test_selloff_does_not_break_silicon_species():
    # 科技风险稿仍归科技/AI (无 sell-off 词)
    assert classify("Uncontrolled AI could lead to 'silicon species' rivalling humans, warns Microsoft", '财经') == '科技/AI'


# ── classify: 间谍产品语境不拉宏观 ──────────────────────────────

def test_spy_chip_not_macro():
    assert classify("Ledger 证实其硬件钱包被植入间谍芯片 提供硬件和软件钱包的 Ledger 公司证实", '科技') != '宏观政策'

def test_spy_chip_truncated_summary():
    # 实际管线形态: 摘要截断50字恰落在"被植入间谍"残尾 — 后缀前瞻够不到, 靠前顾(?<!植入)拦截
    assert classify("Ledger 证实其硬件钱包被植入间谍芯片 提供硬件和软件钱包的 Ledger 公司证实由 CryptoBilis 经销的部分硬件钱包被植入间谍", '科技') != '宏观政策'

def test_spyware_not_macro():
    # "零点击间谍软件" 后缀前瞻拦截
    assert classify("以色列公司通过数字广告安装零点击间谍软件 加拿大多伦多大学公民实验室发表研", '科技') != '宏观政策'

def test_spy_state_still_macro():
    assert classify("军情五处警告：中国资助英国研究的间谍机关渗透风险", '综合') == '宏观政策'

def test_spy_crime_arrest_still_macro():
    # "间谍罪" 不在产品后缀排除表内
    assert classify("日俄北方四岛争议：日本驻库页岛记者因间谍罪嫌被捕", '综合') == '宏观政策'


# ── zelda_totk_remake ──────────────────────────────

def test_zelda_it_physical_case():
    assert entity_key("任天堂展示《塞尔达传说：时之笛重制版》实体版包装：含特殊纹理烫箔，首发限量提供",
                      "任天堂 Switch 2 游戏现已开启预购") == 'zelda_totk_remake'

def test_zelda_it_review_details():
    assert entity_key("任天堂《塞尔达传说：时之笛 重制版》新细节：城镇全程自由视角，钱包容量翻倍",
                      "评测已解禁，IGN 等一众媒体刚刚放出了") == 'zelda_totk_remake'

def test_zelda_engadget_review():
    assert entity_key("The Legend of Zelda: Ocarina of Time remake plays even better than it has any right to",
                      "Nintendo keeps going back to its greatest hits") == 'zelda_totk_remake'

def test_zelda_other_remake_game_guard():
    # 裸"重制版"不带塞尔达锚不得并入
    ek = entity_key("《生化危机4》重制版 DLC 公布", " Capcom 今天公布")
    assert ek != 'zelda_totk_remake'


# ── NOISE ──────────────────────────────

def test_noise_cornell():
    assert is_noise("康奈尔大学因性侵案取消兄弟会派对 州政府官员和其他人士批评康奈尔大学和地方检察官处理此案的方式。")

def test_noise_cornell_english():
    assert is_noise("cornell university cancels fraternity party after sexual assault case")

def test_noise_panay_interview():
    assert is_noise("Amazon devices chief Panos Panay on the importance of failure and bouncing back from it")

def test_noise_guard_legit_company_news():
    # 正常公司新闻不误伤
    assert not is_noise("IBM 与西门子合作推进纳米堆叠架构，加速 3D 晶体管量产进程")
    assert not is_noise("男子发布 AI 视频造谣问界，赛力斯起诉索赔百万元")
