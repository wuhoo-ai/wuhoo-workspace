# QuantaAlpha 因子挖掘阶段性成果总结

**总结时间**: 2026-03-14  
**运行周期**: Mar 12 - Mar 13 (约 7 天)  
**进程状态**: ✅ 已结束 (PID 698949)

---

## 📊 项目概述

**QuantaAlpha** 是一个基于大语言模型 (LLM) 驱动的量化因子自动挖掘系统。

### 核心目标
- ✅ **自动化因子发现**: 利用 LLM 生成市场假设并转化为可计算的因子表达式
- ✅ **进化式优化**: 通过变异 (Mutation) 和交叉 (Crossover) 操作迭代优化因子质量
- ✅ **端到端回测验证**: 基于 Qlib 框架进行因子回测

---

## 🔬 实验配置

### 运行参数

| 参数 | 配置值 |
|------|--------|
| **探索方向** | Momentum and Reversal Strategies (动量与反转策略) |
| **并行方向数** | 2 个 |
| **最大循环次数** | 2 次 |
| **每循环步数** | 5 步 (propose/construct/calculate/backtest/feedback) |
| **回测市场** | A 股 (cn_data) |
| **股票池** | 中证 500/800/1000 |

### 进化流程

```
用户输入 (动量与反转策略)
        ↓
   Planning (生成 2 个并行探索方向)
        ↓
   Evolution Controller
   ┌──────────────────────────────────────┐
   │ Original → Mutation → Crossover → ... │
   │   原始轮    变异轮     交叉轮   循环   │
   └──────────────────────────────────────┘
        ↓
   QuantAgentLoop (5 步循环)
   1. factor_propose    → LLM 生成市场假设
   2. factor_construct  → LLM 生成因子表达式
   3. factor_calculate  → 解析并计算因子值
   4. factor_backtest   → Qlib 回测
   5. feedback          → LLM 分析反馈 + 因子入库
        ↓
   因子库 JSON (所有有效因子归档)
```

---

## 📈 原始因子组合 (10 个)

### 组合 1: 中期趋势稳定性
| 因子 | 表达式 | 含义 |
|------|--------|------|
| RSQR10 | `Rsquare($close, 10)` | 10 日价格线性回归 R²，反映中期趋势稳定性 |
| KLEN | `($high-$low)/$open` | 日内 K 线总长度，衡量价格波动幅度 |
| WVMA5 | `Std(Abs($close/Ref($close, 1)-1)*$volume, 5)/...` | 5 日成交量加权价格波动率 |

### 组合 2: 长期反转与量价关系
| 因子 | 表达式 | 含义 |
|------|--------|------|
| ROC60 | `Ref($close, 60)/$close` | 60 日价格反转因子 |
| CORR20 | `Corr($close, Log($volume+1), 20)` | 20 日收盘价与成交量对数的相关系数 |
| VSTD5 | `Std($volume, 5)/($volume+1e-12)` | 5 日成交量标准差 |

### 组合 3: 价格偏离与支撑
| 因子 | 表达式 | 含义 |
|------|--------|------|
| RESI5 | `Resi($close, 5)/$close` | 5 日线性回归残差 |
| KLOW | `(Less($open, $close)-$low)/$open` | K 线下影线长度 |
| STD5 | `Std($close, 5)/$close` | 5 日收盘价标准差 |

### 组合 4-10: (略)

包括：长期趋势稳定性、量价共振、资金流向、涨跌占优程度等维度。

---

## 📁 数据产出

### 因子数据文件

**位置**: `~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/data/qlib/cn_data/features/`

**格式**: Qlib 二进制格式 (factor.day.bin)

**覆盖股票**:
- sh601886 (凤凰航运)
- sz002990 (中农联合)
- sz000417 (合肥百货)
- sz002300 (太阳电缆)
- sh688426 (康为世纪)
- ... (多个股票)

### 回测结果

**位置**: `~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/data/results/`

| 目录 | 说明 |
|------|------|
| `pickle_cache_exp_20260312_210019/` | 回测缓存数据 |
| `workspace_exp_20260312_210019/` | 回测工作空间 (7.9GB) |

### 运行日志

**位置**: `~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/log/2026-03-12_13-00-20-214241/`

**运行时间**: Mar 12 13:00 - Mar 13 (持续约 36 小时)

---

## 🎯 技术架构

### 核心组件

| 组件 | 功能 |
|------|------|
| **Planning** | 并行探索方向生成 (LLM 驱动) |
| **Evolution Controller** | 进化流程控制 (变异/交叉) |
| **QuantAgentLoop** | 5 步因子挖掘循环 |
| **Qlib 回测** | 因子绩效评估 |
| **因子库** | 有效因子归档 (JSON) |

### 依赖环境

- **Python**: 3.11
- **Qlib**: 量化回测框架
- **LLM**: 百炼 API (qwen 系列模型)
- **数据**: A 股日线数据

---

## 📊 资源消耗

| 资源 | 消耗量 |
|------|--------|
| **CPU 时间** | 593 小时 (约 24.7 天 CPU 时间) |
| **内存占用** | 521MB (峰值) |
| **磁盘空间** | 7.9GB (回测结果) |
| **运行时长** | ~36 小时 (实际时间) |

---

## ✅ 阶段性成果

### 已完成

1. ✅ **环境搭建**: QuantaAlpha 完整部署
2. ✅ **数据准备**: A 股日线数据加载 (中证 500/800/1000)
3. ✅ **初始因子库**: 10 个因子组合，共 30 个基础因子
4. ✅ **回测框架**: Qlib 回测环境配置完成
5. ✅ **运行验证**: 成功执行因子挖掘流程

### 进行中

⏸️ **因子进化**: 已启动进化流程 (变异/交叉)
⏸️ **回测分析**: 部分因子已完成回测

### 待完成

⏳ **因子库生成**: 完整因子库 JSON 输出
⏳ **绩效分析**: 因子 IC/IR 分析
⏳ **可视化报告**: 因子绩效可视化

---

## 🔍 下一步建议

### 短期 (1-2 周)

1. **完成因子进化循环**
   - 执行完整的 Mutation/Crossover 循环
   - 生成更多衍生因子

2. **因子绩效分析**
   - 计算 IC (信息系数)
   - 计算 IR (信息比率)
   - 分组回测 (十分组收益)

3. **因子筛选**
   - 剔除低质量因子
   - 保留高 IC、高 IR 因子

### 中期 (2-4 周)

1. **因子组合优化**
   - 多因子合成
   - 权重优化

2. **策略回测**
   - 完整策略回测
   - 实盘模拟

3. **风险控制**
   - 行业中性化
   - 市值中性化

---

## 📝 项目文件位置

| 文件/目录 | 路径 |
|-----------|------|
| **项目根目录** | `~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/` |
| **配置文件** | `configs/experiment.yaml` |
| **因子数据** | `data/qlib/cn_data/features/` |
| **回测结果** | `data/results/` |
| **运行日志** | `log/2026-03-12_13-00-20-214241/` |
| **实验配置** | `experiment/original_direction_CN.json` |
| **文档** | `docs/experiment_guide.md` |

---

## 🚀 快速启动命令

```bash
# 进入项目目录
cd ~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/

# 激活虚拟环境
source venv/bin/activate

# 运行因子挖掘
quantaalpha mine --direction "momentum and reversal" --config configs/experiment.yaml

# 独立回测
python backtest_v2/run_backtest.py --config backtest_v2/config.yaml
```

---

**维护者**: main-agent  
**总结时间**: 2026-03-14  
**状态**: ⏸️ 已暂停 (进程已结束)
