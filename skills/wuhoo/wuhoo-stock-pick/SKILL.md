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
| 港股 | hk | yfinance (批量) / Futu (实时) | 波动率 + 动量 | 10日动量，越低越好 |
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

`update_all_data.py --market cn --force` 重新下载 ~18 个月的数据，但 **纯串行、无 ThreadPoolExecutor 实际使用**（虽然 import 了），每月 ~50 秒。完整运行需 12-15 分钟，且会卡在 efinance 换手率步骤。仅当需要全量重建时使用，并准备好在换手率步骤手动终止。

### efinance 换手率下载卡死处理

efinance 接口持续返回极低成功率时（实测仅 **2.3%**，23/999），纯串行循环会导致进程运行 50+ 分钟。**症状分两种**：
- **初期**（仍在遍历股票列表）：CPU 正常/偏高（10-20%），但超过 10 分钟无文件写入。此时进程在内存中累积数据，尚未触发进度打印（每 50 只才输出一次）。
- **后期**（已遍历完但卡在重试）：CPU 低（<5%）但有活跃网络连接。
- 通用判断：`/proc/<pid>/io` 中 `write_bytes: 0` 且 `rchar` 持续增长但无 CSV 文件产出。

**⚠️ 关键陷阱：`update_cn_turnover_efinance()` 将所有数据累积在内存中**（`all_data` 列表），**CSV 文件在整个 for 循环结束后才写入**。因此监控期间 `turnover_data/` 无任何新文件是**预期行为**，不代表卡死。判断进程是否在工作的正确方法：多次采样 rchar 计算 KB/s 速率：
- 速率稳定 > 100 KB/s → 仍在下载
- 速率降至 0 → 进程卡死

**诊断命令**：
```bash
# 查看进程 I/O 状态
cat /proc/<pid>/io | head -4
# 检查最近 15 分钟的文件写入
find ~/wuhoo-workspace/data/stock-pick/daily_data/ -name "*.csv" -mmin -15
# 检查 CPU
ps -p <pid> -o %cpu,%mem,etime --no-headers
```

**处置**：`kill <pid>` 终止进程，日线数据已足够选股使用（换手率因子缺失属已知降级）。

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
*更新时间：2026-05-07*
*版本：3.3 — efinance 内存累积行为 + rchar 速率监控法 + 20260507 cron 审计*

## 参考文件

- `references/20260506-cron-audit.md` — 2026-05-06 cron 数据更新审计（父进程 vs 子进程 PID 监控陷阱 + 五一假期后数据更新）
- `references/20260507-cron-audit.md` — 2026-05-07 cron 数据更新审计（efinance 2.3% 成功率 + 50min 超时 + rchar 速率监控法）
- `references/20260505-cron-audit.md` — 2026-05-05 cron 数据更新审计（CN Tushare 跳过 + efinance 换手率 + US ts_code 格式 + 节假日延迟）
- `references/20260504-cron-audit.md` — 2026-05-04 cron 数据更新审计（输出缓冲陷阱 + OpenD 检查修复 + efinance 诊断更新）
- `references/20260503-cron-audit.md` — 2026-05-03 cron 数据更新审计（efinance 卡死 + HK 增量成功率误读）
- `references/20260430-audit.md` — 2026-04-30 全市场数据更新与选股审计记录
- `references/data-update-troubleshooting.md` — 历次数据更新故障排查记录
- `scripts/repair_hk_daily_v2.py` — 港股日线修复（带延迟重连，避免 Futu API 限流）
- `scripts/repair_us_daily.py` — 美股日线历史数据修复（yfinance 批量下载）
