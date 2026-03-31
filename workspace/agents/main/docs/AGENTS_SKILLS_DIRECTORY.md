# ~/.agents/skills/ 目录说明

**版本**: 2026-03-13  
**用途**: 全局技能存储目录

---

## 📋 目录作用

`~/.agents/skills/` 是 **OpenClaw 全局技能存储目录**，用于存放所有 agent 共享的技能。

---

## 🗂️ 目录结构

```
~/.agents/skills/
├── akshare-stock/          # A 股分析技能
├── backtest/               # VectorBT 回测技能
├── backtesting-frameworks/ # 回测框架文档
├── china-stock-analysis/   # A 股价值投资分析
└── find-skills/            # 技能发现工具 (系统自带)
```

---

## 📦 技能清单

### 1. akshare-stock (A 股分析)

**用途**: A 股实时行情、技术分析、基本面分析  
**依赖**: `akshare`, `pandas`, `numpy`  
**安装方式**: `npx skills add molezzz/openclaw-stock-skill@akshare-stock`

**功能**:
- ✅ 实时大盘行情 (上证指数、深证成指等)
- ✅ 个股实时行情
- ✅ 基本面分析 (财务指标)
- ✅ 资金流向分析
- ✅ 涨跌停统计
- ✅ 板块轮动分析

**使用示例**:
```bash
cd ~/.agents/skills/akshare-stock
source venv/bin/activate
python main.py --query "上证指数实时行情"
python main.py --query "贵州茅台 600519 股票分析"
```

---

### 2. backtest (VectorBT 回测)

**用途**: 快速创建 VectorBT 回测脚本  
**类型**: AI Agent 指令模板  
**安装方式**: `npx skills add marketcalls/vectorbt-backtesting-skills@backtest`

**功能**:
- ✅ 自动生成回测 Python 脚本
- ✅ 支持多种策略 (EMA, RSI, MACD, Supertrend 等)
- ✅ 自动获取历史数据
- ✅ 生成收益统计和图表
- ✅ 基准对比 (NIFTY 50)

**使用示例**:
```bash
# 通过 AI Agent 调用
/backtest ema-crossover 600519 SSE D
/backtest rsi SBIN NSE D
/backtest supertrend NIFTY NFO 5m
```

**输出位置**: `backtesting/{strategy_name}/{symbol}_{strategy}_backtest.py`

---

### 3. backtesting-frameworks (回测框架文档)

**用途**: 回测系统最佳实践指南  
**类型**: 文档/模板  
**安装方式**: `npx skills add wshobson/agents@backtesting-frameworks`

**内容**:
- ✅ 回测偏差处理 (前视偏差、幸存者偏差)
- ✅ 训练/验证/测试集划分
- ✅ 走步向前分析 (Walk-Forward)
- ✅ 事件驱动回测器示例代码
- ✅ 交易成本建模

**使用场景**: 设计和开发回测系统时参考

---

### 4. china-stock-analysis (A 股价值投资分析)

**用途**: A 股价值投资分析工具  
**依赖**: `akshare`, `pandas`, `numpy`  
**安装方式**: `npx skills add sugarforever/01coder-agent-skills@china-stock-analysis`

**功能**:
- ✅ 股票筛选器 (PE, PB, ROE 等条件)
- ✅ 个股深度财务分析
- ✅ 同行业横向对比
- ✅ 内在价值测算
- ✅ 财务异常风险检测

**使用示例**:
```bash
cd ~/.agents/skills/china-stock-analysis/scripts
python stock_screener.py --pe-max 15 --roe-min 15
python financial_analyzer.py --stock 600519
python valuation_calculator.py --stock 000858
```

---

### 5. find-skills (技能发现工具)

**用途**: 帮助用户发现和安装技能  
**类型**: 系统自带技能  
**安装方式**: 系统自动安装

**功能**:
- ✅ 搜索 clawhub.com 技能市场
- ✅ 推荐相关技能
- ✅ 提供安装命令

**使用示例**:
```bash
npx skills find "backtest"
npx skills find "stock analysis"
```

---

## 🔧 为什么放在这个目录？

### 1. 全局共享

`~/.agents/skills/` 是 **所有 agent 共享** 的技能目录：

```
~/.agents/skills/           # ✅ 全局技能
├── akshare-stock/          # main, dev, trade 都可用
└── backtest/               # main, dev, trade 都可用

~/.openclaw/workspace/agents/{agent}/skills/  # Agent 专属技能
├── main/skills/stock-pick/ # 仅 main 可用
└── dev/skills/             # 仅 dev 可用
```

### 2. 自动 symlink

安装到 `~/.agents/skills/` 的技能会自动 symlink 到各 agent：

```bash
# 查看 symlink
ls -la ~/.openclaw/.agents/skills/
# 输出：composio -> ../.agents/skills/composio
#      find-skills -> ../../.agents/skills/find-skills
```

### 3. clawhub 标准位置

`npx skills add` 命令默认安装到 `~/.agents/skills/`：

```bash
# 安装技能
npx skills add {owner/repo@skill}

# 安装位置
~/.agents/skills/{skill-name}/
```

---

## 📊 技能类型对比

| 类型 | 位置 | 用途 | 示例 |
|------|------|------|------|
| **全局技能** | `~/.agents/skills/` | 所有 agent 共享 | akshare-stock, backtest |
| **Agent 专属** | `~/.openclaw/workspace/agents/{agent}/skills/` | 特定 agent 专用 | main/skills/stock-pick |
| **系统技能** | `~/.agents/skills/` (内置) | OpenClaw 核心功能 | find-skills, composio |

---

## 🛠️ 管理命令

### 查看已安装技能

```bash
# 列出所有技能
npx skills list

# 查看技能详情
cat ~/.agents/skills/{skill-name}/SKILL.md

# 查看目录结构
tree -L 2 ~/.agents/skills/
```

### 安装新技能

```bash
# 搜索技能
npx skills find {keyword}

# 安装技能
npx skills add {owner/repo@skill}

# 安装到全局 (默认)
npx skills add {owner/repo@skill} -y
```

### 更新技能

```bash
# 更新所有技能
npx skills update

# 检查更新
npx skills check
```

### 卸载技能

```bash
# 删除技能目录
rm -rf ~/.agents/skills/{skill-name}
```

---

## ⚠️ 注意事项

### 1. 不要手动修改

技能应该通过 `npx skills add` 安装，不要手动复制文件：

```bash
# ❌ 错误
cp -r /path/to/skill ~/.agents/skills/

# ✅ 正确
npx skills add {owner/repo@skill}
```

### 2. 虚拟环境

部分技能需要 Python 虚拟环境：

```bash
# akshare-stock 的虚拟环境
~/.agents/skills/akshare-stock/venv/

# 激活虚拟环境
source ~/.agents/skills/akshare-stock/venv/bin/activate
```

### 3. 依赖管理

每个技能的依赖在 `SKILL.md` 中声明：

```yaml
metadata:
  openclaw:
    requires:
      python_modules: ["akshare", "pandas", "numpy"]
      bins: ["python3"]
```

---

## 🔗 参考文档

- [SKILL_INSTALLATION_NORM.md](./SKILL_INSTALLATION_NORM.md) - 技能安装规范
- [DIRECTORY_STRUCTURE_GUIDE.md](./DIRECTORY_STRUCTURE_GUIDE.md) - 目录结构说明
- [ClawHub 技能市场](https://clawhub.com)

---

**维护者**: main-agent  
**最后更新**: 2026-03-13
