# TOOLS.md - dev-agent 工具笔记

## 核心工具

### 编码工具
- **coding-agent**: 代码生成、审查 (使用 Claude Code CLI)
- **github**: 仓库管理、PR/Issue 操作
- **file-search**: 本地文件搜索
- **glob/grep**: 代码内容搜索
- **clawhub**: 技能管理

### 文件操作
- `read` / `edit` / `write`: 代码文件编辑
- `exec`: 运行测试、构建、部署命令

## 模型配置

**主模型**: `bailian/qwen3-coder-next`  
**API**: `https://coding.dashscope.aliyuncs.com/v1`  
**API Key**: `$BAILIAN_API_KEY`

### 使用 Claude Code CLI + 百炼 Coding-Plan（已配置）

**当前配置**: ✅ 已使用阿里云百炼的 coding-plan

1. **环境变量** (已在 `~/.openclaw/.env` 中配置):
```bash
# 方式一：CODING_PLAN_KEY（推荐）
CODING_PLAN_KEY=<你的百炼 API Key>

# 方式二：ANTHROPIC_BASE_URL + BAILIAN_API_KEY
ANTHROPIC_BASE_URL=https://coding.dashscope.aliyuncs.com/apps/anthropic
BAILIAN_API_KEY=<你的百炼 API Key>
```

**注意**: 实际 API Key 已保存在 `~/.openclaw/.env` 文件中，此处使用占位符。

2. **安装 Claude Code CLI**:
```bash
npm install -g @anthropic-ai/claude-code
```

3. **测试连接**:
```bash
# 使用 CODING_PLAN_KEY
claude --api-key $CODING_PLAN_KEY --base-url https://coding.dashscope.aliyuncs.com/v1

# 或使用 ANTHROPIC_BASE_URL
claude "Hello, test connection"
```

4. **在 OpenClaw 中使用**:
   - dev-agent 会自动使用 coding-agent 调用百炼
   - 无需额外配置，已集成到工具链中

5. **可用模型**:
   - `qwen3-coder-next` (默认，代码生成专用)
   - `qwen3-coder-plus` (代码理解和分析)
   - `qwen3.5-plus` (通用编程任务)

## Python 环境

### 项目路径
```
~/.openclaw/workspace/projects/
├── AI-Trader/          # 量化交易项目
├── TrendRadar/         # 热点监控项目
└── ...
```

### 虚拟环境
- **AI-Trader**: `~/.openclaw/workspace/projects/AI-Trader/venv/`
- **TrendRadar**: `~/.openclaw/workspace/projects/TrendRadar/venv/`
- **通用**: Python 3.11+

## 技能目录

### 全局技能 (~/.agents/skills/)
- `file-search` - 文件搜索
- `browse` - 网页浏览
- `get-tldr` - 文章摘要

### dev 专属技能
(暂无，使用全局技能)

## Git 规范

### Commit Message
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**: feat | fix | docs | style | refactor | test | chore

### 分支策略
- `main`: 主分支
- `feature/*`: 新功能
- `fix/*`: Bug 修复
- `hotfix/*`: 紧急修复

## 项目特定命令

### AI-Trader
```bash
cd ~/.openclaw/workspace/projects/AI-Trader

# 启动 MCP 服务
python agent_tools/start_mcp_services.py

# 运行交易
python main.py --config configs/default_config.json

# 查看日志
tail -f data/agent_data/trade-agent/log/*/log.jsonl
```

### TrendRadar
```bash
cd ~/.openclaw/workspace/projects/TrendRadar

# 运行热点监控
python -m trendradar

# 测试 MCP Server
python -m trendradar.mcp_server
```

### OpenClaw
```bash
cd ~/openclaw

# 开发模式
pnpm dev

# 构建
pnpm build

# 测试
pnpm test
```

## 代码审查清单

- [ ] 代码逻辑正确
- [ ] 边界条件处理
- [ ] 错误处理完善
- [ ] 性能无明显问题
- [ ] 无安全漏洞
- [ ] 代码可读性好
- [ ] 有必要的注释
- [ ] 测试覆盖关键逻辑

## 调试技巧

### Python
```bash
# 使用 pdb 调试
python -m pdb script.py

# 查看日志
tail -f logs/*.log
```

### Node.js
```bash
# 使用 inspect 调试
node --inspect script.js

# 查看日志
journalctl -u openclaw -f
```

---

*保持工具简洁，只记录真正用到的*
