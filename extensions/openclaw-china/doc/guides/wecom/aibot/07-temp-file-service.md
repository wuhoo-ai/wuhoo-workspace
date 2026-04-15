# 企业微信智能机器人：插件内置临时文件服务（实践说明）

## 目标

在 `wecom` 智能机器人场景中，把本地文件路径（如 `~/.openclaw/media/inbound/report.pdf`）转换为可下载的临时公网链接，再通过 Markdown 发送给用户。

这是当前插件用于“文件可达性”的核心方案。

## 为什么这么做

企业微信智能机器人在我们当前实现中采用 `stream-first` 路径，消息工具主要走流式追加。为保证文件能被用户下载，插件会将“本地路径”转成临时 URL，并发成 Markdown：

- 文件：`[下载文件](URL)`
- 图片：`![](URL)`

相关实现：

- `extensions/wecom/src/outbound-reply.ts`
- `extensions/wecom/src/channel.ts`
- `extensions/wecom/src/bot.ts`
- `extensions/wecom/src/monitor.ts`

## 核心机制

### 1) 记录公网基地址

插件在收到企业微信回调时，记录当前账号的公网基地址（`https://host`）：

- 优先 `x-forwarded-host` + `x-forwarded-proto`
- 其次 `Host` + socket 是否 TLS

实现：`rememberAccountPublicBaseUrl` in `extensions/wecom/src/outbound-reply.ts`

### 2) 注册临时文件条目

当需要发送本地文件时，插件会：

1. 校验本地文件存在
2. 生成随机 `id` + `token`
3. 以 15 分钟 TTL 放入内存表

实现：`registerTempLocalMedia` in `extensions/wecom/src/outbound-reply.ts`

### 3) 生成临时 URL

URL 形态：

`{baseUrl}/wecom-media/{id}/{filename}?token={token}`

实现：`buildTempMediaUrl` in `extensions/wecom/src/outbound-reply.ts`

### 4) 提供下载路由

网关会先拦截并处理 `/wecom-media/...` 请求：

- 仅允许 `GET`
- 校验 `id + token`
- 命中后读文件并回包（含 `Content-Type`）
- 过期/无效直接 `404`

实现：`handleTempMediaRequest` in `extensions/wecom/src/outbound-reply.ts`，入口在 `extensions/wecom/src/monitor.ts`

## 两种实际触发路径

### A. `message` 工具显式发媒体

`sendMedia` 接到本地路径后，会自动转为临时 URL，然后拼成 Markdown 追加到活动流。

实现：`sendMedia` in `extensions/wecom/src/channel.ts`

### B. 模型输出里出现本地文件路径

流式 `deliver` 会对文本做媒体抽取，识别本地路径/链接，自动转换成可访问 URL，再渲染为 Markdown。

实现：`normalizeChunkForWecomStream` in `extensions/wecom/src/bot.ts`

## 最小实践步骤（可直接照做）

1. 确保企业微信回调可达，并且网关已收到至少一条该账号的入站消息（用于记录公网基地址）。
2. 确保反向代理正确传递 `x-forwarded-host` 和 `x-forwarded-proto`。
3. 让模型或工具产出本地绝对路径文件（如 `~/.openclaw/media/inbound/report.pdf`）。
4. 由插件将本地文件注册为临时资源，并生成 `/wecom-media/...?...` 链接。
5. 插件把链接包装为 Markdown 回给用户：
   - 图片：`![](url)`
   - 文件：`[下载文件](url)`
6. 用户点击链接下载；若超过 TTL 或服务重启导致条目丢失，重新触发一次发送即可生成新链接。

## 部署实践建议

1. 反向代理必须正确传递 `x-forwarded-host` / `x-forwarded-proto`。  
2. `/wecom-media/*` 必须公网可访问，且与 webhook 使用同一对外域名更稳。  
3. 这是“进程内内存路由”：
   - 重启后旧链接失效
   - 多实例时建议粘性会话，或改为对象存储方案  
4. 临时链接默认 15 分钟有效，过期后会 `404`。  

## 常见问题

### `No public base URL captured yet for this account`

说明插件尚未记录到该账号的公网基地址。先确保该账号已收到至少一次有效回调，并检查代理头。

### 用户点击链接 404

常见原因：

- 链接过期（>15 分钟）
- 网关重启导致内存条目丢失
- token 不匹配
- 目标文件被移动/删除

### 文本里还是本地路径，没有变链接

说明媒体映射失败，通常是：

- 无公网基地址
- 文件不存在
- 不是绝对路径且也不是 HTTP URL

## 结论

当前 `wecom` 插件的“文件发送可达性”不是依赖企业微信原生 `file` 主动回复，而是依赖插件内置临时文件服务 + Markdown 链接回传。  
这套方案已可用，适合“先保证用户可下载/可查看”的目标。
