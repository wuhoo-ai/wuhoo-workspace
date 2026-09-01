#!/usr/bin/env python3.11
"""WC2026 Bracket Report PDF — Chinese names, full match details, v5.5 styling."""
import json, os, sys
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, PageBreak, HRFlowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
REPORT_DIR = os.path.join(DATA_DIR, 'reports')
os.makedirs(REPORT_DIR, exist_ok=True)

# ── Fonts & Colours (same as single-match PDF) ──
FONT_PATH = os.path.expanduser('~/.fonts/NotoSansSC-VF.ttf')
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('CJK', FONT_PATH))
    FONT = 'CJK'
else:
    FONT = 'Helvetica'

BLUE = HexColor('#1a5276')
RED = HexColor('#c0392b')
GRAY = HexColor('#666666')
LIGHT_BG = HexColor('#eef5fb')
WHITE = HexColor('#ffffff')
DARK_BG = HexColor('#2980b9')

def S(name, **kw):
    d = dict(fontName=FONT, leading=18, spaceAfter=4)
    d.update(kw)
    from reportlab.lib.styles import ParagraphStyle
    return ParagraphStyle(name, **d)

TITLE = S('title', fontSize=18, textColor=BLUE, spaceAfter=10, leading=24)
H2 = S('h2', fontSize=14, textColor=BLUE, spaceAfter=6, spaceBefore=12, leading=20)
H3 = S('h3', fontSize=12, textColor=BLUE, spaceAfter=4, spaceBefore=10, leading=18)
BODY = S('body', fontSize=10, leading=16, spaceAfter=3)
SMALL = S('small', fontSize=8, textColor=GRAY, leading=12, spaceAfter=1)

# ── Chinese names ──
sys.path.insert(0, BASE_DIR)
from wc2026_predict import TEAM_PROFILES
_TEAMS = TEAM_PROFILES.get('teams', TEAM_PROFILES)

def cn(team_en):
    return _TEAMS.get(team_en, {}).get('name_cn', team_en)

def P(text, style=BODY):
    return Paragraph(text, style)

def make_table(headers, rows, col_widths=None):
    hcells = [P(h, H3) for h in headers]
    data = [hcells] + [[P(str(c), BODY) for c in r] for r in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
    ]))
    return t


def generate():
    with open(os.path.join(DATA_DIR, 'bracket_recursive_results.json')) as f:
        data = json.load(f)

    mds = data.get('match_details', {})
    adv = data.get('advancement_probs', {})
    champs = data.get('champion_probs', {})
    n_sims = data.get('n_sims', 10)

    out = os.path.join(REPORT_DIR, f'bracket_report_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf')
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    story = []

    story.append(P('WC2026 淘汰赛全量推演报告', TITLE))
    story.append(P(f'生成: {datetime.now().strftime("%Y-%m-%d %H:%M")} CST | 推演次数: {n_sims} | 模型: v5.5推理引擎+12层ELO', SMALL))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))

    # ── Champion (no bars, clean table) ──
    story.append(P('冠军概率', H2))
    rows = []
    for team, prob in sorted(champs.items(), key=lambda x: -x[1]):
        rows.append([cn(team), f'{prob:.0f}%'])
    story.append(make_table(['球队', '冠军概率'], rows, col_widths=[160, 120]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))

    # ── R16 Detailed ──
    story.append(P('R16 — 1/8决赛 单场预测详情', H2))
    for mid in [89, 90, 91, 92, 93, 94, 95, 96]:
        md = mds.get(str(mid), {})
        if not md or md.get('pending'):
            continue
        ta, tb = md.get('team_a', '?'), md.get('team_b', '?')
        cna, cnb = cn(ta), cn(tb)
        p = md.get('prediction', {})
        pa = p.get('team_a_win_pct', 0) or 0
        pd = p.get('draw_pct', 0) or 0
        pb = p.get('team_b_win_pct', 0) or 0
        ml = md.get('most_likely', '?')
        xg_a = p.get('expected_goals_a', '?')
        xg_b = p.get('expected_goals_b', '?')
        sc = md.get('scoreline_probs', [])
        sc_str = ', '.join(f'{s["score"]}({s["prob_pct"]}%)' for s in sc[:3]) if sc else '-'
        eff = md.get('effective_elo', {})
        ea = eff.get('team_a', {})
        eb = eff.get('team_b', {})
        elo_a = ea.get('effective', ea.get('base', '?')) if isinstance(ea, dict) else '?'
        elo_b = eb.get('effective', eb.get('base', '?')) if isinstance(eb, dict) else '?'
        diff = eff.get('diff', '?')

        if pa > 55:
            vtext = f'{cna} 胜（高置信度）'
        elif pb > 55:
            vtext = f'{cnb} 胜（高置信度）'
        elif pa > pd and pa > pb:
            vtext = f'{cna} 略优'
        elif pb > pd and pb > pa:
            vtext = f'{cnb} 略优'
        else:
            vtext = '势均力敌'

        story.append(P(f'M{mid}  {cna} vs {cnb}', H3))
        info_rows = [
            ['胜/平/负', f'{cna} {pa:.0f}% / 平 {pd:.0f}% / {cnb} {pb:.0f}%'],
            ['最可能比分', str(ml)],
            ['xG', f'{cna} {xg_a} - {xg_b} {cnb}'],
            ['比分 Top3', sc_str],
            ['有效ELO', f'{cna} {elo_a} vs {cnb} {elo_b} (差{diff})'],
            ['判定', vtext],
        ]
        story.append(make_table(['指标', '数据'], info_rows, col_widths=[80, 410]))
        story.append(Spacer(1, 5))

    story.append(PageBreak())

    # ── QF / SF / F ──
    for section_title, match_ids, show_table in [
        ('QF — 1/4决赛（确定性最可能路径）', [97, 98, 99, 100], True),
        ('SF — 半决赛（确定性最可能路径）', [101, 102], True),
        ('决赛 & 季军赛（确定性最可能路径）', [103, 104], True),
    ]:
        story.append(P(section_title, H2))
        qf_rows = []
        for mid in match_ids:
            md = mds.get(str(mid), {})
            if not md or md.get('pending'):
                qf_rows.append([f'M{mid}', '-', '-', '-', '-', '-'])
                continue
            ta, tb = md.get('team_a', '?'), md.get('team_b', '?')
            cna, cnb = cn(ta), cn(tb)
            p = md.get('prediction', {})
            pa = p.get('team_a_win_pct', 0) or 0
            pb = p.get('team_b_win_pct', 0) or 0
            ml = md.get('most_likely', '?')
            xg_a = p.get('expected_goals_a', '?')
            xg_b = p.get('expected_goals_b', '?')
            label = '季军赛' if mid == 103 else '决赛' if mid == 104 else ''
            qf_rows.append([f'M{mid} {label}', cna, cnb,
                          f'{pa:.0f}% / {100-pa-pb:.0f}% / {pb:.0f}%',
                          str(ml), f'xG: {xg_a}-{xg_b}'])
        if show_table:
            story.append(make_table(['#', '主队', '客队', '胜/平/负', '最可能比分', 'xG'], qf_rows,
                                    col_widths=[60, 65, 65, 85, 65, 70]))
            story.append(Spacer(1, 4))

    story.append(PageBreak())

    # ── Top 3 Bracket Paths ──
    top_paths = data.get('top_bracket_paths', [])
    if top_paths:
        story.append(P('概率性 Top 3 全路径（来自 Monte Carlo 采样，已合并相同路径）', H2))
        story.append(P('注意：上方 QF/SF/F 为确定性最可能路径；此处为概率推演中频率最高的 3 条完整路径', SMALL))
        stages_label = {"R16": "1/8决赛", "QF": "1/4决赛", "SF": "半决赛", "F": "决赛"}
        for i, tp in enumerate(top_paths[:3]):
            count = tp.get('count', 0)
            pct = count / n_sims * 100
            path = tp.get('path', {})
            story.append(P(f'路径 #{i+1} — 出现 {count}/{n_sims} 次 ({pct:.0f}%)', H3))
            path_rows = []
            for stage_key in ['R16', 'QF', 'SF', 'F']:
                stage_data = path.get(stage_key, {})
                if not stage_data:
                    continue
                winners_list = []
                for mid, winner in sorted(stage_data.items()):
                    winners_list.append(f'M{mid}: {cn(winner)}')
                path_rows.append([stages_label.get(stage_key, stage_key), ' | '.join(winners_list)])
            if path_rows:
                story.append(make_table(['轮次', '晋级球队'], path_rows, col_widths=[80, 400]))
            story.append(Spacer(1, 6))
        story.append(PageBreak())

    # ── Advancement ──
    story.append(P('各队晋级概率', H2))
    rounds = ['R16', 'QF', 'SF', 'F']
    adv_rows = []
    for team, rd in sorted(adv.items(), key=lambda x: -sum(x[1].values())):
        cname = cn(team)
        row = [cname]
        for r in rounds:
            row.append(f'{rd.get(r, 0):.0f}%')
        adv_rows.append(row)
    story.append(make_table(['球队'] + rounds, adv_rows,
                            col_widths=[80, 45, 45, 45, 45]))

    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(P('数据源: bracket_recursive.py | 模型: v5.5推理引擎 + 12层ELO栈 | 仅供娱乐参考', SMALL))

    doc.build(story)
    size = os.path.getsize(out)
    print(f'Generated: {out} ({size} bytes)')
    return out


if __name__ == '__main__':
    generate()
