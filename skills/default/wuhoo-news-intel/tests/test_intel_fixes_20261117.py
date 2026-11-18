#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""2026-11-17 P0/P1 修复回归测试。
覆盖: 实体别名扩充(P0-2锚点)/STOP_TICKERS泛词/P1-5动态别名与规范键/
P0-2确定性归并规则/P1-4噪声过滤与豁免/P0-1覆盖解析/LLM归并解析(mock)/单源降权。
全部纯逻辑或内存DB, 不触真实 news.db / 不调真实 LLM。
"""
import json
import sqlite3
from unittest.mock import patch, MagicMock

import pytest

import event_center as ec
import intel
import synthesize as sy


def mem_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    ec.init_db(c)
    c.execute("CREATE TABLE articles (id INTEGER PRIMARY KEY, feed_name TEXT, title TEXT, "
              "summary TEXT, content TEXT, link TEXT, category TEXT, fetched_at TEXT, hash TEXT)")
    return c


class TestEntityAliases:
    def test_canonical_entity(self):
        assert ec.canonical_entity("宁德时代") == "CATL"
        assert ec.canonical_entity("五粮液") == "WULIANGYE"
        assert ec.canonical_entity("黄仁勋") == "JENSEN_HUANG"
        assert ec.canonical_entity("fitb") == "FITB"
        assert ec.canonical_entity("贵州茅台") == "MOUTAI"

    def test_person_anchor_crosslingual(self):
        zh = ec.extract_entities("消息称黄仁勋回归尚未进入英伟达董事会议程")
        en = ec.extract_entities("Trump says it certainly isn't a bad idea for Jensen Huang to return to Nvidia")
        assert "JENSEN_HUANG" in zh and "NVIDIA" in zh
        assert "JENSEN_HUANG" in en and "NVIDIA" in en and "TRUMP" in en
        assert len(zh & en) >= 2  # 确定性归并的实体锚前提

    def test_stop_tickers_junk(self):
        ents = ec.extract_entities("US stocks rise as TO OF IN SAYS SH SZ HK EU report")
        for junk in ("US", "TO", "IN", "OF", "SAYS", "SH", "SZ", "HK", "EU"):
            assert junk not in ents

    def test_holding_tickers_kept(self):
        ents = ec.extract_entities("FITB and HBAN report earnings; FAST raises guidance")
        assert {"FITB", "HBAN", "FAST"} <= ents

    def test_us_holding_aliases(self):
        assert "FITB" in ec.extract_entities("五三银行季度业绩")
        assert "FAST" in ec.extract_entities("Fastenal quarterly results")
        assert "HBAN" in ec.extract_entities("亨廷顿银行公告")


class TestDynamicAliases:
    def test_interest_seed_registration(self):
        c = mem_conn()
        c.execute("INSERT INTO interest_profile(key,weight,updated,source,origin_profile,expires) "
                  "VALUES('entity:五粮液',0.3,'2026-11-17','test','trader','2027-01-15')")
        ec.refresh_dynamic_aliases(c)
        assert "WULIANGYE" in ec.extract_entities("五粮液今日涨停")
        # 规范键对齐: canonical_entity 与抽取结果一致 → salience gain 可命中
        assert ec.canonical_entity("五粮液") == "WULIANGYE"
        c.close()

    def test_watchlist_registration(self):
        c = mem_conn()
        c.execute("INSERT INTO watchlist(kind,value,threshold,alert_channel,enabled,origin_profile) "
                  "VALUES('keyword','皮影','yellow','weixin',1,'gamedev')")
        ec.refresh_dynamic_aliases(c)
        assert "皮影" in ec.extract_entities("皮影动画新工具发布")
        c.close()

    def test_catl_key_migration_alignment(self):
        # 宁德时代文本 → CATL; interest 键必须是 entity:CATL 才命中(旧键 entity:宁德时代 失效根因)
        c = mem_conn()
        ec.refresh_dynamic_aliases(c)
        ents = ec.extract_entities("宁德时代发布新电池")
        assert "CATL" in ents
        gain = {"entity:CATL": 0.3}.get("entity:" + next(iter(ents & {"CATL"})), 0)
        assert gain == 0.3
        c.close()


class TestSameStoryRule:
    STRONG = set(ec.ENTITY_ALIASES.values())

    def test_jensen_crosslingual_merge(self):
        shared = {"NVIDIA", "JENSEN_HUANG"}
        assert intel.same_story_rule("科技", "科技", shared, self.STRONG, 0.48) is True

    def test_rubin_vs_jensen_no_merge(self):
        assert intel.same_story_rule("科技", "科技", {"NVIDIA"}, self.STRONG, 0.19) is False

    def test_weak_only_shared_no_merge(self):
        assert intel.same_story_rule("财经", "财经", {"UBS", "SOME"}, self.STRONG, 0.9) is False

    def test_cross_topic_needs_three(self):
        shared = {"NVIDIA", "JENSEN_HUANG"}
        assert intel.same_story_rule("科技", "财经", shared, self.STRONG, 0.5) is False
        assert intel.same_story_rule("科技", "财经", shared | {"TRUMP"}, self.STRONG, 0.5) is True

    def test_cos_floor(self):
        shared = {"NVIDIA", "JENSEN_HUANG"}
        assert intel.same_story_rule("科技", "科技", shared, self.STRONG, 0.29) is False


class TestNoiseFilter:
    def _ev(self, c, aid, feed, title, eid=1):
        c.execute("INSERT INTO articles(id,feed_name,title) VALUES(?,?,?)", (aid, feed, title))
        return {"event_id": eid, "canonical_id": aid}

    def test_sa_transcript_filtered(self):
        c = mem_conn()
        ev = self._ev(c, 1, "Seeking Alpha", "Aramark (ARMK) Q4 2026 Earnings Call Transcript")
        assert intel.is_noise_candidate(c, ev, set()) is True
        c.close()

    def test_sa_fund_comment_filtered(self):
        c = mem_conn()
        ev = self._ev(c, 1, "Seeking Alpha", "Baron Global Durable Advantage ETF Q3 2026 Top Contributors And Detractors")
        assert intel.is_noise_candidate(c, ev, set()) is True
        c.close()

    def test_sa_slideshow_filtered(self):
        c = mem_conn()
        ev = self._ev(c, 1, "Seeking Alpha", "Unilever PLC (UL) Analyst/Investor Day - Slideshow")
        assert intel.is_noise_candidate(c, ev, set()) is True
        c.close()

    def test_sa_analysis_kept(self):
        c = mem_conn()
        ev = self._ev(c, 1, "Seeking Alpha", "Kratos Q3 2026: Great Tech, Heavy Armor, Thin Margins")
        assert intel.is_noise_candidate(c, ev, set()) is False
        c.close()

    def test_holding_transcript_exempt(self):
        c = mem_conn()
        ev = self._ev(c, 1, "Seeking Alpha", "Fastenal (FAST) Q3 2026 Earnings Call Transcript")
        c.execute("INSERT INTO entities(name,type) VALUES('FAST','auto')")
        ent_id = c.execute("SELECT entity_id FROM entities WHERE name='FAST'").fetchone()[0]
        c.execute("INSERT INTO event_entities(event_id,entity_id,role) VALUES(1,?,'mention')", (ent_id,))
        assert intel.is_noise_candidate(c, ev, {"FAST"}) is False  # 持仓豁免
        assert intel.is_noise_candidate(c, ev, set()) is True
        c.close()

    def test_non_sa_transcript_filtered(self):
        c = mem_conn()
        ev = self._ev(c, 1, "其他源", "Some Corp Q3 2026 Earnings Call Transcript")
        assert intel.is_noise_candidate(c, ev, set()) is True
        c.close()

    def test_digest_meta_filtered(self):
        # 2026-11-18 用户拍板D: 每日聚合meta文章(摘要非新闻)无条件过滤
        for title in ("财联社早间新闻精选", "华尔街见闻早餐 | 11月18日",
                      "投资日历：本周大事前瞻", "晨会精华", "盘前必读",
                      "【早报】英伟达业绩全线超预期；标普500创连跌纪录",
                      "昨夜今晨重要资讯（11月17日-11月18日）",
                      "金十数据整理：每日全球大宗商品市场要闻速递（11月18日）"):
            c = mem_conn()
            ev = self._ev(c, 1, "财联社", title)
            assert intel.is_noise_candidate(c, ev, set()) is True, title
            c.close()

    def test_digest_meta_no_holding_exempt(self):
        # digest为跨主题聚合, 不豁免持仓(与SA机械类噪声的豁免语义不同)
        c = mem_conn()
        ev = self._ev(c, 1, "财联社", "财联社早间新闻精选")
        c.execute("INSERT INTO entities(name,type) VALUES('FAST','auto')")
        ent_id = c.execute("SELECT entity_id FROM entities WHERE name='FAST'").fetchone()[0]
        c.execute("INSERT INTO event_entities(event_id,entity_id,role) VALUES(1,?,'mention')", (ent_id,))
        assert intel.is_noise_candidate(c, ev, {"FAST"}) is True
        c.close()

    def test_normal_news_not_digest(self):
        c = mem_conn()
        ev = self._ev(c, 1, "财联社", "英伟达发布新一代GPU")
        assert intel.is_noise_candidate(c, ev, set()) is False
        c.close()

    def test_non_football_in_football_category(self):
        # 2026-11-18(D): Sky综合体育频道混入板球/F1 → 足球类目内排除
        c = mem_conn()
        c.execute("INSERT INTO articles(id,feed_name,title,category) VALUES(1,'Sky Sports Football',"
                  "'England bat first vs Australia in series-deciding third ODI LIVE!','足球')")
        ev = {"event_id": 1, "canonical_id": 1}
        assert intel.is_noise_candidate(c, ev, set()) is True
        c.close()

    def test_football_news_kept(self):
        c = mem_conn()
        c.execute("INSERT INTO articles(id,feed_name,title,category) VALUES(1,'Sky Sports Football',"
                  "'Haaland fires Norway into Nations League quarters','足球')")
        ev = {"event_id": 1, "canonical_id": 1}
        assert intel.is_noise_candidate(c, ev, set()) is False
        c.close()

    def test_cricket_in_general_category_kept(self):
        # 仅作用足球类目, 综合源的板球新闻不过度过滤
        c = mem_conn()
        c.execute("INSERT INTO articles(id,feed_name,title,category) VALUES(1,'BBC World',"
                  "'England win Ashes Test at Hobart','综合')")
        ev = {"event_id": 1, "canonical_id": 1}
        assert intel.is_noise_candidate(c, ev, set()) is False
        c.close()

    def test_non_football_boxing_golf_racing(self):
        # Sky综合频道存量污染: 拳击WBC/高尔夫DP World Tour/赛马chasing debut
        for title in ("WBC 'absolutely' backs Kabayel title unification",
                      "Bryson 'box office' for DP World Tour but what about Ryder Cup?",
                      "Supreme hero Old Park Star makes chasing debut at Ffos Las"):
            c = mem_conn()
            c.execute("INSERT INTO articles(id,feed_name,title,category) VALUES(1,'Sky Sports Football',?,'足球')",
                      (title,))
            ev = {"event_id": 1, "canonical_id": 1}
            assert intel.is_noise_candidate(c, ev, set()) is True, title
            c.close()

    def test_non_gaming_entertainment(self):
        # IGN全量feed存量污染: 影视娱乐(James Bond选角)在游戏类目内排除
        c = mem_conn()
        c.execute("INSERT INTO articles(id,feed_name,title,category) VALUES(1,'IGN',?,'游戏')",
                  ("Robert Pattinson's James Bond Casting Process Details Revealed by Amazon's Jeff Bezos",))
        ev = {"event_id": 1, "canonical_id": 1}
        assert intel.is_noise_candidate(c, ev, set()) is True
        c.close()

    def test_gaming_news_kept(self):
        c = mem_conn()
        c.execute("INSERT INTO articles(id,feed_name,title,category) VALUES(1,'IGN',?,'游戏')",
                  ("GTA 6 Fans Baffled After Jason's Actor Gets Left Out of Game Awards Nominations",))
        ev = {"event_id": 1, "canonical_id": 1}
        assert intel.is_noise_candidate(c, ev, set()) is False
        c.close()

    def test_entertainment_in_general_category_kept(self):
        c = mem_conn()
        c.execute("INSERT INTO articles(id,feed_name,title,category) VALUES(1,'BBC World',"
                  "'James Bond casting announcement draws fans','综合')")
        ev = {"event_id": 1, "canonical_id": 1}
        assert intel.is_noise_candidate(c, ev, set()) is False
        c.close()


class TestCoverageParse:
    def test_last_round(self, tmp_path):
        log = tmp_path / "hourly_fetch.log"
        log.write_text(
            "2026-11-17 12:00:00 START fetch\n"
            "  🔄 A (财经)... ✅ 10 条\n"
            "  🔄 B (科技)... ✅ 5 条\n"
            "  ⚠️  C: 解析失败 (<urlopen error [Errno 111] Connection refused>)\n"
            "  总条目:  100\n  新增:    15\n  重复:    80\n  失败:    1\n"
            "2026-11-17 12:01:00 END rc=0\n"
            "2026-11-17 13:00:00 START fetch\n"
            "  🔄 A (财经)... ✅ 10 条\n"
            "  🔄 B (科技)... ✅ 5 条\n"
            "  🔄 D (AI)... ✅ 3 条\n"
            "  ⚠️  C: 解析失败 (<urlopen error [Errno 111] Connection refused>)\n"
            "  ⚠️  E: 解析失败 (<urlopen error [Errno 111] Connection refused>)\n"
            "  总条目:  100\n  新增:    18\n  重复:    80\n  失败:    2\n"
            "2026-11-17 13:01:00 END rc=0\n", encoding="utf-8")
        cov = intel.parse_coverage(str(log))
        assert cov["ok"] == 3 and cov["failed"] == 2 and cov["refused"] == 2
        assert cov["total"] == 5 and cov["ratio"] == 0.6
        assert cov["ts"] == "2026-11-17T13:01:00"

    def test_empty_log(self, tmp_path):
        log = tmp_path / "empty.log"
        log.write_text("nothing here", encoding="utf-8")
        assert intel.parse_coverage(str(log)) is None


class TestLlmDedup:
    CANDS = [
        {"event_id": 1, "topic": "科技", "n_indep_sources": 4, "label": "黄仁勋回归中文", "salience": 46.0, "canonical_id": 101},
        {"event_id": 2, "topic": "科技", "n_indep_sources": 3, "label": "Jensen Huang return", "salience": 21.0, "canonical_id": 102},
        {"event_id": 3, "topic": "科技", "n_indep_sources": 1, "label": "Rubin GPU", "salience": 19.0, "canonical_id": 103},
    ]

    def test_groups_parsed_and_validated(self):
        c = mem_conn()
        with patch.object(sy, "call_qwen", return_value={
                "content": '{"groups":[[1,2],[3],[99,1]]}', "usage": {"total_tokens": 500}}):
            groups, usage = intel.llm_dedup(c, self.CANDS)
        assert groups == [[1, 2]]  # 单元素组/非法ID剔除
        assert usage["total_tokens"] == 500
        c.close()

    def test_error_fallback_signal(self):
        c = mem_conn()
        with patch.object(sy, "call_qwen", return_value={"error": "429 quota/rate", "quota": True}):
            groups, usage = intel.llm_dedup(c, self.CANDS)
        assert groups is None  # → build_groups 回退确定性
        c.close()

    def test_parse_failed_fallback(self):
        c = mem_conn()
        with patch.object(sy, "call_qwen", return_value={"content": "不是JSON", "usage": {}}):
            groups, _ = intel.llm_dedup(c, self.CANDS)
        assert groups is None
        c.close()

    def test_build_groups_primary_order(self):
        c = mem_conn()
        with patch.object(intel, "llm_dedup", return_value=([[1, 2]], {"total_tokens": 10})):
            groups, mode, usage = intel.build_groups(c, self.CANDS, set())
        assert mode == "llm+deterministic"  # 并集语义(2026-11-17): LLM组+确定性组
        merged = [g for g in groups if len(g) > 1][0]
        assert merged[0]["event_id"] == 1  # salience 高者为主
        assert any(g[0]["event_id"] == 3 for g in groups if len(g) == 1)
        c.close()


class TestDeterministicGroups:
    def test_jensen_merge_rubin_split(self):
        import numpy as np
        c = mem_conn()
        # 三个事件: 1中文Jensen 2英文Jensen 3Rubin; 规范向量手造
        for eid, aid, ents in ((1, 101, ["NVIDIA", "JENSEN_HUANG"]),
                               (2, 102, ["NVIDIA", "JENSEN_HUANG", "TRUMP"]),
                               (3, 103, ["NVIDIA", "CUDA", "HPC"])):
            c.execute("INSERT INTO articles(id,feed_name,title) VALUES(?,?,?)", (aid, "f", "t"))
            v = np.zeros(384, np.float32)
            v[eid] = 1.0
            if eid in (1, 2):
                v[0] = 0.7  # 1/2 共享方向 → cos≈0.58; 3 与它们 cos≈0
                v = v / np.linalg.norm(v)
            c.execute("INSERT INTO article_vectors(article_id,emb,dim,model) VALUES(?,?,384,'test')",
                      (aid, v.tobytes()))
            for en in ents:
                c.execute("INSERT OR IGNORE INTO entities(name,type) VALUES(?,'auto')", (en,))
                ent_id = c.execute("SELECT entity_id FROM entities WHERE name=?", (en,)).fetchone()[0]
                c.execute("INSERT INTO event_entities(event_id,entity_id,role) VALUES(?,?,'mention')", (eid, ent_id))
        cands = [{"event_id": e, "canonical_id": a, "topic": "科技", "salience": 10.0, "n_indep_sources": 2}
                 for e, a in ((1, 101), (2, 102), (3, 103))]
        groups = intel.deterministic_groups(c, cands, set())
        assert [1, 2] in groups or [2, 1] in groups
        assert not any(3 in g for g in groups)
        c.close()


class TestSelection:
    def test_single_source_discount(self):
        ev1 = {"salience": 20.0, "n_indep_sources": 1}
        ev2 = {"salience": 20.0, "n_indep_sources": 3}
        assert intel.sel_score(ev1) == pytest.approx(18.0)
        assert intel.sel_score(ev2) == 20.0

    def test_resolve_key_canonical(self):
        assert intel.resolve_key("宁德时代") == "entity:CATL"
        assert intel.resolve_key("英伟达") == "entity:NVIDIA"
        assert intel.resolve_key("财经") == "topic:财经"
        assert intel.resolve_key("科技") == "topic:科技"


class TestModelConfig:
    def test_production_model(self):
        assert sy.MODEL == "qwen4-max"  # 用户 2026-11-17 拍板


class TestCallQwen429Backoff:
    """2026-11-18: 429 瞬时 RPM/TPM 限流应退避重试(15/30/60s), 连续失败才标 quota。
    修复前: 单次 429 立即 quota=True → Budget.quota 停掉整个门户后续合成(13类目构建实测触发)。"""

    def _http_error(self):
        import io
        import urllib.error
        return urllib.error.HTTPError(
            "http://x/chat/completions", 429, "Too Many Requests", {},
            io.BytesIO(b'{"error":{"message":"Requests rate limit exceeded"}}'))

    def _ok_resp(self):
        resp = MagicMock()
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        resp.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "OK"}}], "usage": {"total_tokens": 10}}).encode()
        return resp

    def test_transient_429_retries_then_succeeds(self):
        with patch.object(sy.urllib.request, "urlopen",
                          side_effect=[self._http_error(), self._http_error(), self._ok_resp()]), \
             patch.object(sy.time, "sleep") as ms, \
             patch.object(sy, "_KEY", "test-key"):
            r = sy.call_qwen("s", "u", max_tokens=16)
        assert r.get("content") == "OK" and not r.get("quota")
        assert [c.args[0] for c in ms.call_args_list] == [15, 30]

    def test_persistent_429_marks_quota(self):
        with patch.object(sy.urllib.request, "urlopen",
                          side_effect=[self._http_error() for _ in range(4)]), \
             patch.object(sy.time, "sleep") as ms, \
             patch.object(sy, "_KEY", "test-key"):
            r = sy.call_qwen("s", "u", max_tokens=16)
        assert r.get("quota") is True and "429" in r.get("error", "")
        assert [c.args[0] for c in ms.call_args_list] == [15, 30, 60]

    def test_5xx_retry_semantics_unchanged(self):
        # 非429的5xx仍走原多1次重试语义, 4xx立即返回
        import io
        import urllib.error
        err500 = urllib.error.HTTPError("http://x", 500, "ISE", {}, io.BytesIO(b"oops"))
        with patch.object(sy.urllib.request, "urlopen",
                          side_effect=[err500, self._ok_resp()]), \
             patch.object(sy.time, "sleep") as ms, \
             patch.object(sy, "_KEY", "test-key"):
            r = sy.call_qwen("s", "u", max_tokens=16)
        assert r.get("content") == "OK"
        ms.assert_not_called()  # 5xx 不退避(原语义)
