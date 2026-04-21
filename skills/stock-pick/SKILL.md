---
name: wuhoo-stock-pick
description: "可配置因子组合的多市场选股（A/HK/US）。支持自定义因子组合、分位阈值、排序方式。wuhoo 冠名 skill 为 OpenClaw 企业级关键 skill，需重点维护。"
metadata: { "hermes": { "emoji": "📊", "requires": { "env": ["TUSHARE_TOKEN"], "bins": ["python3.11"] } } }
---

# wuhoo-stock-pick — 可配置因子多市场选股

> **⚠️ 企业级关键 Skill**
> 以 `wuhoo-` 冠头的 skill 是当前 OpenClaw 系统的**企业级关键 skill**，承担核心业务价值。
> 这些 skill 的代码质量、稳定性和可维护性需要重点维护。

## 功能概述

基于**可配置因子组合**对 A股/港股/美股进行多因子选股。因子组合、分位阈值、排序方式均可通过 CLI 参数或 JSON 配置文件自定义。

**与因子挖掘的区别**：本 skill 不挖掘新因子，而是基于用户指定的因子组合进行选股。因子组合的探索和优化应通过研究流程完成。

## 市场与默认因子

| 市场 | 代码 | 数据源 | 默认因子 | 排序方式 |
|------|------|--------|----------|----------|
| A股 | cn | Tushare Pro | 残差波动率 + 换手率 + 动量 + Beta | 10日动量，越低越好 |
| 港股 | hk | 富途 OpenAPI | 波动率 + 动量 | 10日动量，越低越好 |
| 美股 | us | yfinance | 残差波动率 + 成交量 + 动量 + Beta | 10日动量，越低越好 |

## 因子配置方式

### 方式一：使用默认配置（向后兼容）

```bash
python stock_pick.py --market cn --date 2026-04-15
```

使用内置的默认因子组合和分位阈值。

### 方式二：JSON 配置文件覆盖

```bash
python stock_pick.py --market cn --date 2026-04-15 --factors-json my_factors.json
```

配置文件格式：

```json
{
  "cn": {
    "factors": ["residual_vol", "turnover_5d", "momentum_5d", "beta_20d"],
    "percentiles": {
      "residual_vol": 0.50,
      "turnover_5d": 0.50,
      "momentum_5d": 0.30,
      "beta_20d": 0.30
    },
    "sort_factor": "momentum_10d",
    "sort_ascending": true
  }
}
```

### 方式三：CLI 参数覆盖

```bash
# 自定义 Top-N
python stock_pick.py --market cn --date 2026-04-15 --top-n 20
```

## 使用方式

```bash
# 所有命令必须使用 python3.11（系统 python3 为 3.6.8 不兼容）
cd ~/wuhoo-skills/wuhoo-stock-pick

# A 股选股（使用默认因子）
python3.11 stock_pick.py --market cn --date 2026-04-15

# 港股选股（简化因子）
python3.11 stock_pick.py --market hk --date 2026-04-15

# 美股选股（完整因子，yfinance 数据源）
python3.11 stock_pick.py --market us --top-n 20

# 更新 A 股数据
python3.11 stock_pick.py --market cn --update-data

# 自定义 Top-N
python3.11 stock_pick.py --market cn --date 2026-04-15 --top-n 20

# 使用自定义因子配置
python3.11 stock_pick.py --market cn --date 2026-04-15 --factors-json configs/my_factors.json
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--market` | 市场 (cn/hk/us) | cn |
| `--date` | 选股日期 (YYYY-MM-DD) | 昨天 |
| `--update-data` | 更新 A 股日线 + 换手率数据 | False |
| `--force` | 强制更新数据 | False |
| `--top-n` | 最终选股数量 | 10 |
| `--factors-json` | 因子配置 JSON 文件路径 | None（使用内置默认值） |

## 默认因子定义

| 因子 | 计算方式 | 排序 | 默认筛选比例 |
|------|----------|------|----------|
| 252 日残差收益波动率 | 过去 252 日残差收益标准差（年化） | 越低越好 | 前 50% |
| 5 日平均换手率 | 过去 5 日换手率均值（SMA） | 越高越好 | 前 50% |
| 5 日价格动量 | TA-Lib ROC(5) | 越高越好 | 前 30% |
| 20 日 Beta 值 | 相对指数的 20 日 Beta | 越高越好 | 前 30% |

**最终排序**: 过去 10 日价格动量（越低越好），输出 Top N

## 输出

```
~/.hermes/data/stock-pick/
├── daily_data/          # 日线数据（按月存储）
├── turnover_data/       # 换手率数据
├── factors/             # 因子计算结果 + 选股结果
│   ├── factors_cn_YYYYMMDD.csv
│   ├── result_cn_YYYYMMDD.csv
│   └── factors_hk_YYYYMMDD.csv
│   └── factors_us_YYYYMMDD.csv
│   └── result_us_YYYYMMDD.csv
├── backups/             # 配置备份
├── index_members.csv    # A 股成分股
├── index_members_hk_top500.csv
├── index_members_us_top500.csv   # S&P 500 成分股（从 GitHub 动态更新）
├── stock_info_us_top500.csv      # 美股信息映射（ts_code 格式: SYMBOL.US）
└── stock_names.csv      # A 股名称映射
```

## 美股 S&P 500 成分股更新流程

硬编码的成分股列表（约 232 只）严重不完整。S&P 500 实际约 503 只，需从 GitHub 动态获取：

```bash
# 从 GitHub 获取最新 S&P 500 成分股列表（约 503 只）
curl -s https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv > constituents.csv

# 提取 Symbol 列，去重后转换为 index_members_us_top500.csv 格式
python3.11 -c "
import pandas as pd
df = pd.read_csv('constituents.csv')
df[['Symbol','Name']].drop_duplicates().to_csv(
    '~/.hermes/data/stock-pick/index_members_us_top500.csv', index=False,
    header=['ts_code','name'])
"
```

### 关键陷阱：stock_info_us_top500.csv 格式

美股信息映射文件 `stock_info_us_top500.csv` 的 `ts_code` 列**必须为 `SYMBOL.US` 格式**（如 `NVDA.US`），而非 `US.SYMBOL`（如 `US.NVDA`）。如果格式错误，stock_pick.py 的名称匹配将全部返回 NaN，导致因子计算失败。

如果文件存在格式问题，需重新生成：
```bash
# 检查格式是否正确（应看到 NVDA.US 而非 US.NVDA）
head ~/.hermes/data/stock-pick/stock_info_us_top500.csv
```

### 双类股过滤

S&P 500 中存在同公司双类股（如 GOOG/GOOGL），需在选股后手动过滤，避免重复暴露。

## 依赖

```bash
pip install tushare pandas numpy talib efinance yfinance
```

A 股需要 `TUSHARE_TOKEN` 环境变量。港股需要富途 OpenD 运行在 `127.0.0.1:11111`。美股使用 yfinance 数据源，无需额外 API。

## 与其他 Workflow 的关系

| Skill | 对应 Workflow | 用途 |
|-------|--------------|------|
| wuhoo-stock-pick | 选股 | 多因子选股（被 Workflow C 调用） |
| wuhoo-stock-deep-analysis | Workflow B | 单股深度分析 |
| wuhoo-stock-trade | Workflow C | 多市场自动选股交易 |

---

*创建时间：2026-03-12*
*更新时间：2026-04-15*
*版本：2.0 — 可配置因子 + 多市场 + 重命名 wuhoo-stock-pick*
