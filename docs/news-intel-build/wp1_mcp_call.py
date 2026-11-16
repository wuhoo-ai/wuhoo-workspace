#!/usr/bin/env python3.11
# WP1 功能验证: 真实 MCP streamableHttp 握手 + tools/call 取 T3 热度数据
import urllib.request, json, sys
URL="http://127.0.0.1:3333/mcp"
def post(payload, session=None):
    h={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
    if session: h['Mcp-Session-Id']=session
    req=urllib.request.Request(URL,data=json.dumps(payload).encode(),headers=h,method='POST')
    resp=urllib.request.urlopen(req,timeout=30)
    sid=resp.headers.get('Mcp-Session-Id')
    body=resp.read().decode()
    # SSE 解析
    data=None
    for line in body.splitlines():
        if line.startswith('data:'):
            try: data=json.loads(line[5:].strip())
            except: pass
    if data is None:
        try: data=json.loads(body)
        except: data={'raw':body[:200]}
    return sid, data
# 1 initialize
sid,init=post({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"wuhoo-wp1","version":"1.0"}}})
print("session:",sid,"| server:",init.get('result',{}).get('serverInfo'))
# 2 initialized notification
try: post({"jsonrpc":"2.0","method":"notifications/initialized"},sid)
except Exception as e: print("initialized note:",str(e)[:40])
# 3 tools/call get_trending_topics
_,tt=post({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_trending_topics","arguments":{"top_n":8}}},sid)
print("\n=== get_trending_topics(top_n=8) ===")
res=tt.get('result',{})
content=res.get('content',[])
for c in content[:1]:
    txt=c.get('text','')
    print(txt[:1200])
# 4 tools/call get_latest_news
_,ln=post({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_latest_news","arguments":{"platforms":["wallstreetcn-hot","zhihu"],"limit":5}}},sid)
print("\n=== get_latest_news(wallstreetcn-hot,zhihu) ===")
for c in ln.get('result',{}).get('content',[])[:1]:
    print(c.get('text','')[:800])
json.dump({"session":sid,"trending":tt,"latest":ln},open("/home/admin/wuhoo-workspace/docs/news-intel-build/wp1_mcp_call_result.json","w"),ensure_ascii=False,indent=1)
print("\nWP1 MCP functional call DONE")
