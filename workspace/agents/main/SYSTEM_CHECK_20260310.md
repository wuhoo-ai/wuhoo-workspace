# OpenClaw 系统检查报告

**检查时间**: 2026-03-10 15:41 GMT+8  
**版本**: v2026.3.8  
**状态**: ✅ 运行正常

---

## 📊 系统状态总览

| 项目 | 状态 | 详情 |
|------|------|------|
| **Gateway** | 🟢 运行中 | PID 594998, 端口 18789 |
| **版本** | ✅ v2026.3.8 | 已更新 |
| **Dashboard** | ✅ 可访问 | http://172.20.53.18:18789/ |
| **Channels** | ✅ 2 个已启用 | 钉钉 + 企业微信 |
| **Agents** | ✅ 3 个 | main, dev, trade |
| **Skills** | ✅ 54 个 | 2 个新增 |
| **Plugins** | ✅ 5/39 已加载 | |

---

## ⚠️ 配置警告

| 警告 | 影响 | 建议 |
|------|------|------|
| `GATEWAY_AUTH_TOKEN` 未配置 | 部分认证功能不可用 | 可选配置 |

---

## 📦 Channels 配置

### 已启用 (2)

| 渠道 | 状态 | 配置 |
|------|------|------|
| **钉钉** | ✅ | 企业应用模式 |
| **企业微信** | ✅ | WebSocket 模式 |

### 钉钉配置
```json
{
  "enabled": true,
  "clientId": "${DINGTALK_CLIENT_ID}",
  "clientSecret": "${DINGTALK_CLIENT_SECRET}",
  "robotCode": "${DINGTALK_ROBOT_CODE}",
  "corpId": "${DINGTALK_CORP_ID}",
  "agentId": 4314706415,
  "dmPolicy": "open",
  "groupPolicy": "closed",
  "allowFrom": ["*"]
}
```

### 企业微信配置
```json
{
  "enabled": true,
  "mode": "ws",
  "botId": "${WECOM_BOT_ID}",
  "secret": "${WECOM_SECRET}",
  "dmPolicy": "open"
}
```

---

## 🤖 Agents 配置

### 工作区 Agents (3)

| Agent | 工作区 | 用途 |
|-------|--------|------|
| **main** | `~/.openclaw/workspace/agents/main` | 主对话 Agent |
| **dev** | `~/.openclaw/workspace/agents/dev` | 开发助手 |
| **trade** | `~/.openclaw/workspace/agents/trade` | 交易助手 |

### 默认模型配置
- **主模型**: `bailian/qwen3.5-plus`
- **可用模型**: 8 个 (通义千问系列 + MiniMax + GLM + Kimi)

---

## 🛠️ Skills 清单

### 总数：54 个

### 最近新增 (2)

| Skill | 添加时间 | 用途 |
|-------|----------|------|
| **jina_search** | 2026-03-09 | Jina AI 搜索 (付费 API) |
| **tushare_search** | 2026-03-09 | Tushare 股票数据 (2120 积分) |

### 常用 Skills 分类

#### 搜索与信息
- `jina_search` - Jina AI 搜索
- `weather` - 天气查询
- `summarize` - 内容摘要

#### 笔记与知识管理
- `notion` - Notion 集成
- `obsidian` - Obsidian 集成
- `bear-notes` - Bear Notes
- `apple-notes` - Apple Notes
- `apple-reminders` - Apple Reminders

#### 通讯与渠道
- `discord` - Discord
- `slack` - Slack
- `telegram` - Telegram
- `whatsapp` - WhatsApp

#### 媒体与创作
- `sag` - ElevenLabs TTS
- `openai-whisper` - 语音转文字
- `openai-image-gen` - 图像生成
- `video-frames` - 视频帧提取

#### 工具与系统
- `github` - GitHub 集成
- `ordercli` - 订单管理
- `healthcheck` - 健康检查
- `tmux` - Tmux 集成

#### 其他
- `things-mac` - Things 任务管理
- `sonoscli` - Sonos 音响
- `spotify-player` - Spotify
- `songsee` - 歌曲识别

---

## 🔌 Plugins (Extensions)

### 已加载 (5/39)

| 插件 | ID | 状态 | 说明 |
|------|-----|------|------|
| **Moltbot China Channels** | channels | ✅ loaded | 钉钉/飞书/企微/QQ |
| **Device Pairing** | device-pair | ✅ loaded | 设备配对 |
| **Memory (Core)** | memory-core | ✅ loaded | 文件记忆搜索 |
| **Phone Control** | phone-control | ✅ loaded | 手机控制 |
| **Talk Voice** | talk-voice | ✅ loaded | 语音选择 |

### 可用但未加载 (部分)

| 插件 | ID | 用途 |
|------|-----|------|
| Feishu | feishu | 飞书渠道 |
| Telegram | telegram | Telegram 渠道 |
| WhatsApp | whatsapp | WhatsApp 渠道 |
| Discord | discord | Discord 渠道 |
| Slack | slack | Slack 渠道 |
| Memory LanceDB | memory-lancedb | 向量数据库记忆 |

---

## 🔑 环境变量

### 已配置

| 服务 | 变量 | 状态 |
|------|------|------|
| **钉钉** | `DINGTALK_CLIENT_ID` 等 | ✅ 已配置 |
| **企业微信** | `WECOM_BOT_ID` 等 | ✅ 已配置 |
| **Jina AI** | `JINA_API_KEY` | ✅ 已配置 (付费) |
| **Tushare** | `TUSHARE_TOKEN` | ✅ 已配置 (2120 积分) |

### 未配置 (可选)

| 变量 | 用途 | 建议 |
|------|------|------|
| `GATEWAY_AUTH_TOKEN` | Gateway 认证 | 可选 |

---

## 📂 目录结构

```
~/.openclaw/
├── openclaw.json          # 主配置
├── .env                   # 环境变量
├── workspace/
│   ├── agents/
│   │   ├── main/         # 主 Agent
│   │   ├── dev/          # 开发 Agent
│   │   └── trade/        # 交易 Agent
│   └── projects/
│       └── AI-Trader/    # AI 交易项目
└── skills/               # 54 个 Skills
```

---

## 🎯 下一步计划

### 1. Skills 整理
- [ ] 清理未使用的 Skills
- [ ] 为新项目创建专用 Skills
- [ ] 更新 Skills 文档

### 2. Extensions 配置
- [ ] 评估需要启用的 Plugins
- [ ] 配置 Feishu (可选)
- [ ] 配置 Telegram (可选)

### 3. PaperPodcast 项目
- [ ] 创建专用 Agent
- [ ] 配置专用 Skills
- [ ] 设置访问控制

---

## 📝 备注

- Gateway 运行正常，无关键错误
- 日志显示 WebSocket 心跳正常
- 企业微信 WebSocket 连接正常
- 所有核心功能可用

---

**报告生成时间**: 2026-03-10 15:45 GMT+8
