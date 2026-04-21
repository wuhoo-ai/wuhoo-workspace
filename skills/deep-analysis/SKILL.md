---
name: wuhoo-stock-deep-analysis
description: "单股深度分析与决策建议（Workflow B 增强版）。整合 akshare 财务数据 + 因子数据 + 多空辩论，输出 4 部分完整投资分析报告（定性→定量→估值→决策）。wuhoo 冠名 skill 为 OpenClaw 企业级关键 skill，需重点维护。"
metadata: { "openclaw": { "emoji": "🔬", "requires": { "bins": ["python3.11"], "pip": ["akshare", "pandas", "numpy"] } } }
---

# wuhoo-stock-deep-analysis — 单股深度分析（Workflow B 增强版）

> **⚠️ 企业级关键 Skill**
> 以 `wuhoo-` 冠头的 skill 是当前 OpenClaw 系统的**企业级关键 skill**，承担核心业务价值。
> 这些 skill 的代码质量、稳定性和可维护性需要特别关注。

## 功能概述

对**单只股票**进行全方位深度分析，整合多源数据（akshare 财务 + DataAggregator 因子 + 技术面），生成结构化的 4 部分投资决策报告。

**适用场景**：用户指定某只股票（如 "帮我深度分析一下 600519"），需要全面的投资视角。

## 报告结构

### 第一部分：定性分析 — 商业模式与经济护城河
- 商业模式阐释（如何赚钱、客户、收入来源）
- 经济护城河评估（品牌/网络效应/成本优势/转换成本/无形资产）
- 管理层与资本配置评估
- 行业格局与成长空间（波特五力模型）

### 第二部分：定量分析 — 财务健康与盈利能力
- 财务健康状况（资产负债率、利息保障倍数、自由现金流）
- 盈利能力与效率（ROE、毛利率/净利率趋势、资产周转率）
- 成长性分析（营收/净利润/FCF 的 5 年 CAGR）
- 财务异常检测（应收/存货/现金流背离等红旗信号）

### 第三部分：估值分析 — 内在价值与安全边际
- 三阶段 DCF 模型（乐观/中性/悲观三情景，含详细计算过程）
- 相对估值（PE/PB/PS/EV-EBITDA 历史分位 + 同业对比）
- 安全边际计算与理想买入价格

### 第四部分：投资决策建议 — 综合研判与交易计划
- 核心优势总结（1-3 点）
- 主要风险识别（1-3 点）
- 明确决策：【强烈买入/买入/持有/卖出/强烈卖出】
- 仓位建议（核心/卫星）、买入策略、卖出纪律

## 使用方式

```bash
# 增强版深度分析（推荐，整合 akshare 财务数据）
python ~/.openclaw/skills/wuhoo-stock-deep-analysis/deep_analysis.py --code 600519

# 港股
python ~/.openclaw/skills/wuhoo-stock-deep-analysis/deep_analysis.py --code 00700 --name 腾讯控股

# 美股（仅因子分析，无 akshare 财务数据）
python ~/.openclaw/skills/wuhoo-stock-deep-analysis/deep_analysis.py --code US.AAPL --name Apple

# 策略报告版（因子数据 + 辩论）
python ~/.openclaw/skills/wuhoo-stock-deep-analysis/strategy_report.py --symbol 600519.SH
```

## 输出

```
~/.openclaw/workspace/agents/trade/data/workflow_b/{code}_{date}/
├── akshare_data.json           # akshare 原始财务数据
├── factor_data.json            # DataAggregator 因子数据
├── valuation_data.json         # 估值计算结果
├── debate_data.json            # 多空辩论结果
├── audit_report.json           # 审计报告（结构化）
├── audit_report.md             # 审计报告（可读 Markdown）
├── all_data.json               # 完整合并数据（含审计）
└── decision_report.md          # 4 部分完整报告
```

### 审计报告

审计报告是分析质量的"质检证书"，包含 8 个审计维度：

| 维度 | 审计内容 |
|------|----------|
| 数据获取 | akshare/Tushare/DataAggregator 可用性与完整性 |
| 公开信息 | 网络搜索、券商研报覆盖度 |
| 定性分析 | 行业识别、护城河证据、管理层分析深度 |
| 定量分析 | ROE/现金流/成长数据覆盖度、数据期数充足性 |
| 估值分析 | DCF 可用性+参数合理性、相对估值+历史分位 |
| 多空辩论 | 辩论方法、多空观点数量、置信度 |
| 一致性校验 | 基本面/估值/辩论结论是否自洽 |
| 红旗检测 | 财务异常识别、极端估值警示 |

**可靠性等级**: A(80+) / B(60-79) / C(40-59) / D(<40)

扣分规则详见 `b_audit.py` 中的 `DEDUCTION_RULES`。

## 数据源

| 数据源 | 内容 | 适用范围 |
|--------|------|----------|
| **akshare** | 利润表、资产负债表、现金流、财务指标、股东、分红 | A 股 |
| **DataAggregator** | 技术因子、基本面因子、舆情面 | A/港/美 |
| **debate 模块** | Bull/Bear/Trader/Risk 四角色辩论 | A/港/美 |

## 降级策略

| 场景 | 降级行为 |
|------|----------|
| akshare 不可用 | 使用 DataAggregator 因子数据，报告标注"基础版" |
| debate 模块不可用 | 回退到纯规则推理多空判断 |
| DCF 数据不完整 | 仅做相对估值，跳过 DCF |
| 港股/美股 | 无 akshare 财务，使用因子数据 + 辩论 |

## 依赖

```bash
# A 股完整分析
pip3.11 install akshare pandas numpy

# 因子数据（trade-agent 环境）
cd ~/.openclaw/workspace/agents/trade
source venv-futu/bin/activate
```

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.0 | 2026-04-09 | 整合 akshare 财务数据，4 部分报告结构，三阶段 DCF |
| 1.0 | 2026-04-09 | 初始版本（因子数据 + 辩论） |

---

*创建时间：2026-04-09 | 版本：2.0*
