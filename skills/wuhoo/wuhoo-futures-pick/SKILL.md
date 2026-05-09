---
name: wuhoo-futures-pick
description: 期货品种筛选 — 基于技术因子的 US+HK 股指期货/贵金属选品，支持做多/做空双向。Phase 1 覆盖 7 个品种（MES/MNQ/MGC/SI/MHI/MCH/HTI）。
version: 0.1.0
category: wuhoo
tags: [wuhoo, futures]
metadata:
  hermes:
    emoji: "📊"
    requires:
      bins: [python3.11]
      pip: [pandas, numpy]
---

# wuhoo-futures-pick — 期货品种筛选

对标 wuhoo-stock-pick，为期货市场设计的品种筛选系统。

## Phase 1 品种（7 个）

| 代码 | 名称 | 市场 | lot_size | 多保证金 | 类型 |
|------|------|:----:|:--------:|:-------:|------|
| US.MESmain | 微型标普500 | US | 5 | $2,408 | 股指 |
| US.MNQmain | 微型纳斯达克100 | US | 2 | $3,637 | 股指 |
| US.MGCmain | 微黄金 | US | 10 | $2,817 | 贵金属 |
| US.SImain | 白银 | US | 5,000 | $42,520 | 贵金属 |
| HK.MHImain | 小恒指 | HK | 10 | HK$17,630 | 股指 |
| HK.MCHmain | 小国指 | HK | 10 | HK$6,730 | 股指 |
| HK.HTImain | 恒生科技指数 | HK | 50 | HK$26,290 | 股指 |

## 统一 venv

所有期货脚本统一使用 hermes-agent venv（已包含 futu-api + yfinance + pandas + ta-lib 等全部依赖）。

| 市场 | 数据源 | venv |
|------|--------|------|
| US 期货 | yfinance (ES=F, NQ=F, GC=F, SI=F) | `~/.hermes/hermes-agent/venv/bin/python3` |
| HK 期货 | Futu OpenD subscribe + get_cur_kline | `~/.hermes/hermes-agent/venv/bin/python3` |

## 使用方式

```bash
VENV=~/.hermes/hermes-agent/venv/bin/python3

# 1. 更新数据
$VENV fetch_futures_kline.py

# 2. 计算因子
$VENV futures_factors.py

# 3. 选品
$VENV futures_pick.py --top-n 3 --direction both

# 4. 调仓（dry-run）
$VENV ../wuhoo-futures-trade/futures_trade.py rebalance --date 2026-05-08

# 5. 查询持仓
$VENV ../wuhoo-futures-trade/futures_trade.py check
```

## 因子体系

| 因子 | 权重 | 说明 |
|------|:----:|------|
| momentum_10d | 30% | 10 日动量，sigmoid 映射 |
| adx_14 | 30% | 趋势强度（手动实现，无 talib 依赖） |
| volatility_20d | 15% | 高斯函数，最优区间 15-30% |
| volume_ratio | 15% | 5 日/20 日均量比 |
| ma20_deviation | 10% | MA20 偏离绝对值越小越好 |

## 数据目录

```
~/wuhoo-workspace/data/futures/
├── daily_kline/{US,HK}/    # 日线 CSV
├── factors/                # 因子 + 选品结果
│   ├── factors_{date}.csv
│   └── pick_result_{date}.csv
├── contract_info.json      # 合约元数据（含保证金）
└── diagnose/               # 持仓诊断（Phase 5）
```

## 全链路工作流 (Phase 0-6 完整)

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-futures-pick
VENV=~/.hermes/hermes-agent/venv/bin/python3

# 一键全链路（选品→技术面→辩论→报告→调仓）
$VENV futures_workflow.py --skip-fetch --skip-debate  # 快速模式 9s
$VENV futures_workflow.py --skip-fetch                 # 含辩论 ~6min
$VENV futures_workflow.py --execute                    # 含实盘调仓

# 分步执行
$VENV futures_factors.py                               # 因子计算
$VENV futures_pick.py --top-n 3 --direction both        # 选品
$VENV futures_technical.py --code US.MNQmain            # 技术面分析
$VENV futures_debate.py --date 2026-05-08               # 辩论
$VENV futures_deep_analysis.py --code US.MNQmain        # 深度报告

# 交易（在 wuhoo-futures-trade 目录）
cd ../wuhoo-futures-trade
$VENV futures_trade.py check                            # 查询持仓
$VENV futures_trade.py rebalance --date 2026-05-08      # 调仓
$VENV futures_risk_manager.py validate-order ...         # 风控验证
$VENV futures_diagnose.py                               # 持仓诊断
```

## 子 Skills

本 skill 包含一个嵌套子 skill：

| 子 Skill | 路径 | 加载方式 |
|----------|------|---------|
| `wuhoo-futures-debate` | `prompts/SKILL.md` | ⚠️ 无法通过 `skill_view()` 加载（非标准路径）。**替代方式**：直接读取 `skills/wuhoo/wuhoo-futures-pick/prompts/SKILL.md`；或传参调用 `futures_debate.py --date <date>` |

### futures-debate 快速参考

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-futures-pick
VENV=~/.hermes/hermes-agent/venv/bin/python3

# 批量辩论（读取 pick_result 自动获取品种）
$VENV futures_debate.py --date 2026-05-08

# 单品种辩论
$VENV futures_debate.py --date 2026-05-08 --code US.MNQmain
```

辩论 prompt 文件：`prompts/bull_futures.md`、`prompts/bear_futures.md`、`prompts/trader_futures.md`、`prompts/risk_futures.md`

## 实测关键发现

- **保证金**: `accinfo_query.initial_margin=N/A`，必须用 `acctradinginfo_query` 逐品种查询
- **US 数据**: yfinance (ES=F, NQ=F) 替代 Futu（需行情权限）
- **HK 数据**: subscribe+get_cur_kline（用订阅额度，非历史额度）
- **单笔限 1000 手**: Futu API 硬限制，大单需拆分
- **MYM 不可交易**: lot_size=0
- **CNmain 是 SG 不是 HK**

---

*创建时间: 2026-05-08 | 版本: 0.1.0 — MVP (Phase 0+1+4)*
