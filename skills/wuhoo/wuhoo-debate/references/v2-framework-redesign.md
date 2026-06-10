# 辩论框架 v2.0 重构设计文档

> 创建日期: 2026-06-10 | 触发事件: 拓维信息 (002261) 辩论三方 SELL → 次日涨停

## 一、v1.x 终局诊断

经多次审计 (2026-05-05, 2026-06-08×2, 2026-06-09)，确认 5 个结构性缺陷无法通过 prompt 层面修复：

| # | 缺陷 | 症状 | 根因 |
|---|------|------|------|
| 1 | Bull 天花板 ≤0.65 | Trader BUY 规则(Bull≥0.70)永不触发 | Bull 被设计为"客观分析师"，无对抗义务 |
| 2 | Bear A股收敛到 SELL | 6/8审计：高残差波自动触发 SELL 7/9 | 风险规则对中证1000过拟合(残差35-38是常态) |
| 3 | Trader 系统性偏空 | BUY 极少，HOLD/SELL 主导 | Bull上限 + Bear下限 = 输入不对称 |
| 4 | 回声室效应 | 同向数据→三方共振(拓维 SELL-SELL-SELL) | 无角色被强制站对立面 |
| 5 | 无统计锚定 | 辩论纯定性推理 | 从不查询"类似因子历史胜率" |

## 二、v2.0 架构

```
Phase 0: pattern_backtest.py (统计底座，非LLM)
   └─ 500K+ 价格索引，3989 历史样本，相似度匹配
         │
         ▼ 注入所有 Agent
   ┌─────┴─────────────────────┐
   │ 📊 Quant    纯统计解读    │ → 概率分布，不给BUY/SELL
   │ 🐂 Advocate 多头辩护律师  │ → 禁止SELL，强制≥3论点
   │ 🐻 Skeptic  逐条反驳者    │ → 必须回应Bull每个论点
   └─────┬─────────────────────┘
         ▼
   🎯 Trader v2  概率+Kelly   → P_up → edge → position → BUY/SKIP/HOLD
```

## 三、角色设计对比

### Bull: 分析师 → 辩护律师

| | v1 Bull | v2 Advocate Bull |
|---|---|---|
| 角色 | 客观量化分析师 | 多头辩护律师 |
| 数据差时 | 降为 HOLD(0.50) 或 SELL | **必须找至少3个多头理由** |
| 下限 | SELL | HOLD(0.40) — 永不禁SELL |
| 论据工具 | 因子解读 | 统计反弹/动量衰竭/超卖反转/估值地板/情绪极端/催化剂 |
| conf范围 | [0.45, 0.65] | [0.40, 0.75] |

### Bear: 风险列表机 → 质疑者

| | v1 Bear | v2 Skeptic Bear |
|---|---|---|
| 输入 | 只看因子数据 | 必须先读Bull的论点 |
| 输出 | 通用风险列表 | 逐条针对性反驳 |
| 可输出BUY | 否 | **是** — Bull压倒性有效时 |
| 反驳方式 | "残差波太高" | 必须解释为什么高残差波在这个上下文不可接受 |

### Trader: 定性门槛 → 概率交易员

| | v1 Trader | v2 Trader |
|---|---|---|
| 决策依据 | Bull≥0.70→BUY(永不触发) | P_up=统计×0.6+辩论×0.4 |
| 仓位 | 固定比例 | Kelly ¼: edge × 0.25, clamp[0, 0.20] |
| SELL | 输出 SELL | 改为 **SKIP** (不持有不卖) |
| 统计锚 | 无 | Quant 占 40% 权重 |

## 四、A股特殊性

中证1000 成分股天然高波动，v2 做了特殊处理：

- 残差波 35-38 = A股中位数，不是异常
- Skeptic Bear 接收额外提示：「请基于相对偏离度而非绝对数值」
- 统计底座按市场分桶，不跨市场比较残差波

## 五、文件清单

```
wuhoo-debate/
├── scripts/pattern_backtest.py      # Phase 0: 相似度匹配统计引擎
├── prompts/advocate_bull.md         # Advocate Bull (禁SELL)
├── prompts/skeptic_bear.md          # Skeptic Bear (逐条反驳)
├── prompts/trader_v2.md             # Trader v2 (概率+Kelly)
├── prompts/quant_analyst.md         # Quant prompt (±LLM)
├── agents/quant_agent.py            # Quant Agent (非LLM)
├── agents/trader_v2_agent.py        # TraderV2Agent
├── batch_debate_v2.py               # 4-phase 批量管线
└── references/v2-framework-redesign.md  # 本文档
```

## 六、使用方式

```bash
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-debate
export $(grep -v '^#' ~/.hermes/.env | xargs)

# 批量 (推荐)
python3.11 batch_debate_v2.py --date 20260610 --market cn --workers 2

# 单只
python3.11 -c "
from agents.quant_agent import QuantAgent
from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.trader_v2_agent import TraderV2Agent
# ... 见 batch_debate_v2.py 中的 _debate_with_agents 参考
"
```

## 七、已知限制

1. **统计底座数据仅2个月** (2026-04~06) — 样本量不足以覆盖多市场状态
2. **fwd_20d 常为 null** — 需要更长的历史数据
3. **single API key contention** — 批量跑 + 主会话共用 DeepSeek key 时延迟显著增加
4. **仅支持 CN 市场** — US/HK pattern_backtest 待构建
