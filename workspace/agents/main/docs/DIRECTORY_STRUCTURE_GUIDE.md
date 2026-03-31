# OpenClaw 工程目录结构指南

**版本**: 2026-03-13  
**作者**: main-agent

---

## 📋 目录概览

```
/home/admin/
├── openclaw/          # OpenClaw 源代码仓库 (Git 项目)
└── .openclaw/         # OpenClaw 运行时数据目录 (配置 + 状态)
```

---

## 🏗️ 核心目录说明

### 1. `~/openclaw/` - 源代码仓库

**性质**: Git 项目，OpenClaw 核心代码  
**用途**: 存放 OpenClaw 框架本身的源代码  
**是否应该修改**: ❌ 不应该直接修改 (除非贡献代码)

```
~/openclaw/
├── src/               # TypeScript 源代码
├── apps/              # 移动端应用 (iOS/Android/macOS)
├── assets/            # 静态资源
├── dist/              # 编译输出
├── packages/          # npm 包
├── AGENTS.md          # 项目开发指南
├── package.json       # npm 配置
└── README.md          # 项目说明
```

**关键文件**:
- `AGENTS.md`: 开发指南
- `package.json`: 依赖管理
- `CHANGELOG.md`: 版本历史

---

### 2. `~/.openclaw/` - 运行时数据目录

**性质**: 配置 + 状态数据  
**用途**: 存放所有用户配置、agent 数据、会话记录  
**是否应该修改**: ✅ 经常修改 (配置文件)

```
~/.openclaw/
├── openclaw.json      # ⭐ 主配置文件 (最重要!)
├── .env               # ⭐ 环境变量 (API Keys 等敏感信息)
├── agents/            # ⭐ Agent 运行时数据
├── workspace/         # ⭐ Agent 工作空间 (代码 + 文档)
├── data/              # 项目数据 (AI-Trader, TrendRadar 等)
├── cron/              # 定时任务配置
├── logs/              # 日志文件
├── memory/            # 长期记忆数据库
└── extensions/        # 扩展插件
```

---

## 📁 详细目录规划

### A. 配置文件位置

| 文件 | 路径 | 用途 | 编辑频率 |
|------|------|------|---------|
| `openclaw.json` | `~/.openclaw/openclaw.json` | 主配置 (agents, channels, models) | 低 |
| `.env` | `~/.openclaw/.env` | 环境变量 (API Keys) | 低 |
| `SOUL.md` | `~/.openclaw/workspace/agents/{agent}/SOUL.md` | Agent 人格定义 | 中 |
| `TOOLS.md` | `~/.openclaw/workspace/agents/{agent}/TOOLS.md` | Agent 工具说明 | 中 |
| `HEARTBEAT.md` | `~/.openclaw/workspace/agents/{agent}/HEARTBEAT.md` | 心跳任务 | 低 |

**示例**:
```bash
# 编辑主配置
vim ~/.openclaw/openclaw.json

# 编辑 main-agent 配置
vim ~/.openclaw/workspace/agents/main/SOUL.md
vim ~/.openclaw/workspace/agents/main/TOOLS.md
```

---

### B. Agent 工作空间

**位置**: `~/.openclaw/workspace/agents/{agent}/`

```
~/.openclaw/workspace/agents/main/
├── SOUL.md            # ⭐ 人格定义 (性格、职责、边界)
├── TOOLS.md           # ⭐ 工具使用说明
├── USER.md            # 用户信息
├── IDENTITY.md        # 身份标识 (名称、emoji、头像)
├── HEARTBEAT.md       # 心跳任务配置
├── AGENTS.md          # 工作空间指南
├── BOOTSTRAP.md       # 启动引导 (首次运行后删除)
├── memory/            # 每日记忆
│   ├── 2026-03-11.md
│   ├── 2026-03-12.md
│   └── 2026-03-13.md
├── MEMORY.md          # 长期记忆 (精选)
├── docs/              # 📚 文档目录
│   ├── AGENT_SETUP_GUIDE.md
│   ├── AGENT_PERMISSIONS.md
│   ├── AGENT_ROUTING_GUIDE.md
│   └── DIRECTORY_STRUCTURE_GUIDE.md
└── skills/            # 🛠️ 技能目录
    ├── stock-pick/
    ├── quantaalpha-deep/
    └── quantaalpha-skill/
```

**各 Agent 目录**:
```
~/.openclaw/workspace/agents/
├── main/              # 主协调者
├── dev/               # 代码开发专家
└── trade/             # 量化交易专家
```

---

### C. 技能 (Skills) 存放位置

#### 方案对比

| 位置 | 路径 | 用途 | 推荐度 |
|------|------|------|-------|
| **全局技能** | `~/.agents/skills/` | 所有 agent 共享 | ⭐⭐⭐⭐⭐ |
| **Agent 专属** | `~/.openclaw/workspace/agents/{agent}/skills/` | 特定 agent 专用 | ⭐⭐⭐ |
| **项目技能** | `~/openclaw/workspace/projects/{project}/skills/` | 项目相关 | ⭐⭐ |

#### 推荐结构

```
~/.agents/skills/                    # 全局技能 (推荐)
├── akshare-stock/                   # A 股行情
├── china-stock-analysis/            # A 股分析
├── backtest/                        # VectorBT 回测
├── backtesting-frameworks/          # 回测框架
└── find-skills/                     # 技能发现

~/.openclaw/workspace/agents/main/skills/  # main 专属
├── stock-pick/                      # 中证 1000 选股
└── quantaalpha-deep/                # 量化 Alpha

~/.openclaw/workspace/agents/dev/skills/   # dev 专属 (如有)
└── (代码开发相关技能)

~/.openclaw/workspace/agents/trade/skills/ # trade 专属 (如有)
└── (交易相关技能)
```

**使用原则**:
1. **通用技能** → `~/.agents/skills/` (所有 agent 可用)
2. **专属技能** → `~/.openclaw/workspace/agents/{agent}/skills/`
3. **项目技能** → 项目目录内

---

### D. 项目代码位置

**位置**: `~/.openclaw/workspace/projects/` 或 `~/openclaw/workspace/Code/`

```
~/.openclaw/workspace/projects/
├── AI-Trader/           # 量化交易系统
│   ├── agent_tools/
│   ├── configs/
│   ├── data/
│   ├── docs/
│   ├── tools/
│   └── .env
├── TrendRadar/          # 热点监控系统
│   ├── config/
│   ├── logs/
│   ├── mcp_server/
│   └── output/
└── OpenClaw/            # OpenClaw 本地开发 (可选)
```

**或** (如果使用独立目录):
```
~/openclaw/workspace/Code/
├── AI-Trader/
├── TrendRadar/
└── ...
```

---

## 🗂️ 完整目录树

```
/home/admin/
│
├── openclaw/                          # 【源代码】OpenClaw 框架代码
│   ├── src/                           # TypeScript 源码
│   ├── apps/                          # 移动端应用
│   ├── packages/                      # npm 包
│   ├── AGENTS.md                      # 开发指南
│   └── README.md
│
└── .openclaw/                         # 【运行时】配置 + 数据
    ├── openclaw.json                  # ⭐ 主配置
    ├── .env                           # ⭐ 环境变量 (API Keys)
    │
    ├── agents/                        # Agent 运行时
    │   └── main/
    │       ├── agent/                 # Agent 状态
    │       └── sessions/              # 会话记录
    │
    ├── workspace/                     # ⭐ Agent 工作空间
    │   ├── agents/
    │   │   ├── main/
    │   │   │   ├── SOUL.md
    │   │   │   ├── TOOLS.md
    │   │   │   ├── USER.md
    │   │   │   ├── memory/
    │   │   │   ├── docs/
    │   │   │   └── skills/
    │   │   ├── dev/
    │   │   └── trade/
    │   ├── projects/                  # 项目代码
    │   │   ├── AI-Trader/
    │   │   └── TrendRadar/
    │   └── skills/                    # 工作空间技能
    │
    ├── data/                          # 项目数据
    │   ├── ai-trader/
    │   ├── trendradar/
    │   └── backups/
    │
    ├── cron/                          # 定时任务
    │   └── jobs.json
    │
    ├── memory/                        # 长期记忆
    │   └── main.sqlite
    │
    ├── logs/                          # 日志
    │   └── openclaw.log
    │
    └── extensions/                    # 扩展插件
        └── openclaw-china/
```

---

## 📝 文件组织最佳实践

### 1. Agent 配置文件

**必须文件**:
```
~/.openclaw/workspace/agents/{agent}/
├── SOUL.md           # 人格定义 (必须)
├── TOOLS.md          # 工具说明 (必须)
├── USER.md           # 用户信息 (推荐)
└── HEARTBEAT.md      # 心跳任务 (可选)
```

**可选文件**:
```
├── IDENTITY.md       # 身份标识
├── AGENTS.md         # 工作指南
├── MEMORY.md         # 长期记忆
└── memory/           # 每日记忆
    └── YYYY-MM-DD.md
```

---

### 2. 技能组织

**全局技能** (推荐):
```bash
# 安装位置
~/.agents/skills/{skill-name}/

# 结构
~/.agents/skills/akshare-stock/
├── SKILL.md          # 技能说明 (必须)
├── main.py           # 入口脚本
├── adapters/         # 适配器
├── services/         # 服务层
└── venv/             # Python 虚拟环境 (如需要)
```

**Agent 专属技能**:
```bash
# 安装位置
~/.openclaw/workspace/agents/{agent}/skills/{skill-name}/

# 示例
~/.openclaw/workspace/agents/main/skills/stock-pick/
├── SKILL.md
├── stock_pick.py
├── factors_definition.md
└── requirements.txt
```

---

### 3. 项目代码

**推荐结构**:
```bash
~/.openclaw/workspace/projects/{project}/
├── src/              # 源代码
├── configs/          # 配置文件
├── data/             # 数据文件
├── docs/             # 文档
├── tests/            # 测试
├── .env              # 项目环境变量
├── .gitignore        # Git 忽略
└── README.md         # 项目说明
```

**AI-Trader 示例**:
```bash
~/.openclaw/workspace/projects/AI-Trader/
├── agent_tools/      # MCP 服务
├── configs/          # 交易配置
├── data/             # 交易数据
├── docs/             # 文档
├── tools/            # 工具脚本
├── .env              # API Keys
└── README.md
```

---

## 🔧 常用路径速查

### 配置编辑
```bash
# 主配置
vim ~/.openclaw/openclaw.json

# 环境变量
vim ~/.openclaw/.env

# Agent 配置
vim ~/.openclaw/workspace/agents/main/SOUL.md
vim ~/.openclaw/workspace/agents/main/TOOLS.md
```

### 技能管理
```bash
# 全局技能目录
cd ~/.agents/skills/

# main 专属技能
cd ~/.openclaw/workspace/agents/main/skills/

# 安装新技能
npx skills add {owner/repo@skill}
```

### 项目代码
```bash
# AI-Trader
cd ~/.openclaw/workspace/projects/AI-Trader/

# TrendRadar
cd ~/.openclaw/workspace/projects/TrendRadar/
```

### 日志查看
```bash
# OpenClaw 日志
tail -f ~/.openclaw/logs/openclaw.log

# 项目日志
tail -f ~/.openclaw/data/ai-trader/logs/*.log
```

---

## ⚠️ 注意事项

### 1. 不要修改的目录
```bash
❌ ~/openclaw/           # 除非贡献代码
❌ ~/.openclaw/agents/   # 运行时数据
❌ ~/.openclaw/memory/   # 数据库文件
```

### 2. 经常修改的目录
```bash
✅ ~/.openclaw/openclaw.json          # 配置
✅ ~/.openclaw/.env                   # 环境变量
✅ ~/.openclaw/workspace/agents/*/    # Agent 配置
✅ ~/.openclaw/workspace/projects/    # 项目代码
```

### 3. 备份建议
```bash
# 定期备份
tar -czf openclaw-backup-$(date +%Y%m%d).tar.gz \
  ~/.openclaw/openclaw.json \
  ~/.openclaw/.env \
  ~/.openclaw/workspace/
```

---

## 📊 目录权限

```bash
# 设置正确权限
chmod 700 ~/.openclaw/                    # 仅用户可访问
chmod 600 ~/.openclaw/.env                # 仅用户可读写
chmod 644 ~/.openclaw/openclaw.json       # 用户可写，其他人可读
chmod 755 ~/.openclaw/workspace/          # 所有人可读，用户可写
```

---

## 🔗 参考文档

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [Agent Workspace 概念](https://docs.openclaw.ai/concepts/agent-workspace)
- [Skills 开发指南](https://docs.openclaw.ai/skills)

---

**维护者**: main-agent  
**最后更新**: 2026-03-13
