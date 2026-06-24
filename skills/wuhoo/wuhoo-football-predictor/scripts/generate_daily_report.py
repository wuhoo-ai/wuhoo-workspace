#!/usr/bin/env python3.11
"""
WC2026 证据链预测日报 — v3.0
从 daily_predictions JSON + 外部数据源 生成完整证据链 PDF 报告。

Usage:
  python3.11 scripts/generate_daily_report.py --date 2026-06-18
"""

import sys, os, json, re, sqlite3
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))
from wc2026_predict import TEAM_PROFILES

DATA_DIR = PROJECT_DIR / 'data'

# ── Dynamic loading from wc2026_results.json ──
def _load_results_and_standings():
    """Load KNOWN_RESULTS and GROUP_STANDINGS dynamically from results DB."""
    results_path = DATA_DIR / 'wc2026_results.json'
    sched_path = DATA_DIR / 'wc2026_schedule.json'
    
    known = {}
    if results_path.exists():
        with open(results_path) as f:
            data = json.load(f)
        for m in data.get('matches', []):
            if m.get('status') != 'completed':
                continue
            ta = m['team_a']
            tb = m['team_b']
            sa = m['score_a']
            sb = m['score_b']
            date_str = m.get('date_beijing', '')[-5:]  # 'MM-DD'
            if date_str.startswith('06-'):
                date_str = date_str[3:] + '/' + date_str[:2]  # 'DD/MM' → '6/12' style
            # Determine result string
            if sa > sb:
                res_a = f'{sa}-{sb} 胜'
                res_b = f'{sb}-{sa} 负'
            elif sa < sb:
                res_a = f'{sa}-{sb} 负'
                res_b = f'{sb}-{sa} 胜'
            else:
                res_a = f'{sa}-{sb} 平'
                res_b = f'{sb}-{sa} 平'
            # Add opponent in Chinese if available
            cn_b = cn(tb)
            cn_a = cn(ta)
            known.setdefault(ta, []).append((date_str, f'vs {cn_b}', res_a))
            known.setdefault(tb, []).append((date_str, f'vs {cn_a}', res_b))
    
    # Build group standings
    # Load group assignments from schedule
    team_group = {}
    if sched_path.exists():
        with open(sched_path) as f:
            sched = json.load(f)
        for m in sched.get('matches', []):
            g = m.get('group', '')
            if g:
                team_group[m.get('team_a', '')] = g
                team_group[m.get('team_b', '')] = g
    
    # Calculate standings per group
    standings = {}
    if results_path.exists():
        with open(results_path) as f:
            data = json.load(f)
        group_stats = {}
        for m in data.get('matches', []):
            if m.get('status') != 'completed':
                continue
            ta = m['team_a']
            tb = m['team_b']
            sa = m['score_a']
            sb = m['score_b']
            g = team_group.get(ta, '?')
            for t, gf, ga in [(ta, sa, sb), (tb, sb, sa)]:
                if g not in group_stats:
                    group_stats[g] = {}
                if t not in group_stats[g]:
                    group_stats[g][t] = {'p': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0}
                st = group_stats[g][t]
                st['p'] += 1
                st['gf'] += gf
                st['ga'] += ga
                if (t == ta and sa > sb) or (t == tb and sb > sa):
                    st['w'] += 1
                elif sa == sb:
                    st['d'] += 1
                else:
                    st['l'] += 1
        
        for g, teams in group_stats.items():
            rows = []
            for t, s in teams.items():
                pts = s['w'] * 3 + s['d']
                rows.append((cn(t), pts, s['p'], s['gf'], s['ga']))
            # Sort by points, then GD
            rows.sort(key=lambda x: (-x[1], -(x[3]-x[4])))
            standings[g] = rows
    
    return known, standings

def cn(team_en):
    return TEAM_PROFILES.get(team_en, {}).get('name_cn', team_en)

KNOWN_RESULTS, GROUP_STANDINGS = _load_results_and_standings()


def ba(v):
    """Bold-adjusted: +5 or -3 or 0."""
    if v == 0: return "0"
    return f"+{v}" if v > 0 else str(v)

def fs(layer, key, sub):
    """Format sub-field rounded."""
    v = layer.get(key, {}).get(sub, 0)
    if isinstance(v, float): v = round(v, 1)
    return ba(v) if isinstance(v, (int, float)) else str(v)

def translate_rss(title, summary):
    """Translate RSS article key points to Chinese using keyword mapping."""
    text = (title + ' ' + (summary or '')).lower()
    parts = []
    
    # Source
    if 'bbc' in text: source = '[BBC]'
    elif 'guardian' in text: source = '[卫报]'
    elif 'sky' in text: source = '[Sky]'
    elif 'football italia' in text: source = '[Football Italia]'
    elif 'breaking' in text: source = '[BreakingTheLines]'
    else: source = ''
    
    # Key events
    signals = []
    if 'red card' in text:
        signals.append('红牌')
    if 'late goal' in text or 'late winner' in text or 'dramatic' in text or 'stoppage' in text:
        signals.append('绝杀/绝平')
    if 'injury' in text or 'injured' in text or 'strain' in text or 'rupture' in text:
        signals.append('伤病')
    if 'drone' in text:
        signals.append('无人机事件')
    if 'upset' in text:
        signals.append('爆冷')
    if 'clean sheet' in text:
        signals.append('零封')
    if 'penalty' in text:
        signals.append('点球')
    if 'var' in text:
        signals.append('VAR争议')
    
    # Match result extraction
    if 'beat' in text or 'win' in text or 'defeat' in text:
        signals.append('胜负')
    if 'draw' in text:
        signals.append('平局')
    
    # Generate Chinese title
    cn_title = title[:60]
    # Replace common English phrases
    for en, zh in [
        ('highlights:', '集锦:'),
        ('prediction:', '预测:'),
        ('world cup 2026:', '世界杯2026:'),
        ('vs', '对阵'),
        ('beat', '击败'),
        ('win against', '战胜'),
        ('draw', '战平'),
        ('ready for', '备战'),
        ('lift-off', '起飞'),
        ('frustration to party', '从沮丧到狂欢'),
        ('steady start', '稳步起步'),
        ('seals', '锁定'),
        ('nine-man', '9人'),
        ('opener', '揭幕战'),
        ('lineups', '首发阵容'),
        ('starting', '首发'),
        ('three red cards', '三张红牌'),
    ]:
        cn_title = cn_title.replace(en, zh)
    
    signal_str = f" [{', '.join(signals)}]" if signals else ''
    return f"{source} {cn_title}{signal_str}"


def nohtml(text):
    if not text: return ''
    return re.sub(r'<[^>]+>', '', text).strip()


# ── PDF Generation ──

FONT_PATH = os.path.expanduser('~/.fonts/NotoSansSC-VF.ttf')

def md_to_pdf(md_path, pdf_path):
    import markdown
    from xhtml2pdf import pisa

    with open(md_path) as f:
        md_text = f.read()

    html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont('NotoSansSC', FONT_PATH))
        font_family = "'NotoSansSC', 'Helvetica', sans-serif"
    except Exception:
        font_family = "'Helvetica', sans-serif"

    css = f"""
    @font-face {{ font-family: 'NotoSansSC'; src: url('{FONT_PATH}') format('truetype'); }}
    body {{ font-family: {font_family}; max-width: 760px; margin: 20px auto;
           color: #1a1a1a; font-size: 14pt; line-height: 1.6; font-weight: 600; }}
    h1 {{ color: #1a5276; font-size: 22pt; border-bottom: 3px solid #2980b9; padding-bottom: 6px; font-weight: 900; }}
    h2 {{ color: #2471a3; font-size: 17pt; font-weight: 900; }}
    h3 {{ color: #2e86c1; font-size: 14pt; font-weight: 800; }}
    h4 {{ color: #3498db; font-size: 13pt; font-weight: 800; }}
    table {{ border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 12pt; table-layout: fixed; }}
    strong {{ color: #c0392b; font-weight: 900; }}
    th {{ background: #2980b9; color: white; font-weight: 800; }}
    td {{ border: 1px solid #999; padding: 5px 8px; text-align: center; word-wrap: break-word; overflow: hidden; font-weight: 500; }}
    tr:nth-child(even) {{ background: #eef5fb; }}
    code {{ background: #f4f4f4; padding: 1px 3px; font-size: 11pt; }}
    pre, code {{ font-family: 'NotoSansSC', 'Courier New', monospace; font-size: 11pt; line-height: 1.4; }}
    pre {{ background: #f8f8f8; padding: 8px 12px; border-left: 3px solid #2980b9; white-space: pre; }}
    """

    html_full = f'<html><head><meta charset="utf-8"><style>{css}</style></head><body>{html_body}</body></html>'

    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    with open(pdf_path, 'wb') as out:
        pisa.CreatePDF(html_full, dest=out, encoding='utf-8')
    return pdf_path


# ── Match Section Builder ──

def build_match_section(match_data, idx, injuries_db, rss_articles):
    audit = match_data['audit']
    sched = match_data.get('schedule', {})
    layers = audit.get('layers', {})
    pred = audit['prediction']
    verdict = audit['verdict']
    eff = audit['effective_elo']
    reasoning_path = audit.get('reasoning_path', '')
    inference_trace = audit.get('inference_trace', {})
    is_engine = audit.get('inference_engine', False)
    reasoning = audit.get('reasoning', [])

    ta = audit['team_a']
    tb = audit['team_b']
    na = cn(ta)
    nb = cn(tb)
    pa = TEAM_PROFILES.get(ta, {})
    pb = TEAM_PROFILES.get(tb, {})

    L = []
    L.append(f"### #{idx}  {na} vs {nb}")
    L.append(f"{sched.get('date_beijing','?')} {sched.get('time_beijing','?')} BJT"
             f"  |  Group {sched.get('group','?')} MD{sched.get('matchday','?')}"
             f"  |  {sched.get('venue','?')}")
    L.append("")
    L.append("#### [证据链]")
    L.append("")

    # L1
    l1 = layers.get('1_elo_base', {})
    L.append(f"**L1  ELO基础实力**  (来源: *elo_ratings.json*)")
    L.append(f"> {na}  FIFA#{pa.get('fifa_rank_est','?')}  **{l1.get('team_a_elo','?')}**"
             f"  ({pa.get('style_tag','?')})  vs  "
             f"{nb}  FIFA#{pb.get('fifa_rank_est','?')}  **{l1.get('team_b_elo','?')}**"
             f"  ({pb.get('style_tag','?')})")
    L.append(f"> 基础差 **{l1.get('elo_diff','?'):+}**,  基础胜率 **{l1.get('base_win_prob','?')}%**")
    L.append("")

    # L2
    l2 = layers.get('2_injuries', {})
    L.append(f"**L2  伤病影响**  (来源: *injuries.json*)")
    has_inj = False
    for te, tc in [(ta, na), (tb, nb)]:
        if injuries_db and te in injuries_db:
            for p in injuries_db[te].get('players', []):
                L.append(f"> {tc}: **{p['name']}** [{p.get('status','?')}] "
                         f"{p.get('injury','?')[:60]}  -> 罚 **{p.get('elo_penalty',0):+}**")
                has_inj = True
    if not has_inj:
        L.append("> 两队均无伤病报告")
    L.append("")

    # L3: Coach table (plain-text for reliable alignment)
    l3 = layers.get('3_coach_meta', {})
    L.append(f"**L3  教练/团队磨合**  (来源: *TEAM_PROFILES*)")
    L.append(f"> {na}: WC{pa.get('wc_appearances','?')}届, 队史{pa.get('wc_best','?')}"
             f"  |  {nb}: WC{pb.get('wc_appearances','?')}届, 队史{pb.get('wc_best','?')}")
    L.append("")
    L.append("```")
    L.append(f"  {'评估维度':<12s} {na:<8s} {nb:<8s} 说明")
    L.append(f"  {'-'*50}")
    L.append(f"  {'教练经验':<12s} {fs(l3,'team_a_breakdown','coach'):>4s}    {fs(l3,'team_b_breakdown','coach'):>4s}    世界杯执教场次/成绩")
    L.append(f"  {'历史战绩':<12s} {fs(l3,'team_a_breakdown','result'):>4s}    {fs(l3,'team_b_breakdown','result'):>4s}    队史最佳成绩加分")
    L.append(f"  {'阵容稳定':<12s} {fs(l3,'team_a_breakdown','stability'):>4s}    {fs(l3,'team_b_breakdown','stability'):>4s}    核心球员保留率")
    L.append(f"  {'团队化学':<12s} {fs(l3,'team_a_breakdown','chemistry'):>4s}    {fs(l3,'team_b_breakdown','chemistry'):>4s}    合练场次/友谊赛默契度")
    L.append(f"  {'-'*50}")
    L.append(f"  合计          {ba(l3.get('team_a_adjustment',0)):>4s}     {ba(l3.get('team_b_adjustment',0)):>4s}")
    L.append("```")
    L.append("")

    # L4: Venue
    l4 = layers.get('4_venue', {})
    vd = l4.get('venue_details', {})
    L.append(f"**L4  场地影响**  (来源: *wc2026_schedule.json*)")
    vp = [f"{vd.get('city','?')}, {vd.get('temp_c','?')}C"]
    if vd.get('indoor'): vp.append("室内球场")
    if vd.get('altitude_m', 0) >= 1000:
        vp.append(f"高原{vd['altitude_m']}m(~{100-vd['altitude_m']//100*1.2:.0f}%含氧)")
        vp.append("非适应队罚ELO")
    if l4.get('home_advantage', 0): vp.append(f"主场+{l4['home_advantage']}({na})")
    L.append(f"> {' | '.join(vp)}")
    L.append(f"> {na} 罚 **{ba(-l4.get('team_a_venue_penalty',0))}**"
             f"  /  {nb} 罚 **{ba(-l4.get('team_b_venue_penalty',0))}**")
    L.append("")

    # L4.5: Friendly
    l45 = layers.get('4.5_friendly_form', {})
    L.append(f"**L4.5  热身赛表现**  (来源: *friendly_form 赛前3场*)")
    L.append(f"> {na} **{ba(l45.get('team_a_adj',0))}**"
             f"  /  {nb} **{ba(l45.get('team_b_adj',0))}**")
    L.append("")

    # L4.6: Tournament Form (v5.1)
    l46 = layers.get('4.6_tournament_form', {})
    ta_adj_46 = l46.get('team_a_adj', 0)
    tb_adj_46 = l46.get('team_b_adj', 0)
    ta_details_46 = l46.get('team_a_details', [])
    tb_details_46 = l46.get('team_b_details', [])
    L.append("**L4.6  本届比赛表现**  (来源: *wc2026_results.json*  权重0.12)")
    L.append(f"> {na} **{ba(ta_adj_46)}**  /  {nb} **{ba(tb_adj_46)}**")
    if ta_details_46:
        for d in ta_details_46:
            L.append(f">   {d}")
    if tb_details_46:
        for d in tb_details_46:
            L.append(f">   {d}")
    L.append("")

    # Group context
    group = sched.get('group', '?')
    ra = KNOWN_RESULTS.get(ta, [])
    rb = KNOWN_RESULTS.get(tb, [])
    st = GROUP_STANDINGS.get(group, [])
    L.append(f"**本届战绩**  (Group {group})")
    L.append("")
    
    # Format each team's result line
    for te, tc, results in [(ta, na, ra), (tb, nb, rb)]:
        if results:
            for d, opp, res in results:
                L.append(f"  * {tc}  [{d}]  {opp}  --  {res}")
        else:
            L.append(f"  * {tc}  暂无比赛记录")
    
    # Standings as a mini table
    if st:
        L.append("")
        L.append(f"  Group {group} 积分榜:")
        L.append("```")
        L.append(f"  {'排名':<4s} {'球队':<8s} {'场':>3s} {'胜':>3s} {'平':>3s} {'负':>3s} {'进':>4s} {'失':>4s} {'分':>3s}")
        L.append(f"  {'-'*40}")
        for rank, (name, pts, played, gf, ga) in enumerate(st, 1):
            # Calculate W/D/L from pts/played (simplified: all matches played are 1)
            w = pts // 3
            d = pts % 3
            l = played - w - d
            L.append(f"  {rank:<4d} {name:<8s} {played:>3d} {w:>3d} {d:>3d} {l:>3d} {gf:>4d} {ga:>4d} {pts:>3d}")
        L.append("```")
    L.append("")

    # L5: RSS + snippets (with Chinese translation)
    l5 = layers.get('5_news_sentiment', {})
    L.append(f"**L5  RSS新闻情感**  (来源: *news.db*  权重0.05)")
    L.append(f"> {na} **{ba(l5.get('team_a_adj',0))}**"
             f"  /  {nb} **{ba(l5.get('team_b_adj',0))}**")
    if rss_articles:
        seen = set()
        snippets_cn = []
        for art in rss_articles:
            t = nohtml(art.get('title', ''))
            if not t or t in seen: continue
            seen.add(t)
            # Translate key info to Chinese
            cn_summary = translate_rss(t, nohtml(art.get('summary', '')))
            snippets_cn.append(f">   {cn_summary}")
        if snippets_cn:
            for s in snippets_cn[:3]:
                L.append(s)
    L.append("")

    # L5.5: v5 signals
    l55 = layers.get('5.5_unstructured_signals', {})
    tac = l55.get('tactical_matchup', 0)
    L.append(f"**L5.5  v5.0 LLM非结构化信号**  (来源: *signal_cache*  权重0.15)")
    L.append(f"> {na} **{ba(l55.get('team_a_adj',0))}**"
             f"  /  {nb} **{ba(l55.get('team_b_adj',0))}**"
             f"  |  战术匹配 **{tac:+.2f}**"
             f"  |  7类信号:伤病/战术/状态/团队/阵容/外部/纪律")
    L.append("")

    # Effective ELO
    ea = eff['team_a']; eb = eff['team_b']
    L.append("---")
    L.append("#### [有效ELO汇总]")
    L.append("")
    L.append("```")
    L.append(f"              {na:<10s} {nb:<10s}")
    L.append(f"  {'-'*30}")
    L.append(f"  ELO原始      {ea['base']:<5d}     {eb['base']:<5d}")
    L.append(f"  L1-L4.6+L5.5 {ba(ea['adjustments']):>4s}      {ba(eb['adjustments']):>4s}")
    L.append(f"  {'-'*30}")
    L.append(f"  有效ELO       {ea['effective']:<5d}     {eb['effective']:<5d}")
    L.append(f"  有效差                  {eff['diff']:+d}")
    # v5.5 engine deltas
    engine_da = eff.get('engine_delta_a', 0)
    engine_db = eff.get('engine_delta_b', 0)
    if engine_da or engine_db:
        L.append(f"  🧠引擎增量              {engine_da:+d}       {engine_db:+d}")
    L.append("```")
    L.append("")
    
    # QMF motivation badge
    l25 = layers.get('2.5_motivation', {})
    if l25.get('team_a_classification') or l25.get('team_b_classification'):
        cls_a = l25.get('team_a_classification', '-')
        cls_b = l25.get('team_b_classification', '-')
        adj_a = l25.get('team_a_adjustment', 0)
        adj_b = l25.get('team_b_adjustment', 0)
        L.append(f"**🎯 MD3动机**: {na} `{cls_a}`({adj_a:+d}) | {nb} `{cls_b}`({adj_b:+d})")
        L.append("")

    # Prediction
    conf = {'high':'[HIGH]','medium':'[MED]','low':'[LOW]'}.get(verdict['confidence'],'[?]')
    L.append("#### [Poisson预测]")
    L.append("")
    L.append("```")
    L.append(f"  {na}胜        {pred['team_a_win']}%")
    L.append(f"  平局          {pred['draw']}%")
    L.append(f"  {nb}胜        {pred['team_b_win']}%")
    L.append(f"  最可能比分    {pred['most_likely_score']}  (xG {pred['expected_goals_a']:.2f}/{pred['expected_goals_b']:.2f})")
    L.append(f"  置信度        {conf}")
    L.append("```")
    L.append(f"\n**判定: {verdict['result']}**")
    L.append("")

    # Reasoning with Chinese RSS insight
    if is_engine and reasoning_path:
        L.append("#### [v5.5 推理路径]")
        for line in reasoning_path.split('\n')[:30]:  # Limit to 30 lines
            stripped = line.strip()
            if stripped:
                # Indent trace lines for readability
                if stripped.startswith('📋') or stripped.startswith('├') or stripped.startswith('└') or stripped.startswith('⚡'):
                    L.append(f"  {stripped}")
                elif stripped.startswith('─') or stripped.startswith('净调整'):
                    L.append(f"  {stripped}")
                else:
                    L.append(stripped)
        L.append("")
    
    if reasoning:
        L.append("#### [推理逻辑]")
        for i, r in enumerate(reasoning, 1):
            L.append(f"{i}. {r}")
        # Add Chinese RSS key point if available
        if rss_articles:
            key_info = []
            for art in rss_articles:
                t = nohtml(art.get('title', ''))
                s = nohtml(art.get('summary', ''))
                # Extract key phrases about form/injury/momentum
                combined = (t + ' ' + s).lower()
                for kw, zh in [('injur', '伤病'), ('red card', '红牌'), ('late goal', '绝杀'),
                               ('upset', '爆冷'), ('momentum', '势头'), ('drone', '无人机'),
                               ('frustrat', '受挫'), ('party', '狂欢')]:
                    if kw in combined:
                        key_info.append(f"{zh}: {t[:50]}")
                        break
            if key_info:
                L.append(f"> RSS关键信号: {'; '.join(key_info[:3])}")
        L.append("")

    summary = {
        'idx': idx, 'team_a': na, 'team_b': nb,
        'a_win': pred['team_a_win'], 'draw': pred['draw'], 'b_win': pred['team_b_win'],
        'score': pred['most_likely_score'],
        'xga': pred['expected_goals_a'], 'xgb': pred['expected_goals_b'],
        'verdict': verdict['result'], 'elo_diff': eff['diff'],
    }
    return '\n'.join(L), summary


# ── Data sources appendix ──

def build_data_sources():
    L = []
    L.append("---\n## [数据源引用]\n")

    # Weights
    wp = PROJECT_DIR / 'configs' / 'weights.json'
    if wp.exists():
        with open(wp) as f:
            w = json.load(f).get('default', {})
        L.append("### 模型权重")
        L.append("| 层级 | 权重 |")
        L.append("|------|------|")
        for k, label in [('elo','ELO基础'),('poisson','Poisson模型'),
                          ('factor_model','因子模型'),('news_sentiment','RSS情感'),
                          ('unstructured_signals','v5.0信号')]:
            L.append(f"| {label} | {w.get(k,0):.2f} |")
        L.append("")

    # RSS feeds
    rss_dir = Path('/home/admin/wuhoo-workspace/skills/wuhoo/wuhoo-news-rss')
    feeds_path = rss_dir / 'feeds' / 'config.yaml'
    if feeds_path.exists():
        import yaml, re
        try:
            with open(feeds_path) as f:
                cfg = yaml.safe_load(f)
        except Exception:
            # YAML contains emoji — strip non-printable chars, retry
            with open(feeds_path, encoding='utf-8') as f:
                raw = f.read()
            raw = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u4E00-\u9FFF\u3000-\u303F\uFF00-\uFFEF]', '', raw)
            cfg = yaml.safe_load(raw)
        fb = [f for f in cfg.get('feeds',[]) if '足球' in str(f.get('category',''))]
        L.append("### RSS资讯源")
        L.append("| 名称 | 语言 | 类型 |")
        L.append("|------|------|------|")
        for f in fb[:12]:
            tags = f.get('tags',[])
            lang = '中' if any('中文' in t for t in tags) else '英'
            is_rh = any('RSSHub' in str(t) for t in tags) or '127.0.0.1:1200' in f.get('url','')
            L.append(f"| {f.get('name','?')} | {lang} | {'RSSHub' if is_rh else 'RSS'} |")
        L.append("")

    # DB stats
    db_path = rss_dir / 'data' / 'news.db'
    if db_path.exists():
        db = sqlite3.connect(str(db_path))
        cnt = db.execute("SELECT COUNT(*) FROM articles WHERE category='足球'").fetchone()[0]
        db.close()
        L.append(f"足球分类文章: {cnt}篇")

    # Signal cache
    sc = DATA_DIR / 'signal_cache'
    if sc.exists():
        L.append(f"v5.0信号缓存: {len(list(sc.glob('*.json')))}个文件")

    L.append("")
    return '\n'.join(L)


# ── Main ──

def generate_report(json_path, output_path=None):
    with open(json_path) as f:
        data = json.load(f)

    generated = data.get('generated', '?')
    matches = data.get('matches', [])

    # Injuries
    injuries_db = {}
    ip = DATA_DIR / 'injuries.json'
    if ip.exists():
        with open(ip) as f:
            injuries_db = json.load(f).get('injuries', {})

    # RSS articles per team (with quality filtering)
    rss_by_team = {}
    EXCLUDED_FEEDS = {'SoccerNews', 'World Soccer Talk', 'Football Rankings'}
    TITLE_BLACKLIST = ['pga tour', 'golf', 'miners brought football']  # false positives
    try:
        db = sqlite3.connect('/home/admin/wuhoo-workspace/skills/wuhoo/wuhoo-news-rss/data/news.db')
        for m in matches:
            for team in [m['audit']['team_a'], m['audit']['team_b']]:
                if team not in rss_by_team:
                    placeholders = ','.join('?' * len(EXCLUDED_FEEDS))
                    rows = db.execute(
                        f"SELECT title, summary, pub_date FROM articles "
                        f"WHERE category='足球' AND feed_name NOT IN ({placeholders}) "
                        f"AND title LIKE ? "
                        f"ORDER BY fetched_at DESC LIMIT 3",
                        (*EXCLUDED_FEEDS, f'%{team}%')
                    ).fetchall()
                    if not rows:
                        # Fallback: also search summary if no title match
                        rows = db.execute(
                            f"SELECT title, summary, pub_date FROM articles "
                            f"WHERE category='足球' AND feed_name NOT IN ({placeholders}) "
                            f"AND (title LIKE ? OR summary LIKE ?) "
                            f"ORDER BY fetched_at DESC LIMIT 2",
                            (*EXCLUDED_FEEDS, f'%{team}%', f'%{team}%')
                        ).fetchall()
                    rss_by_team[team] = [
                        {'title':r[0],'summary':r[1],'date':r[2]} for r in rows
                        if not any(b in (r[0] or '').lower() for b in TITLE_BLACKLIST)
                    ]
        db.close()
    except Exception:
        pass

    L = []
    L.append("# WC2026 预测日报 v5.0")
    L.append(f"生成: {generated[:16]} BJT  |  共 {len(matches)} 场")
    L.append(f"格式: 证据链 (数据源+本届战绩+RSS关键信息)")
    L.append("")

    summaries = []
    for i, m in enumerate(matches, 1):
        audit = m['audit']
        arts = rss_by_team.get(audit['team_a'],[]) + rss_by_team.get(audit['team_b'],[])
        block, summ = build_match_section(m, i, injuries_db, arts)
        L.append(block)
        L.append("---\n")
        summaries.append(summ)

    # Summary table (plain-text)
    L.append("## [汇总表]\n")
    L.append("```")
    L.append(f"  {'#':<3s} {'比赛':<16s} {'胜%':>6s} {'平%':>6s} {'负%':>6s} {'比分':>5s} {'xG':>8s} {'有效差':>6s} 判定")
    L.append(f"  {'-'*80}")
    for s in summaries:
        L.append(f"  {s['idx']:<3d} {s['team_a']+' vs '+s['team_b']:<16s} "
                 f"{s['a_win']:>5.1f}% {s['draw']:>5.1f}% {s['b_win']:>5.1f}% "
                 f"{s['score']:>5s} {s['xga']:.1f}/{s['xgb']:.1f} "
                 f"{s['elo_diff']:>+5d}  {s['verdict']}")
    L.append("```")
    L.append("")

    L.append(build_data_sources())
    L.append("[!] 预测仅供娱乐参考 | v5.0.0")

    report = '\n'.join(L)

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report)

    return report, summaries


def main():
    date_str = None
    json_only = '--json-only' in sys.argv
    if '--date' in sys.argv:
        idx = sys.argv.index('--date')
        if idx + 1 < len(sys.argv):
            date_str = sys.argv[idx + 1]
    if not date_str:
        print("Usage: python3.11 scripts/generate_daily_report.py --date 2026-06-18 [--json-only]")
        sys.exit(1)

    json_path = DATA_DIR / 'daily_predictions' / f'{date_str}.json'
    if not json_path.exists():
        candidates = list((DATA_DIR / 'daily_predictions').glob(f'*{date_str}*.json'))
        if candidates: json_path = candidates[0]
        else: print(f"No prediction JSON for {date_str}"); sys.exit(1)

    md_path = DATA_DIR / 'reports' / f'report_{date_str}.md'
    report, _ = generate_report(str(json_path), str(md_path))
    print(f"MD: {md_path}")

    pdf_path = md_path.with_suffix('.pdf')
    try:
        md_to_pdf(str(md_path), str(pdf_path))
        print(f"PDF: {pdf_path}")
    except Exception as e:
        print(f"PDF failed: {e}")

    if not json_only:
        print(report)


if __name__ == '__main__':
    main()
