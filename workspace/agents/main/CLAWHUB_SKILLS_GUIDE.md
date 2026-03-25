# ClawHub Skills 安装和使用指南

**更新时间**: 2026-03-10  
**OpenClaw 版本**: v2026.3.8

---

## 📚 什么是 ClawHub？

**ClawHub** 是 OpenClaw 的官方技能市场，类似于：
- 📱 iOS App Store (对于 iPhone)
- 🛒 npm Registry (对于 Node.js)
- 🐍 PyPI (对于 Python)

**网址**: https://clawhub.com

---

## ⚠️ 重要说明

### ClawHub 能安装什么？

| 类型 | 支持 | 说明 |
|------|------|------|
| **Skills** | ✅ 支持 | 可以通过 ClawHub 安装 |
| **Plugins** | ❌ 不支持 | Plugins 通过 npm 或本地安装 |

### 当前状态

- `openclaw clawhub` 命令**不可用** (v2026.3.8)
- 需要使用独立的 `clawhub` CLI 工具
- Skills 也可以手动安装（复制文件）

---

## 🔧 安装 ClawHub CLI

### 前提条件

需要 Node.js 和 npm：
```bash
# 检查是否已安装
node --version
npm --version
```

### 安装命令

```bash
# 全局安装 ClawHub CLI
npm install -g clawhub

# 验证安装
clawhub --version
clawhub --help
```

---

## 📥 使用 ClawHub 安装 Skills

### 1. 搜索 Skills

```bash
# 搜索技能
clawhub search "postgres"
clawhub search "weather"
clawhub search "AI search"

# 查看搜索结果
clawhub search --limit 10
```

### 2. 查看 Skill 详情

```bash
# 查看技能信息
clawhub info <skill-name>

# 示例
clawhub info weather-forecast
clawhub info jina-search
```

### 3. 安装 Skill

```bash
# 安装最新版本
clawhub install <skill-name>

# 安装指定版本
clawhub install <skill-name> --version 1.2.3

# 示例
clawhub install weather-forecast
clawhub install jina-search --version 2.0.0
```

### 4. 安装位置

ClawHub 默认安装到：
```
~/openclaw/skills/<skill-name>/
```

---

## 📂 手动安装 Skills（无需 ClawHub CLI）

### 方法一：直接复制

```bash
# 1. 下载 Skill（从 GitHub 或其他来源）
git clone https://github.com/user/my-skill.git
cd my-skill

# 2. 复制到 skills 目录
cp -r my-skill ~/openclaw/skills/

# 3. 验证
ls ~/openclaw/skills/my-skill/
# 应该看到 SKILL.md
```

### 方法二：下载压缩包

```bash
# 1. 下载 zip 文件
wget https://github.com/user/my-skill/archive/main.zip
unzip main.zip

# 2. 移动到 skills 目录
mv my-skill-main ~/openclaw/skills/my-skill

# 3. 验证
ls ~/openclaw/skills/my-skill/SKILL.md
```

### 方法三：使用现有 Skill

当前系统已有 54 个 Skills，可以直接使用：
```bash
# 列出所有 Skills
openclaw skills list

# 查看 Skill 详情
openclaw skills info jina_search
```

---

## ✅ 使能 Skills

### Skills 不需要"启用"

与 Plugins 不同，Skills **不需要启用命令**：

| 操作 | Skills | Plugins |
|------|--------|---------|
| **安装后** | 立即可用 | 需要 `enable` |
| **配置** | Agent 工具策略控制 | `plugins.allow` |
| **重启** | 不需要 | 需要重启 Gateway |

### 控制 Skill 使用

通过 Agent 的 `tools.allow` 配置：

```json
{
  "agents": {
    "main": {
      "tools": {
        "allow": ["jina_search", "tushare_search", "weather"],
        "deny": ["exec", "bash"]
      }
    }
  }
}
```

**配置步骤**:
1. 编辑 `~/.openclaw/openclaw.json`
2. 添加 Skill 到 `tools.allow`
3. 保存即可（无需重启）

---

## 🛠️ 使用 Skills

### 在对话中使用

安装后，Agent 会自动发现并使用 Skills：

```
用户：帮我搜索一下最新的 AI 新闻
Agent: [自动调用 jina_search Skill]
       好的，我来搜索最新的 AI 新闻...
       [搜索结果]
```

### 查看 Skill 状态

```bash
# 列出所有 Skills
openclaw skills list

# 查看 Skill 详情
openclaw skills info <skill-name>

# 检查依赖
openclaw skills check
```

---

## 📦 管理已安装的 Skills

### 查看已安装

```bash
# 列出所有 Skills
ls ~/openclaw/skills/

# 通过 CLI 查看
openclaw skills list
```

### 更新 Skills

```bash
# 使用 ClawHub CLI 更新
clawhub update <skill-name>

# 手动更新（Git）
cd ~/openclaw/skills/<skill-name>
git pull
```

### 删除 Skills

```bash
# 直接删除目录
rm -rf ~/openclaw/skills/<skill-name>

# 验证删除
ls ~/openclaw/skills/ | grep <skill-name>
```

---

## 🔐 鉴权配置

### 需要 API Key 的 Skills

某些 Skills 需要配置环境变量：

**步骤**:
1. 编辑 `~/.openclaw/.env`
2. 添加 API Key
3. 重启 Gateway（可选，某些 Skills 需要）

**示例**:
```bash
# ~/.openclaw/.env
JINA_API_KEY=jina_xxxxxxxx
TUSHARE_TOKEN=822130fe12b4a3f37b23c6718477718ac08450f703e76156bb241a6c
WEATHER_API_KEY=xxxxxx
```

### 查看 Skill 需求

```bash
# 查看 SKILL.md
cat ~/openclaw/skills/<skill-name>/SKILL.md

# 查找 requires 字段
grep -A 5 "requires" ~/openclaw/skills/<skill-name>/SKILL.md
```

---

## 📋 完整流程示例

### 示例：安装天气查询 Skill

#### 方法 A：使用 ClawHub CLI

```bash
# 1. 安装 ClawHub CLI
npm install -g clawhub

# 2. 搜索天气相关 Skills
clawhub search weather

# 3. 查看详情
clawhub info weather-forecast

# 4. 安装
clawhub install weather-forecast

# 5. 验证
ls ~/openclaw/skills/weather-forecast/
```

#### 方法 B：手动安装

```bash
# 1. 从 GitHub 克隆
git clone https://github.com/openclaw/weather-skill.git
cd weather-skill

# 2. 复制到 skills 目录
cp -r weather-skill ~/openclaw/skills/weather

# 3. 验证
cat ~/openclaw/skills/weather/SKILL.md
```

#### 配置使用

```bash
# 1. 编辑 openclaw.json
code ~/.openclaw/openclaw.json

# 2. 添加 tools.allow
{
  "agents": {
    "main": {
      "tools": {
        "allow": ["weather", "jina_search"]
      }
    }
  }
}

# 3. 保存（无需重启）
```

#### 测试使用

在对话中：
```
用户：今天天气怎么样？
Agent: [调用 weather Skill]
       今天天气晴朗，气温 25°C...
```

---

## 🎯 Plugins 安装（对比）

### Plugins 不能通过 ClawHub 安装

**Plugins 安装方式**:

| 方式 | 命令 | 说明 |
|------|------|------|
| **npm** | `openclaw plugins install @openclaw/telegram` | 从 npm Registry |
| **本地** | 复制到 `extensions/` | 本地开发 |
| **内置** | 自动发现 | Gateway 自带 |

### 启用 Plugins

```bash
# 启用插件
openclaw plugins enable telegram

# 禁用插件
openclaw plugins disable discord

# 重启 Gateway
openclaw gateway restart
```

### 配置 Plugins

```json
{
  "plugins": {
    "allow": ["channels", "telegram", "memory-core"]
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "${TELEGRAM_BOT_TOKEN}"
    }
  }
}
```

---

## 📊 Skills vs Plugins 安装对比

| 操作 | Skills | Plugins |
|------|--------|---------|
| **安装源** | ClawHub / Git / 手动 | npm / 本地 / 内置 |
| **安装命令** | `clawhub install` | `openclaw plugins install` |
| **启用** | ❌ 不需要 | ✅ `openclaw plugins enable` |
| **配置** | `tools.allow` | `plugins.allow` + `channels.*` |
| **重启** | ❌ 不需要 | ✅ 需要重启 Gateway |
| **热更新** | ✅ 支持 | ❌ 不支持 |

---

## 🔍 故障排查

### Skill 无法使用

```bash
# 1. 检查 Skill 是否存在
ls ~/openclaw/skills/<skill-name>/SKILL.md

# 2. 检查依赖
openclaw skills check

# 3. 检查环境变量
grep <SKILL_NAME> ~/.openclaw/.env

# 4. 检查 tools.allow
cat ~/.openclaw/openclaw.json | grep -A 5 "tools"
```

### ClawHub CLI 问题

```bash
# 检查是否安装
which clawhub
clawhub --version

# 重新安装
npm uninstall -g clawhub
npm install -g clawhub

# 清除缓存
clawhub cache clean
```

---

## 📚 参考资源

| 资源 | 链接 |
|------|------|
| **ClawHub** | https://clawhub.com |
| **Skills 文档** | https://docs.openclaw.ai/skills |
| **Plugins 文档** | https://docs.openclaw.ai/plugins |
| **CLI 参考** | https://docs.openclaw.ai/cli |
| **GitHub** | https://github.com/openclaw/openclaw |

---

## 📝 总结

### Skills 安装流程

```
1. 安装 ClawHub CLI (可选)
   npm install -g clawhub

2. 搜索 Skill
   clawhub search <keyword>

3. 安装 Skill
   clawhub install <skill-name>
   或手动复制到 ~/openclaw/skills/

4. 配置 tools.allow
   编辑 ~/.openclaw/openclaw.json

5. 开始使用
   在对话中自动调用
```

### Plugins 安装流程

```
1. 安装 Plugin
   openclaw plugins install @openclaw/telegram

2. 启用 Plugin
   openclaw plugins enable telegram

3. 配置 plugins.allow
   编辑 ~/.openclaw/openclaw.json

4. 配置渠道
   添加 channels.telegram 配置

5. 重启 Gateway
   openclaw gateway restart
```

---

**文档结束**
