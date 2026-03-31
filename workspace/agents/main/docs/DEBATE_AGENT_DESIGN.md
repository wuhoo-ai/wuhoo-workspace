# 🐂🐻 多空辩论 Agent 与分层决策系统设计

**设计日期**: 2026-03-16  
**参考**: TradingAgents + 现有系统 (OpenClaw + AI-Trader + QuantaAlpha + TrendRadar)  
**目标**: 美股/A股实战交易

---

## 🎯 设计原则

1. **借鉴 TradingAgents 思想** - 多空辩论 + 分层决策
2. **保留现有优势** - A 股/因子/热点支持
3. **渐进式实现** - 不推倒重来
4. **实战导向** - 可落地、可测试、可实盘

---

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户接口层                                │
│         WebChat / Telegram / Discord / API                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      投资组合经理 (Portfolio Manager)            │
│     最终审批 | 仓位配置 | 策略权重 | 风险预算                    │
│     角色：main-agent (用户确认)                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       风险管理层 (Risk Layer)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Risk Agent (独立风控)                           │   │
│  │  止损检查 | 仓位限制 | 单笔限额 | 日亏损 | 波动率监控      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        决策层 (Decision Layer)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Trader Agent (交易决策)                       │   │
│  │     综合多空观点 | 生成交易计划 | 时机选择                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↑                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            多空辩论 (Bull vs Bear Debate)                 │   │
│  │  ┌─────────────┐         ┌─────────────┐                 │   │
│  │  │ Bull Agent 🐂│  ←辩论→  │ Bear Agent 🐻│                 │   │
│  │  │  多头分析师  │         │  空头分析师  │                 │   │
│  │  └─────────────┘         └─────────────┘                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        分析层 (Analysis Layer)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ 因子分析  │ │ 技术分析  │ │ 舆情分析  │ │ 基本面分析│          │
│  │QuantaAlpha│ │ akshare  │ │TrendRadar│ │ 财务数据  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        数据层 (Data Layer)                       │
│    A 股 (akshare/Tushare) | 美股 (yfinance/AlphaVantage)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 👥 Agent 角色定义

### 1. Bull Agent 🐂 (多头分析师)

**职责**: 寻找上涨理由，识别买入机会

**输入**:
- 因子分析结果 (QuantaAlpha)
- 技术指标 (akshare)
- 舆情数据 (TrendRadar)
- 财务数据

**输出**:
```json
{
  "agent": "bull",
  "symbol": "600519.SH",
  "timestamp": "2026-03-16T15:30:00+08:00",
  "recommendation": "BUY",
  "confidence": 0.75,
  "target_price": 1500,
  "time_horizon": "1M",
  "bullish_points": [
    {
      "category": "factor",
      "point": "动量因子强势，20 日动量排名 top 10%",
      "evidence": "QuantaAlpha 因子评分 8.5/10",
      "weight": 0.3
    },
    {
      "category": "technical",
      "point": "突破 60 日均线，MACD 金叉",
      "evidence": "akshare 技术指标",
      "weight": 0.25
    },
    {
      "category": "sentiment",
      "point": "舆情正面，热点关注度上升",
      "evidence": "TrendRadar 情绪评分 +0.6",
      "weight": 0.25
    },
    {
      "category": "fundamental",
      "point": "Q4 财报超预期，ROE 提升",
      "evidence": "财务数据",
      "weight": 0.2
    }
  ],
  "risks_identified": [
    "大盘系统性风险",
    "板块轮动可能"
  ],
  "stop_loss": 1350,
  "position_suggestion": 0.15
}
```

**Prompt 模板**:
```
你是一位专业的多头分析师 (Bull Analyst)。你的任务是：
1. 分析给定股票/市场的上涨理由
2. 识别买入机会和时机
3. 给出目标价和仓位建议
4. 同时也要识别潜在风险（保持客观）

可用数据：
- 因子分析：{factor_data}
- 技术指标：{technical_data}
- 舆情分析：{sentiment_data}
- 财务数据：{fundamental_data}

请按以下格式输出：
1. 核心观点 (1-2 句话)
2. 上涨理由 (3-5 点，按重要性排序)
3. 目标价和预期收益
4. 建议仓位
5. 止损位
6. 潜在风险

保持专业、客观，用数据支撑观点。
```

---

### 2. Bear Agent 🐻 (空头分析师)

**职责**: 识别下跌风险，提出质疑

**输入**: 同 Bull Agent

**输出**:
```json
{
  "agent": "bear",
  "symbol": "600519.SH",
  "timestamp": "2026-03-16T15:30:00+08:00",
  "recommendation": "HOLD/SELL",
  "confidence": 0.65,
  "bearish_points": [
    {
      "category": "factor",
      "point": "估值因子偏高，PE 处于历史 80% 分位",
      "evidence": "QuantaAlpha 估值评分 3/10",
      "weight": 0.35
    },
    {
      "category": "technical",
      "point": "RSI 超买 (75)，可能回调",
      "evidence": "akshare RSI 指标",
      "weight": 0.25
    },
    {
      "category": "sentiment",
      "point": "舆情过热，警惕反转",
      "evidence": "TrendRadar 热度指数 90%",
      "weight": 0.2
    },
    {
      "category": "macro",
      "point": "行业政策不确定性",
      "evidence": "新闻分析",
      "weight": 0.2
    }
  ],
  "counter_arguments": [
    "针对 Bull 的动量观点：动量可能已反映在价格中",
    "针对 Bull 的财报观点：市场预期已高，难有惊喜"
  ],
  "downside_risk": -0.15,
  "position_suggestion": 0.05
}
```

**Prompt 模板**:
```
你是一位专业的空头分析师 (Bear Analyst)。你的任务是：
1. 分析给定股票/市场的下跌风险
2. 对多头观点提出合理质疑
3. 识别被忽视的风险因素
4. 给出保守的建议

可用数据：
- 因子分析：{factor_data}
- 技术指标：{technical_data}
- 舆情分析：{sentiment_data}
- 财务数据：{fundamental_data}
- 多头观点：{bull_arguments}

请按以下格式输出：
1. 核心观点 (1-2 句话)
2. 下跌风险 (3-5 点，按重要性排序)
3. 对多头观点的反驳
4. 下行风险预估
5. 建议仓位（保守）

保持专业、客观，用数据支撑观点。
你的质疑要有建设性，不是为反而反。
```

---

### 3. Trader Agent (交易员)

**职责**: 综合多空观点，生成交易计划

**输入**:
- Bull Agent 报告
- Bear Agent 报告
- 辩论记录
- 当前仓位
- 市场状态

**输出**:
```json
{
  "agent": "trader",
  "symbol": "600519.SH",
  "timestamp": "2026-03-16T15:35:00+08:00",
  "decision": "BUY",
  "confidence": 0.70,
  "action": {
    "type": "OPEN",
    "quantity": 100,
    "expected_price": 1400,
    "order_type": "LIMIT",
    "valid_days": 3
  },
  "reasoning": {
    "bull_points_accepted": [
      "动量因子强势",
      "技术面突破"
    ],
    "bear_points_addressed": [
      "估值偏高 → 分批建仓",
      "RSI 超买 → 设置止损"
    ],
    "key_factors": [
      "多头论据更充分",
      "风险可控"
    ]
  },
  "risk_management": {
    "stop_loss": 1350,
    "take_profit": 1550,
    "position_size": 0.10,
    "max_holding_days": 20
  },
  "debate_summary": "多空辩论 2 轮，多头略占优"
}
```

**Prompt 模板**:
```
你是一位经验丰富的交易员 (Trader)。你的任务是：
1. 综合多头 (Bull) 和空头 (Bear) 的分析报告
2. 评估双方论据的质量和数据支撑
3. 做出交易决策 (BUY/SELL/HOLD)
4. 生成具体的交易计划

输入：
- 多头报告：{bull_report}
- 空头报告：{bear_report}
- 辩论记录：{debate_log}
- 当前仓位：{current_position}
- 市场状态：{market_status}

决策框架：
1. 评估双方论据的数据支撑强度
2. 识别共识点和分歧点
3. 权衡风险收益比
4. 考虑当前市场环境

输出：
1. 交易决策 (BUY/SELL/HOLD)
2. 决策理由
3. 具体交易计划 (价格/数量/类型)
4. 风险管理参数 (止损/止盈/仓位)
5. 辩论总结

保持谨慎乐观，宁可错过不要做错。
```

---

### 4. Risk Agent (风控官)

**职责**: 独立风险评估，一票否决权

**输入**:
- Trader Agent 交易计划
- 当前组合状态
- 风控规则

**输出**:
```json
{
  "agent": "risk",
  "timestamp": "2026-03-16T15:36:00+08:00",
  "trade_review": {
    "symbol": "600519.SH",
    "action": "BUY",
    "quantity": 100,
    "value": 140000
  },
  "risk_checks": {
    "single_position_limit": {
      "rule": "单仓位 <= 20%",
      "current": "15% (现有) + 10% (新增) = 25%",
      "status": "FAIL",
      "suggestion": "减少到 5%"
    },
    "stop_loss_check": {
      "rule": "止损 >= -10%",
      "proposed": "-3.6%",
      "status": "PASS"
    },
    "daily_loss_limit": {
      "rule": "日亏损 <= 5%",
      "current_today": "-1.2%",
      "potential": "-1.2% - 3.6% = -4.8%",
      "status": "PASS"
    },
    "sector_concentration": {
      "rule": "单一行业 <= 40%",
      "current": "白酒 25% + 新增 10% = 35%",
      "status": "PASS"
    },
    "liquidity_check": {
      "rule": "现金 >= 20%",
      "current": "30%",
      "status": "PASS"
    }
  },
  "decision": "CONDITIONAL_APPROVE",
  "conditions": [
    "仓位减少到 5% (50 股)"
  ],
  "veto": false,
  "veto_reason": null
}
```

**风控规则配置**:
```yaml
risk_rules:
  # 仓位限制
  single_position_max: 0.20        # 单只股票最大 20%
  sector_concentration_max: 0.40   # 单一行业最大 40%
  cash_min: 0.20                   # 最小现金 20%
  
  # 止损规则
  stop_loss_max: -0.10             # 最大止损 -10%
  trailing_stop: 0.05              # 移动止盈 5%
  
  # 亏损限制
  daily_loss_max: -0.05            # 日亏损最大 -5%
  weekly_loss_max: -0.10           # 周亏损最大 -10%
  monthly_loss_max: -0.15          # 月亏损最大 -15%
  
  # 交易限制
  max_trades_per_day: 5            # 日最大交易 5 笔
  max_turnover_per_day: 0.30       # 日最大换手 30%
  
  # 风险指标
  var_max: 0.05                    # VaR 最大 5%
  max_drawdown: -0.20              # 最大回撤 -20%
  
  # 特殊规则
  blacklist: []                    # 黑名单股票
  whitelist_only: false            # 是否仅白名单
```

---

## 🔄 决策流程

### 完整流程

```
┌─────────────────────────────────────────────────────────────────┐
│ 步骤 1: 触发分析请求                                             │
│ 触发条件：定时/信号/用户请求                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 步骤 2: 数据收集 (并行)                                          │
│ - QuantaAlpha: 因子数据                                         │
│ - akshare: 技术面数据                                           │
│ - TrendRadar: 舆情数据                                          │
│ - 财务数据：基本面数据                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 步骤 3: 多空分析 (并行)                                          │
│ ┌──────────────┐         ┌──────────────┐                       │
│ │ Bull Agent 🐂 │         │ Bear Agent 🐻 │                       │
│ │ 生成多头报告  │         │ 生成空头报告  │                       │
│ └──────────────┘         └──────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 步骤 4: 多空辩论 (1-2 轮)                                         │
│ - Bull 回应 Bear 的质疑                                         │
│ - Bear 反驳 Bull 的回应                                         │
│ - 记录辩论要点                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 步骤 5: Trader 决策                                             │
│ - 综合多空观点                                                  │
│ - 生成交易计划                                                  │
│ - 设置风控参数                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 步骤 6: Risk 审核                                               │
│ - 检查风控规则                                                  │
│ - 通过/条件通过/否决                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 步骤 7: Portfolio Manager 审批                                  │
│ - 用户确认 (实盘) / 自动执行 (模拟)                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 步骤 8: 执行交易                                                 │
│ - 模拟交易：记录到模拟账户                                       │
│ - 实盘交易：调用券商 API                                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 步骤 9: 跟踪与复盘                                               │
│ - 持仓监控                                                      │
│ - 盈亏跟踪                                                      │
│ - 决策质量评估                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 辩论流程详细

```
第 1 轮：立论
┌─────────────────────────────────────────────────────────────┐
│ Bull: 提出买入理由 (3-5 点)                                    │
│ Bear: 提出卖出/观望理由 (3-5 点)                              │
└─────────────────────────────────────────────────────────────┘
                    ↓
第 2 轮：反驳
┌─────────────────────────────────────────────────────────────┐
│ Bull: 回应 Bear 的核心质疑                                    │
│ Bear: 反驳 Bull 的核心论据                                    │
└─────────────────────────────────────────────────────────────┘
                    ↓
第 3 轮 (可选): 总结
┌─────────────────────────────────────────────────────────────┐
│ Bull: 最终陈述 (为什么还是应该买入)                          │
│ Bear: 最终陈述 (为什么还是应该谨慎)                          │
└─────────────────────────────────────────────────────────────┘
                    ↓
Trader: 综合判断
┌─────────────────────────────────────────────────────────────┐
│ - 评估双方论据质量                                           │
│ - 识别共识和分歧                                             │
│ - 做出决策                                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 数据结构设计

### 1. 分析报告结构

```python
@dataclass
class AnalysisReport:
    """多空分析报告"""
    agent: str  # "bull" or "bear"
    symbol: str
    timestamp: datetime
    recommendation: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0-1
    
    # 核心论点
    points: List[ArgumentPoint]
    
    # 价格目标
    target_price: Optional[float]
    stop_loss: Optional[float]
    upside_potential: Optional[float]
    downside_risk: Optional[float]
    
    # 仓位建议
    position_suggestion: float  # 0-1
    
    # 风险识别
    risks: List[str]
    
    # 数据支撑
    data_sources: Dict[str, Any]

@dataclass
class ArgumentPoint:
    """单个论点"""
    category: str  # "factor", "technical", "sentiment", "fundamental", "macro"
    point: str  # 论点描述
    evidence: str  # 数据支撑
    weight: float  # 重要性权重 0-1
    data: Optional[Dict]  # 原始数据
```

### 2. 辩论记录结构

```python
@dataclass
class DebateLog:
    """辩论记录"""
    symbol: str
    start_time: datetime
    end_time: datetime
    rounds: int
    
    # 各轮辩论
    round_logs: List[DebateRound]
    
    # 共识点
    consensus_points: List[str]
    
    # 分歧点
    disagreement_points: List[str]
    
    # 辩论总结
    summary: str
    winner: Optional[str]  # "bull", "bear", "tie"

@dataclass
class DebateRound:
    """单轮辩论"""
    round_num: int
    bull_argument: str
    bear_argument: str
    bull_response: Optional[str]
    bear_response: Optional[str]
```

### 3. 交易决策结构

```python
@dataclass
class TradeDecision:
    """交易决策"""
    symbol: str
    timestamp: datetime
    decision: str  # "BUY", "SELL", "HOLD"
    confidence: float
    
    # 交易详情
    action: TradeAction
    
    # 决策理由
    reasoning: DecisionReasoning
    
    # 风控参数
    risk_management: RiskParams
    
    # 辩论引用
    debate_summary: str
    bull_points_accepted: List[str]
    bear_points_addressed: List[str]

@dataclass
class TradeAction:
    """交易动作"""
    type: str  # "OPEN", "CLOSE", "ADD", "REDUCE"
    quantity: int
    expected_price: float
    order_type: str  # "MARKET", "LIMIT"
    valid_days: int

@dataclass
class RiskParams:
    """风控参数"""
    stop_loss: float
    take_profit: float
    position_size: float
    max_holding_days: int
    trailing_stop: Optional[float]
```

### 4. 风控审核结构

```python
@dataclass
class RiskReview:
    """风控审核"""
    timestamp: datetime
    trade: TradeDecision
    
    # 各项检查
    checks: Dict[str, RiskCheck]
    
    # 审核结果
    decision: str  # "APPROVE", "CONDITIONAL_APPROVE", "VETO"
    conditions: List[str]
    veto_reason: Optional[str]
    
    # 组合状态
    portfolio_status: PortfolioStatus

@dataclass
class RiskCheck:
    """单项风控检查"""
    rule: str
    current_value: Any
    limit_value: Any
    status: str  # "PASS", "FAIL", "WARNING"
    suggestion: Optional[str]
```

---

## 💻 实现方案

### 目录结构

```
~/.openclaw/workspace/agents/main/
├── agents/
│   ├── __init__.py
│   ├── bull_agent.py          # 多头 Agent
│   ├── bear_agent.py          # 空头 Agent
│   ├── trader_agent.py        # 交易员 Agent
│   └── risk_agent.py          # 风控 Agent
├── debate/
│   ├── __init__.py
│   ├── debate_manager.py      # 辩论管理
│   └── debate_templates.py    # 辩论模板
├── decision/
│   ├── __init__.py
│   ├── decision_maker.py      # 决策生成
│   └── portfolio_manager.py   # 投资组合管理
├── models/
│   ├── __init__.py
│   ├── analysis_report.py     # 数据模型
│   ├── trade_decision.py      # 交易决策
│   └── risk_review.py         # 风控审核
└── skills/
    ├── debate-analysis/       # 辩论技能
    └── trade-decision/        # 交易决策技能
```

---

### Bull Agent 实现示例

```python
# agents/bull_agent.py

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class BullReport:
    symbol: str
    timestamp: datetime
    recommendation: str
    confidence: float
    target_price: float
    bullish_points: List[Dict]
    risks_identified: List[str]
    stop_loss: float
    position_suggestion: float

class BullAgent:
    """多头分析 Agent"""
    
    def __init__(self, llm_config: Dict):
        self.llm_config = llm_config
        self.prompt_template = self._load_prompt()
    
    def analyze(
        self,
        symbol: str,
        factor_data: Dict,
        technical_data: Dict,
        sentiment_data: Dict,
        fundamental_data: Dict
    ) -> BullReport:
        """生成多头分析报告"""
        
        # 构建输入
        input_data = {
            "symbol": symbol,
            "factor_data": self._format_factor_data(factor_data),
            "technical_data": self._format_technical_data(technical_data),
            "sentiment_data": self._format_sentiment_data(sentiment_data),
            "fundamental_data": self._format_fundamental_data(fundamental_data),
        }
        
        # 调用 LLM
        response = self._call_llm(input_data)
        
        # 解析响应
        report = self._parse_response(response)
        
        return report
    
    def _load_prompt(self) -> str:
        """加载 Prompt 模板"""
        return """
你是一位专业的多头分析师 (Bull Analyst)。你的任务是：
1. 分析给定股票/市场的上涨理由
2. 识别买入机会和时机
3. 给出目标价和仓位建议
4. 同时也要识别潜在风险（保持客观）

可用数据：
- 因子分析：{factor_data}
- 技术指标：{technical_data}
- 舆情分析：{sentiment_data}
- 财务数据：{fundamental_data}

请按以下格式输出 JSON：
{{
    "recommendation": "BUY",
    "confidence": 0.75,
    "target_price": 1500,
    "bullish_points": [
        {{
            "category": "factor",
            "point": "...",
            "evidence": "...",
            "weight": 0.3
        }}
    ],
    "risks_identified": ["...", "..."],
    "stop_loss": 1350,
    "position_suggestion": 0.15
}}

保持专业、客观，用数据支撑观点。
"""
    
    def _call_llm(self, input_data: Dict) -> str:
        """调用 LLM"""
        # 使用 OpenClaw 的 LLM 调用
        from openclaw import llm
        
        prompt = self.prompt_template.format(**input_data)
        
        response = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.llm_config.get("model", "qwen3.5-plus"),
            temperature=0.7,
            max_tokens=2000
        )
        
        return response
    
    def _parse_response(self, response: str) -> BullReport:
        """解析 LLM 响应"""
        import json
        
        # 提取 JSON
        data = json.loads(response)
        
        return BullReport(
            symbol=self.symbol,
            timestamp=datetime.now(),
            recommendation=data["recommendation"],
            confidence=data["confidence"],
            target_price=data["target_price"],
            bullish_points=data["bullish_points"],
            risks_identified=data["risks_identified"],
            stop_loss=data["stop_loss"],
            position_suggestion=data["position_suggestion"]
        )
    
    def _format_factor_data(self, data: Dict) -> str:
        """格式化因子数据"""
        # 从 QuantaAlpha 获取的数据
        return f"""
        - 动量因子：{data.get('momentum', 'N/A')}
        - 估值因子：{data.get('value', 'N/A')}
        - 质量因子：{data.get('quality', 'N/A')}
        - 综合评分：{data.get('total_score', 'N/A')}/10
        """
    
    def _format_technical_data(self, data: Dict) -> str:
        """格式化技术数据"""
        # 从 akshare 获取的数据
        return f"""
        - 当前价格：{data.get('price', 'N/A')}
        - 均线：MA5={data.get('ma5', 'N/A')}, MA20={data.get('ma20', 'N/A')}
        - MACD: {data.get('macd', 'N/A')}
        - RSI: {data.get('rsi', 'N/A')}
        """
    
    def _format_sentiment_data(self, data: Dict) -> str:
        """格式化舆情数据"""
        # 从 TrendRadar 获取的数据
        return f"""
        - 情绪评分：{data.get('sentiment_score', 'N/A')}
        - 热度指数：{data.get('heat_index', 'N/A')}
        - 正面新闻：{data.get('positive_news', 0)} 条
        - 负面新闻：{data.get('negative_news', 0)} 条
        """
    
    def _format_fundamental_data(self, data: Dict) -> str:
        """格式化基本面数据"""
        return f"""
        - PE: {data.get('pe', 'N/A')}
        - PB: {data.get('pb', 'N/A')}
        - ROE: {data.get('roe', 'N/A')}
        - 营收增长：{data.get('revenue_growth', 'N/A')}
        - 净利润增长：{data.get('profit_growth', 'N/A')}
        """
```

---

### Debate Manager 实现示例

```python
# debate/debate_manager.py

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DebateSession:
    """辩论会话"""
    symbol: str
    start_time: datetime
    bull_report: Any
    bear_report: Any
    rounds: List[Dict]
    summary: str
    winner: str

class DebateManager:
    """辩论管理器"""
    
    def __init__(self, bull_agent, bear_agent, trader_agent, llm_config: Dict):
        self.bull_agent = bull_agent
        self.bear_agent = bear_agent
        self.trader_agent = trader_agent
        self.llm_config = llm_config
        self.max_rounds = 2
    
    def run_debate(
        self,
        symbol: str,
        factor_data: Dict,
        technical_data: Dict,
        sentiment_data: Dict,
        fundamental_data: Dict
    ) -> DebateSession:
        """运行多空辩论"""
        
        # 第 1 步：生成初始报告
        bull_report = self.bull_agent.analyze(
            symbol, factor_data, technical_data, sentiment_data, fundamental_data
        )
        
        bear_report = self.bear_agent.analyze(
            symbol, factor_data, technical_data, sentiment_data, fundamental_data,
            bull_arguments=bull_report.bullish_points  # 传入多头观点
        )
        
        # 第 2 步：进行辩论
        debate_rounds = []
        current_bull_args = bull_report.bullish_points
        current_bear_args = bear_report.bearish_points
        
        for round_num in range(1, self.max_rounds + 1):
            round_log = self._run_debate_round(
                round_num,
                symbol,
                current_bull_args,
                current_bear_args
            )
            debate_rounds.append(round_log)
            
            # 更新论据
            current_bull_args = round_log["bull_response"]
            current_bear_args = round_log["bear_response"]
        
        # 第 3 步：生成辩论总结
        summary = self._generate_summary(
            symbol, bull_report, bear_report, debate_rounds
        )
        
        # 第 4 步：判定获胜方
        winner = self._determine_winner(bull_report, bear_report, debate_rounds)
        
        return DebateSession(
            symbol=symbol,
            start_time=datetime.now(),
            bull_report=bull_report,
            bear_report=bear_report,
            rounds=debate_rounds,
            summary=summary,
            winner=winner
        )
    
    def _run_debate_round(
        self,
        round_num: int,
        symbol: str,
        bull_args: List[Dict],
        bear_args: List[Dict]
    ) -> Dict:
        """运行单轮辩论"""
        
        # Bull 回应
        bull_prompt = self._build_bull_response_prompt(
            round_num, symbol, bull_args, bear_args
        )
        bull_response = self._call_llm(bull_prompt, role="bull")
        
        # Bear 反驳
        bear_prompt = self._build_bear_response_prompt(
            round_num, symbol, bull_response, bear_args
        )
        bear_response = self._call_llm(bear_prompt, role="bear")
        
        return {
            "round": round_num,
            "bull_response": bull_response,
            "bear_response": bear_response,
            "timestamp": datetime.now()
        }
    
    def _generate_summary(
        self,
        symbol: str,
        bull_report: Any,
        bear_report: Any,
        debate_rounds: List[Dict]
    ) -> str:
        """生成辩论总结"""
        
        prompt = f"""
请总结以下多空辩论：

股票：{symbol}

多头核心观点：
{self._summarize_points(bull_report.bullish_points)}

空头核心观点：
{self._summarize_points(bear_report.bearish_points)}

辩论轮次：{len(debate_rounds)}

辩论记录：
{self._format_debate_log(debate_rounds)}

请总结：
1. 双方共识点
2. 核心分歧点
3. 哪方论据更有说服力
4. 最终建议
"""
        
        summary = self._call_llm(prompt, role="moderator")
        return summary
    
    def _determine_winner(
        self,
        bull_report: Any,
        bear_report: Any,
        debate_rounds: List[Dict]
    ) -> str:
        """判定获胜方"""
        
        # 简单规则：置信度 + 数据支撑
        bull_score = bull_report.confidence * 0.5 + self._count_evidence(bull_report) * 0.5
        bear_score = bear_report.confidence * 0.5 + self._count_evidence(bear_report) * 0.5
        
        if bull_score > bear_score + 0.1:
            return "bull"
        elif bear_score > bull_score + 0.1:
            return "bear"
        else:
            return "tie"
    
    def _call_llm(self, prompt: str, role: str) -> str:
        """调用 LLM"""
        from openclaw import llm
        
        response = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.llm_config.get("model", "qwen3.5-plus"),
            temperature=0.5,
            max_tokens=1500
        )
        
        return response
```

---

### 集成到 OpenClaw

```python
# skills/trade-decision/main.py

#!/usr/bin/env python3
"""
交易决策技能 - 多空辩论 + 分层决策
"""

import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_agent import TraderAgent
from agents.risk_agent import RiskAgent
from debate.debate_manager import DebateManager

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True, help="股票代码")
    parser.add_argument("--mode", default="debate", choices=["debate", "quick"])
    parser.add_argument("--data", help="数据文件路径")
    args = parser.parse_args()
    
    # 加载数据
    data = load_data(args.data) if args.data else fetch_data(args.symbol)
    
    # 初始化 Agent
    llm_config = {"model": "qwen3.5-plus"}
    bull_agent = BullAgent(llm_config)
    bear_agent = BearAgent(llm_config)
    trader_agent = TraderAgent(llm_config)
    risk_agent = RiskAgent(llm_config)
    
    # 运行辩论
    if args.mode == "debate":
        debate_manager = DebateManager(
            bull_agent, bear_agent, trader_agent, llm_config
        )
        
        session = debate_manager.run_debate(
            symbol=args.symbol,
            factor_data=data["factor"],
            technical_data=data["technical"],
            sentiment_data=data["sentiment"],
            fundamental_data=data["fundamental"]
        )
        
        # 生成交易决策
        decision = trader_agent.make_decision(
            bull_report=session.bull_report,
            bear_report=session.bear_report,
            debate_summary=session.summary
        )
        
        # 风控审核
        review = risk_agent.review(decision)
        
        # 输出结果
        output = {
            "symbol": args.symbol,
            "debate_summary": session.summary,
            "winner": session.winner,
            "decision": decision,
            "risk_review": review,
            "final_action": "APPROVED" if review.decision != "VETO" else "REJECTED"
        }
        
    else:  # quick mode
        # 快速模式：跳过辩论，直接决策
        decision = trader_agent.quick_decision(data)
        output = {"symbol": args.symbol, "decision": decision}
    
    print(json.dumps(output, indent=2, ensure_ascii=False))

def fetch_data(symbol: str) -> Dict:
    """获取数据"""
    # 调用 QuantaAlpha、akshare、TrendRadar 等
    pass

def load_data(path: str) -> Dict:
    """加载数据文件"""
    with open(path, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    main()
```

---

## 📋 配置文件

### Agent 配置

```yaml
# config/agents.yaml

bull_agent:
  model: "qwen3.5-plus"
  temperature: 0.7
  max_tokens: 2000
  system_prompt: "你是一位专业的多头分析师..."
  
bear_agent:
  model: "qwen3.5-plus"
  temperature: 0.7
  max_tokens: 2000
  system_prompt: "你是一位专业的空头分析师..."
  
trader_agent:
  model: "qwen3.5-plus"
  temperature: 0.5
  max_tokens: 2500
  system_prompt: "你是一位经验丰富的交易员..."
  
risk_agent:
  model: "qwen3.5-plus"
  temperature: 0.3
  max_tokens: 1500
  system_prompt: "你是一位严格的风控官..."
```

### 辩论配置

```yaml
# config/debate.yaml

max_rounds: 2
round_timeout: 60  # 秒

scoring:
  evidence_weight: 0.4
  logic_weight: 0.3
  data_quality_weight: 0.3
  
winner_threshold: 0.1  # 分差超过 0.1 判定获胜
```

### 风控配置

```yaml
# config/risk.yaml

rules:
  single_position_max: 0.20
  sector_concentration_max: 0.40
  cash_min: 0.20
  
  stop_loss_max: -0.10
  trailing_stop: 0.05
  
  daily_loss_max: -0.05
  weekly_loss_max: -0.10
  monthly_loss_max: -0.15
  
  max_trades_per_day: 5
  max_turnover_per_day: 0.30
  
  var_max: 0.05
  max_drawdown: -0.20

veto_conditions:
  - "single_position_limit FAIL"
  - "daily_loss_limit FAIL"
  - "blacklist_symbol"
  
conditional_conditions:
  - "sector_concentration WARNING"
  - "liquidity WARNING"
```

---

## 🧪 测试计划

### 单元测试

```python
# tests/test_bull_agent.py

def test_bull_report_generation():
    """测试多头报告生成"""
    agent = BullAgent(test_config)
    report = agent.analyze(
        symbol="600519.SH",
        factor_data=test_factor_data,
        technical_data=test_technical_data,
        sentiment_data=test_sentiment_data,
        fundamental_data=test_fundamental_data
    )
    
    assert report.recommendation in ["BUY", "HOLD"]
    assert 0 <= report.confidence <= 1
    assert len(report.bullish_points) >= 3

def test_debate_manager():
    """测试辩论管理"""
    manager = DebateManager(bull, bear, trader, config)
    session = manager.run_debate("600519.SH", test_data)
    
    assert len(session.rounds) == 2
    assert session.winner in ["bull", "bear", "tie"]
    assert session.summary is not None
```

### 回测测试

```bash
# 使用历史数据测试决策质量
python tests/backtest_debate.py \
  --start-date 2025-01-01 \
  --end-date 2025-12-31 \
  --symbols 600519.SH,000858.SZ,601318.SH \
  --mode debate
```

---

## 📊 预期效果

### 决策质量提升

| 指标 | 当前系统 | + 多空辩论 | 预期提升 |
|------|---------|-----------|---------|
| 胜率 | 55% | 60-65% | +5-10% |
| Sharpe | 1.2 | 1.5-1.8 | +25-50% |
| 最大回撤 | -20% | -15% | -25% |
| 错误决策 | 15% | 8-10% | -30-50% |

### 风险控制改善

| 风险类型 | 当前 | + 独立风控 | 改善 |
|---------|------|-----------|------|
| 超仓位 | 偶发 | 杜绝 | ✅ |
| 无止损 | 偶发 | 杜绝 | ✅ |
| 日亏损超限 | 风险 | 杜绝 | ✅ |

---

## 🎯 实施时间表

| 阶段 | 任务 | 时间 | 产出 |
|------|------|------|------|
| **Week 1** | Bull/Bear Agent 开发 | 3 天 | 可生成报告 |
| **Week 1** | Debate Manager 开发 | 2 天 | 可运行辩论 |
| **Week 2** | Trader/Risk Agent 开发 | 3 天 | 可生成决策 |
| **Week 2** | 数据集成 | 2 天 | 数据流打通 |
| **Week 3** | 回测验证 | 3 天 | 性能报告 |
| **Week 3** | 模拟交易测试 | 2 天 | 测试报告 |

---

## 💡 总结

### 核心优势

1. ✅ **借鉴 TradingAgents 思想** - 多空辩论 + 分层决策
2. ✅ **保留现有优势** - A 股/因子/热点支持
3. ✅ **独立风控** - 一票否决权
4. ✅ **可解释性** - 辩论记录可追溯

### 关键风险

1. ⚠️ **LLM 幻觉** - 需数据验证
2. ⚠️ **过度辩论** - 限制轮次
3. ⚠️ **延迟增加** - 辩论需要时间

### 下一步

1. **本周**: 实现 Bull/Bear Agent
2. **下周**: 完成辩论流程
3. **Week 3**: 回测验证

---

*设计完成时间：2026-03-16*  
*实施开始：2026-03-17*
