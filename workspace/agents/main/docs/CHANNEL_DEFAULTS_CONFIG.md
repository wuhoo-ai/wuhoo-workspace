# ⚠️ OpenClaw Channel 默认配置 - 重要说明

## 🚫 不支持的配置方式

**不要**在 `~/.openclaw/openclaw.json` 中添加 `channelDefaults` 配置项！

```json
❌ 错误示例 (会导致网关无法启动):
{
  "agents": {
    "defaults": {
      "channelDefaults": {
        "webchat": { ... }
      }
    }
  }
}
```

**原因**: 当前版本的 OpenClaw (2026.3.8) **不支持**在配置文件中预设 channel 级别的 `/think`、`/verbose`、`/reasoning` 设置。

---

## ✅ 正确的配置方式

### 方式 1: 手动执行命令 (推荐)

每次使用 `/new` 开始新会话后，执行对应渠道的命令：

| 渠道 | 命令 |
|------|------|
| **WebChat** | `/think high /verbose on /reasoning off` |
| **Telegram** | `/think high /verbose on /reasoning on` |
| **Discord** | `/think high /verbose on /reasoning on` |

---

### 方式 2: 使用快捷脚本

```bash
# WebChat
~/.openclaw/scripts/set-channel-defaults.sh webchat

# Telegram
~/.openclaw/scripts/set-channel-defaults.sh telegram

# Discord
~/.openclaw/scripts/set-channel-defaults.sh discord
```

脚本会输出对应命令，复制粘贴到 OpenClaw 即可。

---

### 方式 3: 使用 BOOT.md (不推荐)

可以在 `~/.openclaw/workspace/agents/main/BOOT.md` 中添加：

```bash
/think high
/verbose on
/reasoning off
```

⚠️ **缺点**: BOOT.md 无法检测渠道，会对所有渠道应用相同设置。

---

## 📋 当前配置总结

| 设置项 | 作用范围 | 是否可配置 | 说明 |
|-------|---------|-----------|------|
| `/think` | Session | ❌ | 只能手动执行命令 |
| `/verbose` | Session | ❌ | 只能手动执行命令 |
| `/reasoning` | Session | ❌ | 只能手动执行命令 |
| `/model` | Session/Agent | ✅ | 可在配置文件配置 |

---

## 🔧 未来可能的改进

如果 OpenClaw 后续版本支持，可以在配置文件中添加：

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "defaults": {
          "channels": {
            "webchat": {
              "think": "high",
              "verbose": "on",
              "reasoning": "off"
            }
          }
        }
      }
    ]
  }
}
```

但当前版本**不支持**此配置。

---

## 📚 相关文档

- **快速参考**: `~/workspace/agents/main/TOOLS.md`
- **调用链路追踪**: `~/workspace/agents/main/docs/CALL_TRACE_GUIDE.md`

---

*最后更新：2026-03-16*  
*OpenClaw 版本：2026.3.8*
