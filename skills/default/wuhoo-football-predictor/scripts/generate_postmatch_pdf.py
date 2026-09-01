#!/usr/bin/env python3.11
"""Generate post-match report PDF for a given date."""
import json, os, sys
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, PageBreak)
from reportlab.lib.units import mm, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# Register Chinese font
try:
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    CN_FONT = 'STSong-Light'
except:
    try:
        pdfmetrics.registerFont(TTFont('NotoSansSC', '/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc'))
        CN_FONT = 'NotoSansSC'
    except:
        pdfmetrics.registerFont(TTFont('WenQuanYi', '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc'))
        CN_FONT = 'WenQuanYi'

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
REPORT_DIR = os.path.join(DATA_DIR, 'reports', 'postmatch')
os.makedirs(REPORT_DIR, exist_ok=True)

# Colors
DARK_BG = HexColor('#1a1a2e')
ACCENT = HexColor('#e94560')
GOLD = HexColor('#f5c518')
GREEN = HexColor('#00b894')
LIGHT_GRAY = HexColor('#f0f0f0')
MID_GRAY = HexColor('#666666')

def load_data(date_str):
    with open(os.path.join(DATA_DIR, 'wc2026_schedule.json')) as f:
        schedule = json.load(f)
    with open(os.path.join(DATA_DIR, 'wc2026_results.json')) as f:
        results = json.load(f)
    with open(os.path.join(DATA_DIR, 'elo_ratings.json')) as f:
        elo_data = json.load(f)
    with open(os.path.join(DATA_DIR, 'team_profiles.json')) as f:
        profiles = json.load(f)
    
    day_matches = [m for m in schedule['matches'] if m.get('date', '').startswith(date_str)]
    day_results = {r['match_id']: r for r in results['matches'] if r.get('date', '').startswith(date_str)}
    
    elos = elo_data.get('ratings', elo_data)
    if isinstance(elos, list):
        elo_map = {e['team']: e['elo'] for e in elos}
    else:
        elo_map = elos
    
    teams_prof = profiles.get('teams', profiles)
    def cn(en):
        if en in teams_prof and isinstance(teams_prof[en], dict):
            return teams_prof[en].get('name_cn', en)
        return en
    
    return day_matches, day_results, elo_map, cn

def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'CN_TITLE', fontName=CN_FONT, fontSize=18, leading=24,
        alignment=TA_CENTER, textColor=black, spaceAfter=6*mm
    ))
    styles.add(ParagraphStyle(
        'CN_SUBTITLE', fontName=CN_FONT, fontSize=11, leading=16,
        alignment=TA_CENTER, textColor=MID_GRAY, spaceAfter=10*mm
    ))
    styles.add(ParagraphStyle(
        'CN_H2', fontName=CN_FONT, fontSize=14, leading=20,
        textColor=DARK_BG, spaceBefore=8*mm, spaceAfter=4*mm
    ))
    styles.add(ParagraphStyle(
        'CN_BODY', fontName=CN_FONT, fontSize=10, leading=16,
        textColor=black, spaceAfter=3*mm
    ))
    styles.add(ParagraphStyle(
        'CN_SCORE', fontName=CN_FONT, fontSize=28, leading=34,
        alignment=TA_CENTER, textColor=DARK_BG
    ))
    styles.add(ParagraphStyle(
        'CN_TEAM_H', fontName=CN_FONT, fontSize=14, leading=18,
        alignment=TA_RIGHT, textColor=DARK_BG
    ))
    styles.add(ParagraphStyle(
        'CN_TEAM_A', fontName=CN_FONT, fontSize=14, leading=18,
        alignment=TA_LEFT, textColor=DARK_BG
    ))
    styles.add(ParagraphStyle(
        'CN_NOTE', fontName=CN_FONT, fontSize=9, leading=14,
        textColor=MID_GRAY, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        'CN_FOOTER', fontName=CN_FONT, fontSize=8, leading=10,
        textColor=MID_GRAY, alignment=TA_CENTER
    ))
    return styles

def generate(date_str='2026-07-02'):
    day_matches, day_results, elo_map, cn = load_data(date_str)
    styles = build_styles()
    
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    date_cn = date_obj.strftime('%Y年%m月%d日')
    
    output_path = os.path.join(REPORT_DIR, f'postmatch_{date_str}.pdf')
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           leftMargin=20*mm, rightMargin=20*mm,
                           topMargin=18*mm, bottomMargin=18*mm)
    
    story = []
    
    # Title
    story.append(Paragraph(f'2026世界杯 · 赛后简报', styles['CN_TITLE']))
    story.append(Paragraph(f'{date_cn}  |  R32 淘汰赛 第2比赛日', styles['CN_SUBTITLE']))
    story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY))
    story.append(Spacer(1, 6*mm))
    
    # Summary line
    completed = sum(1 for r in day_results.values() if r.get('status') == 'completed')
    total = len(day_matches)
    story.append(Paragraph(f'本日 {completed}/{total} 场比赛完赛', styles['CN_BODY']))
    story.append(Spacer(1, 4*mm))
    
    # Match cards
    for m in day_matches:
        mid = m['match_id']
        result = day_results.get(mid)
        if not result:
            continue
        
        team_a = m['team_a']
        team_b = m['team_b']
        cn_a = cn(team_a)
        cn_b = cn(team_b)
        score_a = result['score_a']
        score_b = result['score_b']
        notes = result.get('notes', '')
        stage = m.get('stage', 'R32')
        venue = m.get('venue', '')
        
        elo_a = elo_map.get(team_a, '?')
        elo_b = elo_map.get(team_b, '?')
        
        # Match card background
        card_data = [
            [Paragraph(f'<b>{cn_a}</b>', styles['CN_TEAM_H']),
             Paragraph(f'<b>{score_a} - {score_b}</b>', styles['CN_SCORE']),
             Paragraph(f'<b>{cn_b}</b>', styles['CN_TEAM_A'])],
            [Paragraph(f'ELO: {elo_a}', styles['CN_NOTE']),
             Paragraph(f'{stage} · {venue}', styles['CN_NOTE']),
             Paragraph(f'ELO: {elo_b}', styles['CN_NOTE'])],
        ]
        
        card_table = Table(card_data, colWidths=[55*mm, 60*mm, 55*mm])
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
            ('ALIGN', (2, 0), (2, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ]))
        
        story.append(card_table)
        story.append(Spacer(1, 2*mm))
        
        # Notes
        if notes:
            story.append(Paragraph(f'{notes}', styles['CN_NOTE']))
        story.append(Spacer(1, 5*mm))
    
    # Summary statistics
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('<b>数据摘要</b>', styles['CN_H2']))
    
    total_goals = sum(r['score_a'] + r['score_b'] for r in day_results.values())
    home_wins = sum(1 for r in day_results.values() if r['score_a'] > r['score_b'])
    away_wins = sum(1 for r in day_results.values() if r['score_a'] < r['score_b'])
    draws = sum(1 for r in day_results.values() if r['score_a'] == r['score_b'])
    
    stats = [
        f'总进球: {total_goals} 球 (场均 {total_goals/len(day_results):.1f})' if day_results else '',
        f'主队胜: {home_wins} | 平局: {draws} | 客队胜: {away_wins}',
    ]
    for s in stats:
        if s:
            story.append(Paragraph(s, styles['CN_BODY']))
    
    # ELO changes
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph('<b>ELO 变动</b>', styles['CN_H2']))
    
    elo_header = [Paragraph('<b>球队</b>', ParagraphStyle('h', fontName=CN_FONT, fontSize=9, alignment=TA_CENTER)),
                  Paragraph('<b>变动</b>', ParagraphStyle('h', fontName=CN_FONT, fontSize=9, alignment=TA_CENTER)),
                  Paragraph('<b>新ELO</b>', ParagraphStyle('h', fontName=CN_FONT, fontSize=9, alignment=TA_CENTER))]
    elo_rows = [elo_header]
    for m in day_matches:
        mid = m['match_id']
        result = day_results.get(mid)
        if not result:
            continue
        team_a = m['team_a']
        team_b = m['team_b']
        elo_a = elo_map.get(team_a, 0)
        elo_b = elo_map.get(team_b, 0)
        
        elo_rows.append([
            Paragraph(cn(team_a), ParagraphStyle('e', fontName=CN_FONT, fontSize=10, alignment=TA_CENTER)),
            Paragraph(f'+?', ParagraphStyle('e', fontName=CN_FONT, fontSize=10, alignment=TA_CENTER, textColor=GREEN)),
            Paragraph(str(elo_a), ParagraphStyle('e', fontName=CN_FONT, fontSize=10, alignment=TA_CENTER)),
        ])
        elo_rows.append([
            Paragraph(cn(team_b), ParagraphStyle('e', fontName=CN_FONT, fontSize=10, alignment=TA_CENTER)),
            Paragraph(f'?', ParagraphStyle('e', fontName=CN_FONT, fontSize=10, alignment=TA_CENTER)),
            Paragraph(str(elo_b), ParagraphStyle('e', fontName=CN_FONT, fontSize=10, alignment=TA_CENTER)),
        ])
    
    elo_table = Table(elo_rows, colWidths=[55*mm, 50*mm, 55*mm])
    elo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, MID_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(elo_table)
    
    # Tournament progress
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph('<b>赛事进度</b>', styles['CN_H2']))
    
    total_matches = len([m for m in json.load(open(os.path.join(DATA_DIR, 'wc2026_schedule.json')))['matches']])
    completed_total = len([r for r in json.load(open(os.path.join(DATA_DIR, 'wc2026_results.json')))['matches'] if r.get('status') == 'completed'])
    story.append(Paragraph(f'已完成: {completed_total}/{total_matches} 场 ({completed_total/total_matches*100:.1f}%)', styles['CN_BODY']))
    
    # Round of 16 qualifiers so far
    story.append(Paragraph('<b>已晋级R16球队 (6/16)</b>', styles['CN_H2']))
    r16_teams = ['France', 'Norway', 'Mexico', 'England', 'United States', 'Belgium']
    r16_cn = [cn(t) for t in r16_teams]
    story.append(Paragraph(' · '.join(r16_cn), styles['CN_BODY']))
    
    # Footer
    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")} CST | 数据来源: ESPN/BBC/FIFA', styles['CN_FOOTER']))
    
    doc.build(story)
    return output_path

if __name__ == '__main__':
    date_str = sys.argv[1] if len(sys.argv) > 1 else '2026-07-02'
    path = generate(date_str)
    print(f'PDF generated: {path}')
    print(f'Size: {os.path.getsize(path)} bytes')
