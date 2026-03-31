# Agent 配置总结

**版本**: 2026-03-13  
**状态**: ✅ 配置完成

---

## 📋 配置概览

| Agent | 模型 | 职责 | 工具权限 |
|-------|------|------|---------|
| **main** | qwen3.5-plus | 用户对话、任务路由、新闻摘要 | read, edit, write, web_search, web_fetch, message, exec, file-search, clawhub, web-search-pro |
| **dev** | qwen3-coder-next | 代码编写、代码分析、Skill 实现 | read, edit, write, exec, file-search, glob, grep, clawhub |
| **trade** | qwen3.5-plus | 因子挖掘、选股、金融数据、回测 | read, edit, write, exec, file-search, glob, grep, web_search, web_fetch, clawhub |

---

## 🛠️ 技能清单

### 全局技能 (~/.agents/skills/)

共 **19 个技能**：

#### 金融交易类
| 技能 | 用途 | API Key |
|------|------|---------|
| `akshare-stock` | A 股实时行情 | - |
| `china-stock-analysis` | A 股价值投资分析 | - |
| `backtest` | VectorBT 快速回测 | - |
| `backtesting-frameworks` | 回测框架文档 | - |
| `tushare_search` | Tushare 数据查询 | `$TUSHARE_TOKEN` |

#### 信息搜索类
| 技能 | 用途 | API Key |
|------|------|---------|
| `jina_search` | Jina AI 搜索 | `$JINA_API_KEY` |
| `web_search` | Brave 搜索 | `$BRAVE_API_KEY` |
| `web_fetch` | 网页内容提取 | - |
| `browse` | 网页浏览 | `$JINA_API_KEY` |
| `technews` | 科技新闻 | - |
| `agent-news` | AI 行业新闻 | - |

#### 工具类
| 技能 | 用途 |
|------|------|
| `file-search` | 本地文件搜索 |
| `get-tldr` | 文章摘要 |
| `task-status` | 任务管理 |
| `openclaw-backup` | OpenClaw 备份 |
| `skill-vetter` | 技能安全审查 |
| `self-improving-agent` | 自我改进 Agent |
| `using-superpowers` | OpenClaw 高级功能指南 |
| `web-search-pro` | 专业网络搜索 |
| `openclaw-tavily-search` | Tavily 搜索 | `$TAVILY_API_KEY` |
| `find-skills` | 技能发现 (系统自带) |

---

## 🎯 Agent 职责分工

### main-agent (主协调者)

**职责**:
- ✅ 用户对话与需求理解
- ✅ 任务分解与路由 (dev/trade)
- ✅ 新闻摘要与心跳检查
- ✅ 跨代理协调与结果汇总
- ✅ 外部消息推送 (DingTalk/WeCom)

**工作流**:
```
用户消息 → main 判断任务类型 → 路由到 dev/trade → 汇总结果 → 回复用户
```

---

### dev-agent (代码开发专家)

**职责**:
- ✅ 代码编写与重构
- ✅ Bug 调试与修复
- ✅ 代码审查与建议
- ✅ Skill 实现与优化
- ✅ 开发环境配置

**使用场景**:
```
用户："帮我写一个 Python 函数计算移动平均线"
→ main 路由到 dev
→ dev 使用 qwen3-coder-next 生成代码
→ 返回代码和说明
```

**工具**:
- `coding-agent` (通过 BAILIAN_API_KEY)
- `file-search`, `glob`, `grep` (代码搜索)
- `exec` (运行测试、构建)

---

### trade-agent (量化交易专家)

**职责**:
- ✅ 因子挖掘与选股
- ✅ 金融数据查询
- ✅ 金融新闻与信息查询
- ✅ 模拟交易与回测
- ✅ 持仓管理与风险控制

**使用场景**:
```
用户："查询贵州茅台今天的价格"
→ main 路由到 trade
→ trade 使用 akshare-stock 获取行情
→ 返回价格和涨跌幅
```

**工具**:
- `tushare_search` (财务数据)
- `akshare-stock` (实时行情)
- `backtest` (回测)
- `web_search`, `jina_search` (新闻)

---

## 🔧 配置文件位置

| 文件 | 路径 | 用途 |
|------|------|------|
| 主配置 | `~/.openclaw/openclaw.json` | agents, channels, models |
| 环境变量 | `~/.openclaw/.env` | API Keys |
| main 配置 | `~/.openclaw/workspace/agents/main/` | SOUL.md, TOOLS.md |
| dev 配置 | `~/.openclaw/workspace/agents/dev/` | SOUL.md, TOOLS.md |
| trade 配置 | `~/.openclaw/workspace/agents/trade/` | SOUL.md, TOOLS.md |

---

## 📊 权限矩阵

| 工具/技能 | main | dev | trade |
|----------|------|-----|-------|
| **基础工具** | | | |
| `read` | ✅ | ✅ | ✅ |
| `edit` | ✅ | ✅ | ✅ |
| `write` | ✅ | ✅ | ✅ |
| `exec` | ✅ | ✅ | ✅ |
| **搜索工具** | | | |
| `web_search` | ✅ | ❌ | ✅ |
| `web_fetch` | ✅ | ❌ | ✅ |
| `file-search` | ✅ | ✅ | ✅ |
| `glob` | ❌ | ✅ | ✅ |
| `grep` | ❌ | ✅ | ✅ |
| **技能工具** | | | |
| `clawhub` | ✅ | ✅ | ✅ |
| `message` | ✅ | ❌ | ❌ |
| `web-search-pro` | ✅ | ❌ | ❌ |
| **金融技能** | | | |
| `tushare_search` | ❌ | ❌ | ✅ |
| `akshare-stock` | ❌ | ❌ | ✅ |
| `backtest` | ❌ | ❌ | ✅ |
| **开发技能** | | | |
| `coding-agent` | ❌ | ✅ | ❌ |

---

## 🚀 使用示例

### 代码开发任务

```bash
# 用户请求
"帮我实现一个选股策略，使用动量因子"

# 路由流程
用户 → main (理解需求) → dev (实现代码)
→ dev 使用 qwen3-coder-next 生成代码
→ 返回 Python 脚本和说明
```

### 金融数据查询

```bash
# 用户请求
"查询中证 1000 成分股中 ROE>15% 的股票"

# 路由流程
用户 → main (理解需求) → trade (执行查询)
→ trade 使用 tushare_search 获取数据
→ 使用 china-stock-analysis 筛选
→ 返回股票列表
```

### 回测任务

```bash
# 用户请求
"回测双均线策略在贵州茅台上的表现"

# 路由流程
用户 → main (理解需求) → trade (执行回测)
→ trade 使用 backtest 技能
→ 生成 VectorBT 回测脚本
→ 运行回测并返回结果
```

---

## ⚠️ 注意事项

### 1. API Key 管理

```bash
# 确保以下环境变量已配置
export JINA_API_KEY=...
export TUSHARE_TOKEN=...
export BAILIAN_API_KEY=...
export TAVILY_API_KEY=...  # 可选
export BRAVE_API_KEY=...   # 可选
```

### 2. 技能依赖

```bash
# Python 技能需要虚拟环境
source ~/.agents/skills/akshare-stock/venv/bin/activate

# 安装依赖
pip install akshare pandas numpy
```

### 3. 路由规则

- 所有消息首先到达 main
- main 根据关键词判断是否路由到 dev/trade
- 默认由 main 处理

---

## 🔗 参考文档

- [AGENT_SETUP_GUIDE.md](./AGENT_SETUP_GUIDE.md) - 多代理配置指南
- [AGENT_PERMISSIONS.md](./AGENT_PERMISSIONS.md) - 权限管理文档
- [AGENT_ROUTING_GUIDE.md](./AGENT_ROUTING_GUIDE.md) - 路由机制说明
- [DIRECTORY_STRUCTURE_GUIDE.md](./DIRECTORY_STRUCTURE_GUIDE.md) - 目录结构说明
- [SKILL_INSTALLATION_NORM.md](./SKILL_INSTALLATION_NORM.md) - 技能安装规范

---

**维护者**: main-agent  
**最后更新**: 2026-03-13  
**状态**: ✅ 配置完成
