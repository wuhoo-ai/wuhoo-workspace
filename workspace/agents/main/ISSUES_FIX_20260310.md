# 问题修复指南

**时间**: 2026-03-10 17:47 GMT+8

---

## 问题 1：main 会话消息发到钉钉

### 🔍 问题描述

在 main 会话（WebChat）中的对话，回复消息被发送到了钉钉会话。

### 📋 原因分析

**当前配置**:
```json
{
  "dingtalk": {
    "enabled": true,
    "dmPolicy": "open",
    "allowFrom": ["*"],
    "requireMention": false
  }
}
```

**问题根源**:
- `allowFrom: ["*"]` - 允许所有用户
- `dmPolicy: "open"` - 私聊开放
- 没有配置 `bindings` 路由规则

导致所有渠道的消息都可能路由到钉钉。

### ✅ 解决方案

#### 方案 A：限制钉钉允许的用户（推荐）

```json
{
  "dingtalk": {
    "enabled": true,
    "allowFrom": ["01443329476136537748"],  // 只允许你的钉钉 ID
    "dmPolicy": "open",
    "requireMention": false
  }
}
```

#### 方案 B：配置 Agent Binding（精细控制）

```json
{
  "dingtalk": {
    "enabled": true,
    "allowFrom": ["*"],
    "bindings": [
      {
        "peer": "01443329476136537748",
        "agentId": "main"
      }
    ]
  },
  "webchat": {
    "enabled": true,
    "allowFrom": ["*"],
    "bindings": [
      {
        "peer": "*",
        "agentId": "main"
      }
    ]
  }
}
```

#### 方案 C：关闭钉钉私聊（仅群聊）

```json
{
  "dingtalk": {
    "enabled": true,
    "dmPolicy": "closed",  // 关闭私聊
    "groupPolicy": "open", // 仅开放群聊
    "allowFrom": ["*"]
  }
}
```

### 🔧 推荐配置

根据你的需求（专属使用）：

```json
{
  "channels": {
    "dingtalk": {
      "enabled": true,
      "allowFrom": ["01443329476136537748"],  // 只允许你
      "dmPolicy": "open",
      "groupPolicy": "closed",
      "requireMention": false
    },
    "wecom": {
      "enabled": true,
      "allowFrom": ["haohaijiao"],  // 只允许你
      "dmPolicy": "open",
      "groupPolicy": "closed"
    },
    "webchat": {
      "enabled": true,
      "allowFrom": ["*"],  // WebChat 开放
      "dmPolicy": "open"
    }
  }
}
```

---

## 问题 2：clawhub 显示 blocked，新 Skills 看不到

### 🔍 问题描述

- Skills 页面显示 clawhub 为 "blocked" 状态
- 新安装的 file-search 和 web-search-pro 刷新后看不到

### 📋 原因分析

**从 `openclaw skills check` 输出**:
```
Total: 52
✓ Eligible: 3
🚫 Blocked by allowlist: 49
✗ Missing requirements: 0

Ready to use:
  📦 clawhub
  🌤️ weather
  📦 find-skills
```

**分析**:
1. **clawhub 是 ready 状态**，不是 blocked
2. **49 个 Skills 被 blocked** - 这是因为 `plugins.allow` 未配置
3. **新 Skills 可能未被识别** - 需要刷新缓存

### ✅ 解决方案

#### 1. 配置 plugins.allow

```json
{
  "plugins": {
    "allow": ["channels", "memory-core", "device-pair", "phone-control", "talk-voice"]
  }
}
```

#### 2. 刷新 Skills 缓存

```bash
# 方法 A：重启 Gateway（推荐）
openclaw gateway restart

# 方法 B：清除缓存（如果支持）
rm -rf ~/.openclaw/cache/skills
```

#### 3. 检查 Skills 格式

确保 SKILL.md 格式正确：
```markdown
# skill-name Skill

## 描述
技能描述...

## 使用方式
```bash
exec command...
```
```

### 🔧 完整修复步骤

**步骤 1**: 更新 openclaw.json
```json
{
  "plugins": {
    "allow": [
      "channels",
      "memory-core",
      "device-pair",
      "phone-control",
      "talk-voice"
    ]
  }
}
```

**步骤 2**: 重启 Gateway
```bash
openclaw gateway restart
```

**步骤 3**: 验证
```bash
openclaw skills check
openclaw skills list | grep -E "clawhub|file-search|web-search-pro"
```

---

## 📝 配置备份

### 当前配置备份

```bash
# 备份当前配置
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup.$(date +%Y%m%d_%H%M%S)
```

### 推荐完整配置

```json
{
  "channels": {
    "dingtalk": {
      "enabled": true,
      "clientId": "${DINGTALK_CLIENT_ID}",
      "clientSecret": "${DINGTALK_CLIENT_SECRET}",
      "robotCode": "${DINGTALK_ROBOT_CODE}",
      "corpId": "${DINGTALK_CORP_ID}",
      "agentId": 4314706415,
      "dmPolicy": "open",
      "groupPolicy": "closed",
      "messageType": "markdown",
      "showThinking": true,
      "allowFrom": ["01443329476136537748"],
      "requireMention": false
    },
    "wecom": {
      "enabled": true,
      "mode": "ws",
      "botId": "${WECOM_BOT_ID}",
      "secret": "${WECOM_SECRET}",
      "dmPolicy": "open",
      "groupPolicy": "closed",
      "messageType": "markdown",
      "showThinking": true,
      "allowFrom": ["haohaijiao"],
      "requireMention": false
    },
    "webchat": {
      "enabled": true,
      "dmPolicy": "open",
      "allowFrom": ["*"]
    }
  },
  "plugins": {
    "allow": [
      "channels",
      "memory-core",
      "device-pair",
      "phone-control",
      "talk-voice"
    ]
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "bailian/qwen3.5-plus"
      }
    },
    "list": [
      {
        "id": "main",
        "workspace": "/home/admin/.openclaw/workspace/agents/main",
        "model": {
          "primary": "bailian/qwen3.5-plus",
          "fallbacks": ["bailian/MiniMax-M2.5"]
        },
        "tools": {
          "allow": [
            "read",
            "edit",
            "write",
            "web_search",
            "web_fetch",
            "clawhub",
            "message",
            "exec",
            "file-search",
            "web-search-pro"
          ],
          "exec": {
            "node": "local"
          }
        }
      }
    ]
  }
}
```

---

## 🧪 验证步骤

### 验证问题 1 修复

1. 在 WebChat 发送消息
2. 确认回复只在 WebChat 显示
3. 钉钉不会收到消息

### 验证问题 2 修复

```bash
# 检查 Skills 状态
openclaw skills check

# 检查新 Skills
openclaw skills list | grep -E "file-search|web-search-pro"

# 测试 Skills
# 在对话中：
# "帮我搜索包含 trading 的文件"
# "搜索最新的 AI 新闻"
```

---

## 📚 参考资源

| 资源 | 链接 |
|------|------|
| Skills 文档 | https://docs.openclaw.ai/skills |
| Plugins 文档 | https://docs.openclaw.ai/plugins |
| CLI 参考 | https://docs.openclaw.ai/cli |

---

**文档结束**
