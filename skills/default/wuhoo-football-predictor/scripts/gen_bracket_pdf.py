#!/usr/bin/env python3.11
"""
v5.10.1 淘汰赛推演PDF — 完整版
结构: 冠军概率 → 晋级路径 → QF/SF/F各轮详情 → 暗马预警 → 模型说明
"""
import json, os
from datetime import datetime

WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(WORKDIR, "data")
OUT = os.path.join(DATA, "reports", "single")
os.makedirs(OUT, exist_ok=True)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    pdfmetrics.registerFont(TTFont('CJK', os.path.expanduser('~/.fonts/NotoSansSC-VF.ttf')))
    F = 'CJK'
except: F = 'Helvetica'

B = HexColor('#1a5276'); R = HexColor('#c0392b'); G = HexColor('#666666')
LB = HexColor('#eef5fb'); DB = HexColor('#2980b9'); W = HexColor('#ffffff')
GR = HexColor('#27ae60'); OR = HexColor('#e67e22'); RD = HexColor('#c0392b')

def S(name, **kw):
    d = dict(fontName=F, leading=18, spaceAfter=4); d.update(kw)
    return ParagraphStyle(name, **d)

STY = {
    'title':  S('t', fontSize=18, textColor=B, spaceAfter=10, leading=24),
    'h2':     S('h2', fontSize=13, textColor=B, spaceAfter=6, spaceBefore=10, leading=20),
    'h3':     S('h3', fontSize=11, textColor=B, spaceAfter=4, spaceBefore=8, leading=18),
    'body':   S('body', fontSize=10, leading=15, spaceAfter=2),
    'small':  S('small', fontSize=8, textColor=G, leading=11, spaceAfter=1),
    'source': S('source', fontSize=7, textColor=G, leading=9, spaceAfter=2),
    'warn':   S('warn', fontSize=10, textColor=OR, leading=15, spaceAfter=3),
    'verdict':S('verdict', fontSize=11, textColor=GR, leading=18, spaceAfter=4),
}
P = lambda t, s='body': Paragraph(t, STY[s])

def T(headers, rows, widths=None):
    t = Table([headers] + rows, colWidths=widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DB), ('TEXTCOLOR', (0, 0), (-1, 0), W),
        ('FONTNAME', (0, 0), (-1, -1), F), ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, G),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [W, LB]),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t

TEAM_CN = {
    'France': '法国', 'Morocco': '摩洛哥', 'Spain': '西班牙', 'Belgium': '比利时',
    'Norway': '挪威', 'England': '英格兰', 'Argentina': '阿根廷', 'Switzerland': '瑞士',
    'Brazil': '巴西', 'Mexico': '墨西哥', 'Netherlands': '荷兰', 'Germany': '德国',
    'Portugal': '葡萄牙', 'Colombia': '哥伦比亚', 'United States': '美国', 'Egypt': '埃及',
}
cn = lambda n: TEAM_CN.get(n, n)

# ── Load data ──
br = json.load(open(os.path.join(DATA, "bracket_recursive_results.json")))
n_sims = br.get('n_sims', 5000)
champion = br.get('champion_probs', {})
advancement = br.get('advancement_probs', {})
match_details = br.get('match_details', {})

doc = SimpleDocTemplate(
    os.path.join(OUT, "bracket_recursive_v510.pdf"),
    pagesize=A4, leftMargin=16*mm, rightMargin=16*mm,
    topMargin=12*mm, bottomMargin=12*mm,
    title='WC2026 淘汰赛全量推演'
)
story = []

# ── TITLE ──
story.append(P("WC2026 淘汰赛全量推演报告", 'title'))
story.append(P(f"模型: v5.10 Ensemble · 模拟: {n_sims}次 · 生成: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 'small'))
story.append(Spacer(1, 6))

# ═══════════════════════════════════════
# SECTION 1: 冠军概率
# ═══════════════════════════════════════
story.append(P("冠军概率", 'h2'))
cp_sorted = sorted(champion.items(), key=lambda x: -x[1])
cp_rows = []
for i, (t, v) in enumerate(cp_sorted):
    bar = "█" * int(v / 2)
    cp_rows.append([str(i+1), cn(t), f"{v:.1f}%", bar])
story.append(T(['#','球队','夺冠概率',''], cp_rows, [30, 80, 70, 230]))

# Top 3 summary
if len(cp_sorted) >= 3:
    top3 = cp_sorted[:3]
    story.append(P(f"🏆 夺冠热门: {cn(top3[0][0])} {top3[0][1]:.1f}% > {cn(top3[1][0])} {top3[1][1]:.1f}% > {cn(top3[2][0])} {top3[2][1]:.1f}%", 'verdict'))

# ═══════════════════════════════════════
# SECTION 2: 晋级概率矩阵
# ═══════════════════════════════════════
story.append(Spacer(1, 6))
story.append(P("逐轮晋级概率", 'h2'))
qf_teams = ['France','Morocco','Spain','Belgium','Norway','England','Argentina','Switzerland']
adv_rows = []
for t in qf_teams:
    s = advancement.get(t, {})
    adv_rows.append([
        cn(t),
        f"{s.get('QF', 0):.1f}%",
        f"{s.get('SF', 0):.1f}%",
        f"{s.get('F', 0):.1f}%",
        f"{champion.get(t, 0):.1f}%"
    ])
story.append(T(['球队','QF→','SF→','决赛→','🏆夺冠'], adv_rows, [80, 60, 60, 60, 70]))
story.append(P("QF→=已确定晋级QF · SF=晋级半决赛概率 · 决赛=晋级决赛概率", 'source'))

# ═══════════════════════════════════════
# SECTION 3: 四分之一决赛详情
# ═══════════════════════════════════════
story.append(Spacer(1, 6))
story.append(P("四分之一决赛 预测详情", 'h2'))

for mid in sorted(match_details.keys()):
    m = match_details[mid]
    if m.get('round') != 'QF' or not m.get('team_a'): continue
    p = m.get('prediction', {})
    ta, tb = m['team_a'], m['team_b']
    wa = p.get('team_a_win_pct', 0) or p.get('team_a_win', 0)
    dp = p.get('draw_pct', 0) or p.get('draw', 0)
    wb = p.get('team_b_win_pct', 0) or p.get('team_b_win', 0)
    dt = m.get('date', '?')[:10]

    winner = cn(ta) if wa > wb else cn(tb) if wb > wa else '平局'
    story.append(P(f"M{mid} ({dt})  {cn(ta)} vs {cn(tb)}", 'h3'))
    story.append(P(f"  预测: {winner} ({cn(ta)} {wa:.0f}% / 平 {dp:.0f}% / {cn(tb)} {wb:.0f}%)", 'body'))

    sp = m.get('scoreline_probs', [])
    if sp:
        strs = [f"{s['score']}({s['prob_pct']:.0f}%)" for s in sp[:4]]
        story.append(P(f"  比分: {', '.join(strs)}", 'small'))

# ═══════════════════════════════════════
# SECTION 4: 暗马预警
# ═══════════════════════════════════════
story.append(Spacer(1, 6))
story.append(P("暗马预警", 'h2'))

# Find teams with low champion prob but high SF/F probability
warnings = []
for t, ch in champion.items():
    adv = advancement.get(t, {})
    sf_prob = adv.get('SF', 0) or 0
    if ch < 10 and sf_prob > 20:
        warnings.append((t, ch, sf_prob, 'SF'))

if warnings:
    for t, ch, pct, stage in sorted(warnings, key=lambda x: -x[1]):
        story.append(P(f"⚠ {cn(t)}: 夺冠仅 {ch:.1f}% 但晋级{stage}概率 {pct:.1f}% — 可能成为搅局者", 'warn'))
else:
    story.append(P('当前概率分布符合预期，无明显暗马信号', 'body'))

# ═══════════════════════════════════════
# SECTION 5: 方法论
# ═══════════════════════════════════════
story.append(Spacer(1, 8))
story.append(P("模型说明", 'h2'))
story.append(P("· v5.10 Ensemble = Poisson(50%) + Ordered Logit(50%)", 'body'))
story.append(P("· 淘汰赛λ校准: 0.78×抑制(94场历史: 场均2.1球)", 'body'))
story.append(P("· 规则引擎: rules_v3.json (27条规则, 8条KO专用, Phase-aware)", 'body'))
story.append(P("· ELO轨迹因子: 趋势+波动性双重评估", 'body'))
story.append(P("· 递归推演: 每场完整预测 → 胜者晋级 → 下一轮 Monte Carlo × {n_sims}", 'body'))
story.append(Spacer(1, 6))
story.append(P(f"生成时间: 2026-07-08 · 数据源: v5.10 + rules_v3 + ELO轨迹 + 有序Logit", 'source'))

doc.build(story)
size_kb = os.path.getsize(os.path.join(OUT, "bracket_recursive_v510.pdf")) / 1024
print(f"bracket_recursive_v510.pdf: {size_kb:.0f}KB")
