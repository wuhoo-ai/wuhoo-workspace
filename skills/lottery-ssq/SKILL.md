---
name: lottery-ssq
description: "双色球数据分析与预测工具 — 基于 3000+ 期历史开奖数据，提供统计分析、号码推荐、策略回测和购买建议。娱乐工具，数学上无法实现长期盈利。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    emoji: "🎱"
    tags: [lottery, prediction, statistics, analysis]
    requires:
      bins: [python3.11]
      pip: [pandas, numpy, requests, beautifulsoup4]
---

# 🎱 lottery-ssq — 双色球分析与预测

> **⚠️ 免责声明**：双色球是独立随机事件，头奖概率 1/17,721,088。本工具提供统计学角度的分析和选号优化，**无法保证中奖或盈利**。所有策略的数学期望值均为负（约 -50%）。请理性购买，量力而行。

## 功能概述

| 功能 | 说明 |
|------|------|
| **数据抓取** | 从中彩网获取全量/增量历史开奖数据 |
| **统计分析** | 频率、遗漏、区间、奇偶、和值、AC值、连号等 10 个维度 |
| **号码预测** | 4 种策略集成推荐，多策略投票输出高共识组合 |
| **策略回测** | 滚动窗口回测 + 蒙特卡洛模拟验证策略表现 |
| **资金管理** | 预算分配、定投策略、风险评估 |

## 快速开始

```bash
cd ~/wuhoo-workspace/skills/lottery-ssq

# 安装依赖
pip install -r requirements.txt

# 首次运行（下载历史数据 + 预测）
python3.11 ssq_predict.py --full

# 更新数据
python3.11 ssq_predict.py --update

# 分析历史数据
python3.11 ssq_predict.py --analyze

# 预测下期号码（默认 5 注）
python3.11 ssq_predict.py --predict

# 自定义注数 + 预算
python3.11 ssq_predict.py --predict --count 10 --budget 50

# 回测验证
python3.11 ssq_predict.py --backtest --periods 100

# 蒙特卡洛模拟
python3.11 ssq_predict.py --backtest --monte-carlo 10000
```

## CLI 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--update` | 更新数据（增量） | - |
| `--analyze` | 运行历史分析 | - |
| `--predict` | 预测号码 | - |
| `--backtest` | 策略回测 | - |
| `--full` | 完整流程（更新+分析+预测） | - |
| `--count N` | 预测注数 | 5 |
| `--budget N` | 月预算（元） | 20 |
| `--seed N` | 随机种子 | 无 |
| `--periods N` | 回测期数 | 100 |
| `--monte-carlo N` | 蒙特卡洛模拟次数 | 0 |
| `--no-advice` | 不显示购买建议 | - |

## 分析维度

### 1. 频率分析
- 全量/近期（50 期）热号冷号统计
- 各号码出现次数与频率

### 2. 遗漏分析
- 当前遗漏值（多少期未出现）
- 历史最大遗漏
- 高遗漏号码识别

### 3. 区间分布（三区比）
- 一区 (1-11)、二区 (12-22)、三区 (23-33)
- 推荐三区比：2:2:2, 2:3:1 等

### 4. 奇偶比
- 最常见：3:3、4:2、2:4

### 5. 和值分析
- 推荐区间：90-130（覆盖 70% 数据）

### 6. AC值（号码复杂度）
- 常见范围：4-9

### 7. 连号分析
- 约 80% 的期次包含连号

### 8. 重号分析
- 通常 1-2 个上期重复号码

### 9. 蓝球专项
- 奇偶比、大小比、012 路分布

### 10. 历史同期
- 同月/同月同日历史偏好

## 预测策略

| 策略 | 权重 | 原理 |
|------|------|------|
| 频率加权 | 30% | 基于出现频率加权随机采样 |
| 遗漏回补 | 25% | 优先选择遗漏值接近历史平均的号码 |
| 统计过滤 | 25% | 用统计条件过滤不合理组合 |
| 形态匹配 | 20% | 匹配历史高频三区比形态 |

**集成推荐**：多策略并行生成候选，按策略共识度投票排序，输出高共识组合。

## 配置

配置文件：`configs/default_config.json`

```json
{
  "strategies": {
    "frequency_weighted": {"weight": 0.30, "enabled": true},
    "omission_recovery": {"weight": 0.25, "enabled": true},
    "statistical_filter": {"weight": 0.25, "enabled": true},
    "pattern_matching": {"weight": 0.20, "enabled": true}
  },
  "constraints": {
    "sum_range": [80, 130],
    "ac_range": [4, 9],
    "max_consecutive": 2,
    "odd_even_ratios": ["3:3", "4:2", "2:4"]
  },
  "generate_count": 5
}
```

## 项目结构

```
skills/lottery-ssq/
├── SKILL.md
├── ssq_predict.py              # CLI 入口
├── requirements.txt
├── configs/
│   └── default_config.json     # 策略配置
├── scripts/
│   ├── fetch_history.py        # 数据抓取
│   ├── analysis_engine.py      # 分析引擎
│   ├── predictor.py            # 预测引擎
│   ├── monte_carlo.py          # 回测模拟
│   └── money_management.py     # 资金管理
├── data/
│   ├── ssq_history.csv         # 历史开奖数据
│   └── ssq_stats.json          # 分析缓存
└── tests/
    └── test_lottery.py           # 20 tests (analysis, predictor, money, monte carlo)
```

## 数据源与已知问题

- **中彩网 (cwl.gov.cn)**：⚠️ **403 反爬**，不可用
- **新浪彩票、17500.cn、zhcw.com**：多数下线或需鉴权
- **500.com**：✅ **当前主数据源**。使用 BeautifulSoup 解析 HTML 表格，支持全量和增量更新。
  - URL: `https://datachart.500.com/ssq/history/newinc/history.php?start={start}&end={end}`
  - 优点：无需 API Key、无需鉴权、支持任意日期范围
  - 注意：HTML 结构若改版需同步更新选择器（`table.tdata` → `tr.t_tr1` → `td`）

**真实数据**：`data/ssq_history.csv` 含 3441 条真实开奖记录（2003-2026）。

**数据清洗关键**：
- 500.com 数据混合了 7 位期号（模拟/旧版）和 5 位期号（真实）
- 必须过滤 `issue.str.len() == 5`，否则统计和期号推算出错
- 5 位期号格式：前 2 位=年（26=2026），后 3 位=期数（001-160）

**依赖**：需安装 `beautifulsoup4`：`pip install beautifulsoup4`

数据格式：CSV（期号, 日期, 红1-6, 蓝球, 销售额, 奖池）

## 依赖

- Python 3.11+
- pandas >= 2.0.0
- numpy >= 1.24.0
- requests >= 2.28.0

## 注意事项

1. **数学事实**：双色球无法通过任何策略实现长期正收益
2. **理性购买**：建议月预算不超过月收入的 2%
3. **娱乐为主**：数据可视化和统计分析本身有参考价值
4. **数据时效**：建议在开奖前更新最新数据
5. **随机种子**：设置 `--seed` 可复现预测结果
