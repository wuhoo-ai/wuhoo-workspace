#!/usr/bin/env python3.11
"""
v5.10.1 QF单场PDF生成器 — 完整版
结构: 战术对比 → 伤病 → 教练/磨合 → 场地/天气/旅途 → 本届表现 → 新闻情感 → ELO分解 → 模型预测 → 比分分布 → ELO轨迹
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
    'body':   S('body', fontSize=10, leading=15, spaceAfter=2),
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

def get_tournament_matches(team):
    """Get all tournament matches for a team"""
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
                'date': m.get('date', '?')[:10],
                'round': m.get('round', '?'),
                'opponent': opp,
                'score': score_str,
                'outcome': outcome,
                'penalties': m.get('penalties', ''),
                'aet': m.get('aet', False),
            })
    return matches

def get_weather_for_match(team_a, team_b, venue_name=''):
    """Find weather for this match — by venue name since QF team_a/team_b may be None"""
    fc = WEATHER.get('forecasts', {})
    if isinstance(fc, dict):
        for mid, f in fc.items():
            if isinstance(f, dict):
                # Match by venue (QF weather data may not have team names filled)
                if venue_name and f.get('venue') == venue_name:
                    return f
                if (f.get('team_a') == team_a and f.get('team_b') == team_b) or \
                   (f.get('team_a') == team_b and f.get('team_b') == team_a):
                    return f
    return {}

def get_rss_articles(team_a, team_b):
    """Fetch recent RSS articles"""
    db_path = '/home/admin/wuhoo-workspace/skills/wuhoo/wuhoo-news-rss/data/news.db'
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
def generate_match_report(team_a, team_b, prediction, outpath):
    doc = SimpleDocTemplate(outpath, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm,
                             topMargin=12*mm, bottomMargin=12*mm,
                             title=f'WC2026 QF {cn(team_a)} vs {cn(team_b)}')
    story = []
    ca, cb = cn(team_a), cn(team_b)

    # Parse prediction data
    ens = prediction['ensemble']; poi = prediction['poisson']; log = prediction['logit']
    xg = prediction['expected_goals']; scores = prediction['top_scorelines']
    traj = prediction.get('trajectory', {})
    # Parse string dicts if needed
    for k in ['ensemble','poisson','logit','expected_goals','trajectory']:
        v = prediction.get(k)
        if isinstance(v, str): prediction[k] = eval(v)
    ens = prediction['ensemble']; poi = prediction['poisson']; log = prediction['logit']
    xg = prediction['expected_goals']; traj = prediction.get('trajectory', {})

    # ── TITLE ──
    story.append(P(f"{ca} vs {cb} — 世界杯2026 四分之一决赛预测", 'title'))
    story.append(P(f"{team_a} vs {team_b} · Quarter-finals · v5.10.1 完整分析", 'small'))

    # Find match details from knockout schedule OR bracket_recursive_results
    match_info = None
    for mid, m in KO_SCHEDULE.items():
        if m.get('team_a') == team_a and m.get('team_b') == team_b:
            match_info = m; break
        if m.get('team_b') == team_a and m.get('team_a') == team_b:
            match_info = m; break

    if not match_info:
        # Try bracket_recursive_results
        try:
            br = json.load(open(os.path.join(DATA, 'bracket_recursive_results.json')))
            for mid, m in br.get('match_details', {}).items():
                if m.get('team_a') == team_a and m.get('team_b') == team_b:
                    match_info = {'venue': m.get('venue', '?'), 'date': m.get('date', '?'), 'round': m.get('round', 'QF')}
                    break
                if m.get('team_b') == team_a and m.get('team_a') == team_b:
                    match_info = {'venue': m.get('venue', '?'), 'date': m.get('date', '?'), 'round': m.get('round', 'QF')}
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
        story.append(P(f'【{tc}】', 'h3'))
        fm = tac.get('formation', ''); co = tac.get('coach', '')
        if fm or co: story.append(P(f"阵型: {fm}  |  主帅: {co}", 'body'))
        if tac.get('style_summary'): story.append(P(tac['style_summary'], 'body'))
        if tac.get('attacking'): story.append(P(f"进攻: {tac['attacking']}", 'body'))
        if tac.get('defensive'): story.append(P(f"防守: {tac['defensive']}", 'body'))
        if tac.get('transitions'): story.append(P(f"转换: {tac['transitions']}", 'body'))
        if tac.get('set_pieces'): story.append(P(f"定位球: {tac['set_pieces']}", 'body'))
        strengths = tac.get('strengths', []); weaknesses = tac.get('weaknesses', [])
        if strengths: story.append(P(f"优势: {'; '.join(strengths)}", 'body'))
        if weaknesses: story.append(P(f"短板: {'; '.join(weaknesses)}", 'body'))
        if tac.get('key_players'): story.append(P(f"核心球员: {', '.join(tac['key_players'])}", 'body'))
        story.append(Spacer(1, 3))

    # ═══════════════════════════════════════
    # SECTION 2: 伤病报告
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[伤病报告] — 数据源: injuries.json (ESPN/BBC/Fox Sports)', 'h2'))
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

    # ═══════════════════════════════════════
    # SECTION 3: 教练/团队磨合
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[教练/磨合] — 数据源: team_profiles.json', 'h2'))
    coach_rows = []
    for te, tc in [(team_a, ca), (team_b, cb)]:
        p = TEAM_PROFILES.get(te, {})
        fifa = p.get('fifa_rank_est', '?'); coach = p.get('coach', p.get('coach_info', '?'))
        stability = p.get('stability', '?'); chemistry = p.get('chemistry', '?')
        style = p.get('style', p.get('style_category', '?'))
        coach_rows.append([tc, f'#{fifa}', str(coach)[:40], str(stability), str(chemistry), str(style)])
    story.append(T(['球队','FIFA','教练','阵容稳定','团队化学','风格'], coach_rows,
                    [70, 40, 120, 60, 60, 80]))

    # ═══════════════════════════════════════
    # SECTION 4: 场地/天气/旅途疲劳
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[场地/天气/旅途] — 数据源: venues.json + Open-Meteo', 'h2'))

    venue_name = match_info.get('venue', '?') if match_info else '?'
    venue_data = VENUES.get(venue_name, {})
    city = venue_data.get('city', '?'); altitude = venue_data.get('altitude_m', 0)
    indoor = venue_data.get('indoor', False)
    story.append(P(f"场地: {venue_name} ({city}) · 海拔 {altitude}m · {'室内' if indoor else '室外'}", 'body'))

    # Weather
    wx = get_weather_for_match(team_a, team_b, venue_name)
    if wx:
        cond = wx.get('condition', '?'); temp = wx.get('temp_c', '?')
        prec = wx.get('precip_mm', 0); wind = wx.get('wind_kph', 0)
        wx_parts = [f"天气: {cond}", f"气温: {temp}°C"]
        if not indoor:
            if prec > 0: wx_parts.append(f"降水量: {prec}mm")
            if wind > 0: wx_parts.append(f"风力: {wind}km/h")
        story.append(P(' · '.join(wx_parts), 'body'))
    else:
        story.append(P('天气数据暂缺', 'body'))

    # Schedule fatigue
    for te, tc in [(team_a, ca), (team_b, cb)]:
        matches = get_tournament_matches(te)
        if len(matches) >= 2:
            last_two = matches[-2:]
            story.append(P(f'{tc}: 近两场 {last_two[0]["date"]} vs {cn(last_two[0]["opponent"])} {last_two[0]["score"]} → {last_two[1]["date"]} vs {cn(last_two[1]["opponent"])} {last_two[1]["score"]}', 'source'))
    story.append(P('注: QF阶段旅途影响较小(淘汰赛固定城市)', 'source'))

    # ═══════════════════════════════════════
    # SECTION 5: 本届比赛表现
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[本届比赛表现] — 数据源: wc2026_results.json', 'h2'))

    for te, tc in [(team_a, ca), (team_b, cb)]:
        matches = get_tournament_matches(te)
        if not matches: continue
        wins = sum(1 for m in matches if m['outcome'] == 'W')
        draws = sum(1 for m in matches if m['outcome'] == 'D')
        losses = sum(1 for m in matches if m['outcome'] == 'L')
        gf = sum(int(m['score'].split('-')[0]) for m in matches)
        ga = sum(int(m['score'].split('-')[1]) for m in matches)
        story.append(P(f'{tc}: {wins}胜{draws}平{losses}负 · 进{gf}失{ga} · 净胜{gf-ga:+d}', 'body'))

        match_rows = []
        for m in matches:
            outcome_icon = {'W': '✓', 'D': '=', 'L': '✗'}.get(m['outcome'], '?')
            extra = ''
            if m.get('penalties'): extra = f' (PK{m["penalties"]})'
            elif m.get('aet'): extra = ' (加时)'
            match_rows.append([m['date'], m['round'], f"{cn(m['opponent'])}", m['score']+extra, outcome_icon])
        story.append(T(['日期','阶段','对手','比分','结果'], match_rows, [70, 65, 80, 65, 35]))
        story.append(Spacer(1, 3))

    # ═══════════════════════════════════════
    # SECTION 6: 新闻/情感分析
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[新闻/RSS报道] — 数据源: news.db (RSSHub+BBC+懂球帝+卫报)', 'h2'))
    articles = get_rss_articles(team_a, team_b)
    if articles:
        for art in articles:
            title = nohtml(art.get('title', '')); feed = art.get('feed', '')
            summary = nohtml(art.get('summary', ''))[:80]
            story.append(P(f"[{feed}] {title[:100]}", 'source'))
            if summary: story.append(P(f"  {summary}", 'source'))
    else:
        story.append(P('(近5日无相关报道)', 'source'))

    # ═══════════════════════════════════════
    # SECTION 7: ELO 汇总
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[ELO实力] — 数据源: elo_ratings.json', 'h2'))
    elo_a = ELO.get(team_a, 1500); elo_b = ELO.get(team_b, 1500)
    diff = elo_a - elo_b
    story.append(P(f'{ca} ELO {elo_a} · {cb} ELO {elo_b} · 原始差 {diff:+d}', 'body'))

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
    # SECTION 8: 预测模型
    # ═══════════════════════════════════════
    story.append(HR())
    story.append(P('[预测模型] 胜平负概率', 'h2'))
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
    # SECTION 9: 比分概率分布 (Top 5 — Poisson计算补充)
    # ═══════════════════════════════════════
    story.append(Spacer(1, 6))
    story.append(P('[比分概率分布] Top 5 · 90分钟·淘汰赛λ=0.78校准', 'h2'))

    # Compute full Poisson matrix for top 5
    import math
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
    # SECTION 10: 判定
    # ═══════════════════════════════════════
    story.append(Spacer(1, 8))
    story.append(HR())
    story.append(P(f'判定: {v}', 'verdict'))
    conf = '高' if max(wa, dr, wb) >= 70 else ('中' if max(wa, dr, wb) >= 55 else '低')
    story.append(P(f'置信度: {conf} · 数据保鲜: {datetime.now().strftime("%Y-%m-%d %H:%M")} · 模型: v5.10.1', 'source'))
    story.append(P('数据源: ELO + FIFA + team_tactics.json + injuries.json + Open-Meteo + RSSHub + WC1998-2022淘汰赛统计', 'source'))

    doc.build(story)
    size_kb = os.path.getsize(outpath) / 1024
    print(f"  {os.path.basename(outpath)}: {size_kb:.0f}KB")
    return outpath

# ── Main ──
if __name__ == '__main__':
    d = json.load(open(os.path.join(DATA, "daily_predictions/2026-07-08_qf.json")))
    for p in d['predictions']:
        ta, tb = p['team_a'], p['team_b']
        out = os.path.join(OUT, f"QF_{ta}_vs_{tb}.pdf")
        generate_match_report(ta, tb, p, out)
    print("\nAll QF PDFs generated.")
