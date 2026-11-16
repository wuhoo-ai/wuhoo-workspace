#!/usr/bin/env python3.11
# WP0 收尾：合并并发+串行探测 -> feed_health；修可修坏源；统计有效源。
import sqlite3, json, time, urllib.request, ssl, re
from pathlib import Path
import yaml
SKILL=Path("/home/admin/wuhoo-workspace/skills/default/wuhoo-news-rss")
CFG=SKILL/"feeds/config.yaml"; DB=SKILL/"data/news.db"
BUILD=Path("/home/admin/wuhoo-workspace/docs/news-intel-build")
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
now=time.strftime("%F %T")

full={r['name']:r for r in json.load(open(BUILD/'full_health.json'))['results']}
serial=json.load(open(BUILD/'serial_recheck.json'))
cfg=yaml.safe_load(CFG.read_text(encoding='utf-8'))
tiers={f['name']:f.get('tier','T2') for f in cfg['feeds']}

# 修 MarketWatch: http->https 验证
mw=https_ok=None
for u in ["https://feeds.marketwatch.com/marketwatch/topstories/","https://www.marketwatch.com/rss/topstories"]:
    try:
        b=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 WuhooNewsIntel'}),timeout=20,context=ctx).read(200000)
        n=len(re.findall(rb'<item[\s>]',b))+len(re.findall(rb'<entry[\s>]',b))
        if n>0: mw=u; https_ok=n; break
    except Exception as e: pass
if mw:
    t=CFG.read_text(encoding='utf-8')
    t=t.replace("  url: http://feeds.marketwatch.com/marketwatch/topstories/","  url: "+mw)
    CFG.write_text(t,encoding='utf-8'); print(f"MarketWatch fixed -> {mw} ({https_ok} items)")
else:
    print("MarketWatch: no working alternative found, mark degraded")

conn=sqlite3.connect(DB); conn.execute("PRAGMA journal_mode=WAL")
ok=deg=down=0
for f in cfg['feeds']:
    name=f['name']; url=f['url']; tier=tiers[name]
    r=full.get(name,{}); s=serial.get(name)
    # 串行恢复优先
    if s and s['ok']:
        status='ok'; items=s['items']; hs=s['status']; lat=s['latency']; note='serial-recovered (concurrency false-negative)'
    elif r.get('ok'):
        status='ok'; items=r['items']; hs=r['status']; lat=r['latency']; note=''
    elif s:
        hs=s['status']; items=0; lat=s['latency']
        status='degraded' if hs in (402,403,429,503) else ('empty' if hs==200 else 'down')
        note=s.get('err','persistent failure')
    elif r:
        hs=r.get('status'); items=r.get('items',0); lat=r.get('latency')
        status='degraded' if hs in (402,403,429,503) else ('empty' if hs==200 else 'down')
        note=r.get('err','')
    else:
        status='unprobed'; hs=None; items=None; lat=None; note=''
    # 冗余空源禁用：36氪原生(与36氪快讯冗余)
    disabled=1 if (name=='36氪' and status=='empty') else 0
    if name=='MarketWatch' and mw: status='ok'; items=https_ok; hs=200; note='fixed https'
    conn.execute("INSERT OR REPLACE INTO feed_health(feed_name,url,tier,status,http_status,items,latency,last_check,fail_streak,disabled,note) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
      (name,url,tier,status,hs,items,lat,now,0 if status=='ok' else 1,disabled,note))
    if status=='ok': ok+=1
    elif status in ('degraded','empty'): deg+=1
    else: down+=1
conn.commit()
# 有效源统计（排除足球权重0 + disabled）
weights=cfg.get('feed_weights',{})
news_ok=[r[0] for r in conn.execute("select feed_name from feed_health where status='ok' and disabled=0")]
news_ok_nonfootball=[n for n in news_ok if weights.get(n,3)!=0]
print(f"feed_health: ok={ok} degraded/empty={deg} down/unprobed={down}")
print(f"effective OK sources (non-football, enabled): {len(news_ok_nonfootball)}")
print(f"  by tier:", {t:sum(1 for n in news_ok_nonfootball if tiers[n]==t) for t in ['T0','T1','T2','T4']})
conn.close()
json.dump({"ts":now,"ok":ok,"degraded":deg,"down":down,"effective_nonfootball":len(news_ok_nonfootball)},
          open(BUILD/'wp0_health_summary.json','w'),ensure_ascii=False,indent=1)
print("WP0 finalize DONE")
