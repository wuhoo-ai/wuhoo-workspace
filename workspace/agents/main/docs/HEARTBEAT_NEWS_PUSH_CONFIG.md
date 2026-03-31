# Heartbeat 新闻推送配置

**版本**: 2026-03-13 15:27  
**状态**: ✅ 已优化

---

## 📅 推送时间

**北京时间 (UTC+8)**:
- ✅ 09:00 - 早间新闻
- ✅ 12:00 - 午间新闻
- ✅ 16:00 - 下午新闻
- ✅ 20:00 - 晚间新闻

**UTC 时间**: 01:00, 04:00, 08:00, 12:00

---

## 📰 推送内容 (拆分成 2 条)

### 消息 1: TrendRadar 热榜 Top20

**来源**: 42 个平台热点聚合

**格式**:
```
📰 TrendRadar 热榜 Top20

【今日头条 | 2026-03-13】
1. [新闻标题](https://链接)
2. [新闻标题](https://链接)
3. ...

【华尔街见闻 快讯 | 2026-03-13】
1. [新闻标题](https://链接)
2. ...
```

**特点**:
- ✅ 保留原文超链接
- ✅ Markdown 格式
- ✅ 每个分类 Top5

---

### 消息 2: 主题新闻 Top20

**主题**:
| 主题 | 关键词 | 数量 |
|------|--------|------|
| 🤖 AI | AI,大模型，LLM,Agent | Top5 |
| 📈 量化交易 | 量化交易，AI-Trader，因子 | Top5 |
| 💻 科技 | 科技，创业，融资，IPO | Top5 |
| 🏭 大宗商品 | 原油，黄金，铜，大豆 | Top5 |

**格式**:
```
📰 主题新闻 Top20

🤖 AI 主题 Top5
1. [新闻标题](https://链接)
2. [新闻标题](https://链接)
3. ...

📈 量化交易 Top5
1. [新闻标题](https://链接)
2. ...
```

---

## 📱 推送渠道 (仅限 2 个)

| 渠道 | Agent | 类型 | 用户 ID | 用户 |
|------|-------|------|--------|------|
| **钉钉** | main | direct | 01443329476136537748 | 郝海皎 ✅ |
| **企业微信** | main | direct | haohaijiao | 郝海皎 ✅ |

**不推送到**:
- ❌ 其他用户
- ❌ 任何群聊
- ❌ WebChat

---

## 🛠️ 技术实现

### 脚本位置

```bash
~/.openclaw/scripts/heartbeat-news.sh
```

### Cron 配置

```bash
# 北京时间 09:00/12:00/16:00/20:00
# UTC 时间 01:00/04:00/08:00/12:00
0 1,4,8,12 * * * ~/.openclaw/scripts/heartbeat-news.sh
```

### 推送流程

```
1. 执行 TrendRadar 获取热榜
   ↓
2. 发送消息 1: TrendRadar 热榜 Top20
   ↓ (等待 2 秒)
3. 使用 jina_search 搜索各主题新闻
   ↓
4. 发送消息 2: 主题新闻 Top20
   ↓
5. 记录日志
```

---

## 📋 推送格式示例

### 消息 1: TrendRadar 热榜

```markdown
📰 TrendRadar 热榜 Top20

时间：2026-03-13 09:00:00

【今日头条 | 2026-03-13】
1. [OpenAI 发布 GPT-5.4，超越人类水平](https://example.com/news1)
2. [量化交易新趋势：AI 多模型竞争](https://example.com/news2)
3. [跨境电商 AI 直播成主流](https://example.com/news3)
4. [伊朗局势升级，油价突破 100 美元](https://example.com/news4)
5. [特斯拉 Optimus 机器人量产](https://example.com/news5)

【华尔街见闻 快讯 | 2026-03-13】
1. [美联储维持利率不变](https://example.com/news6)
2. [纳斯达克指数创新高](https://example.com/news7)
3. [AI 概念股持续上涨](https://example.com/news8)
4. [比特币突破 75000 美元](https://example.com/news9)
5. [中金公司上调 A 股目标价](https://example.com/news10)

【微博 | 2026-03-13】
1. ...

【IT 之家 | 2026-03-13】
1. ...
```

---

### 消息 2: 主题新闻

```markdown
📰 主题新闻 Top20

时间：2026-03-13 09:00:00

🤖 AI 主题 Top5
1. [阿里云百炼发布 coding-agent](https://example.com/ai1)
2. [OpenClaw 多代理系统实战](https://example.com/ai2)
3. [Python 量化交易框架对比](https://example.com/ai3)
4. [AI Agent 市场规模达 491 亿美元](https://example.com/ai4)
5. [多因子选股模型实战分享](https://example.com/ai5)

📈 量化交易 Top5
1. [AI-Trader 开源项目更新](https://example.com/trade1)
2. [残差波动率因子优化](https://example.com/trade2)
3. [中证 1000 成分股筛选](https://example.com/trade3)
4. [VectorBT 回测框架教程](https://example.com/trade4)
5. [多模型竞争交易策略](https://example.com/trade5)

💻 科技主题 Top5
1. [科技巨头 AI 投资竞赛](https://example.com/tech1)
2. [创业公司融资动态](https://example.com/tech2)
3. [IPO 市场回暖](https://example.com/tech3)
4. [大模型技术突破](https://example.com/tech4)
5. [云计算市场增长](https://example.com/tech5)

🏭 大宗商品 Top5
1. [原油价格波动分析](https://example.com/commodity1)
2. [黄金避险需求上升](https://example.com/commodity2)
3. [铜价创历史新高](https://example.com/commodity3)
4. [大豆进口量增加](https://example.com/commodity4)
5. [铁矿石供应紧张](https://example.com/commodity5)

---
数据来源：Jina AI Search
推送渠道：钉钉、企业微信
```

---

## 🔧 配置说明

### TrendRadar 配置

**位置**: `~/.openclaw/data/trendradar/config/config.yaml`

```yaml
report:
  mode: "current"
  rank_threshold: 20  # Top20
  max_news_per_keyword: 5
```

### 推送白名单

**位置**: `~/.openclaw/scripts/heartbeat-news.sh`

```bash
# 推送白名单 (仅允许这两个用户)
DINGTALK_USER_ID="01443329476136537748"
WECOM_USER_ID="haohaijiao"
```

### 关键词配置

```bash
AI_KEYWORDS="AI,大模型，LLM,Agent，自动驾驶，机器学习"
TRADE_KEYWORDS="量化交易，AI-Trader，因子挖掘，多因子，选股策略"
TECH_KEYWORDS="科技，创业，融资，IPO，大模型"
COMMODITY_KEYWORDS="原油，黄金，铜，大豆，铁矿石，大宗商品"
```

---

## 🧪 测试方法

### 手动测试

```bash
# 执行测试推送 (发送 2 条测试消息)
~/.openclaw/scripts/test-heartbeat-push.sh

# 或手动执行一次正式推送
~/.openclaw/scripts/heartbeat-news.sh
```

### 查看日志

```bash
# 实时查看日志
tail -f ~/.openclaw/logs/heartbeat-news.log

# 查看最近 20 条
tail -20 ~/.openclaw/logs/heartbeat-news.log

# 测试日志
tail -f ~/.openclaw/logs/heartbeat-news-test.log
```

### 验证 cron

```bash
# 查看 cron 任务
crontab -l | grep heartbeat

# 验证 cron 语法
which cronlint && cronlint -f <(crontab -l)
```

---

## ⚠️ 注意事项

1. **推送时间**: 北京时间，注意时区
2. **推送限制**: 每条消息不超过 4000 字符
3. **消息拆分**: 分成 2 条推送 (热榜 + 主题)
4. **超链接**: Markdown 格式保留原文链接
5. **频率限制**: 消息之间等待 2 秒
6. **TrendRadar 依赖**: 需要 Docker 环境
7. **Jina API**: 需要有效的 API Key
8. **白名单限制**: 仅推送到指定 2 个用户

---

## 📊 监控指标

| 指标 | 目标值 | 当前状态 |
|------|--------|---------|
| 推送频率 | 4 次/天 | ✅ 已配置 |
| 推送渠道 | 2 个 (钉钉 + 企业微信) | ✅ 已配置 |
| 消息拆分 | 2 条 (热榜 + 主题) | ✅ 已配置 |
| 超链接保留 | 100% | ✅ 已配置 |
| TrendRadar 热榜 | Top20 | ✅ 已配置 |
| 主题新闻 | Top20 (4 主题×5 条) | ✅ 已配置 |
| 推送成功率 | >95% | ⏳ 待监控 |

---

## 🔗 相关文档

- [HEARTBEAT.md](~/openclaw/workspace/agents/main/HEARTBEAT.md) - Heartbeat 配置
- [TRENDRADAR_SKILL_GUIDE.md](./TRENDRADAR_SKILL_GUIDE.md) - TrendRadar 技能
- [NEWS_SKILLS_STATUS.md](./NEWS_SKILLS_STATUS.md) - 新闻检索技能

---

## 📝 下次推送

| 推送时间 | 北京时间 | UTC 时间 |
|---------|---------|---------|
| **下午新闻** | 2026-03-13 16:00 | 2026-03-13 08:00 |
| **晚间新闻** | 2026-03-13 20:00 | 2026-03-13 12:00 |
| **明日早间** | 2026-03-14 09:00 | 2026-03-14 01:00 |

---

**维护者**: main-agent  
**创建时间**: 2026-03-13 15:22  
**最后更新**: 2026-03-13 15:27  
**状态**: ✅ 已优化，待验证
