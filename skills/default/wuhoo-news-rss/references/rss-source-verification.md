# RSS 源验证方法

> 2026-06-18, from WC2026 football predictor v5.0 RSS source expansion session.

## 系统性路由测试流程

当需要验证新的 RSS/RSSHub 源是否可用时：

### Step 1: 检查 RSSHub 运行状态

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:1200
# 期望: 200
```

### Step 2: 批量测试路由 HTTP 状态

```bash
# 对每个候选路由测试 HTTP code + 内容大小
for url in \
  "http://127.0.0.1:1200/dongqiudi/daily" \
  "http://127.0.0.1:1200/hupu/bbs/34" \
  "http://127.0.0.1:1200/zhibo8/more"; do
  code=$(curl -sL -o /dev/null -w "%{http_code}" --max-time 15 "$url")
  bytes=$(curl -sL --max-time 15 "$url" 2>/dev/null | wc -c)
  echo "$code | $bytes bytes | $url"
done
```

### Step 3: 利用 RSSHub Debug Info 发现可用路由

RSSHub 首页 (`http://127.0.0.1:1200/`) 的 Debug Info 包含 `Hot Routes` 和 `Hot Error Routes` 两个列表，可以快速了解哪些路由被使用过以及哪些路由有问题：

- `Hot Routes`: 高访问量路由 — 通常是可用的
- `Hot Error Routes`: 出错路由 — 可能不可用或需要特定参数

### Step 4: 验证内容质量

对于返回 200 的路由，抽样检查内容：

```bash
curl -sL "http://127.0.0.1:1200/dongqiudi/daily" | head -50
# 检查: 是否返回有效 RSS XML? 内容是否相关? item 数量?
```

### Step 5: 分类结果

| HTTP Code | 含义 | 处理 |
|-----------|------|------|
| 200 | 可用 | 加入 config.yaml |
| 301/302 | 需要跟随重定向 | 用 `-L` 再试 |
| 503 | RSSHub 路由存在但源不可达 | 标记不可用，注释放置 |
| 403/404/405 | 源明确拒绝 | 放弃，注释放置 |
| 000 | 连接失败 (DNS/网络) | 原生源不可达 |

## 已验证的路由状态 (2026-06-18)

### ✅ 可用并已加入配置
- `dongqiudi/daily` — 懂球帝早报, 中文 WC2026 内容, ~168KB/天
- `bbc/sport/football` — BBC RSSHub 路由, WC2026 coverage, ~307KB
- `breakingthelines.com/feed` — 战术分析 (redirect → old.breakingthelines.com)

### ❌ 不可用 (503)
- `dongqiudi/special/:id` — 503
- `dongqiudi/news` — 503  
- `hupu/bbs/:id` — 503
- `zhibo8/more` — 503
- `fifa/news`, `fifa/worldcup`, `fifa/latest`, `fifa/rankings` — 全 503
- `uefa/news` — 503
- `espn/soccer`, `espn/fc` — 503
- `theguardian/football`, `theguardian/worldcup` — RSSHub 路由 503 (但原生 RSS 可用)
- `skysports/football` — RSSHub 路由 503 (但原生 RSS 可用)
- `dailymail/football` — 503
- `goal/news` — 503
- `weibo/search/hot` — 503

### ❌ 不可达
- `zonalmarking.net/feed` — connection refused (exit 7)
- `theathletic.com/feed/football` — 301 → paywall (无 RSS)
- `transfermarkt.com/rss/news` — 405 Method Not Allowed
- `fbref.com` — 403 Forbidden

## 已知陷阱

1. **RSSHub 的 RSS 输出是 XML 但 curl 不加 -L 可能只拿到 HTML wrapper** — 始终用 `-L` 跟随重定向
2. **部分路由需要 URL 参数** — 例如 `dongqiudi/special/1` 503 但 `dongqiudi/daily` 200
3. **RSSHub Debug Info 中的 `Hot Error Routes` 列表很有价值** — 从中可以发现用户试图使用但失败的路由，可作为替代方案的参考
4. **原生 RSS 源和 RSSHub 路由可能返回不同内容** — BBC Sport 原生 RSS 和 RSSHub 路由内容不同，都值得加入
