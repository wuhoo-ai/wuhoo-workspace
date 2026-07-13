---
name: wuhoo-value-investing
description: "价值投资研究框架 — 巴菲特/芒格/段永平/李录四大师方法论。整合 ai-berkshire 到 wuhoo 选股→分析→交易流水线。wuhoo 冠名 skill 为 Hermes 企业级关键 skill，需重点维护。"
tags: ["wuhoo", "value-investing"]
category: wuhoo
metadata:
  hermes:
    emoji: "🏛️"
    requires:
      bins: ["python3.11"]
      pip: ["yfinance", "akshare", "pandas", "pyyaml"]
---

# wuhoo-value-investing — 价值投资研究框架

> **⚠️ 企业级关键 Skill**
> 基于 [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire) 的巴菲特-芒格-段永平-李录四大师方法论，揉合到 wuhoo 选股→辩论→分析→交易流水线。

## 核心功能

| 模块 | 入口 | 功能 |
|------|------|------|
| 质量预筛选 | `quality_screen.py` | 7条去劣指标+3豁免，过滤非一流公司 |
| 投资决策 Checklist | `investment_checklist.py` | 6关+镜子测试+8条否决红线 |
| 四大师深度分析 | `value_deep_analysis.py` | 7模块综合分析（生意/护城河/逆向/管理层/文明/估值/决策） |
| 行业漏斗筛选 | `industry_funnel.py` | 5层漏斗（全市场→10家→3家） |
| 组合审视 | `portfolio_review.py` | 集中度/相关性/机会成本/压力测试 |
| 价值投资辩论 | `value_debate.py` | 四大师独立辩论（方案C：独立运行） |
| 论文追踪 | `thesis_tracker.py` | 买入论文记录+定期检查+破裂信号 |
| 精确计算 | `tools/financial_rigor.py` | Decimal计算/市值验算/三情景估值/反向DCF |
| 报告审计 | `tools/report_audit.py` | 15%随机抽检+准出/打回判决 |

## 快速开始

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-value-investing

# === 日常使用（推荐工作流）===

# 1️⃣ 每周一：生成三市场筛选报告（自动推送到微信）
python3.11 weekly_screening_report.py --market all

# 2️⃣ 对报告中的重点标的做 Checklist
python3.11 investment_checklist.py --code AAPL --market us --name Apple

# 3️⃣ Checklist通过后做深度分析
python3.11 value_deep_analysis.py --code AAPL --market us --name Apple

# 4️⃣ 记录投资论文
python3.11 thesis_tracker.py add --code AAPL --market us --name Apple --thesis "..." --buy-price 150

# === 其他功能 ===

# 行业级别标的发现
python3.11 industry_funnel.py --industry "AI算力" --market us

# 四大师价值辩论（与量化辩论并行）
python3.11 value_debate.py --code AAPL --market us --name Apple

# 组合审视（月度）
python3.11 portfolio_review.py --market us

# 论文追踪
python3.11 thesis_tracker.py check --code AAPL --current-price 160
python3.11 thesis_tracker.py list

# 工具
python3.11 tools/financial_rigor.py three-scenario --price 100 --eps 5 --shares 10 --growth 15 10 5 --pe 20 15 10
```

## 与现有 wuhoo 流水线的集成

```
质量预筛选 → 量化选股 → 行业漏斗(新) → 辩论(量化+价值) → 深度分析(增强) → Checklist → 交易执行 → 组合审视(新)
    ↑                                                          ↑
quality_screen.py                          investment_checklist.py
```

**注入点**：
1. **stock_pick.py 前置**：`--quality-filter` 参数，选股前调用 quality_screen.py
2. **辩论并行**：value_debate.py 与 batch_debate_v2.py 并行运行，Trader 综合两者
3. **交易前置**：`--checklist` 参数，Checklist 否决的不执行
4. **定期审视**：portfolio_review.py 月度 run

## 各市场阈值

| 指标 | A股 | 港股 | 美股 |
|------|:---:|:---:|:---:|
| ROE < | 5% | 8% | 8% |
| 负债率 > | 60% | 60%（地产70%） | 60% |
| 毛利率 < | 15% | 15% | 15% |
| 净利率 < | 5% | 5% | 5% |

详见 `configs/quality_thresholds.yaml`

## Cron 任务

| 任务 | 频率 | 说明 |
|------|------|------|
| 质量预筛选 | 每日 8:00 | 对三市场universe运行quality_screen |
| 组合审视 | 每周一 10:00 | 组合集中度/相关性/风险检查 |
| 论文追踪检查 | 每日 21:00 | 检查活跃论文是否成立 |
| 行业监测 | 每周六 14:00 | 扫描1-2个热门行业 |

## 依赖

```bash
pip install yfinance akshare pandas pyyaml
```

- `yfinance`: US/HK 财务数据
- `akshare`: A股财务数据
- `pandas`: 数据处理
- `pyyaml`: 配置文件解析
- LLM: DeepSeek v4-pro（辩论和深度分析用）

## 参考文件

- `references/plan.md` — 集成方案设计文档
- `configs/quality_thresholds.yaml` — 各市场质量阈值配置
- `prompts/` — LLM Prompt 模板（预留）

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-06-29 | 初始版本：8模块完整实现 |

---

*原始 ai-berkshire: https://github.com/xbtlin/ai-berkshire*
*MIT License*
