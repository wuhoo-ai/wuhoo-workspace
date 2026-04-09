---
name: quantaalpha-skill
description: "QuantaAlpha - LLM 驱动的自进化量化因子挖掘框架。使用自然语言描述研究方向，自动挖掘、进化和验证 Alpha 因子。支持 OpenAI 兼容 API（百炼/通义千问可用）。"
metadata: { "openclaw": { "emoji": "🧬", "requires": { "bins": ["python3.11"], "env": [] } } }
---

# QuantaAlpha Skill - LLM 驱动的量化因子挖掘

## 概述

QuantaAlpha 是一个结合 LLM 智能与进化策略的量化 Alpha 因子挖掘框架。只需描述研究方向，即可自动挖掘、进化和验证 Alpha 因子。

**论文**: https://arxiv.org/abs/2602.07085  
**GitHub**: https://github.com/QuantaAlpha/QuantaAlpha

## 核心特性

- 💬 **自然语言输入** - 用中文/英文描述研究方向
- 🧩 **多样化规划** - 从多个角度生成初始因子假设
- 🔄 **自进化轨迹** - 因子在进化轨迹中自我优化
- ✅ **自动验证** - 使用 Qlib 进行回测验证

## 目录结构

```
~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/
├── configs/              # 配置文件
├── quantaalpha/          # 核心代码
├── data/
│   ├── qlib/cn_data/     # Qlib A 股数据 (2016-2025)
│   └── results/          # 输出结果
├── git_ignore_folder/
│   └── factor_implementation_source_data/  # 价格 - 成交量数据
├── venv/                 # Python 3.11 虚拟环境
├── .env                  # 环境配置
└── run.sh                # 启动脚本
```

## 使用方式

### 1. 激活环境
```bash
cd ~/.openclaw/workspace/agents/main/skills/quantaalpha-deep
source venv/bin/activate
```

### 2. 运行因子挖掘
```bash
# 基础用法
./run.sh "量价因子挖掘"

# 示例研究方向
./run.sh "Price-Volume Factor Mining"
./run.sh "Microstructure Factors"
./run.sh "Momentum and Reversal Strategies"
./run.sh "波动率相关因子"
```

### 3. 查看结果
```bash
# 因子库
cat data/results/all_factors_library.json

# 回测结果
cat data/results/backtest_results/*.csv
```

### 4. 独立回测
```bash
# 使用自定义因子回测
python -m quantaalpha.backtest.run_backtest \
  -c configs/backtest.yaml \
  --factor-source custom \
  --factor-json data/results/all_factors_library.json

# 结合 Alpha158 基线
python -m quantaalpha.backtest.run_backtest \
  -c configs/backtest.yaml \
  --factor-source combined \
  --factor-json data/results/all_factors_library.json
```

## 研究方向示例

| 方向 | 描述 |
|------|------|
| **量价因子** | Price-Volume Factor Mining |
| **微观结构** | Market Microstructure Patterns |
| **动量策略** | Momentum and Reversal Effects |
| **波动率** | Volatility-based Factors |
| **流动性** | Liquidity and Trading Activity |
| **资金流** | Order Flow and Capital Flow |

## 配置说明

### 环境变量 (.env)
```bash
# 数据路径
QLIB_DATA_DIR=/home/admin/.openclaw/workspace/agents/main/skills/quantaalpha-deep/data/qlib/cn_data
DATA_RESULTS_DIR=/home/admin/.openclaw/workspace/agents/main/skills/quantaalpha-deep/data/results

# LLM API (支持 OpenAI 兼容 API)
# 阿里云百炼配置（推荐）
OPENAI_API_KEY=sk-sp-xxxxxxxxxxxxxxxx  # 百炼 API Key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
REASONING_MODEL=qwen-max
CHAT_MODEL=qwen-max

# 或使用原生 OpenAI
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
# OPENAI_BASE_URL=https://api.openai.com/v1
# REASONING_MODEL=o1
# CHAT_MODEL=gpt-4o
```

### 修改 API 配置
```bash
cd ~/.openclaw/workspace/agents/main/skills/quantaalpha-deep
nano .env  # 编辑配置
```

## 性能指标

根据论文数据（沪深 300 → 中证 500 迁移）：

| 指标 | 数值 |
|------|------|
| Information Coefficient (IC) | 0.1501 |
| Rank IC | 0.1465 |
| 年化超额收益 (ARR) | 27.75% |
| 最大回撤 (MDD) | 7.98% |
| Calmar 比率 | 3.4774 |

## 数据说明

| 数据 | 说明 | 大小 |
|------|------|------|
| cn_data | Qlib A 股数据 (2016-2025) | 493 MB |
| daily_pv.h5 | 全量价格 - 成交量数据 | 398 MB |
| daily_pv_debug.h5 | 调试子集 | 1.41 MB |

## 故障处理

| 问题 | 解决方案 |
|------|----------|
| API Key 错误 | 检查 .env 中的 OPENAI_API_KEY 格式（百炼 Key 以 `sk-sp-` 开头）|
| 数据路径错误 | 确认 QLIB_DATA_DIR 指向正确的目录 |
| 内存不足 | 使用 daily_pv_debug.h5 进行测试 |
| 因子挖掘超时 | 调整 FACTOR_MINING_TIMEOUT 参数 |
| 模型调用失败 | 确认 OPENAI_BASE_URL 与 API Key 匹配 |

## Web Dashboard (可选)

```bash
cd ~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/frontend-v2
bash start.sh
# 访问 http://localhost:3000
```

## 相关资源

- 中文文档：`docs/README_CN.md`
- 用户指南：`docs/user_guide.md`
- 实验指南：`experiment/README_EXPERIMENT_CN.md`
- 团队主页：https://quantaalpha.github.io/

## 引用

```bibtex
@misc{han2026quantaalpha,
  title={QuantaAlpha: An Evolutionary Framework for LLM-Driven Alpha Mining},
  author={Jun Han et al.},
  year={2026},
  eprint={2602.07085},
  archivePrefix={arXiv},
  primaryClass={q-fin.ST},
}
```

---

*部署时间：2026-03-12*  
*版本：0.1.0*  
*Python: 3.11.13*
