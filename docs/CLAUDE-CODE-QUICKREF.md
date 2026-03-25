# Claude Code + 百炼配置 - 快速参考卡

**状态**: ✅ 已配置完成  
**最后更新**: 2026-03-13

---

## 🚀 快速使用

### 在 OpenClaw 中使用 dev-agent

```bash
# 代码生成
/dev 帮我写一个 Python 快速排序算法

# 代码审查
/dev 请审查这段代码...

# Bug 修复
/dev 这个函数有问题，帮我调试...
```

---

## 🔧 查看配置

### 检查环境变量
```bash
grep "CODING_PLAN_KEY\|BAILIAN_API_KEY" ~/.openclaw/.env
```

### 检查 Claude Code CLI
```bash
claude --version
```

---

## 📝 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| **环境变量** | `~/.openclaw/.env` | ⚠️ 包含敏感信息，勿分享 |
| **OpenClaw 配置** | `~/.openclaw/openclaw.json` | Agent 和工具配置 |
| **dev-agent 文档** | `~/.openclaw/workspace/agents/dev/TOOLS.md` | 工具使用说明 |

---

## 🧪 测试连接

### 方法 1: 使用 curl 测试 API
```bash
curl -X POST "https://coding.dashscope.aliyuncs.com/v1/chat/completions" \
  -H "Authorization: Bearer $BAILIAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-coder-next","messages":[{"role":"user","content":"Hello"}]}'
```

### 方法 2: 使用claude 命令
```bash
claude --api-key "$CODING_PLAN_KEY" \
       --base-url "https://coding.dashscope.aliyuncs.com/v1" \
       "你好，测试连接"
```

---

## 🔍 故障排查速查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| `command not found: claude` | 未安装 CLI | `npm install -g @anthropic-ai/claude-code` |
| `401 Unauthorized` | API Key 无效 | 检查 `.env` 中的 Key 是否正确 |
| 连接超时 | 网络问题 | 检查网络连接或 DNS 设置 |
| dev-agent 无法调用工具 | 配置错误 | 检查 `openclaw.json` 中 tools.allow |

---

## 📚 完整文档

- **详细配置指南**: `docs/CLAUDE-CODE-BAILIAN-CONFIG.md`
- **环境变量说明**: `~/.openclaw/.env` (注释部分)
- **工具使用文档**: `workspace/agents/dev/TOOLS.md`

---

## ⚡ 常用命令

```bash
# 重新加载环境变量
source ~/.openclaw/.env

# 查看当前配置
echo "CODING_PLAN_KEY: ${CODING_PLAN_KEY:0:10}..."
echo "BAILIAN_API_KEY: ${BAILIAN_API_KEY:0:10}..."
echo "ANTHROPIC_BASE_URL: $ANTHROPIC_BASE_URL"

# 检查服务状态
ps aux | grep openclaw

# 查看日志
tail -f ~/.openclaw/logs/*.log
```

---

## 🆘 需要帮助？

1. 查看详细文档：`docs/CLAUDE-CODE-BAILIAN-CONFIG.md`
2. 检查配置清单：运行测试脚本
3. 查看日志文件：`~/.openclaw/logs/`

---

**提示**: 本卡片不包含任何敏感信息，可以安全分享。实际 API Key 保存在 `~/.openclaw/.env` 文件中。
