#!/usr/bin/env python3
"""
WC2026 体彩串关投注方案生成器 — v1.0
基于预测模型的胜平负概率，生成 100 元预算的串关投注组合。

核心思路：
  1. 将预测概率映射为竞彩赔率（含12%抽水）
  2. 计算每场比赛的「价值投注」方向
  3. 生成 2串1/3串1/4串1 多档组合
  4. 按 Kelly 比例分配 100 元资金

Usage:
  python3.11 scripts/lottery_parlay.py                          # 从未来4场预测中生成
  python3.11 scripts/lottery_parlay.py --matches 4              # 指定场次数
  python3.11 scripts/lottery_parlay.py --budget 200             # 自定义预算
  python3.11 scripts/lottery_parlay.py --json predictions.json  # 从JSON文件读取

依赖：wc2026_predict.py, team_profiles.json, wc2026_schedule.json
"""

import sys
import os
import json
import math
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

from wc2026_predict import predict_single_match, _get_schedule, TEAM_PROFILES

DATA_DIR = os.path.join(PROJECT_DIR, 'data')

# ============================================================
# 赔率模型 — 将预测概率映射为竞彩赔率（返奖率71%）
# ============================================================

# 概率校准温度 — 收缩极端概率（足球最大胜率约80-85%）
# T=1: 不校准; T=5: 中庸; T=10: 激进（99.9%→67%）
# 竞彩@1.26 隐含胜率56%，说明市场比模型现实得多
CALIBRATION_T = 5.0


def calibrate_prob(raw_prob_pct):
    """温度校准：用 logit 收缩把极端概率拉回足球现实区间。

    原始 99.9% → 79.9%（足球最大胜率约80%）
    原始 95.1% → 64.4%
    原始 50.0% → 50.0%（50%不变）
    原始 23.8% → 44.2%（提升平局概率）
    """
    import math
    p = raw_prob_pct / 100.0
    if p <= 0.01:
        return raw_prob_pct
    if p >= 0.99:
        p = 0.99
    logit = math.log(p / (1 - p))
    calibrated_logit = logit / CALIBRATION_T
    calibrated = 1.0 / (1.0 + math.exp(-calibrated_logit))
    return calibrated * 100.0

# 竞彩赔率标准档位（胜平负玩法，含超低赔）
ODDS_LEVELS = [
    1.01, 1.02, 1.03, 1.04, 1.05, 1.06, 1.07, 1.08, 1.10, 1.12,
    1.15, 1.18, 1.20, 1.22, 1.25, 1.28, 1.30, 1.33, 1.36, 1.40,
    1.44, 1.48, 1.53, 1.58, 1.62, 1.68, 1.72, 1.78, 1.83, 1.90,
    1.95, 2.00, 2.08, 2.15, 2.23, 2.32, 2.40, 2.50, 2.62, 2.75,
    2.90, 3.05, 3.20, 3.40, 3.60, 3.80, 4.00, 4.30, 4.60, 4.90,
    5.25, 5.70, 6.20, 6.80, 7.50, 8.50, 10.00, 12.00, 15.00, 20.00,
]


def prob_to_odds(prob_pct, is_favorite=True):
    """将模型概率映射为竞彩赔率。

    Args:
        prob_pct: 模型预测概率 (0-100)
        is_favorite: True 表示热门方（赔率较低）

    Returns:
        float: 估计的竞彩赔率
    """
    prob = prob_pct / 100.0
    if prob <= 0.001:
        prob = 0.001

    # 公平赔率
    fair_odds = 1.0 / prob

    # 庄家抽水 ~29%（竞彩返奖率约 71%）
    vig_factor = 0.71
    market_odds = fair_odds * vig_factor

    # 热门方赔率不能太低，冷门方有上限（竞彩区间 ~1.02-20.00）
    if is_favorite:
        market_odds = max(market_odds, 1.05)
        market_odds = min(market_odds, 5.00)
    else:
        market_odds = max(market_odds, 2.00)
        market_odds = min(market_odds, 20.00)

    # 取最近的标准赔率档位
    return min(ODDS_LEVELS, key=lambda x: abs(x - market_odds))


def get_cn_name(team_en):
    """获取中文队名"""
    return TEAM_PROFILES.get(team_en, {}).get('name_cn', team_en)


def get_pick_name(pick_type, team_a, team_b):
    """生成投注选项的中文名称"""
    cn_a = get_cn_name(team_a)
    cn_b = get_cn_name(team_b)
    if pick_type == 'home':
        return f"{cn_a} 胜"
    elif pick_type == 'draw':
        return f"{cn_a} vs {cn_b} 平局"
    elif pick_type == 'away':
        return f"{cn_b} 胜"
    return "未知"


# ============================================================
# 核心: 串关计划生成
# ============================================================

class ParlayPlan:
    """单个串关方案"""

    def __init__(self, name, risk_level, picks, allocation):
        self.name = name
        self.risk_level = risk_level
        self.picks = picks          # list of pick dicts
        self.allocation = allocation  # RMB

    @property
    def n_legs(self):
        return len(self.picks)

    @property
    def combined_prob(self):
        """模型预测的组合胜率"""
        p = 1.0
        for pick in self.picks:
            p *= pick['prob'] / 100.0
        return p

    @property
    def combined_odds(self):
        """组合赔率（各场赔率相乘）"""
        o = 1.0
        for pick in self.picks:
            o *= pick['odds']
        return round(o, 2)

    @property
    def max_return(self):
        """最高可能回报"""
        return round(self.allocation * self.combined_odds, 2)

    @property
    def expected_return(self):
        """期望回报（模型概率加权）"""
        return round(self.allocation * self.combined_prob * self.combined_odds, 2)

    @property
    def expected_profit(self):
        """期望收益"""
        return round(self.expected_return - self.allocation, 2)

    @property
    def ev_pct(self):
        """期望收益率"""
        return round((self.expected_return / self.allocation - 1) * 100, 1)

    @property
    def ev_color(self):
        """EV 状态图标"""
        if self.ev_pct > 5:
            return '🟢'
        elif self.ev_pct > -10:
            return '🟡'
        else:
            return '🔴'

    def format(self):
        """格式化为可读的报告"""
        lines = []
        lines.append(f"## {self.name}  {'🔵保守' if self.risk_level == 'low' else '🟡均衡' if self.risk_level == 'medium' else '🔴进取'}")

        # 各场分析
        lines.append("")
        lines.append("| # | 比赛 | 投注选项 | 模型概率 | 估测赔率 |")
        lines.append("|---|------|----------|----------|----------|")
        for i, pick in enumerate(self.picks, 1):
            m = pick['match']
            cn_a = get_cn_name(m['team_a'])
            cn_b = get_cn_name(m['team_b'])
            lines.append(
                f"| {i} | {m['date_beijing']} {cn_a} vs {cn_b} | "
                f"{pick['pick_name']} | {pick['prob']:.1f}% | @{pick['odds']:.2f} |"
            )

        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 🎯 玩法 | **{self.n_legs}串1** |")
        lines.append(f"| 💰 投入 | **{self.allocation} 元** |")
        lines.append(f"| 📊 模型胜率 | {self.combined_prob * 100:.1f}% |")
        lines.append(f"| 📈 综合赔率 | @{self.combined_odds} |")
        lines.append(f"| 🏆 最高回报 | **{self.max_return} 元** |")
        lines.append(f"| 📐 期望回报 | {self.expected_return} 元 |")
        lines.append(f"| 📐 期望收益 | {self.ev_color} {self.expected_profit:+.1f} 元 (EV: {self.ev_pct:+.1f}%) |")
        lines.append("")

        return '\n'.join(lines)


def generate_parlay_plan(matches, budget=100):
    """生成100元预算的串关投注方案 — v2.0 全组合分散策略。

    与 v1.0 的关键区别：
    - v1.0: 每场只选单一最优方向 → 单注全押
    - v2.0: 枚举所有 (主/平/客) 组合 → EV×概率加权分配

    这样中奖率从 ~25% 提升到 ~50%，更符合"娱乐为主"的目标。

    Args:
        matches: list of dicts with schedule + prediction
        budget: total budget in RMB (default 100)

    Returns:
        list of DiversifiedParlay plans, skipped info
    """
    # 第一步: 收集每场比赛的三个方向（概率+赔率），过滤鸡肋场次
    match_outcomes = []  # [{name, outcomes: [{label, prob, odds}, ...]}, ...]
    skipped = []

    for m in matches:
        audit = m['audit']
        team_a = audit['team_a']
        team_b = audit['team_b']
        pred = audit['prediction']

        cn_a = get_cn_name(team_a)
        cn_b = get_cn_name(team_b)

        p_home = pred['team_a_win']
        p_draw = pred['draw']
        p_away = pred['team_b_win']

        # 三个方向的赔率（先校准概率再算赔率）
        cp_home = calibrate_prob(p_home)
        cp_draw = calibrate_prob(p_draw)
        cp_away = calibrate_prob(p_away)
        odds_home = prob_to_odds(cp_home, is_favorite=(p_home >= p_draw and p_home >= p_away))
        odds_draw = prob_to_odds(cp_draw, is_favorite=False)
        odds_away = prob_to_odds(cp_away, is_favorite=(p_away >= p_home and p_away >= p_draw))

        outcomes = [
            {'label': f'{cn_a} 胜', 'prob': cp_home, 'odds': odds_home},
            {'label': f'平局', 'prob': cp_draw, 'odds': odds_draw},
            {'label': f'{cn_b} 胜', 'prob': cp_away, 'odds': odds_away},
        ]

        # 跳过逻辑：如果最强的方向赔率 < 1.15，整场跳过
        # 🔑 跳过"鸡肋赔率"：赔率 < 1.05 的超级热门不加回报只加风险
        best_outcome = max(outcomes, key=lambda x: x['prob'])
        if best_outcome['odds'] < 1.05 and best_outcome['prob'] > 90:
            skipped.append({
                'match': f"{cn_a} vs {cn_b}",
                'pick': best_outcome['label'],
                'prob': best_outcome['prob'],
                'odds': best_outcome['odds'],
                'reason': f"赔率过低(@{best_outcome['odds']})，串关中不加回报只加风险"
            })
            continue

        match_outcomes.append({
            'name': f"{cn_a} vs {cn_b}",
            'date': m['schedule'].get('date_beijing', '?'),
            'time': m['schedule'].get('time_beijing', '?'),
            'team_a': team_a, 'team_b': team_b,
            'cn_a': cn_a, 'cn_b': cn_b,
            'outcomes': outcomes,
        })

    if len(match_outcomes) < 2:
        return [], skipped

    # 第二步: 生成所有子集组合（2场、3场、...、N场）
    # 不只全量笛卡尔积，也枚举任意2场/3场子集
    import itertools
    all_combos = []

    for subset_size in range(2, len(match_outcomes) + 1):
        for subset_indices in itertools.combinations(range(len(match_outcomes)), subset_size):
            subset_matches = [match_outcomes[i] for i in subset_indices]
            for combo in itertools.product(*[sm['outcomes'] for sm in subset_matches]):
                prob = 1.0
                odds = 1.0
                legs = []
                for j, oc in enumerate(combo):
                    prob *= oc['prob'] / 100.0
                    odds *= oc['odds']
                    sm = subset_matches[j]
                    legs.append({
                        'match': sm['name'],
                        'date': sm['date'],
                        'time': sm['time'],
                        'pick': oc['label'],
                        'prob': oc['prob'],
                        'odds': oc['odds'],
                    })

                ev_per_yuan = prob * odds
                if prob < 0.02:
                    continue

                all_combos.append({
                    'legs': legs,
                    'prob': prob,
                    'odds': round(odds, 2),
                    'ev_per_yuan': ev_per_yuan,
                    'n_legs': subset_size,
                    'subset_indices': list(subset_indices),
                })

    # 第三步: 按 EV×概率 综合评分排序，分配资金
    for c in all_combos:
        c['score'] = c['ev_per_yuan'] * (c['prob'] ** 0.3)

    all_combos.sort(key=lambda x: x['score'], reverse=True)

    # ============================================================
    # 策略 A: 集中筹码 — Top-2 组合，各 50%
    # ============================================================
    n_concentrated = min(2, len(all_combos))
    top_concentrated = all_combos[:n_concentrated]
    alloc_concentrated = []
    if n_concentrated == 1:
        alloc_concentrated = [budget // 2]  # 集中只用一半预算
    else:
        mid = budget // 2 // 2
        alloc_concentrated = [mid, budget // 2 - mid]

    def union_prob(combos_list):
        """计算任意一注中奖概率（1 - 全不中）"""
        p = 1.0
        for c in combos_list:
            p *= (1.0 - c['prob'])
        return 1.0 - p

    total_prob_c = union_prob(top_concentrated)
    total_ev_c = sum(c['ev_per_yuan'] * a for c, a in zip(top_concentrated, alloc_concentrated))

    plan_concentrated = DiversifiedParlay(
        name="集中串关",
        combos=list(zip(top_concentrated, alloc_concentrated)),
        total_budget=sum(alloc_concentrated),
        total_hit_prob=total_prob_c,
        total_ev=total_ev_c,
        skipped=skipped,
    )

    # ============================================================
    # 策略 B: 全覆盖 — Top-N 组合，按评分比例分配
    # ============================================================
    n_covered = min(8, len(all_combos))
    top_covered = all_combos[:n_covered]
    
    # 按 score 比例分配覆盖预算（预算的一半用于覆盖）
    cover_budget = budget // 2
    total_score = sum(c['score'] for c in top_covered)
    alloc_covered = []
    for c in top_covered:
        if total_score > 0:
            alloc = max(5, round(cover_budget * c['score'] / total_score / 5) * 5)  # 5元取整
        else:
            alloc = cover_budget // n_covered
        alloc_covered.append(alloc)
    
    # 调整总和 = cover_budget
    diff = cover_budget - sum(alloc_covered)
    if diff != 0 and alloc_covered:
        alloc_covered[0] += diff  # 多退少补到第一个

    total_prob_cv = union_prob(top_covered)
    total_ev_cv = sum(c['ev_per_yuan'] * a for c, a in zip(top_covered, alloc_covered))

    plan_covered = DiversifiedParlay(
        name="全覆盖串关",
        combos=list(zip(top_covered, alloc_covered)),
        total_budget=sum(alloc_covered),
        total_hit_prob=total_prob_cv,
        total_ev=total_ev_cv,
        skipped=skipped,
    )

    return [plan_concentrated, plan_covered], skipped


class DiversifiedParlay:
    """多组合分散投注方案"""

    def __init__(self, name, combos, total_budget, total_hit_prob, total_ev, skipped):
        self.name = name
        self.combos = combos          # [(combo_dict, allocation), ...]
        self.total_budget = total_budget
        self.total_hit_prob = total_hit_prob
        self.total_ev = total_ev
        self.skipped = skipped

    @property
    def total_max_return(self):
        return round(max(c['odds'] * a for c, a in self.combos), 0)

    @property
    def ev_pct(self):
        return round((self.total_ev / self.total_budget - 1) * 100, 1)

    @property
    def ev_color(self):
        if self.ev_pct > 5:
            return '🟢'
        elif self.ev_pct > -10:
            return '🟡'
        else:
            return '🔴'

    def format(self):
        lines = []
        lines.append(f"## {self.name}  🎯 {len(self.combos)}注集中")

        lines.append("")
        lines.append("| # | 投入 | 组合 | 概率 | 赔率 | 中奖回报 |")
        lines.append("|---|------|------|------|------|----------|")
        for i, (combo, alloc) in enumerate(self.combos, 1):
            leg_str = " + ".join(l['pick'] for l in combo['legs'])
            payout = round(alloc * combo['odds'])
            lines.append(
                f"| {i} | **{alloc}元** | {leg_str} | "
                f"{combo['prob']*100:.1f}% | @{combo['odds']} | {payout}元 |"
            )

        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 💰 总投入 | **{self.total_budget} 元** |")
        lines.append(f"| 🎯 总中奖概率 | {self.total_hit_prob*100:.1f}% （任意一注中奖） |")
        lines.append(f"| 🏆 最高单注回报 | **{self.total_max_return:.0f} 元** |")
        lines.append(f"| 📐 期望总回报 | {self.total_ev:.1f} 元 |")
        lines.append(f"| 📐 期望收益 | {self.ev_color} {self.total_ev - self.total_budget:+.1f} 元 (EV: {self.ev_pct:+.1f}%) |")

        return '\n'.join(lines)


def generate_parlay_report(plans, skipped, budget):
    """生成完整的投注报告 — v2.2 双策略：集中 + 全覆盖"""
    lines = []
    lines.append("# 🎲 WC2026 体彩串关投注计划")
    lines.append(f"")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} BJT")
    lines.append(f"> 总预算: **{budget} 元** | 娱乐为主，理性投注")
    if len(plans) >= 2:
        lines.append(f"> 策略A: **集中筹码** (50元) + 策略B: **全覆盖** (50元)")
    elif plans:
        plan = plans[0]
        lines.append(f"> 策略: **{plan.name}** — {len(plan.combos)}注")
    lines.append(f"> 已跳过: {len(skipped)} 场超级热门")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 跳过的比赛说明
    if skipped:
        lines.append("## ⏭️ 已跳过的比赛")
        lines.append("")
        lines.append("以下比赛因赔率过低（超级热门）被跳过——串关中几乎不加回报，只增加「翻车」风险：")
        lines.append("")
        lines.append("| 比赛 | 建议投注 | 概率 | 估算赔率 | 跳过原因 |")
        lines.append("|------|----------|------|----------|----------|")
        for s in skipped:
            lines.append(f"| {s['match']} | {s['pick']} | {s['prob']:.1f}% | @{s['odds']:.2f} | {s['reason']} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 各方案详情
    for plan in plans:
        lines.append(plan.format())
        lines.append("")
        lines.append("---")
        lines.append("")

    # 汇总
    if plans:
        lines.append("## 📊 资金汇总")
        lines.append("")
        lines.append(f"| 策略 | 投入 | 中奖概率 | 最高回报 | 期望收益 |")
        lines.append(f"|------|------|----------|----------|----------|")
        for plan in plans:
            lines.append(
                f"| **{plan.name}** | {plan.total_budget}元 | {plan.total_hit_prob*100:.1f}% | "
                f"{plan.total_max_return:.0f}元 | {plan.ev_color} {plan.total_ev - plan.total_budget:+.0f}元 (EV: {plan.ev_pct:+.1f}%) |"
            )
        
        total_budget_all = sum(p.total_budget for p in plans)
        total_ev_all = sum(p.total_ev for p in plans)
        total_ev_pct = round((total_ev_all / total_budget_all - 1) * 100, 1)
        lines.append(
            f"| **合计** | **{total_budget_all}元** | — | — | "
            f"{'🟢' if total_ev_pct > 5 else '🟡' if total_ev_pct > -10 else '🔴'} "
            f"{total_ev_all - total_budget_all:+.0f}元 (EV: {total_ev_pct:+.1f}%) |"
        )
        lines.append("")

    # 风险提示
    lines.append("---")
    lines.append("")
    lines.append("## ⚠️ 风险提示")
    lines.append("")

    has_negative_ev = any(p.ev_pct < -5 for p in plans)
    if has_negative_ev:
        lines.append("> 🔴 **当前方案存在负期望值（EV < -5%）！**")
        lines.append("> 这意味着从数学模型看，长期执行此策略**大概率亏损**。")
        lines.append("> 竞彩抽水 ~12% 意味着大多数串关的数学期望为负。")
        lines.append("> 以下方案仅供娱乐——把它当成看球时的「参与感」而非投资。")
        lines.append("")

    lines.append("- 所有赔率为基于模型概率的**估测值**，实际赔率以体彩店为准")
    lines.append("- 串关玩法中**任意一场错误则全单作废**，风险随关数指数上升")
    lines.append("- 本方案仅供娱乐参考，**不构成任何投注建议**")
    lines.append("- 请理性购彩，量力而行。未成年人不得购彩")
    lines.append("")
    if plans:
        plan = plans[0]
        lines.append(f"> 🎲 模型说: {'集中火力，博高回报！' if plan.total_hit_prob > 0.25 else '谨慎为上，娱乐第一！'}")

    return '\n'.join(lines)


def get_next_n_matches(n):
    """获取未来 N 场比赛的赛程"""
    sched = _get_schedule()
    matches = sched['matches']
    matches.sort(key=lambda m: (m['date_beijing'], m['time_beijing']))

    now_bjt = datetime.now(timezone(timedelta(hours=8)))
    now_str = now_bjt.strftime('%H:%M')
    today_str = now_bjt.strftime('%Y-%m-%d')

    upcoming = []
    for m in matches:
        dt = (m['date_beijing'], m['time_beijing'])
        now_dt = (today_str, now_str)
        if dt > now_dt:
            upcoming.append(m)
            if len(upcoming) >= n:
                break

    return upcoming


def predict_matches(schedule_matches, enable_news=True):
    """对一组赛程运行预测"""
    results = []
    for m in schedule_matches:
        try:
            audit = predict_single_match(
                m['team_a'], m['team_b'],
                venue_name=m.get('venue'),
                enable_news=enable_news,
                knockout=False
            )
            results.append({'schedule': m, 'audit': audit})
        except Exception as e:
            print(f"  ⚠️ 预测失败 {m['team_a']} vs {m['team_b']}: {e}", file=sys.stderr)
    return results


def load_from_json(json_path):
    """从 JSON 预测文件加载"""
    with open(json_path) as f:
        data = json.load(f)
    # Try to match against schedule
    sched = _get_schedule()
    sched_by_id = {m['match_id']: m for m in sched['matches']}

    results = []
    for p in data.get('predictions', [data]):
        match_id = p.get('match_id', 0)
        schedule = sched_by_id.get(match_id, {
            'match_id': match_id,
            'date_beijing': '?',
            'time_beijing': '?',
            'team_a': p.get('team_a', '?'),
            'team_b': p.get('team_b', '?'),
            'venue': p.get('venue', '?'),
            'group': p.get('group', '?'),
            'matchday': p.get('matchday', '?'),
        })
        audit = {
            'team_a': p.get('team_a', '?'),
            'team_b': p.get('team_b', '?'),
            'prediction': {
                'team_a_win': p.get('team_a_win_pct', 33),
                'draw': p.get('draw_pct', 34),
                'team_b_win': p.get('team_b_win_pct', 33),
            }
        }
        results.append({'schedule': schedule, 'audit': audit})
    return results


def main():
    budget = 100
    n_matches = 4
    enable_news = True
    json_path = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--budget' and i + 1 < len(args):
            budget = int(args[i + 1])
            i += 2
        elif args[i] == '--matches' and i + 1 < len(args):
            n_matches = int(args[i + 1])
            i += 2
        elif args[i] == '--no-news':
            enable_news = False
            i += 1
        elif args[i] == '--json' and i + 1 < len(args):
            json_path = args[i + 1]
            i += 2
        else:
            i += 1

    print(f"🎲 WC2026 体彩串关方案生成中...")
    print(f"📅 北京时间 (UTC+8)")
    print()

    # Step 1: 获取预测数据
    if json_path:
        print(f"📂 从文件加载: {json_path}")
        match_results = load_from_json(json_path)
    else:
        upcoming = get_next_n_matches(n_matches)
        if not upcoming:
            print("✅ 没有即将到来的比赛。")
            return

        print(f"🔮 预测 {len(upcoming)} 场比赛...")
        match_results = predict_matches(upcoming, enable_news=enable_news)
        print()

    # Step 2: 生成串关方案
    plans, skipped = generate_parlay_plan(match_results, budget)

    if not plans:
        print("⚠️ 没有足够的有效投注选项生成串关方案。")
        print("   （需要至少2场比赛且有明确的胜负方向，且赔率 > 1.15）")
        if skipped:
            print(f"\n⏭️ 跳过的比赛（赔率过低）:")
            for s in skipped:
                print(f"   {s['match']}: {s['pick']} @{s['odds']:.2f}")
        return

    # Step 3: 输出报告
    report = generate_parlay_report(plans, skipped, budget)
    print(report)


if __name__ == '__main__':
    main()
