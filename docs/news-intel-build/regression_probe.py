#!/usr/bin/env python3.11
# 通用回归探测：读 [{name,url}] 列表，输出 OK/FAIL+items。用法: regression_probe.py <in.json> <out.json>
import json, sys, time, concurrent.futures as cf, urllib.request, urllib.error, ssl, re
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA="Mozilla/5.0 (compatible; WuhooNewsIntel/1.0)"
def count(body):
    n=len(re.findall(rb"<item[\s>]",body))+len(re.findall(rb"<entry[\s>]",body))
    if n: return n
    b=body.strip()
    if b[:1] in (b"{",b"["):
        try:
            j=json.loads(b)
            if isinstance(j,dict):
                for k in ("data","items","list","articles"):
                    if isinstance(j.get(k),list): return len(j[k])
            return len(j) if isinstance(j,list) else 1
        except: return 0
    return 0
def probe(f):
    u=f["url"]; t0=time.time(); r={"name":f.get("name"),"url":u}
    try:
        req=urllib.request.Request(u,headers={"User-Agent":UA})
        with urllib.request.urlopen(req,timeout=20,context=ctx) as resp:
            body=resp.read(400000); r["status"]=resp.status
        r["items"]=count(body); r["ok"]=r["status"]==200 and r["items"]>0
    except urllib.error.HTTPError as e:
        r["status"]=e.code; r["items"]=0; r["ok"]=False
    except Exception as e:
        r["status"]=0; r["items"]=0; r["ok"]=False; r["err"]=str(e)[:60]
    r["latency"]=round(time.time()-t0,2); return r
def main():
    inp,out=sys.argv[1],sys.argv[2]
    feeds=json.load(open(inp))
    res=[]
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(probe,feeds): res.append(r)
    json.dump({"ts":time.strftime("%F %T"),"results":res},open(out,"w"),ensure_ascii=False,indent=1)
    ok=sum(1 for r in res if r["ok"])
    print(f"{out}: OK {ok}/{len(res)}")
    for r in res:
        if not r["ok"]: print(f"  FAIL {r['name']} status={r['status']} {r.get('err','')}")
if __name__=="__main__": main()
