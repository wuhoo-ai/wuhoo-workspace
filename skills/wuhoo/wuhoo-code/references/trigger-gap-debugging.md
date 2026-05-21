# Trigger Gap 调试方法论

当路由类 skill（如 wuhoo-code）创建后从未被触发时，按以下流程排查。

## 问题模式

Skill 定义了触发条件（关键词表），但 Agent 从未加载该 skill 来处理匹配的任务。

## 调试步骤

### 1. 确认问题的存在

用 session_search 搜索预期的工具调用模式：

```
session_search(query="claude -p")  → 0 results
session_search(query="terminal.*claude")  → 0 results
```

### 2. 检查 skill 配置

- skill 是否在 available_skills 列表中？
- description 是否包含 Agent 能匹配到的关键词？
- 系统 prompt 的 skill 匹配逻辑是否能命中？

### 3. 分析触发链路

```
用户消息: "fix stock_pick.py..."
     ↓
Hermes 扫描 available_skills:
  ✓ 看到 wuhoo-code (description: "编码任务路由 Skill")
  ✗ description 不含 fix/bug 等关键词 → 不匹配
     ↓
Hermes: 未加载 wuhoo-code，直接用 terminal() 处理
     ↓
结果: Claude Code 路由从未触发
```

### 4. 设计修复（双重保障）

**保障 A — Description 关键词注入：**
在 skill description 中直接嵌入触发关键词，利用 Hermes 的 available_skills 扫描机制。

```
description: "... fix bug 修复 error 报错 refactor 重构 ..."
```

**保障 B — Memory 规则强制：**
写 memory 条目明确触发条件，memory 在每次 session 开始注入。

```
"用户消息含 fix/bug/修复/refactor/重构/实现 → 先 skill_view('wuhoo-code')"
```

### 5. 验证修复

1. 测试 Claude Code 可用性：`claude -p "hello" --output-format json --max-turns 1`
2. 检查 memory 规则已写入
3. 检查 skill description 已更新
4. 下次 coding 任务时观察是否触发

## 适用场景

此方法论适用于所有 **触发条件写在 skill 内容里的路由型 skill**：
- 路由 skill 依赖 Agent 先加载才能看到触发条件
- Agent 的自动加载依赖 description 关键词匹配
- 如果 description 不含关键词 → 永远不加载 → 触发条件永远看不到

## 案例

- **wuhoo-code v1.0.0**：创建后 0 次触发，description 只说"编码任务路由"不含 fix/bug/refactor
- **修复**：v1.1.0 注入关键词 + memory 规则
- **验证**：修复后实测 Claude Code 正常调用（2 turns 成功）
