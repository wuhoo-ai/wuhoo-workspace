# -*- coding: utf-8 -*-
"""portal.py 回归测试（2026-11-17 门户定制）。纯逻辑/合成数据, 不调 LLM 不碰生产 DB。"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import portal


def ev(label, topic="财经", ents=None, eid=1, sal=10.0, n=2):
    return {"event_id": eid, "label": label, "topic": topic, "salience": sal,
            "n_indep_sources": n, "canonical_id": eid, "last_seen": "2026-11-17T08:00:00",
            "ents": set(ents or []), "sel": sal, "cat": None}


class TestClassify:
    def test_a_hk_entity_priority(self):
        e = ev("某公司发布新产品", topic="科技", ents={"CATL"})
        assert portal.classify(e, e["ents"]) == "a_hk"

    def test_crypto_keyword(self):
        assert portal.classify(ev("比特币突破10万美元"), set()) == "crypto"

    def test_commodity_keyword(self):
        assert portal.classify(ev("OPEC延长减产，原油价格上涨"), set()) == "commodity"

    def test_macro_keyword(self):
        assert portal.classify(ev("美联储暗示12月降息"), set()) == "macro"

    def test_a_hk_keyword(self):
        assert portal.classify(ev("北交所新股申购中签率出炉"), set()) == "a_hk"

    def test_ai_tech_keyword_over_finance_topic(self):
        assert portal.classify(ev("OpenAI发布新模型", topic="财经"), set()) == "ai_tech"

    def test_topic_fallback(self):
        assert portal.classify(ev("某财报超预期", topic="财经"), set()) == "finance"
        assert portal.classify(ev("某AI论文", topic="AI"), set()) == "ai_tech"
        assert portal.classify(ev("某游戏更新", topic="游戏"), set()) == "gaming"
        assert portal.classify(ev("某赛事", topic="足球"), set()) == "football"

    def test_priority_crypto_over_commodity(self):
        # "黄金" 在 commodity, 但 "比特币黄金" 含 crypto 词 → crypto 优先
        assert portal.classify(ev("比特币与黄金同涨"), set()) == "crypto"

    def test_pingan_not_christmas(self):
        # "平安夜" 不应误判 A股(模式用 中国平安 全称); v3: 含"消费"关键词 → consumer
        assert portal.classify(ev("平安夜消费数据", topic="财经"), set()) == "consumer"


class TestHelpers:
    def test_heat_pct_bounds(self):
        assert portal.heat_pct(0, 0) == 4
        assert portal.heat_pct(50, 100) == 50
        assert portal.heat_pct(200, 100) == 100
        assert portal.heat_pct(0.1, 100) == 4

    def test_first_sentence(self):
        assert portal.first_sentence("第一句。第二句很长很长", 80) == "第一句。"
        assert portal.first_sentence("短", 80) == "短"
        long = "x" * 100
        assert portal.first_sentence(long, 80).endswith("…")

    def test_budget_guard(self):
        b = portal.Budget(100)
        assert b.ok()
        b.tokens = 100
        assert not b.ok()
        b2 = portal.Budget(100)
        b2.quota = True
        assert not b2.ok()
        # budget 耗尽时 llm 返回 None 且不调用(零token)
        assert b.llm("s", "u") is None


class TestHotlistCross:
    def test_match_by_title(self, tmp_path, monkeypatch):
        evs = [ev("财政部发布中加经济财金战略对话联合成果文件", eid=10, sal=50)]
        evs[0]["ents"] = set()
        signals = {"computed_at": "2026-11-17T15:20:50", "signals": [
            {"item_id": 1, "title": "财政部发布中加经济财金战略对话联合成果文件",
             "platform": "weibo", "url": "https://weibo.com/x", "best_rank": 3,
             "latest_rank": 5, "rank_delta": 2, "velocity": 2.0},
            {"item_id": 2, "title": "完全无关的娱乐八卦标题", "platform": "douyin",
             "url": "https://douyin.com/y", "best_rank": 1, "velocity": 3.0}]}
        monkeypatch.setattr(portal, "DATA", str(tmp_path))
        (tmp_path / "velocity_signals.json").write_text(json.dumps(signals, ensure_ascii=False))
        import sqlite3
        c = sqlite3.connect(":memory:")
        out = portal.hotlist_cross(c, evs)
        assert len(out["matched"]) == 1
        assert out["matched"][0]["event_id"] == 10
        assert out["matched"][0]["platforms"][0]["platform"] == "微博"
        assert len(out["blind"]) == 1  # 无关高rank条目进盲区
        c.close()


class TestRender:
    def _data(self):
        cd = {"event_id": 1, "title": "测试事件", "topic": "财经", "n_indep": 3,
              "salience": 20.0, "fact": "事实第一句。第二句。", "impact": "影响",
              "divergence": "", "next_step": "下一步", "unverified_numbers": [],
              "links": [{"url": "https://example.com", "feed": "测试源"}],
              "primary_entities": ["CATL"], "_cat": "a_hk"}
        return {
            "meta": {"date": "2026-11-17", "edition": "morning", "model": "qwen4-max",
                     "generated_at": "2026-11-17 16:00", "data_asof": "16:00",
                     "tokens": 1000, "calls": 5, "quota_hit": False, "partial": False,
                     "coverage": {"ok": 85, "total": 91, "ratio": 0.9341, "ts": "2026-11-17T15:17:35"}},
            "overview": "今日总览测试文本。", "headlines": [cd],
            "categories": {k: {"cards": [cd] if k == "a_hk" else [],
                               "heat_list": [{"event_id": 9, "title": "热度条目", "cat": "a_hk", "sel": 8.0,
                                              "n_indep": 2, "ents": ["CATL"], "summary": "摘要。", "lead": "摘要。",
                                              "members": [{"title": "成员", "feed": "源", "url": "https://m.com", "pub_date": "2026-11-17"}],
                                              "merged_from": None}] if k == "a_hk" else [],
                               "digest": "导读" if k == "a_hk" else "",
                               "merged": [], "mode": "llm+deterministic", "n_total": 2} for k, _, _ in portal.CATEGORIES},
            "interest": {"radar": {"CATL": [{"event_id": 1, "title": "测试事件", "sel": 20.0,
                                             "cat": "a_hk", "n_indep": 3}],
                                   "FITB": []},
                         "enhanced": [{"event_id": 2, "title": "增强卡", "cat": "finance",
                                       "salience": 15.0, "n_indep": 2, "fact": "事实",
                                       "background": "背景补充(模型知识,非当日报道):某公司主业。",
                                       "impact": "影响", "data": "", "divergence": "",
                                       "next_step": "下一步", "unverified_numbers": [],
                                       "links": [], "fulltext_fetched": ["https://example.com"],
                                       "primary_entities": ["FITB"]}],
                         "watchlist_hits": [{"keyword": "宁德时代", "items": [
                             {"title": "命中文章", "feed_name": "财联社", "link": "https://x.com", "pub_date": ""}]}],
                         "interest_entities": ["CATL", "FITB"]},
            "hotlist": {"computed_at": "2026-11-17T15:20:50",
                        "matched": [{"event_id": 1, "title": "测试事件", "sel": 20.0,
                                     "platforms": [{"platform": "微博", "best_rank": 3,
                                                    "latest_rank": 5, "rank_delta": 2,
                                                    "url": "https://weibo.com", "velocity": 2.0}]}],
                        "blind": [{"title": "盲区条目", "platform": "抖音", "best_rank": 1,
                                   "url": "https://douyin.com"}]},
            "archive": {"dailies": [{"date": "2026-11-17", "n_cards": 10, "tokens": 18000, "top_cat": "财经"}],
                        "editions": ["2026-11-17-morning"]},
        }

    def test_render_smoke(self):
        html = portal.render_html(self._data())
        assert "<!DOCTYPE html>" in html
        assert "Wuhoo 情报门户" in html
        for k, n, _ in portal.CATEGORIES:
            assert f'id="cat-{k}"' in html
        assert 'id="interest"' in html and 'id="hotlist"' in html and 'id="archive"' in html
        assert "背景补充(模型知识,非当日报道)" in html
        assert "今日无新增" in html  # FITB 空态
        assert "盲区条目" in html
        assert "data-theme" in html and "portal-theme" in html  # 夜间模式
        assert 'id="search"' in html
        assert "源覆盖 85/91" in html and "降级" not in html.split("今日总览")[0].replace("源覆盖降级", "")

    def test_render_degraded_banner(self):
        d = self._data()
        d["meta"]["coverage"] = {"ok": 40, "total": 91, "ratio": 0.44, "ts": "x"}
        html = portal.render_html(d)
        assert "源覆盖降级" in html

    def test_render_empty_category(self):
        d = self._data()
        d["categories"]["finance"] = {"cards": [], "digest": "", "merged": [], "mode": "empty"}
        html = portal.render_html(d)
        assert "今日该类目无显著事件" in html

    def test_card_search_attr(self):
        d = self._data()
        html = portal.render_html(d)
        assert 'data-search="' in html and "catl" in html.lower()


class TestPortalV2:
    """2026-11-17 用户反馈4点: 总览条目化/类目分页+热度榜/日期下拉/默认展开单列宽幅。"""

    def test_overview_structured(self):
        ov = {"mainline": "主线X", "points": [{"head": "要点一", "body": "展开一"},
                                            {"head": "要点二", "body": "展开二"}], "watch": "关注Y"}
        h = portal.render_overview(ov)
        assert "主线X" in h and "要点一" in h and "展开一" in h and "关注Y" in h
        assert "<ol" in h and "mainline" in h

    def test_overview_string_fallback(self):
        h = portal.render_overview("一段旧文本。")
        assert "一段旧文本" in h and "ovtext" in h

    def test_overview_empty(self):
        assert portal.render_overview("") == ""
        assert portal.render_overview(None) == ""

    def test_compact_render(self):
        item = {"event_id": 5, "title": "紧凑卡", "cat": "finance", "sel": 12.0, "n_indep": 3,
                "ents": ["NVIDIA"], "summary": "摘要正文。", "lead": "摘要正文。",
                "members": [{"title": "文章", "feed": "路透", "url": "https://x.com", "pub_date": "2026-11-17"}],
                "merged_from": [5, 6]}
        h = portal.render_compact(item, 5, 20.0, {})
        assert "<details open>" in h and "紧凑卡" in h and "#5" in h
        assert "路透" in h and "跨源归并" in h and 'class="card compact"' in h

    def test_compact_card_data(self):
        import sqlite3
        import event_center as ec
        c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
        c.execute("CREATE TABLE IF NOT EXISTS articles(id INTEGER PRIMARY KEY, feed_name TEXT, "
                  "title TEXT, summary TEXT, content TEXT, link TEXT, pub_date TEXT, category TEXT)")
        ec.init_db(c)
        c.execute("INSERT INTO articles(id,feed_name,title,summary,content,link,pub_date,category) "
                  "VALUES(?,?,?,?,?,?,?,?)",
                  (100, "路透", "标题A", "这是摘要第一句。第二句。", "", "https://a.com", "2026-11-17", "财经"))
        c.execute("INSERT INTO events(event_id,label,topic,salience,n_indep_sources,canonical_id,status) "
                  "VALUES(?,?,?,?,?,?,?)", (1, "事件A", "财经", 10.0, 2, 100, "active"))
        c.execute("INSERT INTO event_members(event_id,article_id,similarity) VALUES(?,?,?)", (1, 100, 1.0))
        c.commit()
        ev = {"event_id": 1, "label": "事件A", "cat": "finance", "sel": 10.0,
              "n_indep_sources": 2, "canonical_id": 100, "ents": {"NVIDIA"}}
        row = c.execute("SELECT event_id FROM events WHERE event_id=1").fetchone()
        item = portal.compact_card_data(c, ev, [row])
        assert item["event_id"] == 1 and item["lead"].startswith("这是摘要第一句")
        assert any(m["url"] == "https://a.com" for m in item["members"])
        c.close()

    def test_pagination_and_date_select(self):
        d = TestRender()._data()
        d["archive"]["editions"] = ["2026-11-17-morning", "2026-11-16-evening"]
        html = portal.render_html(d)
        assert 'id="dateSelect"' in html
        assert "/news/portal/2026-11-17-morning.html" in html
        assert "/news/portal/2026-11-16-evening.html" in html
        assert 'class="page active"' in html
        assert html.count('class="page"') >= 10
        assert 'id="prevPage"' in html and 'id="nextPage"' in html
        assert "grid-template-columns:1fr" in html
        assert "1fr 1fr" not in html
        assert "<details open>" in html

    def test_category_heat_list_rendered(self):
        d = TestRender()._data()
        html = portal.render_html(d)
        assert "热度条目" in html and 'class="card compact"' in html

    def test_heat_count_rule(self):
        # 冷类目(top<5)封顶8; 热类目按ratio纳入, 上限由CAT_LIST_MAX按类目覆盖(v3动态上限)
        assert portal.LIST_MIN == 8 and portal.LIST_MAX == 40
        assert portal.CAT_LIST_MAX["finance"] == 40 and portal.CAT_LIST_MAX["gaming"] == 10
        pool_hot = [{"sel": 100 - i} for i in range(60)]
        top = pool_hot[0]["sel"]
        n = len([e for e in pool_hot if e["sel"] >= top * portal.HEAT_RATIO])
        N = max(portal.LIST_MIN, min(portal.CAT_LIST_MAX["finance"], n))
        assert N == 40
        pool_cold = [{"sel": 3 - i * 0.1} for i in range(20)]
        topc = pool_cold[0]["sel"]
        nc = len([e for e in pool_cold if e["sel"] >= topc * portal.HEAT_RATIO])
        Nc = max(portal.LIST_MIN, min(portal.CAT_LIST_MAX["finance"], nc))
        if topc < portal.COLD_CAP:
            Nc = min(Nc, portal.LIST_MIN)
        assert Nc == 8

    def test_bounded_deep_pool_preserves_heat(self, monkeypatch):
        """财报日头部候选塌缩成巨组时, 热度榜仍保住头部池外候选(多样性不被吞空)。"""
        import sqlite3
        import event_center as ec
        c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
        ec.init_db(c)
        for i in range(1, 16):
            c.execute("INSERT INTO events(event_id,label,topic,salience,n_indep_sources,canonical_id,status,last_seen) "
                      "VALUES(?,?,?,?,?,?,?,?)",
                      (i, f"ev{i}", "科技", 50.0 - i, 2, i, "active", "2026-11-18T08:00:00"))
        c.commit()
        evs = [{"event_id": i, "label": f"ev{i}", "cat": "ai_tech", "sel": 50.0 - i,
                "n_indep_sources": 2, "canonical_id": i, "ents": {"NVIDIA"}, "topic": "科技",
                "last_seen": "2026-11-18T08:00:00"} for i in range(1, 16)]

        def fake_groups(conn, rows, keep):
            r = list(rows)  # 头部6候选 → 塌缩成2组(模拟NVIDIA财报过并)
            return [[r[0], r[1], r[2], r[3], r[4]], [r[5]]], "llm+deterministic", {"total_tokens": 10}

        monkeypatch.setattr(portal.intel, "build_groups", fake_groups)
        monkeypatch.setattr(portal.sy, "synthesize_event",
                            lambda conn, eid, **k: {"event_id": eid, "title": f"card{eid}", "fact": "f",
                                                    "usage": {"total_tokens": 100}, "links": [], "primary_entities": []})
        monkeypatch.setattr(portal, "compact_card_data",
                            lambda conn, ev, g: {"event_id": ev["event_id"], "title": ev["label"]})
        monkeypatch.setattr(portal.sy, "call_qwen",
                            lambda *a, **k: {"content": "导读文本", "usage": {"total_tokens": 10}})
        out = portal.synthesize_category(c, evs, set(), portal.Budget(90000))
        assert len(out["cards"]) == 2
        heat_ids = {h["event_id"] for h in out["heat_list"]}
        assert set(range(7, 16)) <= heat_ids  # 头部池外 ev7..ev15 全保留
        assert out["n_total"] == 11
        c.close()


class TestPortalV3:
    """2026-11-18 用户拍板A-F: 13类目/动态上限/军工加权/热度榜跨语去重(贪心非传递)。"""

    def test_thirteen_categories(self):
        keys = [k for k, _, _ in portal.CATEGORIES]
        assert len(keys) == 13
        assert {"us_stock", "pharma", "geopolitics", "new_energy", "consumer"} <= set(keys)
        assert set(portal.CAT_NAME) == set(keys)
        assert set(portal.CAT_FLOOR) == set(keys)
        assert set(portal.CAT_LIST_MAX) == set(keys)

    def test_classify_us_stock(self):
        assert portal.classify(ev("美股三大指数收涨，纳指创历史新高"), set()) == "us_stock"
        assert portal.classify(ev("Fifth Third Bancorp季度业绩超预期"), set()) == "us_stock"

    def test_classify_pharma(self):
        assert portal.classify(ev("恒瑞医药创新药获FDA批准"), set()) == "pharma"
        assert portal.classify(ev("医保目录调整启动"), set()) == "pharma"

    def test_classify_geopolitics(self):
        # 1117剖析中的漏网案例: 普京抵达深圳曾落财经兜底
        assert portal.classify(ev("普京抵达深圳进行国事访问"), set()) == "geopolitics"
        assert portal.classify(ev("国防部回应台海局势"), set()) == "geopolitics"

    def test_classify_new_energy(self):
        assert portal.classify(ev("宁德时代发布固态电池"), set()) == "new_energy"
        assert portal.classify(ev("比亚迪电动车交付量创新高"), set()) == "new_energy"

    def test_classify_consumer(self):
        assert portal.classify(ev("双十一消费数据出炉"), set()) == "consumer"
        assert portal.classify(ev("茅台批价回升"), set()) == "consumer"
        assert portal.classify(ev("京东零售业务增长"), set()) == "consumer"

    def test_retail_sales_data_goes_macro(self):
        # 零售销售=宏观数据, consumer用负向前瞻放行(零售(?!销售)), 不误抢macro
        assert portal.classify(ev("美国零售销售数据超预期"), set()) == "macro"
        assert portal.classify(ev("10年期美债收益率在零售销售数据发布后V形反转"), set()) == "macro"

    def test_sector_keyword_over_holding_entity(self):
        # sector类目在a_hk前: 持仓个股按主题归sector, 不再全落A股港股
        assert portal.classify(ev("宁德时代发布固态电池"), {"CATL"}) == "new_energy"
        assert portal.classify(ev("恒瑞医药创新药获FDA批准"), {"HENGRUI"}) == "pharma"
        assert portal.classify(ev("茅台批价回升"), {"MOUTAI"}) == "consumer"

    def test_entity_fallback_a_hk(self):
        # 无sector关键词的持仓事件仍经实体兜底归a_hk
        assert portal.classify(ev("某公司发布重大公告"), {"PINGAN"}) == "a_hk"

    def test_new_topic_fallbacks(self):
        assert portal.classify(ev("某新药进展", topic="医药"), set()) == "pharma"
        assert portal.classify(ev("某电池技术突破", topic="新能源"), set()) == "new_energy"
        assert portal.classify(ev("某链上动态", topic="加密"), set()) == "crypto"
        assert portal.classify(ev("某防务展观察", topic="军工"), set()) == "geopolitics"

    def test_word_boundary_no_false_positive(self):
        # Hegseth 尾音 eth 不触发 \bETH\b; Shanghai 尾音 ai 不触发 \bAI\b
        assert portal.classify(ev("Hegseth谈预算安排"), set()) != "crypto"
        assert portal.classify(ev("Shanghai城市治理报告"), set()) != "ai_tech"

    def test_cat_list_max_values(self):
        assert portal.CAND_PER_CAT == 40
        for k in ("finance", "ai_tech", "macro", "us_stock"):
            assert portal.CAT_LIST_MAX[k] == 40
        for k in ("a_hk", "commodity", "pharma", "new_energy", "consumer", "geopolitics"):
            assert portal.CAT_LIST_MAX[k] == 25
        for k in ("gaming", "crypto", "football"):
            assert portal.CAT_LIST_MAX[k] == 10
        assert portal.CAT_SALIENCE_MULT == {"geopolitics": 1.3}

    def _mem_with_events(self, n, cat, topic="财经", base=100.0):
        import sqlite3
        import event_center as ec
        c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
        ec.init_db(c)
        for i in range(1, n + 1):
            c.execute("INSERT INTO events(event_id,label,topic,salience,n_indep_sources,canonical_id,status,last_seen) "
                      "VALUES(?,?,?,?,?,?,?,?)",
                      (i, f"ev{i}", topic, base - i, 2, i, "active", "2026-11-18T08:00:00"))
        c.commit()
        evs = [{"event_id": i, "label": f"ev{i}", "cat": cat, "sel": base - i,
                "n_indep_sources": 2, "canonical_id": i, "ents": set(), "topic": topic,
                "last_seen": "2026-11-18T08:00:00"} for i in range(1, n + 1)]
        return c, evs

    def _fake_synth(self, monkeypatch):
        def fake_groups(conn, rows, keep):
            r = list(rows)  # 头部6候选 → 2组(模拟头部归并)
            return [[r[0], r[1], r[2], r[3], r[4]], [r[5]]], "llm+deterministic", {"total_tokens": 10}
        monkeypatch.setattr(portal.intel, "build_groups", fake_groups)
        monkeypatch.setattr(portal.sy, "synthesize_event",
                            lambda conn, eid, **k: {"event_id": eid, "title": f"card{eid}", "fact": "f",
                                                    "usage": {"total_tokens": 100}, "links": [], "primary_entities": []})
        monkeypatch.setattr(portal, "compact_card_data",
                            lambda conn, ev, g: {"event_id": ev["event_id"], "title": ev["label"]})
        monkeypatch.setattr(portal.sy, "call_qwen",
                            lambda *a, **k: {"content": "导读文本", "usage": {"total_tokens": 10}})

    def test_dynamic_cap_finance_40(self, monkeypatch):
        c, evs = self._mem_with_events(45, "finance")
        self._fake_synth(monkeypatch)
        out = portal.synthesize_category(c, evs, set(), portal.Budget(90000))
        assert len(out["cards"]) == 2
        assert len(out["heat_list"]) == 34  # 40候选 - 头部6 = 34热度榜
        assert out["n_total"] == 36 and out["heat_dup"] == 0
        c.close()

    def test_dynamic_cap_gaming_10(self, monkeypatch):
        c, evs = self._mem_with_events(20, "gaming", topic="游戏", base=50.0)
        self._fake_synth(monkeypatch)
        out = portal.synthesize_category(c, evs, set(), portal.Budget(90000))
        assert len(out["cards"]) == 2
        assert len(out["heat_list"]) == 4  # 上限10 - 头部6
        assert out["n_total"] == 6
        c.close()

    def test_geopolitics_salience_mult(self):
        import sqlite3
        import event_center as ec
        from datetime import datetime
        c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
        ec.init_db(c)
        c.execute("CREATE TABLE articles (id INTEGER PRIMARY KEY, feed_name TEXT, title TEXT, "
                  "summary TEXT, content TEXT, link TEXT, category TEXT, fetched_at TEXT, hash TEXT)")
        now = datetime.now().isoformat()
        for eid, label in ((1, "普京抵达深圳进行国事访问"), (2, "某银行发布季度报告")):
            c.execute("INSERT INTO articles(id,feed_name,title) VALUES(?,?,?)", (eid, "测试源", label))
            c.execute("INSERT INTO events(event_id,label,topic,salience,n_indep_sources,canonical_id,status,last_seen) "
                      "VALUES(?,?,?,?,?,?,?,?)", (eid, label, "财经", 10.0, 2, eid, "active", now))
        c.commit()
        evs, keep, n_noise = portal.load_window(c)
        by_id = {e["event_id"]: e for e in evs}
        assert by_id[1]["cat"] == "geopolitics"
        assert by_id[1]["sel"] == pytest.approx(13.0)  # 10 × 1.3 军工提权
        assert by_id[2]["cat"] == "finance"
        assert by_id[2]["sel"] == pytest.approx(10.0)  # 非军工类目不加权
        c.close()

    def _dedup_db(self, third_shared=True):
        import sqlite3
        import numpy as np
        import event_center as ec
        c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
        ec.init_db(c)
        for name in ("NVIDIA", "JENSEN_HUANG"):
            c.execute("INSERT INTO entities(name,type) VALUES(?,?)", (name, "auto"))
        ent_ids = {r["name"]: r["entity_id"] for r in c.execute("SELECT entity_id,name FROM entities")}
        # cos(A,B)=0.8 cos(A,C)=0.2 cos(B,C)≈0.748
        vecs = {101: (1.0, 0.0), 102: (0.8, 0.6), 103: (0.2, 0.9797958971)}
        for eid, aid in ((1, 101), (2, 102), (3, 103)):
            if eid < 3 or third_shared:
                for name in ("NVIDIA", "JENSEN_HUANG"):
                    c.execute("INSERT INTO event_entities(event_id,entity_id,role) VALUES(?,?,?)",
                              (eid, ent_ids[name], "mention"))
            v = np.zeros(384, dtype=np.float32)
            v[0], v[1] = vecs[aid]
            c.execute("INSERT INTO article_vectors(article_id,emb,dim,model) VALUES(?,?,?,?)",
                      (aid, v.tobytes(), 384, "test"))
        c.commit()
        return c

    def _evd(self, eid, aid, label, sel, topic="科技"):
        return {"event_id": eid, "canonical_id": aid, "label": label, "topic": topic,
                "sel": sel, "salience": sel, "n_indep_sources": 2, "ents": set(),
                "last_seen": "2026-11-18T08:00:00"}

    def test_dedup_heat_crosslingual(self):
        # 中英同故事(共享强实体+同主题+cos0.8): 热度榜条目被深度卡primary吸收
        c = self._dedup_db(third_shared=False)
        deep = self._evd(1, 101, "英伟达黄仁勋谈AI前景", 50.0)
        heat = [self._evd(2, 102, "Nvidia CEO Jensen Huang on AI outlook", 20.0),
                self._evd(3, 103, "苹果发布新款iPhone", 15.0)]
        out, ndup = portal.dedup_heat(c, heat, [deep], set())
        assert ndup == 1
        assert [e["event_id"] for e in out] == [3]
        c.close()

    def test_dedup_heat_greedy_non_transitive(self):
        # B与深度卡A同故事→丢; C与B同故事但与A cos=0.2<0.30 →
        # 贪心非传递: C不经B传递丢弃, 保留(防过并吞多样性)
        c = self._dedup_db(third_shared=True)
        deep = self._evd(1, 101, "英伟达黄仁勋谈AI前景", 50.0)
        heat = [self._evd(2, 102, "Nvidia CEO Jensen Huang on AI", 20.0),
                self._evd(3, 103, "黄仁勋确认英伟达新平台", 15.0)]
        out, ndup = portal.dedup_heat(c, heat, [deep], set())
        assert ndup == 1
        assert [e["event_id"] for e in out] == [3]
        c.close()

    def test_dedup_heat_empty(self):
        import sqlite3
        c = sqlite3.connect(":memory:")
        assert portal.dedup_heat(c, [], [], set()) == ([], 0)
        c.close()

    def test_synthesize_heat_dup_count(self, monkeypatch):
        # ev7与深度卡primary ev1同故事(实体+向量注入) → 热度榜去重1条, heat_dup字段记录
        import numpy as np
        c, evs = self._mem_with_events(15, "ai_tech", topic="科技", base=50.0)
        self._fake_synth(monkeypatch)
        for name in ("NVIDIA", "JENSEN_HUANG"):
            c.execute("INSERT INTO entities(name,type) VALUES(?,?)", (name, "auto"))
        ent_ids = {r["name"]: r["entity_id"] for r in c.execute("SELECT entity_id,name FROM entities")}
        for eid in (1, 7):
            for name in ("NVIDIA", "JENSEN_HUANG"):
                c.execute("INSERT INTO event_entities(event_id,entity_id,role) VALUES(?,?,?)",
                          (eid, ent_ids[name], "mention"))
        for aid in (1, 7):
            v = np.zeros(384, dtype=np.float32); v[0] = 1.0
            c.execute("INSERT INTO article_vectors(article_id,emb,dim,model) VALUES(?,?,?,?)",
                      (aid, v.tobytes(), 384, "test"))
        c.commit()
        out = portal.synthesize_category(c, evs, set(), portal.Budget(90000))
        assert out["heat_dup"] == 1
        assert 7 not in {h["event_id"] for h in out["heat_list"]}
        assert out["n_total"] == 10  # 2深度 + (9热度 - 1去重)
        c.close()