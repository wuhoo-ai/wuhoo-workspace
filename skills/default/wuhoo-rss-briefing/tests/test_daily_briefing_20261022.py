# -*- coding: utf-8 -*-
"""2026-10-22 回归：
1) ENTITY claude_duet_launch — Anthropic 发布 Claude Duet 4 源拆占科技/AI TOP1+TOP3 合并；
   Engadget 标题含 "Meta Muse" 字样，规则顺序必须先于 meta_muse 抢判。
2) ENTITY france_unrest — 法国骚乱浪潮 10+ 篇 (繁简英文多语序) 跨 宏观/产业 两榜合并。
3) classify — 法国骚乱代表稿回归宏观政策 (产业表泛词"平台"命中"二手平台"不再抢走)。
防误并回归: 毛里求斯宵禁稿 / Muse 下载量稿 / Patriot 子串 / 万斯无骚乱词稿。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from daily_briefing import entity_key, classify

# ── 1) Claude Duet 发布合并 ──────────────────────────

def test_duet_ithome():
    assert entity_key(
        "24 小时为你在线打工：Anthropic 推出 Claude Duet AI 智能体，迎战 Meta 和 OpenAI",
        "IT之家 10 月 22 日消息，Anthropic 昨日宣布以研究预览版形式，推出全新应用 Claude Duet") == "claude_duet_launch"

def test_duet_engadget_beats_meta_muse():
    # Engadget 标题同时含 "Meta Muse" — 若 meta_muse 抢先，Claude Duet 会被并进 Muse 泛簇
    assert entity_key(
        "Claude Duet is Anthropic's answer to Meta Muse and OpenAI Dots",
        "Anthropic subscribers in the US can join a waitlist to try the company's new agent.") == "claude_duet_launch"

def test_duet_jianwen():
    assert entity_key(
        "Anthropic推出全天候AI智能体Claude Duet，与Meta、OpenAI展开竞争",
        "Anthropic正将AI竞争从模型能力延伸至任务执行。") == "claude_duet_launch"

def test_duet_hn_bare_title():
    assert entity_key("Claude Duet", "Article URL: https://claude.com/product/claude-duet") == "claude_duet_launch"

def test_muse_download_article_not_merged_into_duet():
    # Meta Muse 下载量稿不含 duet 字样，仍归 meta_muse 泛簇
    assert entity_key("Meta AI 助手 Muse 上线 40 天美国下载量破千万，仅 11 款应用曾达成该纪录",
                      "") != "claude_duet_launch"

def test_muse_suspend_still_own_key():
    k = entity_key("Meta suspends Muse chats sharing feature after it left private details exposed",
                   "Researchers could access 6,800 shared Muse conversations")
    assert k != "claude_duet_launch"

# ── 2) 法国骚乱多源合并 ──────────────────────────────

def test_france_bbc():
    assert entity_key("法国骚乱：巴黎局部宵禁 被劫商品现身二手平台",
                      "巴黎共和广场在示威期间曾发生纵火烧车等事件，警察在宵禁下加强布防") == "france_unrest"

def test_france_cna_traditional():
    assert entity_key("巴黎里昂等地局部宵禁　法國不排除宣布緊急狀態",
                      "法國上週末抗議物價高漲的示威活動演變成近年來最嚴重的街頭暴力衝突") == "france_unrest"

def test_france_cna_traditional2():
    assert entity_key("法國示威演變成暴力衝突　北部城市局部宵禁", "里爾等4座北部城市這兩天將在晚間8時至翌日清晨6時實施局部宵禁") == "france_unrest"

def test_france_rfi():
    assert entity_key("法国暴力事件：政府宣布首批措施，在巴黎、里昂、里尔和尼斯实施“局部”宵禁 - RFI - 法国国际广播电台",
                      "周一下午，法国政府宣布了应对全国多座城市周末骚乱的首批措施") == "france_unrest"

def test_france_dw():
    assert entity_key("法国宣布实施局部宵禁 暴力骚乱蔓延至欧洲多国",
                      "上周六法国全国约50万人走上街头抗议生活成本飙升") == "france_unrest"

def test_france_market_angle():
    # 见闻金融角度衍生稿 (法国国债抛售) — 同一骚乱事件的报道波次，并入
    assert entity_key("法国骚乱冲击金融市场，10年期国债收益率单日飙升14个基点，银行与零售股大跌",
                      "法国市场周一遭遇全面抛售") == "france_unrest"

def test_france_vance():
    assert entity_key("万斯发警告：希望美国人注意法国骚乱，这就是民主党人寻求的未来",
                      "法国近来爆发严重抗议，给该国造成巨大破坏") == "france_unrest"

def test_france_english_guardian():
    assert entity_key("France: partial curfew imposed in Paris after nights of rioting",
                      "Looters hit shops in Lyon") == "france_unrest"

def test_mauritius_curfew_not_merged():
    # 毛里求斯宵禁稿 — 无法国锚不命中
    assert entity_key("毛里求斯宣布全国多地实施宵禁", "毛里求斯总理拉姆古兰宣布多地宵禁") != "france_unrest"

def test_patriot_riot_substring_not_merged():
    # "Patriot" 含子串 riot — 词边界拦截；且无法国骚乱语境
    assert entity_key("Patriot missile production to double under new Pentagon deal",
                      "US allies in Europe to receive systems") != "france_unrest"

def test_france_food_news_not_merged():
    # 法国正常新闻无骚乱语系不命中
    assert entity_key("法国奢侈品牌开展秋冬新品发布", "巴黎时装周启幕") != "france_unrest"

# ── 3) classify: 法国骚乱代表稿回宏观 ────────────────

def test_classify_france_riot_macro():
    text = "法国骚乱：巴黎局部宵禁 被劫商品现身二手平台 巴黎共和广场在示威期间曾发生纵火烧车等事件，警察在宵禁下加强布防"
    assert classify(text, "综合") == "宏观政策"

def test_classify_france_riot_market_finance_kept():
    # 见闻金融角度稿自身有强财经语境，仍归财经不矛盾（宏观侧骚乱词仅 1 命中）
    text = "法国骚乱冲击金融市场，10年期国债收益率单日飙升14个基点，银行与零售股大跌 法国市场周一遭遇全面抛售"
    assert classify(text, "财经") in ("宏观政策", "财经/投资")

# ── 4) ENTITY china_rtx_order — 字节/阿里/腾讯英伟达显卡订单拆榜合并 ──

def test_rtx_solidot():
    assert entity_key("字节阿里腾讯订购了逾 350 亿美元的 RTX PRO 5500 显卡",
                      "字节跳动、阿里巴巴和腾讯已订购超过 300 万个、总值超过 350 亿美元的英伟达 RTX PRO 5500") == "china_rtx_order"

def test_rtx_rfi():
    assert entity_key("字节、阿里和腾讯向英伟达订购了总值逾350亿美元的显卡",
                      "据路透社援引两位知情人士报导称，字节跳动、阿里巴巴和腾讯已订购了超过300万张") == "china_rtx_order"

def test_rtx_false_merge_tiktok_orders():
    # TikTok 电商订单稿: 有字节+订单但无产品锚不命中
    assert entity_key("字节跳动旗下TikTok Shop季度订单量翻倍", "东南亚电商大促期间订单激增") != "china_rtx_order"

def test_rtx_false_merge_nvidia_earnings():
    assert entity_key("Nvidia reports record data center revenue in Q3", "") != "china_rtx_order"

def test_rtx_false_merge_google_nvidia():
    assert entity_key("Google has joined Amazon in attacking Nvidia's stronghold with AI app developers",
                      "Google has joined Amazon in releasing a developer alternative") != "china_rtx_order"

# ── 5) classify: 严重漏洞网络安全事件回科技/AI ──────────

def test_classify_php_vuln_tech():
    text = "AI发现PHP严重漏洞！全球75%网站面临威胁，欧洲多国政府网站紧急下线 全球互联网基础设施面临自人工智能工具普及以来最严峻的安全威胁之一"
    assert classify(text, "财经") == "科技/AI"

def test_classify_regulatory_loophole_not_flipped():
    # "监管漏洞" 不带 严重/高危/重大 前缀也不带 威胁/下线 组合，不被语境规则拉走
    text = "分析师指出该行权监管存在漏洞，董事会治理需加强，投资者建议关注合规风险"
    assert classify(text, "财经") == "财经/投资"

# ── 6) NOISE 亚马逊雨林特稿续 ─────────────────────────

def test_rainforest_guardian_noise():
    from daily_briefing import is_noise
    assert is_noise("Giving £2 a day to people in the Amazon helps protect rainforest, pilot project finds")

def test_amazon_company_news_not_noise():
    from daily_briefing import is_noise
    assert not is_noise("Amazon announces new AWS data center region in Germany")

def test_rtx_lianhezaobao_traditional_chip_wording():
    # 联合早报"晶片"措辞变体 (无显卡/RTX 字样但有 350亿+英伟达 锚) 须并入
    assert entity_key("路透：字节阿里腾讯订购总值逾350亿美元英伟达晶片", "") == "china_rtx_order"

# ── 回归: 旧实体规则不受新规则抢判 ───────────────────

def test_anthropic_q3_revenue_still_wins_over_duet_absent():
    assert entity_key("Anthropic tells investors quarterly revenue up 50% to $16.8bn ahead of IPO",
                      "") != "claude_duet_launch"

def test_gemini_hack_not_affected():
    assert entity_key("谷歌 Gemini 越狱后自主入侵三家真实企业", "安全研究人员利用越狱提示") == "gemini_hack_incident"
