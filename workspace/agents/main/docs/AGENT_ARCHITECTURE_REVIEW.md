# 🏗️ OpenClaw 交易系统 Agent 架构梳理

**梳理日期**: 2026-03-16  
**目标**: 理清各 Agent 关系、定位、运行形态

---

## 📊 当前系统 vs 计划系统对比

### 当前系统 (As-Is)

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenClaw Gateway                         │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  main-agent   │    │  trade-agent  │    │  dev-agent    │
│  (通用对话)    │    │  (交易决策)    │    │  (代码开发)    │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │
        │                     ├────→ [akshare-stock] Skill
        │                     ├────→ [backtest] Skill
        │                     └────→ [TrendRadar] Skill (未集成)
        │
        └────→ [TrendRadar] Skill (独立运行，推送 DingTalk)
```

**问题**:
- ❌ TrendRadar 与 AI-Trader 隔离
- ❌ trade-agent 单层决策，无辩论
- ❌ 无独立风控
- ❌ 美股数据缺失

---

### 计划系统 (To-Be)

```
┌─────────────────────────────────────────────────────────────────┐
│                    OpenClaw Gateway                             │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  main-agent   │    │ trade-agent   │    │  dev-agent    │
│  (PM 角色)     │    │  (决策中枢)    │    │  (代码开发)    │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │
        │                     ├──────────────────────────────┐
        │                     │                              │
        ↓                     ↓                              ↓
┌──────────────────────────────────────────────────────────────────┐
│              交易决策链 (Trading Decision Chain)                  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Layer 1: 分析层 (Analysis Layer) - Skills                 │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │ │
│  │  │ 因子分析  │ │ 技术分析  │ │ 舆情分析  │ │ 基本面分析    │  │ │
│  │  │QuantaAlpha│ │ akshare  │ │TrendRadar│ │ 财务数据     │  │ │
│  │  │ [Skill]  │ │ [Skill]  │ │ [Skill]  │ │ [Skill]     │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↑                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Layer 2: 辩论层 (Debate Layer) - Sub-Agents               │ │
│  │  ┌──────────────┐         ┌──────────────┐                 │ │
│  │  │ Bull Agent 🐂│  ←辩论→  │ Bear Agent 🐻│                 │ │
│  │  │ [Sub-Agent]  │         │ [Sub-Agent]  │                 │ │
│  │  └──────────────┘         └──────────────┘                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↑                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Layer 3: 决策层 (Decision Layer) - Agent                  │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │           Trader Agent (交易员)                       │  │ │
│  │  │           [trade-agent 核心职责]                      │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↑                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Layer 4: 风控层 (Risk Layer) - Agent                      │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │           Risk Agent (风控官)                         │  │ │
│  │  │           [trade-agent 子职责 或 独立 Skill]          │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↑                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Layer 5: 审批层 (Approval Layer) - Human/Agent            │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │     Portfolio Manager (main-agent / 用户确认)         │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ↓
                    ┌─────────────────┐
                    │   执行层         │
                    │  模拟/实盘交易   │
                    └─────────────────┘
```

---

## 👥 Agent 角色清单与定位

### 1. main-agent

| 属性 | 说明 |
|------|------|
| **OpenClaw 定位** | 主 Agent (默认会话) |
| **目录** | `~/.openclaw/workspace/agents/main/` |
| **形态** | OpenClaw Agent |
| **新角色** | **Portfolio Manager (投资组合经理)** |
| **职责** | - 用户对话接口<br>- 最终交易审批<br>- 组合层面决策<br>- 策略权重配置 |
| **保留功能** | - 日常对话<br>- 信息查询<br>- TrendRadar 热点推送接收 |
| **新增功能** | - 交易决策审批<br>- 组合状态查看<br>- 风控规则配置 |

**与交易的关系**:
```
用户 → main-agent (PM 角色) → 审批交易 → 执行
```

---

### 2. trade-agent

| 属性 | 说明 |
|------|------|
| **OpenClaw 定位** | 专用 Agent (交易决策) |
| **目录** | `~/.openclaw/workspace/agents/trade/` |
| **形态** | OpenClaw Agent |
| **新角色** | **决策中枢 + 多空辩论主持人** |
| **职责** | - 调用分析层 Skills<br>- 运行多空辩论<br>- 生成交易决策<br>- 风控初审 |
| **子职责** | - Bull Agent (多头分析)<br>- Bear Agent (空头分析)<br>- Trader (交易员)<br>- Risk (风控官) |

**关键变化**:
```
当前：trade-agent → 直接决策
计划：trade-agent → 组织辩论 → 综合决策 → 风控审核 → main-agent 审批
```

**形态选择**:
- ✅ **方案 A**: trade-agent 作为"容器"，Bull/Bear 作为其内部子流程
- ⚠️ **方案 B**: Bull/Bear 作为独立 Agent (增加复杂度)

**推荐方案 A**，原因:
- 减少 Agent 数量，降低调度复杂度
- 辩论过程在 trade-agent 内部完成
- 符合 OpenClaw 的 Agent 设计哲学

---

### 3. Bull/Bear Agent (新)

| 属性 | 说明 |
|------|------|
| **OpenClaw 定位** | **trade-agent 的子流程** (非独立 Agent) |
| **形态** | **Skill 或 内部函数** |
| **目录** | `~/.openclaw/workspace/agents/main/skills/debate-analysis/` |
| **职责** | - Bull: 生成多头报告<br>- Bear: 生成空头报告 |
| **调用方式** | trade-agent 调用 Skill |
| **LLM 配置** | 可独立配置 (如使用不同 temperature) |

**为什么不是独立 Agent**:
1. 生命周期依赖 trade-agent
2. 不直接对外服务
3. 减少 OpenClaw Agent 数量
4. 辩论过程需要紧密协作

**代码形态**:
```python
# skills/debate-analysis/main.py

def analyze_bull(symbol, data) -> BullReport:
    """多头分析"""
    # 调用 LLM 生成多头报告
    pass

def analyze_bear(symbol, data, bull_report) -> BearReport:
    """空头分析"""
    # 调用 LLM 生成空头报告
    pass

def run_debate(symbol, data, rounds=2) -> DebateSession:
    """运行多空辩论"""
    bull_report = analyze_bull(symbol, data)
    bear_report = analyze_bear(symbol, data, bull_report)
    # ... 进行辩论
    return session
```

---

### 4. Trader Agent (新)

| 属性 | 说明 |
|------|------|
| **OpenClaw 定位** | **trade-agent 的核心职责** |
| **形态** | trade-agent 内部函数 |
| **职责** | - 综合多空观点<br>- 生成交易计划<br>- 设置风控参数 |

---

### 5. Risk Agent (新)

| 属性 | 说明 |
|------|------|
| **OpenClaw 定位** | **独立 Skill 或 trade-agent 子流程** |
| **形态** | Skill (推荐) |
| **目录** | `~/.openclaw/workspace/agents/main/skills/risk-check/` |
| **职责** | - 风控规则检查<br>- 一票否决<br>- 条件审批 |

**为什么推荐独立 Skill**:
1. 风控规则可配置
2. 可独立测试
3. 可被多个 Agent 调用
4. 风控逻辑复杂，值得独立

---

### 6. TrendRadar

| 属性 | 说明 |
|------|------|
| **OpenClaw 定位** | Skill |
| **目录** | `~/.agents/skills/trendradar/` |
| **当前形态** | 独立运行，推送 DingTalk |
| **计划形态** | **分析层数据源 Skill** |
| **职责变化** | - 当前：热点推送<br>- 计划：为多空辩论提供舆情数据 |

**集成方式**:
```python
# trade-agent 调用
from skills.trendradar import fetch_sentiment

sentiment_data = fetch_sentiment(symbol)
# 传给 Bull/Bear Agent 使用
```

**新增功能**:
- 情绪量化评分 (-1 到 +1)
- 个股舆情追踪 (不仅是热点)
- 交易信号生成 (可选)

---

### 7. AI-Trader

| 属性 | 说明 |
|------|------|
| **当前定位** | 独立项目 (`~/.openclaw/data/ai-trader/`) |
| **形态** | MCP 服务 + Agent |
| **计划调整** | **整合到 OpenClaw 技能体系** |
| **整合方式** | - MCP 服务保留<br>- Agent 逻辑转为 trade-agent 职责<br>- 配置整合到 OpenClaw |

**整合原因**:
1. 避免双系统维护
2. OpenClaw 已有完整 Agent 框架
3. 减少复杂度
4. 统一调度

**整合步骤**:
```
1. 保留 MCP 服务 (数学/搜索/交易/价格)
2. AI-Trader Agent 逻辑 → trade-agent Skill
3. 配置文件 → OpenClaw 配置
4. 历史数据 → 保留
```

---

## 🔄 数据流与调用关系

### 完整调用链

```
用户请求 ("分析贵州茅台")
    ↓
main-agent (PM 角色)
    ↓
调用 trade-agent (通过 OpenClaw Agent 路由)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ trade-agent 执行流程                                         │
│                                                              │
│ 1. 数据收集 (并行调用 Skills)                                │
│    ├─ quantaalpha.get_factors("600519.SH")                  │
│    ├─ akshare.get_technical("600519.SH")                    │
│    ├─ trendradar.get_sentiment("600519.SH")                 │
│    └─ financial.get_fundamentals("600519.SH")               │
│                                                              │
│ 2. 多空辩论 (内部流程)                                       │
│    ├─ Bull Agent 生成多头报告                               │
│    ├─ Bear Agent 生成空头报告                               │
│    └─ 运行 1-2 轮辩论                                         │
│                                                              │
│ 3. 交易决策                                                  │
│    └─ Trader 综合辩论结果，生成交易计划                      │
│                                                              │
│ 4. 风控审核                                                  │
│    └─ risk-check.validate(trade_plan)                       │
│                                                              │
│ 5. 返回结果到 main-agent                                     │
└─────────────────────────────────────────────────────────────┘
    ↓
main-agent 展示给用户
    ↓
用户确认 (实盘) / 自动执行 (模拟)
    ↓
执行交易
```

---

### Skill 调用关系

```
┌──────────────────────────────────────────────────────────────┐
│                     trade-agent                              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  数据层 Skills (独立，可复用)                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ quantaalpha  │  │ akshare-stock│  │ trendradar   │ │ │
│  │  │ [Skill]      │  │ [Skill]      │  │ [Skill]      │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ backtest     │  │ financial-data│ │ stock-pick   │ │ │
│  │  │ [Skill]      │  │ [Skill]      │  │ [Skill]      │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  决策层 Skills (trade-agent 专用)                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ debate-      │  │ risk-check   │  │ trade-       │ │ │
│  │  │ analysis     │  │ [Skill]      │  │ execution    │ │ │
│  │  │ [Skill]      │  │              │  │ [Skill]      │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 OpenClaw 目录结构

### 推荐结构

```
~/.openclaw/
├── openclaw.json                    # 主配置
├── agents/
│   ├── main/                        # main-agent (PM 角色)
│   │   ├── SOUL.md
│   │   ├── USER.md
│   │   ├── TOOLS.md
│   │   └── skills/                  # main-agent 专用 Skills
│   │       ├── debate-analysis/     # 多空辩论
│   │       ├── risk-check/          # 风控检查
│   │       └── trade-decision/      # 交易决策
│   │
│   ├── trade/                       # trade-agent (决策中枢)
│   │   ├── config.json
│   │   └── skills/                  # trade-agent 专用 Skills
│   │       └── ...
│   │
│   └── dev/                         # dev-agent (代码开发)
│       └── ...
│
├── workspace/
│   └── agents/
│       └── main/
│           ├── skills/              # 共享 Skills
│           │   ├── quantaalpha-deep/
│           │   ├── akshare-stock/
│           │   ├── trendradar/
│           │   ├── backtest/
│           │   ├── stock-pick/
│           │   ├── debate-analysis/     # 新
│           │   ├── risk-check/          # 新
│           │   └── trade-execution/     # 新
│           │
│           └── docs/
│               ├── DEBATE_AGENT_DESIGN.md
│               ├── REALISTIC_TRADING_ROADMAP.md
│               └── ...
│
├── data/
│   ├── ai-trader/                   # AI-Trader 数据 (保留)
│   │   ├── configs/
│   │   ├── data/
│   │   ├── logs/
│   │   └── ...
│   │
│   └── trendradar/                  # TrendRadar 数据
│       └── output/
│
└── logs/
    ├── commands.log
    └── openclaw-*.log
```

---

## 🎯 Agent 定位总结表

| Agent/Skill | OpenClaw 形态 | 目录 | 职责 | 是否独立 |
|-------------|--------------|------|------|---------|
| **main-agent** | Agent | `workspace/agents/main/` | PM 角色、用户接口、最终审批 | ✅ 独立 |
| **trade-agent** | Agent | `workspace/agents/trade/` | 决策中枢、组织辩论 | ✅ 独立 |
| **Bull Agent** | Skill (内部流程) | `skills/debate-analysis/` | 多头分析 | ❌ 依赖 trade-agent |
| **Bear Agent** | Skill (内部流程) | `skills/debate-analysis/` | 空头分析 | ❌ 依赖 trade-agent |
| **Trader** | trade-agent 职责 | - | 综合决策 | ❌ trade-agent 核心 |
| **Risk Agent** | Skill | `skills/risk-check/` | 风控审核 | ✅ 独立 Skill |
| **TrendRadar** | Skill | `skills/trendradar/` | 舆情数据源 | ✅ 独立 Skill |
| **AI-Trader** | 整合到 trade-agent | `data/ai-trader/` (数据保留) | 交易逻辑整合 | ⚠️ 整合 |
| **QuantaAlpha** | Skill | `skills/quantaalpha-deep/` | 因子挖掘 | ✅ 独立 Skill |
| **akshare** | Skill | `skills/akshare-stock/` | A 股数据 | ✅ 独立 Skill |

---

## 🔧 OpenClaw 配置

### agents.main 配置

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "workspace": "/home/admin/.openclaw/workspace/agents/main",
        "model": {
          "primary": "bailian/qwen3.5-plus",
          "fallbacks": ["bailian/MiniMax-M2.5"]
        },
        "tools": {
          "allow": [
            "read", "edit", "write", "exec",
            "web_search", "web_fetch",
            "file-search", "glob", "grep",
            "memory_get", "memory_write",
            "message",
            // 交易相关 Skills
            "quantaalpha",
            "akshare-stock",
            "trendradar",
            "backtest",
            "stock-pick",
            "debate-analysis",    // 新
            "risk-check",          // 新
            "trade-execution"      // 新
          ],
          "exec": {
            "node": "local"
          }
        },
        "role": "portfolio-manager"  // 新：PM 角色
      },
      {
        "id": "trade",
        "workspace": "/home/admin/.openclaw/workspace/agents/trade",
        "model": "bailian/qwen3.5-plus",
        "tools": {
          "allow": [
            "read", "edit", "write", "exec",
            "quantaalpha",
            "akshare-stock",
            "trendradar",
            "debate-analysis",
            "risk-check",
            "trade-execution"
          ],
          "exec": {
            "node": "local"
          }
        },
        "role": "trader"  // 新：交易员角色
      }
    ]
  }
}
```

---

## 🚀 运行方式

### 1. 用户发起交易分析

```bash
# WebChat / Telegram / Discord
用户："分析一下贵州茅台 600519"

# OpenClaw 路由
→ main-agent (PM 角色)
  → 识别交易相关请求
  → 调用 trade-agent

# trade-agent 执行
→ 调用数据层 Skills
→ 运行多空辩论
→ 生成交易决策
→ 风控审核
→ 返回 main-agent

# main-agent 展示
→ 格式化输出
→ 等待用户确认
```

### 2. 定时分析 (Heartbeat)

```bash
# HEARTBEAT.md 配置
0 9 * * *  # 每日 9 点

# 执行
→ trade-agent (自动运行)
  → 分析持仓股票
  → 多空辩论
  → 风控检查
  → 生成日报
  → 推送 DingTalk
```

### 3. TrendRadar 热点触发

```bash
# TrendRadar 推送
→ DingTalk 收到热点

# main-agent 处理
→ 识别交易相关热点
→ 调用 trade-agent 分析
→ 生成交易信号 (可选)
```

---

## 📊 与 TradingAgents 对比

| 维度 | TradingAgents | 我们的设计 |
|------|---------------|-----------|
| **架构** | 多独立 Agent | Agent + Skill 混合 |
| **Bull/Bear** | 独立 Agent | trade-agent 内部 Skill |
| **Trader** | 独立 Agent | trade-agent 核心职责 |
| **Risk** | 独立团队 | 独立 Skill |
| **PM** | 无 (自动执行) | main-agent + 用户确认 |
| **数据源** | Yahoo Finance | akshare/Tushare/TrendRadar |
| **市场** | 美股 | A 股 + 美股 |
| **部署** | 独立 Python 项目 | OpenClaw 技能系统 |

**我们的优势**:
1. ✅ 更轻量 (减少 Agent 数量)
2. ✅ 更灵活 (Skill 可复用)
3. ✅ 用户确认 (实盘更安全)
4. ✅ A 股支持
5. ✅ 热点舆情

---

## 💡 关键决策点

### 决策 1: Bull/Bear 作为独立 Agent 还是 Skill?

**选择**: Skill (trade-agent 内部流程)

**理由**:
- 生命周期依赖 trade-agent
- 减少 OpenClaw Agent 数量
- 辩论需要紧密协作
- 降低调度复杂度

---

### 决策 2: AI-Trader 整合还是保留?

**选择**: 整合到 trade-agent

**理由**:
- 避免双系统维护
- OpenClaw 已有完整框架
- 统一调度更简单
- 数据保留，逻辑整合

---

### 决策 3: Risk Agent 独立还是内置?

**选择**: 独立 Skill

**理由**:
- 风控规则可配置
- 可独立测试
- 可被多个 Agent 调用
- 风控逻辑复杂

---

### 决策 4: TrendRadar 如何集成?

**选择**: 保持独立 Skill，增加数据接口

**理由**:
- 已有完整功能
- 只需增加情绪量化接口
- 可被 trade-agent 调用

---

## 🎯 实施优先级

### Phase 1 (本周) - 基础框架

```bash
1. 创建 skills/debate-analysis/
   - bull_agent.py
   - bear_agent.py
   - debate_manager.py

2. 创建 skills/risk-check/
   - risk_rules.yaml
   - risk_checker.py

3. 修改 trade-agent 配置
   - 添加新 Skills
   - 定义调用流程
```

---

### Phase 2 (下周) - 数据集成

```bash
4. TrendRadar 情绪量化接口
   - get_sentiment(symbol)
   - 情绪评分 (-1 到 +1)

5. QuantaAlpha 数据接口
   - get_factors(symbol)
   - 因子评分

6. akshare 技术数据
   - get_technical(symbol)
   - 技术指标
```

---

### Phase 3 (Week 3) - 回测验证

```bash
7. 历史数据回测
   - 辩论决策质量
   - 与单层决策对比

8. 模拟交易测试
   - 实盘流程演练
   - 风控规则验证
```

---

## 📋 总结

### Agent 定位一句话总结

| 角色 | 定位 | 形态 |
|------|------|------|
| **main-agent** | Portfolio Manager (最终审批) | OpenClaw Agent |
| **trade-agent** | 决策中枢 (组织辩论) | OpenClaw Agent |
| **Bull/Bear** | 多空分析师 | trade-agent 内部 Skill |
| **Trader** | 交易员 | trade-agent 核心职责 |
| **Risk** | 风控官 | 独立 Skill |
| **TrendRadar** | 舆情数据源 | 独立 Skill |
| **QuantaAlpha** | 因子数据源 | 独立 Skill |

---

### 核心设计原则

1. ✅ **减少 Agent 数量** - Bull/Bear 作为 Skill
2. ✅ **Skill 可复用** - 数据层 Skills 独立
3. ✅ **用户确认** - main-agent 最终审批
4. ✅ **渐进式改进** - 保留现有系统
5. ✅ **实战导向** - 可落地、可测试

---

*梳理完成时间：2026-03-16 15:45*
