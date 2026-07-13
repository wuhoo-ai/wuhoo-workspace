---
name: wuhoo-trade
description: 多市场交易执行（Workflow C）。接收选股结果、分析结果、辩论结果作为输入，执行风控检查、交易模拟/实盘、复盘。支持美股等权持仓策略。
tags: ["wuhoo"]
category: wuhoo
metadata: { "hermes": { "requires": { "bins": ["python3.11"], "pip": ["pandas", "numpy", "futu-api"] } } }
---

# wuhoo-trade — 多市场交易执行

## 执行入口
- **交易执行**: `python3.11 skills/wuhoo-trade/workflow_c_multi_market.py --market us --date 2026-04-22`
- **定期交易**: `python3.11 skills/wuhoo-trade/workflow_e_periodic_trade.py`
- **风控管理**: `python3.11 skills/wuhoo-trade/risk_manager.py` (单笔风控) + `portfolio_risk.py` (组合风控，已集成到 workflow_c Step 4.5)
- **持仓审计**: `python3.11 skills/wuhoo-trade/audit_module.py`
- **组合指标**: `python3.11 skills/wuhoo-trade/portfolio_metrics.py`
- **每日复盘**: `python3.11 skills/wuhoo-trade/daily_review.py`
- **美股等权持仓**: `python3.11 skills/wuhoo-trade/us_equal_weight_portfolio.py [show|rebalance|check]`
- **PnL 追踪**: `python3.11 skills/wuhoo-trade/pnl_tracker.py [snapshot|metrics|full]` — 每日组合净值快照 + 绩效指标
- **策略回测**: `python3.11 skills/wuhoo-trade/backtest.py --market us --months 12` — Walk-forward 回测
- **自适应回测**: `python3.11 skills/wuhoo-trade/adaptive_backtest.py --market us --months 12` — 按月判定市场状态 + 策略路由回测
- **多策略回测**: `python3.11 skills/wuhoo-trade/strategies.py --strategy dual_momentum --market us --months 12` — 4 种新策略统一回测框架

## 依赖
- 富途 OpenD 运行在 127.0.0.1:11111
- python3.11 + pandas + numpy + futu-api
- 环境变量在 ~/.hermes/.env

> **🐛 execute_code 沙箱超时陷阱**：在 `execute_code` 沙箱中直接使用 `OpenQuoteContext`/`OpenSecTradeContext` 连接 OpenD 会超时（300s+），即使连接成功。**所有 Futu API 调用必须通过 `terminal` 运行 `python3.11` 脚本**，不能用 execute_code。反过来，yfinance 数据获取用 execute_code 完全正常（仅需 10-15s）。

## 账户配置 (path_config.py)

> **⚠️ 已验证账户列表 (2026-05-06 重新实测 — `filter_trdmarket` 必须按市场分别查询！)**：
> - SIMULATE US MARGIN: `18767293` ✅ (需 `filter_trdmarket=TrdMarket.US`)
> - SIMULATE HK CASH: `18767294` ✅ (trdmarket_auth: ["HK"])
> - SIMULATE CN CASH: `18767295` ✅ (需 `filter_trdmarket=TrdMarket.CN`)
> - SIMULATE HK MARGIN: `18767296` ✅ (trdmarket_auth: ["HK"]) — 注意是 HK 非 US
> - REAL MARGIN: `281756481352860561`, `281756455996103774`, `281756460291071070`

> **⚠️ 关键陷阱**：不传 `filter_trdmarket` 时 `get_acc_list()` 默认只返回 HK 市场账户！CN/US 账户不会出现在列表中。必须用 `filter_trdmarket=TrdMarket.CN` 或 `TrdMarket.US` 分别查询！

| 市场 | 账户 ID | 类型 | 环境 | filter_trdmarket | 状态 |
|------|---------|------|------|:---:|------|
| US   | 18767293 | MARGIN | SIMULATE | US | ✅ |
| HK   | 18767294 | CASH | SIMULATE | HK | ✅ |
| CN   | 18767295 | CASH | SIMULATE | CN | ✅ |
| HK   | 18767296 | MARGIN | SIMULATE | HK | ✅ (cash N/A — 见下方陷阱) |

> **⚠️ HK Margin 账户 (18767296) accinfo_query 陷阱**：`accinfo_query` 对该账户返回 `cash='N/A'`、`total_assets='N/A'`，所有数值字段需用 `safe_float()` 包装：
> ```python
> def safe_float(v, default=0.0):
>     if v is None or v == 'N/A' or v == '': return default
>     try: return float(v)
>     except: return default
> ```
> HK Cash 账户 (18767294) 不受影响，字段正常返回。

### A 股行情权限与交易注意事项

1. **行情权限缺失**：`OpenQuoteContext.get_market_snapshot()` 对 A 股返回 "无权限获取行情"。替代方案：用本地日线数据获取价格（`~/wuhoo-workspace/data/stock-pick/daily_data/YYYY/YYYYMM.csv`，列名 `ts_code`）
2. **市价单优先**：A 股模拟交易中限价单可能长时间停留在 SUBMITTED 不成交，市价单（`OrderType.MARKET`）秒级成交
3. **限价取消**：用 `modify_order(modify_order_op=ModifyOrderOp.CANCEL, ...)` 取消 SUBMITTED 订单后再下市价单

## 美股等权持仓策略 (us_equal_weight_portfolio.py)

**策略逻辑:**
- 持仓范围: stock_pick.py 当天选出的结果（非 S&P 500 全量）
- 权重分配: 每只股票等权重 = (1 - 10%现金) / N
- 现金储备: 10%
- 再平衡: 每次选股结果更新后自动再平衡

**用法:**
```bash
python3.11 skills/wuhoo-trade/us_equal_weight_portfolio.py show      # 查看当前持仓
python3.11 skills/wuhoo-trade/us_equal_weight_portfolio.py rebalance # 执行再平衡
python3.11 skills/wuhoo-trade/us_equal_weight_portfolio.py check     # 检查是否需要再平衡
```

**数据文件:**
- 选股结果: ~/.hermes/data/stock-pick/factors/result_us_YYYYMMDD.csv
- 持仓记录: ~/wuhoo-workspace/data/us/portfolio.json

## 工作流

```
选股 (stock-pick) → 分析 (deep-analysis) → 辩论 (debate)
  → 风控检查 (risk_manager / RiskAgent) → 交易执行 (workflow_c) → 复盘 (daily_review)
```

### 🔴 必须辩论优先 — 禁止跳过辩论直接调仓（2026-05-21）

**标准执行顺序是硬约束**：选股 → 辩论 → 调仓。**绝对不允许选股完成后直接跳到交易。**

**为什么辩论不可跳过**：因子选股只看量价技术面，辩论引入 Bull/Bear/Trader 三视角 LLM 分析，可能对选股结果做出相反判断：

| 选股结果 | 辩论结果 | 实际案例 (2026-05-21) |
|----------|----------|----------------------|
| 入选 (10d ROC 最低) | SELL (0.72) | HK.01113 长实集团 — 选股因子入选但辩论三方一致看空 |
| 入选 (10d ROC 最低) | SELL (0.73) | HK.02020 安踏体育 — 同上 |
| 入选 (10d ROC 最低) | SELL (0.75) | 002993.SZ 奥海科技 — Bull/Bear/Trader 均 SELL |

**跳过辩论的后果**：买入辩论看空的股票 → 必须反向卖出纠正 → 双重交易成本 + 持仓时间窗口浪费。

**正确流程**：
```bash
# 1. 选股（产出 result_{market}_{date}.csv）
python3.11 stock_pick.py --market hk --date 20260521

# 2. 批量辩论（产出 debate_summary.json）
python3.11 batch_debate.py --date 20260521 --workers 3 --market hk

# 3. 检查辩论结果，排除 Trader=SELL 的股票
python3.11 -c "
import json
with open('data/debate/20260521/deepseek/debate_summary.json') as f:
    d = json.load(f)
for r in d['results']:
    if r.get('trader',{}).get('decision') == 'SELL':
        print(f'排除: {r[\"symbol\"]}')  # 这些股票不买入
# 如果已持有，应卖出
"

# 4. 基于辩论过滤后的名单执行调仓
```

**已执行错误调仓的补救**（本次教训）：
- 港股 HK.01113/HK.02020 已买入但辩论看空 → 需市价卖出纠正
- A 股 002993.SZ 从买入名单移除 → 不执行买入

## 风控集成 (2026-04-24 更新)
- `_debate_quick()` 方法已集成 `RiskAgent.review()` 进行风控审核
- 构建 `trader_decision` 结构传递止损/止盈/仓位/RRR 给 RiskAgent
- 降级策略：RiskAgent 不可用时使用简化风控（波动率、涨幅、Beta 检查）
- RRR 计算修正：`潜在收益 / 潜在损失` = `(止盈价-现价) / (现价-止损价)`

## 风控规则差距分析 (2026-04-24 → 2026-06-09 修复)

**risk_rules.yaml 定义 13 条规则，现已全面覆盖：**

| 规则 | 实现位置 | 状态 |
|------|---------|:--:|
| single_stock_max 20% | risk_manager.py + portfolio_risk.py | ✅ |
| single_industry_max 40% | portfolio_risk.py `_check_industry_concentration` | ✅ |
| cash_min 10% | risk_manager.py + portfolio_risk.py | ✅ |
| 分层仓位管理 | portfolio_risk.py `_check_position_tiers` | ✅ |
| 动态止损（波动率调整） | RiskAgent `_get_dynamic_stop_loss_limit` | ✅ |
| RRR min_ratio 2.0 | RiskAgent + workflow_c debate_quick | ✅ |
| 流动性检查 | RiskAgent `_check_liquidity` | ✅ |
| 事件风险（财报黑名单） | portfolio_risk.py `_check_event_risk` | ✅ |
| 相关性检查 max_correlation 0.7 | portfolio_risk.py `_check_correlation` | ✅ |
| 自动审批条件 | RiskAgent `_determine_recommendation` | ✅ |
| CONDITIONAL 阻断 | workflow_c Step 3 (收紧条件) + Step 4.5 (组合阻断) | ✅ |
| max_drawdown 15% | portfolio_risk.py `_check_max_drawdown` | ✅ |
| volatility high_threshold 0.60 | RiskAgent `_check_volatility` | ✅ |

**2026-06-09 集成修复：**
- workflow_c Step 3: CONDITIONAL 不再静默通过，收紧条件 (conf>0.7 + RRR>2.5) 或转观望
- workflow_c Step 4.5: 新增 `PortfolioRiskChecker.check_all()` 组合级风控，不通过则阻断交易
- workflow_c Step 5: 每笔下单前调用 `risk_manager.risk_check()` 做单笔风控
- DEBATE_PATH / STOCK_PICK_SCRIPT / FACTORS_DIR 路径修复为实际目录
- `--debate-file` 新参数支持加载 batch_debate.py 产出的外部辩论结果

## 📊 策略回测与绩效追踪（2026-06-09）

### 策略多元化框架（Phase 2，2026-06-09）

回测发现单一策略（超跌反弹）在三市场表现严重分化后，新增两个核心模块：

#### 趋势动量策略 (trend_momentum.py)

与超跌反弹互补：买涨最多的而非跌最多的。6 因子选股（动量10/20/60日 + 量比 + Beta + 相对强度），按动量10日降序排序。

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-trade
python3.11 trend_momentum.py --market us --months 12
python3.11 trend_momentum.py --market all --months 12
```

**因子筛选**：momentum_10d > 0（硬性） + momentum_60d > P50 + volume_ratio > 0.8 + beta > max(P20, 1.0)。

> ⚠️ **trend_momentum.py 仅支持历史回测，无实时选股模式**（2026-06-12 确认）。
> 该脚本无 `--date` 参数，test dates 硬编码为每月 15 日（到最近已过月份为止）。
> BULL_TRENDING / BULL_VOLATILE 市场的 cron 选股需降级为 `stock_pick.py`（超跌反弹模型），
> 但超跌反弹按 `momentum_10d` 越低越好排序，与趋势动量的追高方向相反。
> 长期应扩展 trend_momentum.py 增加 `--date` 参数输出当日动量排序 Top N。

#### 市场状态判定 (market_regime.py)

5 维度加权投票系统，自动判断 Bull/Bear/Ranging/Volatile：

| 维度 | 权重 | 指标 |
|------|:---:|------|
| MA 位置 | 30% | 价格 vs MA50/MA200，金叉/死叉 |
| 市场广度 | 25% | 站上 MA50/MA200 的股票占比 |
| 趋势强度 | 20% | MA50 斜率 + 连续涨跌天数 |
| 波动率 | 15% | 20日 vs 60日年化波动率比 |
| 动量广度 | 10% | 正20日动量股票占比 |

```bash
python3.11 market_regime.py --market us          # 单市场
python3.11 market_regime.py --market all --save  # 三市场 + 存 JSON
```

> **🐛 Breadth-Mask 修复 (2026-06-09)**：当市场广度极差（仅有少数大票站上均线）时，MA位置维度容易被拉高产生假阳性——CN实测MA位置+2但广度-2(仅27%站上MA50)，composite被推至BULL区→误启用趋势动量→追高被套-17.77%。修复：`detect_regime()`中当`breadth_score ≤ -1`时composite强制cap到+0.4（最多RANGING，永不到BULL）。详见`references/20260609-all-strategies-comparison.md`。

#### 策略自适应路由

```
市场状态        →  策略             →  仓位
BULL_TRENDING   →  trend_momentum   →  100%
BULL_VOLATILE   →  trend_momentum   →   75%
RANGING         →  oversold_rebound →   80%
BEAR_VOLATILE   →  defensive        →   50%
BEAR_TRENDING   →  cash_only        →    0%
```

#### 回测扩展 (backtest.py)

新增 `--strategy` 参数支持三种模式：

```bash
python3.11 backtest.py --market us --strategy contrarian   # 仅超跌反弹
python3.11 backtest.py --market us --strategy momentum     # 仅趋势动量
python3.11 backtest.py --market us --strategy both         # 对比两种策略
```

> 详细回测对比报告见 `references/20260609-strategy-comparison.md`

### PnL 追踪器 (pnl_tracker.py)

每日组合净值快照，产出时序 JSONL 供绩效计算：

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-trade
python3.11 pnl_tracker.py snapshot   # 当日快照（连接 OpenD 获取三账户持仓+现金）
python3.11 pnl_tracker.py metrics    # 计算绩效指标（Sharpe/Max DD/Calmar + Benchmark 对比）
python3.11 pnl_tracker.py full       # 快照 + 指标
```

输出：
- `~/wuhoo-workspace/data/pnl/snapshots.jsonl` — 每日快照（JSONL）
- `~/wuhoo-workspace/data/pnl/metrics_report.json` — 最新绩效报告

### 策略回测 (backtest.py)

Walk-forward 回测：每月用当时可得的历史数据计算因子 → 按策略选股 → 模拟持有 → 统计表现。

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-trade
python3.11 backtest.py --market us --months 12 --top-n 10 --hold-days 20
python3.11 backtest.py --market all --months 12  # 三市场全量
```

### 回测核心发现

> 详见 `references/20260609-backtest-results.md`

**同一策略在不同市场表现差异极大**：

| 市场 | 月均收益 | 胜率 | 累计收益 | Sharpe | 最大回撤 | 有效性 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| US | **+1.50%** | 91.7% | +19.45% | 1.01 | -1.6% | ✅ 强 |
| HK | +0.10% | 50.0% | +0.50% | 0.03 | -6.8% | ❌ 弱 |

**关键教训**：
1. 美股超跌反弹策略几乎无回撤 —— 可以安心实盘
2. 港股 2026 年进入单边下跌后策略系统性接飞刀 —— 需市场状态感知
3. 单一策略无法跨市场通用 —— 需要策略多样化 + 市场状态路由

**陷阱：HK 数据混合格式**。HK 日线数据存在两种格式：
- 旧文件（2024-2025）：yfinance 格式，列 `Date, Close`
- 新文件（2026）：Futu 格式，列 `time_key, close`
合并处理时必须在 concat 前逐文件统一列名，否则一半数据被 dropna 丢弃。

### 回测数据覆盖

| 市场 | 股票数 | 历史月数 | 数据量 | 基准 |
|------|:---:|:---:|------|------|
| US | 505 (S&P 500) | 25 月 | ~284K 行 | SPY |
| HK | 601 (Top 500+) | 25 月 | ~271K 行 | ^HSI |
| CN | ~1000 (中证1000) | 25 月 | 大 | 沪深300 |

CN 回测计算量大（1000+ 股票），单次运行需 5-10 分钟。

### HK 每手数量不是固定 100！

港股每手（lot_size）因股票而异，**必须从 Futu 快照获取**，不能假设为 100：

```python
# ✅ 正确：先查每手大小
quote = OpenQuoteContext('127.0.0.1', 11111)
ret, snap = quote.get_market_snapshot(['HK.00857'])
lot_size = snap.iloc[0]['lot_size']  # 中国石油股份=2000，长实集团=500，多数=100
quote.close()

qty = (target_amount // (price * lot_size)) * lot_size

# ❌ 错误：假设每手100
qty = int(target_amount / price / 100) * 100  # 中国石油股份会报"不足1手数量的碎股"
```

**实测案例（2026-05-04）**：
| 股票 | lot_size | 买入 4200 股 | 买入 100 股 | 买入 2000 股 |
|------|:---:|:---:|:---:|:---:|
| HK.00857 中国石油股份 | **2000** | ❌ 碎股 | ❌ 碎股 | ✅ |
| HK.01113 长实集团 | 500 | — | — | — |

### 🟡 HK 模拟盘卖出成交速度：时快时慢，不可预测

**症状（2026-05-25 实测）**：HK 模拟账户 (18767294) 卖出 400 股 HK.00005 汇丰控股，三种订单类型全部卡 SUBMITTED 60s+：
- NORMAL 限价单 @ bid (143.9)：SUBMITTED → 等待 60s 未成交
- MARKET 市价单：SUBMITTED → 等待 60s 未成交
- NORMAL 限价单 @ ask (144.0)：SUBMITTED → 等待 60s 未成交

**反例（2026-06-10 实测）**：同一账户，4 只股票市价卖出（00552/00700/01766/01999），**全部 5 秒内 FILLED_ALL**。下午 14:03 港股交易时段执行。

**结论**: HK 模拟引擎的 fill 速度是**间歇性的**，不是永久性故障。不同交易日/时段表现差异大：
- ✅ 有时秒级成交（如 2026-06-10 下午盘）
- ❌ 有时挂单数分钟（如 2026-05-25）

**调仓时的正确做法**：
1. **先尝试市价单** — 不要预设会卡，很多情况下能秒成交
2. 下单后 `sleep(5)` + `order_list_query(refresh_cache=True)` 检查状态
3. 如果 5s 后仍 SUBMITTED → 等待 60s 再查（不要反复取消重建！）
4. 60s 后仍 SUBMITTED → 接受延迟，在审计报告中标注
5. **核对最终持仓** — `position_list_query(refresh_cache=True)` 确认股数变化，因为即使订单状态未更新，持仓可能已变

### ✅ 路径已修复 (2026-06-09)

`workflow_c_multi_market.py` 三处硬编码路径已修正为实际路径：
- `STOCK_PICK_SCRIPT` → `~/wuhoo-workspace/skills/wuhoo/wuhoo-stock-pick/stock_pick.py`
- `FACTORS_DIR` → `~/wuhoo-workspace/data/stock-pick/factors/`
- `DEBATE_PATH` → `~/wuhoo-workspace/skills/wuhoo/wuhoo-debate/`

不再需要软链接或手动复制文件。

### CN 模拟账户可用时的注意事项

CN 模拟账户 18767295 **已确认可用**（需 `filter_trdmarket=TrdMarket.CN`）。交易时注意：

1. **行情权限缺失**：A 股 `get_market_snapshot()` 不可用，需从本地日线数据获取价格
2. **市价单优先**：限价单可能挂起不成交，市价单秒级成交
3. **辩论价格偏差**：辩论假设的价格可能与实际偏离较大（如 300098 假设 ¥10.0 vs 实际 ¥5.51），执行前需验证价格

### 🔴 A 股交易时段陷阱：午盘休市下单全部卡 SUBMITTED

**A 股交易时段**：上午 9:30-11:30，下午 13:00-15:00。**11:30-13:00 为午间休市**。在此期间提交的市价单全部停留在 SUBMITTED 状态，不会成交，必须等到 13:00 开盘。

**症状**（2026-05-21 实测）：
- 11:42 提交 6 笔 CN 市价卖单，全部 `order_status=SUBMITTED`
- `refresh_cache=True` 后持仓和现金均未变化
- 即使 `order_type=OrderType.MARKET` 也无法在休市期间成交

**正确做法**：
```bash
# 下单前先检查 A 股市场状态
python3.11 -c "
from datetime import datetime
now = datetime.now()
h = now.hour + now.minute/60
if not (9.5 <= h <= 11.5 or 13.0 <= h <= 15.0):
    print('⚠️ A 股休市，等待开盘后再下单')
    exit(1)
"
```

**已挂单处理**：
- 搁置等待 → 13:00 自动成交（适用于午休前下单）
- 撤单重来 → `modify_order(modify_order_op=ModifyOrderOp.CANCEL, ...)` 取消后在开盘时重新下

```python
# 批量取消 SUBMITTED 订单
for _, o in orders[orders['order_status'] == 'SUBMITTED'].iterrows():
    trd.modify_order(
        modify_order_op=ModifyOrderOp.CANCEL,
        order_id=o['order_id'], qty=0, price=0,
        trd_env=TrdEnv.SIMULATE, acc_id=ACC_ID
    )
```

### 🔴 下单频率限制：30 秒内最多 15 次

Futu OpenD 对所有订单类型施加频率限制：**每 30 秒最多 15 次下单**（含买卖）。超过后返回错误 `下单频率太高，请求失败，每30秒最多15次`。

**实际触发场景**（2026-05-26 US 调仓）：卖出 9 只 + 买入 8 只 = 17 次下单，第 16-17 次（MMM、HON）被拒绝。

**解决方案**：
1. **拆分批次**：每批 ≤ 15 次下单，批次间 `sleep(35)` 让计数器重置
2. **优先级排序**：先下卖单（释放资金），再下买单
3. **失败重试**：检测频率限制错误后 `sleep(35)` 重试
4. **预估下单数**：卖单数 + 买单数 > 15 则自动拆分

```python
# ✅ 正确：拆分批次
MAX_ORDERS_PER_WINDOW = 15
all_orders = sell_orders + buy_orders
for i in range(0, len(all_orders), MAX_ORDERS_PER_WINDOW):
    batch = all_orders[i:i + MAX_ORDERS_PER_WINDOW]
    for code, side, qty in batch:
        place_order(...)
    if i + MAX_ORDERS_PER_WINDOW < len(all_orders):
        print(f'批次 {i//MAX_ORDERS_PER_WINDOW+1} 完成，等待 35s...')
        time.sleep(35)
```



`OpenSecTradeContext.__init__` 签名为 `(self, filter_trdmarket, host, port, is_encrypt, security_firm, ai_type)`。**`filter_trdmarket` 是第一个位置参数**，不是仅关键字参数。

混用位置参数和关键字参数会报 `TypeError: got multiple values for argument 'filter_trdmarket'`：

```python
# ❌ 错误：host/port 位置传入 + filter_trdmarket 关键字 → 冲突
ctx = OpenSecTradeContext('127.0.0.1', 11111, filter_trdmarket=TrdMarket.HK)

# ✅ 正确：全部用关键字参数
ctx = OpenSecTradeContext(host='127.0.0.1', port=11111, filter_trdmarket=TrdMarket.HK)

# ✅ 也正确：全部用位置参数（不推荐，可读性差）
ctx = OpenSecTradeContext(TrdMarket.HK, '127.0.0.1', 11111)
```

### Futu API 常用模式速查
| 操作 | API | Context |
|------|-----|---------|
| 查行情 | `get_market_snapshot(codes)` | `OpenQuoteContext` |
| 下单 | `place_order(price, qty, code, trd_side, order_type, trd_env, acc_id)` | `OpenSecTradeContext` |
| 查持仓 | `position_list_query(trd_env, acc_id)` | `OpenSecTradeContext` |
| 查订单 | `order_list_query(trd_env, acc_id)` | `OpenSecTradeContext` |

## 🐛 多市场调仓工作流陷阱

### 🔴 必须「先卖后买」：卖出未成交时购买力不足

批量调仓时，如果在卖出订单尚未成交时就提交买入订单，会因卖出资金未释放导致后续买单全部报「账户购买力不足」：

```python
# ❌ 错误：卖和买混在同一批次
for code in sell_list:
    place_order(SELL, code)  # 限价单，可能一直 SUBMITTED
for code in buy_list:
    place_order(BUY, code)   # ❌ 卖出未成交，购买力不足！

# ✅ 正确：卖出 → 确认成交 → 买入
# Step 1: 市价卖出（确保立即成交）
for code in sell_list:
    place_order(SELL, code, order_type=OrderType.MARKET)

# Step 2: 验证全部卖出已成交
orders = order_list_query(refresh_cache=True)
assert all(o['order_status'] == 'FILLED_ALL' for o in sell_orders)

# Step 3: 查询最新现金余额
cash = accinfo_query(...)['cash']

# Step 4: 按最新现金计算买入数量并下单
for code in buy_list:
    place_order(BUY, code, qty=calc_qty(cash, ...))
```

**关键点**：
- 市价单（MARKET）秒级成交，限价单可能挂单不成交
- 卖出后必须 `refresh_cache=True` 查询订单状态和现金
- 港股限价单低于 bid 时不会成交，需撤单后重新以 ask 价下单
- 同一连接内连续下单需加 `time.sleep(0.3)` 避免频率限制

### 🔴 CN 模拟盘市价买入「购买力不足」反复失败

即使 `accinfo_query` 显示现金充足，A 股市价买单仍可能报「账户购买力不足」。原因可能是前序订单冻结资金尚未释放。

**解决方法：递减重试**

```python
# ❌ 一次性全额买入 → 可能失败
place_order(BUY, 'SZ.300459', qty=23800, order_type=MARKET)  # ❌ 购买力不足

# ✅ 递减重试直到成功
for qty in [20000, 15000, 10000, 5000]:
    ret, data = place_order(BUY, code, qty=qty, order_type=MARKET)
    if ret == RET_OK:
        break  # ✅ 成功
```

此问题在批量市价买入的最后几只时特别容易出现，建议预留 5-10% 现金缓冲。

### 数据路径不匹配

`workflow_c_multi_market.py` 硬编码的路径与项目实际结构不一致：

| 变量 | 脚本硬编码 | 实际路径 |
|------|-----------|---------|
| `FACTORS_DIR` | `~/.hermes/data/stock-pick/factors/` | `~/wuhoo-workspace/data/stock-pick/factors/` |
| `STOCK_PICK_SCRIPT` | `~/wuhoo-workspace/skills/stock-pick/stock_pick.py` | `~/wuhoo-workspace/skills/wuhoo/wuhoo-stock-pick/stock_pick.py` |

**症状**：`--skip-select` 时脚本在 `FACTORS_DIR` 找不到 `result_cn_*.csv`，报「无可用选股结果」。
**修复**：创建软链接或复制文件到脚本期望的路径：
```bash
mkdir -p ~/.hermes/data/stock-pick
ln -sf ~/wuhoo-workspace/data/stock-pick/factors ~/.hermes/data/stock-pick/factors
# 或直接复制
cp ~/wuhoo-workspace/data/stock-pick/factors/result_cn_20260430.csv ~/.hermes/data/stock-pick/factors/
```

### ✅ --debate-file 已支持外部辩论结果 (2026-06-09)

新增 `--debate-file <path>` 参数，可加载 batch_debate.py 产出的 `debate_summary.json`：
```bash
python3.11 workflow_c_multi_market.py --market hk --skip-debate \
  --debate-file ~/wuhoo-workspace/data/debate/20260609/deepseek/debate_summary.json
```
Trader=SELL 的股票自动排除买入，BUY 的股票进入推荐流程。

**当前 workaround**：在此 gap 修复前，A 股调仓需手动编写交易脚本直接调用 Futu API，基于 `debate_summary.json` 中的 Trader 决策逐只下单。

### CN 市场配置错误

脚本 `MARKET_CONFIG['cn']` 硬编码 `acc_id: 18767295`，但此账户已不存在。CN 交易前需确认可用账户并更新配置或传参覆盖。

## 参考文件

- `references/20260609-strategy-comparison.md` — 策略对比回测（趋势动量 vs 超跌反弹 + 市场自适应）
- `references/20260609-all-strategies-comparison.md` — 全策略回测排名（5×US + 4×CN + 3×HK）
- `references/20260609-regime-breadth-mask-fix.md` — Regime 广度 Mask 修复（CN 误判根因）
- `references/20260609-backtest-results.md` — 三市场 Walk-forward 回测结果
- `references/futu-rebalance-pitfalls.md` — Futu 批量调仓常见陷阱（价格精度、频率限制、限价对齐）
- `references/20260506-cn-workflow-audit.md` — 2026-05-06 A股全链路审计（数据→选股→辩论→调仓失败）
- `references/20260513-ahk-rebalance-audit.md` — 2026-05-13 A/HK 双市场调仓审计（卖前买后购买力不足 + 构造函数签名陷阱 + CN 购买力递减重试）
- `references/20260521-ahk-rebalance-audit.md` — 2026-05-21 A/HK 调仓审计（跳过辩论导致反向交易：长实+安踏买入后辩论看空 + A 股午盘休市卡 SUBMITTED）
- `references/20260610-hk-us-cn-rebalance.md` — 2026-06-10 三市场联合调仓（HK 4只秒成交→推翻HK卡单说法；CN减仓→现金率59%；US HON止损监控）
- `scripts/rebalance_us.py` — 美股等权调仓执行脚本模板
```\\nskills/wuhoo-trade/\\n  workflow_c_multi_market.py   # 主交易执行流程\\n  workflow_e_periodic_trade.py # 定期交易\\n  us_equal_weight_portfolio.py # 美股等权策略\\n  pnl_tracker.py               # 每日组合净值快照 + 绩效指标\\n  backtest.py                  # Walk-forward 策略回测（支持 contrarian/momentum/both）\\n  trend_momentum.py            # 趋势动量策略（Phase 2，2026-06-09）\\n  market_regime.py             # 市场状态判定模块（Phase 2，2026-06-09）\\n  risk_manager.py              # 风控模块\\n  audit_module.py              # 持仓审计\\n  portfolio_metrics.py         # 组合指标计算\\n  daily_review.py              # 每日复盘\\n  approval_manager.py          # 审批管理\\n  path_config.py               # 统一路径配置\\n  tests/                       # 测试\\n```
