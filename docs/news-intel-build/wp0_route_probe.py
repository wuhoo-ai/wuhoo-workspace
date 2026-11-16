#!/usr/bin/env python3.11
# WP0 A1: RSSHub 候选路由 + 原生源实测（用户已授权）。输出 route_verification.json
import json, time, concurrent.futures as cf, urllib.request, urllib.error, ssl, re
import xml.etree.ElementTree as ET

BASE = "http://127.0.0.1:1200"
UA = "Mozilla/5.0 (compatible; WuhooNewsIntel/1.0; +audit)"
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

# (tier, label, url)  RSSHub 本地路由用相对路径；原生源用完整 URL
CAND = [
 # T0 一手/官方
 ("T0","上交所科创板","/sse/renewal"),
 ("T0","上交所披露","/sse/disclosure"),
 ("T0","北交所要闻","/bse/important_news"),
 ("T0","北交所发行","/bse/fxrz_list"),
 ("T0","北交所监管","/bse/cxjg_list"),
 ("T0","北交所审核","/bse/audit_result"),
 ("T0","深交所","/szse"),
 ("T0","港交所","/hkex/news"),
 ("T0","央行沟通(Puppeteer)","/gov/pbc/goutongjiaoliu"),
 ("T0","央行公开市场(Puppeteer)","/gov/pbc/tradeAnnouncement"),
 ("T0","央行政策研究","/gov/pbc/zcjl"),
 ("T0","央行工作论文","/gov/pbc/gzlw"),
 ("T0","ECB press","/ecb/press"),
 ("T0","SEC press(RSSHub)","/sec/pressreleases"),
 # T1 实时快讯
 ("T1","财联社电报全部","/cls/telegraph"),
 ("T1","财联社加红","/cls/telegraph/red"),
 ("T1","财联社公司","/cls/telegraph/announcement"),
 ("T1","财联社港股","/cls/telegraph/hk"),
 ("T1","财联社深度","/cls/depth/1000"),
 ("T1","金十重要","/jin10/1"),
 ("T1","金十全部","/jin10"),
 ("T1","华尔街见闻live","/wallstreetcn/live"),
 ("T1","华尔街见闻news","/wallstreetcn/news"),
 ("T1","富途要闻","/futunn/highlights"),
 ("T1","格隆汇首页","/gelonghui/home"),
 ("T1","格隆汇快讯","/gelonghui/live"),
 ("T1","中证快讯","/cs/news/zzkx"),
 # T2 新增深度
 ("T2","机器之心","/jiqizhixin"),
 ("T2","量子位","/qbitai"),
 ("T2","新智元","/xinzhiyuan"),
 ("T2","晚点","/latepost"),
 ("T2","钛媒体","/tmtpost"),
 ("T2","界面","/jiemian"),
 ("T2","财新最新","/caixin/latest"),
 ("T2","环球网","/huanqiu"),
 ("T2","观察者网","/guancha"),
 ("T2","参考消息","/cankaoxiaoxi"),
 ("T2","MIT Tech Review","/technologyreview"),
 ("T2","InfoQ","/infoq"),
 ("T2","智通港股","/zhitongcaijing/hkstock"),
 ("T2","智通美股","/zhitongcaijing/meigu"),
 ("T2","智通公告","/zhitongcaijing/announcement"),
 ("T2","巴伦中文","/barronschina"),
 ("T2","finviz NVDA","/finviz/news/NVDA"),
 ("T2","36氪快讯","/36kr/newsflashes"),
 ("T2","36氪资讯","/36kr/information/web_news"),
 # T2 坏源修复候选
 ("T2fix","美联社","/apnews"),
 ("T2fix","半岛","/aljazeera"),
 ("T2fix","HN(RSSHub)","/hackernews"),
 # T4 游戏
 ("T4game","Unity Blog","/unity/blog"),
 ("T4game","Unity Release","/unity/release"),
 ("T4game","游戏葡萄","/youxiputao"),
 ("T4game","GameLook","/gamelook"),
 ("T4game","触乐","/chuapp"),
 ("T4game","游研社","/yystv"),
 ("T4game","indienova","/indienova"),
 ("T4game","GDC","/gdc"),
 # T4 AI/量化
 ("T4ai","Anthropic News","/anthropic/news"),
 ("T4ai","HF Papers","/huggingface/papers"),
 ("T4ai","HF Blog","/huggingface/blog"),
 ("T4ai","SeekingAlpha AAPL","/seekingalpha/AAPL/news"),
 ("T4ai","UnusualWhales","/unusualwhales/news"),
 ("T4ai","GitHub Trending","/github/trending/daily/any"),
 ("T4ai","ProductHunt","/producthunt/today"),
 # 原生源（完整 URL）
 ("native","HN frontpage","https://hnrss.org/frontpage"),
 ("native","AlJazeera原生","https://www.aljazeera.com/xml/rss/all.xml"),
 ("native","CoinDesk原生","https://www.coindesk.com/arc/outboundfeeds/rss/"),
 ("native","arXiv cs.AI","http://arxiv.org/rss/cs.AI"),
 ("native","arXiv cs.GR","http://arxiv.org/rss/cs.GR"),
 ("native","arXiv q-fin","http://arxiv.org/rss/q-fin"),
 ("native","美联储press","https://www.federalreserve.gov/feeds/press_all.xml"),
 ("native","CNBC","https://www.cnbc.com/id/100003114/device/rss/rss.html"),
 ("native","MarketWatch","http://feeds.marketwatch.com/marketwatch/topstories/"),
 ("native","YahooFinance","https://finance.yahoo.com/news/rssindex"),
 ("native","GameDiscoverCo","https://newsletter.gamediscover.co/feed"),
 ("native","gamesindustry","https://www.gamesindustry.biz/feed"),
 ("native","UnityBlog原生","https://blog.unity.com/feed"),
 ("native","ImportAI","https://importai.substack.com/feed"),
 ("native","TheBatch","https://www.deeplearning.ai/the-batch/rss/"),
 ("native","SEC EDGAR NVDA 8-K","https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=NVDA&type=8-K&output=atom"),
]

def count_items(body):
    b = body.strip()
    try:
        if b.startswith("{") or b.startswith("["):
            j = json.loads(b)
            if isinstance(j, dict):
                for k in ("data","items","list","articles"):
                    if isinstance(j.get(k), list): return len(j[k])
                return 1
            return len(j) if isinstance(j,list) else 1
        # XML: count <item> or <entry>
        n = len(re.findall(rb"<item[\s>]", body)) + len(re.findall(rb"<entry[\s>]", body))
        if n: return n
        root = ET.fromstring(body)
        return len(list(root.iter()))
    except Exception:
        return len(re.findall(rb"<item[\s>]", body)) + len(re.findall(rb"<entry[\s>]", body))

def probe(t):
    tier,label,u = t
    url = u if u.startswith("http") else BASE+u
    t0=time.time(); rec={"tier":tier,"label":label,"url":url,"rsshub":not u.startswith("http")}
    try:
        req=urllib.request.Request(url, headers={"User-Agent":UA})
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            body=r.read(400000); rec["status"]=r.status
        rec["items"]=count_items(body); rec["bytes"]=len(body)
        rec["ok"]= rec["status"]==200 and rec["items"]>0
    except urllib.error.HTTPError as e:
        rec["status"]=e.code; rec["items"]=0; rec["ok"]=False; rec["err"]=f"HTTP {e.code}"
    except Exception as e:
        rec["status"]=0; rec["items"]=0; rec["ok"]=False; rec["err"]=str(e)[:80]
    rec["latency"]=round(time.time()-t0,2)
    return rec

def main():
    res=[]
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(probe, CAND):
            res.append(r)
    out="/home/admin/wuhoo-workspace/docs/news-intel-build/route_verification.json"
    json.dump({"ts":time.strftime("%F %T"),"total":len(res),"results":res}, open(out,"w"), ensure_ascii=False, indent=1)
    ok=[r for r in res if r["ok"]]
    print(f"TOTAL {len(res)}  OK {len(ok)}  FAIL {len(res)-len(ok)}")
    from collections import defaultdict
    by=defaultdict(lambda:[0,0])
    for r in res:
        by[r["tier"]][0]+=1
        if r["ok"]: by[r["tier"]][1]+=1
    for k,(tot,o) in sorted(by.items()): print(f"  {k}: {o}/{tot} OK")
    print("--- OK 路由 ---")
    for r in ok: print(f"  [{r['tier']}] {r['label']} {r['url'].replace(BASE,'')} items={r['items']} {r['latency']}s")
    print("--- FAIL ---")
    for r in res:
        if not r["ok"]: print(f"  [{r['tier']}] {r['label']} status={r['status']} {r.get('err','')}")

if __name__=="__main__": main()
