# OpenClaw 多代理权限管理

**版本**: 2026-03-13  
**最后更新**: 2026-03-13 11:05 AM

---

## 📋 权限概览

| 工具/技能 | main | dev | trade | 说明 |
|----------|------|-----|-------|------|
| **基础工具** | | | | |
| `read` | ✅ | ✅ | ✅ | 读取文件 |
| `edit` | ✅ | ✅ | ✅ | 编辑文件 |
| `write` | ✅ | ✅ | ✅ | 写入文件 |
| `exec` | ✅ | ✅ | ✅ | 执行命令 |
| **搜索工具** | | | | |
| `web_search` | ✅ | ❌ | ✅ | 网络搜索 (Brave) |
| `web_fetch` | ✅ | ❌ | ✅ | 网页内容提取 |
| `file-search` | ✅ | ✅ | ✅ | 本地文件搜索 |
| `glob` | ❌ | ✅ | ✅ | 文件模式匹配 |
| `grep` | ❌ | ✅ | ✅ | 内容搜索 |
| **技能工具** | | | | |
| `clawhub` | ✅ | ✅ | ✅ | 技能管理 |
| `message` | ✅ | ❌ | ❌ | 消息推送 (仅 main) |
| `web-search-pro` | ✅ | ❌ | ❌ | 专业搜索 (仅 main) |

---

## 🎯 代理职责与权限

### main-agent (主协调者)

**职责**:
- 用户对话与需求理解
- 任务分解与路由 (dev/trade)
- 新闻摘要与心跳检查
- 跨代理协调与结果汇总
- 外部消息推送 (DingTalk/WeCom)

**权限特点**:
- ✅ 唯一可以发送外部消息的代理
- ✅ 拥有完整的搜索工具 (web_search, web_fetch, web-search-pro)
- ❌ 无 glob/grep (代码搜索交给 dev)

**使用场景**:
```bash
# 用户对话
"今天的新闻摘要"
"帮我安排一个会议"
"路由到 dev 实现一个功能"
```

---

### dev-agent (代码开发专家)

**职责**:
- 代码编写与重构
- Bug 调试与修复
- 代码审查与建议
- Skill 实现与优化
- 开发环境配置

**权限特点**:
- ✅ 拥有代码搜索工具 (glob, grep)
- ✅ 完整的文件操作权限
- ❌ 无外部消息权限
- ❌ 无网络搜索 (专注代码)

**使用场景**:
```bash
# 代码任务
"帮我写一个 Python 函数计算移动平均线"
"修复这个 bug"
"审查这段代码"
"实现一个新的 skill"
```

**可用技能**:
- `coding-agent` (通过 BAILIAN_API_KEY)
- `github` (需配置 GitHub Token)
- `tmux` (远程开发会话)

---

### trade-agent (量化交易专家)

**职责**:
- 因子挖掘与选股
- 金融数据查询
- 金融新闻与信息查询
- 模拟交易与回测
- 持仓管理与风险控制

**权限特点**:
- ✅ 拥有网络搜索 (查询金融新闻)
- ✅ 拥有代码搜索 (分析策略代码)
- ❌ 无外部消息权限
- ❌ 无 web-search-pro (不需要专业搜索)

**使用场景**:
```bash
# 交易任务
"查询贵州茅台今天的价格"
"回测双均线策略"
"分析今天的资金流向"
"筛选低估值股票"
```

**可用技能**:
- `tushare_search` (TUSHARE_TOKEN)
- `akshare-stock` (Python 3.11 venv)
- `stock-pick` (中证 1000 选股)
- `china-stock-analysis` (价值投资分析)
- `backtest` (VectorBT 回测)
- `backtesting-frameworks` (回测框架)

---

## 🛣️ 路由规则

### 配置位置
`~/.openclaw/openclaw.json` → `routing.rules`

### 路由规则详情

#### 1. dev-code-routing (代码开发)
**触发条件**:
- **关键词**: 代码、编程、开发、bug、调试、skill、实现、功能、修复、重构、Git、GitHub、编写、脚本、CLI、工具
- **正则**:
  - `(写 | 修改 | 优化 | 审查 | 实现 | 创建 | 添加).*(代码 | 程序 | 脚本 | 功能 | 工具)`
  - `(修复 | 解决).*bug`
  - `(代码 | 程序).*审查`

**目标**: dev-agent

**示例**:
```
用户："帮我写一个 Python 函数"
→ 路由到：dev

用户："修复这个 bug"
→ 路由到：dev

用户："实现一个新的 skill"
→ 路由到：dev
```

---

#### 2. trade-finance-routing (金融交易)
**触发条件**:
- **关键词**: 选股、回测、因子、持仓、交易、股票、行情、金融、量化、收益、Tushare、AkShare、市值、PE、PB、ROE、均线、K 线、涨停、跌停、资金流、板块、ETF、基金、期货
- **正则**:
  - `(分析 | 查询 | 获取 | 查看).*(股票 | 行情 | 金融 | 股价 | 市值)`
  - `(模拟 | 实盘 | 虚拟).*交易`
  - `(因子 | 选股 | 回测).*策略`

**目标**: trade-agent

**示例**:
```
用户："查询贵州茅台的价格"
→ 路由到：trade

用户："回测双均线策略"
→ 路由到：trade

用户："筛选低估值股票"
→ 路由到：trade
```

---

#### 3. main-default (默认路由)
**触发条件**: `default: true` (其他规则不匹配时)

**目标**: main-agent

**示例**:
```
用户："今天的新闻摘要"
→ 路由到：main

用户："你好"
→ 路由到：main

用户："帮我安排会议"
→ 路由到：main
```

---

## 🔧 技能权限管理

### 技能分类

#### 1. 全局技能 (所有代理可用)
- `clawhub`: 技能管理
- `read/edit/write`: 文件操作
- `exec`: 命令执行

#### 2. main 专用技能
- `message`: 消息推送 (DingTalk/WeCom)
- `web-search-pro`: 专业搜索

#### 3. dev 专用技能
- `glob`: 文件模式匹配
- `grep`: 内容搜索
- `coding-agent`: 代码生成 (通过 BAILIAN_API_KEY)

#### 4. trade 专用技能
- `web_search`: 网络搜索 (查询金融新闻)
- `web_fetch`: 网页内容提取
- `tushare_search`: Tushare 数据查询
- `akshare-stock`: AkShare 行情
- `stock-pick`: 选股工具
- `backtest`: VectorBT 回测

---

## 📝 技能元数据配置

### SKILL.md 中的 metadata

技能可以指定所需的环境变量和工具：

```yaml
---
name: stock-pick
description: 中证 1000 选股工具
metadata:
  openclaw:
    emoji: "📊"
    requires:
      env: ["TUSHARE_TOKEN"]
      bins: ["python3"]
---
```

### 权限控制方式

1. **环境变量控制**: 技能需要的 API Key 在 `.env` 中配置
2. **工具白名单**: 每个 agent 的 `tools.allow` 列表
3. **技能目录隔离**: 各 agent 的 skills 目录独立

---

## 🔒 安全注意事项

### 1. exec 权限

所有代理都有 `exec` 权限，但有以下限制：
- `exec.node: "local"` - 只能在本地执行
- 危险命令 (rm, chmod 等) 需要用户确认
- 可以通过 `openclaw exec-approvals` 管理审批

### 2. 外部消息

只有 main-agent 有 `message` 权限：
- 防止 dev/trade 擅自发送外部消息
- 所有交易通知必须通过 main 汇总

### 3. API Key 管理

```bash
# .env 文件权限
chmod 600 ~/.openclaw/.env

# 各代理使用各自的 API Key
# dev: BAILIAN_API_KEY (coding)
# trade: TUSHARE_TOKEN, JINA_API_KEY
```

---

## 🧪 测试验证

### 测试路由规则

```bash
# 测试 dev 路由
echo "帮我写一个 Python 函数" | openclaw chat
# 预期：dev-agent 响应

# 测试 trade 路由
echo "查询贵州茅台的价格" | openclaw chat
# 预期：trade-agent 响应

# 测试 main 默认
echo "今天的新闻摘要" | openclaw chat
# 预期：main-agent 响应
```

### 测试工具权限

```bash
# 测试 dev 的 glob 权限
openclaw use dev
echo "查找所有 Python 文件" | openclaw chat
# 预期：dev 可以使用 glob

# 测试 trade 的 web_search 权限
openclaw use trade
echo "搜索今天的金融新闻" | openclaw chat
# 预期：trade 可以使用 web_search

# 测试 dev 无 message 权限
openclaw use dev
echo "发送消息到 DingTalk" | openclaw chat
# 预期：dev 无法使用 message 工具
```

---

## 📊 权限变更历史

| 日期 | 变更内容 | 影响代理 |
|------|---------|---------|
| 2026-03-13 | 初始配置 | 所有代理 |
| 2026-03-13 | 添加路由规则 | main → dev/trade |
| 2026-03-13 | dev 添加 glob/grep | dev |
| 2026-03-13 | trade 添加 web_search/web_fetch | trade |

---

## 🔗 参考文档

- [OpenClaw 配置文档](https://docs.openclaw.ai/config)
- [技能开发指南](https://docs.openclaw.ai/skills)
- [路由规则配置](https://docs.openclaw.ai/routing)

---

**维护者**: main-agent  
**最后审查**: 2026-03-13
