# Skills 使用指南

**更新时间**: 2026-03-11 13:45 GMT+8  
**状态**: ✅ 全部就绪 (12/12)

---

## 📊 Skills 总览

| # | Skill | 用途 | 触发方式 | 状态 |
|---|-------|------|----------|------|
| 1 | **skill-vetter** | 安全审核 | 被动 | ✅ |
| 2 | **openclaw-backup** | 数据备份 | 主动/被动 | ✅ |
| 3 | **openclaw-tavily-search** | AI 搜索 | 被动 | ✅ |
| 4 | **browse** | 浏览器自动化 | 被动 | ✅ |
| 5 | **self-improving-agent** | 自我改进 | 被动 | ✅ |
| 6 | **jina_search** | 网络搜索 | 被动 | ✅ |
| 7 | **tushare_search** | 股票数据 | 被动 | ✅ |
| 8 | **web-search-pro** | 专业搜索 | 被动 | ✅ |
| 9 | **file-search** | 文件搜索 | 被动 | ✅ |
| 10 | **weather** | 天气查询 | 被动 | ✅ |
| 11 | **clawhub** | Skill 管理 | 主动 | ✅ |
| 12 | **find-skills** | Skill 发现 | 被动 | ✅ |

---

## 🔒 安全与基础

### 1. skill-vetter 🛡️

**用途**: 安装任何 Skill 前的安全审核

**触发方式**: 被动（安装 Skill 前手动调用）

**使用示例**:
```
用户：帮我安装 tavily-search skill
Agent: [自动调用 skill-vetter 审核]
       正在审核 tavily-search...
       ✅ 安全检查通过，可以安装
```

**如何观察效果**:
- 安装 Skill 前会显示审核报告
- 列出所有检查项和结果
- 发现危险代码会立即警告

**最佳实践**:
- 安装任何 Skill 前必须使用
- 仔细阅读审核报告
- 发现红色警告立即停止

---

### 2. openclaw-backup 💾

**用途**: 自动备份 OpenClaw 配置和数据

**触发方式**: 主动 + 被动

**主动使用**:
```
用户：备份当前配置
Agent: [调用 openclaw-backup]
       ✅ 已创建备份：backup-20260311-134500
```

**被动触发**:
- 安装新 Skill 前自动备份
- 配置变更前自动备份

**如何观察效果**:
- 备份成功后显示备份文件名
- 备份位置：`~/.openclaw/backups/`
- 可通过 `openclaw-backup list` 查看

**最佳实践**:
- 重大变更前手动备份
- 定期自动备份（可配置 cron）

---

## 🔍 搜索类 Skills

### 3. openclaw-tavily-search 🔍

**用途**: AI 优化的网页搜索

**触发方式**: 被动

**使用示例**:
```
用户：搜索最新的 AI 量化交易研究
Agent: [调用 tavily-search]
       找到以下相关信息：
       1. [论文] AI 在量化交易中的最新应用...
       2. [文章] 2026 年 AI 交易策略综述...
```

**如何观察效果**:
- 搜索结果显示在对话中
- 每条结果包含标题、来源、摘要
- 可点击链接查看原文

**配置**:
- 需要 `TAVILY_API_KEY` (已配置)
- 免费额度：1000 次/月

---

### 4. jina_search 🔎

**用途**: Jina AI 高质量搜索

**触发方式**: 被动

**使用示例**:
```
用户：查找跨境电商直播的方案
Agent: [调用 jina_search]
       搜索到以下结果：
       1. [知乎] 跨境直播数字人方案...
       2. [36 氪] AI 直播电商趋势...
```

**如何观察效果**:
- 高质量搜索结果
- 自动过滤低质内容
- 优先展示权威来源

**配置**:
- `JINA_API_KEY` 已配置 (付费)

---

### 5. web-search-pro 🔍

**用途**: 多引擎专业搜索

**触发方式**: 被动

**使用示例**:
```
用户：搜索高分子材料最新研究
Agent: [调用 web-search-pro]
       多引擎搜索结果：
       [Google] ...
       [Bing] ...
       [学术] ...
```

**如何观察效果**:
- 显示多个搜索引擎结果
- 结果去重和排序
- 支持时间过滤

---

### 6. find-skills 📦

**用途**: 帮助用户发现新 Skills

**触发方式**: 被动

**使用示例**:
```
用户：有没有能帮我写代码的 skill？
Agent: [调用 find-skills]
       找到以下相关 Skills:
       1. coding-agent - 编码助手
       2. github - GitHub 集成
       3. debug-pro - 调试工具
```

**如何观察效果**:
- 列出相关 Skills
- 显示评分和下载量
- 提供安装命令

---

## 🌐 浏览器自动化

### 7. browse 🌐

**用途**: 浏览器自动化操作

**触发方式**: 被动

**使用示例**:
```
用户：帮我打开 GitHub 看看 trending 项目
Agent: [调用 browse]
       正在打开 GitHub...
       ✅ 已截图，当前 trending:
       1. project-a
       2. project-b
```

**如何观察效果**:
- 浏览器操作过程
- 截图显示结果
- 可查看页面内容

**依赖**:
- `agent-browser` ✅ 已安装 (v0.17.1)

**最佳实践**:
- 适合复杂网页交互
- 可自动化重复操作
- 支持截图和录制

---

## 📈 专业数据

### 8. tushare_search 📈

**用途**: A 股股票数据查询

**触发方式**: 被动

**使用示例**:
```
用户：查询贵州茅台的日线行情
Agent: [调用 tushare_search]
       贵州茅台 (600519.SH) 日线:
       日期       开盘    收盘    成交量
       20260311  1700   1720   12345
```

**如何观察效果**:
- 显示股票数据表格
- 支持多种查询类型
- 数据来自 Tushare Pro

**配置**:
- `TUSHARE_TOKEN` 已配置 (2120 积分)

---

### 9. weather 🌤️

**用途**: 天气查询

**触发方式**: 被动

**使用示例**:
```
用户：北京今天天气怎么样？
Agent: [调用 weather]
       北京天气：
       晴，15-25°C
       湿度：45%
       风力：北风 3 级
```

**如何观察效果**:
- 实时天气数据
- 支持全球城市
- 支持预报

**依赖**:
- wttr.in API (免费，无需 Key)

---

## 🔧 工具类

### 10. file-search 📁

**用途**: 本地文件搜索

**触发方式**: 被动

**使用示例**:
```
用户：帮我找一下包含"trading"的文件
Agent: [调用 file-search]
       找到以下文件：
       1. ~/workspace/AI-Trader/trading.py
       2. ~/notes/trading-notes.md
```

**如何观察效果**:
- 列出匹配文件
- 支持内容搜索
- 支持文件名匹配

**最佳实践**:
- 快速定位文件
- 支持递归搜索
- 支持正则表达式

---

### 11. clawhub 📦

**用途**: Skill 管理工具

**触发方式**: 主动

**主动使用**:
```
用户：列出已安装的 Skills
Agent: [调用 clawhub list]
       已安装 Skills:
       1. skill-vetter
       2. openclaw-backup
       ...
```

**命令行使用**:
```bash
clawhub list              # 列出已安装
clawhub search "search"   # 搜索 Skills
clawhub install <skill>   # 安装 Skill
```

**如何观察效果**:
- 显示 Skills 列表
- 显示版本和状态
- 提供管理命令

---

### 12. self-improving-agent 🔄

**用途**: Agent 自我改进

**触发方式**: 被动

**使用示例**:
```
用户：这个方案有问题，应该...
Agent: [调用 self-improving-agent]
       已记录改进建议：
       - 问题：方案不完整
       - 改进：添加实施步骤
       - 已保存到记忆
```

**如何观察效果**:
- 记录用户反馈
- 自动改进响应
- 建立长期记忆

**最佳实践**:
- 提供明确反馈
- 定期回顾改进
- 积累领域知识

---

## 📋 使用场景总结

### 安全相关
| 场景 | 使用 Skill |
|------|-----------|
| 安装新 Skill | skill-vetter (先审核) |
| 配置变更前 | openclaw-backup (先备份) |

### 搜索相关
| 场景 | 使用 Skill |
|------|-----------|
| 一般搜索 | jina_search |
| AI 优化搜索 | openclaw-tavily-search |
| 多引擎搜索 | web-search-pro |
| 找 Skills | find-skills |

### 数据相关
| 场景 | 使用 Skill |
|------|-----------|
| 股票数据 | tushare_search |
| 天气查询 | weather |
| 文件查找 | file-search |

### 自动化相关
| 场景 | 使用 Skill |
|------|-----------|
| 网页操作 | browse |
| 代码编写 | coding-agent (已有) |
| GitHub 操作 | github (已有) |

### 改进相关
| 场景 | 使用 Skill |
|------|-----------|
| 学习反馈 | self-improving-agent |
| Skill 管理 | clawhub |

---

## 🔍 观察效果的方法

### 1. 对话日志
- 所有 Skill 调用都在对话中显示
- 可查看调用过程和结果
- 日志位置：`/tmp/openclaw/openclaw-*.log`

### 2. Dashboard
- 访问：http://172.20.53.18:18789/
- 查看会话历史
- 监控 Skill 使用情况

### 3. 命令行检查
```bash
# 查看 Skills 状态
openclaw skills check

# 查看特定 Skill
openclaw skills info <skill-name>

# 查看日志
tail -f /tmp/openclaw/openclaw-*.log
```

---

## ⚠️ 注意事项

1. **API 限制**:
   - Tavily: 1000 次/月 (免费)
   - Jina: 付费账户
   - Tushare: 2120 积分

2. **依赖工具**:
   - browse: agent-browser ✅ 已安装
   - 其他：无额外依赖

3. **最佳实践**:
   - 安装 Skill 前先用 skill-vetter 审核
   - 重大变更前先备份
   - 定期清理不用的 Skills

---

**文档结束**
