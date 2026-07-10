#!/usr/bin/env python3.11
"""单场预测PDF生成器 — 干净排版 + 数据源标注 + v5.5推理路径"""
import json, os, sys
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, PageBreak, HRFlowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── Fonts ──
FONT_PATH = os.path.expanduser('~/.fonts/NotoSansSC-VF.ttf')
try:
    pdfmetrics.registerFont(TTFont('CJK', FONT_PATH))
    FONT = 'CJK'
except Exception:
    FONT = 'Helvetica'

BLUE = HexColor('#1a5276')
RED = HexColor('#c0392b')
GRAY = HexColor('#666666')
LIGHT_BG = HexColor('#eef5fb')
WHITE = HexColor('#ffffff')
DARK_BG = HexColor('#2980b9')

def S(name, **kw):
    """ParagraphStyle factory"""
    defaults = dict(fontName=FONT, leading=18, spaceAfter=4)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)

STYLES = {
    'title': S('title', fontSize=18, textColor=BLUE, spaceAfter=10, leading=24),
    'h2': S('h2', fontSize=14, textColor=BLUE, spaceAfter=6, spaceBefore=12, leading=20),
    'h3': S('h3', fontSize=12, textColor=BLUE, spaceAfter=4, spaceBefore=10, leading=18),
    'body': S('body', fontSize=10, leading=16, spaceAfter=3),
    'small': S('small', fontSize=8, textColor=GRAY, leading=12, spaceAfter=1),
    'source': S('source', fontSize=7, textColor=GRAY, leading=10, spaceAfter=2),
    'verdict': S('verdict', fontSize=12, textColor=RED, spaceAfter=6, spaceBefore=8, leading=20),
    'center': S('center', fontSize=10, alignment=TA_CENTER, leading=16),
}

def P(text, style='body'):
    return Paragraph(text, STYLES[style])

def make_table(headers, rows, col_widths=None):
    """Styled table with header"""
    all_rows = [headers] + rows
    t = Table(all_rows, colWidths=col_widths)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t

# ── Data ──
DATA_DIR = Path('/home/admin/wuhoo-workspace/skills/wuhoo/wuhoo-football-predictor/data')
PROJECT_DIR = DATA_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))
from wc2026_predict import TEAM_PROFILES
_TEAMS = TEAM_PROFILES.get('teams', TEAM_PROFILES)

# ── Tactics database ──
TACTICS_PATH = DATA_DIR / 'team_tactics.json'
TACTICS_DB = {}
if TACTICS_PATH.exists():
    with open(TACTICS_PATH) as f:
        TACTICS_DB = json.load(f)

def cn(team_en):
    return _TEAMS.get(team_en, {}).get('name_cn', team_en)

# ── Build one match ──

def build_match_pdf(match_data, idx, output_path):
    audit = match_data['audit']
    sched = match_data.get('schedule', {})
    layers = audit.get('layers', {})
    pred = audit['prediction']
    verdict = audit['verdict']
    eff = audit['effective_elo']
    reasoning_path = audit.get('reasoning_path', '')
    is_engine = audit.get('inference_engine', False)

    ta = audit['team_a']
    tb = audit['team_b']
    na = cn(ta)
    nb = cn(tb)
    pa = _TEAMS.get(ta, {})
    pb = _TEAMS.get(tb, {})

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm,
        title=f'WC2026 {na} vs {nb}'
    )

    story = []

    # ── Title ──
    match_info = f"{sched.get('date_beijing','?')} {sched.get('time_beijing','?')} BJT · Group {sched.get('group','?')} MD{sched.get('matchday','?')} · {sched.get('venue','?')}"
    story.append(P(f'{na} vs {nb}', 'title'))
    story.append(P(match_info, 'small'))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 6))

    # ── Team Style & Tactical Overview ──
    _add_tactical_section(story, ta, tb, na, nb)

    # ── ELO ──
    l1 = layers.get('1_elo_base', {})
    story.append(P('[L1] ELO 基础实力 — 数据源: elo_ratings.json', 'h3'))
    story.append(P(f'{na} FIFA#{pa.get("fifa_rank_est","?")} ELO={l1.get("team_a_elo","?")} · {nb} FIFA#{pb.get("fifa_rank_est","?")} ELO={l1.get("team_b_elo","?")} · 基础差 {l1.get("elo_diff",0):+d}, 胜率 {l1.get("base_win_prob",0)}%', 'body'))

    # ── Injuries ──
    l2 = layers.get('2_injuries', {})
    ip = DATA_DIR / 'injuries.json'
    injuries_db = {}
    if ip.exists():
        with open(ip) as f:
            injuries_db = json.load(f).get('injuries', {})
    story.append(P('[L2] 伤病影响 — 数据源: injuries.json (ESPN/BBC/Fox Sports)', 'h3'))
    has_inj = False
    for te, tc in [(ta, na), (tb, nb)]:
        if te in injuries_db:
            for p in injuries_db[te].get('players', []):
                story.append(P(f'{tc}: {p["name"]} [{p.get("status","?")}] {p.get("injury","?")[:80]} → ELO调整 {p.get("elo_penalty",0):+d}', 'body'))
                has_inj = True
    if not has_inj:
        story.append(P('两队均无伤病报告', 'body'))

    # ── Motivation (MD3) ──
    l25 = layers.get('2.5_motivation', {})
    if l25.get('team_a_classification') or l25.get('team_b_classification'):
        story.append(P('[L2.5] 出线动机 (QMF) — 数据源: compute_motivation.py → matchday3_motivation.json', 'h3'))
        cls_a = l25.get('team_a_classification', '-')
        cls_b = l25.get('team_b_classification', '-')
        adj_a = l25.get('team_a_adjustment', 0)
        adj_b = l25.get('team_b_adjustment', 0)
        rows = [
            [na, cls_a, f'{adj_a:+d}', nb, cls_b, f'{adj_b:+d}'],
        ]
        story.append(make_table(['球队', '动机分类', 'ELO调整', '对手', '动机分类', 'ELO调整'], rows))
        story.append(P('QMF分类: LOCKED_IN=已出线/MUST_WIN=必须赢/NEED_RESULT=需要分数/DRAW_OK=平局可接受/PRIDE_ONLY=荣誉战/TOP_SEED=头名之争', 'source'))

    # ── Coach ──
    l3 = layers.get('3_coach_meta', {})
    story.append(P('[L3] 教练/阵容 — 数据源: team_tactics.json + team_profiles.json', 'h3'))
    
    # Coach info with real names from tactics DB
    coach_rows = []
    for te, tc in [(ta, na), (tb, nb)]:
        prof = TEAM_PROFILES.get(te, {})
        tac = TACTICS_DB.get(te, {})
        coach_name = tac.get('coach', '') or prof.get('coach', '') or '?'
        fm = tac.get('formation', '')
        wc_best = prof.get('wc_best', '?')
        # ELO adjustment from layers
        adj = int(l3.get('team_a_adjustment' if te == ta else 'team_b_adjustment', 0))
        coach_rows.append([tc, str(coach_name)[:40], str(fm)[:20], str(wc_best)[:20], f'{adj:+d}'])
    story.append(make_table(['球队', '主帅', '常用阵型', '世界杯最佳', 'ELO调整'], coach_rows,
                            [60, 130, 80, 85, 60]))

    # ── Venue + Weather + Schedule ──
    l4 = layers.get('4_venue', {})
    vd = l4.get('venue_details', {})
    story.append(P('[L4] 场地/天气/赛程 — 数据源: venues.json + fetch_weather.py (Open-Meteo API)', 'h3'))
    venue_parts = [f"{vd.get('city','?')} {vd.get('temp_c','?')}°C"]
    if vd.get('indoor'):
        venue_parts.append('室内球场')
    if vd.get('altitude_m', 0) >= 1000:
        venue_parts.append(f'高原{vd["altitude_m"]}m')
    venue_parts.append(f'{na}场地调整: {ba(-l4.get("team_a_venue_penalty",0))}')
    venue_parts.append(f'{nb}场地调整: {ba(-l4.get("team_b_venue_penalty",0))}')
    story.append(P(' · '.join(venue_parts), 'body'))

    # ── Weather (Layer 4a) ──
    l4a = layers.get('4a_weather', {})
    if l4a:
        wd = l4a.get('weather_details', {})
        story.append(P('[L4a] 天气因子 — 数据源: fetch_weather.py (Open-Meteo API)', 'h3'))
        cond = wd.get('condition', '?')
        prec = wd.get('precip_category', '?')
        wind = wd.get('wind_category', '?')
        temp = wd.get('temp_c', '?')
        indoor = wd.get('indoor', False)
        parts = [f'天气: {cond}', f'气温: {temp}°C']
        if indoor:
            parts.append('室内球场 (风雨豁免)')
        else:
            if prec != 'none':
                parts.append(f'降水: {prec} ({wd.get("precip_mm",0)}mm)')
            if wind != 'none' and wind != 'indoor':
                parts.append(f'风力: {wind} ({wd.get("wind_kph",0)}km/h)')
        adj_a = l4a.get('team_a_adj', 0)
        adj_b = l4a.get('team_b_adj', 0)
        parts.append(f'ELO调整: {na} {ba(adj_a)} · {nb} {ba(adj_b)}')
        story.append(P(' · '.join(parts), 'body'))
        story.append(P(l4a.get('description', ''), 'source'))

    # ── Schedule Density (Layer 4b) ──
    l4b = layers.get('4b_schedule_density', {})
    if l4b:
        story.append(P('[L4b] 赛程密度 — 数据源: 赛程表 + Haversine距离计算 (Open-Meteo)', 'h3'))
        sd_a = l4b.get('team_a_details', {})
        sd_b = l4b.get('team_b_details', {})
        dist_a = sd_a.get('distance_km', 0)
        dist_b = sd_b.get('distance_km', 0)
        rest_a = sd_a.get('rest_days', 0)
        rest_b = sd_b.get('rest_days', 0)
        parts = []
        if dist_a > 0:
            parts.append(f'{na}: 旅途 {dist_a:.0f}km')
        if dist_b > 0:
            parts.append(f'{nb}: 旅途 {dist_b:.0f}km')
        parts.append(f'休息天数: 各{rest_a}天')
        adj_a = l4b.get('team_a_adj', 0)
        adj_b = l4b.get('team_b_adj', 0)
        parts.append(f'ELO调整: {na} {ba(adj_a)} · {nb} {ba(adj_b)}')
        story.append(P(' · '.join(parts), 'body'))
        story.append(P(l4b.get('description', ''), 'source'))
    l45 = layers.get('4.5_friendly_form', {})
    story.append(P('[L4.5] 热身赛状态 — 数据源: friendly_form_adjustments.json (赛前3场)', 'h3'))
    story.append(P(f'{na}: {ba(l45.get("team_a_adj",0))} ELO · {nb}: {ba(l45.get("team_b_adj",0))} ELO', 'body'))

    # ── Tournament form ──
    l46 = layers.get('4.6_tournament_form', {})
    story.append(P('[L4.6] 本届比赛表现 — 数据源: wc2026_results.json (权重0.12)', 'h3'))
    for tc, adj, details in [(na, l46.get('team_a_adj',0), l46.get('team_a_details',[])),
                               (nb, l46.get('team_b_adj',0), l46.get('team_b_details',[]))]:
        story.append(P('{} (调整 {:+d} ELO):'.format(tc, adj), 'body'))
        for d in details[:4]:
            story.append(P('  ' + str(d), 'source'))
        if not details:
            story.append(P('  (无比赛数据)', 'source'))

    # ── RSS ──
    l5 = layers.get('5_news_sentiment', {})
    story.append(P('[L5] 新闻情感 — 数据源: news.db (RSSHub+BBC+懂球帝+卫报+天空体育)', 'h3'))
    story.append(P(f'{na}: {ba(l5.get("team_a_adj",0))} · {nb}: {ba(l5.get("team_b_adj",0))}', 'body'))
    
    # Fetch actual RSS articles for this match
    rss_articles = _fetch_rss_articles(ta, tb)
    if rss_articles:
        for art in rss_articles[:5]:
            title = _nohtml(art.get('title', ''))
            feed = art.get('feed', '')[:15]
            story.append(P(f'[{feed}] {title[:100]}', 'source'))
    else:
        story.append(P('(近2日无相关报道)', 'source'))

    # ── Effective ELO ──
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(P('有效ELO汇总', 'h2'))
    ea = eff['team_a']; eb = eff['team_b']
    engine_da = eff.get('engine_delta_a', 0)
    engine_db = eff.get('engine_delta_b', 0)
    rows = [
        ['ELO原始', str(ea['base']), str(eb['base'])],
        ['各层累计调整', f'{ba(ea["adjustments"])}', f'{ba(eb["adjustments"])}'],
    ]
    if engine_da or engine_db:
        rows.append(['推理引擎增量', f'{engine_da:+d}', f'{engine_db:+d}'])
    rows.append(['有效ELO', str(ea['effective']), str(eb['effective'])])
    story.append(make_table(['', na, nb], rows))
    story.append(P(f'有效ELO差: {eff["diff"]:+d}', 'body'))

    # ── Poisson ──
    story.append(P('Poisson 预测', 'h2'))
    conf_label = {'high': '高', 'medium': '中', 'low': '低'}.get(verdict['confidence'], '?')
    rows = [
        [f'{na}胜', f'{pred["team_a_win"]}%'],
        ['平局', f'{pred["draw"]}%'],
        [f'{nb}胜', f'{pred["team_b_win"]}%'],
        ['最可能比分', pred['most_likely_score']],
        ['预期进球(xG)', f'{na}: {pred["expected_goals_a"]:.2f} / {nb}: {pred["expected_goals_b"]:.2f}'],
        ['置信度', conf_label],
    ]
    story.append(make_table(['指标', '数值'], rows))
    story.append(P(f'判定: {verdict["result"]}', 'verdict'))

    # ── v5.7 Scoreline Distribution ──
    score_probs = pred.get('scoreline_probs', [])
    if score_probs:
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
        story.append(P('[比分概率分布] 90分钟 — 数据源: Poisson(λ_a,λ_b) 独立采样', 'h2'))
        rows = [['比分', '概率', '累计']]
        for sp in score_probs:
            ga, gb = map(int, sp['score'].split('-'))
            result = f'{na}胜' if ga > gb else f'{nb}胜' if gb > ga else '平局'
            rows.append([
                f"{sp['score']} ({result})",
                f"{sp['prob_pct']:.1f}%",
                f"{sp['cumulative']*100:.1f}%"
            ])
        story.append(make_table(['比分', '概率', '累计'], rows))
        story.append(P(f'90分钟预期进球: {na} {pred["expected_goals_a"]:.2f} / {nb} {pred["expected_goals_b"]:.2f}', 'source'))

    # ── v5.5 Reasoning ──
    if is_engine and reasoning_path:
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
        story.append(P('v5.5 推理引擎路径 — 数据源: rules_v1.json + inference_engine.py', 'h2'))
        for line in reasoning_path.split('\n')[:50]:
            stripped = line.strip()
            if not stripped:
                continue
            # Replace emoji
            clean = stripped.replace('📋', '[规则] ').replace('⚡', '[修正] ').replace('└', '  ->').replace('├', '  |')
            is_header = not (clean.startswith('  ') or clean.startswith('[规则]') or clean.startswith('[修正]'))
            story.append(P(clean, 'body' if is_header else 'small'))

    # ── Build ──
    doc.build(story)
    return output_path


def ba(v):
    if isinstance(v, float): v = round(v, 1)
    if v == 0: return '0'
    return f'+{v}' if v > 0 else str(v)

def _fs(layer, key, sub):
    v = layer.get(key, {}).get(sub, 0)
    if isinstance(v, float): v = round(v, 1)
    return ba(v)


def _nohtml(text):
    import re
    if not text: return ''
    return re.sub(r'<[^>]+>', '', text).strip()


def _fetch_rss_articles(team_a, team_b):
    """Fetch recent RSS articles mentioning either team"""
    import sqlite3
    db_path = '/home/admin/wuhoo-workspace/skills/wuhoo/wuhoo-news-rss/data/news.db'
    EXCLUDED = {'SoccerNews', 'Football Rankings'}
    try:
        db = sqlite3.connect(db_path)
        placeholders = ','.join('?' * len(EXCLUDED))
        results = []
        for team in [team_a, team_b]:
            rows = db.execute(
                f"SELECT title, feed_name, pub_date FROM articles "
                f"WHERE category='足球' AND feed_name NOT IN ({placeholders}) "
                f"AND (title LIKE ? OR summary LIKE ?) "
                f"AND pub_date > datetime('now', '-5 days') "
                f"ORDER BY fetched_at DESC LIMIT 5",
                (*EXCLUDED, f'%{team}%', f'%{team}%')
            ).fetchall()
            for r in rows:
                results.append({'title': r[0], 'feed': r[1], 'date': r[2]})
        db.close()
        # Deduplicate by title
        seen = set()
        unique = []
        for r in results:
            if r['title'] not in seen:
                seen.add(r['title'])
                unique.append(r)
        return unique[:8]
    except Exception:
        return []


def _add_tactical_section(story, ta, tb, na, nb):
    """[风格战术] 紧凑段落式 — 数据源: team_tactics.json"""
    tac_a = TACTICS_DB.get(ta, {})
    tac_b = TACTICS_DB.get(tb, {})

    if not tac_a and not tac_b:
        return  # 静默跳过

    story.append(P('[风格战术] 球队对比 — 数据源: team_tactics.json', 'h2'))

    # Paragraph blocks per team — avoids table overflow
    for tc, tac in [(na, tac_a), (nb, tac_b)]:
        if not tac:
            continue
        parts = []
        # Key info line: formation + coach
        fm = tac.get('formation', '')
        co = tac.get('coach', '')
        if fm or co:
            parts.append(f"阵型: {fm}  |  主帅: {co}")
        if tac.get('style_summary'):
            parts.append(tac['style_summary'])
        if tac.get('attacking'):
            parts.append(f"进攻: {tac['attacking']}")
        if tac.get('defensive'):
            parts.append(f"防守: {tac['defensive']}")
        if tac.get('transitions'):
            parts.append(f"转换: {tac['transitions']}")
        if tac.get('set_pieces'):
            parts.append(f"定位球: {tac['set_pieces']}")
        strengths = tac.get('strengths', [])
        weaknesses = tac.get('weaknesses', [])
        if strengths:
            parts.append(f"优势: {'; '.join(strengths)}")
        if weaknesses:
            parts.append(f"短板: {'; '.join(weaknesses)}")
        if tac.get('key_players'):
            parts.append(f"核心: {', '.join(tac['key_players'])}")
        if tac.get('tournament_form_note'):
            parts.append(f"本届: {tac['tournament_form_note']}")

        story.append(P(f'【{tc}】', 'h3'))
        for line in parts:
            story.append(P(line, 'body'))
        story.append(Spacer(1, 4))

# ── Main ──
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='单场/批量预测PDF生成器')
    parser.add_argument('match_idx', nargs='?', type=int, default=0, help='场次序号(1-N)')
    parser.add_argument('--date', default=None, help='日期 YYYY-MM-DD')
    parser.add_argument('--all', action='store_true', help='生成所有场次')
    args = parser.parse_args()

    date_str = args.date or '2026-06-25'
    json_path = DATA_DIR / 'daily_predictions' / f'{date_str}.json'
    if not json_path.exists():
        candidates = list((DATA_DIR / 'daily_predictions').glob(f'*{date_str}*.json'))
        if candidates:
            json_path = candidates[0]
        else:
            print(f"No prediction JSON for {date_str}")
            sys.exit(1)

    with open(json_path) as f:
        data = json.load(f)

    matches = data.get('matches', [])
    out_dir = DATA_DIR / 'reports' / 'single'
    os.makedirs(out_dir, exist_ok=True)

    if args.all or args.match_idx == 0:
        idxs = range(1, len(matches) + 1)
    else:
        idxs = [args.match_idx]

    results = []
    for i in idxs:
        m = matches[i - 1]
        na = cn(m['audit']['team_a'])
        nb = cn(m['audit']['team_b'])
        # Naming: report_2026-06-25_瑞士vs加拿大.pdf
        fname = f'report_{date_str}_{na}_vs_{nb}.pdf'
        out = out_dir / fname
        build_match_pdf(m, i, str(out))
        size_kb = os.path.getsize(out) / 1024
        print(f'OK ({i}/{len(matches)}): {fname} ({size_kb:.0f}KB)')
        results.append(str(out))
    print(f'\nDone: {len(results)} PDFs in {out_dir}')
