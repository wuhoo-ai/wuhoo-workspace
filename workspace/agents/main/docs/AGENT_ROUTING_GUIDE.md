# OpenClaw 多代理路由指南

**版本**: 2026-03-13  
**最后更新**: 2026-03-13 11:15 AM

---

## 📋 路由机制说明

OpenClaw 的多代理路由是通过 **channel 绑定** 实现的，而不是关键词匹配。

### 路由方式

```
用户消息 → Channel (DingTalk/Telegram) → 绑定的 Agent → 处理
```

### 当前配置

```bash
# 查看当前绑定
openclaw agents bindings
# 输出：No routing bindings.

# 查看可用 agents
openclaw agents list
# 输出：main, dev, trade
```

---

## 🔧 配置方案

### 方案 1: 按 Channel 路由 (推荐)

不同 channel 绑定不同 agent：

```bash
# DingTalk → main (默认)
# Telegram → dev
# WeCom → trade

# 绑定 dev 到 Telegram
openclaw agents bind --agent dev --bind telegram

# 绑定 trade 到 WeCom
openclaw agents bind --agent trade --bind wecom

# 查看绑定
openclaw agents bindings
```

**优点**:
- ✅ 简单明了
- ✅ 不同渠道用户访问不同专业 agent
- ✅ 无需关键词判断

**缺点**:
- ❌ 同一渠道用户无法自动路由到不同 agent

---

### 方案 2: 用户手动切换

用户在对话中指定 agent：

```bash
# 切换到 dev
/dev 帮我写个代码

# 切换到 trade  
/trade 查询股票价格

# 切换到 main
/main 今天的新闻
```

**实现方式**: 在 SOUL.md 中定义命令前缀路由

---

### 方案 3: main 代理内部分流 (当前方案)

所有消息先到 main，main 根据内容判断是否转交：

```
用户 → main-agent → 判断任务类型 → 内部调用 dev/trade
```

**实现方式**: 在 main 的 SOUL.md 中定义路由逻辑

---

## 🎯 推荐配置

### 当前配置 (方案 3)

所有渠道默认绑定 main，由 main 内部分流：

```bash
# 不设置任何 binding，所有消息默认到 main
openclaw agents bindings
# 输出：No routing bindings. (正确)
```

**main 的路由逻辑** (在 SOUL.md 中定义):

```markdown
### 任务路由
识别到专业任务时:
- 代码相关 → "这个问题 dev-agent 更擅长，我来转交"
- 交易相关 → "需要 trade-agent 分析市场数据"
- 不确定 → 先尝试自己处理，搞不定再求助
```

---

## 📊 工具权限配置

### 当前权限

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

### 权限说明

**main-agent**:
- ✅ 完整搜索工具 (web_search, web_fetch, web-search-pro)
- ✅ 唯一可以发送外部消息 (message)
- ❌ 无 glob/grep (代码搜索交给 dev)

**dev-agent**:
- ✅ 代码搜索工具 (glob, grep)
- ✅ 完整文件操作
- ❌ 无网络搜索 (专注代码)
- ❌ 无外部消息

**trade-agent**:
- ✅ 网络搜索 (查询金融新闻)
- ✅ 代码搜索 (分析策略代码)
- ❌ 无外部消息

---

## 🛠️ 使用示例

### dev-agent 使用

```bash
# 切换到 dev
openclaw use dev

# 代码任务
"帮我写一个 Python 函数计算移动平均线"
"修复这个 bug"
"审查这段代码"
"实现一个新的 skill"
```

### trade-agent 使用

```bash
# 切换到 trade
openclaw use trade

# 交易任务
"查询贵州茅台今天的价格"
"回测双均线策略"
"分析今天的资金流向"
"筛选低估值股票"
```

### main-agent 使用

```bash
# 默认使用 main
openclaw use main

# 通用任务
"今天的新闻摘要"
"帮我安排会议"
"路由到 dev 实现功能"
"路由到 trade 查询股票"
```

---

## 🔒 安全注意事项

### exec 权限

所有代理都有 `exec` 权限，但有以下限制：
- `exec.node: "local"` - 只能在本地执行
- 危险命令 (rm, chmod 等) 需要用户确认
- 可以通过 `openclaw approvals` 管理审批

### 外部消息

只有 main-agent 有 `message` 权限：
- 防止 dev/trade 擅自发送外部消息
- 所有交易通知必须通过 main 汇总

### API Key 管理

```bash
# .env 文件权限
chmod 600 ~/.openclaw/.env

# 各代理使用各自的 API Key
# main/dev: BAILIAN_API_KEY (通用)
# trade: TUSHARE_TOKEN, JINA_API_KEY
```

---

## 📝 配置验证

### 检查配置

```bash
# 验证配置有效性
openclaw doctor

# 查看 agents 配置
openclaw config get agents

# 查看工具权限
openclaw config get tools
```

### 测试路由

```bash
# 测试 dev
openclaw use dev
echo "帮我写代码" | openclaw chat

# 测试 trade
openclaw use trade
echo "查询股票" | openclaw chat

# 测试 main
openclaw use main
echo "新闻摘要" | openclaw chat
```

---

## 🔗 参考文档

- [OpenClaw Agents CLI](https://docs.openclaw.ai/cli/agents)
- [多代理路由概念](https://docs.openclaw.ai/concepts/multi-agent)
- [Agent Workspace](https://docs.openclaw.ai/concepts/agent-workspace)

---

**维护者**: main-agent  
**最后审查**: 2026-03-13
