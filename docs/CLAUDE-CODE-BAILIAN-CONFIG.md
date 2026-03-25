# Claude Code CLI + 百炼 Coding-Plan 配置指南

**配置日期**: 2026-03-13  
**状态**: ✅ 已完成

---

## 📋 配置概览

本配置允许 Claude Code CLI 使用阿里云百炼的 coding-plan API，为 dev-agent 提供代码生成和审查能力。

### 核心组件

| 组件 | 配置值 | 状态 |
|------|--------|------|
| **Claude Code CLI** | `@anthropic-ai/claude-code` | ✅ 已安装 |
| **API Provider** | 阿里云百炼 (coding.dashscope.aliyuncs.com) | ✅ 已配置 |
| **API Key** | `CODING_PLAN_KEY` (见 `.env` 文件) | ✅ 已配置 |
| **Base URL** | `https://coding.dashscope.aliyuncs.com/v1` | ✅ 已配置 |
| **默认模型** | `qwen3-coder-next` | ✅ 已配置 |

---

## 🔧 配置详情

### 1. 环境变量配置 (`~/.openclaw/.env`)

```bash
# 方式一：CODING_PLAN_KEY（推荐）
CODING_PLAN_KEY=<你的百炼 API Key>

# 方式二：ANTHROPIC_BASE_URL + BAILIAN_API_KEY
ANTHROPIC_BASE_URL=https://coding.dashscope.aliyuncs.com/apps/anthropic
BAILIAN_API_KEY=<你的百炼 API Key>
```

**注意**: 实际的 API Key 已配置在 `~/.openclaw/.env` 文件中，请勿将真实 Key 提交到版本控制系统。

### 2. OpenClaw 配置 (`openclaw.json`)

```json
{
  "agents": {
    "list": [
      {
        "id": "dev",
        "tools": {
          "allow": [
            "coding-agent"  // ✅ 已启用
          ]
        }
      }
    ]
  },
  "skills": {
    "entries": {
      "coding-agent": {
        "enabled": true  // ✅ 已启用
      }
    }
  }
}
```

---

## 🚀 使用方式

### 在 OpenClaw 中使用

向 dev-agent 发送编码任务即可：

```bash
# 示例 1: 代码生成
/dev 帮我写一个 Python 函数计算斐波那契数列

# 示例 2: 代码审查
/dev 帮我审查一下这段代码...

# 示例 3: Bug 修复
/dev 这个函数有 bug，帮我修复一下...

# 示例 4: 功能实现
/dev 实现一个双均线策略的选股脚本
```

### 直接使用 Claude Code CLI

```bash
# 测试连接
claude --api-key $CODING_PLAN_KEY \
       --base-url https://coding.dashscope.aliyuncs.com/v1 \
       "你好，测试连接"

# 执行编码任务
claude --api-key $CODING_PLAN_KEY \
       --base-url https://coding.dashscope.aliyuncs.com/v1 \
       "帮我写一个快速排序算法"
```

---

## 🧪 测试验证

运行测试脚本验证配置：

```bash
cd ~/.openclaw
chmod +x scripts/test-claude-code-bailian.sh
./scripts/test-claude-code-bailian.sh
```

测试内容包括：
- ✅ 环境变量检查
- ✅ Claude Code CLI 安装状态
- ✅ 百炼 API 连接测试
- ✅ Claude Code CLI 直接调用测试

---

## 📊 可用模型列表

| 模型 | 用途 | 推荐场景 |
|------|------|---------|
| `qwen3-coder-next` | 代码生成 | 默认使用，适合各种编程任务 |
| `qwen3-coder-plus` | 代码理解 | 代码分析、重构建议 |
| `qwen3.5-plus` | 通用编程 | 复杂逻辑、多步骤任务 |

---

## ⚙️ 高级配置

### 切换默认模型

如果需要修改 dev-agent 使用的默认模型，编辑 `openclaw.json`:

```json
{
  "agents": {
    "list": [
      {
        "id": "dev",
        "model": "bailian/qwen3-coder-plus"  // 修改这里
      }
    ]
  }
}
```

### 使用不同的 API Key

如果有多个 API Key 用于负载均衡：

```bash
# 在 .env 中添加
CODING_PLAN_KEY_PRIMARY=<你的主 API Key>
CODING_PLAN_KEY_SECONDARY=<你的备用 API Key>
```

---

## 🔍 故障排查

### 问题 1: Claude Code CLI 未找到

**症状**: `command not found: claude`

**解决方案**:
```bash
npm install -g @anthropic-ai/claude-code
```

### 问题 2: API Key 无效

**症状**: `401 Unauthorized` 或 `Invalid API Key`

**解决方案**:
1. 检查 `.env` 文件中 `CODING_PLAN_KEY` 是否正确配置
2. 确认 Key 没有过期或在百炼控制台查看是否已启用
3. 重新加载环境变量：`source ~/.openclaw/.env`

### 问题 3: 连接超时

**症状**: 请求超时或无响应

**解决方案**:
1. 检查网络连接
2. 尝试使用国内 DNS
3. 如果使用代理，确保代理正常工作

### 问题 4: dev-agent 无法调用 coding-agent

**症状**: dev-agent 回复无法使用编码工具

**解决方案**:
1. 检查 `openclaw.json` 中 dev-agent 的 tools.allow 是否包含 `coding-agent`
2. 重启 OpenClaw Gateway
3. 查看日志：`tail -f ~/.openclaw/logs/*.log`

---

## 📝 最佳实践

### 1. 任务描述清晰

✅ **好的示例**:
```
/dev 用 Python 实现一个快速排序算法，要求：
1. 支持升序和降序
2. 添加类型注解
3. 包含单元测试
```

❌ **不好的示例**:
```
/dev 写个排序
```

### 2. 分步进行大任务

对于复杂的编码任务，建议分步进行：

```
第一步：/dev 设计一个用户管理系统的数据库 schema
第二步：/dev 根据上面的 schema 创建 SQLAlchemy 模型
第三步：/dev 实现用户 CRUD 操作的 API 接口
```

### 3. 代码审查

让 dev-agent 审查现有代码：

```
/dev 请审查这段代码，指出：
1. 潜在的性能问题
2. 安全漏洞
3. 代码风格问题
4. 改进建议
```

### 4. 调试辅助

遇到 bug 时：

```
/dev 这个函数返回了错误的结果，帮我调试一下：
[粘贴代码]
[描述预期行为和实际行为]
```

---

## 🆚 与原生 Claude Code CLI 的对比

| 特性 | 百炼 Coding-Plan | 原生 Anthropic API |
|------|-----------------|-------------------|
| **API Key** | `<你的百炼 Key>` (成本低) | `<你的 Anthropic Key>` (成本较高) |
| **网络要求** | ✅ 国内直连 | ❌ 需要国际网络 |
| **延迟** | 🟢 低 (~50ms) | 🟡 高 (~300ms+) |
| **成本** | 💰 低 | 💰💰 高 |
| **模型版本** | Qwen Coder 系列 | Claude 3.5 Sonnet |
| **中文支持** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **推荐度** | ⭐⭐⭐⭐⭐ (当前使用) | ⭐⭐⭐ |

---

## 📚 相关资源

- [阿里云百炼官方文档](https://help.aliyun.com/zh/model-studio/)
- [Claude Code CLI GitHub](https://github.com/anthropics/claude-code)
- [Qwen Coder 模型介绍](https://help.aliyun.com/zh/model-studio/getting-started/models)

---

## 🔐 安全提醒

1. **保护 API Key**: 
   - ✅ API Key 已保存在 `~/.openclaw/.env` 文件
   - ✅ `.gitignore` 已配置忽略 `.env` 文件
   - ❌ 不要将真实 API Key 提交到 Git 或任何文档中

2. **定期轮换**: 建议每 3-6 个月更换一次 API Key

3. **监控用量**: 定期检查百炼控制台的用量统计

4. **最小权限**: 仅授予必要的权限

5. **文档中的占位符**: 
   - 本文档中使用 `<你的百炼 API Key>` 作为占位符
   - 实际配置在 `~/.openclaw/.env` 文件中
   - 查看配置请运行：`grep "CODING_PLAN_KEY" ~/.openclaw/.env`

---

**配置完成！** 🎉

现在你可以开始使用 dev-agent 进行高效的编码工作了！
