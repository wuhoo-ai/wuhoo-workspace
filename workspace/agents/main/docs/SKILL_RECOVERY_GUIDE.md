# 中国区特有技能恢复指南

**版本**: 2026-03-13  
**状态**: ⚠️ 需要恢复

---

## 📋 问题说明

以下技能是 OpenClaw China 版本特有的，不在国际版 Git 仓库中：

### 丢失的技能清单

| 技能名称 | 用途 | 状态 |
|---------|------|------|
| `agent-news` | AI Agent 行业新闻 | ❌ 丢失 |
| `agentguard` | AI Agent 安全监控 | ❌ 丢失 |
| `browse` | 网页浏览 | ❌ 丢失 |
| `file-search` | 本地文件搜索 | ❌ 丢失 |
| `get-tldr` | 文章摘要 | ❌ 丢失 |
| `jina_search` | Jina AI 搜索 | ❌ 丢失 |
| `openclaw-backup` | OpenClaw 备份 | ❌ 丢失 |
| `openclaw-tavily-search` | Tavily 搜索 | ❌ 丢失 |
| `self-improving-agent` | 自我改进 Agent | ❌ 丢失 |
| `skill-vetter` | 技能审查 | ❌ 丢失 |
| `task-status` | 任务状态管理 | ❌ 丢失 |
| `technews` | 科技新闻 | ❌ 丢失 |
| `tushare_search` | Tushare 股票数据 | ❌ 丢失 |
| `using-superpowers` | OpenClaw 高级功能指南 | ❌ 丢失 |
| `web-search-pro` | 专业网页搜索 | ❌ 丢失 |

---

## 🔍 技能来源

这些技能原本位于：`~/openclaw/skills/`

**原因**: 这些是 OpenClaw China 版本的内置技能，通过以下方式安装：
1. OpenClaw China 扩展包
2. clawhub 中国区技能市场
3. 本地开发技能

---

## 🛠️ 恢复方案

### 方案 1: 从备份恢复 (推荐)

如果你有备份，从备份恢复：

```bash
# 从备份恢复
tar -xzf openclaw-backup-YYYYMMDD.tar.gz -C ~/openclaw/skills/
```

### 方案 2: 重新安装 OpenClaw China

```bash
# 重新安装中国区扩展
cd ~/openclaw/extensions/openclaw-china
pnpm install
pnpm build
```

### 方案 3: 从 clawhub 重新安装

部分技能可以通过 clawhub 重新安装：

```bash
# 搜索并安装
npx skills find jina
npx skills find tavily
npx skills find backup
```

### 方案 4: 手动创建技能

对于没有替代的技能，需要手动创建 SKILL.md 文件。

---

## 📦 可用替代技能

### Jina Search 替代

```bash
# 安装 Jina Reader 技能
npx skills add sundial-org/awesome-openclaw-skills@jina-reader
```

### Tavily Search 替代

```bash
# 安装 Tavily 官方技能
npx skills add tavily-ai/skills@search
npx skills add tavily-ai/skills@research
```

### 文件搜索替代

使用 OpenClaw 内置的 `file-search` 工具 (不需要单独技能)。

---

## 🔧 临时解决方案

### 使用内置工具

OpenClaw 内置工具可以替代部分技能：

```bash
# 文件搜索
openclaw exec "find ~/.openclaw -name '*.md'"

# 网页搜索 (需要配置 Brave API)
openclaw exec "curl -s 'https://api.brave.com/search?q=keyword'"

# 使用 Jina AI (已有 API Key)
exec curl -s -H "Authorization: Bearer $JINA_API_KEY" "https://r.jina.ai/https://example.com"
```

### 使用已有的技能

当前已安装的技能：

```bash
# 全局技能
~/.agents/skills/
├── akshare-stock/          # A 股行情
├── backtest/               # VectorBT 回测
├── backtesting-frameworks/ # 回测框架
├── china-stock-analysis/   # A 股分析
└── find-skills/            # 技能发现
```

---

## 📝 技能创建模板

如果需要手动创建技能，使用以下模板：

```markdown
---
name: skill-name
description: "技能描述"
metadata: { "openclaw": { "emoji": "🔧", "requires": { "bins": [] } } }
---

# Skill Name

技能说明和使用方法。
```

---

## ✅ 当前状态

### 已恢复的技能

| 技能 | 位置 | 状态 |
|------|------|------|
| (等待恢复) | - | ⏳ |

### 已安装的替代技能

| 技能 | 位置 | 用途 |
|------|------|------|
| `akshare-stock` | `~/.agents/skills/` | A 股行情 |
| `china-stock-analysis` | `~/.agents/skills/` | A 股分析 |
| `backtest` | `~/.agents/skills/` | 回测 |
| `backtesting-frameworks` | `~/.agents/skills/` | 回测框架 |
| `find-skills` | `~/.agents/skills/` | 技能发现 |

---

## 🔗 参考资源

- [ClawHub 技能市场](https://clawhub.com)
- [OpenClaw 技能开发指南](https://docs.openclaw.ai/skills)
- [SKILL_INSTALLATION_NORM.md](./SKILL_INSTALLATION_NORM.md) - 技能安装规范

---

**维护者**: main-agent  
**最后更新**: 2026-03-13  
**状态**: ⚠️ 等待恢复
