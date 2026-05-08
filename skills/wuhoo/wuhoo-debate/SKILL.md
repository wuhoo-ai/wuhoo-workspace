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

### ✅ P0: Bear JSON 截断 — 已根除（2026-05-05 v4）
**旧**: Bear 25% 失败率（3/12），JSON 在 `key_points` 数组中间被截断
**根因**: max_tokens 6000 不足（Bear 含 bull_points_refuted 三组数组）+ 无重试
**修复 (v4)**:
- `base_agent.py:179`: max_tokens 6000 → **10000**（DeepSeek 自动 bump）
- `bear_agent.py:79-113`: 3 次升量重试（10K→14K→18K），失败降级为 HOLD+note
- `base_agent.py:310-370`: `_repair_truncated_json` 剥离 ```json、处理转义引号、保留截断字符串行
**效果**: Bear 12/12 PASS ✅（0% 失败率）。详见 `references/deepseek-truncation-fix.md`

### ✅ P0: Bull Rebuttal JSON 截断 — 已修复（2026-05-05 v4）
**旧**: `bull_agent.py::analyze_with_context` 无重试，BAC/MET Rebuttal 阶段失败
**修复**: `bull_agent.py:173-202` 添加 3 次升量重试（同 Bear 模式）
**效果**: 后续批量辩论 Bull Rebuttal 不再静默失败

### ✅ P1: Trader 过度保守 — 已突破（2026-05-05 v4）
**旧**: Trader 2/12=BUY (17%), 7/12=HOLD (58%)，提示词 "风险第一: 不确定时选择 HOLD" 过度保守
**修复**: `prompts/trader_decision.md`:
- 替换为置信度门槛规则：Bull≥0.70+Bear<0.60→BUY，Bear≥0.70+Bull<0.60→SELL
- 新增 "弱质疑不挡强信号" 规则
- HOLD 仅用于置信度差<0.15 的真平衡
**效果**: BUY 2→**7** (↑350%), HOLD 7→2, SELL 0→1

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

### ✅ P2: JSON 解析失败 — 已根除（2026-05-05 终局）
- 旧: Bear Agent 25% 失败率（美股 12→3），原因: deepseek max_tokens=6000 不足 + 无重试 + 截断修复仅能补括号
- **三管齐下修复 (2026-05-05)**:
  1. max_tokens 6000 → **10000** (`base_agent.py:_call_openai`) — Bear 输出大三组数组不再溢出
  2. **Bear 重试机制** (`bear_agent.py:analyze`) — 3 次尝试，逐步升 max_tokens (10K→14K→18K)，失败降级为 HOLD(0.50) + error note
  3. **截断修复增强** (`base_agent.py:_repair_truncated_json`) — 处理 ```json 包裹、转义引号检测、数组内字符串截断保留
- 验证: 原失败 3 只 (ORLY/AAPL/CSCO) 全通过，Bear 输出 BUY(0.68-0.70) / HOLD(0.55)
- **额外发现**: Bull `analyze_with_context` (Rebuttal 阶段) 同样会 JSON 截断 (2026-05-05 重跑中 MET/BAC 失败)。**已同步加装重试** (`bull_agent.py:173-200`)，与 Bear 同模式: 3 次升 max_tokens 重试，失败降级 HOLD(0.50)
- 详见: `references/deepseek-api.md`

### ✅ P3: Trader 偏保守 HOLD — 已修复（2026-05-05）
- 症状: Bull 7/12=BUY(0.68-0.78) 但 Trader 仅 2/12=BUY，7/12=HOLD — "风险第一HOLD" 规则过度保守
- **修复** (`prompts/trader_decision.md`):
  - 废弃「风险第一: 不确定时HOLD」→ 改为置信度门槛: Bull≥0.70 + Bear<0.60 → BUY
  - 新增「弱质疑不挡强信号」: Bear 置信度≤0.55 的 HOLD 不应推翻 Bull 强 BUY
  - HOLD 收紧: 仅当多空置信度差<0.15 且双方证据均不足
- 预期: 合理场景下 BUY 比例从 22% 升至 40-60%

---

## 📊 批量辩论

### 脚本: `batch_debate.py`（2026-05-04 创建）
```
cd ~/wuhoo-workspace/skills/wuhoo/wuhoo-debate
source ~/.hermes/.env
python3.11 batch_debate.py --date 20260504 --workers 3 --market hk
```

**核心设计**:
1. 跳过 DataAggregator（不拉实时数据，避免网络超时 + bailian 依赖）
2. 从选股结果 CSV 直接注入因子数据（自动适配不同市场的列名、去 BOM）
3. 从 Futu OpenD 获取股票名称（`fetch_names()`，港股选股 CSV name 列为 "N/A"）
4. ThreadPoolExecutor 并行，默认 3 线程
5. 每只股票执行: Bull.analyze → Bear.analyze → Bull.analyze_with_context → simple_consensus() → Trader.make_decision（4 次 LLM）
6. 输出: 逐只 JSON（debate_{symbol}.json）+ 汇总（debate_summary.json）
7. 硬编码 DeepSeek（provider="openai", model="deepseek-v4-pro"），需 `DEEPSEEK_API_KEY`

**性能**（deepseek-v4-pro, 3 线程）:
- 港股 9 只 (2026-05-04): ~503s, ~56s/只
- 美股 12 只 (2026-05-05): ~717s, ~60s/只 — Bear JSON 截断导致部分重试，略慢于港股

### 输出位置
```
~/wuhoo-workspace/data/debate/{date}/deepseek/
├── debate_HK00005.json      # 逐只辩论结果（含 bull/bear/rebuttal/trader）
├── ...
└── debate_summary.json       # 汇总（含 statistics + results 数组）
```

### 输入格式与兼容性
从 `~/wuhoo-workspace/data/stock-pick/factors/result_{market}_{date}.csv` 读取：

| 市场 | 列名差异 | 脚本适配 |
|------|---------|---------|
| A股 | `ts_code, residual_vol, turnover_5d, momentum_5d, beta_20d, momentum_10d, name` | 自动映射 |
| 港股 | `\ufeffts_code, volatility, momentum_5d, momentum_10d, name, market` | 自动去 BOM + volatility→residual_vol |
| 美股 | `ts_code, residual_vol, turnover_5d, momentum_5d, beta_20d, momentum_10d, name, market` | 自动映射 |

### 🐛 批量辩论常见陷阱

**1. CSV BOM 头（✅ 已修复 2026-05-05）**: 选股结果 CSV 首列含 BOM (`\ufeffts_code`)，需 `open(csv_path, encoding='utf-8-sig')`。**港股+美股 CSV 均有此问题**。修复前 US 选股结果 symbol 全部为空字符串，所有结果覆盖写入 `debate_.json`。`batch_debate.py:55` 已添加 `encoding='utf-8-sig'`。

**2. 名称缺失**: 选股 CSV 中港股 `name` 列恒为 `"N/A"`。脚本通过 `fetch_names()` 从 Futu `get_market_snapshot()` 获取真实名称。

**3. Agent API 签名（关键！）**:
```python
# ✅ 正确
bull_view = bull.analyze(symbol, factor_data={}, technical_data={}, sentiment_data={}, fundamental_data={})
bear_view = bear.analyze(symbol, ..., bull_view=bull_view)          # 参数名是 bull_view
bull_rebuttal = bull.analyze_with_context(symbol, data={...}, bear_view=bear_view)  # 不同方法！
trader_decision = trader.make_decision(symbol, bull_view=..., bear_view=..., consensus_points=..., disagreement_points=...)

# ❌ 常见错误
bear.analyze(..., bull_arguments=...)   # 参数名错误
bull.analyze(..., bear_arguments=...)   # Bull 无此参数
trader.decide(...)                       # 方法不存在（是 make_decision）
trader.make_decision()['action']         # 返回字段是 'decision' 不是 'action'
```
详见 `references/batch-debate-agent-api.md`。

**4. 名称未注入导致趋同**: 如果不向 Agent 提供 `fundamental_data={"name": name}`，所有股票看起来完全一样（只有因子数值差异），导致 Agent 输出趋同。必须注入名称。

**5. DeepSeek 后端默认**: `batch_debate.py` 硬编码使用 DeepSeek（provider="openai"），不依赖 bailian。`run_debate.py` 默认使用 bailian → 需手动配置 DeepSeek 或设置 `LLM_API_BASE` 环境变量。

**6. ⚠️ 输出目录陈旧文件污染（2026-05-06 发现）**: 辩论输出目录 `data/debate/{date}/deepseek/` 按日期组织，不按选股批次。如果同一日期多次运行选股（不同因子配置或市场），旧辩论 JSON 会与新文件共存。`batch_debate.py` 会跳过已存在文件的股票（复用旧结果），但 **`debate_summary.json` 聚合目录中所有文件** — 包括前次不同选股结果。症状：
- 目录中出现不在当前选股列表中的股票（如本次 A 股选股 10 只，但目录含 300075/600037/688567 等旧文件）
- `debate_summary.json` 的 `statistics` 计数 > 当前批次股票数
- 调仓脚本可能基于错误的股票集合执行

**处置**：
```bash
# 运行辩论前清理旧文件（仅清理与当前选股不重叠的）
cd ~/wuhoo-workspace/data/debate/{date}/deepseek/
# 列出不在当前选股结果中的辩论文件
comm -13 <(cut -d, -f1 result_{market}_{date}.csv | sed 's/\./_/g' | sort) \
         <(ls debate_*_{SZ,SH,HK,US}.json | sed 's/debate_//;s/\.json//' | sort)
# 安全方式：整个目录按日期+市场隔离，重跑前删除旧汇总
rm -f debate_summary.json debate_summary.csv
```

**最佳实践**：选股结果变更后，删除旧 `debate_summary.json` 让 `batch_debate.py` 重新生成。复用个股 JSON 是安全的（因子数据按日期固定），但汇总必须反映当前批次。

**7. ⚠️ Trader 纯文本输出（非 JSON，2026-05-06 发现）**: DeepSeek v4-pro 在 Trader 阶段可能输出原生推理文本而非 JSON：
```
我们被要求基于多空辩论为股票 002077.SZ 做出交易决策。需要根据 JSON 格式输出。
首先读取双方观点：
Bull: 推荐 BUY, 置信度 0.60...
```
**区别于 JSON 截断**：`_repair_truncated_json` 只能修复不完整的 JSON 字符串，无法处理纯自然语言推理文本。此模式发生在模型忽略 prompt 首行 `OUTPUT ONLY VALID JSON` 指令时。

**影响**：`batch_debate.py:103` 调用 `trader.make_decision()` → `_parse_json_output()` 抛出 `ValueError: Failed to parse JSON from: ...` → 该股票标记为 ERROR，不参与最终决策。

**当前缓解**：
- Trader prompt 已含 `OUTPUT ONLY VALID JSON. NO OTHER TEXT.` 首行指令
- 降级策略缺失 — `_parse_json_output` 抛出后无 retry，直接失败
- 建议修复：在 `trader_agent.py:make_decision()` 中添加与 Bear/Bull 相同的 3 次升量重试机制

### 批量审计
- `references/audit-20260501.md` — bailian vs deepseek 全量对比（27 只）
- `references/deepseek-truncation-fix.md` — DeepSeek v4-pro JSON 截断根因+三层防御修复（2026-05-05）
- `references/deepseek-api.md` — DeepSeek API 集成参考
- `references/batch-debate-agent-api.md` — Agent API 正确签名速查（新建于 2026-05-04）
- `references/us-rebalance-workflow.md` — 美股端到端工作流：选股→辩论→等权调仓（2026-05-05）

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
