#!/usr/bin/env python3.11
# WP0 源治理：additive 扩展 config.yaml + feed_health + deferred + tier 映射。保留原格式。
import shutil, sqlite3, json, time, os
from pathlib import Path
SKILL=Path("/home/admin/wuhoo-workspace/skills/default/wuhoo-news-rss")
CFG=SKILL/"feeds/config.yaml"
INTEL=Path("/home/admin/wuhoo-workspace/skills/default/wuhoo-news-intel")
BUILD=Path("/home/admin/wuhoo-workspace/docs/news-intel-build")
DB=SKILL/"data/news.db"
ts=time.strftime("%Y%m%d-%H%M%S")

# 1. 备份
bak=CFG.with_suffix(f".yaml.bak-{ts}-pre-intel")
shutil.copy2(CFG,bak); print("backup:",bak.name)
text=CFG.read_text(encoding="utf-8")

# 2. 修坏源 URL（已验证替代）
fixes=[
 ("  url: http://export.arxiv.org/rss/cs.AI",
  "  url: \"http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=30\""),
 ("  url: http://export.arxiv.org/rss/q-fin",
  "  url: \"http://export.arxiv.org/api/query?search_query=cat:q-fin&sortBy=submittedDate&sortOrder=descending&max_results=30\""),
 ("  url: http://127.0.0.1:1200/aljazeera/news",
  "  url: https://www.aljazeera.com/xml/rss/all.xml"),
]
for old,new in fixes:
    assert text.count(old)==1, f"fix anchor not unique: {old}"
    text=text.replace(old,new)
print("fixed 3 bad source URLs (arXiv AI/q-fin -> API, aljazeera -> native)")

# 3. 新源（仅已验证 OK）。(name,url,category,tier,tags,weight)
R="http://127.0.0.1:1200"
NEW=[
 ("上交所科创板",R+"/sse/renewal","投资","T0",["A股","科创板","公告"],9),
 ("上交所披露",R+"/sse/disclosure","投资","T0",["A股","公告","披露"],9),
 ("美联储新闻","https://www.federalreserve.gov/feeds/press_all.xml","财经","T0",["央行","美联储","官方"],9),
 ("财联社电报",R+"/cls/telegraph","财经","T1",["快讯","A股","实时"],10),
 ("财联社加红",R+"/cls/telegraph/red","财经","T1",["快讯","重要","实时"],10),
 ("财联社公司公告",R+"/cls/telegraph/announcement","财经","T1",["公告","公司","实时"],9),
 ("财联社深度",R+"/cls/depth/1000","财经","T1",["深度","财经"],8),
 ("金十重要",R+"/jin10/1","财经","T1",["快讯","宏观","实时"],9),
 ("金十数据",R+"/jin10","财经","T1",["快讯","宏观","实时"],8),
 ("华尔街见闻实时",R+"/wallstreetcn/live","财经","T1",["快讯","宏观","实时"],9),
 ("格隆汇首页",R+"/gelonghui/home","财经","T1",["港股","A股","深度"],7),
 ("晚点LatePost",R+"/latepost","科技","T2",["深度","商业","中国"],8),
 ("财新最新",R+"/caixin/latest","财经","T2",["深度","财经","中国"],8),
 ("观察者网",R+"/guancha","综合","T2",["时政","中国"],6),
 ("参考消息",R+"/cankaoxiaoxi","综合","T2",["国际","中文"],6),
 ("MIT科技评论",R+"/technologyreview","科技","T2",["深度","科技","英文"],7),
 ("巴伦中文",R+"/barronschina","财经","T2",["美股","投资","中文"],7),
 ("36氪快讯",R+"/36kr/newsflashes","科技","T2",["快讯","创业","中国"],7),
 ("CNBC","https://www.cnbc.com/id/100003114/device/rss/rss.html","财经","T2",["美股","财经","英文"],7),
 ("MarketWatch","http://feeds.marketwatch.com/marketwatch/topstories/","财经","T2",["美股","财经","英文"],7),
 ("HN头版","https://hnrss.org/frontpage","科技","T2",["科技","编程","硅谷"],6),
 ("Anthropic新闻",R+"/anthropic/news","AI","T4",["AI","Claude","官方"],8),
 ("UnusualWhales",R+"/unusualwhales/news","投资","T4",["美股","期权","异动"],7),
 ("ImportAI","https://importai.substack.com/feed","AI","T4",["AI","周报","英文"],7),
 ("触乐",R+"/chuapp","游戏","T4",["游戏","中文","深度"],6),
 ("GameDiscoverCo","https://newsletter.gamediscover.co/feed","游戏","T4",["游戏","市场","英文"],6),
 ("GamesIndustry","https://www.gamesindustry.biz/feed","游戏","T4",["游戏","产业","英文"],6),
 ("Unity博客","https://blog.unity.com/feed","游戏","T4",["游戏","Unity","引擎"],6),
 ("arXiv NLP","http://export.arxiv.org/api/query?search_query=cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=30","AI","T0",["AI","NLP","论文"],5),
 ("arXiv 机器学习","http://export.arxiv.org/api/query?search_query=cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=30","AI","T0",["AI","ML","论文"],5),
 ("arXiv 图形学","http://export.arxiv.org/api/query?search_query=cat:cs.GR&sortBy=submittedDate&sortOrder=descending&max_results=30","游戏","T0",["图形学","渲染","论文"],5),
]
def yq(s):
    return '"'+s+'"' if ('&' in s or ':' in s.split('//')[-1] and '?' in s) else s
block=[]
for name,url,cat,tier,tags,w in NEW:
    u='"'+url+'"' if '&' in url else url
    block.append(f"- name: {name}\n  url: {u}\n  category: {cat}\n  tier: {tier}\n  tags:")
    for t in tags: block.append(f"  - {t}")
    block.append(f"  status: \u2705 WP0\u65b0\u589e (2026-11-16, \u5b9e\u6d4bOK, {tier})")
newfeeds="\n".join(block)+"\n"
assert text.count("\nsettings:\n")==1
text=text.replace("\nsettings:\n", "\n"+newfeeds+"settings:\n")
print(f"inserted {len(NEW)} new verified feeds (tier-tagged)")

# 4. feed_weights 追加
wblock="".join(f"  {name}: {w}\n" for name,url,cat,tier,tags,w in NEW)
anchor="  Stratechery: 9"
assert text.count(anchor)==1
text=text.replace(anchor, anchor+"\n"+wblock.rstrip("\n"))
print("appended feed_weights for new sources")

CFG.write_text(text,encoding="utf-8")

# 5. 验证 YAML 可加载 + feed 数
import yaml
cfg=yaml.safe_load(CFG.read_text(encoding="utf-8"))
feeds=cfg["feeds"]; names=[f["name"] for f in feeds]
assert len(names)==len(set(names)), "duplicate feed names!"
print(f"config OK: total feeds={len(feeds)} (was 60, +{len(NEW)}), weights={len(cfg['feed_weights'])}")
tiers={}
for f in feeds: tiers[f["name"]]=f.get("tier","T2")

# 6. feed_health 表（additive，不动 articles）
conn=sqlite3.connect(DB); conn.execute("PRAGMA journal_mode=WAL")
conn.execute("""CREATE TABLE IF NOT EXISTS feed_health(
  feed_name TEXT PRIMARY KEY, url TEXT, tier TEXT, status TEXT,
  http_status INTEGER, items INTEGER, latency REAL, last_check TEXT,
  fail_streak INTEGER DEFAULT 0, disabled INTEGER DEFAULT 0, note TEXT)""")
# 从探测结果填充
rv=json.load(open(BUILD/"route_verification.json"))
def find(url):
    for r in rv["results"]:
        if r["url"]==url: return r
    return None
now=time.strftime("%F %T")
for f in feeds:
    r=find(f["url"]); tier=f.get("tier","T2")
    if r:
        st="ok" if r["ok"] else ("degraded" if r.get("status") in (403,503) else "down")
        conn.execute("INSERT OR REPLACE INTO feed_health(feed_name,url,tier,status,http_status,items,latency,last_check,fail_streak,disabled,note) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
          (f["name"],f["url"],tier,st,r.get("status"),r.get("items"),r.get("latency"),now,0 if r["ok"] else 1,0,""))
    else:
        conn.execute("INSERT OR IGNORE INTO feed_health(feed_name,url,tier,status,last_check,note) VALUES(?,?,?,?,?,?)",
          (f["name"],f["url"],tier,"unprobed",now,"existing feed, not in WP0 probe"))
conn.commit()
hc={r[0]:r[1] for r in conn.execute("select status,count(*) from feed_health group by status")}
print("feed_health populated:",hc)
conn.close()

# 7. 降级/未纳入源清单（404/503/需Puppeteer/代理，诚实标记，不进 active config）
deferred=[r for r in rv["results"] if not r["ok"]]
json.dump({"ts":now,"count":len(deferred),"sources":deferred},
          open(BUILD/"deferred_sources.json","w"),ensure_ascii=False,indent=1)
print(f"deferred sources recorded: {len(deferred)} (not added to active config)")

# 8. 权威 tier 映射（事件中心用）
(INTEL/"config").mkdir(exist_ok=True)
yaml.safe_dump({"source_tiers":tiers,"tier_weights":{"T0":10,"T1":9,"T2":7,"T3":5,"T4":6},
  "note":"WP0 2026-11-16; tier 决定 salience 基础权重 W; T3=TrendRadar热度源(WP1)"},
  open(INTEL/"config/source_tiers.yaml","w"),allow_unicode=True,sort_keys=False)
print("source_tiers.yaml written:",len(tiers),"sources")
print("WP0 config build DONE")
