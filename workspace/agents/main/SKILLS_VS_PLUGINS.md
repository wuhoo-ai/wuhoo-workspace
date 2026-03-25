# OpenClaw Skills vs Plugins 对比指南

**更新时间**: 2026-03-10  
**版本**: v2026.3.8

---

## 🎯 核心区别

| 维度 | Skills | Plugins (Extensions) |
|------|--------|---------------------|
| **定义** | Agent 的**能力/工具** | Gateway 的**功能模块/渠道** |
| **用途** | 扩展 Agent 能做什么 | 扩展 Gateway 能连接什么 |
| **执行时机** | Agent 决策后调用 | Gateway 启动时加载 |
| **运行位置** | Agent 工作区 | Gateway 进程内 |
| **类比** | 手机 App | 操作系统驱动/服务 |

---

## 📂 存放目录

### Skills

```
~/openclaw/skills/              # 系统 Skills
├── jina_search/                # 每个 Skill 独立目录
│   ├── SKILL.md               # Skill 定义文档
│   └── jina_search.sh         # 执行脚本
├── tushare_search/
│   ├── SKILL.md
│   └── tushare_query.py
├── weather/
│   └── SKILL.md
└── ... (54 个)

~/.openclaw/workspace/agents/main/skills/  # Agent 专属 Skills
└── ...
```

### Plugins (Extensions)

```
~/openclaw/extensions/          # 扩展源码
├── openclaw-china/            # 中国渠道包
│   └── packages/channels/
│       └── dist/index.js

~/.openclaw/extensions/         # 已安装 Extensions
└── stock/                     # 内置插件
    ├── channels/index.js      # 渠道插件
    ├── memory-core/index.js   # 记忆插件
    └── ... (39 个)
```

---

## 📥 获取方式

### Skills

| 方式 | 命令 | 说明 |
|------|------|------|
| **手动创建** | `mkdir ~/openclaw/skills/my_skill` | 创建 SKILL.md |
| **从 ClawHub** | `openclaw clawhub install <skill>` | 从技能市场 |
| **复制** | `cp -r skill_dir ~/openclaw/skills/` | 直接复制 |
| **Git 克隆** | `git clone <repo> ~/openclaw/skills/` | 从 Git |

**示例**:
```bash
# 创建 Skill
mkdir -p ~/openclaw/skills/my_search
cat > ~/openclaw/skills/my_search/SKILL.md << 'EOF'
# my_search Skill
## 描述
使用 XXX API 进行搜索
## 使用方式
exec curl "https://api.xxx.com/search?q=$QUERY"
EOF
```

### Plugins

| 方式 | 命令 | 说明 |
|------|------|------|
| **内置** | 自动加载 | Gateway 自带 |
| **npm 安装** | `openclaw plugins install @openclaw/telegram` | 从 npm |
| **本地开发** | 配置 `extensions` 目录 | 开发模式 |
| **ClawHub** | `openclaw clawhub install plugin` | 从技能市场 |

**示例**:
```bash
# 安装插件
openclaw plugins install @openclaw/telegram

# 启用插件
openclaw plugins enable telegram

# 禁用插件
openclaw plugins disable discord
```

---

## 🔐 鉴权方式

### Skills

| 鉴权层 | 配置位置 | 示例 |
|--------|----------|------|
| **环境变量** | `~/.openclaw/.env` | `JINA_API_KEY=xxx` |
| **Skill 配置** | `SKILL.md` 中定义 | `requires: [api_key]` |
| **Agent 策略** | `openclaw.json` | `tools.allow: ["jina_search"]` |
| **执行权限** | 文件系统权限 | `chmod +x script.sh` |

**示例配置**:
```bash
# ~/.openclaw/.env
JINA_API_KEY=jina_xxxxxxxx
TUSHARE_TOKEN=822130fe12b4a3f37b23c6718477718ac08450f703e76156bb241a6c

# SKILL.md
# 需要环境变量: JINA_API_KEY
```

### Plugins

| 鉴权层 | 配置位置 | 示例 |
|--------|----------|------|
| **Secrets** | `openclaw.json` + `.env` | `${WECOM_SECRET}` |
| **OAuth** | 插件配置 | `clientId`, `clientSecret` |
| **Plugin 策略** | `plugins.allow` | `["channels", "telegram"]` |
| **Channel 策略** | `channels.*.allowFrom` | `["user_id"]` |

**示例配置**:
```json
{
  "plugins": {
    "allow": ["channels", "telegram", "memory-core"]
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "${TELEGRAM_BOT_TOKEN}"
    }
  }
}
```

---

## ⚙️ 网关配置入口

### Skills 配置

**配置位置**: `~/.openclaw/openclaw.json`

```json
{
  "agents": {
    "defaults": {
      "tools": {
        "allow": ["jina_search", "tushare_search", "weather"],
        "deny": ["exec", "bash"]
      }
    },
    "list": [
      {
        "id": "main",
        "workspace": "~/.openclaw/workspace/agents/main",
        "tools": {
          "allow": ["jina_search", "tushare_search"],
          "deny": []
        }
      }
    ]
  }
}
```

**配置项**:
- `tools.allow` - 允许使用的 Skills
- `tools.deny` - 禁止使用的 Skills
- `workspace` - Agent 工作区（包含专属 Skills）

### Plugins 配置

**配置位置**: `~/.openclaw/openclaw.json`

```json
{
  "plugins": {
    "allow": ["channels", "telegram", "memory-core"],
    "deny": ["discord", "whatsapp"]
  },
  "channels": {
    "dingtalk": {
      "enabled": true,
      "clientId": "${DINGTALK_CLIENT_ID}",
      "clientSecret": "${DINGTALK_CLIENT_SECRET}"
    },
    "telegram": {
      "enabled": true,
      "botToken": "${TELEGRAM_BOT_TOKEN}"
    }
  }
}
```

**配置项**:
- `plugins.allow` - 允许加载的 Plugins
- `channels.*` - 各渠道详细配置
- `extensions` - 扩展目录路径

---

## 🔄 加载时机

### Skills

```
用户消息
  ↓
Agent 接收
  ↓
Agent 读取 SKILL.md
  ↓
Agent 决定是否调用 Skill
  ↓
执行 Skill 脚本/命令
  ↓
返回结果给 Agent
```

**加载特点**:
- ✅ 按需加载（Agent 决策后）
- ✅ 每次调用独立执行
- ✅ 可以动态添加/删除
- ✅ 每个 Agent 可以有专属 Skills

### Plugins

```
Gateway 启动
  ↓
读取 openclaw.json
  ↓
加载 plugins.allow 列表
  ↓
初始化每个 Plugin
  ↓
注册到 Gateway 运行时
  ↓
等待事件触发
```

**加载特点**:
- ✅ 启动时加载
- ✅ 常驻内存
- ✅ 需要重启 Gateway 生效
- ✅ 全局共享（所有 Agent 可用）

---

## 📊 功能对比表

| 功能 | Skills | Plugins |
|------|--------|---------|
| **动态添加** | ✅ 无需重启 | ❌ 需要重启 |
| **Agent 专属** | ✅ 可以 | ❌ 全局共享 |
| **内存占用** | 🟢 低（按需） | 🟡 中（常驻） |
| **开发难度** | 🟢 简单（Markdown+ 脚本） | 🟡 中等（TypeScript） |
| **发布到 ClawHub** | ✅ 支持 | ✅ 支持 |
| **版本管理** | 🟡 手动 | ✅ npm 语义化版本 |
| **热更新** | ✅ 支持 | ❌ 不支持 |
| **调试难度** | 🟢 简单 | 🟡 中等 |

---

## 🛠️ 开发对比

### Skill 开发

**文件结构**:
```
my_skill/
├── SKILL.md           # 必需：定义文档
├── my_skill.sh        # 可选：执行脚本
└── utils.py           # 可选：辅助代码
```

**SKILL.md 模板**:
```markdown
# my_skill

## 描述
使用 XXX API 做 YYY

## 使用方式
```bash
exec curl "https://api.xxx.com?q=$QUERY"
```

## 配置
需要环境变量：`XXX_API_KEY`
```

**开发时间**: 10-30 分钟

### Plugin 开发

**文件结构**:
```
my-plugin/
├── package.json
├── tsconfig.json
├── src/
│   └── index.ts       # 主入口
└── dist/
    └── index.js       # 编译输出
```

**index.ts 模板**:
```typescript
import { Plugin } from '@openclaw/plugin-sdk';

export default class MyPlugin extends Plugin {
  async onMessage(message) {
    // 处理消息
  }
  
  async onCommand(command) {
    // 处理命令
  }
}
```

**开发时间**: 2-8 小时

---

## 📦 当前系统状态

### Skills (54 个)

**分类统计**:
| 分类 | 数量 | 示例 |
|------|------|------|
| 搜索 | 2 | jina_search, weather |
| 笔记 | 5 | notion, obsidian, bear-notes |
| 媒体 | 4 | sag, whisper, image-gen |
| 工具 | 10 | github, ordercli, healthcheck |
| 通讯 | 4 | discord, slack, telegram |
| 系统 | 29 | 其他 |

**存放位置**:
```
~/openclaw/skills/ (54 个)
```

### Plugins (39 个可用，5 个已加载)

**已加载**:
| 插件 | ID | 用途 |
|------|-----|------|
| Moltbot China Channels | channels | 钉钉/飞书/企微 |
| Device Pairing | device-pair | 设备配对 |
| Memory (Core) | memory-core | 文件记忆 |
| Phone Control | phone-control | 手机控制 |
| Talk Voice | talk-voice | 语音选择 |

**可用但未加载**:
- Feishu, Telegram, WhatsApp
- Discord, Slack, Mattermost
- Memory LanceDB, Diagnostics

**存放位置**:
```
~/.openclaw/extensions/ (内置)
~/openclaw/extensions/ (用户扩展)
```

---

## 🎯 使用场景对比

### 什么时候用 Skills？

- ✅ 需要 Agent 调用外部 API
- ✅ 需要执行系统命令
- ✅ 需要读取/写入文件
- ✅ 快速原型开发
- ✅ Agent 专属功能
- ✅ 简单数据处理

**示例场景**:
- 查询股票数据 (tushare_search)
- 网络搜索 (jina_search)
- 查询天气 (weather)
- 发送通知 (自定义脚本)

### 什么时候用 Plugins？

- ✅ 需要连接新渠道 (Telegram, WhatsApp)
- ✅ 需要扩展 Gateway 功能
- ✅ 需要处理底层事件
- ✅ 需要常驻服务
- ✅ 全局功能（所有 Agent 共享）
- ✅ 复杂业务逻辑

**示例场景**:
- 添加 Telegram 渠道
- 添加向量数据库记忆
- 添加监控和诊断
- 添加自定义认证

---

## 🔄 协同工作

Skills 和 Plugins 可以协同工作：

```
用户 (Telegram)
  ↓
Telegram Plugin (接收消息)
  ↓
Gateway (路由到 Agent)
  ↓
Agent (决策)
  ↓
jina_search Skill (搜索信息)
  ↓
Agent (整理结果)
  ↓
Telegram Plugin (发送回复)
```

**配置示例**:
```json
{
  "plugins": {
    "allow": ["telegram"]  // 启用 Telegram 插件
  },
  "channels": {
    "telegram": {
      "enabled": true
    }
  },
  "agents": {
    "main": {
      "tools": {
        "allow": ["jina_search"]  // Agent 可以使用搜索技能
      }
    }
  }
}
```

---

## 📝 总结

| 维度 | Skills | Plugins |
|------|--------|---------|
| **本质** | Agent 的工具 | Gateway 的模块 |
| **难度** | 🟢 简单 | 🟡 中等 |
| **灵活性** | 🟢 高 | 🟡 中 |
| **性能** | 🟢 按需加载 | 🟡 常驻内存 |
| **适用** | API 调用/脚本 | 渠道/服务 |

**建议**:
- 简单功能 → 优先 Skills
- 渠道集成 → 必须 Plugins
- 复杂服务 → 考虑 Plugins
- 快速原型 → 先用 Skills

---

**文档结束**
