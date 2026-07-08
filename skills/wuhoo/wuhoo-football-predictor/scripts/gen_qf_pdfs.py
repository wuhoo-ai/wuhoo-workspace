#!/usr/bin/env python3.11
"""v5.10 QF单场PDF快速生成器"""
import json, os, sys

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

FONT_PATH = os.path.expanduser('~/.fonts/NotoSansSC-VF.ttf')
try:
    pdfmetrics.registerFont(TTFont('CJK', FONT_PATH))
    F = 'CJK'
except Exception:
    F = 'Helvetica'

B = HexColor('#1a5276')
R = HexColor('#c0392b')
G = HexColor('#666666')
LB = HexColor('#eef5fb')
DB = HexColor('#2980b9')
W = HexColor('#ffffff')

def style(name, **kw):
    d = dict(fontName=F, leading=18, spaceAfter=4)
    d.update(kw)
    return ParagraphStyle(name, **d)

S = {
    'title': style('t', fontSize=18, textColor=B, spaceAfter=10, leading=24),
    'h2': style('h2', fontSize=14, textColor=B, spaceAfter=6, spaceBefore=12, leading=20),
    'h3': style('h3', fontSize=12, textColor=B, spaceAfter=4, spaceBefore=10, leading=18),
    'body': style('body', fontSize=10, leading=16, spaceAfter=3),
    'small': style('small', fontSize=8, textColor=G, leading=12),
    'verdict': style('verdict', fontSize=12, textColor=R, spaceAfter=6, spaceBefore=8, leading=20),
}
P = lambda t, s='body': Paragraph(t, S[s])

def tbl(headers, rows, widths=None):
    all_rows = [headers] + rows
    t = Table(all_rows, colWidths=widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DB), ('TEXTCOLOR', (0, 0), (-1, 0), W),
        ('FONTNAME', (0, 0), (-1, -1), F), ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, G),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [W, LB]),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t

def cn(name):
    """Team name mapping"""
    m = {
        'France': '法国', 'Morocco': '摩洛哥', 'Spain': '西班牙', 'Belgium': '比利时',
        'Norway': '挪威', 'England': '英格兰', 'Argentina': '阿根廷', 'Switzerland': '瑞士',
        'Colombia': '哥伦比亚', 'Portugal': '葡萄牙', 'Egypt': '埃及', 'United States': '美国',
    }
    return m.get(name, name)

def generate_qf_match(team_a, team_b, prediction, outpath):
    doc = SimpleDocTemplate(outpath, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                             topMargin=15*mm, bottomMargin=15*mm)
    story = []
    ca, cb = cn(team_a), cn(team_b)
    ens = prediction['ensemble']
    poi = prediction['poisson']
    log = prediction['logit']
    xg = prediction['expected_goals']
    scores = prediction['top_scorelines']
    traj = prediction.get('trajectory', {})
    
    # Title
    story.append(P(f"{ca} vs {cb} — 世界杯2026 四分之一决赛预测", 'title'))
    story.append(P(f"{team_a} vs {team_b} · Quarter-finals · v5.10 Ensemble", 'small'))
    story.append(Spacer(1, 10))
    
    # Verdict
    wa, dr, wb = ens['team_a_win'], ens['draw'], ens['team_b_win']
    if wa > dr and wa > wb: v = f"预测: {ca} 胜 ({wa}%)"
    elif wb > wa and wb > dr: v = f"预测: {cb} 胜 ({wb}%)"
    else: v = f"预测: 平局 ({dr}%)"
    story.append(P(v, 'verdict'))
    
    # Win/Draw/Loss table
    story.append(P("胜平负概率", 'h2'))
    story.append(tbl(
        ['模型', f'{ca}胜', '平局', f'{cb}胜'],
        [
            ['Ensemble (v5.10)', f'{wa}%', f'{dr}%', f'{wb}%'],
            ['Poisson (原始)', f'{poi["team_a_win"]}%', f'{poi["draw"]}%', f'{poi["team_b_win"]}%'],
            ['有序Logit', f'{log["team_a_win"]}%', f'{log["draw"]}%', f'{log["team_b_win"]}%'],
        ],
        [120, 95, 80, 95]
    ))
    story.append(P("Ensemble = Poisson × 50% + 有序Logit × 50% (基于WC1998-2022淘汰赛历史校准)", 'small'))
    story.append(Spacer(1, 8))
    
    # Scoreline
    story.append(P("比分概率分布 (淘汰赛λ=0.78校准)", 'h2'))
    score_rows = []
    cumul = 0
    for s, p in scores[:5]:
        cumul += p
        score_rows.append([s, f'{p}%', f'{cumul:.1f}%'])
    story.append(tbl(['比分', '概率', '累计'], score_rows, [100, 90, 90]))
    story.append(P(f"校准后预期进球: {ca} {xg['a']} - {xg['b']} {cb}", 'small'))
    story.append(Spacer(1, 8))
    
    # Elo Trajectory
    story.append(P("Elo动态轨迹 (Layer 1.5)", 'h2'))
    traj_rows = []
    for t, tn in [(team_a, ca), (team_b, cb)]:
        tr = traj.get(t, {})
        traj_rows.append([tn, tr.get('classification', '?'), 
                          f"{tr.get('delta_avg', 0):+.1f}",
                          f"σ={tr.get('volatility', 0):.1f}",
                          f"±{tr.get('adjustment', 0):+d} ELO"])
    story.append(tbl(['球队', '轨迹分类', 'ΔElo均值', '波动性', '调整值'], traj_rows,
                      [100, 90, 80, 80, 80]))
    story.append(P("稳步上升=趋势强+波动低 → +15 ELO | 持续下滑=-15 | 波动大→不加分但降置信度", 'small'))
    story.append(Spacer(1, 8))
    
    # Methodology
    story.append(P("模型配置", 'h2'))
    story.append(P("v5.10 Ensemble = Poisson(50%) + Ordered Logit(50%)", 'body'))
    story.append(P("淘汰赛λ校准: 0.78×抑制(94场历史: 场均2.1球) + 平局增强(ΔELO<100时追加0.92×)", 'body'))
    story.append(P("规则引擎: rules_v3.json (27条规则, 8条KO专用, Phase-aware)", 'body'))
    story.append(P("新增: Elo轨迹因子 + 6条淘汰赛专用规则 + Interaction Constraints修复", 'body'))
    story.append(Spacer(1, 6))
    story.append(P(f"生成时间: 2026-07-08 · 模型版本: v5.10 · 数据源: ELO+FIFA+WC1998-2022淘汰赛统计", 'small'))
    
    doc.build(story)
    size_kb = os.path.getsize(outpath) / 1024
    print(f"  {os.path.basename(outpath)}: {size_kb:.0f}KB")

# Generate all 4 QF matches
d = json.load(open(os.path.join(DATA, "daily_predictions/2026-07-08_qf.json")))
for p in d['predictions']:
    ta, tb = p['team_a'], p['team_b']
    out = os.path.join(OUT, f"QF_{ta}_vs_{tb}.pdf")
    generate_qf_match(ta, tb, p, out)
print("\nAll QF PDFs generated.")
