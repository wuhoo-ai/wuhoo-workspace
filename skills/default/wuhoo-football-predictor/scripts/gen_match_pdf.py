#!/usr/bin/env python3.11
"""
v5.11 单场PDF生成器 — 完整版（小组赛+淘汰赛通用）
结构: 战术对比 → L1 ELO → L2 伤病 → L3 教练 → L4 场地/天气/旅途
       → L4a 天气因子 → L4b 赛程密度 → L4.5 热身赛 → L4.6 本届表现
       → L5 新闻情感 → 有效ELO汇总 → 3模型预测 → 比分分布 → ELO轨迹 → 推理引擎 → 判定

用法:
  python3.11 scripts/gen_match_pdf.py                  # 处理所有 daily JSON
  python3.11 scripts/gen_match_pdf.py --date 2026-07-15 # 指定日期
  python3.11 scripts/gen_match_pdf.py --round SF        # 按轮次筛选

Auto-enrich: 若 daily JSON 缺少 sub_models，自动调用 enrich_predictions 计算
"""
import json, os, sys, sqlite3, math, re
from datetime import datetime

WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(WORKDIR, "data")
OUT = os.path.join(DATA, "reports", "single")
os.makedirs(OUT, exist_ok=True)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, PageBreak)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Fonts ──
try:
    pdfmetrics.registerFont(TTFont('CJK', os.path.expanduser('~/.fonts/NotoSansSC-VF.ttf')))
    F = 'CJK'
except:
    F = 'Helvetica'

B = HexColor('#1a5276'); R = HexColor('#c0392b'); G = HexColor('#666666')
LB = HexColor('#eef5fb'); DB = HexColor('#2980b9'); W = HexColor('#ffffff')

def S(name, **kw):
    d = dict(fontName=F, leading=18, spaceAfter=4); d.update(kw)
    return ParagraphStyle(name, **d)

STY = {
    'title':  S('t', fontSize=18, textColor=B, spaceAfter=10, leading=24),
    'h2':     S('h2', fontSize=13, textColor=B, spaceAfter=6, spaceBefore=10, leading=20),
    'h3':     S('h3', fontSize=11, textColor=B, spaceAfter=4, spaceBefore=8, leading=18),
    'body':   S('body', fontSize=9, leading=14, spaceAfter=2),
    'small':  S('small', fontSize=8, textColor=G, leading=11, spaceAfter=1),
    'source': S('source', fontSize=7, textColor=G, leading=9, spaceAfter=2),
    'verdict': S('verdict', fontSize=12, textColor=R, spaceAfter=6, spaceBefore=6, leading=20),
    'center': S('center', fontSize=10, alignment=TA_CENTER, leading=16),
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

def HR():
    return HRFlowable(width="100%", thickness=1, color=B)

def ba(v):
    if isinstance(v, float): v = round(v, 1)
    if v == 0: return '0'
    return f'+{v}' if v > 0 else str(v)

# ── Data loaders ──
TEAM_CN = {
    'France': '法国', 'Morocco': '摩洛哥', 'Spain': '西班牙', 'Belgium': '比利时',
    'Norway': '挪威', 'England': '英格兰', 'Argentina': '阿根廷', 'Switzerland': '瑞士',
    'Colombia': '哥伦比亚', 'Portugal': '葡萄牙', 'Egypt': '埃及', 'United States': '美国',
    'Brazil': '巴西', 'Mexico': '墨西哥', 'Netherlands': '荷兰', 'Germany': '德国',
    'Croatia': '克罗地亚', 'Japan': '日本', 'Senegal': '塞内加尔', 'Uruguay': '乌拉圭',
    'South Korea': '韩国', 'Australia': '澳大利亚', 'Iran': '伊朗', 'Serbia': '塞尔维亚',
    'Canada': '加拿大', 'Paraguay': '巴拉圭', 'Austria': '奥地利', 'Algeria': '阿尔及利亚',
    'Cape Verde': '佛得角', 'Sweden': '瑞典', 'DR Congo': '民主刚果', 'Ivory Coast': '科特迪瓦',
    'Ghana': '加纳', 'Panama': '巴拿马', 'Saudi Arabia': '沙特阿拉伯', 'Bosnia and Herzegovina': '波黑',
    'Qatar': '卡塔尔', 'New Zealand': '新西兰', 'Iraq': '伊拉克', 'Haiti': '海地',
    'Scotland': '苏格兰', 'Jordan': '约旦',
}
def cn(name): return TEAM_CN.get(name, name)

# Round label mapping
ROUND_LABELS = {
    'GS1': '小组赛第1轮', 'GS2': '小组赛第2轮', 'GS3': '小组赛第3轮',
    'R32': '三十二强赛', 'R16': '十六强赛', 'QF': '四分之一决赛',
    'SF': '半决赛', 'F': '决赛', '3rd': '季军赛',
}
ROUND_SHORT = {
    'GS1': 'GS1', 'GS2': 'GS2', 'GS3': 'GS3',
    'R32': 'R32', 'R16': 'R16', 'QF': 'QF',
    'SF': 'SF', 'F': 'Final', '3rd': '3rd',
}

# ISO 3-letter country codes for filename
ISO3 = {
    'France': 'FRA', 'Spain': 'ESP', 'England': 'ENG', 'Argentina': 'ARG',
    'Germany': 'GER', 'Brazil': 'BRA', 'Netherlands': 'NED', 'Portugal': 'POR',
    'Belgium': 'BEL', 'Morocco': 'MAR', 'Norway': 'NOR', 'Switzerland': 'SUI',
    'Croatia': 'CRO', 'Japan': 'JPN', 'Senegal': 'SEN', 'Uruguay': 'URU',
    'South Korea': 'KOR', 'Australia': 'AUS', 'Iran': 'IRN', 'Serbia': 'SRB',
    'Canada': 'CAN', 'Paraguay': 'PAR', 'Austria': 'AUT', 'Algeria': 'ALG',
    'Cape Verde': 'CPV', 'Sweden': 'SWE', 'DR Congo': 'COD', 'Ivory Coast': 'CIV',
    'Ghana': 'GHA', 'Panama': 'PAN', 'Saudi Arabia': 'KSA', 'Bosnia and Herzegovina': 'BIH',
    'Qatar': 'QAT', 'New Zealand': 'NZL', 'Iraq': 'IRQ', 'Haiti': 'HAI',
    'Scotland': 'SCO', 'Jordan': 'JOR', 'Egypt': 'EGY', 'United States': 'USA',
    'Mexico': 'MEX', 'Colombia': 'COL', 'Ecuador': 'ECU',
}

# Auto-enrich support
try:
    from enrich_predictions import enrich_match as _enrich_match
    _HAS_ENRICH = True
except ImportError:
    _HAS_ENRICH = False

# Load tactics
TACTICS = {}
tp = os.path.join(DATA, 'team_tactics.json')
if os.path.exists(tp): TACTICS = json.load(open(tp))

# Load injuries
INJURIES = {}
ip = os.path.join(DATA, 'injuries.json')
if os.path.exists(ip): INJURIES = json.load(open(ip)).get('injuries', {})

# Load team profiles (coach/stability/chemistry)
TEAM_PROFILES = {}
pp = os.path.join(DATA, 'team_profiles.json')
if os.path.exists(pp):
    raw = json.load(open(pp))
    TEAM_PROFILES = raw.get('teams', raw)

# Load venues
VENUES = {}
vp = os.path.join(DATA, 'venues.json')
if os.path.exists(vp):
    raw = json.load(open(vp))
    VENUES = raw.get('venues', {})

# Load weather
WEATHER = {}
wp = os.path.join(DATA, 'match_weather.json')
if os.path.exists(wp): WEATHER = json.load(open(wp))

# Load tournament results
RESULTS = []
rp = os.path.join(DATA, 'wc2026_results.json')
if os.path.exists(rp): RESULTS = json.load(open(rp)).get('matches', [])

# Load ELO
ELO = {}
ep = os.path.join(DATA, 'elo_ratings.json')
if os.path.exists(ep): ELO = json.load(open(ep))

# Load knockout schedule
KO_SCHEDULE = {}
kp = os.path.join(DATA, 'knockout_schedule.json')
if os.path.exists(kp):
    for m in json.load(open(kp)).get('matches', []):
        KO_SCHEDULE[m['match_id']] = m

# Load daily layers for enrichment
DAILY_LAYERS = {}  # (team_a, team_b) → audit
daily_dir = os.path.join(DATA, 'daily_predictions')
import glob as _glob
for fpath in sorted(_glob.glob(os.path.join(daily_dir, '2026-07-*.json')), reverse=True):
    try:
        dd = json.load(open(fpath))
    except: continue
    for m in dd.get('matches', []):
        audit = m.get('audit', {})
        ta, tb = audit.get('team_a', ''), audit.get('team_b', '')
        if not ta or not tb: continue
        key = (ta, tb) if ta < tb else (tb, ta)
        if key not in DAILY_LAYERS:
            DAILY_LAYERS[key] = audit

def get_tournament_matches(team):
    matches = []
    for m in RESULTS:
        if m.get('team_a') == team or m.get('team_b') == team:
            opp = m['team_b'] if m['team_a'] == team else m['team_a']
            sa, sb = m.get('score_a', '?'), m.get('score_b', '?')
            if m['team_a'] == team:
                outcome = 'W' if sa > sb else ('D' if sa == sb else 'L')
                score_str = f"{sa}-{sb}"
            else:
                outcome = 'W' if sb > sa else ('D' if sa == sb else 'L')
                score_str = f"{sb}-{sa}"
            matches.append({
                'date': (m.get('date_beijing') or m.get('date', '?'))[:10],
                'round': m.get('round', '?'),
                'opponent': opp,
                'score': score_str,
                'outcome': outcome,
                'penalties': m.get('penalties', ''),
                'aet': m.get('aet', False),
            })
    return matches

def get_weather_for_match(team_a, team_b, venue_name=''):
    fc = WEATHER.get('forecasts', {})
    if isinstance(fc, dict):
        for mid, f in fc.items():
            if isinstance(f, dict):
                if venue_name and f.get('venue') == venue_name:
                    return f
                if (f.get('team_a') == team_a and f.get('team_b') == team_b) or \
                   (f.get('team_a') == team_b and f.get('team_b') == team_a):
                    return f
    return {}

def get_rss_articles(team_a, team_b):
    db_path = '/home/admin/wuhoo-workspace/skills/default/wuhoo-news-rss/data/news.db'
    EXCLUDED = {'SoccerNews', 'Football Rankings'}
    try:
        db = sqlite3.connect(db_path)
        results = []
        for team in [team_a, team_b]:
            rows = db.execute(
                f"SELECT title, feed_name, summary FROM articles "
                f"WHERE category='足球' AND feed_name NOT IN ({','.join('?'*len(EXCLUDED))}) "
                f"AND (title LIKE ? OR summary LIKE ?) "
                f"AND pub_date > datetime('now', '-5 days') "
                f"ORDER BY fetched_at DESC LIMIT 5",
                (*EXCLUDED, f'%{team}%', f'%{team}%')
            ).fetchall()
            for r in rows:
                title = nohtml(r[0]); feed = (r[1] or '')[:20]
                summary = nohtml(r[2] or '')
                results.append({'title': title, 'feed': feed, 'summary': summary[:100]})
        db.close()
        seen = set(); unique = []
        for r in results:
            if r['title'] not in seen: seen.add(r['title']); unique.append(r)
        return unique[:6]
    except: return []

def nohtml(t): return re.sub(r'<[^>]+>', '', t or '').strip()

# ── Main generator ──
def generate_match_report(team_a, team_b, prediction, outpath, round_label='', subjective=None):
    rnd_label = ROUND_LABELS.get(round_label, round_label or '淘汰赛')
    rnd_short = ROUND_SHORT.get(round_label, round_label or '')
    doc = SimpleDocTemplate(outpath, pagesize=A4, leftMargin=12*mm, rightMargin=12*mm,
                             topMargin=10*mm, bottomMargin=10*mm,
                             title=f'WC2026 {rnd_short} {cn(team_a)} vs {cn(team_b)}')
    story = []
    ca, cb = cn(team_a), cn(team_b)

    # Parse prediction data
    for k in ['ensemble','poisson','logit','expected_goals','trajectory']:
        v = prediction.get(k)
        if isinstance(v, str): prediction[k] = eval(v)
    ens = prediction['ensemble']; poi = prediction['poisson']; log = prediction['logit']
    xg = prediction['expected_goals']; traj = prediction.get('trajectory', {})

    # ── Load daily layers for enrichment ──
    daily_key = (team_a, team_b) if team_a < team_b else (team_b, team_a)
    daily = DAILY_LAYERS.get(daily_key, {})
    layers = daily.get('layers', {})
    reasoning_path = daily.get('reasoning_path', '')
    is_engine = daily.get('inference_engine', False)

    # ── TITLE ──
    story.append(P(f"{ca} vs {cb} — 世界杯2026 {rnd_label}预测", 'title'))
    story.append(P(f"{team_a} vs {team_b} · {rnd_label} · v5.11 完整分析", 'small'))

    # Find match details
    match_info = None
    for mid, m in KO_SCHEDULE.items():
        if m.get('team_a') == team_a and m.get('team_b') == team_b:
            match_info = m; break
        if m.get('team_b') == team_a and m.get('team_a') == team_b:
            match_info = m; break
    if not match_info:
        try:
            br = json.load(open(os.path.join(DATA, 'bracket_recursive_results.json')))
            for mid, m in br.get('match_details', {}).items():
                if m.get('team_a') == team_a and m.get('team_b') == team_b:
                    match_info = {'venue': m.get('venue', '?'), 'date': m.get('date', '?'), 'round': m.get('round', round_label or '?')}
                    break
                if m.get('team_b') == team_a and m.get('team_a') == team_b:
                    match_info = {'venue': m.get('venue', '?'), 'date': m.get('date', '?'), 'round': m.get('round', round_label or '?')}
                    break
        except: pass

    if match_info:
        story.append(P(f"日期: {match_info.get('date','?')} · 场地: {match_info.get('venue','?')} · {match_info.get('round','?')}", 'small'))

    # Verdict line
    wa, dr, wb = ens['team_a_win'], ens['draw'], ens['team_b_win']
    if wa > dr and wa > wb: v = f"综合预测: {ca} 胜 ({wa}%)"
    elif wb > wa and wb > dr: v = f"综合预测: {cb} 胜 ({wb}%)"
    else: v = f"综合预测: 平局 ({dr}%)"
    story.append(Spacer(1, 4))
    story.append(P(v, 'verdict'))

    # ═══════════════════════════════════════
    # SECTION 1: 球队风格战术对比
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[风格战术] 球队对比 — 数据源: team_tactics.json', 'h2'))

    for tc, tac in [(ca, TACTICS.get(team_a, {})), (cb, TACTICS.get(team_b, {}))]:
        if not tac: continue
        fm = tac.get('formation', ''); co = tac.get('coach', '')
        strengths = tac.get('strengths', []); weaknesses = tac.get('weaknesses', [])
        parts = []
        if fm or co: parts.append(f"阵型: {fm}  |  主帅: {co}")
        if tac.get('style_summary'): parts.append(tac['style_summary'][:100])
        if strengths: parts.append(f"优势: {'; '.join(strengths[:2])}")
        if weaknesses: parts.append(f"短板: {'; '.join(weaknesses[:2])}")
        if tac.get('key_players'): parts.append(f"核心: {', '.join(tac['key_players'][:3])}")
        story.append(P(f'【{tc}】 ' + ' | '.join(parts), 'body'))

    # ═══════════════════════════════════════
    # [L1] ELO 基础实力
    # ═══════════════════════════════════════
    l1 = layers.get('1_elo_base', {})
    story.append(HR())
    story.append(P('[L1] ELO 基础实力 — 数据源: elo_ratings.json', 'h2'))
    elo_a = ELO.get(team_a, 1500); elo_b = ELO.get(team_b, 1500)
    diff = elo_a - elo_b
    prof_a = TEAM_PROFILES.get(team_a, {}); prof_b = TEAM_PROFILES.get(team_b, {})
    story.append(P(f"{ca} FIFA#{prof_a.get('fifa_rank_est','?')} ELO={elo_a} · "
                   f"{cb} FIFA#{prof_b.get('fifa_rank_est','?')} ELO={elo_b} · "
                   f"基础差 {diff:+d}, 胜率 {l1.get('base_win_prob', '?')}%", 'body'))

    # ELO trajectory
    if traj:
        story.append(P('[ELO动态轨迹] Layer 1.5', 'h3'))
        traj_rows = []
        for te, tc in [(team_a, ca), (team_b, cb)]:
            tr = traj.get(te, {})
            traj_rows.append([tc,
                tr.get('classification', '?'),
                f"{tr.get('delta_avg', 0):+.1f}",
                f"σ={tr.get('volatility', 0):.1f}",
                f"±{tr.get('adjustment', 0):+d} ELO"])
        story.append(T(['球队','轨迹分类','ΔElo均值','波动性','调整值'], traj_rows,
                        [80, 90, 70, 70, 70]))
        story.append(P("稳步上升=趋势强+波动低→+15 | 持续下滑→-15 | 波动大→不加分", 'source'))

    # ═══════════════════════════════════════
    # [L2] 伤病报告
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[L2] 伤病影响 — 数据源: injuries.json (ESPN/BBC/Fox Sports)', 'h2'))
    has_inj = False
    for te, tc in [(team_a, ca), (team_b, cb)]:
        if te in INJURIES:
            players = INJURIES[te].get('players', [])
            if players:
                story.append(P(f'{tc} ({len(players)}人伤停):', 'body'))
                for p in players:
                    name = p.get('name', '?'); status = p.get('status', '?')
                    injury = p.get('injury', '?'); pen = p.get('elo_penalty', 0)
                    story.append(P(f"  · {name} [{status}] {injury[:60]} → ELO {pen:+d}", 'small'))
                total = INJURIES[te].get('total_penalty', 0)
                story.append(P(f"  合计伤病扣分: {total:+d} ELO", 'source'))
                has_inj = True
    if not has_inj: story.append(P('两队均无重大伤病报告', 'body'))

    # ── L2.5 Motivation (QMF) ──
    l25 = layers.get('2.5_motivation', {})
    if l25.get('team_a_classification') or l25.get('team_b_classification'):
        story.append(P('[L2.5] 出线动机 (QMF) — 数据源: compute_motivation.py', 'h3'))
        cls_a = l25.get('team_a_classification', '-'); adj_a = l25.get('team_a_adjustment', 0)
        cls_b = l25.get('team_b_classification', '-'); adj_b = l25.get('team_b_adjustment', 0)
        story.append(P(f"{ca}: {cls_a} (ELO {adj_a:+d})  |  {cb}: {cls_b} (ELO {adj_b:+d})", 'body'))

    # ═══════════════════════════════════════
    # [L3] 教练/阵容 — 文字版（避免CJK表格重叠）
    # ═══════════════════════════════════════
    l3 = layers.get('3_coach_meta', {})
    story.append(HR())
    story.append(P('[L3] 教练/阵容 — 数据源: team_tactics.json + team_profiles.json', 'h2'))
    for te, tc in [(team_a, ca), (team_b, cb)]:
        prof = TEAM_PROFILES.get(te, {})
        tac = TACTICS.get(te, {})
        fifa = prof.get('fifa_rank_est', '?')
        coach = tac.get('coach', '') or prof.get('coach', '') or prof.get('coach_info', '')
        if not coach: coach = '?'
        fm = tac.get('formation', '') or '?'
        wc_best = prof.get('wc_best', '?')
        style = prof.get('style_category', '') or prof.get('style', '') or '?'
        adj = int(l3.get('team_a_adjustment' if te == team_a else 'team_b_adjustment', 0))
        story.append(P(
            f'{tc} | FIFA #{fifa} | 主帅: {coach} | 阵型: {fm} | 世界杯最佳: {wc_best} | 风格: {style} | ELO: {adj:+d}',
            'body'))

    # ═══════════════════════════════════════
    # [L4] 场地/天气/旅途疲劳
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[L4] 场地/天气/赛程 — 数据源: venues.json + Open-Meteo', 'h2'))

    venue_name = match_info.get('venue', '?') if match_info else '?'
    venue_data = VENUES.get(venue_name, {})
    city = venue_data.get('city', '?'); altitude = venue_data.get('altitude_m', 0)
    indoor = venue_data.get('indoor', False)
    story.append(P(f"场地: {venue_name} ({city}) · 海拔 {altitude}m · {'室内' if indoor else '室外'}", 'body'))

    # Weather
    wx = get_weather_for_match(team_a, team_b, venue_name)
    if wx and wx.get('temp_c') is not None and wx.get('temp_c') != '?':
        cond = wx.get('condition', wx.get('cond', '?')); temp = wx.get('temp_c', wx.get('temp_c_avg', '?'))
        prec = wx.get('precip_mm', wx.get('precip', 0)); wind = wx.get('wind_kph', 0)
        wx_parts = [f"天气: {cond}", f"气温: {temp}°C"]
        if not indoor:
            if prec > 0: wx_parts.append(f"降水量: {prec}mm")
            if wind > 0: wx_parts.append(f"风力: {wind}km/h")
        story.append(P(' · '.join(wx_parts), 'body'))
    else:
        days_to = 0
        try:
            from datetime import timedelta
            md = match_info.get('date', '')[:10] if match_info else ''
            if md:
                dt = datetime.strptime(md, '%Y-%m-%d')
                days_to = (dt - datetime.now()).days
        except: pass
        note = f'赛前{days_to}天更新' if days_to > 0 else '赛前更新'
        story.append(P(f'天气数据: {note} (Open-Meteo预报范围外)', 'body'))

    # ── L4a Weather Factor ──
    l4a = layers.get('4a_weather', {})
    if l4a:
        story.append(P('[L4a] 天气因子 — 数据源: fetch_weather.py (Open-Meteo API)', 'h3'))
        wd = l4a.get('weather_details', {})
        adj_a = l4a.get('team_a_adj', 0); adj_b = l4a.get('team_b_adj', 0)
        story.append(P(f"ELO调整: {ca} {ba(adj_a)} · {cb} {ba(adj_b)}", 'body'))

    # ── L4b Schedule Density ──
    l4b = layers.get('4b_schedule_density', {})
    if l4b:
        story.append(P('[L4b] 赛程密度 — 数据源: 赛程表 + Haversine距离', 'h3'))
        sd_a = l4b.get('team_a_details', {}); sd_b = l4b.get('team_b_details', {})
        adj_a = l4b.get('team_a_adj', 0); adj_b = l4b.get('team_b_adj', 0)
        story.append(P(f"ELO调整: {ca} {ba(adj_a)} · {cb} {ba(adj_b)} | "
                       f"休息: 各{sd_a.get('rest_days','?')}天 | "
                       f"旅途: {ca} {sd_a.get('distance_km',0):.0f}km / {cb} {sd_b.get('distance_km',0):.0f}km", 'body'))

    # Rest days: last match → this upcoming match
    match_date = None
    if match_info:
        try:
            md = match_info.get('date', '')[:10]
            match_date = datetime.strptime(md, '%Y-%m-%d') if md else None
        except: pass

    for te, tc in [(team_a, ca), (team_b, cb)]:
        matches = get_tournament_matches(te)
        if not matches: continue
        last = matches[-1]
        if match_date:
            try:
                ld = datetime.strptime(last['date'][:10], '%Y-%m-%d')
                rest = (match_date - ld).days
                story.append(P(f"{tc}: 上一场 {last['date'][:10]} vs {cn(last['opponent'])} {last['score']} -> 本场间隔 {rest} 天", 'source'))
                continue
            except: pass
        story.append(P(f"{tc}: 上一场 {last['date'][:10]} vs {cn(last['opponent'])} {last['score']}", 'source'))

    # ── L4.5 Friendly Form ──
    l45 = layers.get('4.5_friendly_form', {})
    if l45:
        story.append(P('[L4.5] 热身赛状态 — 数据源: friendly_form_adjustments.json', 'h3'))
        story.append(P(f"{ca}: {ba(l45.get('team_a_adj',0))} ELO · {cb}: {ba(l45.get('team_b_adj',0))} ELO", 'body'))

    # ═══════════════════════════════════════
    # [L4.6] 本届比赛表现
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[L4.6] 本届比赛表现 — 数据源: wc2026_results.json', 'h2'))

    for te, tc in [(team_a, ca), (team_b, cb)]:
        matches = get_tournament_matches(te)
        if not matches: continue
        wins = sum(1 for m in matches if m['outcome'] == 'W')
        draws = sum(1 for m in matches if m['outcome'] == 'D')
        losses = sum(1 for m in matches if m['outcome'] == 'L')
        gf = sum(int(m['score'].split('-')[0]) for m in matches)
        ga = sum(int(m['score'].split('-')[1]) for m in matches)
        # Build compact match summary line
        match_parts = []
        for m in matches:
            icon = {'W': '✓', 'D': '=', 'L': '✗'}.get(m['outcome'], '?')
            match_parts.append(f"{m['date']} {icon} vs {cn(m['opponent'])} {m['score']}")
        story.append(P(f'{tc}: {wins}胜{draws}平{losses}负 · 进{gf}失{ga} · 净胜{gf-ga:+d}', 'body'))
        story.append(P('  ' + '  |  '.join(match_parts), 'small'))
        story.append(Spacer(1, 3))

    # ═══════════════════════════════════════
    # [L5] 新闻/情感分析
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[L5] 新闻情感 — 数据源: news.db (RSSHub+BBC+懂球帝+卫报+天空体育)', 'h2'))
    articles = get_rss_articles(team_a, team_b)
    if articles:
        story.append(P(f'近5日相关报道 {len(articles)} 篇:', 'body'))
        for art in articles[:3]:
            title = nohtml(art.get('title', '')); feed = art.get('feed', '')
            story.append(P(f"[{feed}] {title[:80]}", 'source'))
    else:
        story.append(P('(近5日无相关报道)', 'source'))

    # ═══════════════════════════════════════
    # 有效ELO汇总
    # ═══════════════════════════════════════
    if daily.get('effective_elo'):
        eff = daily['effective_elo']
        story.append(HR())
        story.append(P('有效ELO汇总', 'h2'))
        ea = eff['team_a']; eb = eff['team_b']
        rows = [
            ['ELO原始', str(ea['base']), str(eb['base'])],
            ['各层累计调整', f'{ba(ea["adjustments"])}', f'{ba(eb["adjustments"])}'],
        ]
        engine_da = eff.get('engine_delta_a', 0); engine_db = eff.get('engine_delta_b', 0)
        if engine_da or engine_db:
            rows.append(['推理引擎增量', f'{engine_da:+d}', f'{engine_db:+d}'])
        rows.append(['有效ELO', str(ea['effective']), str(eb['effective'])])
        story.append(T(['', ca, cb], rows, [100, 80, 80]))
        story.append(P(f'有效ELO差: {eff["diff"]:+d}', 'body'))

    # ═══════════════════════════════════════
    # SECTION 8: 预测模型 (3 models)
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[预测模型] 胜平负概率 · 3模型对比', 'h2'))
    story.append(T(
        ['模型', f'{ca}胜', '平局', f'{cb}胜'],
        [
            ['Ensemble (v5.10)', f'{wa}%', f'{dr}%', f'{wb}%'],
            ['Poisson (原始)', f'{poi["team_a_win"]}%', f'{poi["draw"]}%', f'{poi["team_b_win"]}%'],
            ['有序Logit', f'{log["team_a_win"]}%', f'{log["draw"]}%', f'{log["team_b_win"]}%'],
        ],
        [130, 95, 80, 95]
    ))
    story.append(P("Ensemble = Poisson × 50% + 有序Logit × 50% (WC1998-2022 94场淘汰赛历史校准)", 'source'))
    story.append(P(f"校准后预期进球: {ca} {xg['a']} - {xg['b']} {cb}", 'body'))

    # ═══════════════════════════════════════
    # SECTION 9: 比分概率分布 (Top 5)
    # ═══════════════════════════════════════
    story.append(Spacer(1, 6))
    story.append(P('[比分概率分布] Top 5 · 90分钟·淘汰赛λ=0.78校准', 'h2'))

    la, lb = float(xg['a']), float(xg['b'])
    all_scores = []
    for ga in range(0, 6):
        for gb in range(0, 5):
            pa = (la**ga * math.exp(-la) / math.factorial(ga))
            pb = (lb**gb * math.exp(-lb) / math.factorial(gb))
            prob = pa * pb * 100
            all_scores.append((f'{ga}-{gb}', prob))

    all_scores.sort(key=lambda x: -x[1])
    score_rows = []; cumul = 0
    for s, p in all_scores[:5]:
        cumul += p
        ga, gb = s.split('-')
        result = f'{ca}胜' if ga > gb else (f'{cb}胜' if gb > ga else '平局')
        score_rows.append([s, f'{p:.1f}%', f'{cumul:.1f}%', result])
    story.append(T(['比分','概率','累计',''], score_rows, [80, 80, 80, 80]))

    # ═══════════════════════════════════════
    # v5.5 推理引擎路径
    # ═══════════════════════════════════════
    if is_engine and reasoning_path:
        story.append(HR())
        story.append(P('v5.5 推理引擎路径', 'h2'))
        for line in reasoning_path.split('\n')[:25]:
            stripped = line.strip()
            if not stripped: continue
            clean = stripped.replace('\U0001f4cb', '[规则] ').replace('\u26a1', '[修正] ').replace('\u2514', '  ->').replace('\u251c', '  |')
            is_header = not (clean.startswith('  ') or clean.startswith('[规则]') or clean.startswith('[修正]'))
            story.append(P(clean, 'body' if is_header else 'small'))

    # ═══════════════════════════════════════
    # SECTION 11: 主观判断 (第二意见 — optional)
    # ═══════════════════════════════════════
    if subjective:
        story.append(HR())
        story.append(P('[主观判断] 独立 web 分析 — 数据源: web_fetch（不依赖管线数据）', 'h2'))

        sub_v = subjective.get('verdict', '')
        sub_conf = subjective.get('confidence', 'medium')
        sub_score = subjective.get('predicted_score', '')
        sub_factors = subjective.get('key_factors', [])
        sub_sources = subjective.get('sources', [])
        sub_div = subjective.get('divergence_from_model', {})

        verdict_cn = {'team_a_win': f'{ca} 胜', 'draw': '平局', 'team_b_win': f'{cb} 胜'}
        conf_cn = {'high': '高', 'medium': '中', 'low': '低'}
        conf_color = {'high': R, 'medium': HexColor('#e67e22'), 'low': G}

        # Subjective verdict
        story.append(P(f"判定: {verdict_cn.get(sub_v, sub_v)} ({conf_cn.get(sub_conf, sub_conf)}置信度)",
                       'verdict'))
        if sub_score:
            story.append(P(f"预期比分: {sub_score}", 'body'))

        # Key factors
        if sub_factors:
            story.append(P('关键因素:', 'h3'))
            for f in sub_factors:
                story.append(P(f'  · {f}', 'body'))

        # Divergence box
        if sub_div and sub_div.get('divergence', 'none') != 'none':
            div_model = sub_div.get('model_says', '?')
            div_subj = sub_div.get('subjective_says', '?')
            YELLOW_BG = HexColor('#fff8e1')
            YELLOW_BD = HexColor('#ffc107')
            YELLOW_TX = HexColor('#856404')
            div_table = Table(
                [['⚠ 模型 vs 主观判断分歧'],
                 [f'模型: {div_model}'],
                 [f'主观: {div_subj}'],
                 [f'分歧度: {sub_div.get("divergence", "?")}']],
                colWidths=[330])
            div_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), YELLOW_BG),
                ('BACKGROUND', (0, 1), (-1, -1), W),
                ('TEXTCOLOR', (0, 0), (-1, -1), YELLOW_TX),
                ('FONTNAME', (0, 0), (-1, -1), F),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOX', (0, 0), (-1, -1), 1, YELLOW_BD),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(Spacer(1, 4))
            story.append(div_table)
            story.append(Spacer(1, 4))

        # Reasoning
        sub_reasoning = subjective.get('reasoning', '')
        if sub_reasoning:
            story.append(P(f'分析: {sub_reasoning}', 'body'))

        # Sources
        if sub_sources:
            story.append(P('分析依据:', 'h3'))
            for s in sub_sources[:5]:
                site = s.get('site', '?')
                title = s.get('title', '')[:80]
                story.append(P(f"[{site}] {title}", 'source'))

        src_names = ', '.join(s.get('site', '?') for s in sub_sources[:5])
        story.append(P(f'数据源: {src_names} | 分析时间: {subjective.get("generated", "?")}', 'source'))

    # ═══════════════════════════════════════
    # SECTION 10: 判定
    # ═══════════════════════════════════════
    story.append(Spacer(1, 8))
    story.append(HR())
    story.append(P(f'判定: {v}', 'verdict'))
    conf = '高' if max(wa, dr, wb) >= 70 else ('中' if max(wa, dr, wb) >= 55 else '低')
    story.append(P(f'置信度: {conf} · 数据保鲜: {datetime.now().strftime("%Y-%m-%d %H:%M")} · 模型: v5.11', 'source'))
    story.append(P('数据源: ELO + FIFA + team_tactics.json + injuries.json + Open-Meteo + RSSHub + WC1998-2022淘汰赛统计', 'source'))

    doc.build(story)
    size_kb = os.path.getsize(outpath) / 1024
    print(f"  {os.path.basename(outpath)}: {size_kb:.0f}KB")
    return outpath

# ── Main ──
if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='v5.11 单场PDF生成器')
    ap.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    ap.add_argument('--round', type=str, help='按轮次筛选 (QF/SF/F/R16/R32)')
    ap.add_argument('--no-enrich', action='store_true', help='跳过 auto-enrich')
    args = ap.parse_args()

    # ── Load ELO for auto-enrich ──
    elo_ratings = {}
    if _HAS_ENRICH and not args.no_enrich:
        elo_path = os.path.join(DATA, 'elo_ratings.json')
        if os.path.exists(elo_path):
            raw_elo = json.load(open(elo_path))
            raw_r = raw_elo.get('ratings', raw_elo)
            elo_ratings = {k: v.get('elo', v) if isinstance(v, dict) else v for k, v in raw_r.items()}

    trajectory_data = {}
    if _HAS_ENRICH and not args.no_enrich:
        try:
            from elo_trajectory import get_trajectory_adjustments
            trajectory_data = get_trajectory_adjustments()
        except: pass

    # ── Read daily JSONs ──
    daily_files = sorted(
        [f for f in os.listdir(daily_dir) if f.endswith('.json') and f[:4].isdigit()],
        reverse=True
    )
    if args.date:
        target = f'{args.date}.json'
        daily_files = [f for f in daily_files if f == target]
        if not daily_files:
            print(f"No daily JSON for {args.date}")
            sys.exit(1)

    # ── Process each daily JSON ──
    total_generated = 0
    for fname in daily_files:
        date_str = fname.replace('.json', '')
        fpath = os.path.join(daily_dir, fname)
        try:
            dd = json.load(open(fpath))
        except Exception as e:
            print(f"  Error loading {fname}: {e}")
            continue

        for m in dd.get('matches', []):
            audit = m.get('audit', {})
            ta = audit.get('team_a', '')
            tb = audit.get('team_b', '')
            if not ta or not tb:
                continue

            # Determine round
            sched = m.get('schedule', {})
            rnd = sched.get('round', audit.get('round', ''))
            if args.round and rnd != args.round:
                continue
            if not rnd:
                # Try knockout_schedule
                for mid, km in KO_SCHEDULE.items():
                    if km.get('team_a') == ta and km.get('team_b') == tb:
                        rnd = km.get('round', '')
                        break
                    if km.get('team_b') == ta and km.get('team_a') == tb:
                        rnd = km.get('round', '')
                        break
            if not rnd:
                rnd = 'GS' if 'Group' in str(audit.get('round', '')) else '?'

            # ── Auto-enrich if sub_models missing ──
            if _HAS_ENRICH and not args.no_enrich and not audit.get('sub_models'):
                is_ko = rnd not in ('GS', 'GS1', 'GS2', 'GS3', '?') and 'Group' not in str(rnd)
                _enrich_match(audit, elo_ratings, trajectory_data, is_knockout=is_ko)
                print(f"  [auto-enrich] {ta} vs {tb} ({rnd})")

            # Build prediction dict
            pred = audit.get('prediction', {})
            sm = audit.get('sub_models', {})
            xga = float(pred.get('expected_goals_a', 0))
            xgb = float(pred.get('expected_goals_b', 0))

            p = {
                'team_a': ta, 'team_b': tb,
                'ensemble': sm.get('ensemble', {
                    'team_a_win': pred.get('team_a_win', 0),
                    'draw': pred.get('draw', 0),
                    'team_b_win': pred.get('team_b_win', 0),
                }),
                'poisson': sm.get('poisson', {
                    'team_a_win': pred.get('team_a_win', 0),
                    'draw': pred.get('draw', 0),
                    'team_b_win': pred.get('team_b_win', 0),
                }),
                'logit': sm.get('logit', {
                    'team_a_win': pred.get('team_a_win', 0),
                    'draw': pred.get('draw', 0),
                    'team_b_win': pred.get('team_b_win', 0),
                }),
                'expected_goals': sm.get('expected_goals', {'a': xga, 'b': xgb}),
                'top_scorelines': [
                    {'score': sp['score'], 'prob': sp['prob_pct']}
                    for sp in pred.get('scoreline_probs', [])[:5]
                ],
                'trajectory': audit.get('e_data', {}).get('trajectory', {}),
            }

            # Output filename: {YYYYMMDD}_{ISO_A}_{ISO_B}.pdf
            date_compact = date_str.replace('-', '')
            iso_a = ISO3.get(ta, ta[:3].upper())
            iso_b = ISO3.get(tb, tb[:3].upper())
            out = os.path.join(OUT, f"{date_compact}_{iso_a}_{iso_b}.pdf")

            # ── Load subjective judgment if exists ──
            subj_fname = f'{date_str}_{ta}_vs_{tb}.json'
            subj_path = os.path.join(DATA, 'subjective', subj_fname)
            subjective = None
            if os.path.exists(subj_path):
                subjective = json.load(open(subj_path))
                print(f"  [subjective] Loaded {subj_fname}")

            generate_match_report(ta, tb, p, out, round_label=rnd, subjective=subjective)
            total_generated += 1

    print(f"\nAll done: {total_generated} PDF(s) generated.")
