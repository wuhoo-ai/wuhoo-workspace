# 全链路自动化交易 Pipeline 设计

**版本**: v1.0  
**创建时间**: 2026-03-25  
**状态**: 🚧 设计中 → 开发中 → 测试中 → 生产

---

## 📋 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           全链路自动化交易 Pipeline                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ 因子组合挖掘  │ →  │   选股引擎   │ →  │ Debate 辩论  │ →  │ 人工确认  │ │
│  │  QuantaAlpha │    │ 中证 1000/港股│    │  多空辩论   │    │  用户审批  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └─────┬─────┘ │
│                                                                    │       │
│                                                                    ▼       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   交易执行   │ ←  │  风控检查    │ ←  │  订单生成    │ ←  │ 策略信号  │ │
│  │ VnPy+富途模拟│    │  仓位/止损   │    │  止盈止损    │    │  买入/卖出│ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘ │
│       │                                                                       │
│       ▼                                                                       │
│  ┌──────────────┐                                                            │
│  │   持仓管理   │                                                            │
│  │  监控/调仓   │                                                            │
│  └──────────────┘                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 模块详解

### 1. 因子组合挖掘 (QuantaAlpha-Deep)

**位置**: `~/.openclaw/workspace/agents/main/skills/quantaalpha-deep/`

**职责**:
- 自动挖掘 Alpha 因子
- 因子有效性检验
- 因子组合优化

**输入**:
```json
{
  "universe": "中证 1000",
  "start_date": "2024-01-01",
  "end_date": "2026-03-24",
  "target": "超额收益",
  "constraints": {
    "max_turnover": 0.3,
    "min_ic": 0.03,
    "max_correlation": 0.7
  }
}
```

**输出**:
```json
{
  "factors": [
    {
      "name": "residual_volatility_252d",
      "ic": 0.045,
      "ic_ir": 1.8,
      "turnover": 0.15,
      "direction": "negative"
    },
    {
      "name": "turnover_5d_avg",
      "ic": 0.038,
      "ic_ir": 1.5,
      "turnover": 0.22,
      "direction": "positive"
    }
  ],
  "combined_score": "weighted_sum",
  "weights": [0.6, 0.4]
}
```

**触发方式**: 
- 定时触发（每周日 22:00）
- 手动触发（用户命令）

---

### 2. 选股引擎 (Stock-Pick)

**位置**: `~/.openclaw/workspace/agents/main/skills/stock-pick/`

**职责**:
- 根据因子组合筛选股票
- 生成候选股票池
- 计算综合得分排序

**输入**:
```json
{
  "universe": "中证 1000",
  "factors": [
    {"name": "residual_volatility_252d", "condition": "<=", "threshold": "50%"},
    {"name": "turnover_5d_avg", "condition": ">=", "threshold": "50%"},
    {"name": "roc_5d", "condition": ">=", "threshold": "30%"},
    {"name": "beta_20d", "condition": ">=", "threshold": "30%"}
  ],
  "top_n": 20,
  "sort_by": "composite_score"
}
```

**输出**:
```json
{
  "date": "2026-03-25",
  "selected_stocks": [
    {
      "code": "603220.SH",
      "name": "中贝通信",
      "score": 0.85,
      "factors": {
        "residual_volatility": 35.56,
        "turnover_5d": 16.01,
        "roc_5d": -6.95,
        "beta_20d": 1.697
      },
      "rank": 1
    }
  ],
  "total_candidates": 971,
  "after_filters": 22
}
```

**触发方式**:
- 每个交易日 06:00 AM
- 接收 QuantaAlpha 的因子配置

---

### 3. Debate 多空辩论

**位置**: `~/.openclaw/workspace/agents/debate/`

**职责**:
- 对候选股票进行多空分析
- 生成看多/看空论点
- 综合评估给出建议

**输入**:
```json
{
  "stocks": [
    {"code": "603220.SH", "name": "中贝通信"},
    {"code": "000875.SZ", "name": "电投绿能"}
  ],
  "context": {
    "market_sentiment": "neutral",
    "sector": "通信设备",
    "recent_news": true
  }
}
```

**输出**:
```json
{
  "debate_results": [
    {
      "code": "603220.SH",
      "bull_case": [
        "5 日换手率 16%，市场关注度高",
        "Beta 1.7，弹性大",
        "10 日回调 17%，短期超跌"
      ],
      "bear_case": [
        "残差波动率 35%，波动较大",
        "通信板块近期表现疲软",
        "无重大利好催化"
      ],
      "recommendation": "HOLD",
      "confidence": 0.65,
      "suggested_position": 0.05
    }
  ]
}
```

**触发方式**:
- 选股完成后自动触发
- 输出给人工确认环节

---

### 4. 人工确认 (用户审批)

**位置**: WebChat / DingTalk 推送

**职责**:
- 展示选股 + 辩论结果
- 用户确认/修改/拒绝
- 记录决策原因

**输入**:
```json
{
  "recommendations": [
    {
      "code": "603220.SH",
      "action": "BUY",
      "suggested_position": 0.05,
      "debate_summary": "看多 vs 看空，信心 65%"
    }
  ],
  "deadline": "2026-03-25 15:00"
}
```

**输出**:
```json
{
  "approved": [
    {
      "code": "603220.SH",
      "action": "BUY",
      "position": 0.05,
      "user_note": "同意，但仓位降至 3%"
    }
  ],
  "rejected": [],
  "modified": [
    {
      "code": "603220.SH",
      "original_position": 0.05,
      "new_position": 0.03
    }
  ]
}
```

**推送渠道**:
- DingTalk (工作通知)
- WebChat (直接消息)

---

### 5. 交易执行 (VnPy + vnpy_futu)

**位置**: `~/.openclaw/workspace/agents/trade/skills/vnpy-futu-trader/` (新建)

**职责**:
- 连接富途 OpenD (模拟盘)
- 执行买入/卖出订单
- 设置止盈止损
- 订单状态跟踪

**输入**:
```json
{
  "orders": [
    {
      "code": "603220.SH",
      "action": "BUY",
      "position_ratio": 0.03,
      "order_type": "LIMIT",
      "limit_price": 12.50,
      "stop_loss": 11.50,
      "take_profit": 14.00,
      "valid_days": 5
    }
  ],
  "account": "SIMULATE",
  "risk_check": true
}
```

**输出**:
```json
{
  "execution_results": [
    {
      "code": "603220.SH",
      "order_id": "FT20260325001",
      "status": "FILLED",
      "filled_price": 12.48,
      "filled_qty": 300,
      "filled_time": "2026-03-25 10:35:22",
      "stop_loss_set": 11.50,
      "take_profit_set": 14.00
    }
  ],
  "total_commission": 5.00,
  "account_balance_after": 98500.00
}
```

**环境配置**:
```python
# ~/.openclaw/workspace/agents/trade/venv-futu/
Python 3.11
vnpy >= 3.9.0
vnpy_futu >= 6.3.2808.0
futu-api >= 7.1.0
```

**连接配置**:
```json
{
  "futu": {
    "host": "127.0.0.1",
    "port": 11111,
    "market": "HK",
    "trd_env": "SIMULATE",
    "password": "${FUTU_TRADE_PASSWORD}"
  }
}
```

---

### 6. 风控检查

**位置**: `~/.openclaw/workspace/agents/trade/skills/risk-manager/` (新建)

**职责**:
- 仓位检查
- 止损检查
- 流动性检查
- 黑名单检查

**输入**:
```json
{
  "order": {
    "code": "603220.SH",
    "action": "BUY",
    "position_ratio": 0.03,
    "amount": 3750
  },
  "current_position": {
    "total_value": 100000,
    "cash": 25000,
    "positions": [...]
  }
}
```

**输出**:
```json
{
  "passed": true,
  "checks": {
    "position_limit": {"passed": true, "current": 0.75, "limit": 0.90},
    "cash_available": {"passed": true, "available": 25000, "required": 3750},
    "single_stock_limit": {"passed": true, "current": 0.02, "new": 0.05, "limit": 0.20},
    "stop_loss_check": {"passed": true, "stop_loss": 11.50, "current": 12.50, "distance": 0.08},
    "blacklist_check": {"passed": true}
  },
  "warnings": [],
  "block_reason": null
}
```

---

### 7. 持仓管理

**位置**: `~/.openclaw/workspace/agents/trade/`

**职责**:
- 实时监控持仓
- 止盈止损触发
- 调仓建议
- 每日估值

**输入**:
- 实时行情 (富途 API 订阅)
- 持仓数据 (本地 JSONL)

**输出**:
- 止盈止损触发信号
- 调仓建议
- 每日持仓报告

**止盈止损逻辑**:
```python
def check_stop_loss_take_profit(position, current_price):
    if current_price <= position.stop_loss:
        return {"action": "SELL", "reason": "STOP_LOSS", "urgency": "HIGH"}
    elif current_price >= position.take_profit:
        return {"action": "SELL", "reason": "TAKE_PROFIT", "urgency": "MEDIUM"}
    elif current_price >= position.take_profit * 0.95:
        return {"action": "HOLD", "reason": "NEAR_PROFIT", "urgency": "LOW"}
    return {"action": "HOLD", "reason": "NORMAL"}
```

---

## 📡 模块间通信协议

### 数据格式标准

所有模块使用 JSON 格式通信，统一字段命名：

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string | 股票代码 (603220.SH) |
| `name` | string | 股票名称 |
| `action` | enum | BUY/SELL/HOLD |
| `position_ratio` | float | 仓位比例 (0-1) |
| `price` | float | 价格 |
| `timestamp` | string | ISO8601 时间 |

### 消息队列 (可选)

如需异步通信，可使用：
- Redis Pub/Sub
- RabbitMQ
- 本地文件队列 (`~/.openclaw/workspace/agents/trade/queue/`)

---

## 🔐 安全与审计

### 交易日志

所有交易操作记录到：
```
~/.openclaw/workspace/agents/trade/memory/trade_log/
├── 2026-03/
│   ├── 2026-03-25.jsonl
│   └── 2026-03-26.jsonl
```

日志格式：
```json
{
  "timestamp": "2026-03-25T10:35:22+08:00",
  "module": "vnpy-futu-trader",
  "action": "ORDER_PLACED",
  "data": {
    "code": "603220.SH",
    "order_id": "FT20260325001",
    "price": 12.48,
    "qty": 300
  },
  "user": "main-agent",
  "session_id": "abc123"
}
```

### 权限控制

| 操作 | 权限级别 | 说明 |
|------|----------|------|
| 选股/分析 | 只读 | 无需审批 |
| 模拟盘交易 | 低 | 自动执行 |
| 实盘交易 (<5%) | 中 | 需用户确认 |
| 实盘交易 (>5%) | 高 | 需用户二次确认 |
| 清仓/大额卖出 | 高 | 需用户确认 |

---

## 🚀 部署步骤

### 阶段一：环境搭建 (Week 1)

```bash
# 1. 创建 Python 虚拟环境
python3.11 -m venv ~/.openclaw/workspace/agents/trade/venv-futu
source ~/.openclaw/workspace/agents/trade/venv-futu/bin/activate

# 2. 安装 VnPy + 富途接口
pip install vnpy
pip install vnpy-futu

# 3. 下载并配置富途 OpenD
# 下载地址：https://www.futunn.com/OpenAPI

# 4. 配置环境变量
export FUTU_HOST=127.0.0.1
export FUTU_PORT=11111
export FUTU_PASSWORD=xxx
export FUTU_ENV=SIMULATE
```

### 阶段二：链路测试 (Week 2)

- [ ] 测试富途 OpenD 连接
- [ ] 测试行情订阅
- [ ] 测试模拟盘下单
- [ ] 测试止盈止损设置
- [ ] 测试订单状态查询

### 阶段三：集成开发 (Week 3-4)

- [ ] QuantaAlpha → Stock-Pick 对接
- [ ] Stock-Pick → Debate 对接
- [ ] Debate → 人工确认 推送
- [ ] 人工确认 → VnPy 执行
- [ ] 风控模块集成

### 阶段四：实盘准备 (Week 5+)

- [ ] 切换到实盘环境
- [ ] 小仓位测试 (10%)
- [ ] 监控告警配置
- [ ] 逐步增加仓位

---

## 📝 决策记录

### 2026-03-25: 初始设计

**决策**: 使用 VnPy + vnpy_futu 作为交易执行层

**理由**:
1. VnPy 是国内最成熟的开源量化框架
2. 已有官方富途接口
3. 支持 CTA 策略，内置止盈止损
4. 社区活跃，文档完善

**备选方案**: 
- 富途官方 SDK + 自研（放弃，重复造轮子）
- 富途 APP 条件单（放弃，无法动态调整）

**负责人**: trade-agent

---

## 🔗 相关文档

- [VnPy 文档](https://www.vnpy.com/docs/)
- [富途 OpenAPI 文档](https://openapi.futumm.com/futu-api-doc/)
- [vnpy_futu GitHub](https://github.com/veighna-global/vnpy_futu)
- [QuantaAlpha Skill](~/openclaw/workspace/agents/main/skills/quantaalpha-deep/)
- [Stock-Pick Skill](~/openclaw/workspace/agents/main/skills/stock-pick/)
