---
name: wuhoo-stock-pick
description: "可配置因子组合的多市场选股（A/HK/US）。支持自定义因子组合、分位阈值、排序方式。wuhoo 冠名 skill 为 Hermes 企业级关键 skill，需重点维护。"
tags: ["wuhoo"]
category: wuhoo
metadata: { "hermes": { "emoji": "📊", "requires": { "env": ["TUSHARE_TOKEN"], "bins": ["python3.11"] } } }
---

# wuhoo-stock-pick — 可配置因子多市场选股

> **⚠️ 企业级关键 Skill**
> 以 `wuhoo-` 冠头的 skill 是当前 Hermes 系统的**企业级关键 skill**，承担核心业务价值。
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
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-stock-pick

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
~/wuhoo-workspace/data/stock-pick/
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
curl -s https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv > /tmp/constituents.csv

# 转换格式并保存到 index_members_us_top500.csv + stock_info_us_top500.csv
python3.11 -c "
import pandas as pd
df = pd.read_csv('/tmp/constituents.csv')
members = df[['Symbol','Security']].drop_duplicates()
members.columns = ['code', 'name']
members['ts_code'] = members['code'] + '.US'
DATA_DIR = Path.home() / 'wuhoo-workspace' / 'data' / 'stock-pick'
members[['code','name','ts_code']].to_csv(DATA_DIR / 'index_members_us_top500.csv', index=False)
info = members[['ts_code','code','name']].copy()
info['total_market_val'] = 0
info.to_csv(DATA_DIR / 'stock_info_us_top500.csv', index=False)
print(f'Updated {len(members)} stocks')
"
```

### 关键陷阱：stock_info_us_top500.csv 格式

美股信息映射文件 `stock_info_us_top500.csv` 的 `ts_code` 列**必须为 `SYMBOL.US` 格式**（如 `NVDA.US`），而非 `US.SYMBOL`（如 `US.NVDA`）。如果格式错误，stock_pick.py 的名称匹配将全部返回 NaN，导致因子计算失败。

如果文件存在格式问题，需重新生成：
```bash
# 检查格式是否正确（应看到 NVDA.US 而非 US.NVDA）
head ~/wuhoo-workspace/data/stock-pick/stock_info_us_top500.csv
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

## 数据更新维护

### 数据路径

所有数据存储在 `~/wuhoo-workspace/data/stock-pick/`（非 `~/.hermes/data/`）。
脚本位于 `~/wuhoo-workspace/skills/wuhoo/wuhoo-stock-pick/`。

> 详细故障排查记录见 `references/data-update-troubleshooting.md`

### 数据更新预检（Cron Job 必做）

在定时任务中运行数据更新前，先验证前置条件，避免静默失败：

```bash
# 1. 检查 Tushare Token
[ -n "$TUSHARE_TOKEN" ] && echo "✅ TUSHARE_TOKEN" || echo "❌ TUSHARE_TOKEN 未设置"

# 2. 检查 Futu OpenD（港股必需）
curl -s --connect-timeout 3 http://127.0.0.1:11111/ > /dev/null 2>&1 && echo "✅ OpenD" || echo "❌ OpenD 未运行"

# 3. 检查 python3.11 和关键包
python3.11 -c "import tushare, pandas, yfinance; print('✅ 核心依赖')" 2>&1

# 4. 检查 A 股日线数据完整性（关键：daily_data/ 是否被美股数据污染）
python3.11 -c "
from pathlib import Path
import pandas as pd
d = Path.home() / 'wuhoo-workspace/data/stock-pick/daily_data/2026/202604.csv'
if d.exists():
    df = pd.read_csv(d, nrows=1)
    col = 'ts_code' if 'ts_code' in df.columns else df.columns[0]
    val = str(df[col].iloc[0])
    is_us = val[0].isalpha() and len(val) <= 5  # AAPL, MMM etc
    is_cn = '.' in val and val.split('.')[0].isdigit()  # 000001.SZ etc
    if is_us and not is_cn:
        print('🔴 严重：daily_data/ 包含美股数据，A股日线已损坏！需要 --force 重建')
    elif is_cn:
        print('✅ A股日线数据正常')
    else:
        print(f'⚠️ 无法判断数据来源: {val}')
else:
    print('⚠️ daily_data/2026/202604.csv 不存在')
"
```

### 美股数据更新

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-stock-pick
python3.11 update_all_data.py --market us --incremental
```

**⚠️ 已知问题：**
- `update_all_data.py` 的 yfinance 下载逻辑存在但未成功生成 `daily_data_us/` 目录
- 美股因子计算依赖 yfinance 实时下载，速度较慢
- 建议：预下载美股日线数据或改用单独的美股数据下载脚本

**🔴 致命陷阱：US/CN 数据文件冲突**
- `update_all_data.py --market us` 和 `--market cn` **共用** `daily_data/` 目录
- 美股数据是 yfinance 格式（列名: `Date,Open,High,Low,Close,Volume,ts_code,Adj Close`）
- A股数据是 Tushare 格式（列名: `ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount`）
- **先跑 US 再跑 CN 选股会报 `KeyError: 'trade_date'`** — 因为月度 CSV 已被美股格式覆盖
- **修复**: 见下方 "A股数据被污染后的并行修复"
- **根治**: 需要代码层面分离 `daily_data_us/` 和 `daily_data_cn/` 目录，目前仅靠操作顺序规避：**永远先跑 CN 数据更新，最后跑 US**；或在 US 更新后、CN 选股前强制重下 CN 数据

### A股数据被污染后的并行修复

当 `daily_data/` 月度 CSV 被 yfinance 格式覆盖后，需要从 Tushare 批量重建。**不要用 `update_all_data.py --market cn --force`** — 它是纯串行的，18 个月需 ~15 分钟。使用 ThreadPoolExecutor 并行补拉：

```bash
# 1. 识别所有被污染的月份（列头以 "Date," 开头 = yfinance 格式）
for f in ~/wuhoo-workspace/data/stock-pick/daily_data/*/20*.csv; do
  head -1 "$f" | grep -q "^Date," && echo "CORRUPT: $f"
done

# 2. 运行并行修复脚本
python3.11 /tmp/repair_cn_parallel.py
```

并行修复脚本模板（8 线程，84s 完成 13 个月）：
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading, time, calendar, pandas as pd, tushare as ts
from pathlib import Path

# ... (完整脚本见 references/20260430-audit.md 的修复过程)

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(download_month, ym): ym for ym in to_fix}
    for future in as_completed(futures):
        ym, count = future.result()
```

**关键提醒**：修复后必须**全量扫描所有月份**确认无遗漏：
```bash
bad=0
for f in ~/wuhoo-workspace/data/stock-pick/daily_data/*/20*.csv; do
  head -1 "$f" | grep -q "^Date," && { echo "STILL CORRUPT: $f"; bad=$((bad+1)); }
done
echo "Corrupted: $bad"  # 必须为 0 才能跑选股
```

**常见遗漏**：修复 2024-2025 年时容易忘记检查 2026 年 01-02 月是否也被污染。`pd.concat` 合并混列名 CSV 时会同时出现 `Date` 和 `trade_date` 两套列，静默导致因子计算结果为空（`results=[]` → `KeyError: 'ts_code'`）。

### `--force` 模式的性能陷阱

`update_all_data.py --market cn --force` 重新下载 ~18 个月的数据，但 **纯串行、无 ThreadPoolExecutor 实际使用**（虽然 import 了），每月 ~50 秒。完整运行需 12-15 分钟，且会卡在 efinance 换手率步骤。仅当需要全量重建时使用，并准备好在换手率步骤手动终止。

### efinance 换手率下载卡死处理

efinance 接口持续返回 0 成功率时会无限重试。判断标准：
- 进程无文件写入超过 5 分钟
- CPU 低（<5%）但有活跃网络连接
- `ps aux` 显示进程仍存在但 `/proc/<pid>/fd/` 只有 socket 无文件 FD

**处置**：`kill <pid>` 终止进程，日线数据已足够选股使用（换手率因子缺失属已知降级）。

### 多市场全量更新与选股审计流程

用户偏好审计追踪。正确执行顺序：

```bash
# 1. 前置检查
curl -s --connect-timeout 3 http://127.0.0.1:11111/  # OpenD?
grep TUSHARE_TOKEN ~/.hermes/.env | wc -c              # Token?

# 2. 启动 OpenD（如未运行）
bash ~/wuhoo-workspace/scripts/start_opend.sh start    # 需要 start 参数！

# 3. 并行更新数据（注意：CN 必须不晚于 US）
python3.11 update_all_data.py --market cn --incremental &
python3.11 fetch_hk_data.py --incremental &            # futu 全局可用，无需 venv
python3.11 update_all_data.py --market us --incremental &

# 4. 更新 S&P 500 成分股
curl -s https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv | ... 

# 5. 选股（可并行）
python3.11 stock_pick.py --market us --date YYYY-MM-DD
python3.11 stock_pick.py --market hk --date YYYY-MM-DD
python3.11 stock_pick.py --market cn --date YYYY-MM-DD

# 6. 验证输出
head ~/wuhoo-workspace/data/stock-pick/factors/result_{us,hk,cn}_YYYYMMDD.csv
```

### 港股 Futu OpenD 启动

### S&P 500 成分股补全

旧版 `index_members_us_top500.csv` 仅 242 只，需定期从 GitHub 更新到 503 只。

---

*创建时间：2026-03-12*
*更新时间：2026-05-01*
*版本：2.3 — 添加并行修复技术 + 全量扫描验证 + `--force` 性能陷阱 + 20260430 审计*

## 参考文件

- `references/20260430-audit.md` — 2026-04-30 全市场数据更新与选股审计记录（含 17 个月污染修复全过程）
- `references/data-update-troubleshooting.md` — 历次数据更新故障排查记录
