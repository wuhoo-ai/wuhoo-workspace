# Workflow C 美股整合说明

**版本**: v2.0 - 美股完整因子集成版  
**更新日期**: 2026-03-27  
**状态**: ✅ 已测试通过

---

## 📋 更新概览

### 主要变更

1. **选股模块升级**
   - 美股使用完整因子 (残差波动率 + 成交量 + 动量 + Beta)
   - 数据源：yfinance (替代富途数据)
   - 基准指数：SPY (标普 500 ETF)

2. **分析模块优化**
   - A 股/美股：简化分析 (基于因子数据)
   - 港股：完整 DataAggregator 分析

3. **辩论模块适配**
   - A 股：简化辩论 (基于动量)
   - 美股：快速辩论分析 (基于因子，解决数据源限制)
   - 港股：完整辩论模块 (run_full_debate)

4. **投资建议生成**
   - 支持快速辩论和完整辩论两种格式
   - 统一输出格式，便于下游交易执行

---

## 🚀 使用方法

### 运行美股 Workflow C

```bash
cd /home/admin/.openclaw/workspace/agents/trade
source venv-futu/bin/activate

# 完整流程 (选股→分析→辩论→建议→交易)
python3 workflow_c_multi_market.py --market us --date 2026-03-27

# 跳过交易 (仅分析)
python3 workflow_c_multi_market.py --market us --date 2026-03-27 --skip-trades

# 指定选股数量
python3 workflow_c_multi_market.py --market us --date 2026-03-27 --top-n 20
```

### 运行其他市场

```bash
# A 股
python3 workflow_c_multi_market.py --market cn --date 2026-03-27

# 港股
python3 workflow_c_multi_market.py --market hk --date 2026-03-27
```

---

## 📊 输出文件

### 目录结构

```
trade/data/workflow_c/US_2026-03-27/
├── 01_selected_stocks.json      # 选股结果
├── 01_stock_pick_output.txt      # 选股脚本输出
├── 02_analysis_results.json      # 分析结果
├── 03_debate_results.json        # 辩论结果
├── 04_recommendations.json       # 投资建议
├── 05_trade_results.json         # 交易结果 (如执行)
└── workflow_results.json         # 完整流程汇总
```

### 文件格式示例

**01_selected_stocks.json**:
```json
{
  "success": true,
  "market": "US",
  "selected_count": 6,
  "selected_stocks": [
    {
      "ts_code": "CSX.US",
      "name": "CSX Corporation",
      "residual_vol": 19.28,
      "turnover_5d": 16.39,
      "momentum_5d": 2.75,
      "beta_20d": 1.38,
      "momentum_10d": 0.84
    }
  ]
}
```

**03_debate_results.json**:
```json
{
  "success": true,
  "method": "quick_analysis",
  "debate_results": [
    {
      "code": "CSX.US",
      "name": "CSX Corporation",
      "bull_points": ["低残差波动"],
      "bear_points": [],
      "recommendation": "BUY",
      "confidence": 0.60,
      "risk_approval": "CONDITIONAL",
      "final_action": "watch"
    }
  ]
}
```

---

## 🔄 完整流程说明

### Step 1: 选股

**调用**: `stock_pick.py --market us`

**因子**:
- 252 日残差波动率 (相对于 SPY)
- 5 日平均成交量 (log)
- 5 日价格动量 (ROC)
- 20 日 Beta (相对于 SPY)
- 10 日动量 (排序用)

**筛选逻辑**:
```
242 只成分股
  ↓ 残差波动率 ≤ 24.33% (前 50%)
121 只
  ↓ 成交量 ≥ 15.10 (前 50%)
61 只
  ↓ 5 日动量 ≥ 1.68% (前 30%)
19 只
  ↓ Beta ≥ 0.87 (前 30%)
6 只 ← 最终选出
```

**输出**: `result_us_YYYYMMDD.csv` (6 只)

---

### Step 2: 多维度分析

**方法**: 简化分析 (基于因子数据)

**评分逻辑**:
```python
score = 5.0
if residual_vol < 20: score += 1  # 低波动
if momentum_5d > 2: score += 1     # 正向动量
if 0.9 <= beta <= 1.3: score += 1  # Beta 适中
```

**输出**: 评分 1-10，推荐 BUY/HOLD

---

### Step 3: 多空辩论

**方法**: 快速辩论分析

**多方论点**:
- 低残差波动 (<20%)
- 强势动量 (>3%)
- Beta 适中 (0.9-1.3)
- 高流动性

**空方论点**:
- 波动率偏高 (>23%)
- 动量疲软 (<1.5%)
- 短期涨幅过大 (>5%)
- 高 Beta 风险 (>1.4)

**风控检查**:
- 0 个风险因素 → APPROVE
- 1 个风险因素 → CONDITIONAL
- 2+ 个风险因素 → REJECT

**输出**: 推荐 + 置信度 + 风控审批

---

### Step 4: 投资建议

**格式统一**:
```json
{
  "code": "TFC.US",
  "name": "Truist Financial",
  "action": "BUY",
  "confidence": 0.70,
  "reason": "快速辩论：BUY, 风控:APPROVE",
  "bull_points": ["低残差波动", "Beta 适中"],
  "bear_points": []
}
```

**动作映射**:
- `buy` → BUY
- `watch` → HOLD
- `reject` → HOLD

---

### Step 5: 交易执行

**支持**:
- A 股：OpenCNTradeContext (账户 18767295)
- 港股：OpenHKTradeContext (账户 18767294)
- 美股：OpenUSTradeContext (账户动态获取)

**订单类型**: 模拟盘使用 DAY 订单

---

## 📈 测试结果 (2026-03-27)

### 选股结果
| 排名 | 代码 | 名称 | 10 日 ROC% | 残差波% | Beta |
|------|------|------|----------|---------|------|
| 1 | CSX.US | CSX Corp | 0.84 | 19.28 | 1.38 |
| 2 | TFC.US | Truist Financial | 1.35 | 19.68 | 1.13 |
| 3 | HST.US | Host Hotels | 3.85 | 22.37 | 1.44 |
| 4 | FITB.US | Fifth Third | 4.18 | 22.28 | 0.94 |
| 5 | MS.US | Morgan Stanley | 5.74 | 18.76 | 0.90 |
| 6 | C.US | Citigroup | 6.55 | 22.06 | 1.20 |

### 辩论结果
| 代码 | 推荐 | 置信度 | 风控 | 最终动作 |
|------|------|--------|------|---------|
| TFC.US | ✅ BUY | 70% | APPROVE | **买入** |
| FITB.US | ✅ BUY | 70% | CONDITIONAL | **买入** |
| CSX.US | HOLD | 60% | CONDITIONAL | 观望 |
| MS.US | HOLD | 50% | CONDITIONAL | 观望 |
| HST.US | HOLD | 60% | REJECT | 观望 |

---

## ⚠️ 注意事项

### 数据源限制

1. **yfinance 依赖**: 需要网络访问，可能需要代理
2. **SPY 基准**: 如果 SPY 数据获取失败，降级为简单波动率
3. **基本面数据**: 美股基本面数据使用降级估计 (不可用于实盘)

### 辩论模块限制

1. **快速辩论**: 美股使用基于因子的快速分析，非完整 LLM 辩论
2. **数据质量**: 完整辩论模块对美股数据覆盖不足
3. **建议**: 快速辩论结果仅供参考，不建议直接用于实盘

### 交易风险

1. **模拟盘**: 当前配置为模拟盘 (FUTU_ENV=SIMULATE)
2. **实盘切换**: 需要用户确认 + 额外风控检查
3. **行业集中**: 美股选股结果金融股占比高，注意分散风险

---

## 🔧 配置文件

### 市场配置 (`workflow_c_multi_market.py`)

```python
MARKET_CONFIG = {
    'us': {
        'name': '美股 (Top 500)',
        'gateway': 'Futu OpenAPI',
        'venv': Path.home() / '.../stock-pick/venv/bin/activate',
        'stock_pick_script': Path.home() / '.../stock-pick/stock_pick.py',
    },
    # ...
}
```

### 环境变量

```bash
export FUTU_HOST=127.0.0.1
export FUTU_PORT=11111
export FUTU_ENV=SIMULATE  # 或 REAL
```

---

## 📝 待办事项

- [ ] 增加美股基本面数据源 (如 Alpha Vantage)
- [ ] 优化快速辩论算法 (增加技术指标)
- [ ] 添加行业中性化筛选
- [ ] 支持自定义因子权重
- [ ] 增加回测模块验证选股效果

---

## 📚 相关文档

- 美股因子升级：`skills/stock-pick/CHANGELOG_US.md`
- 选股脚本：`skills/stock-pick/stock_pick.py`
- 快速辩论：`data/stock-pick/debate_quick_analysis.py`
- 完整辩论：`debate/run_debate.py`

---

**整合完成时间**: 2026-03-27 20:36  
**整合执行**: main-agent  
**测试状态**: ✅ 通过
