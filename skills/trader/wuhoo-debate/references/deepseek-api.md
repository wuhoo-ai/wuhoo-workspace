# DeepSeek API 集成参考

## 双协议架构（base_agent.py）

BaseAgent 支持 `provider` 参数：`"anthropic"` / `"openai"` / `"auto"`。

`"auto"` 检测规则：
- API base 包含 `deepseek` → provider=`openai`
- API base 包含 `dashscope` 或 `anthropic` → provider=`anthropic`
- 其他 → 默认 `openai`

### Anthropic（bailian）
```python
# headers
{"x-api-key": KEY, "anthropic-version": "2023-06-01"}
# endpoint
POST {api_base}/v1/messages
# response
result["content"][0]["text"]
```

注意：bailian Anthropic 兼容接口**不支持** `{"role": "system"}` in messages。系统提示拼接到第一个 user 消息前缀 `<system>...</system>`。

### OpenAI（deepseek）
```python
# headers
{"Authorization": "Bearer KEY"}
# endpoint
POST {api_base}/chat/completions
# response
result["choices"][0]["message"]["content"]
# reasoning (deepseek v4-pro)
result["choices"][0]["message"]["reasoning_content"]
```

## deepseek-v4-pro 特性

- **推理模型**: 即使不设 `reasoning_effort`，内部仍消耗 ~900-1500 reasoning tokens
- **reasoning_effort="max"**: 会导致 `content` 为空（所有 tokens 被 reasoning 消耗），辩论系统已移除此参数
- **延迟**: 简单 prompt ~16s，完整 debate prompt（~2200 chars system + 500 chars user）~53s
- **max_tokens**: BaseAgent 自动提升到 6000（deepseek API 下）
- **输出格式**: 推理输出到 `reasoning_content`，最终答案在 `content`

## JSON 输出策略

deepseek-v4-pro 容易输出推理链文字而非 JSON。缓解措施：

1. **Prompt 首行**: `OUTPUT ONLY VALID JSON. NO OTHER TEXT. NO EXPLANATION.`
2. **精简 Prompt**: 旧版 ~3700 chars → 新版 ~1700 chars（减少推理触发）
3. **低温**: retry 时 `temperature=0.3`
4. **5 步 JSON 解析器**: 直接→```json→{…}→推理定位→截断修复
5. **Retry fallback**: 首次失败后用精简 prompt + 数据重试

### JSON 解析器步骤

```python
# 1. json.loads(text.strip())
# 2. re.search(r'```json\s*(.*?)(?:```|$)', text) → json.loads
# 3. text.find('{') → text.rfind('}') → json.loads
# 4. re.finditer(r'\{(?=[^{]*"(?:agent|recommendation|symbol)")', text) → brace-count end → json.loads
# 5. _repair_truncated_json(text[start:]) → 补全括号/字符串 → json.loads
```

### 截断修复逻辑

```python
def _repair_truncated_json(text):
    # 1. 移除末尾不完整行
    # 2. 检测未闭合括号数
    # 3. 补全 ] + }
    # 4. 移除尾部逗号
    # 5. 补全被截断的字符串引号
```

## Agent 鲁棒性

**已修复**: BullAgent、BearAgent、TraderAgent 中所有 `bullish_points` / `bearish_points` / `bull_points_refuted` 的迭代都加了 `isinstance(point, dict)` 检查。原因：LLM 有时在 points 数组中输出纯字符串而非字典。

涉及位置：
- `bull_agent.py` `_build_rebuttal_input` line 204
- `bear_agent.py` `_build_input` line 106
- `trader_agent.py` `_build_input` lines 185, 202, 208

## 环境变量

```bash
# DeepSeek
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_API_BASE=https://api.deepseek.com/v1  # 可选

# Bailian (fallback)
BAILIAN_API_KEY=xxx
CODING_PLAN_KEY=xxx   # 优先级高于 BAILIAN_API_KEY
```
