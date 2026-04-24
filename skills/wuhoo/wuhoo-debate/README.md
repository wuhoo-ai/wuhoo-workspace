# 🐂🐻 多空辩论 Agent 系统

基于 TradingAgents 思想的多 Agent 辩论交易系统。

**版本**: v0.2.0  
**状态**: ✅ 第二阶段完成 (数据集成)

## 📖 概述

本系统模拟真实交易公司的决策流程，通过多空双方辩论 + 独立风控 + 最终决策的分层架构，做出更理性的交易决策。

---

## 🚀 更新日志

### v0.2.0 (2026-03-17) - 第二阶段
- ✅ 新增数据适配器层 (QuantaAlpha/TrendRadar/AkShare)
- ✅ 新增数据聚合器统一接口
- ✅ 新增 Portfolio Manager
- ✅ 新增 AI-Trader 集成
- ✅ 新增测试套件

### v0.1.0 (2026-03-17) - 第一阶段
- ✅ 实现 Bull/Bear/Trader/Risk Agent
- ✅ 实现辩论协议
- ✅ 创建 Prompt 模板和风控规则

## 🏗️ 架构设计

```
用户接口层
    ↓
Portfolio Manager (最终审批)
    ↓
Risk Agent (独立风控)
    ↓
Trader Agent (交易决策)
    ↑
Bull Agent 🐂 ← 辩论 → Bear Agent 🐻
    ↑
分析层 (因子/技术/舆情/基本面)
```

## 👥 Agent 角色

| Agent | 角色 | 职责 |
|-------|------|------|
| **Bull Agent** 🐂 | 多头分析师 | 寻找上涨理由，给出买入建议 |
| **Bear Agent** 🐻 | 空头分析师 | 识别风险，反驳 Bull 观点 |
| **Trader Agent** 💼 | 交易决策者 | 综合多空观点，做出决策 |
| **Risk Agent** 🛡️ | 风控官 | 独立审核，确保风险可控 |
| **Portfolio Manager** | 组合经理 | 最终审批 (含用户确认) |

## 🚀 快速开始

### 安装依赖

```bash
cd /home/admin/.openclaw/workspace/agents/debate
pip install requests pyyaml
```

### 配置 API Key

```bash
export BAILIAN_API_KEY="your-api-key"
```

### 运行辩论

```bash
# 快速模式 (使用模拟数据)
python run_debate.py --symbol 600519.SH --mode quick

# 完整模式 (需要数据源集成)
python run_debate.py --symbol 600519.SH --mode full
```

## 📁 目录结构

```
debate/
├── agents/
│   ├── base_agent.py          # Agent 基类
│   ├── bull_agent.py          # 多头分析师
│   ├── bear_agent.py          # 空头分析师
│   ├── trader_agent.py        # 交易决策者
│   ├── risk_agent.py          # 风控官
│   └── portfolio_manager.py   # 投资组合经理 ✨
├── adapters/                  # 数据适配器层 ✨
│   ├── quantaalpha_adapter.py # QuantaAlpha
│   ├── trendradar_adapter.py  # TrendRadar
│   ├── akshare_adapter.py     # AkShare
│   └── data_aggregator.py     # 数据聚合
├── integrations/              # 外部集成 ✨
│   └── ai_trader_integration.py # AI-Trader
├── prompts/
│   ├── bull_analyst.md        # Bull Prompt
│   ├── bear_analyst.md        # Bear Prompt
│   ├── trader_decision.md     # Trader Prompt
│   ├── risk_check.md          # Risk Prompt
│   └── portfolio_manager.md   # PM Prompt ✨
├── protocols/
│   └── debate_protocol.py     # 辩论协议
├── rules/
│   └── risk_rules.yaml        # 风控规则
├── schemas/
│   └── debate_record.json     # 辩论记录 Schema
├── data/                      # 辩论记录存储
├── tests/                     # 测试用例 ✨
│   └── test_debate_system.py
├── run_debate.py              # 主入口
└── README.md
```

## 🔄 辩论流程

1. **Bull 分析**: 基于因子/技术/舆情/基本面数据，给出多头观点
2. **Bear 分析**: 接收 Bull 观点，进行反驳，给出空头观点
3. **辩论分析**: 提取共识点和分歧点
4. **Trader 决策**: 综合双方观点，做出交易决策
5. **Risk 审批**: 独立风控审核
6. **最终执行**: 执行/修改/拒绝/用户确认

## 📊 输出示例

```json
{
  "debate_id": "debate_20260317_154530_600519SH",
  "symbol": "600519.SH",
  "bull_view": {
    "recommendation": "BUY",
    "confidence": 0.75,
    "target_price": 1500,
    "bullish_points": [...]
  },
  "bear_view": {
    "recommendation": "SELL",
    "confidence": 0.65,
    "target_price": 1200,
    "bearish_points": [...],
    "bull_points_refuted": [...]
  },
  "trader_decision": {
    "decision": "BUY",
    "confidence": 0.60,
    "position_size": 0.10,
    "risk_reward_ratio": 2.5
  },
  "risk_approval": {
    "recommendation": "APPROVE",
    "risk_score": 0.35
  },
  "final_action": "execute"
}
```

## 🛡️ 风控规则

详见 `rules/risk_rules.yaml`:

- 单票最大仓位：20%
- 最大止损：8%
- 最低风险收益比：1:2
- 自动审批：仓位≤5% 且 风险评分≤0.4

## 🔌 数据源集成

### 已支持
- ✅ QuantaAlpha (因子数据)
- ✅ akshare (技术面)
- ✅ TrendRadar (舆情)

### 待集成
- ⏳ 财务数据 API
- ⏳ 实时行情

## 📝 下一步

### 第一阶段 (已完成) ✅
- [x] 创建项目结构
- [x] 实现 Bull/Bear/Trader/Risk Agent
- [x] 实现辩论协议
- [x] 创建 Prompt 模板
- [x] 创建风控规则

### 第二阶段 (进行中) 🚧
- [ ] 集成 QuantaAlpha 数据
- [ ] 集成 TrendRadar 数据
- [ ] 集成 akshare 数据

### 第三阶段 (计划) 📋
- [ ] 单元测试
- [ ] 集成测试
- [ ] 历史回测

## 📄 许可证

MIT License
