#!/usr/bin/env python3.11
"""v5.10 bracket推演PDF快速生成器"""
import json, os

WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(WORKDIR, "data")
OUT = os.path.join(DATA, "reports", "single")
os.makedirs(OUT, exist_ok=True)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    pdfmetrics.registerFont(TTFont('CJK', os.path.expanduser('~/.fonts/NotoSansSC-VF.ttf')))
    F = 'CJK'
except Exception:
    F = 'Helvetica'

B = HexColor('#1a5276')
R = HexColor('#c0392b')
G = HexColor('#666666')
LB = HexColor('#eef5fb')
DB = HexColor('#2980b9')
W = HexColor('#ffffff')
GREEN = HexColor('#27ae60')

def style(name, **kw):
    d = dict(fontName=F, leading=18, spaceAfter=4)
    d.update(kw)
    return ParagraphStyle(name, **d)
S = {
    'title': style('t', fontSize=18, textColor=B, spaceAfter=10, leading=24),
    'h2': style('h2', fontSize=14, textColor=B, spaceAfter=6, spaceBefore=12, leading=20),
    'h3': style('h3', fontSize=12, textColor=B, spaceAfter=4, spaceBefore=10, leading=18),
    'body': style('body', fontSize=10, leading=16),
    'small': style('small', fontSize=8, textColor=G, leading=12),
}
P = lambda t, s='body': Paragraph(t, S[s])

def tbl(headers, rows, widths=None):
    t = Table([headers] + rows, colWidths=widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DB), ('TEXTCOLOR', (0, 0), (-1, 0), W),
        ('FONTNAME', (0, 0), (-1, -1), F), ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, G),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [W, LB]),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t

cn = lambda n: {'France':'法国','Morocco':'摩洛哥','Spain':'西班牙','Belgium':'比利时',
    'Norway':'挪威','England':'英格兰','Argentina':'阿根廷','Switzerland':'瑞士',
    'Colombia':'哥伦比亚','Portugal':'葡萄牙','Egypt':'埃及','United States':'美国'}.get(n,n)

# Load bracket results
br = json.load(open(os.path.join(DATA, "bracket_recursive_results.json")))
n_sims = br['n_sims']

doc = SimpleDocTemplate(os.path.join(OUT, "bracket_recursive_v510.pdf"),
                         pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                         topMargin=15*mm, bottomMargin=15*mm)
story = []

story.append(P("WC2026 淘汰赛全量推演报告", 'title'))
story.append(P(f"模型: v5.10 Ensemble · 模拟次数: {n_sims} · 剩余比赛: {br.get('total_remaining_matches','?')}场", 'small'))
story.append(Spacer(1, 8))

# Champion
story.append(P("冠军概率", 'h2'))
cp = br.get('champion_probs', {})
cp_rows = []
for i, (t, v) in enumerate(sorted(cp.items(), key=lambda x: -x[1])):
    cp_rows.append([str(i+1), cn(t), f"{v:.1f}%", "█" * int(v)])
story.append(tbl(['#', '球队', '夺冠概率', ''], cp_rows, [30, 100, 80, 180]))
story.append(Spacer(1, 8))

# Advancement
story.append(P("晋级概率", 'h2'))
ap = br.get('advancement_probs', {})
qf_teams = ['France','Morocco','Spain','Belgium','Norway','England','Argentina','Switzerland']
adv_rows = []
for t in qf_teams:
    s = ap.get(t, {})
    adv_rows.append([cn(t), f"{s.get('QF',0):.1f}%", f"{s.get('SF',0):.1f}%", 
                     f"{s.get('F',0):.1f}%", f"{cp.get(t,0):.1f}%"])
story.append(tbl(['球队', 'QF晋级', 'SF晋级', '决赛', '夺冠'], adv_rows, [90, 65, 65, 65, 65]))
story.append(Spacer(1, 8))

# QF match predictions
story.append(P("四分之一决赛预测详情", 'h2'))
md = br.get('match_details', {})
for mid in sorted(md.keys()):
    m = md[mid]
    if m.get('round') != 'QF' or not m.get('team_a'):
        continue
    p = m.get('prediction', {})
    ta, tb = m['team_a'], m['team_b']
    wa, dp, wb = p.get('team_a_win_pct', 0), p.get('draw_pct', 0), p.get('team_b_win_pct', 0)
    dt = m.get('date', '?')[:10]
    story.append(P(f"M{mid} ({dt})  {cn(ta)} {wa:.0f}% vs Draw {dp:.0f}% vs {cn(tb)} {wb:.0f}%", 'body'))
    sp = m.get('scoreline_probs', [])
    if sp:
        strs = [f"{s['score']}({s['prob_pct']}%)" for s in sp[:3]]
        story.append(P(f"  比分: {', '.join(strs)}", 'small'))

story.append(Spacer(1, 6))
story.append(P(f"生成时间: 2026-07-08 · 数据源: v5.10 + rules_v3 + ELO轨迹 + 有序Logit", 'small'))

doc.build(story)
size_kb = os.path.getsize(os.path.join(OUT, "bracket_recursive_v510.pdf")) / 1024
print(f"bracket_recursive_v510.pdf: {size_kb:.0f}KB")
