# OpenClaw 目录迁移规范

**版本**: 2026-03-13  
**状态**: ✅ 已完成迁移

---

## 📋 迁移目标

```
/home/admin/
├── openclaw/          # 【源代码】OpenClaw 框架本身 (Git 仓库)
│                      # ❌ 不要修改 (除非贡献代码)
│
└── .openclaw/         # 【运行时】配置 + 数据
                       # ✅ 所有工作都在这个目录
```

---

## ✅ 当前状态检查

### 已完成迁移的目录

| 目录 | 路径 | 状态 | 说明 |
|------|------|------|------|
| **Agent 配置** | `~/.openclaw/workspace/agents/` | ✅ | main, dev, trade |
| **项目代码** | `~/.openclaw/workspace/projects/` | ✅ | AI-Trader, TrendRadar |
| **全局技能** | `~/.agents/skills/` | ✅ | akshare-stock, backtest 等 |
| **Agent 专属技能** | `~/.openclaw/workspace/agents/*/skills/` | ✅ | stock-pick 等 |
| **项目数据** | `~/.openclaw/data/` | ✅ | ai-trader, trendradar |
| **配置文件** | `~/.openclaw/openclaw.json` | ✅ | 主配置 |
| **环境变量** | `~/.openclaw/.env` | ✅ | API Keys |

### 未迁移的目录 (无需迁移)

| 目录 | 路径 | 原因 |
|------|------|------|
| **OpenClaw 源码** | `~/openclaw/` | ✅ 正确 - 这是 Git 仓库，不应修改 |
| **workspace 空目录** | `~/openclaw/workspace/` | ✅ 正确 - 已废弃，使用 `~/.openclaw/workspace/` |
| **data 空目录** | `~/openclaw/data/` | ✅ 正确 - 已废弃，使用 `~/.openclaw/data/` |

---

## 📁 标准目录结构

```
~/.openclaw/                           # ✅ 主工作目录
│
├── openclaw.json                      # ⭐ 主配置文件
├── .env                               # ⭐ 环境变量 (API Keys)
│
├── workspace/                         # ⭐ 工作空间
│   ├── agents/                        # Agent 配置
│   │   ├── main/
│   │   │   ├── SOUL.md
│   │   │   ├── TOOLS.md
│   │   │   ├── USER.md
│   │   │   ├── HEARTBEAT.md
│   │   │   ├── docs/                  # 文档
│   │   │   └── skills/                # 专属技能
│   │   ├── dev/
│   │   └── trade/
│   │
│   ├── projects/                      # 项目代码
│   │   ├── AI-Trader/
│   │   └── TrendRadar/
│   │
│   └── skills/                        # 工作空间技能
│
├── data/                              # 项目数据
│   ├── ai-trader/
│   ├── trendradar/
│   └── backups/
│
├── agents/                            # Agent 运行时
│   └── main/
│       ├── agent/
│       └── sessions/
│
├── cron/                              # 定时任务
│   └── jobs.json
│
├── memory/                            # 长期记忆
│   └── main.sqlite
│
└── logs/                              # 日志
    └── openclaw.log
```

---

## 🔧 文件位置规范

### 1. Agent 配置文件

**位置**: `~/.openclaw/workspace/agents/{agent}/`

**必须文件**:
- `SOUL.md` - 人格定义
- `TOOLS.md` - 工具说明
- `USER.md` - 用户信息
- `HEARTBEAT.md` - 心跳任务

**可选文件**:
- `IDENTITY.md` - 身份标识
- `MEMORY.md` - 长期记忆
- `docs/` - 文档目录
- `skills/` - 专属技能

---

### 2. 技能文件

**全局技能** (所有 agent 共享):
```
~/.agents/skills/
├── akshare-stock/
├── china-stock-analysis/
├── backtest/
└── backtesting-frameworks/
```

**Agent 专属技能**:
```
~/.openclaw/workspace/agents/{agent}/skills/
└── stock-pick/
```

---

### 3. 项目代码

**位置**: `~/.openclaw/workspace/projects/`

```
~/.openclaw/workspace/projects/AI-Trader/
├── agent_tools/
├── configs/
├── data/
├── docs/
├── tools/
└── .env
```

---

### 4. 配置文件

**主配置**: `~/.openclaw/openclaw.json`
- agents 配置
- channels 配置
- models 配置
- routing 配置

**环境变量**: `~/.openclaw/.env`
- API Keys (BAILIAN_API_KEY, TUSHARE_TOKEN 等)
- 渠道配置 (DingTalk, WeCom 等)

---

## 🚫 禁止操作

### 不要修改的目录

```bash
❌ ~/openclaw/                    # OpenClaw 源代码
❌ ~/.openclaw/agents/            # Agent 运行时数据
❌ ~/.openclaw/memory/            # 记忆数据库
❌ ~/.openclaw/sessions/          # 会话记录
```

### 不要创建的文件

```bash
❌ ~/openclaw/workspace/          # 已废弃
❌ ~/openclaw/data/               # 已废弃
❌ ~/.openclaw/.git/              # 不是 Git 仓库
```

---

## ✅ 推荐操作

### 日常编辑

```bash
# 编辑主配置
vim ~/.openclaw/openclaw.json

# 编辑环境变量
vim ~/.openclaw/.env

# 编辑 Agent 配置
vim ~/.openclaw/workspace/agents/main/SOUL.md
vim ~/.openclaw/workspace/agents/main/TOOLS.md

# 查看项目代码
cd ~/.openclaw/workspace/projects/AI-Trader/

# 查看技能
cd ~/.agents/skills/
cd ~/.openclaw/workspace/agents/main/skills/
```

### 安装技能

```bash
# 安装全局技能
npx skills add {owner/repo@skill}
# 安装位置：~/.agents/skills/

# 技能会自动 symlink 到各 agent
```

### 备份配置

```bash
# 备份重要配置
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

## 🔍 验证命令

```bash
# 检查目录结构
tree -L 3 ~/.openclaw/

# 检查 Agent 配置
openclaw agents list

# 检查配置有效性
openclaw doctor

# 检查技能
npx skills list
```

---

## 📝 迁移历史

| 日期 | 操作 | 状态 |
|------|------|------|
| 2026-03-13 | 创建目录规范文档 | ✅ 完成 |
| 2026-03-13 | 确认所有文件在正确位置 | ✅ 完成 |
| 2026-03-13 | 创建迁移规范文档 | ✅ 完成 |

---

## 🔗 参考文档

- [DIRECTORY_STRUCTURE_GUIDE.md](./DIRECTORY_STRUCTURE_GUIDE.md) - 完整目录结构说明
- [AGENT_SETUP_GUIDE.md](./AGENT_SETUP_GUIDE.md) - Agent 配置指南
- [OpenClaw 官方文档](https://docs.openclaw.ai)

---

**维护者**: main-agent  
**最后更新**: 2026-03-13  
**状态**: ✅ 所有文件已正确迁移
