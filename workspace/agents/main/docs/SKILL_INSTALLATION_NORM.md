# 技能安装规范

**版本**: 2026-03-13  
**状态**: ✅ 已修复错误安装问题

---

## ⚠️ 问题说明

### 错误现象

技能被错误安装到 `~/openclaw/skills/` (源代码目录)：

```bash
# ❌ 错误位置
~/openclaw/skills/
├── agent-news/
├── agentguard/
├── browse/
├── file-search/
└── ...
```

**问题**:
- 污染了 Git 仓库
- `git status` 显示大量未跟踪文件
- 违反了目录规范

---

### 正确位置

技能应该安装到 `~/.agents/skills/` (全局技能目录)：

```bash
# ✅ 正确位置
~/.agents/skills/
├── akshare-stock/
├── backtest/
├── backtesting-frameworks/
├── china-stock-analysis/
└── find-skills/
```

---

## 🔧 修复方法

### 1. 清理错误安装

```bash
# 删除错误安装的技能
cd ~/openclaw
rm -rf skills/agent-news skills/agentguard skills/browse ...

# 或使用 Git 恢复
cd ~/openclaw
git checkout -- skills/
```

### 2. 验证 Git 状态

```bash
cd ~/openclaw
git status
# 应该只显示 pnpm-lock.yaml 修改 (如有)
```

---

## 📋 技能安装规范

### 技能目录层级

```
~/.agents/skills/              # ⭐ 全局技能 (推荐)
└── {skill-name}/

~/.openclaw/workspace/agents/{agent}/skills/  # Agent 专属技能
└── {skill-name}/
```

### 安装命令

```bash
# 安装到全局目录 (所有 agent 可用)
npx skills add {owner/repo@skill}

# 示例
npx skills add molezzz/openclaw-stock-skill@akshare-stock
npx skills add sugarforever/01coder-agent-skills@china-stock-analysis
```

### 安装位置验证

```bash
# 检查安装位置
ls -la ~/.agents/skills/

# 检查 symlink
ls -la ~/.openclaw/.agents/skills/
```

---

## 🚫 禁止操作

### 不要安装到源代码目录

```bash
❌ ~/openclaw/skills/          # OpenClaw 框架源码
```

### 不要手动创建技能

```bash
# 应该使用 clawhub 安装
npx skills add {owner/repo@skill}

# 不要手动复制到 skills/ 目录
```

---

## ✅ 正确流程

### 1. 查找技能

```bash
# 搜索技能
npx skills find {keyword}

# 浏览技能市场
https://clawhub.com
```

### 2. 安装技能

```bash
# 安装到全局目录
npx skills add {owner/repo@skill}

# 安装到特定 agent (可选)
npx skills add {owner/repo@skill} --agent {agent-id}
```

### 3. 验证安装

```bash
# 查看已安装技能
npx skills list

# 检查技能文件
ls -la ~/.agents/skills/{skill-name}/

# 检查 SKILL.md
cat ~/.agents/skills/{skill-name}/SKILL.md
```

---

## 📊 技能分类

### 全局技能 (推荐)

**位置**: `~/.agents/skills/`  
**用途**: 所有 agent 共享  
**示例**:
- `akshare-stock` - A 股行情
- `backtest` - VectorBT 回测
- `china-stock-analysis` - A 股分析

### Agent 专属技能

**位置**: `~/.openclaw/workspace/agents/{agent}/skills/`  
**用途**: 特定 agent 专用  
**示例**:
- `main/skills/stock-pick/` - main 专属选股

---

## 🔍 故障排查

### 问题 1: 技能安装到错误位置

**症状**: `git status` 显示 `skills/` 目录有修改

**解决**:
```bash
cd ~/openclaw
git checkout -- skills/
rm -rf skills/{skill-name}
```

### 问题 2: 技能无法找到

**症状**: agent 无法使用已安装的技能

**检查**:
```bash
# 检查技能是否存在
ls -la ~/.agents/skills/{skill-name}/

# 检查 symlink
ls -la ~/.openclaw/.agents/skills/

# 检查 SKILL.md
cat ~/.agents/skills/{skill-name}/SKILL.md
```

### 问题 3: clawhub 配置错误

**检查配置**:
```bash
cat ~/.openclaw/.config/clawhub.json
cat ~/.openclaw/openclaw.json | grep -A 10 clawhub
```

---

## 📝 已安装技能清单

### 全局技能 (~/.agents/skills/)

| 技能 | 用途 | 安装时间 |
|------|------|---------|
| `akshare-stock` | A 股实时行情 | 2026-03-13 |
| `china-stock-analysis` | A 股价值投资分析 | 2026-03-13 |
| `backtest` | VectorBT 快速回测 | 2026-03-13 |
| `backtesting-frameworks` | 回测框架文档 | 2026-03-13 |
| `find-skills` | 技能发现工具 | 系统自带 |

### Agent 专属技能

| Agent | 技能 | 用途 |
|-------|------|------|
| main | `stock-pick` | 中证 1000 选股 |
| main | `quantaalpha-deep` | 量化 Alpha (venv) |
| main | `quantaalpha-skill` | 量化技能 |

---

## 🔗 参考文档

- [CLAWHUB_SKILLS_GUIDE.md](./CLAWHUB_SKILLS_GUIDE.md) - ClawHub 使用指南
- [DIRECTORY_STRUCTURE_GUIDE.md](./DIRECTORY_STRUCTURE_GUIDE.md) - 目录结构说明
- [MIGRATION_NORM.md](./MIGRATION_NORM.md) - 迁移规范

---

**维护者**: main-agent  
**最后更新**: 2026-03-13  
**状态**: ✅ 错误已修复，规范已建立
