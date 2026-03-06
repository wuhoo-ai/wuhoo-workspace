# TOOLS.md - dev-agent 工具笔记

## 开发环境

### 工作目录
```
~/openclaw/workspace/Code/
├── AI-Trader/          # 量化交易项目
├── TrendRadar/         # 热点监控项目
└── ...                 # 其他项目
```

### Python 环境
- **版本**: Python 3.10+
- **AI-Trader**: `~/openclaw/workspace/Code/AI-Trader/venv/` (如有)
- **TrendRadar**: `~/openclaw/workspace/Code/TrendRadar/venv/` (如有)

### Node.js 环境
- **版本**: v22.16.0
- **OpenClaw**: `~/openclaw/`

## 可用技能

### 代码开发
- `coding-agent`: 代码生成、审查
- `github`: 仓库管理、PR/Issue
- `gh-issues`: GitHub Issue 追踪
- `tmux`: 远程开发会话

### 文件操作
- `read` / `edit` / `write`: 代码编辑
- `exec`: 运行测试、构建、部署

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
cd ~/openclaw/workspace/Code/AI-Trader

# 启动 MCP 服务
python agent_tools/start_mcp_services.py

# 运行交易
python main.py --config configs/default_config.json

# 查看日志
tail -f data/agent_data/trade-agent/log/*/log.jsonl
```

### TrendRadar
```bash
cd ~/openclaw/workspace/Code/TrendRadar

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
