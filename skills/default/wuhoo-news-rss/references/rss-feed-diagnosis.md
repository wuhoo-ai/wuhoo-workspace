# RSS 源诊断与替换工作流

## 何时使用

- 某个 RSS 源长时间无新文章（DB 中 count=0 或 pub_date 过期）
- 新增足球/体育等垂直领域 RSS 源
- 定期巡检 RSS 源健康状况

## 诊断流水线（4 步）

### Step 1: 从 SQLite 查活跃度

```sql
SELECT feed_name, COUNT(*), MAX(pub_date), MIN(pub_date)
FROM articles WHERE feed_name = '目标源名';
```

关键信号：
- `COUNT=0` → 源从未拉取成功过
- `MAX(pub_date)` 距今 >7 天 → 源可能已失效
- `COUNT>0` 但最近一次 fetch 无新增 → 源可能改版但 feed URL 仍可访问

### Step 2: 直接测试 URL

```python
import urllib.request, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
content = resp.read()
```

常见 HTTP 状态：
- `403 Forbidden` → 源已关闭公开访问，需 User-Agent 绕过或放弃
- `404 Not Found` → URL 已变更，需找新 URL
- `200` 返回 HTML → 源不再提供 RSS，RSS feed URL 已改为网站主页
- `200` 返回 XML/RSS → 检查是否包含 `<item>` 或 `<entry>`
- 超时 → 网络不可达（GFW 或服务器拒绝）

### Step 3: 解析验证

```python
import xml.etree.ElementTree as ET
root = ET.fromstring(content)
items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
print(f"Items: {len(items)}")
```

### Step 4: 找替代源

优先级：
1. **FeedSpot 榜单** — `https://rss.feedspot.com/<topic>_rss_feeds/` 
2. **RSSHub 路由** — 检查自部署 RSSHub (`http://127.0.0.1:1200/`) 是否有对应路由
3. **Web Search** — `"<topic>" RSS feed working 2026`
4. **已知可靠源** — BBC/Guardian/Sky Sports 的 RSS 长期稳定

## 已验证的足球 RSS 源状态（2026-06-02）

| 源 | URL | 状态 | 备注 |
|---|---|---|---|
| BBC Sport Football | `https://feeds.bbci.co.uk/sport/football/rss.xml` | ✅ | 387 条历史 |
| The Guardian Football | `https://www.theguardian.com/football/rss` | ✅ | 283 条历史 |
| Sky Sports Football | `https://www.skysports.com/rss/12040` | ✅ | 197 条历史 |
| Football Rankings | `http://www.football-rankings.info/feeds/posts/default` | ✅ 新增 | ELO/FIFA 排名方法论，25 items |
| SoccerNews | `https://www.soccernews.com/feed` | ✅ 新增 | 10 items |
| World Soccer Talk | `https://worldsoccertalk.com/feed` | ✅ 新增 | 100 items |
| Football Italia | `https://football-italia.net/feed` | ✅ 新增 | 20 items |
| ESPN Football | `https://www.espn.com/espn/rss/soccer/news` | ❌ 403 | ESPN 封杀 RSS 访问 |
| Goal.com | `https://www.goal.com/feeds/en/news` | ❌ 404 | Feed 已移除 |
| FIFA.com | `https://www.fifa.com/news.rss` | ❌ 返回HTML | 不再提供 RSS |
| UEFA | `https://www.uefa.com/insideuefa/news/news.rss` | ❌ 超时 | 可能被 GFW |
| 懂球帝/直播吧 | RSSHub 路由 | ❌ 路由不可用 | RSSHub 未安装对应路由 |

## RSSHub 路由诊断

```bash
# 检查 RSSHub 是否运行
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:1200/

# 检查路由是否可用（404=未安装，503=target site unreachable）
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:1200/<route>

# 查看 RSSHub 日志
podman logs rsshub 2>&1 | tail -20
```

常见 503 原因：
- `NotFoundError` → 路由未安装在当前 RSSHub 实例
- `FetchError: getaddrinfo ENOTFOUND` → DNS 解析失败
- 目标网站需 JS 渲染（需 puppeteer，当前未配置）

## 更新 feeds/config.yaml 后验证

```bash
cd ~/wuhoo-workspace/skills/default/wuhoo-news-rss
/usr/bin/python3.11 src/fetcher.py --fetch --category 足球
# 检查输出，确认每个新源都有 ✅ 标记和非零文章数
```
