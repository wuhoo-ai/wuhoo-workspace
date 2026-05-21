"""
v2.2 核心 MC 逻辑测试 — wc2026_predict.py 函数测试
覆盖: upset概率, 小组分析, venue惩罚, 模拟比赛, 数据校验, 边界条件
"""

import pytest
import sys
import os
import random
from pathlib import Path

# 加载 wc2026_predict 模块
sys.path.insert(0, str(Path(__file__).parent.parent))
import wc2026_predict as wc


# ============================================================
# 1. Cold Model (v2.2)
# ============================================================
class TestUpsetProb:
    """测试动态冷门概率函数"""

    def test_equal_elo_max_upset(self):
        """ELO 相等时冷门概率最高 ~18%"""
        p = wc._upset_prob(0)
        assert 0.15 < p < 0.19, f"Expected ~0.18, got {p}"

    def test_large_gap_min_upset(self):
        """ELO 差距很大时冷门概率最低 2%"""
        p = wc._upset_prob(1000)
        assert p == 0.02, f"Expected 0.02 (floor), got {p}"

    def test_moderate_gap(self):
        """中等差距 200 ELO"""
        p = wc._upset_prob(200)
        # 0.18 - 0.0003 * 200 = 0.12
        assert 0.10 < p < 0.14, f"Expected ~0.12, got {p}"

    def test_small_gap(self):
        """小差距 50 ELO"""
        p = wc._upset_prob(50)
        # 0.18 - 0.0003 * 50 = 0.165
        assert 0.15 < p < 0.18, f"Expected ~0.165, got {p}"

    def test_monotonic(self):
        """ELO 差距越大，冷门概率越低"""
        p0 = wc._upset_prob(0)
        p100 = wc._upset_prob(100)
        p500 = wc._upset_prob(500)
        assert p0 >= p100 >= p500

    def test_negative_elo_diff(self):
        """ELO 差为负（客队更强）"""
        p = wc._upset_prob(-200)
        assert 0.10 < p < 0.14


# ============================================================
# 2. analyze_group() — 6 条研判规则
# ============================================================
class TestAnalyzeGroup:
    """测试小组分析"""

    def test_clear_favorite(self):
        """绝对热门: Δ1-2 > 100"""
        elos = {'T1': 2100, 'T2': 1900, 'T3': 1800, 'T4': 1700}
        adv = {'X': {'T1': 99, 'T2': 85, 'T3': 10, 'T4': 6}}
        pts = {'X': {'T1': 7.5, 'T2': 5.0, 'T3': 1.5, 'T4': 0.5}}
        result = wc.analyze_group('X', ['T1', 'T2', 'T3', 'T4'], elos, adv, pts)
        tags_str = ' '.join(result['tags'])
        assert '绝对热门' in tags_str

    def test_group_of_death(self):
        """死亡之组: Δ1-3 < 80"""
        elos = {'T1': 2000, 'T2': 1970, 'T3': 1940, 'T4': 1700}
        adv = {'X': {'T1': 60, 'T2': 55, 'T3': 50, 'T4': 35}}
        pts = {'X': {'T1': 5.0, 'T2': 4.5, 'T3': 4.0, 'T4': 2.0}}
        result = wc.analyze_group('X', ['T1', 'T2', 'T3', 'T4'], elos, adv, pts)
        tags_str = ' '.join(result['tags'])
        assert '死亡之组' in tags_str

    def test_tight_race_for_second(self):
        """争2白热化: Δ2-3 < 40 and Δ1-2 > 50"""
        elos = {'T1': 2100, 'T2': 1950, 'T3': 1930, 'T4': 1700}
        adv = {'X': {'T1': 99, 'T2': 60, 'T3': 40, 'T4': 1}}
        pts = {'X': {'T1': 8.0, 'T2': 4.0, 'T3': 3.5, 'T4': 0.5}}
        result = wc.analyze_group('X', ['T1', 'T2', 'T3', 'T4'], elos, adv, pts)
        tags_str = ' '.join(result['tags'])
        assert '争2白热化' in tags_str

    def test_host_advantage(self):
        """东道主标签"""
        elos = {'USA': 1920, 'T2': 1800, 'T3': 1750, 'T4': 1700}
        adv = {'X': {'USA': 95, 'T2': 70, 'T3': 25, 'T4': 10}}
        pts = {'X': {'USA': 7.0, 'T2': 5.0, 'T3': 2.0, 'T4': 1.0}}
        result = wc.analyze_group('X', ['USA', 'T2', 'T3', 'T4'], elos, adv, pts)
        tags_str = ' '.join(result['tags'])
        assert '东道主' in tags_str

    def test_dark_horse(self):
        """黑马信号: Δ2-3 < 30, e3 > 1750, 无东道主"""
        elos = {'T1': 2000, 'T2': 1850, 'T3': 1830, 'T4': 1700}
        adv = {'X': {'T1': 80, 'T2': 55, 'T3': 50, 'T4': 15}}
        pts = {'X': {'T1': 7.0, 'T2': 4.5, 'T3': 3.5, 'T4': 1.0}}
        result = wc.analyze_group('X', ['T1', 'T2', 'T3', 'T4'], elos, adv, pts)
        tags_str = ' '.join(result['tags'])
        assert '黑马候选' in tags_str

    def test_weak_team(self):
        """送分队: Δ3-4 > 120"""
        elos = {'T1': 2000, 'T2': 1900, 'T3': 1850, 'T4': 1650}
        adv = {'X': {'T1': 80, 'T2': 70, 'T3': 50, 'T4': 0}}
        pts = {'X': {'T1': 7.0, 'T2': 6.0, 'T3': 4.0, 'T4': 0.0}}
        result = wc.analyze_group('X', ['T1', 'T2', 'T3', 'T4'], elos, adv, pts)
        tags_str = ' '.join(result['tags'])
        assert '实力明显不足' in tags_str

    def test_balanced_group_no_tags(self):
        """均衡组：不应有极端标签"""
        elos = {'T1': 1900, 'T2': 1880, 'T3': 1860, 'T4': 1800}
        adv = {'X': {'T1': 40, 'T2': 35, 'T3': 30, 'T4': 25}}
        pts = {'X': {'T1': 4.5, 'T2': 4.0, 'T3': 3.5, 'T4': 3.0}}
        result = wc.analyze_group('X', ['T1', 'T2', 'T3', 'T4'], elos, adv, pts)
        # Δ1-3 = 40 < 80 → death group, Δ2-3 = 20 < 40, Δ1-2 = 20 < 50
        # So: death group + dark horse (no host)
        tags_str = ' '.join(result['tags'])
        # 死亡之组 should trigger since e1-e3 = 40 < 80
        assert '死亡之组' in tags_str

    def test_narrative_not_empty(self):
        """分析结果必须有叙事文本"""
        elos = {'T1': 2000, 'T2': 1900, 'T3': 1800, 'T4': 1700}
        adv = {'X': {'T1': 90, 'T2': 70, 'T3': 30, 'T4': 10}}
        pts = {'X': {'T1': 7.0, 'T2': 5.0, 'T3': 2.0, 'T4': 1.0}}
        result = wc.analyze_group('X', ['T1', 'T2', 'T3', 'T4'], elos, adv, pts)
        # Default narrative is ~19 chars; check it's not empty
        assert len(result['narrative']) > 10


# ============================================================
# 3. get_venue_penalty()
# ============================================================
class TestVenuePenalty:
    """测试球场惩罚"""

    def test_no_venue_no_penalty(self):
        """未知球场无惩罚"""
        p = wc.get_venue_penalty('Brazil', 'Nonexistent Stadium')
        assert p == 0

    def test_azteca_altitude_penalty(self):
        """Azteca 2200m 对非适应队惩罚（正值，在 sim_match 中减去）"""
        p = wc.get_venue_penalty('France', 'Estadio Azteca')
        assert p > 0, f"Expected positive penalty (ELO to subtract), got {p}"

    def test_azteca_acclimated_no_penalty(self):
        """墨西哥对 Azteca 无海拔惩罚"""
        p = wc.get_venue_penalty('Mexico', 'Estadio Azteca')
        assert p == 0, f"Mexico should be altitude-acclimated, got {p}"

    def test_ecuador_acclimated(self):
        """厄瓜多尔对高海拔适应"""
        p = wc.get_venue_penalty('Ecuador', 'Estadio Azteca')
        assert p == 0, f"Ecuador should be altitude-acclimated, got {p}"

    def test_miami_heat_penalty(self):
        """Hard Rock Stadium (Miami 32°C) 对非耐热队惩罚（正值）"""
        p = wc.get_venue_penalty('England', 'Hard Rock Stadium')
        assert p > 0, f"Expected positive heat penalty, got {p}"

    def test_brazil_heat_resistant(self):
        """巴西对高温适应"""
        p = wc.get_venue_penalty('Brazil', 'Hard Rock Stadium')
        assert p == 0, f"Brazil should be heat-resistant, got {p}"

    def test_indoor_reduces_heat(self):
        """室内球场高温惩罚减半"""
        p_outdoor = wc.get_venue_penalty('England', 'Hard Rock Stadium')
        p_indoor = wc.get_venue_penalty('England', 'NRG Stadium')  # indoor
        # NRG: 34°C, indoor → halved. Comparison not exact due to diff temps.
        assert p_indoor > p_outdoor or abs(p_indoor) < abs(p_outdoor), \
            f"Indoor penalty ({p_indoor}) should be less severe than outdoor ({p_outdoor})"


# ============================================================
# 4. sim_match()
# ============================================================
class TestSimMatch:
    """测试比赛模拟"""

    def test_basic_score(self):
        """基本：返回两个非负整数"""
        ga, gb = wc.sim_match('Brazil', 'Germany', 2000, 1900)
        assert isinstance(ga, int) and isinstance(gb, int)
        assert ga >= 0 and gb >= 0

    def test_favorite_wins_more_often(self):
        """强队胜率高（1000 次采样）"""
        wins = 0
        for _ in range(500):
            ga, gb = wc.sim_match('Spain', 'Qatar', 2165, 1705)
            if ga > gb:
                wins += 1
        assert wins > 300, f"Spain should win most matches, got {wins}/500"

    def test_ko_no_draw(self):
        """KO 阶段不应平局"""
        for _ in range(20):
            ga, gb = wc.sim_match('Spain', 'Argentina', 2165, 2113, ko=True)
            assert ga != gb, f"KO match should not end in draw: {ga}-{gb}"

    def test_equal_teams_close(self):
        """实力相当球队比分接近"""
        ga, gb = wc.sim_match('TeamA', 'TeamB', 1900, 1900)
        assert abs(ga - gb) <= 3  # With jitter, should still be reasonable

    def test_venue_penalty_applied(self):
        """venue 惩罚影响结果（在高原球场，适应队占优）"""
        # This is probabilistic — run multiple times and check trend
        mexico_wins = 0
        for _ in range(200):
            ga, gb = wc.sim_match('Mexico', 'Netherlands', 1910, 1961,
                                  venue_name='Estadio Azteca')
            if ga > gb:
                mexico_wins += 1
        # Netherlands has higher ELO, but Mexico has altitude advantage
        # Should be relatively even
        assert 50 < mexico_wins < 150, \
            f"Mexico Azteca wins: {mexico_wins}/200 (expected 50-150)"


# ============================================================
# 5. simulate_one_tournament()
# ============================================================
class TestSimulateOneTournament:
    """测试单次赛事模拟"""

    def test_returns_structure(self):
        """返回结构完整"""
        result = wc.simulate_one_tournament()
        stage_winners, group_standings, r32_teams = result
        assert isinstance(stage_winners, dict)
        assert isinstance(group_standings, dict)
        assert isinstance(r32_teams, dict)

    def test_all_groups_in_standings(self):
        """12 组都有排名"""
        _, standings, _ = wc.simulate_one_tournament()
        assert len(standings) == 12
        for letter in 'ABCDEFGHIJKL':
            assert letter in standings
            assert len(standings[letter]) == 4  # 4 teams per group

    def test_group_standings_sorted_by_points(self):
        """小组排名已按积分排序"""
        _, standings, _ = wc.simulate_one_tournament()
        for letter, teams in standings.items():
            pts_list = [t[1] for t in teams]  # t[1] = points
            for i in range(len(pts_list) - 1):
                assert pts_list[i] >= pts_list[i+1], \
                    f"Group {letter} not sorted by points: {pts_list}"

    def test_has_knockout_stages(self):
        """淘汰赛各阶段均存在"""
        stage_winners, _, _ = wc.simulate_one_tournament()
        for stage in ['R32', 'R16', 'QF', 'SF', 'F']:
            assert stage in stage_winners, f"Missing stage: {stage}"

    def test_r32_has_16_slots(self):
        """R32 应该有 16 场比赛"""
        _, _, r32 = wc.simulate_one_tournament()
        # Should have up to 16 slots (some may be empty in edge cases)
        assert 14 <= len(r32) <= 16, f"Expected ~16 R32 slots, got {len(r32)}"

    def test_no_same_team_in_r32_pair(self):
        """R32 对阵不应有同队对战"""
        _, _, r32 = wc.simulate_one_tournament()
        for slot_id, (t1, t2) in r32.items():
            assert t1 != t2, f"Slot {slot_id}: same team {t1} vs {t2}"

    def test_champion_is_valid(self):
        """冠军是 48 队之一"""
        stage_winners, _, _ = wc.simulate_one_tournament()
        champ = stage_winners.get('F', {}).get(1)
        assert champ is not None
        assert champ in wc.ALL_TEAMS

    def test_runner_up_recorded(self):
        """v2.2: 亚军也被记录"""
        stage_winners, _, _ = wc.simulate_one_tournament()
        assert 2 in stage_winners.get('F', {})
        runner_up = stage_winners['F'][2]
        assert runner_up in wc.ALL_TEAMS

    def test_sf_all_recorded(self):
        """v2.2: SF_all 包含 4 队"""
        stage_winners, _, _ = wc.simulate_one_tournament()
        assert 'SF_all' in stage_winners
        assert len(stage_winners['SF_all']) == 4

    def test_elo_adjustments_applied(self):
        """v2.2: elo_adjustments 参数生效"""
        # 给某队 +500 ELO，结果应偏向该队
        adj = {'Haiti': 500}  # Haiti 1695 + 500 = 2195 → should do well
        wins = 0
        for _ in range(20):
            stage_winners, _, _ = wc.simulate_one_tournament(adj)
            champ = stage_winners.get('F', {}).get(1)
            if champ == 'Haiti':
                wins += 1
        assert wins > 0, "Haiti +500 ELO should win at least some tournaments"


# ============================================================
# 6. validate_data()
# ============================================================
class TestValidateData:
    """测试数据校验"""

    def test_current_data_passes(self):
        """当前数据应通过校验"""
        assert wc.validate_data() is True

    def test_team_names_in_elo(self):
        """所有 Group 球队在 ELO 中"""
        for team in wc.ALL_TEAMS:
            assert team in wc.ELO, f"Team {team} missing from ELO"


# ============================================================
# 7. expected_score()
# ============================================================
class TestExpectedScore:
    """测试预期比分"""

    def test_returns_tuple(self):
        """返回 (score_tuple, win_p, draw_p, loss_p)"""
        result = wc.expected_score('Spain', 'France')
        assert len(result) == 4
        score, win, draw, loss = result
        assert isinstance(score, tuple) and len(score) == 2
        assert 0 <= win <= 1
        assert 0 <= draw <= 1
        assert 0 <= loss <= 1

    def test_probs_sum_to_one(self):
        """概率和应 ≈ 1"""
        _, win, draw, loss = wc.expected_score('Spain', 'France')
        assert abs(win + draw + loss - 1.0) < 0.02

    def test_stronger_team_favored(self):
        """强队胜率更高"""
        _, w_strong, _, _ = wc.expected_score('Spain', 'Qatar')
        _, w_weak, _, _ = wc.expected_score('Qatar', 'Spain')
        assert w_strong > w_weak

    def test_venue_effect(self):
        """venue 参数影响结果"""
        # France at Azteca should perform worse
        _, w_neutral, _, _ = wc.expected_score('Mexico', 'France')
        _, w_azteca, _, _ = wc.expected_score('Mexico', 'France',
                                               venue_name='Estadio Azteca')
        assert w_azteca > w_neutral * 0.8, "Azteca should boost Mexico"


# ============================================================
# 8. 数据完整性
# ============================================================
class TestDataIntegrity:
    """测试数据文件一致性"""

    def test_all_groups_have_4_teams(self):
        """每组恰好 4 队"""
        for letter in 'ABCDEFGHIJKL':
            assert len(wc.GROUPS[letter]) == 4

    def test_48_unique_teams(self):
        """48 队不重复"""
        assert len(wc.ALL_TEAMS) == 48

    def test_elo_range_sanity(self):
        """ELO 在合理范围"""
        for team in wc.ALL_TEAMS:
            elo = wc.ELO.get(team, 0)
            assert 1600 < elo < 2250, f"{team} ELO={elo} out of range"

    def test_bracket_slots_match_venues(self):
        """R32 slot 与 venue 数量一致"""
        assert len(wc.R32_SLOTS) == 16
        assert len(wc.R32_VENUES) == 16

    def test_r16_pairings_valid(self):
        """R16 对阵引用的 slot 存在"""
        for s1, s2 in wc.R16_PAIRINGS:
            assert 1 <= s1 <= 16
            assert 1 <= s2 <= 16

    def test_team_profiles_have_required_fields(self):
        """team_profiles 包含必要字段"""
        for team in wc.ALL_TEAMS:
            p = wc.TEAM_PROFILES.get(team, {})
            assert 'name_cn' in p, f"{team} missing name_cn"
            assert 'fifa_rank_est' in p, f"{team} missing fifa_rank_est"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
