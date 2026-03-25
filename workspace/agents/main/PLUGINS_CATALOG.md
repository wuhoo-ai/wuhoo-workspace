# OpenClaw Plugins 完整目录

**版本**: v2026.3.8  
**更新时间**: 2026-03-10  
**总数**: 39 个 (5 个已加载，34 个未加载)

---

## 📊 状态总览

| 状态 | 数量 | 说明 |
|------|------|------|
| **已加载** | 5 | 正在运行 |
| **未加载** | 34 | 可用但未启用 |
| **总计** | 39 | 内置插件 |

---

## ✅ 已加载 Plugins (5)

### 1. Moltbot China Channels 🇨🇳
| 属性 | 值 |
|------|-----|
| **ID** | `channels` |
| **版本** | 0.1.0 |
| **状态** | ✅ 已加载 |
| **来源** | `~/.openclaw/extensions/openclaw-china/` |

**功能**:
- 统一渠道包，支持中国本土通讯平台
- 钉钉 (DingTalk) ✅ 已启用
- 飞书 (Feishu/Lark)
- 企业微信 (WeCom) ✅ 已启用
- QQ Bot

**配置入口**:
```json
{
  "channels": {
    "dingtalk": { "enabled": true },
    "wecom": { "enabled": true },
    "feishu": { "enabled": false }
  }
}
```

---

### 2. Device Pairing
| 属性 | 值 |
|------|-----|
| **ID** | `device-pair` |
| **状态** | ✅ 已加载 |

**功能**:
- 生成设备配对码
- 审批设备配对请求
- 管理已连接设备

**用途**: 多设备连接管理

---

### 3. Memory (Core)
| 属性 | 值 |
|------|-----|
| **ID** | `memory-core` |
| **状态** | ✅ 已加载 |

**功能**:
- 文件支持的记忆搜索工具
- CLI 命令行接口
- 基础记忆存储和检索

**用途**: Agent 长期记忆管理

---

### 4. Phone Control
| 属性 | 值 |
|------|-----|
| **ID** | `phone-control` |
| **状态** | ✅ 已加载 |

**功能**:
- 远程手机控制
- 摄像头/屏幕/写入命令
- 可选自动过期

**用途**: 高风险节点手机管理

---

### 5. Talk Voice
| 属性 | 值 |
|------|-----|
| **ID** | `talk-voice` |
| **状态** | ✅ 已加载 |

**功能**:
- 管理 Talk 语音选择
- 列出可用语音
- 设置首选语音

**用途**: TTS 语音管理

---

## 📦 渠道类 Plugins (18)

### 即时通讯

| 插件 | ID | 状态 | 功能 |
|------|-----|------|------|
| **Discord** | `discord` | ⏸️ | Discord 渠道集成 |
| **Slack** | `slack` | ⏸️ | Slack 渠道集成 |
| **Telegram** | `telegram` | ⏸️ | Telegram 渠道集成 |
| **WhatsApp** | `whatsapp` | ⏸️ | WhatsApp 渠道集成 |
| **Signal** | `signal` | ⏸️ | Signal 加密消息 |
| **LINE** | `line` | ⏸️ | LINE 渠道 (日本/台湾) |
| **Matrix** | `matrix` | ⏸️ | Matrix 去中心化消息 |
| **Nostr** | `nostr` | ⏸️ | Nostr NIP-04 加密 DM |

### 企业协作

| 插件 | ID | 状态 | 功能 |
|------|-----|------|------|
| **Feishu/Lark** | `feishu` | ⏸️ | 飞书/李卡渠道 |
| **Microsoft Teams** | `msteams` | ⏸️ | Teams 企业协作 |
| **Google Chat** | `googlechat` | ⏸️ | Google Chat 集成 |
| **Nextcloud Talk** | `nextcloud-talk` | ⏸️ | Nextcloud 私有云 |
| **Synology Chat** | `synology-chat` | ⏸️ | 群晖 Chat |

### 其他渠道

| 插件 | ID | 状态 | 功能 |
|------|-----|------|------|
| **iMessage** | `imessage` | ⏸️ | Apple iMessage |
| **BlueBubbles** | `bluebubbles` | ⏸️ | BlueBubbles (Android 用 iMessage) |
| **IRC** | `irc` | ⏸️ | IRC 聊天协议 |
| **Twitch** | `twitch` | ⏸️ | Twitch 直播聊天 |
| **Zalo** | `zalo` | ⏸️ | Zalo (越南) |
| **Zalo User** | `zalouser` | ⏸️ | Zalo 个人账号 |

---

## 🧠 记忆与存储 Plugins (2)

| 插件 | ID | 状态 | 功能 |
|------|-----|------|------|
| **Memory (Core)** | `memory-core` | ✅ | 文件记忆 (已加载) |
| **Memory LanceDB** | `memory-lancedb` | ⏸️ | 向量数据库记忆 |

**区别**:
- `memory-core`: 基于文件，简单快速
- `memory-lancedb`: 基于向量数据库，支持语义搜索

---

## 🔐 认证与授权 Plugins (5)

| 插件 | ID | 状态 | 功能 |
|------|-----|------|------|
| **Google Gemini CLI Auth** | `google-gemini-cli-auth` | ⏸️ | Gemini OAuth 认证 |
| **MiniMax Portal Auth** | `minimax-portal-auth` | ⏸️ | MiniMax OAuth |
| **Qwen Portal Auth** | `qwen-portal-auth` | ⏸️ | 通义千问 OAuth |
| **Copilot Proxy** | `copilot-proxy` | ⏸️ | GitHub Copilot 代理 |
| **ACPX Runtime** | `acpx` | ⏸️ | ACP 运行时后端 |

---

## 🛠️ 工具与功能 Plugins (7)

| 插件 | ID | 状态 | 功能 |
|------|-----|------|------|
| **LLM Task** | `llm-task` | ⏸️ | JSON 结构化任务工具 |
| **Lobster** | `lobster` | ⏸️ | 可恢复审批的工作流工具 |
| **Diffs** | `diffs` | ⏸️ | 只读差异查看器 |
| **OpenProse** | `open-prose` | ⏸️ | VM 技能包，/prose 命令 |
| **Diagnostics OTel** | `diagnostics-otel` | ⏸️ | OpenTelemetry 诊断导出 |
| **Thread Ownership** | `thread-ownership` | ⏸️ | Slack 线程防重复回复 |
| **Phone Control** | `phone-control` | ✅ | 手机控制 (已加载) |

---

## 📋 按用途分类

### 推荐启用的 Plugins

| 优先级 | 插件 | 用途 | 建议 |
|--------|------|------|------|
| 🔴 高 | `telegram` | Telegram 渠道 | 国际用户推荐 |
| 🔴 高 | `feishu` | 飞书渠道 | 国内企业推荐 |
| 🟡 中 | `memory-lancedb` | 向量记忆 | 需要语义搜索 |
| 🟡 中 | `slack` | Slack 渠道 | 海外团队 |
| 🟢 低 | `discord` | Discord 渠道 | 社区运营 |

### 可选的 Plugins

| 插件 | 适用场景 |
|------|----------|
| `whatsapp` | 需要 WhatsApp 业务 |
| `line` | 面向日本/台湾用户 |
| `msteams` | 企业使用 Teams |
| `googlechat` | 使用 Google Workspace |
| `signal` | 需要端到端加密 |

### 开发相关的 Plugins

| 插件 | 用途 |
|------|------|
| `copilot-proxy` | GitHub Copilot 集成 |
| `llm-task` | 结构化 LLM 任务 |
| `diagnostics-otel` | 性能监控 |

---

## 🌐 渠道覆盖地图

```
亚洲:
  🇨🇳 钉钉 ✅ (China Channels)
  🇨🇳 企业微信 ✅ (China Channels)
  🇨🇳 飞书 ⏸️ (feishu)
  🇯🇵 LINE ⏸️ (line)
  🇻🇳 Zalo ⏸️ (zalo)

欧美:
  🌍 Telegram ⏸️ (telegram)
  🌍 WhatsApp ⏸️ (whatsapp)
  🇺🇸 Slack ⏸️ (slack)
  🇺🇸 Discord ⏸️ (discord)
  🇺🇸 iMessage ⏸️ (imessage)

企业:
  🏢 Microsoft Teams ⏸️ (msteams)
  🏢 Google Chat ⏸️ (googlechat)
  🏢 Nextcloud Talk ⏸️ (nextcloud-talk)

加密:
  🔐 Signal ⏸️ (signal)
  🔐 Nostr ⏸️ (nostr)

其他:
  💬 IRC ⏸️ (irc)
  🎮 Twitch ⏸️ (twitch)
```

---

## 📥 获取 Plugins 的途径

### 1. 内置 Plugins (39 个)

**位置**: `~/.openclaw/extensions/stock/`

**启用方式**:
```bash
# 启用插件
openclaw plugins enable <plugin-id>

# 禁用插件
openclaw plugins disable <plugin-id>

# 查看状态
openclaw plugins list
```

**配置**:
```json
{
  "plugins": {
    "allow": ["channels", "telegram", "memory-core"]
  }
}
```

### 2. ClawHub (社区市场)

**访问**: https://clawhub.com

**使用方式**:
```bash
# 浏览可用插件
openclaw clawhub list

# 安装插件
openclaw clawhub install <plugin-name>

# 搜索插件
openclaw clawhub search <keyword>
```

### 3. npm Registry

**适用**: 第三方开发的插件

**安装**:
```bash
openclaw plugins install @openclaw/telegram
openclaw plugins install @openclaw/slack
```

### 4. 本地开发

**开发流程**:
```bash
# 创建插件
mkdir -p ~/openclaw/extensions/my-plugin
cd ~/openclaw/extensions/my-plugin

# 开发完成后配置
# 在 openclaw.json 中添加:
{
  "extensions": ["~/openclaw/extensions/my-plugin"]
}
```

---

## 🔧 管理 Plugins

### 查看状态
```bash
# 列出所有插件
openclaw plugins list

# 查看已加载
openclaw plugins list --loaded

# 查看详细信息
openclaw plugins info <plugin-id>
```

### 启用/禁用
```bash
# 启用
openclaw plugins enable telegram

# 禁用
openclaw plugins disable discord

# 重启网关生效
openclaw gateway restart
```

### 安装/卸载
```bash
# 安装
openclaw plugins install @openclaw/telegram

# 卸载
openclaw plugins uninstall @openclaw/telegram
```

---

## 📝 配置示例

### 启用 Telegram 渠道

**1. 启用插件**:
```bash
openclaw plugins enable telegram
```

**2. 配置 openclaw.json**:
```json
{
  "plugins": {
    "allow": ["channels", "telegram"]
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "${TELEGRAM_BOT_TOKEN}"
    }
  }
}
```

**3. 配置 .env**:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

**4. 重启网关**:
```bash
openclaw gateway restart
```

---

## 🎯 推荐配置方案

### 国内用户推荐
```json
{
  "plugins": {
    "allow": ["channels", "memory-core"]
  },
  "channels": {
    "dingtalk": { "enabled": true },
    "wecom": { "enabled": true },
    "feishu": { "enabled": false }
  }
}
```

### 国际用户推荐
```json
{
  "plugins": {
    "allow": ["channels", "telegram", "slack", "memory-core"]
  },
  "channels": {
    "telegram": { "enabled": true },
    "slack": { "enabled": true },
    "discord": { "enabled": false }
  }
}
```

### 企业用户推荐
```json
{
  "plugins": {
    "allow": ["channels", "msteams", "memory-lancedb"]
  },
  "channels": {
    "dingtalk": { "enabled": true },
    "wecom": { "enabled": true },
    "msteams": { "enabled": true }
  }
}
```

---

## 📚 参考资源

| 资源 | 链接 |
|------|------|
| **OpenClaw 文档** | https://docs.openclaw.ai |
| **ClawHub** | https://clawhub.com |
| **GitHub** | https://github.com/openclaw/openclaw |
| **插件 SDK** | https://docs.openclaw.ai/plugins |
| **社区 Discord** | https://discord.gg/clawd |

---

**文档结束**
