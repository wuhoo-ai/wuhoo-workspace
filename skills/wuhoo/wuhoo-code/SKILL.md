---
name: wuhoo-code
description: "编码任务路由 Skill — 将终端和 WeChat 中的编码任务自动路由到 Claude Code harness（DeepSeek v4-pro 后端）。覆盖 bug 修复、功能实现、重构、PR 审查、测试编写等编码场景。"
tags: ["wuhoo"]
category: wuhoo
version: 1.0.0
metadata:
  hermes:
    emoji: "🔧"
    requires:
      bins: ["claude"]
      env: ["DEEPSEEK_API_KEY"]
---

# wuhoo-code — 编码任务 Claude Code 路由

将 Hermes 中的编码任务路由到 **Claude Code harness + DeepSeek v4-pro 后端**执行。

## 为什么

Claude Code 的 agentic harness 在编码场景下优于 Hermes delegate_task：
- **Git worktree 隔离**（`-w`）防止并行开发的代码冲突
- **Hooks**（PreToolUse/PostToolUse）自动格式化、lint、安全检查
- **内置 code review**（`/review`、`/security-review`）
- **上下文可视化管理**（`/compact`、`/context`）
- **多层级子 agent**（安全审查 agent、测试 agent 并行）
- **成本不变** — 后端仍是 DeepSeek v4-pro，模型成本与 Hermes delegate_task 相同

## 触发条件

**必须路由到 Claude Code 的消息特征（任一匹配即触发）：**

| 类别 | 关键词/模式 | 示例 |
|------|-----------|------|
| Bug 修复 | `fix`、`bug`、`修复`、`修`、`报错`、`error`、`异常` | "修复 stock_pick.py 日期解析 bug" |
| 功能实现 | `add`、`implement`、`加`、`实现`、`新增`、`添加` | "给 trade.py 加个止损参数" |
| 重构 | `refactor`、`重构`、`整理`、`拆分` | "重构 diagnose.py 的循环逻辑" |
| PR/代码审查 | `review`、`审查`、`检查代码`、`PR` | "审查 wuhoo-futuapi 最近的改动" |
| 测试编写 | `test`、`测试`、`单测`、`pytest` | "给 stock-pick 写单元测试" |
| 代码分析 | `分析.*代码`、`解释.*逻辑`、`这段代码` | "分析 debate.py 的多线程逻辑" |
| 配置/依赖 | `config`、`配置`、`install`、`安装依赖`、`pip` | "给 wuhoo-trade 加个 yaml 配置项" |

**不路由到 Claude Code 的（保持 Hermes 自身处理）：**
- 交易执行（trade、下单、调仓）
- 数据查询（选股结果、持仓诊断、行情查询）
- 资讯/新闻分析
- 双色球/足球预测
- 纯对话/咨询

## 调用模板

### 标准调用（推荐）

```bash
claude -p "任务描述" \
  --output-format json \
  --max-turns 10 \
  --allowedTools "Read,Edit,Write,Bash" \
  --dangerously-skip-permissions \
  --model "deepseek-v4-pro[1m]"
```

### 参数说明

| 参数 | 值 | 说明 |
|------|---|------|
| `-p` | 必须 | Print 模式（一枪头，WeChat 只能用这个） |
| `--output-format` | `json` | 便于 Agent 解析结果 |
| `--max-turns` | 10-15 | 取决于复杂度；bug fix=5，feature=15，review=3 |
| `--allowedTools` | 按需 | bug fix: `Read,Edit,Bash`；feature: `Read,Edit,Write,Bash`；review: `Read,Bash` |
| `--dangerously-skip-permissions` | 按需 | 自动化场景用；安全敏感任务不加 |
| `--model` | `deepseek-v4-pro[1m]` | 明确指定模型 |
| `workdir` | 按项目 | wuhoo: `~/wuhoo-workspace`；hermes: `~/.hermes` |
| `timeout` | 300-600s | feature=600，bug=300，review=180 |

### max-turns 参考

| 任务类型 | max-turns | 说明 |
|---------|-----------|------|
| 简单 bug fix | 3-5 | 定位 + 修改 + 验证 |
| 中等 feature | 10-12 | 设计 + 实现 + 测试 |
| 重构 | 10-15 | 多文件改动 + 验证 |
| PR review | 3-5 | 检查 + 评论 |
| 测试编写 | 5-8 | 写测试 + 跑通 |
| 安全审查 | 5-8 | 检查 + 修复 |

## 结果处理

### JSON 输出关键字段

```json
{
  "subtype": "success",           // success 或 error_max_turns
  "result": "完整的执行结果文本",
  "num_turns": 5,
  "session_id": "bf3e636f-...",
  "total_cost_usd": 0.166,        // Anthropic 定价显示，实际 DeepSeek 成本更低
  "usage": {
    "input_tokens": 33107,
    "output_tokens": 350
  }
}
```

### WeChat/终端展示模板

成功时提取 `result` 字段展示，附加成本信息：

```
✅ Claude Code 完成 (5 turns, DeepSeek)

[result 内容摘要]

📊 33K input + 350 output tokens (~$0.17 displayed)
```

失败时（`subtype: "error_max_turns"` / `"error_budget"`）：

```
❌ Claude Code 未完成
原因：超过最大轮次限制 / 预算超限
session_id: bf3e636f-...（可用于 --resume 续接）
```

## 环境验证

调用前快速验证 Claude Code 配置：

```bash
claude auth status --text 2>&1 | grep -q "api.deepseek.com"
```

如果输出不是 DeepSeek URL，说明 `~/.claude/settings.json` 配置有问题，需修复后再调用。

### 当前配置快照

- **配置位置**：`~/.claude/settings.json` → `env` 字段
- **后端**：`https://api.deepseek.com/anthropic`
- **模型**：`deepseek-v4-pro[1m]`
- **子 agent**：`deepseek-v4-flash`
- **effort**：`max`

## 不支持的场景（fallback 到 Hermes 自身处理）

以下任务**不能**用 Claude Code，用 Hermes delegate_task 或自行处理：

1. 需要 Futu OpenAPI 连接的任务（futuapi、trade）
2. 需要 Tushare/akshare 数据的分析（数据在 Hermes venv 中）
3. 涉及 `~/.hermes/.env` 密钥的修改
4. 修改 `~/.claude/settings.json` 本身（Claude Code 无法在运行时修改自己的配置）

## Pitfalls

1. **WeChat 下只用 `-p` 模式** — tmux 交互模式对微信不可见，用户无法发送后续指令
2. **`--output-format json` 是必须的** — 否则 Agent 无法可靠解析结果
3. **workdir 要正确** — wuhoo 项目用 `~/wuhoo-workspace`，hermes 项目用 `~/.hermes`
4. **`--max-turns` 不是越大越好** — 太大可能跑飞，WeChat 30min 超时内需留余量
5. **Claude Code 无法访问 Hermes venv** — 如果任务需要 venv 中的依赖（如 akshare），在 `workdir` 中设置正确的 Python 路径
6. **成本显示是 Anthropic 定价** — `total_cost_usd` 按 Anthropic 公式计算，实际 DeepSeek 成本约为此值的 1/50
7. **Git commit 消息避免 shell 特殊字符** — `&`、`> <`、`>=` 等会被 terminal() 工具解析为 shell 重定向/后台操作。用单引号包裹 `-m '...'` 而非双引号，或转义 `\>`。提交信息中用 `->` 替代 `→`，用 `to` 替代 `>=`
