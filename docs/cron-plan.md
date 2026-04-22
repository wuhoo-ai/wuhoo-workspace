# Wuhoo Cron 调度方案

## 目标
自动化日常交易和研究流程，减少人工干预。

---

## 方案概览

### 1. 每日 RSS 资讯采集 + 微信推送
**调度：** 每天 10:00 AM (HKT/CST)
**任务：**
- 运行 `news-rss/src/fetcher.py --fetch` 拉取所有RSS源
- 运行 `news-rss/src/fetcher.py --top 10 --json` 获取今日TOP10热点
- 筛选主题（AI/量化/港股/美股/宏观）各取TOP2
- 通过微信推送精选资讯

**Prompt：**
```
运行以下流程：
1. 执行 python3.11 ~/wuhoo-workspace/skills/news-rss/src/fetcher.py --fetch
2. 执行 python3.11 ~/wuhoo-workspace/skills/news-rss/src/fetcher.py --top 20 --json
3. 解析JSON结果，按类别分组（科技/AI、财经/投资、跨境电商、宏观政策）
4. 每个类别选热度最高的2条，生成中文摘要
5. 格式化为微信消息推送
```

---

### 2. 每日A/HK/US 数据更新
**调度：** 每个交易日 18:00 PM (收盘后)
**任务：**
- 运行 `stock-pick/update_all_data.py` 更新A股数据
- 运行 `stock-pick/fetch_hk_data.py` 更新港股数据
- 检查数据完整性

**Prompt：**
```
运行以下数据更新流程：
1. 执行 python3.11 ~/wuhoo-workspace/skills/stock-pick/update_all_data.py
2. 执行 python3.11 ~/wuhoo-workspace/skills/stock-pick/fetch_hk_data.py
3. 检查各市场数据文件数量和最后修改时间
4. 如果有异常（如文件缺失、数据量异常），报告错误
```

---

### 3. 每周持仓诊断 (Diagnose)
**调度：** 每周五 17:00 PM (美股收盘后)
**任务：**
- 运行 `diagnose/diagnose.py` 扫描OpenD持仓
- 对每只持仓重新评估（调用deep-analysis）
- 生成调仓建议报告

**Prompt：**
```
执行持仓诊断流程：
1. 通过Futu OpenD读取当前模拟盘持仓
2. 对每只持仓股票运行深度分析
3. 对比当前持仓与最新评估结果
4. 生成调仓建议（买入/卖出/持有）
5. 输出诊断报告
```

---

### 4. 每日美股等权 Rebalance
**调度：** 每个交易日 09:30 AM EST (美股开盘前)
**任务：**
- 运行 `stock-pick/stock_pick.py --market us` 选出美股
- 运行 `trade/us_equal_weight_portfolio.py` 计算等权配置
- 生成调仓订单
- 模拟盘执行（需确认后实盘）

**Prompt：**
```
执行美股等权rebalance流程：
1. 运行 python3.11 ~/wuhoo-workspace/skills/stock-pick/stock_pick.py --market us
2. 读取选股结果
3. 运行 us_equal_weight_portfolio.py 计算等权配置
4. 对比当前持仓，生成BUY/SELL订单
5. 通过risk_manager检查风控
6. 输出调仓报告（模拟模式）
```

---

### 5. 每日复盘报告
**调度：** 每天 22:00 PM
**任务：**
- 汇总当日市场动态
- 检查持仓表现
- 生成复盘报告

**Prompt：**
```
生成每日复盘报告：
1. 读取当日持仓数据
2. 计算当日收益/回撤
3. 检查是否有触发止损的持仓
4. 汇总当日重大新闻
5. 输出复盘报告
```

---

## 执行优先级
1. P0: RSS资讯推送（每日10:00）- 信息收集
2. P0: 数据更新（每日18:00）- 数据基础
3. P1: 美股rebalance（交易日09:30 EST）- 核心交易
4. P1: 持仓诊断（每周五）- 风险控制
5. P2: 每日复盘（每日22:00）- 总结改进

## 注意事项
- 所有cron任务使用独立session，不依赖当前对话上下文
- 交易相关任务默认使用模拟盘，实盘需用户确认
- RSS推送使用微信channel
- 失败任务需要记录错误并通知用户
