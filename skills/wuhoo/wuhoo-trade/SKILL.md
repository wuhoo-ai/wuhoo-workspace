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
- **风控管理**: `python3.11 skills/wuhoo-trade/risk_manager.py`
- **持仓审计**: `python3.11 skills/wuhoo-trade/audit_module.py`
- **组合指标**: `python3.11 skills/wuhoo-trade/portfolio_metrics.py`
- **每日复盘**: `python3.11 skills/wuhoo-trade/daily_review.py`
- **美股等权持仓**: `python3.11 skills/wuhoo-trade/us_equal_weight_portfolio.py [show|rebalance|check]`

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
| HK   | 18767296 | MARGIN | SIMULATE | HK | ✅ |

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

## 风控集成 (2026-04-24 更新)
- `_debate_quick()` 方法已集成 `RiskAgent.review()` 进行风控审核
- 构建 `trader_decision` 结构传递止损/止盈/仓位/RRR 给 RiskAgent
- 降级策略：RiskAgent 不可用时使用简化风控（波动率、涨幅、Beta 检查）
- RRR 计算修正：`潜在收益 / 潜在损失` = `(止盈价-现价) / (现价-止损价)`

## 风控规则差距分析 (2026-04-24)

**risk_rules.yaml 定义 13 条规则，实际仅 5 条生效：**

| 规则 | YAML 定义 | risk_agent.py | risk_manager.py | 状态 |
|------|-----------|--------------|-----------------|------|
| single_stock_max 20% | ✅ | ✅ | ✅ | 已实现 |
| single_industry_max 40% | ✅ | ❌ | ❌ | **未实现** |
| cash_min 10% | ✅ | ❌ | ✅ | risk_manager 实现 |
| 分层仓位管理 | ✅ | ❌ | ❌ | **未实现** |
| 动态止损（波动率调整） | ✅ | ❌ | ⚠️ 部分 | **需完善** |
| RRR min_ratio 2.0 | ✅ | ✅ | ❌ | RiskAgent 实现 |
| 流动性检查 | ✅ | ✅ | ❌ | RiskAgent 实现 |
| 事件风险（财报黑名单） | ✅ | ❌ | ❌ | **未实现** |
| 相关性检查 max_correlation 0.7 | ✅ | ❌ | ❌ | **未实现** |
| 自动审批条件 | ✅ | ⚠️ 未使用 | ❌ | **未生效** |
| CONDITIONAL 阻断 | ✅ | ❌ | ❌ | **未阻断** |
| max_drawdown 15% | ✅ | ❌ | ❌ | **未实现** |
| volatility high_threshold 0.60 | ✅ | ⚠️ pass当无数据 | ❌ | **形同虚设** |

**关键发现**：
1. RiskAgent `_check_volatility()` 无 market_data 时默认 pass，实际调用几乎从不传入 → 波动率检查形同虚设
2. RiskAgent `_check_concentration()` 依赖 `industry_exposure` 字段，但调用方从未传入 → 集中度检查永远 pass
3. CONDITIONAL 结果未阻断交易执行路径
4. 组合级风控（回撤/行业集中度/相关性）完全缺失

**计划新增 `portfolio_risk.py`** 模块，实现：
- `check_portfolio_drawdown()` → 组合级回撤检查（阈值 15%）
- `check_industry_concentration()` → 行业集中度（阈值 40%）
- `check_correlation()` → 持仓相关性（阈值 0.7）
- `check_event_risk()` → 事件风险（财报日检查）
- `apply_tier_position()` → 分层仓位管理（按 confidence 分配）
- `enforce_risk_decision()` → 强制 RiskAgent 结果执行（CONDITIONAL 需确认或阻断）

## 🐛 港股交易陷阱

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

### 🐛 workflow_c 路径不匹配（2026-05-06 发现）

`workflow_c_multi_market.py` 硬编码了数据路径，与实际目录不一致：

```python
# 脚本中的路径（第71行）
FACTORS_DIR = Path.home() / '.hermes' / 'data' / 'stock-pick' / 'factors'

# 实际数据路径
# ~/wuhoo-workspace/data/stock-pick/factors/
```

**症状**：`--skip-select --skip-debate` 运行时输出 "❌ 无可用选股结果"，即使选股已完成且结果文件存在。

**临时解决**：将结果 CSV 复制到脚本期望的路径：
```bash
cp ~/wuhoo-workspace/data/stock-pick/factors/result_cn_YYYYMMDD.csv \
   ~/.hermes/data/stock-pick/factors/
```

**长期修复**：修改 `workflow_c_multi_market.py:71` 的 `FACTORS_DIR` 指向实际路径。

### CN 模拟账户可用时的注意事项

CN 模拟账户 18767295 **已确认可用**（需 `filter_trdmarket=TrdMarket.CN`）。交易时注意：

1. **行情权限缺失**：A 股 `get_market_snapshot()` 不可用，需从本地日线数据获取价格
2. **市价单优先**：限价单可能挂起不成交，市价单秒级成交
3. **辩论价格偏差**：辩论假设的价格可能与实际偏离较大（如 300098 假设 ¥10.0 vs 实际 ¥5.51），执行前需验证价格

### Futu API 常用模式速查
| 操作 | API | Context |
|------|-----|---------|
| 查行情 | `get_market_snapshot(codes)` | `OpenQuoteContext` |
| 下单 | `place_order(price, qty, code, trd_side, order_type, trd_env, acc_id)` | `OpenSecTradeContext` |
| 查持仓 | `position_list_query(trd_env, acc_id)` | `OpenSecTradeContext` |
| 查订单 | `order_list_query(trd_env, acc_id)` | `OpenSecTradeContext` |

## 🐛 workflow_c 路径与集成陷阱

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

### --skip-debate 无法使用外部辩论结果

`workflow_c_multi_market.py --skip-debate` 会完全跳过 Step 3（辩论），导致 Step 4（投资建议）输出空数组（`recommendations: [], count: 0`），Step 5 无任何交易。

**根因**：脚本设计为全链路自执行，不支持加载外部 `batch_debate.py` 产出的 `debate_*.json`。`--skip-debate` 只适用于「只选股不辩论」的简化场景，不适用于「已通过 batch_debate 完成辩论，只需执行交易」的场景。

**当前 workaround**：在此 gap 修复前，A 股调仓需手动编写交易脚本直接调用 Futu API，基于 `debate_summary.json` 中的 Trader 决策逐只下单。

### CN 市场配置错误

脚本 `MARKET_CONFIG['cn']` 硬编码 `acc_id: 18767295`，但此账户已不存在。CN 交易前需确认可用账户并更新配置或传参覆盖。

## 参考文件

- `references/futu-rebalance-pitfalls.md` — Futu 批量调仓常见陷阱（价格精度、频率限制、限价对齐）
- `references/20260506-cn-workflow-audit.md` — 2026-05-06 A股全链路审计（数据→选股→辩论→调仓失败）
- `scripts/rebalance_us.py` — 美股等权调仓执行脚本模板
```
skills/wuhoo-trade/
  workflow_c_multi_market.py   # 主交易执行流程
  workflow_e_periodic_trade.py # 定期交易
  us_equal_weight_portfolio.py # 美股等权策略
  risk_manager.py              # 风控模块
  audit_module.py              # 持仓审计
  portfolio_metrics.py         # 组合指标计算
  daily_review.py              # 每日复盘
  approval_manager.py          # 审批管理
  path_config.py               # 统一路径配置
  tests/                       # 测试
```
