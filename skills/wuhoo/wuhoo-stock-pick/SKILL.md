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
| 港股 | hk | **yfinance + ^HSI 基准** | **残差波动率 + 换手率(Volume) + 动量 + Beta** | 10日动量，越低越好 |
| 美股 | us | yfinance + SPY 基准 | 残差波动率 + 成交量 + 动量 + Beta | 10日动量，越低越好 |

> **v4.1 (2026-06-08)**: 港股因子全面升级。原 2 因子简版（波动率+动量）仅覆盖 5% 股票且全是银行。现改为 yfinance 批量下载 + ^HSI 基准的 5 因子完整模型（与 A 股/美股同级），覆盖率达 98.4%（492/500）。详见 `references/20260608-hk-factor-upgrade.md`。

> ⚠️ **港股选股已知缺陷**（2026-06-08 诊断）：
> 1. **数据覆盖率极低**：Futu 实时 K 线拉取 500 只仅 ~25 只有效（5%），其余静默失败。需改用 yfinance 批量替代。
> 2. **因子偏差 → 银行垄断**：仅用 2 因子（波动率 + 动量），波动率阈值 <25.84 自动过滤所有科技股（美团 35%、比亚迪 37%、中芯 55%），低波动银行（19-25%）天然通过且全部入选。

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
| 20 日 Beta 值 | 相对指数的 20 日 Beta | 越高越好 | 前 20% + 硬地板 ≥1.0 |

**最终排序**: 过去 10 日价格动量（越低越好），输出 Top N

**新增：行业分散约束**（v4.0，2026-06-08）：最终选股阶段限制单行业 ≤ `MAX_PER_INDUSTRY` 只（默认 3），避免过度集中于单一板块。行业数据从 Tushare `stock_basic` API 获取并缓存到 `stock_industry.csv`。若候选池不足以填满行业分散要求，按排序放宽补充。

### 分位阈值可配置性

> **2026-06-08 调整**：Beta 分位从 0.30（前 30%）收紧至 0.20（前 20%），并新增 `BETA_HARD_FLOOR = 1.0`（绝对地板）。
> 原因：原阈值 β ≥ 0.57 过松，筛选出大量 β<1 的防御型股票，与超跌反弹策略矛盾。
> 新阈值取 `max(P80分位, 1.0)`，确保仅保留高贝塔攻击型标的。

## 输出

```
~/wuhoo-workspace/data/stock-pick/
├── daily_data/          # A股日线（按月存储，Tushare 格式）
├── daily_data_hk/       # 港股日线（按月存储，Futu 格式）
├── daily_data_us/       # 美股日线（按月存储，yfinance 格式）
├── turnover_data/       # A股换手率数据
├── factors/             # 因子计算结果 + 选股结果
│   ├── factors_cn_YYYYMMDD.csv
│   ├── result_cn_YYYYMMDD.csv
│   ├── factors_hk_YYYYMMDD.csv
│   ├── result_hk_YYYYMMDD.csv
│   ├── factors_us_YYYYMMDD.csv
│   └── result_us_YYYYMMDD.csv
├── backups/             # 配置备份
├── index_members.csv    # A 股中证1000成分股
├── index_members_hk_top500.csv
├── index_members_us_top500.csv   # S&P 500 成分股
├── stock_info_us_top500.csv      # 美股信息映射（ts_code 格式: SYMBOL.US）
└── stock_names.csv      # A 股名称映射
```
>
> **v2.4 更新**：三市场日线现已独立存储到 `daily_data/` (A股), `daily_data_hk/` (港股), `daily_data_us/` (美股)。不再存在 US/CN 数据覆盖问题。

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

## Market Regime → 选股路由（Cron Job 专用）

每日 cron 选股流程：先跑 `market_regime.py` 判定市场状态，再按 regime 路由到对应选股策略。

### 路由规则

| Regime | 策略 | 仓位 | 工具 |
|--------|------|------|------|
| BULL_TRENDING | trend_momentum | 100% | ⚠️ 见下方限制 |
| BULL_VOLATILE | trend_momentum | 75% | ⚠️ 见下方限制 |
| RANGING | oversold_rebound | 80% | `stock_pick.py` |
| BEAR_VOLATILE | oversold_rebound (defensive) | 50% | `stock_pick.py` |
| BEAR_TRENDING | 空仓 (cash_only) | 0% | 不选股 |

### 执行命令

```bash
# 1. 判定市场状态
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-trade
python3.11 market_regime.py --market all --save 2>&1

# 2. 读取 regime JSON
REGIME_FILE=$(ls -t ~/wuhoo-workspace/data/regime/regime_all_*.json 2>/dev/null | head -1)

# 3. 对每个市场按 strategy 字段执行：
#    - oversold_rebound → stock_pick.py
#    - trend_momentum → ⚠️ trend_momentum.py 仅做回测（见下）
#    - cash_only → 跳过

# RANGING / BEAR_VOLATILE（超跌反弹）
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-stock-pick
python3.11 stock_pick.py --market <market> --date $(date +%Y-%m-%d) --top-n 10 2>&1
```

### ⚠️ trend_momentum.py 实时选股限制

`trend_momentum.py` **仅做历史回测**，无 `--date` 参数也无实时选股模式。BULL_TRENDING / BULL_VOLATILE 市场无法通过它获得当日 Top 10，只能降级为 `stock_pick.py` 超跌反弹模型输出。

**设计冲突**：超跌反弹模型按 `momentum_10d` **越低越好**排序（偏好超跌标的），与趋势动量策略的**追高动量**方向相反。降级使用的选股结果不完全匹配策略意图。

**当前处置**：BULL_TRENDING 市场 cron 中**双重运行**：

```bash
# 并行运行：trend_momentum 回测 + stock_pick 选股
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-trade
python3.11 trend_momentum.py --market us --months 12 &
TM_PID=$!
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-stock-pick
python3.11 stock_pick.py --market us --date $(date +%Y-%m-%d) --top-n 10 &
SP_PID=$!
wait $TM_PID $SP_PID
```

报告中：
- 主选股表使用 `stock_pick.py` 输出，标注「超跌反弹模型输出（降级执行，非趋势动量）」
- 附注区输出 `trend_momentum.py` 回测摘要（Sharpe、CumReturn、WinRate），标注「仅供参考」
- 长期应扩展 trend_momentum.py 增加实时选股模式

### HK 名称查找

`stock_pick.py --market hk` 的输出中 `name` 列常显示 N/A。需手动从 `stock_info_hk_top500.csv` 查表补全：

```bash
python3.11 -c "
import pandas as pd
result = pd.read_csv('~/wuhoo-workspace/data/stock-pick/factors/result_hk_YYYYMMDD.csv')
info = pd.read_csv('~/wuhoo-workspace/data/stock-pick/stock_info_hk_top500.csv')
name_map = dict(zip(info['code'], info['name']))  # HK.00700 → 腾讯控股
for _, row in result.iterrows():
    print(f'{row.ts_code}  {name_map.get(row.ts_code, \"N/A\")}')
"
```

### CN 数据日期滞后

CN 因子计算使用的「最近交易日」可能比 target date 早 1-7 个交易日（Tushare / efinance 入库延迟）。属正常现象，cron 报告中标注实际数据日期即可。对 252d/20d 窗口因子影响有限。

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
| **wuhoo-value-investing** | **质量预筛选** | **价值投资7指标去劣筛选，选股前过滤 universe** |

### 价值投资质量预筛选集成

v4.4 (2026-06-29) — 新增与 `wuhoo-value-investing` 的集成点：

```bash
# 选股前先运行质量筛选，排除非一流公司
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-value-investing
python3.11 quality_screen.py --market us --date $(date +%Y-%m-%d)

# 通过池在 ~/wuhoo-workspace/data/value-investing/quality_pass_{market}_{date}.csv
# stock_pick.py 可从通过池中选股，而非全量 universe
```

质量筛选阈值（各市场独立）：
| 指标 | A股 | 港股 | 美股 |
|------|:---:|:---:|:---:|
| ROE < | 5% | 8% | 8% |
| 负债率 > | 60% | 60%（地产70%） | 60% |
| 毛利率 < | 15% | 15% | 15% |

详见 `wuhoo-value-investing` skill。

## 数据保鲜检查

每日 cron 可运行保鲜检查脚本，扫描所有数据源的新鲜度：

```bash
python3.11 ~/wuhoo-workspace/scripts/check_data_freshness.py          # 完整 Markdown 报告
python3.11 ~/wuhoo-workspace/scripts/check_data_freshness.py --quiet  # 仅问题项
python3.11 ~/wuhoo-workspace/scripts/check_data_freshness.py --json   # JSON 输出
```

覆盖范围：A股/港股/美股日线、换手率、因子、成分股、市场状态、期货日线（共 12 个数据源）。

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
#    注意：OpenD 不响应 HTTP — curl 到 11111 会超时，需用 ss/netstat 检查端口监听
ss -tlnp 2>/dev/null | grep -q 11111 && echo "✅ OpenD" || echo "❌ OpenD 未运行"
# 如未运行，启动：
# bash ~/wuhoo-workspace/scripts/start_opend.sh start

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

### yfinance 已知失败模式（无需修复）

以下股票在 yfinance 批量下载中始终失败，属于预期行为，**不需要排查或重试**：

| 市场 | 代码 | 失败原因 | 处理 |
|------|------|----------|------|
| HK | `0638.HK` | 已退市（possibly delisted） | 忽略 |
| US | `BF.B` | 已退市（possibly delisted） | 忽略 |
| US | `BRK.B` | yfinance 无法解析时区（no timezone found） | 忽略 |

这些失败不影响选股功能（选股因子从有效股票中计算），出现时无需告警。

### 美股数据更新与修复

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-stock-pick
python3.11 update_all_data.py --market us --incremental
```

**⚠️ US daily_data_us 历史数据缺失修复**：
如果 `daily_data_us/` 仅有 1-2 个月数据（缺少 2024-2025），运行修复脚本重新下载：

```bash
python3.11 ~/wuhoo-workspace/scripts/repair_us_daily.py
```

该脚本调用 `update_us_daily(members, start_date=2024-01-01, force=True)`，批量下载 S&P 500 全量历史日线。
预计耗时 10-20 分钟（503 只 × 25 个月，yfinance 批量 API）。

> 注意：美股因子计算（`calculate_factors_us_complete`）**直接使用 yfinance 实时数据**，不依赖 `daily_data_us/`。
> 离线日线数据仅用于备份、质量检查和未来可能的离线回测。

**✅ v3.0 已修复：三市场日线目录隔离**
- 2026-05-02 修复：`update_all_data.py` 新增 `DAILY_DATA_HK_DIR` 和 `DAILY_DATA_US_DIR`，三市场数据完全隔离
- A股 → `daily_data/` | 港股 → `daily_data_hk/` | 美股 → `daily_data_us/`
- 不会再出现 US/HK 数据覆盖 CN 日线的问题

### 数据完整性诊断（三市场交叉污染扫描）

当怀疑数据被污染时，运行以下诊断流程：

```bash
# 1. 检查各目录文件数量和日期范围
for market in cn hk us; do
  case $market in
    cn) dir=~/wuhoo-workspace/data/stock-pick/daily_data ;;
    hk) dir=~/wuhoo-workspace/data/stock-pick/daily_data_hk ;;
    us) dir=~/wuhoo-workspace/data/stock-pick/daily_data_us ;;
  esac
  echo "$market: $(find $dir -name '*.csv' | wc -l) files, range: $(ls $dir/*/*.csv 2>/dev/null | head -1 | xargs basename) → $(ls $dir/*/*.csv 2>/dev/null | tail -1 | xargs basename)"
done

# 2. 交叉污染扫描：检查 CN 目录是否含 US/HK 代码
echo "=== US codes in CN daily_data ==="
grep -rl '\.US' ~/wuhoo-workspace/data/stock-pick/daily_data/*/ 2>/dev/null || echo "None ✅"
echo "=== HK codes in CN daily_data ==="
grep -rl 'HK\.' ~/wuhoo-workspace/data/stock-pick/daily_data/*/ 2>/dev/null || echo "None ✅"

# 3. 代码类型抽样验证（每市场各年取样）
for y in 2024 2025 2026; do
  codes=$(head -3 ~/wuhoo-workspace/data/stock-pick/daily_data/$y/*.csv 2>/dev/null | grep -oP '^\d{6}\.(SZ|SH)|[A-Z]+\.US|HK\.\d{5}' | sort -u | head -3)
  echo "CN $y: $codes"
done
```

**判断标准**：
- CN 目录：所有代码应为数字.SZ 或 数字.SH
- HK 目录：所有代码应为 HK.数字
- US 目录：所有代码应为字母.US
- 任一日录出现其他市场代码即为污染

**⚠️ 各市场 CSV 列名差异**（验证脚本需注意）：
| 市场 | 日期列 | 代码列 | 价格列 |
|------|--------|--------|--------|
| CN | `trade_date` | `ts_code` | `open/high/low/close` |
| HK | `time_key` | `ts_code` | `open/high/low/close` |
| US | `Date` | `ts_code` | `Open/High/Low/Close` |

**⚠️ US daily_data_us ts_code 格式差异**：`daily_data_us/*.csv` 中 `ts_code` 列存储的是**裸股票代码**（如 `MMM`、`AAPL`），不含 `.US` 后缀。这与 `stock_info_us_top500.csv` 的 `SYMBOL.US` 格式要求**不同**。在格式检查时不要把裸代码误判为污染：
- CN 污染判断：代码含 `.US` 后缀 → 异常
- US 正常格式：裸代码（`head -2 daily_data_us/2026/202604.csv | tail -1 | cut -d',' -f2` 应看到纯大写字母）
- 因子计算（`calculate_factors_us_complete`）直接使用 yfinance API，不受此差异影响

```bash
# 快速查看各市场列名
head -1 ~/wuhoo-workspace/data/stock-pick/daily_data/2026/202604.csv      # CN
head -1 ~/wuhoo-workspace/data/stock-pick/daily_data_hk/2026/202604.csv   # HK
head -1 ~/wuhoo-workspace/data/stock-pick/daily_data_us/2026/202604.csv   # US
```

### `--force` 模式的性能陷阱

`update_all_data.py --market cn --force` 重新下载 ~18 个月的日线数据，Tushare 阶段纯串行、每月 ~50 秒，完整运行 12-15 分钟。**efinance 换手率阶段已并行化**（v3.6），见下方。

### efinance 换手率数据更新（v3.6 并行重写）

**旧版（v3.5 及之前）**：纯串行逐只拉取，999 只股票历时 50+ 分钟，成功率仅 2.3%。所有数据在内存中累积，循环结束后才写入 CSV — 监控期间 `turnover_data/` 无新文件属**预期行为**。

**v3.6 并行版**（2026-05-28 重写）：
- **ThreadPoolExecutor 20 线程并行** — 999 只全量从 67 分钟降至 ~3 分钟
- **增量检测** — 检查已有 CSV 中的 `ts_code`，跳过已缓存的股票。日常增量仅拉取 0-70 只
- **断点续传** — 每只股票拉取后立即 merge 到月度 CSV（边拉边存），超时中断不丢失进度
- **增量合并写入** — 新数据与已有 CSV `concat + drop_duplicates`，不覆盖历史

```bash
# 并行拉取核心逻辑
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(_fetch_one, code): code for code in to_fetch}
    for future in as_completed(futures):
        pass  # 结果在 _fetch_one 中已 lock 保护地写入 all_data
```

**日常预期**：首次运行全量 ~3 分钟（写入 2000-01 至今全部月度 CSV），后续增量秒级完成（全部 999 只跳过）。

**成功率**：efinance 单次成功 ~67%（47/70），失败是网络波动/限流所致。23 次失败的股票下次增量重试时会自动补齐。

**处置**：正常情况下无需干预。如连续多次全量失败，检查 efinance 版本和网络。

### Cron Job 输出缓冲陷阱

在 Hermes 后台进程 (`terminal ... --background`) 或 cron 中运行 Python 脚本时，`stdout`/`stderr` 被管道缓冲，**进度输出在进程结束前完全不可见**。症状：
- `process poll` 显示 `output_preview: ""`，`process log` 返回 0 行
- 但 `/proc/<pid>/io` 显示 `wchar` 持续增长（输出正在累积）
- 进程结束后所有输出一次性出现

**这会导致 Agent 误判进程卡死**，实际进程可能正常运行。正确监控方式：

```bash
# 1. 确认进程存活
pgrep -P <bash_pid>  # 查找 Python 子进程

# 2. 检查 I/O 活动（rchar 增长 = 仍在读取，wchar 增长 = 仍在输出）
cat /proc/<python_pid>/io | head -4

# 3. 检查内存增长（VmRSS 持续增长 = 数据处理中）
cat /proc/<python_pid>/status | grep VmRSS

# 4. 检查网络连接（活跃 TCP = API 调用进行中）
ss -tnp | grep <python_pid>

# 5. 检查文件产出（确认数据正在落盘）
find ~/wuhoo-workspace/data/stock-pick/daily_data/ -name "*.csv" -mmin -5
```

**⚠️ 父进程 vs 子进程 PID 陷阱**（2026-05-06 发现）：

`terminal ... --background` 返回的 PID 是 **bash 包装进程**，而非实际的 Python 进程。bash 父进程始终处于 `wait4` 系统调用（等待子进程退出），其 `/proc/<pid>/io` **永远不变**。监控 bash PID 会误判进程卡死。

```bash
# ❌ 错误 — 监控的是 bash 包装进程，IO 永远冻结
cat /proc/<returned_pid>/io  # rchar/wchar 不变 → 误判为卡死

# ✅ 正确 — 先找到 Python 子进程，再监控
pgrep -P <returned_pid>       # 获取实际 Python PID
cat /proc/<python_pid>/io     # 真实 IO 活动
```

**识别方法**：
- `pstree -p <returned_pid>` 查看进程树 → 应看到 `bash(pid)---python3.11(child_pid)`
- bash 父进程：`State: S`, `wchan: 0`, syscall 为 `wait4`，IO 冻结
- Python 子进程：`State: S`（网络等待）或 `Rl`（运行中），IO 持续增长，有 TCP 连接

> 2026-05-06 cron：bash PID 798773 的 IO 在 3 分钟内完全不变（rchar=277301），但子进程 798797 的 rchar 从 53MB 增长到 114MB，CPU 25%。监控父进程导致误判"卡死"。

**CN --incremental 进程监控要点**：
- Tushare 阶段：检查 `daily_data/` 目录下的月度 CSV 文件写入
- efinance 阶段：检查 `turnover_data/` 目录下的文件写入（**不是 daily_data/**）
- 内存从 ~150MB 增长到 ~700MB+ 是正常的（efinance 逐只下载并累积数据）
- 两个 Tushare HTTP 连接进入 CLOSE-WAIT 状态后，进程切换到 efinance 阶段（短连接，不持续保持 TCP）
- **rchar 速率监控法**：多次采样 `/proc/<python_pid>/io` 的 `rchar`，计算 KB/s 速率。速率稳定 > 100 KB/s = 仍在下载（活着）；速率降至 0 = 卡死。详见 `references/20260507-cron-audit.md`

**⚠️ CN --incremental 日线阶段 "0 months updated" 是正常的**：当 `daily_data/` 中已有当月和上月 CSV 时，Tushare 日线阶段会全部跳过（显示 "已存在，跳过"），最终报告 "A 股日线更新完成：0 个月"。**这不是错误** — 日线数据已是最新。efinance 换手率阶段不受影响，仍会独立运行并更新全部 999 只股票。

### Tushare index_weight API 静默返回空（2026-06-22）

`pro.index_weight(index_code='000852.SH', ...)` 可能返回空 DataFrame（0 rows），导致 `update_cn_members()` 返回 `[]`，后续日线更新跳过后所有股票（`update_cn_daily` 收到 0 只 members → 0 个月更新）。

**症状**：`--force` 模式下仍报「无法获取成分股数据」，A股日线停滞。

**根因**：Tushare API 行为变更（不确定），`index_weight` 不再返回中证1000成分股数据。

**修复**：`update_all_data.py` 已加入 akshare 降级逻辑（`ak.index_stock_cons('000852')`）。Tushare 失败时自动用 akshare 获取成分股，格式化为 `XXXXXX.SH/SZ`。

**验证**：
```bash
python3.11 -c "
import tushare as ts, os
pro = ts.pro_api(os.environ['TUSHARE_TOKEN'])
df = pro.index_weight(index_code='000852.SH', start_date='20260601', end_date='20260622')
print(f'Tushare: {len(df)} rows — {\"OK\" if len(df)>0 else \"BROKEN, use akshare fallback\"}')
"
```

### Tushare 节假日数据延迟

中国长假期间（春节、五一、国庆），Tushare Pro 数据入库严重滞后：
- 假期交易日少，且数据通常在 T+1 日傍晚才入库
- 月初（如 5 月 1-5 日）可能完全查不到当月数据 → `202605.csv` 不生成是**预期行为**
- 验证方法：`python3.11 -c "import tushare as ts, os; pro=ts.pro_api(os.environ['TUSHARE_TOKEN']); print(len(pro.daily(ts_code='000001.SZ', start_date='20260501', end_date='20260505')))"` → 返回 0 即确认延迟
- 无需任何修复操作，下一次 cron 运行将自动补齐

### 多市场全量更新与选股审计流程

用户偏好审计追踪。正确执行顺序：

```bash
# 1. 前置检查
curl -s --connect-timeout 3 http://127.0.0.1:11111/  # OpenD?
grep TUSHARE_TOKEN ~/.hermes/.env | wc -c              # Token?

# 2. 启动 OpenD（如未运行）
bash ~/wuhoo-workspace/scripts/start_opend.sh start    # 需要 start 参数！

# 3. 并行更新数据（v3.0 目录隔离后可任意顺序，三市场可完全并行）
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

### Cron 自动化（2026-05-09 批量增设）

全部 13 个定时任务清单、设计模式和经验教训见：
- `references/cron-inventory.md` — 完整 cron inventory，含 delivery 模式、token 优化、交易日策略

本 skill 相关的 cron 任务：
- **市场数据更新** (`0 8 * * *`) — 更新三市场日线
- **每日选股结果** (`20 8 * * 1-5`) — 数据更新后自动产出 Top 10 选股
- **美股等权调仓检查** (`0 22 * * 1`) — 每周一检查是否需要 rebalance
- **数据完整性扫描** (`0 8 * * 6`) — 每周六交叉污染检查
- **S&P500 成分股更新** (`0 3 * * 6`) — 每周六自动刷新

> ⚠️ **Cron 暂停陷阱**：`hermes cron list` CLI 只显示 active 任务，paused 任务不可见。
> 如 CLI 返回 "No scheduled jobs"，必须用 `cronjob(action='list')` 查看完整清单。
> 恢复步骤见 `references/cron-pause-recovery.md`。
>
> 🔴 **Cron 调度器静默卡死**（2026-06-10 发现）：ticker 可能无日志静默停止，`hermes cron status` 的 "Next run" 冻结在过去。恢复需 `hermes gateway restart`（会杀 OpenD 子进程）。诊断与恢复详见 `references/cron-scheduler-stall.md`。

## Cron Job 执行策略

CN efinance 换手率阶段已并行化（v3.6），全量 ~3 分钟。**增量「秒级」仅在待重试股票数 ≤20 时成立** — 当积累了大量先前失败的股票（如 100+）需要重试时，增量可能仍需 5+ 分钟。因此无论 v3.6 与否，CN 必须用 `timeout 300` 包装作为安全网，日线数据足够选股，换手率中断不受影响。

US 和 HK 各需 2-5 分钟。三市场可安全并行启动：

```bash
# ✅ 推荐：三市场并行 + CN timeout 安全网
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-stock-pick
timeout 300 python3.11 update_all_data.py --market cn --incremental &
CN_PID=$!
python3.11 fetch_hk_data.py --incremental &
HK_PID=$!
python3.11 update_all_data.py --market us --incremental &
US_PID=$!
wait $CN_PID $HK_PID $US_PID
# CN timeout → EXIT_CODE=124，属预期行为，不阻塞报告

# 策略：US/HK 完成即可先输出部分报告，CN 等 timeout 结束
# wait $US_PID $HK_PID  # 仅等待 US+HK（~3 分钟），CN 后台继续
```

**CN 进程监控要点**（Cron 中适用）：
- v3.6 并行版：全量 ~3 分钟，纯增量（≤20 retry）秒级，积压 retry（100+）仍可能 5+ 分钟
- 如进程仍卡在 efinance，检查网络：`ef.stock.get_quote_history('000001')` 测试单只
- 换手率数据存储在 `turnover_data/`（**不是 `daily_data/`**），文件在拉取过程中**实时写入**（v3.6 增量合并）
- 首次全量运行时内存从 ~150MB 增长到 ~1GB 是正常的（批量拉取 999 只数据）
- timeout 返回 `EXIT_CODE=124` 是**预期行为**（非错误），表示换手率阶段被安全截断

### 港股数据更新

港股因子计算（`calculate_factors_simple`）通过 Futu OpenD API 实时获取 K 线，不依赖本地日线文件。
`daily_data_hk/` 中的月度 CSV 用于离线备份和质量检查。

### 增量模式 HK 成功率解读陷阱

`fetch_hk_data.py --incremental` 输出的 "成功 X/500" **仅统计在增量窗口（35天）内有新数据的股票**，不是总覆盖率。例如 `96/500` 是正常的 — 历史数据中已有 596 只股票的完整记录，本次只是为 96 只有近期交易的股票追加新行。

**判断数据是否健康的正确方法**：查看月份 CSV 中实际股票数和有效行数，而非增量输出：
```bash
python3.11 -c "
import pandas as pd
df = pd.read_csv('daily_data_hk/2026/202604.csv')
print(f'股票数: {df.ts_code.nunique()}, 有效行: {df.close.notna().sum()}/{len(df)}')
"
```

### daily_data_hk/ 根目录孤儿文件

旧版脚本可能在 `daily_data_hk/` 根目录遗留 CSV 文件（如 `HK_stock_daily_20260421.csv`），这些不在年/月子目录结构中，不影响功能但应清理：
```bash
rm -f ~/wuhoo-workspace/data/stock-pick/daily_data_hk/HK_stock_daily_*.csv
```

### HK 代码前缀双重 Bug（已修复 2026-05-02）

`update_hk_daily()` 曾存在严重 bug：`members_file` 存储格式为 `HK.00700`，但代码再次拼接 `f"HK.{code}"` → 产生 `HK.HK.00700`，Futu API 全部返回 `-1 (wrong format)`，异常被 `except: pass` 静默吞掉。

**症状**：500 只港股仅 60 只成功（刚好那些缺 HK. 前缀的 code 侥幸通过），成功率 12%。

**修复** (已应用到 `update_all_data.py:334`)：
```python
# 修复前（BUG）
stock_code = f"HK.{code.replace('.HK', '')}"  # HK.00700 → HK.HK.00700 ❌

# 修复后
stock_code = code  # members file 已含 HK. 前缀 ✅
```

### Futu OpenD 批量调用限流

500 只港股逐个调用 `request_history_kline` 时，如无延迟/重连，约 60 次后 API 开始拒绝（静默失败）。解决方案：

- 每 100 次调用重建 `OpenQuoteContext` 连接
- 每次调用间 `time.sleep(0.1)`
- 连接建立后 `time.sleep(0.3)` 等待稳定

完整脚本见 `scripts/repair_hk_daily_v2.py`。

**HK daily_data_hk 数据迁移**：
如果 `daily_data_hk/` 仅有少量月份，可从 legacy 目录迁移历史数据：

```bash
# legacy 数据在 data/hk/daily/（25 个月，202404-202604）
SRC=~/wuhoo-workspace/data/hk/daily
DST=~/wuhoo-workspace/data/stock-pick/daily_data_hk
for srcfile in $(find "$SRC" -name '*.csv' -type f); do
    rel=$(echo "$srcfile" | sed "s|$SRC/||")
    dstfile="$DST/$rel"
    mkdir -p "$(dirname "$dstfile")"
    [ ! -f "$dstfile" ] && cp "$srcfile" "$dstfile"
done
```

Legacy 格式（含 `change_rate` 列）与 stock-pick 格式兼容，额外列不影响使用。

### S&P 500 成分股补全

旧版 `index_members_us_top500.csv` 仅 242 只，需定期从 GitHub 更新到 503 只。

---

*创建时间：2026-03-12*
*更新时间：2026-06-27*
*版本：4.3 — v3.6 增量性能校准：增量「秒级」仅 ≤20 retry；积压 100+ 仍需 5+ 分钟，timeout 300 安全网必留*

## 参考文件

- `references/20260612-cron-stock-pick-audit.md` — 2026-06-12 cron 选股审计：trend_momentum 实时限制 + HK 名称 N/A + CN 数据滞后
- `references/20260608-audit.md` — 2026-06-08 选股审计：数据膨胀修复 + Beta 阈值调整 + 行业分散实现
- `references/20260528-efinance-parallel-rewrite.md` — 2026-05-28 efinance 时序超时修复审计（并行化 v3.6）
- `references/20260509-cron-audit.md` — 2026-05-09 cron 数据更新审计（三市场并行启动，US/HK 快速完成，CN efinance 阻塞报告）
- `references/20260507-cron-audit.md` — 2026-05-07 cron 数据更新审计（efinance 2.3% 成功率 + 50min 超时 + rchar 速率监控法）
- `references/20260505-cron-audit.md` — 2026-05-05 cron 数据更新审计（CN Tushare 跳过 + efinance 换手率 + US ts_code 格式 + 节假日延迟）
- `references/20260504-cron-audit.md` — 2026-05-04 cron 数据更新审计（输出缓冲陷阱 + OpenD 检查修复 + efinance 诊断更新）
- `references/20260503-cron-audit.md` — 2026-05-03 cron 数据更新审计（efinance 卡死 + HK 增量成功率误读）
- `references/20260430-audit.md` — 2026-04-30 全市场数据更新与选股审计记录
- `references/data-update-troubleshooting.md` — 历次数据更新故障排查记录
- `references/manual-tushare-fast-pull.md` — 手动 Tushare 日线快速拉取（绕过 efinance 瓶颈的 ~30s 方案）
- `scripts/repair_hk_daily_v2.py` — 港股日线修复（带延迟重连，避免 Futu API 限流）
- `scripts/repair_us_daily.py` — 美股日线历史数据修复（yfinance 批量下载）
