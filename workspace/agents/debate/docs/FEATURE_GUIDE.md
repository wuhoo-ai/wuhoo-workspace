# 功能详解指南

**版本**: v0.3.0  
**更新日期**: 2026-03-17

---

## 📖 系统概览

多空辩论 Agent 系统是一个**智能投资决策辅助系统**，通过模拟真实交易公司的决策流程，帮助投资者做出更理性的交易决策。

### 核心价值

1. **避免情绪化决策**: 多空双方充分辩论，减少认知偏差
2. **全面风险评估**: 独立风控层，量化风险指标
3. **数据驱动**: 整合多个数据源，基于事实决策
4. **可追溯**: 完整记录决策过程和理由

---

## 🏗️ 系统架构与数据流

```
┌─────────────────────────────────────────────────────────────┐
│                      输入层                                  │
│         股票代码 + 公司名称 (可选)                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      数据层                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ QuantaAlpha │ │  TrendRadar │ │   AkShare   │           │
│  │  因子数据   │ │  舆情数据   │ │  技术面数据 │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      分析层                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Bull Agent 🐂     Bear Agent 🐻              │    │
│  │         多头分析师         空头分析师                │    │
│  │         (寻找上涨理由)      (识别风险)               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      决策层                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Trader Agent                            │    │
│  │              综合多空观点，做出交易决策               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      风控层                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Risk Agent                              │    │
│  │              独立审核，量化风险                       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      审批层                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Portfolio Manager                       │    │
│  │              最终审批，用户确认                       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      输出层                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  • 辩论记录 JSON                                      │    │
│  │  • 交易决策 (BUY/SELL/HOLD)                          │    │
│  │  • 风险提示                                           │    │
│  │  • 执行结果 (可选：AI-Trader 集成)                    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📥 输入说明

### 基本输入

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `symbol` | string | ✅ | 股票代码 | `"600519.SH"` |
| `company_name` | string | ❌ | 公司名称 | `"贵州茅台"` |
| `use_real_data` | boolean | ❌ | 是否使用真实数据 | `true` |

### 命令行输入

```bash
# 基本用法
python run_debate.py --symbol 600519.SH

# 带公司名称
python run_debate.py --symbol 600519.SH --name "贵州茅台"

# 使用模拟数据 (快速测试)
python run_debate.py --symbol 600519.SH --mode quick

# 指定输出目录
python run_debate.py --symbol 600519.SH --output my_debates
```

### Python API 输入

```python
from run_debate import run_full_debate

result = run_full_debate(
    symbol="600519.SH",
    company_name="贵州茅台",
    output_dir="data",
    use_real_data=True
)
```

### 数据层输入 (自动获取)

| 数据源 | 获取内容 | 字段示例 |
|--------|---------|---------|
| **QuantaAlpha** | 因子评分 | `momentum_score`, `volatility_score` |
| **TrendRadar** | 舆情数据 | `sentiment_score`, `hot_topics` |
| **AkShare** | 技术面 | `macd`, `rsi`, `trend` |
| **内置** | 基本面 | `pe`, `roe`, `revenue_growth` |

---

## 📤 输出说明

### 1. 完整辩论记录 (JSON)

**保存位置**: `data/debate_YYYYMMDD_HHMMSS_SYMBOL.json`

```json
{
  "debate_id": "debate_20260317_140000_600519SH",
  "symbol": "600519.SH",
  "timestamp": "2026-03-17T14:00:00",
  "status": "completed",
  
  "bull_view": {
    "agent": "bull",
    "recommendation": "BUY",
    "confidence": 0.75,
    "target_price": 1500,
    "time_horizon": "1M",
    "bullish_points": [
      {
        "category": "factor",
        "point": "动量因子强势，20 日动量排名 top 10%",
        "evidence": "QuantaAlpha 因子评分 8.5/10",
        "weight": 0.35
      },
      {
        "category": "technical",
        "point": "MACD 金叉，RSI 处于健康区间",
        "evidence": "akshare 数据显示 MACD 由负转正",
        "weight": 0.30
      }
    ],
    "risks_identified": ["大盘系统性风险"],
    "stop_loss": 1350,
    "position_suggestion": 0.15
  },
  
  "bear_view": {
    "agent": "bear",
    "recommendation": "SELL",
    "confidence": 0.68,
    "target_price": 1200,
    "bearish_points": [
      {
        "category": "technical",
        "point": "RSI 接近超买区",
        "evidence": "RSI=72，接近 70 超买线",
        "weight": 0.40
      }
    ],
    "bull_points_refuted": [
      {
        "bull_point": "动量因子强势",
        "rebuttal": "动量因子已持续 2 个月，可能即将反转",
        "evidence": "历史数据显示动量因子平均持续 6-8 周"
      }
    ],
    "stop_loss": 1450
  },
  
  "consensus_points": [
    "双方都认同需要设置止损",
    "当前处于关键位置"
  ],
  
  "disagreement_points": [
    "推荐方向分歧：Bull 推荐 BUY, Bear 推荐 SELL",
    "目标价分歧较大：Bull 目标 1500, Bear 目标 1200 (差异 22.6%)"
  ],
  
  "trader_decision": {
    "agent": "trader",
    "decision": "BUY",
    "confidence": 0.60,
    "action": {
      "side": "buy",
      "quantity": 100,
      "order_type": "limit",
      "limit_price": 1380,
      "stop_loss": 1350,
      "take_profit": 1500
    },
    "reasoning": "Bull 的因子分析更有说服力，Bear 的技术面担忧有道理但已部分定价",
    "bull_weight": 0.60,
    "bear_weight": 0.40,
    "risk_reward_ratio": 2.5,
    "position_size": 0.10
  },
  
  "risk_approval": {
    "agent": "risk",
    "approved": true,
    "recommendation": "CONDITIONAL",
    "risk_score": 0.45,
    "conditions": [
      "仓位从 15% 降至 10%",
      "严格执行止损 1350"
    ],
    "warnings": [
      "近期波动率有所上升"
    ],
    "checks": {
      "stop_loss": "pass",
      "position_size": "warn",
      "risk_reward": "pass",
      "volatility": "warn",
      "liquidity": "pass"
    }
  },
  
  "portfolio_manager_approval": {
    "agent": "portfolio_manager",
    "action": "pending_user_approval",
    "reason": "大额交易 (仓位 10%)，需要用户确认",
    "requires_user_approval": true,
    "position_value": 13800
  },
  
  "final_action": {
    "action": "pending_user_approval",
    "reason": "需要用户确认大额交易"
  }
}
```

### 2. 控制台输出

```
============================================================
🎯 开始多空辩论：600519.SH
   公司：贵州茅台
============================================================

📥 加载数据...
   ✅ 因子数据：QuantaAlpha (momentum: 7.5/10)
   ✅ 技术面：akshare (MACD: golden_cross)
   ✅ 舆情：TrendRadar (sentiment: +0.4)
   ✅ 基本面：PE 25.5, ROE 15%

🐂 Bull Agent 分析中...
   推荐：BUY, 置信度：0.75

🐻 Bear Agent 分析中...
   推荐：SELL, 置信度：0.68

📊 分析辩论...
   共识点：2 个
      • 双方都认同需要设置止损
      • 双方置信度接近 (Bull: 0.75, Bear: 0.68)
   分歧点：2 个
      • 推荐方向分歧：Bull 推荐 BUY, Bear 推荐 SELL
      • 目标价分歧较大：Bull 目标 1500, Bear 目标 1200 (差异 22.6%)

💼 Trader Agent 决策中...
   决策：BUY, 仓位：10.0%

🛡️ Risk Agent 审核中...
   审批：CONDITIONAL, 风险评分：0.45

📋 Portfolio Manager 审批...
   动作：pending_user_approval
   原因：大额交易，需要用户确认

============================================================
✅ 辩论完成：debate_20260317_140000_600519SH
   最终动作：pending_user_approval
   原因：需要用户确认大额交易
============================================================
```

### 3. 用户确认请求 (需要审批时)

```json
{
  "type": "user_approval_request",
  "debate_id": "debate_20260317_140000_600519SH",
  "symbol": "600519.SH",
  "summary": {
    "bull_view": {
      "recommendation": "BUY",
      "confidence": 0.75,
      "key_points": [
        "动量因子强势 (评分 8.5/10)",
        "MACD 金叉确认买点"
      ]
    },
    "bear_view": {
      "recommendation": "SELL",
      "confidence": 0.68,
      "key_points": [
        "RSI 接近超买区",
        "动量因子可能即将反转"
      ]
    },
    "trader_decision": {
      "decision": "BUY",
      "reasoning": "Bull 的因子分析更有说服力",
      "position_size": 0.10
    },
    "risk_approval": {
      "recommendation": "CONDITIONAL",
      "risk_score": 0.45,
      "conditions": ["仓位从 15% 降至 10%"]
    }
  },
  "action_required": {
    "action": "buy",
    "quantity": 100,
    "limit_price": 1380,
    "stop_loss": 1350,
    "take_profit": 1500
  },
  "approval_url": "http://localhost:18789/approve/debate_20260317_140000_600519SH"
}
```

---

## 🎯 能够达到的效果

### 效果 1: 全面分析个股

**使用前**:
```
"这只股票看起来不错，买入吧"
```

**使用后**:
```
✅ 因子分析：动量 7.5/10，波动率 5.2/10
✅ 技术面：MACD 金叉，RSI=55 (健康)
✅ 舆情：正面 (+0.4)，热点 AI/芯片
✅ 基本面：PE 25.5, ROE 15%, 营收增长 20%

🐂 看多理由:
   1. 动量因子强势 (权重 35%)
   2. MACD 金叉确认买点 (权重 30%)
   3. 舆情正面催化 (权重 20%)
   4. 基本面稳健 (权重 15%)

🐻 看空理由:
   1. RSI 接近超买 (权重 40%)
   2. 估值偏高 vs 行业 (权重 30%)
   3. 动量可能见顶 (权重 30%)

⚖️ 综合决策：BUY (置信度 60%)
   - 仓位：10%
   - 入场：1380 限价
   - 止损：1350 (-2.2%)
   - 止盈：1500 (+8.7%)
   - 风险收益比：1:3.9

🛡️ 风险提示:
   - 仓位建议从 15% 降至 10%
   - 近期波动率上升
   - 严格执行止损
```

### 效果 2: 避免情绪化决策

**场景**: 股票连续上涨，想追高

**无系统时**:
```
"涨这么猛，赶紧追！"
→ 高位接盘，随后回调被套
```

**有系统时**:
```
🐂 Bull: "动量确实强势，但..."
🐻 Bear: "RSI=78 超买，MACD 顶背离，风险大于机会"
⚖️ Trader: "HOLD，等待回调"
🛡️ Risk: "风险评分 0.75，建议观望"

最终决策：HOLD (不追高)
→ 避免高位接盘
```

### 效果 3: 量化风险评估

**传统方式**:
```
"感觉风险有点大" (主观)
```

**系统输出**:
```
风险评分：0.45/1.00

分项检查:
✅ 止损检查：pass (止损 2.2% < 8%)
⚠️  仓位检查：warn (15% > 10% 建议值)
✅ 风险收益：pass (1:3.9 > 1:2)
⚠️  波动率：warn (近期上升)
✅ 流动性：pass (日均成交 8000 万)

建议：
- 仓位从 15% 降至 10%
- 严格执行止损 1350
```

### 效果 4: 完整决策追溯

**问题**: "为什么当时决定买入这只股票？"

**系统记录**:
```json
{
  "debate_id": "debate_20260317_140000_600519SH",
  "decision": "BUY",
  "reasoning": "Bull 的因子分析更有说服力，Bear 的技术面担忧有道理但已部分定价",
  "bull_weight": 0.60,
  "bear_weight": 0.40,
  "key_factors": [
    "动量因子评分 8.5/10",
    "MACD 金叉",
    "舆情正面 +0.4"
  ],
  "risk_considerations": [
    "RSI 接近超买",
    "波动率上升"
  ],
  "timestamp": "2026-03-17T14:00:00"
}
```

### 效果 5: 组合层面风控

**单票决策** → **组合影响**:

```
当前组合状态:
- 总资金：100,000 元
- 可用现金：50,000 元 (50%)
- 持仓数量：3 只

本次交易影响:
- 交易金额：13,800 元
- 新仓位占比：13.8%
- 交易后现金：36,200 元 (36.2%)
- 持仓数量：4 只

组合检查:
✅ 单票仓位：13.8% < 20% (通过)
✅ 行业集中度：科技 35% < 40% (通过)
✅ 现金比例：36.2% > 10% (通过)

审批结果：需要用户确认 (仓位>10%)
```

---

## 📊 实际效果对比

### 测试案例：600519.SH (贵州茅台)

| 指标 | 无系统 | 有系统 | 改善 |
|------|--------|--------|------|
| **决策时间** | ~5 分钟 (凭感觉) | ~15 秒 (自动) | 20x |
| **考虑因素** | 2-3 个 | 10+ 个 | 3x |
| **风险评估** | 主观 | 量化 (0.45/1.0) | - |
| **决策理由** | 模糊 | 清晰可追溯 | - |
| **情绪影响** | 高 | 低 | - |
| **合规性** | 无检查 | 自动风控检查 | - |

### 用户反馈 (模拟)

> "以前买股票就是看 K 线、听消息，现在系统会帮我全面分析，还能看到多空双方的辩论，决策更有底气了。"

> "最有用的是风险提示，有几次我想追高，系统提示 RSI 超买、风险收益比不佳，忍住了，后来果然回调了。"

> "辩论记录保存得很好，回头看看当时的决策理由，能学到很多东西。"

---

## 🔧 典型使用场景

### 场景 1: 日常选股分析

```bash
# 早上开盘前，分析关注的股票
python run_debate.py --symbol 600519.SH --name "贵州茅台"
python run_debate.py --symbol 000858.SZ --name "五粮液"
python run_debate.py --symbol 601318.SH --name "中国平安"

# 查看辩论结果，辅助决策
```

### 场景 2: 交易前风控检查

```python
# 准备下单前，跑一遍辩论系统
result = run_full_debate(symbol="600519.SH")

# 检查审批结果
if result["final_action"] == "reject":
    print("❌ 交易被拒绝，风险过高")
elif result["final_action"] == "pending_user_approval":
    print("⚠️  需要确认：{}".format(result["reason"]))
else:
    print("✅ 审批通过，可以执行")
```

### 场景 3: 批量回测验证

```bash
# 对历史数据进行回测
python scripts/backtest_debate.py \
  --symbol 600519.SH \
  --start 2026-01-01 \
  --end 2026-03-17 \
  --capital 100000

# 查看回测报告
cat backtest_result.json | jq '.metrics'
```

### 场景 4: 组合定期审查

```python
# 每周审查持仓
holdings = ["600519.SH", "000858.SZ", "601318.SH"]

for symbol in holdings:
    result = run_full_debate(symbol, use_real_data=True)
    
    # 如果 Trader 建议 SELL，考虑减仓
    if result["trader_decision"]["decision"] == "SELL":
        print(f"⚠️ {symbol}: 建议卖出")
```

---

## 📈 系统局限性

### 当前限制

1. **数据依赖**: 需要配置数据源 (QuantaAlpha/TrendRadar/AkShare)
2. **LLM 成本**: 每次辩论调用 3-4 次 LLM API
3. **A 股限制**: 暂不支持做空 (受限于 A 股机制)
4. **实时性**: 非实时决策，适合日线/小时线级别

### 不适用场景

- ❌ 高频交易 (系统延迟~10 秒)
- ❌ 期权/期货等衍生品
- ❌ 无数据源的小众市场

---

## 🎓 最佳实践

1. **盘前分析**: 开盘前运行辩论，制定交易计划
2. **严格执行**: 按系统建议的止损/止盈执行
3. **定期复盘**: 查看历史辩论记录，总结经验
4. **组合分散**: 不要过度集中单只股票
5. **风险优先**: Risk 拒绝的交易，慎重考虑

---

**祝你投资顺利！** 📈

_最后更新：2026-03-17_
