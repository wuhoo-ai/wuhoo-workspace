# Wuhoo Cron 调度方案

## 目标
自动化日常交易和研究流程，减少人工干预。

---

## 方案概览

### 1. 每日 RSS 资讯采集 + 微信推送
**调度：** 每天 10:00 AM (HKT/CST)
**任务：**
- 运行 `news-rss/src/fetcher.py --fetch` 拉取所有RSS源
- 运行 `news-rss/src/fetcher.py --top 50 --json` 获取TOP50
- 按6个主题分别筛选并各取TOP10：军事、科技、芯片、机器人、财经/投资、宏观政策
- 分段推送，每个主题10条

**Prompt：**
```
运行以下流程：
1. 执行 python3.11 ~/wuhoo-workspace/skills/news-rss/src/fetcher.py --fetch
2. 执行 python3.11 ~/wuhoo-workspace/skills/news-rss/src/fetcher.py --top 50 --json
3. 按主题（军事/科技/芯片/机器人/财经/宏观）各取TOP10
4. 分段输出，格式：【主题】\n1. 标题 | 来源 | 热度分\n   摘要
5. 通过微信推送分段简报
```

---

### 2. 市场数据更新
**调度：** 每周六 10:00 AM
**任务：**
- 运行 `stock-pick/update_all_data.py` 更新A股数据
- 运行 `stock-pick/fetch_hk_data.py` 更新港股数据
- 检查数据完整性

---

### 3. 每日持仓诊断 (Diagnose)
**调度：** 每天 09:00 AM
**任务：**
- 通过Futu OpenD读取模拟盘持仓（账户ID: 18767293）
- 对每只持仓运行深度分析
- 对比当前持仓与最新评估，生成调仓建议
- 输出诊断报告

---

## 已取消
- ~~美股等权 Rebalance~~ - 用户明确不需要定时执行，手动触发
- ~~每日复盘~~ - 暂不启用

## 执行优先级
1. P0: 每日持仓诊断（每天09:00）- 交易决策
2. P0: RSS资讯推送（每天10:00）- 信息收集
3. P1: 数据更新（每周六10:00）- 数据基础

## 注意事项
- 所有cron任务使用独立session，不依赖当前对话上下文
- 交易相关任务默认使用模拟盘，实盘需用户确认
- RSS推送使用微信channel
- 失败任务需要记录错误并通知用户
