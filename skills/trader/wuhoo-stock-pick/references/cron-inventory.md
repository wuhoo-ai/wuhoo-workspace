# Wuhoo Cron Job Inventory — 2026-05-09

13 个定时任务的完整清单、设计模式与经验教训。

## 完整清单

### 每日任务（按时间排序）

| 时间 | 名称 | Schedule | 市场 | Skills | Delivery | 状态 |
|------|------|----------|:----:|--------|----------|------|
| 00:00 | 微信通道检查 | `0 */12 * * *` | — | — | local | ✅ ok |
| 03:00 | S&P500 成分股更新 | `0 3 * * 6` | US | wuhoo-stock-pick | local | 🆕 周六 |
| 08:00 | 市场数据更新 | `0 8 * * *` | CN/HK/US | wuhoo-stock-pick | local | ⚠️ error |
| 08:20 | 每日选股结果 | `20 8 * * 1-5` | CN/HK/US | wuhoo-stock-pick | local | 🆕 |
| 08:30 | 期货品种筛选 | `30 8 * * 1-5` | US/HK | wuhoo-futures-pick | local | 🆕 |
| 09:00 | 港股期货持仓诊断 | `0 9 * * 1-5` | HK | wuhoo-futures-trade | local | 🆕 |
| 09:00 | 系统健康日报 | `0 9 * * *` | — | — | local | 🆕 |
| 09:30 | RSS 资讯简报推送 | `30 9 * * *` | — | wuhoo-news-rss, wuhoo-rss-briefing | local | 🆕 |
| 10:00 | A股/港股 持仓诊断 | `0 10 * * *` | CN/HK | wuhoo-trade-diagnose, wuhoo-trade | local | ✅ ok |
| 22:00 | 美股等权调仓检查 | `0 22 * * 1` | US | wuhoo-stock-pick | local | 🆕 周一 |
| 22:30 | 美股期货持仓诊断 | `30 22 * * 1-5` | US | wuhoo-futures-trade | local | 🆕 |
| 23:00 | 美股 持仓诊断 | `0 23 * * *` | US | us-stock-portfolio-diagnosis, wuhoo-trade | local | ✅ ok |

### 每周维护

| 时间 | 名称 | 星期 |
|------|------|:----:|
| 03:00 | S&P 500 成分股自动更新 | 周六 |
| 08:00 | 三市场数据完整性交叉污染扫描 | 周六 |
| 22:00 | 美股等权调仓检查 | 周一 |

## 设计模式

### 1. Delivery 模式：统一 `local`

**原因**: WeChat Gateway 存在 asyncio `Timeout context manager should be used inside a task` bug，导致微信投递失败（内容已生成但无法推送）。

**方案**: 所有 13 个 cron 全部使用 `deliver=local`。输出保存到 cron 日志，需要时通过 `hermes cron show <job_id>` 查看或手动转发到微信。

**旧教训**: RSS 简报 cron（v1.0）曾因微信推送超时被删除（2026-05-03），改用 local 后于 2026-05-09 恢复。

### 2. 交易日模式：`1-5` vs 交易日脚本

| 模式 | 适用任务 | 说明 |
|------|----------|------|
| `1-5`（cron 内置） | 期货选品/诊断 | 简单粗暴，周末必定跳过。无法处理节假日 |
| 交易日检查脚本 | 股票持仓诊断 | 精细控制。`check_cn_trading_day.py` / `check_us_trading_day.py` 输出 JSON，cron prompt 先读 JSON 判断 |

### 3. Token 优化：`enabled_toolsets` 最小化

监控类/脚本执行类任务启用最小 toolset：

| 任务 | enabled_toolsets | 原因 |
|------|:---:|------|
| 系统健康日报 | `["terminal","file"]` | 纯 shell 命令，不需要 Python/web |
| 数据完整性扫描 | `["terminal","file"]` | 纯 shell 扫描 |
| S&P500 成分股更新 | `["terminal","file"]` | curl + Python 一行 |

其余任务不设置（使用默认 toolset）。

### 4. `workdir` 设置

期货任务需要指定工作目录以执行脚本：

| 任务 | workdir |
|------|---------|
| 期货品种筛选 | `~/wuhoo-workspace/skills/trader/wuhoo-futures-pick` |
| 港股期货持仓诊断 | `~/wuhoo-workspace/skills/trader/wuhoo-futures-trade` |
| 美股期货持仓诊断 | `~/wuhoo-workspace/skills/trader/wuhoo-futures-trade` |

### 5. 依赖链：时间编排隐式依赖

无显式的 cron 间依赖机制。通过时间间隔实现隐式依赖：

```
08:00 数据更新 ──→ 08:20 选股结果（等 CB efinance 可能 50min，选股只读已落盘数据）
            ──→ 08:30 期货品种筛选（期货数据源独立，不依赖股票数据）
```

选股 cron prompt 内置了数据存在性检查（`if daily_data 无数据 → 跳过`），避免在数据未就绪时静默失败。

## 已删除/废弃任务

| 名称 | 删除原因 | 日期 |
|------|----------|------|
| RSS 资讯推送（微信 delivery） | Gateway asyncio timeout bug | 2026-05-03 |
| 学习循环 | 微信 timeout bug，功能不再需要 | 2026-05-03 前 |

## 经验教训

1. **CN efinance 换手率阶段 50+ 分钟**是数据更新 cron 的主要瓶颈。选股和期货任务的时间编排需避免与之冲突。
2. **Tushare 节假日数据延迟**（月初无当月数据）是预期行为，无需修复。
3. **`local` delivery 是所有新建 cron 的默认选择**，除非微信推送已确认可用。
4. **工作日 cron 用 `1-5`**，全周 cron 用 `*`。区分清晰。
