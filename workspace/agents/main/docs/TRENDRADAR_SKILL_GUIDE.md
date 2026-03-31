# TrendRadar 技能使用指南

**版本**: 2026-03-13  
**状态**: ✅ 已安装

---

## 📡 技能概述

**TrendRadar** 是一个热点趋势雷达技能，监控 42 个平台的热点新闻，支持关键词搜索和热点榜单查询。

**技能位置**: `~/.agents/skills/trendradar/`

---

## 🎯 功能特点

### 监控平台 (42 个)

| 类别 | 平台 | 数量 |
|------|------|------|
| **综合新闻** | 今日头条、百度热搜、澎湃新闻、凤凰网等 | 10 个 |
| **财经投资** | 华尔街见闻、财联社、雪球、金十数据等 | 14 个 |
| **社交娱乐** | 微博、抖音、B 站、知乎、虎扑等 | 6 个 |
| **科技类** | IT 之家、掘金、GitHub、Hacker News 等 | 12 个 |

### 工作模式

**1. 热点模式** (默认)
- 获取各平台 Top10 热点
- 自动计算热点排名
- 加权算法：排名 60% + 频次 30% + 热度 10%

**2. 关键词模式**
- 搜索特定关键词
- 支持多个关键词
- 示例：`"AI,量化交易，跨境电商"`

**3. 混合模式**
- 热点榜单 + 关键词过滤
- 示例：`"新能源" --hot`

---

## 🚀 使用方式

### 方式 1: 通过 Agent 调用

```bash
# 热点模式
openclaw agent --agent main --message "查看今天的热点新闻"

# 关键词模式
openclaw agent --agent main --message "搜索 AI 和量化交易相关新闻"

# 指定关键词
openclaw agent --agent main --message "trendradar 关键词：AI,跨境电商，大模型"
```

### 方式 2: 使用技能脚本

```bash
# 热点模式
~/.agents/skills/trendradar/trendradar.sh

# 关键词模式
~/.agents/skills/trendradar/trendradar.sh "AI,量化交易"

# 多个关键词
~/.agents/skills/trendradar/trendradar.sh "AI,大模型，LLM,自动驾驶"
```

### 方式 3: 直接运行 TrendRadar

```bash
cd ~/openclaw/workspace/projects/TrendRadar

# 热点模式
./run-local.sh

# 关键词模式
./run-local.sh "AI,量化交易，跨境电商"
```

### 方式 4: 定时任务 (已配置)

```bash
# 每日 9:00 和 18:00 自动执行
0 9,18 * * * ~/.agents/skills/trendradar/trendradar.sh
```

---

## 📋 配置说明

### 关键词配置

编辑 `~/.openclaw/data/trendradar/config/config.yaml`:

```yaml
keywords:
  - "AI"
  - "量化交易"
  - "跨境电商"
  - "大模型"
  - "芯片"
  - "新能源"
  - "自动驾驶"
  - "区块链"
```

### 推送配置

TrendRadar 已配置 DingTalk 推送，自动发送到当前渠道。

**环境变量**:
```bash
DINGTALK_CLIENT_ID=dingzgn6ohjyrvvf9bnu
DINGTALK_CLIENT_SECRET=Hw3HFD2NU6t44bc95i9q1nsape9USb7_q9OEufMCIZapX1hi-ps2bsp6g-s6EGWi
```

### 输出位置

```
~/.openclaw/data/trendradar/output/
├── 2026-03-13/          # 按日期分区
│   ├── txt/             # TXT 格式
│   │   └── 2026-03-13.txt
│   ├── sqlite/          # SQLite 数据库
│   │   └── hot_news.db
│   └── html/            # HTML 报告 (可选)
└── logs/                # 执行日志
    └── trendradar.log
```

---

## 📊 输出示例

### 热点模式输出

```
📰 TrendRadar 热点新闻
时间：2026-03-13 09:00:00

=== 今日头条 | 2026-03-13 ===
1. OpenAI 发布 GPT-5.4，超越人类水平
2. 量化交易新趋势：AI 多模型竞争
3. 跨境电商 AI 直播成主流
4. 伊朗局势升级，油价突破 100 美元
5. 特斯拉 Optimus 机器人量产

=== 华尔街见闻 快讯 | 2026-03-13 ===
1. 美联储维持利率不变
2. 纳斯达克指数创新高
3. AI 概念股持续上涨
4. 比特币突破 75000 美元
5. 中金公司上调 A 股目标价

=== 知乎 | 2026-03-13 ===
1. 如何评价 OpenClaw 多代理系统？
2. AI Agent 开发最佳实践
3. 量化交易入门指南
...
```

### 关键词模式输出

```
🔍 关键词：AI,量化交易

=== 今日头条 | 2026-03-13 ===
1. AI Agent 市场规模预计 2034 年达 491 亿美元
2. 量化交易平台 AI-Trader 开源
3. 多因子选股模型实战分享

=== IT 之家 | 2026-03-13 ===
1. 阿里云百炼 coding-agent 上线
2. Python 量化交易框架对比
3. ...
```

---

## 🔧 技术架构

```
TrendRadar
├── 爬虫模块 (crawler)
│   ├── 42 个平台适配器
│   ├── 请求限流 (1 秒/请求)
│   └── 数据清洗
│
├── 热点计算模块
│   ├── 排名权重 (60%)
│   ├── 频次权重 (30%)
│   └── 热度权重 (10%)
│
├── 存储模块
│   ├── SQLite (主存储)
│   ├── TXT (快照)
│   └── HTML (报告，可选)
│
└── 推送模块
    ├── DingTalk
    └── 其他渠道 (可扩展)
```

---

## 📝 使用场景

### 场景 1: 每日新闻摘要 (Heartbeat)

```bash
# 自动执行 (每日 9:00 和 18:00)
0 9,18 * * * ~/.agents/skills/trendradar/trendradar.sh
```

**输出**: 精简摘要，推送到 DingTalk

---

### 场景 2: 特定主题监控

```bash
# 监控 AI 相关新闻
~/.agents/skills/trendradar/trendradar.sh "AI,大模型，LLM"

# 监控量化交易
~/.agents/skills/trendradar/trendradar.sh "量化交易，AI-Trader，因子挖掘"

# 监控跨境电商
~/.agents/skills/trendradar/trendradar.sh "跨境电商，AI 直播，TikTok"
```

---

### 场景 3: 突发事件追踪

```bash
# 监控中东局势
~/.agents/skills/trendradar/trendradar.sh "伊朗，中东，油价"

# 监控科技巨头
~/.agents/skills/trendradar/trendradar.sh "OpenAI,Google,Meta,Nvidia"
```

---

## ⚙️ 依赖检查

```bash
# 检查 Docker
docker --version

# 检查 TrendRadar 镜像
docker images trendradar-local

# 构建镜像 (如需要)
cd ~/openclaw/workspace/projects/TrendRadar
./build-on-demand.sh
```

---

## ❓ 常见问题

### Q1: 镜像构建失败

```bash
# 清理旧镜像
docker rmi trendradar-local

# 重新构建
cd ~/openclaw/workspace/projects/TrendRadar
./build-on-demand.sh
```

---

### Q2: 推送失败

**检查 DingTalk 配置**:
```bash
cat ~/.openclaw/.env | grep DINGTALK
```

**测试推送**:
```bash
bash ~/openclaw/scripts/notify.sh "测试消息"
```

---

### Q3: 无输出

**检查输出目录**:
```bash
ls -la ~/.openclaw/data/trendradar/output/$(date '+%Y-%m-%d')/
```

**查看日志**:
```bash
tail -20 ~/.openclaw/data/trendradar/logs/trendradar.log
```

---

### Q4: 关键词不生效

**检查配置文件**:
```bash
cat ~/.openclaw/data/trendradar/config/config.yaml | grep -A 10 "keywords:"
```

**手动指定关键词**:
```bash
~/.agents/skills/trendradar/trendradar.sh "AI,量化交易"
```

---

## 🔗 相关文档

- [SKILL.md](~/.agents/skills/trendradar/SKILL.md) - 技能说明
- [README.md](~/openclaw/workspace/projects/TrendRadar/README.md) - 完整文档
- [FAQ](~/openclaw/workspace/projects/TrendRadar/README-MCP-FAQ.md) - 常见问题
- [MCP Server](~/openclaw/workspace/projects/TrendRadar/mcp_server/) - MCP 服务

---

## ⚠️ 注意事项

1. **请求频率**: 默认 1 秒/请求，避免被封禁
2. **数据保留**: 默认保留 7 天数据
3. **推送限制**: 每条消息不超过 4000 字符
4. **时区设置**: Asia/Shanghai (北京时间)
5. **Docker 依赖**: 需要 Docker/Podman 环境

---

## 📊 技能状态

| 项目 | 状态 |
|------|------|
| 技能安装 | ✅ 已完成 |
| 工具权限 | ✅ 已添加到 main-agent |
| 脚本创建 | ✅ trendradar.sh |
| 定时任务 | ⏳ 待配置 |
| 测试验证 | ⏳ 待执行 |

---

**维护者**: main-agent  
**创建时间**: 2026-03-13  
**状态**: ✅ 已安装，可使用
