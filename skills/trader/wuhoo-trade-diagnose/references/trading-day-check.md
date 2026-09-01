# 交易日检查脚本

## 概述

定时任务通过 cronjob `script` 参数在每次执行前运行交易日检查脚本。脚本输出 JSON 到 stdout，被注入到 cron job prompt 上下文。

## 文件位置

| 文件 | 用途 |
|------|------|
| `~/wuhoo-workspace/scripts/check_trading_day.py` | 共享库，包含 `check_cn_trading_day()` 和 `check_us_trading_day()` |
| `~/.hermes/scripts/check_cn_trading_day.py` | CN 市场 cron pre-exec 脚本 |
| `~/.hermes/scripts/check_us_trading_day.py` | US 市场 cron pre-exec 脚本 |

> **⚠️ cronjob script 路径限制**：cronjob 的 `script` 参数必须是相对于 `~/.hermes/scripts/` 的文件名，不能使用绝对路径或传递命令行参数。因此需要为每个市场创建独立脚本。

## 数据源

- **CN/HK**: `akshare.tool_trade_date_hist_sina()` — 返回 A 股所有交易日列表
- **US**: `yfinance.Ticker("^GSPC").history(period="10d")` — 获取 S&P 500 最近交易记录，结合 weekday 判断周末

## 输出格式

```json
{
  "check_date": "2026-05-03",
  "results": [
    {
      "market": "CN",
      "is_trading_day": false,
      "next_trading_day": "2026-05-06"
    }
  ]
}
```

## 已知限制

- HK 市场使用 CN 日历（绝大多数交易日重合，仅部分本地假期不同）
- US 假期检测依赖 yfinance 最近 10 天记录，如遇长假期（如圣诞节）可能无法准确判断下一个交易日
