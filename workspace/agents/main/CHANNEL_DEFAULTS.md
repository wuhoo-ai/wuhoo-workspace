# 🚀 OpenClaw 会话默认配置

## 📋 当前配置

| 渠道 | /think | /verbose | /reasoning |
|------|--------|----------|------------|
| **WebChat** (main) | `high` | `on` | `off` |
| **Telegram** | `high` | `on` | `on` |
| **Discord** | `high` | `on` | `on` |
| **其他** | `high` | `on` | `on` |

---

## ⚡ 快速设置命令

### WebChat 专用
```bash
/think high /verbose on /reasoning off
```

### Telegram/Discord 专用
```bash
/think high /verbose on /reasoning on
```

---

## 🔧 配置方法

### 方法 1: 每次新会话时执行

使用 `/new` 开始新会话后，执行对应渠道的命令。

### 方法 2: 使用快捷宏 (推荐)

在 `~/.openclaw/workspace/agents/main/TOOLS.md` 添加:

```markdown
## 快捷命令

### WebChat 默认设置
```bash
/think high /verbose on /reasoning off
```

### Telegram/Discord 默认设置
```bash
/think high /verbose on /reasoning on
```
```

### 方法 3: 创建别名脚本

```bash
# ~/.openclaw/scripts/set-defaults.sh
#!/bin/bash
CHANNEL="$1"
case "$CHANNEL" in
  webchat)
    echo "/think high /verbose on /reasoning off"
    ;;
  telegram|discord|*)
    echo "/think high /verbose on /reasoning on"
    ;;
esac
```

---

## 📝 说明

- 这些设置是 **Session 级别**，每次 `/new` 或 `/reset` 后需要重新设置
- 设置会在当前会话中持续有效
- 不同渠道的会话是独立的，设置不共享

---

*最后更新：2026-03-16*
