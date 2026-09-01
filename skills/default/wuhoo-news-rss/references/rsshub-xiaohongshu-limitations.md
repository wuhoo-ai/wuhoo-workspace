# RSSHub 小红书路由说明

## 可用路由

RSSHub 对小红书仅提供 **一条路由**:

```
/xiaohongshu/user/:user_id/:category
```

- `user_id`: 24位字符用户ID
- `category`: `notes` (笔记) 或 `collect` (收藏)

## 前置条件

必须在 RSSHub 容器中配置 `XIAOHONGSHU_COOKIE` 环境变量:

```bash
XIAOHONGSHU_COOKIE="abRequestId=xxx; a1=xxx; webId=xxx; ..."
```

Cookie 获取方式: 浏览器打开 xiaohongshu.com → F12 → Network → 任意 XHR 请求 → Request Headers → Cookie

## 不支持的功能

- ❌ 关键词搜索笔记
- ❌ 热门话题/热搜榜
- ❌ 话题标签聚合
- ❌ 评论内容获取
- ❌ 笔记互动数据（点赞/收藏/评论数仅部分字段）

## 已知稳定性问题

- 反爬机制：频繁请求触发验证码
- GitHub Issues: #19505 (路由停止工作), #14812 (Chrome依赖)
- Cookie 过期需要手动更新
- 建议请求频率: ≤1次/分钟

## 替代方案

对于需要关键词搜索、话题热度、社区情绪的场景，使用 Python 采集方案:
- XHS-Downloader (GitHub: JoeanAmier/XHS-Downloader)
- 直接 HTTP API + Cookie 签名
- web_search site:xiaohongshu.com 兜底
