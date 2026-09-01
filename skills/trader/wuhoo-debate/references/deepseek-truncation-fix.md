# DeepSeek v4-pro JSON 截断问题 — 根因与修复

> 2026-05-05 修复记录。Bear Agent 曾是 25% 失败率的最大痛点。

## 截断模式分类

### 模式 1: 纯截断（最常见）
JSON 在数组元素字符串中间被切断，无 ```json 包裹：
```
..."key_points": ["残差波动率22.7%处于低水平，风险可控","10日动
```
- 原因: max_tokens 不足（DeepSeek 推理 tokens 计入 completion_tokens）
- 修复: max_tokens 6000→10000 + 重试升量

### 模式 2: ```json 包裹 + 截断
模型在 JSON 外包裹了 markdown 代码块，且同样被截断：
```
```json
{"recommendation":"BUY","confidence":0.68,..."key_points":["短期...
```
- 修复: `_repair_truncated_json` 先剥离 ```json 前缀

### 模式 3: 字符串中间截断
截断点在引号内的字符串值中间（如 "残差波动率17.3%虽不高但需关注不..."）：
- 修复: 重写字符串检测为逐字符扫描（处理转义引号 `\\\"`），截断时补引号

## 修复方案（三层防御）

| 层 | 位置 | 机制 |
|----|------|------|
| 1 | `base_agent.py:179` | DeepSeek 自动 bump max_tokens 到 10000 |
| 2 | `bear_agent.py:79-113` | 3次重试（10K→14K→18K），每次重新调用 LLM |
| 3 | `base_agent.py:310-370` | 截断修复：剥离包裹→补括号→补引号→去尾逗号 |

## 重试降级策略
```
尝试 0: max_tokens=10000
  ├─ 成功 → 返回结果
  └─ ValueError → 尝试 1
尝试 1: max_tokens=14000 (sleep 1s)
  ├─ 成功 → 返回结果
  └─ ValueError → 尝试 2
尝试 2: max_tokens=18000 (sleep 1s)
  ├─ 成功 → 返回结果
  └─ 全部失败 → 返回降级 HOLD (conf=0.50, key_points=[error_note])
```

## Bull Rebuttal 同样修复
`bull_agent.py:analyze_with_context` 在 2026-05-05 重跑中发现同样问题（BAC/MET Rebuttal 截断），已应用相同重试逻辑。

## 效果验证
| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| Bear 成功率 | 9/12 (75%) | 12/12 (100%) |
| 全流程成功率 | 9/12 (75%) | 10/12 (83%) |
| 残余失败 | — | 2/12 (Bull Rebuttal，已额外修复) |
