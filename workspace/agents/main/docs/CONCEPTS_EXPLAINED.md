# OpenClaw 核心概念详解

**版本**: 2026-03-13  
**目的**: 理清 Session、Channel、Agent 的关系与隔离

---

## 📊 核心概念图解

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户设备                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  DingTalk   │  │  WeCom      │  │  WebChat    │  ...        │
│  │  (Channel)  │  │  (Channel)  │  │  (Channel)  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Gateway (消息网关)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Session Manager (会话管理器)                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │ Session A    │  │ Session B    │  │ Session C    │   │  │
│  │  │ user:main    │  │ user:dev     │  │ user:trade   │   │  │
│  │  │ (私聊会话)   │  │ (私聊会话)   │  │ (私聊会话)   │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Pool (代理池)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ main-agent   │  │ dev-agent    │  │ trade-agent  │         │
│  │ qwen3.5-plus │  │coder-next    │  │qwen3.5-plus  │         │
│  │ (对话/路由)  │  │ (代码开发)   │  │ (量化交易)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Workspace (工作空间)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ main/        │  │ dev/         │  │ trade/       │         │
│  │ - SOUL.md    │  │ - SOUL.md    │  │ - SOUL.md    │         │
│  │ - TOOLS.md   │  │ - TOOLS.md   │  │ - TOOLS.md   │         │
│  │ - memory/    │  │ - memory/    │  │ - memory/    │         │
│  │ - skills/    │  │ - skills/    │  │ - skills/    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1️⃣ Channel (通道)

### 定义
**Channel** 是消息的**输入/输出通道**，连接用户设备和 OpenClaw 系统。

### 当前配置
```json
{
  "channels": {
    "dingtalk": {
      "enabled": true,
      "dmPolicy": "open",      // 私聊策略
      "groupPolicy": "closed", // 群聊策略
      "messageType": "markdown"
    },
    "wecom": {
      "enabled": true,
      "dmPolicy": "open",
      "groupPolicy": "closed",
      "messageType": "markdown"
    }
  }
}
```

### 关键配置

| 配置项 | 含义 | 可选值 |
|--------|------|--------|
| `enabled` | 是否启用 | `true` / `false` |
| `dmPolicy` | 私聊消息策略 | `open` (接收所有) / `closed` (仅白名单) |
| `groupPolicy` | 群聊消息策略 | `open` / `closed` / `mention` (仅@) |
| `messageType` | 消息格式 | `markdown` / `text` |

### 工作原理

```
用户发送消息
    ↓
Channel 接收 (DingTalk/WeCom)
    ↓
验证 dmPolicy/groupPolicy
    ↓
转发到 Gateway
    ↓
创建/更新 Session
```

### 示例场景

**场景 1: 用户在 DingTalk 私聊**
```
用户 (DingTalk) → Channel:dingtalk → Session:user:main → main-agent
```

**场景 2: 用户在微信群聊 (@机器人)**
```
用户 (WeCom 群) → Channel:wecom → 检查 groupPolicy:mention → Session:group:xxx → main-agent
```

---

## 2️⃣ Session (会话)

### 定义
**Session** 是**对话上下文**，保存用户与 Agent 的对话历史、记忆和状态。

### 会话隔离机制

#### 当前配置：`dmScope: main`
```json
{
  "session": {
    "dmScope": "main"  // 所有私聊都路由到 main-agent
  }
}
```

#### 会话 Key 生成规则

```
Session Key = {scope}:{channel}:{account}:{peer}

示例:
- main:dingtalk:corp123:user456  (main-agent 的 DingTalk 私聊会话)
- main:wecom:corp123:user456     (main-agent 的 WeCom 私聊会话)
```

### dmScope 配置详解

| dmScope 值 | 含义 | 会话隔离 |
|-----------|------|---------|
| `main` | 所有私聊固定路由到 main-agent | ❌ 无隔离 (所有私聊共享 main 会话) |
| `channel` | 按 Channel 隔离 | ⚠️ 中等隔离 (DingTalk 和 WeCom 分开) |
| `account` | 按账号隔离 | ⚠️ 中等隔离 (不同企业微信账号分开) |
| `per-channel-peer` | 按 Channel+ 用户隔离 | ✅ 完全隔离 (每个用户在每个 Channel 独立会话) |

### 当前会话状态

```bash
# 查看活跃会话
openclaw status

# 输出示例:
Sessions: 6 active · default qwen3.5-plus (1000k ctx) · 3 stores
```

### 会话生命周期

```
创建会话
    ↓
保存对话历史 (memory)
    ↓
更新上下文 (context)
    ↓
空闲超时 (默认 1 小时)
    ↓
会话归档/清理
```

---

## 3️⃣ Agent (代理)

### 定义
**Agent** 是**AI 助手实例**，有独立的模型、工具、工作空间和人格定义。

### 当前 Agent 配置

| Agent | 模型 | 职责 | Workspace |
|-------|------|------|-----------|
| **main** | qwen3.5-plus | 用户对话、任务路由 | `~/.openclaw/workspace/agents/main/` |
| **dev** | qwen3-coder-next | 代码开发 | `~/.openclaw/workspace/agents/dev/` |
| **trade** | qwen3.5-plus | 量化交易 | `~/.openclaw/workspace/agents/trade/` |

### Agent 隔离机制

每个 Agent 完全独立：

```
main-agent
├── 模型：qwen3.5-plus
├── 工具：17 个 (read, edit, web_search, message...)
├── Workspace: ~/.openclaw/workspace/agents/main/
│   ├── SOUL.md (人格定义)
│   ├── TOOLS.md (工具说明)
│   ├── memory/ (记忆文件)
│   └── skills/ (专属技能)
└── Sessions: 多个 (不同 Channel/用户)

dev-agent
├── 模型：qwen3-coder-next
├── 工具：13 个 (read, edit, exec, github, coding-agent...)
├── Workspace: ~/.openclaw/workspace/agents/dev/
└── Sessions: 多个

trade-agent
├── 模型：qwen3.5-plus
├── 工具：15 个 (read, edit, web_search, jina_search...)
├── Workspace: ~/.openclaw/workspace/agents/trade/
└── Sessions: 多个
```

### Agent 切换方式

**方式 1: 显式指定**
```bash
openclaw agent --agent dev --message "帮我写代码"
```

**方式 2: 路由规则** (需要配置 routing bindings)
```bash
# 绑定 dev 到特定 Channel
openclaw agents bind --agent dev --bind telegram:dev-channel
```

**方式 3: 会话内切换** (需要应用层实现)
```
用户：/use dev
Bot: 已切换到 dev-agent

用户：帮我写个函数
dev-agent: 好的...
```

---

## 🔄 三者关系总结

### 消息流转

```
用户消息
    ↓
Channel (接收消息)
    ↓
Gateway (验证 dmPolicy/groupPolicy)
    ↓
Session Manager (创建/更新会话)
    ↓
Router (根据 dmScope 决定 Agent)
    ↓
Agent (处理消息)
    ↓
Session (保存对话历史)
    ↓
Channel (发送回复)
    ↓
用户收到回复
```

### 隔离级别

| 维度 | 隔离级别 | 说明 |
|------|---------|------|
| **Channel 之间** | ✅ 完全隔离 | DingTalk 和 WeCom 的消息互不影响 |
| **Agent 之间** | ✅ 完全隔离 | main/dev/trade 有独立的工作空间和记忆 |
| **Session 之间** | ⚠️ 取决于 dmScope | `dmScope: main` 时所有私聊共享 main 会话 |

### 数据归属

| 数据类型 | 归属 | 存储位置 |
|---------|------|---------|
| Channel 配置 | 全局 | `~/.openclaw/openclaw.json` |
| Session 数据 | 会话级 | `~/.openclaw/agents/{agent}/sessions/` |
| Agent 配置 | Agent 级 | `~/.openclaw/openclaw.json` + `~/.openclaw/workspace/agents/{agent}/` |
| Memory 文件 | Agent 级 | `~/.openclaw/workspace/agents/{agent}/memory/` |
| 技能 | Agent 级 | `~/.openclaw/workspace/agents/{agent}/skills/` + `~/.agents/skills/` |

---

## 🎯 你的当前配置分析

### 当前配置
```json
{
  "session": {
    "dmScope": "main"  // ⚠️ 所有私聊都到 main-agent
  },
  "channels": {
    "dingtalk": { "dmPolicy": "open" },
    "wecom": { "dmPolicy": "open" }
  },
  "agents": ["main", "dev", "trade"]
}
```

### 这意味着什么？

**场景 1: 用户在 DingTalk 私聊**
```
用户 (DingTalk) → Channel:dingtalk → Session:main → main-agent
```
✅ 正常工作

**场景 2: 用户在 WeCom 私聊**
```
用户 (WeCom) → Channel:wecom → Session:main → main-agent
```
✅ 正常工作

**场景 3: 想用 dev-agent 写代码**
```
方式 A: main-agent 内部路由
用户："帮我写个函数"
main-agent: "这个问题 dev-agent 更擅长，我来转交"
→ main 调用 dev 处理，然后汇总结果

方式 B: 显式指定
用户：(通过控制台) openclaw agent --agent dev --message "帮我写代码"
→ 直接使用 dev-agent
```

### 当前限制

由于 `dmScope: main`：
- ❌ 无法在 DingTalk/WeCom 上直接切换到 dev/trade
- ✅ 所有消息都通过 main-agent 统一处理
- ✅ main 可以内部路由到 dev/trade

---

## 🛠️ 配置建议

### 方案 A: 保持现状 (推荐)

**配置**: `dmScope: main`

**优点**:
- ✅ 统一管理，用户体验一致
- ✅ main 可以智能路由到 dev/trade
- ✅ 会话状态简单，易于维护

**缺点**:
- ❌ 无法直接在 Channel 上切换 Agent
- ❌ 所有消息都经过 main，增加延迟

**适用场景**: 个人使用，main 作为统一入口

---

### 方案 B: 完全隔离

**配置**: `dmScope: per-channel-peer`

**优点**:
- ✅ 每个用户在每个 Channel 有独立会话
- ✅ 可以绑定不同 Agent 到不同 Channel

**缺点**:
- ❌ 会话数量激增
- ❌ 记忆分散，上下文不连贯

**适用场景**: 多用户、多团队场景

---

### 方案 C: 按 Channel 隔离

**配置**: `dmScope: channel`

**优点**:
- ✅ DingTalk 和 WeCom 会话分开
- ✅ 可以为不同 Channel 配置不同 Agent

**缺点**:
- ⚠️ 同一用户在不同 Channel 的对话不连贯

**适用场景**: 不同 Channel 用于不同目的 (如 DingTalk 用于工作，WeCom 用于生活)

---

## 📝 快速参考

### 查看当前配置

```bash
# 查看 Agent 列表
openclaw agents list

# 查看 Channel 状态
openclaw channels status

# 查看会话
openclaw status | grep Sessions
```

### 修改配置

```bash
# 编辑 openclaw.json
vim ~/.openclaw/openclaw.json

# 修改 dmScope
"session": {
  "dmScope": "main"  // 或 "channel", "account", "per-channel-peer"
}

# 重启 Gateway
openclaw gateway restart
```

### 测试会话

```bash
# 发送测试消息
openclaw agent --agent main --message "测试"

# 查看会话历史
cat ~/.openclaw/agents/main/sessions/*.jsonl | tail -20
```

---

## 🔗 参考文档

- [AGENT_ROUTING_GUIDE.md](./AGENT_ROUTING_GUIDE.md) - 路由机制说明
- [AGENT_CONFIG_SUMMARY.md](./AGENT_CONFIG_SUMMARY.md) - Agent 配置总结
- [SYSTEM_STATUS_20260313_1400.md](./SYSTEM_STATUS_20260313_1400.md) - 系统状态报告

---

**维护者**: main-agent  
**最后更新**: 2026-03-13  
**目的**: 理清 Session、Channel、Agent 的关系
