# OpenClaw 调用链路追踪方案

## 🎯 目标
显性获取每一次任务下发和执行过程中的调用链路，包括：
- 使用了哪些 Skill
- 调用了哪些 API（付费/免费额度）
- 执行时间和结果

---

## 📋 现有能力

### 1. Gateway 日志
**位置**: `/tmp/openclaw/openclaw-YYYY-MM-DD.log`
**查看方式**:
```bash
# 实时跟踪
openclaw logs --follow --json

# 查看最近 100 条
openclaw logs --limit 100 --json
```

**包含内容**:
- ✅ 工具调用 (exec, read, write, web_search 等)
- ✅ 错误信息
- ✅ 执行结果
- ❌ 技能名称映射
- ❌ API 成本统计

---

### 2. Command Logger Hook
**启用**:
```bash
openclaw hooks enable command-logger
```

**位置**: `~/.openclaw/logs/commands.log`

**包含内容**:
- ✅ 命令类型 (/new, /reset, 等)
- ✅ 时间戳
- ✅ 会话 ID
- ✅ 发送者 ID
- ❌ 具体技能调用
- ❌ API 使用详情

---

### 3. Usage Tracking
**查看**:
```bash
openclaw status --usage
# 或在聊天中
/usage full
/usage cost
```

**包含内容**:
- ✅ Token 使用量
- ✅ 配额状态
- ✅ 估算成本
- ❌ 按技能分解
- ❌ 实时追踪

---

## 🔧 推荐方案：创建追踪 Hook

### 方案 A: 增强型 Command Logger

创建一个自定义 Hook，记录以下信息：

```json
{
  "timestamp": "2026-03-16T10:45:00+08:00",
  "session_id": "agent:main:main",
  "message_id": "abc123",
  "sender": "HaoHaiJiao",
  "task": "查询 TrendRadar 热点",
  "skills_used": ["trendradar", "exec"],
  "tools_called": [
    {"name": "exec", "command": "trendradar.sh", "duration_ms": 120000},
    {"name": "read", "path": "/output/2026-03-16/txt/09-55.txt", "duration_ms": 50}
  ],
  "api_usage": {
    "provider": "bailian",
    "model": "qwen3.5-plus",
    "input_tokens": 1500,
    "output_tokens": 2800,
    "cost_cny": 0.042
  },
  "result": "success"
}
```

### 方案 B: 会话后处理脚本

创建脚本分析会话记录，生成报告：

```bash
#!/bin/bash
# ~/.openclaw/scripts/trace-session.sh

SESSION_FILE="$1"
OUTPUT_DIR="~/.openclaw/logs/traces"

# 提取工具调用
jq -r 'select(.type=="tool_call") | 
  "\(.timestamp) | \(.tool_name) | \(.tool_args)"' "$SESSION_FILE"

# 统计 API 使用
jq -r 'select(.type=="usage") | 
  "\(.provider) | \(.model) | +\(.output_tokens) tokens"' "$SESSION_FILE"
```

---

## 📊 实时监控面板

### 快速查看命令

```bash
# 1. 最近技能调用
grep -h '"tool"' /tmp/openclaw/openclaw-*.log | \
  jq -r '.tool' | sort | uniq -c | sort -rn | head -20

# 2. 错误追踪
grep '"level":"error"' /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log | \
  jq -r '.message'

# 3. 执行时间分析
grep '"duration"' /tmp/openclaw/openclaw-*.log | \
  jq -r '.duration_ms' | \
  awk '{sum+=$1; count++} END {print "平均:", sum/count, "ms"}'
```

---

## 🔍 调试模式

### 启用详细日志
```bash
# 修改 ~/.openclaw/openclaw.json
{
  "logging": {
    "level": "debug",
    "consoleLevel": "debug",
    "consoleStyle": "json"
  }
}

# 重启网关
openclaw gateway restart
```

### 启用原始流记录
```bash
openclaw gateway --raw-stream --raw-stream-path ~/.openclaw/logs/streams.jsonl
```

---

## 📝 最佳实践

### 1. 日常监控
```bash
# 添加到 ~/.bashrc
alias oc-logs='openclaw logs --follow --json | jq -r ".message"'
alias oc-trace='tail -f ~/.openclaw/logs/commands.log | jq .'
alias oc-usage='openclaw status --usage'
```

### 2. 定期审计
```bash
# 每周生成报告
0 9 * * 1 ~/.openclaw/scripts/weekly-audit.sh
```

### 3. 告警设置
```bash
# 监控错误率
grep '"level":"error"' /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log | \
  wc -l | awk '$1 > 10 {print "错误过多！"}'
```

---

## 🚀 未来改进建议

1. **内置 Skill 追踪**: 在 Skill 元数据中添加 `requires.api` 字段
2. **成本标签**: 为每个 API 调用添加成本标签 (免费/付费/配额内)
3. **可视化面板**: 创建 Web UI 展示调用链路图
4. **导出功能**: 支持导出为 CSV/JSON 用于外部分析

---

*最后更新：2026-03-16*
