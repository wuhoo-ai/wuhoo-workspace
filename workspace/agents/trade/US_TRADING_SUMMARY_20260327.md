# 美股 Workflow C 交易执行报告

**日期**: 2026-03-27  
**状态**: ⚠️ 部分完成 (OpenD 服务中断)

---

## 📊 执行概览

| 步骤 | 状态 | 详情 |
|------|------|------|
| 1. 选股 | ✅ 完成 | 6 只股票 |
| 2. 分析 | ✅ 完成 | 5 只股票评分 |
| 3. 辩论 | ✅ 完成 | 快速辩论分析 |
| 4. 建议 | ✅ 完成 | 2 只 BUY 建议 |
| 5. 交易执行 | ❌ 失败 | OpenD 服务未运行 |

---

## 🎯 选股结果

**初始股票池**: 242 只美股成分股

**筛选流程**:
```
242 只
  ↓ 残差波动率 ≤ 24.33% (前 50%)
121 只
  ↓ 成交量 ≥ 15.10 (前 50%)
61 只
  ↓ 5 日动量 ≥ 1.68% (前 30%)
19 只
  ↓ Beta ≥ 0.87 (前 30%)
6 只 ← 最终选出
```

**选股结果**:

| 排名 | 代码 | 名称 | 10 日 ROC% | 残差波% | Beta |
|------|------|------|----------|---------|------|
| 1 | CSX.US | CSX Corporation | 0.84 | 19.28 | 1.38 |
| 2 | TFC.US | Truist Financial | 1.35 | 19.68 | 1.13 |
| 3 | HST.US | Host Hotels | 3.85 | 22.37 | 1.44 |
| 4 | FITB.US | Fifth Third Bancorp | 4.18 | 22.28 | 0.94 |
| 5 | MS.US | Morgan Stanley | 5.74 | 18.76 | 0.90 |
| 6 | C.US | Citigroup | 6.55 | 22.06 | 1.20 |

---

## 🐂🐻 多空辩论结果

| 代码 | 名称 | 推荐 | 置信度 | 风控 | 最终动作 |
|------|------|------|--------|------|---------|
| TFC.US | Truist Financial | BUY | 70% | ✅ APPROVE | **买入** |
| FITB.US | Fifth Third Bancorp | BUY | 70% | ⚠️ CONDITIONAL | **买入** |
| CSX.US | CSX Corporation | HOLD | 60% | ⚠️ CONDITIONAL | 观望 |
| MS.US | Morgan Stanley | HOLD | 50% | ⚠️ CONDITIONAL | 观望 |
| HST.US | Host Hotels | HOLD | 60% | ❌ REJECT | 观望 |

---

## 💼 推荐买入股票

### TFC.US - Truist Financial (首选)

| 指标 | 数值 | 评价 |
|------|------|------|
| 残差波动率 | 19.68% | ✅ 低波动 |
| 5 日动量 | +2.48% | ✅ 正向 |
| Beta | 1.13 | ✅ 适中 |
| 成交量 (log) | 16.16 | ✅ 充足 |

**辩论结果**: 2 个利好，0 个利空  
**风控审批**: ✅ APPROVE (风险评分 0.20)

### FITB.US - Fifth Third Bancorp (次选)

| 指标 | 数值 | 评价 |
|------|------|------|
| 残差波动率 | 22.28% | ⚠️ 略高 |
| 5 日动量 | +4.01% | ✅ 强势 |
| Beta | 0.94 | ✅ 稳健 |
| 成交量 (log) | 16.37 | ✅ 充足 |

**辩论结果**: 2 个利好，0 个利空  
**风控审批**: ⚠️ CONDITIONAL (波动率偏高)

---

## ❌ 交易执行失败

### 问题描述

**错误**: `ECONNREFUSED` - 无法连接到 127.0.0.1:11111

**原因**: 富途 OpenD 服务未运行

### 技术分析

1. **OpenD 进程状态**: 检测到残留进程 (PID 1605627 等)
2. **端口状态**: 11111 未监听
3. **日志文件**: 存在但为二进制格式
4. **可执行文件**: 未找到标准安装位置

### 历史交易记录

之前成功执行的交易 (2026-03-27 14:27):
```json
{
  "market": "US",
  "trade_results": [
    {
      "code": "US.AAPL",
      "name": "Apple Inc",
      "action": "BUY",
      "price": 255.42,
      "qty": 1,
      "order_id": "7548925",
      "status": "SUBMITTED"
    }
  ]
}
```

说明 OpenD 之前运行过，现在已停止。

---

## 📁 输出文件

| 文件 | 路径 | 状态 |
|------|------|------|
| 选股结果 | `data/stock-pick/factors/result_us_20260327.csv` | ✅ |
| 因子数据 | `data/stock-pick/factors/factors_us_20260327.csv` | ✅ |
| 辩论结果 | `data/stock-pick/factors/debate_quick_20260327.csv` | ✅ |
| Workflow 选股 | `trade/data/workflow_c/US_2026-03-27/01_selected_stocks.json` | ✅ |
| Workflow 分析 | `trade/data/workflow_c/US_2026-03-27/02_analysis_results.json` | ✅ |
| Workflow 辩论 | `trade/data/workflow_c/US_2026-03-27/03_debate_results.json` | ✅ |
| Workflow 建议 | `trade/data/workflow_c/US_2026-03-27/04_recommendations.json` | ✅ |
| 交易结果 | `trade/data/workflow_c/US_2026-03-27/05_trade_results.json` | ❌ (旧数据) |

---

## 🔧 恢复步骤

### 启动 OpenD 服务

1. **找到 OpenD 安装位置**:
```bash
# 可能的位置
~/futu/bin/Futu_OpenD
/opt/futu/bin/Futu_OpenD
/usr/local/bin/Futu_OpenD
```

2. **启动 GUI 版 OpenD**:
```bash
# 后台启动
nohup Futu_OpenD &

# 或手动启动图形界面
Futu_OpenD
```

3. **登录并解锁交易**:
   - 使用账号：15088682042
   - 在 GUI 界面手动解锁交易

4. **验证连接**:
```python
from futu import OpenQuoteContext
ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, data = ctx.get_global_state()
print(ret, data)
```

### 重新执行交易

OpenD 启动后运行：
```bash
cd /home/admin/.openclaw/workspace/agents/trade
source venv-futu/bin/activate
python3 workflow_c_multi_market.py --market us --date 2026-03-27
```

---

## 📋 待执行订单

| 代码 | 名称 | 数量 | 预计价格 | 预计金额 | 状态 |
|------|------|------|---------|---------|------|
| TFC.US | Truist Financial | 100 股 | ~$55 | ~$5,500 | ⏳ 等待 |
| FITB.US | Fifth Third Bancorp | 100 股 | ~$38 | ~$3,800 | ⏳ 等待 |
| **合计** | - | - | - | **~$9,300** | - |

---

## ⚠️ 风险提示

1. **数据延迟**: yfinance 数据可能有 15 分钟延迟
2. **快速辩论限制**: 使用因子分析而非完整 LLM 辩论
3. **行业集中**: 2 只都是金融股，建议分散配置
4. **模拟盘**: 当前为模拟环境，非真实资金

---

## 📝 总结

### 已完成
- ✅ 美股选股模块升级 (完整因子)
- ✅ Workflow C 整合美股流程
- ✅ 快速辩论分析
- ✅ 投资建议生成

### 未完成
- ❌ 模拟盘交易执行 (OpenD 服务中断)

### 下一步
1. 重启富途 OpenD 服务
2. 重新执行交易下单
3. 验证订单状态

---

**报告生成时间**: 2026-03-27 22:45  
**执行代理**: main-agent
