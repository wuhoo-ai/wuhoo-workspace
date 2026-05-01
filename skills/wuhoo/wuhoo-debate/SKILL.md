---
name: wuhoo-debate
description: 多空辩论分析模块。对个股进行多维度辩论分析，生成投资决策建议。
tags: ["wuhoo"]
category: wuhoo
metadata: { "hermes": { "requires": { "bins": ["python3.11"] } } }
---

# wuhoo-debate — 多空辩论分析

## 执行入口
- 单只: `python3.11 run_debate.py --symbol 600519.SH --mode full`
- 批量: `python3.11 batch_debate.py --date 20260430 --workers 4 --market all`
- 审计报告: `references/audit-20260501.md`

## 模块结构
- `agents/` — BullAgent（量化分析师）、BearAgent（风险分析师）、TraderAgent（交易决策）、RiskAgent（风控）
- `adapters/` — 数据适配器（akshare、Futu K线、RSS、TrendRadar、WebSearch、基本面）
- `prompts/` — 提示词模板（bull_analyst.md、bear_analyst.md、trader_decision.md、risk_check.md）
- `protocols/` — 辩论协议（DebateProtocol、DebateRecord）
- `rules/` — 风控规则（risk_rules.yaml）
- `batch_debate.py` — 批量辩论脚本（2026-05-01 新增）
- `references/` — 审计报告、API 配置参考

---

## API 配置（2026-05-01 更新）

### 双协议支持
BaseAgent 现支持 Anthropic（bailian）和 OpenAI（deepseek）双协议，通过 `provider` 参数或自动检测切换：

| Provider | API Base | 认证 Header | 端点路径 | 模型 |
|----------|----------|-----------|---------|------|
| anthropic | dashscope.aliyuncs.com/apps/anthropic | x-api-key | /v1/messages | qwen3.5-plus |
| openai | api.deepseek.com/v1 | Authorization: Bearer | /chat/completions | deepseek-v4-pro |

### 环境变量
```bash
# Bailian（Anthropic 兼容）
BAILIAN_API_KEY=xxx
CODING_PLAN_KEY=xxx   # 优先级高于 BAILIAN_API_KEY

# DeepSeek（OpenAI 兼容）
DEEPSEEK_API_KEY=xxx
DEEPSEEK_API_BASE=https://api.deepseek.com/v1   # 可选，默认值
```

### Agent 初始化（新签名）
```python
BullAgent(
    model="deepseek-v4-pro",
    api_base="https://api.deepseek.com/v1",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    provider="openai"  # 或 "auto" 自动检测
)
```

### DeepSeek v4-pro 注意事项
- **推理模式**: 模型内置 reasoning，即使不设 `reasoning_effort` 也会消耗 ~900-1500 reasoning tokens
- **延迟**: 简单 prompt ~16s，完整 debate prompt（~2200 chars system + 500 chars user）~53s/次
- **max_tokens**: 需要 ≥ 4000（推理 tokens 计入 completion_tokens）
- **reasoning_effort=max**: 会导致 content 为空（所有 tokens 被 reasoning 消耗），辩论系统已禁用此参数
- **输出格式**: 返回 `choices[0].message.content`（标准 OpenAI 格式），reasoning 在 `reasoning_content` 字段

---

## 🚨 已知问题与修复

### ✅ P0: Bear 趋同 — 已突破（2026-05-01）
**旧**: Bear 27/27=SELL (std=0.023)
**修复**: `prompts/bear_analyst.md` 重写为「风险分析师，可输出 BUY/SELL/HOLD」
**效果**: Bear 12/20=HOLD (60%), 4/20=SELL (20%), 4/20=BUY (20%), std=0.105 ↑4.5x
**结论**: ✅ Bear 趋同已解除

### ✅ P1: Bull 偏多 — 已突破（2026-05-01 v3）
**旧**: Bull 27/27=BUY (std=0.035)
**v2**: prompt 重写为「量化分析师，可输出 BUY/SELL/HOLD」→ Bull 19/20=BUY (95%), std=0.066
**v3 终局**: prompt 增加「反偏规则表」（高换手+横盘=派发、高残差波动率>30=高不确定性等）→ **Bull 16/27=BUY (59%), 11/27=HOLD (41%), std=0.104 ↑3x**
**结论**: ✅ Bull 趋同已解除。核心手段：场景→recommendation 映射表 + 置信度分档 + 精简 prompt 至 1700 chars

### ✅ P0: API 延迟 — 已切换到 DeepSeek（2026-05-01）
- 旧: bailian qwen3.5-plus ~70s/次
- 新: deepseek-v4-pro ~53s/次（快 25%）
- 批量: 37min → 29min（4 线程）
- 如需更快: 可考虑 deepseek-chat（v3，无 reasoning）或减少 LLM 调用轮次

### 🔴 P2: JSON 解析失败 — 已根除（2026-05-01 v3）
- v2: 成功率 20/27 (74%)；v3 终局: **27/27 (100%)**，零失败
- 修复措施:
  - `_parse_json_output` 5 步提取器
  - `_repair_truncated_json` 智能补全
  - `_call_with_retry` 全部 4 个 Agent 带 fallback 重试
  - max_tokens 提升到 6000
  - 全部 3 个 Agent × 5 处 `isinstance` 检查（抵御 points 数组字符串元素）
- 详见: `references/deepseek-api.md`

---

## 📊 批量辩论

### 脚本: `batch_debate.py`
```
python3.11 batch_debate.py --date 20260430 --workers 4 [--market cn|hk|us|all]
```

**核心设计**:
1. 跳过 DataAggregator（不拉实时数据，避免网络超时）
2. 从选股结果 CSV 直接注入因子数据（residual_vol, turnover_5d, momentum_5d, beta_20d, momentum_10d）
3. ThreadPoolExecutor 并行，默认 4 线程
4. 每只股票执行: Bull → Bear → Bull Rebuttal → Trader（4 次 LLM）
5. 完整审计日志（audit_log.json）+ 逐只 JSON（debate_{symbol}.json）+ 汇总 CSV（debate_summary.csv）

### 输出位置
```
~/wuhoo-workspace/data/debate/{date}/          ← bailian 结果
~/wuhoo-workspace/data/debate/{date}/deepseek/ ← deepseek 结果
```

### 输入格式
从 `~/wuhoo-workspace/data/stock-pick/factors/result_{market}_{date}.csv` 读取：
- A股列: ts_code, residual_vol, turnover_5d, momentum_5d, beta_20d, momentum_10d, name
- 港股列: ts_code, volatility, momentum_5d, momentum_10d, name, market
- 美股列: ts_code, residual_vol, turnover_5d, momentum_5d, beta_20d, momentum_10d, name, market

注意：港股 CSV 列名不同（volatility 而非 residual_vol，缺少 turnover_5d 和 beta_20d），脚本自动适配。

### 批量审计
- `references/audit-20260501.md` — bailian vs deepseek 全量对比（27 只，成功率 20/27 vs 27/27）
- `references/deepseek-api.md` — DeepSeek API 集成参考（协议、陷阱、响应格式）

---

## 🎨 Prompt 设计规则（反趋同）

### 核心教训：角色 Prompt 锁定输出方向

旧 Bull prompt: "你是多头分析师，寻找上涨理由" → 100% BUY  
旧 Bear prompt: "你是空头分析师，寻找下跌理由" → 100% SELL

**规则 1: Prompt 不要预设立场。** 让 Agent 基于数据做判断，而非角色要求。

**规则 2: 明确 HOLD 触发条件。** 给出具体场景 → recommendation 映射表：

| 场景 | recommendation | confidence |
|------|---------------|------------|
| 5日+10日动量双正 + 换手健康 + Beta适中 | BUY | 0.70-0.80 |
| 5日动量正 + 10日动量负（信号矛盾） | HOLD | 0.45-0.55 |
| 双动量负 + 高换手（派发） | SELL | 0.70-0.80 |
| 信号混合无明显方向 | HOLD | 0.40-0.55 |

**规则 3: 首行 JSON-only 指令。** 推理模型（deepseek-v4-pro）容易输出推理链文字而非 JSON。Prompt 首行写 `OUTPUT ONLY VALID JSON. NO OTHER TEXT. NO EXPLANATION.`

**规则 4: 精简 Prompt。** 旧 prompt ~3700 chars 触发过多推理 tokens → 延迟高 + 截断风险。新 prompt ~1700 chars（缩短 54%），保留核心规则+场景表+JSON 格式。

**规则 5: 置信度标准差异化。** 强制不同输入产生不同输出：
- 冲突信号 → 低置信 HOLD (0.40-0.55)
- 明确信号 → 高置信 BUY/SELL (0.70-0.85)
- 弱信号 → 中低置信 (0.55-0.65)
- 禁止所有输出集中在窄区间

---

## ✅ 已修复问题（历史）

### P0: RiskAgent 风控被绕过（2026-04-24）
- `workflow_c_multi_market.py` 已集成 `RiskAgent.review()`
- `trader_agent.py` RRR 计算公式已修正

### A股数据污染（2026-04-30）
- `update_all_data.py --market us` 将 yfinance 格式写入共享 daily_data/ 目录
- 17 个月 A 股 CSV 被污染（列名变为 Date,Open,High,Low,Close,Volume）
- 修复: Tushare 8 线程并行重拉，84s 恢复 ~30 万条记录
