# OpenClaw 多代理配置指南

**版本**: 2026-03-13  
**作者**: main-agent

---

## 📋 目录

1. [架构概览](#架构概览)
2. [代理分工](#代理分工)
3. [环境配置](#环境配置)
4. [技能配置](#技能配置)
5. [路由规则](#路由规则)
6. [测试验证](#测试验证)

---

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    OpenClaw Gateway                      │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
    │   main    │  │    dev    │  │   trade   │
    │  (协调者)  │  │  (开发)   │  │  (交易)   │
    └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
          │               │               │
          │               │               │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
    │  qwen3.5  │  │ qwen3-    │  │ qwen3.5   │
    │  -plus    │  │ coder-next│  │ -plus     │
    └───────────┘  └───────────┘  └───────────┘
          │               │               │
          │               │               │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
    │ 通用技能  │  │ 编码技能  │  │ 金融技能  │
    │ - web搜索 │  │ - coding  │  │ - Tushare │
    │ - 文件操作│  │ - GitHub  │  │ - 回测    │
    │ - 消息推送│  │ - 调试    │  │ - 选股    │
    └───────────┘  └───────────┘  └───────────┘
```

---

## 🎯 代理分工

### main-agent (主协调者)

**职责**:
- ✅ 用户对话与需求理解
- ✅ 任务分解与路由 (dev/trade)
- ✅ 新闻摘要与心跳检查
- ✅ 跨代理协调与结果汇总

**模型**: `bailian/qwen3.5-plus`  
**工作空间**: `~/.openclaw/workspace/agents/main/`

**触发条件**:
- 所有用户消息首先到达 main
- main 根据内容判断是否需要路由到 dev 或 trade

---

### dev-agent (代码开发专家)

**职责**:
- ✅ 代码编写与重构
- ✅ Bug 调试与修复
- ✅ 代码审查与建议
- ✅ Skill 实现与优化
- ✅ 开发环境配置

**模型**: `bailian/qwen3-coder-next` (编码专用模型)  
**工作空间**: `~/.openclaw/workspace/agents/dev/`

**专用工具**:
- `coding-agent`: 代码生成、审查
- `github`: 仓库管理、PR/Issue
- `tmux`: 远程开发会话

**触发关键词**:
```
"写代码"、"修复 bug"、"实现功能"、"代码审查"、
"skill"、"开发"、"调试"、"重构"、"Git"
```

---

### trade-agent (量化交易专家)

**职责**:
- ✅ 因子挖掘与选股
- ✅ 金融数据查询
- ✅ 金融新闻与信息查询
- ✅ 模拟交易与回测
- ✅ 持仓管理与风险控制

**模型**: `bailian/qwen3.5-plus` (通用推理)  
**工作空间**: `~/.openclaw/workspace/agents/trade/`

**专用工具**:
- `tushare_search`: A 股数据查询
- `stock-pick`: 中证 1000 选股
- `akshare-stock`: A 股实时行情
- `backtest`: VectorBT 回测
- `backtesting-frameworks`: 回测框架

**触发关键词**:
```
"选股"、"回测"、"因子"、"持仓"、"交易"、
"股票"、"行情"、"金融"、"量化"、"收益"
```

---

## 🔧 环境配置

### 1. 更新 ~/.openclaw/.env

```bash
# =============================================================================
# 多代理专用配置
# =============================================================================

# -----------------------------------------------------------------------------
# Bailian (阿里云百炼) - 主 API Key
# -----------------------------------------------------------------------------
BAILIAN_API_KEY=<你的百炼 API Key>
BAILIAN_BASE_URL=https://coding.dashscope.aliyuncs.com/v1

# -----------------------------------------------------------------------------
# Coding-Plan Key (用于 dev-agent 的 Claude Code CLI)
# -----------------------------------------------------------------------------
# 注意：这是专门用于编码的 API Key，与主 Key 分开
BAILIAN_CODING_PLAN_KEY=<你的百炼 API Key>
# 或者使用独立 key (如果有)
# CODING_PLAN_API_KEY=sk-coding-xxx

**注意**: 以上示例使用占位符，实际 API Key 请配置在 `~/.openclaw/.env` 文件中。

# -----------------------------------------------------------------------------
# 金融数据 API Keys (trade-agent 专用)
# -----------------------------------------------------------------------------
TUSHARE_TOKEN=<你的 Tushare Token>
JINA_API_KEY=<你的 Jina API Key>
TAVILY_API_KEY=<你的 Tavily API Key>

**注意**: 实际 API Keys 请配置在 `~/.openclaw/.env` 文件中。

# AlphaVantage (美股数据，可选)
# ALPHA_VANTAGE_API_KEY=your_key_here

# -----------------------------------------------------------------------------
# 通用工具 API Keys
# -----------------------------------------------------------------------------
BRAVE_API_KEY=  # web_search 需要
GITHUB_TOKEN=   # dev-agent GitHub 操作需要
```

### 2. 验证 API Keys

```bash
# 测试 Bailian API
curl -X POST "https://coding.dashscope.aliyuncs.com/v1/chat/completions" \
  -H "Authorization: Bearer $BAILIAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.5-plus","messages":[{"role":"user","content":"Hello"}]}'

# 测试 Tushare API
curl -X POST "http://api.tushare.pro" \
  -H "Content-Type: application/json" \
  -d '{"api_name":"daily","token":"'"$TUSHARE_TOKEN"'","params":{"ts_code":"000001.SZ","start_date":"20260301","end_date":"20260313"}}'
```

---

## 📦 技能配置

### dev-agent 技能列表

编辑 `~/.openclaw/workspace/agents/dev/TOOLS.md`:

```markdown
# TOOLS.md - dev-agent 工具笔记

## 核心技能

### 编码相关
- **coding-agent**: 代码生成、审查 (使用 Claude Code CLI)
- **github**: 仓库管理、PR/Issue 操作
- **gh-issues**: GitHub Issue 追踪
- **tmux**: 远程开发会话管理

### 文件操作
- `read` / `edit` / `write`: 代码文件编辑
- `exec`: 运行测试、构建、部署命令
- `glob`: 文件搜索
- `grep`: 内容搜索

## Python 环境

### 项目路径
```
~/openclaw/workspace/Code/
├── AI-Trader/          # 量化交易项目
├── TrendRadar/         # 热点监控项目
└── OpenClaw/           # OpenClaw 本体
```

### 虚拟环境
- **AI-Trader**: `~/openclaw/workspace/Code/AI-Trader/venv/`
- **TrendRadar**: `~/openclaw/workspace/Code/TrendRadar/venv/`
- **OpenClaw**: 使用系统 Node.js v22.16.0

## 编码规范

### Commit Message
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**: feat | fix | docs | style | refactor | test | chore

### 代码审查清单
- [ ] 逻辑正确性
- [ ] 边界条件处理
- [ ] 错误处理
- [ ] 性能影响
- [ ] 安全漏洞
- [ ] 代码可读性
- [ ] 注释充分性
- [ ] 测试覆盖

## Claude Code CLI 配置

### 安装
```bash
npm install -g @anthropic-ai/claude-code
```

### 使用方式
```bash
# 使用 coding-plan key
claude --api-key $BAILIAN_CODING_PLAN_KEY \
       --base-url https://coding.dashscope.aliyuncs.com/v1

# 或在 OpenClaw 中通过 coding-agent 调用
```

### 最佳实践
1. 复杂任务先给整体方案
2. 大改动分多次 commit
3. 关键逻辑必须有注释
4. 修改后必须运行测试
```

---

### trade-agent 技能列表

编辑 `~/.openclaw/workspace/agents/trade/TOOLS.md`:

```markdown
# TOOLS.md - trade-agent 工具笔记

## 核心技能

### 金融数据
- **tushare_search**: A 股数据查询 (Tushare Pro)
- **akshare-stock**: A 股实时行情 (AkShare)
- **stock-pick**: 中证 1000 多因子选股
- **china-stock-analysis**: A 股价值投资分析

### 回测工具
- **backtest**: VectorBT 快速回测
- **backtesting-frameworks**: 回测框架文档

### 信息搜索
- **jina_search**: 金融新闻搜索
- **web_fetch**: 网页内容提取

## 数据源配置

### Tushare Pro
- **Token**: `$TUSHARE_TOKEN`
- **积分**: 需要足够积分获取高频数据
- **限制**: 基础积分只能获取日线数据

### AkShare
- **安装**: `pip install akshare`
- **环境**: Python 3.11+
- **虚拟环境**: `~/.agents/skills/akshare-stock/venv/`

### Jina Search
- **API Key**: `$JINA_API_KEY`
- **用途**: 金融新闻、公司公告、研报搜索

## 回测配置

### VectorBT
```bash
# 安装
pip install vectorbt quantstats plotly

# 使用 backtest 技能
/backtest ema-crossover 600519 SSE D
```

### 回测参数
- **初始资金**: ¥100,000 (A 股) / $10,000 (美股)
- **手续费**: 0.0003 (万分之三)
- **滑点**: 0.001 (千分之一)
- **基准**: 沪深 300 (000300.SH)

## 因子库

### 已实现因子
1. **残差波动率**: 252 日残差收益标准差
2. **换手率**: 5 日平均换手率
3. **动量**: 5 日/10 日/20 日价格动量
4. **Beta**: 相对沪深 300 的 20 日 Beta

### 因子筛选流程
```
1. 获取中证 1000 成分股
2. 计算各因子值
3. 按因子排序筛选
4. 等权重组合
5. 定期调仓 (周/月)
```

## 风险控制

### 仓位限制
- 单股票 ≤ 20%
- 单行业 ≤ 40%
- 现金 ≥ 10%

### 止损规则
- 单笔止损：-8%
- 总账户止损：-15%
- 连续亏损 3 笔：暂停复盘

## 交易日志

### 持仓文件
```
~/.openclaw/workspace/agents/main/data/stock-pick/
├── position.jsonl      # 当前持仓
└── trades.jsonl        # 交易记录
```

### 绩效报告
- **日报**: 每日收盘后生成
- **周报**: 每周一生成
- **月报**: 每月归因分析
```

---

## 🛣️ 路由规则

### 配置 openclaw.json

编辑 `~/.openclaw/openclaw.json`:

```json
{
  "routing": {
    "mode": "rules",
    "rules": [
      {
        "name": "dev-routing",
        "description": "代码开发任务路由到 dev-agent",
        "conditions": {
          "keywords": ["代码", "编程", "开发", "bug", "调试", "skill", "实现", "功能", "修复", "重构", "Git", "GitHub"],
          "regex": ["(写 | 修改 | 优化 | 审查).*(代码 | 程序| 脚本)", "(实现 | 添加 | 创建).*功能"]
        },
        "target": "dev"
      },
      {
        "name": "trade-routing",
        "description": "交易相关任务路由到 trade-agent",
        "conditions": {
          "keywords": ["选股", "回测", "因子", "持仓", "交易", "股票", "行情", "金融", "量化", "收益", "Tushare", "AkShare"],
          "regex": ["(分析 | 查询 | 获取).*(股票 | 行情 | 金融)", "(模拟 | 实盘).*交易"]
        },
        "target": "trade"
      },
      {
        "name": "main-default",
        "description": "默认由 main-agent 处理",
        "conditions": {
          "default": true
        },
        "target": "main"
      }
    ]
  }
}
```

### 路由测试

```bash
# 测试路由规则
openclaw routing test "帮我写一个选股脚本"
# 预期输出：dev

openclaw routing test "今天贵州茅台的行情如何"
# 预期输出：trade

openclaw routing test "今天的新闻摘要"
# 预期输出：main
```

---

## ✅ 测试验证

### 1. 测试 dev-agent

```bash
# 切换到 dev 代理
openclaw use dev

# 测试代码生成
echo "帮我写一个 Python 函数，计算移动平均线" | openclaw chat

# 预期：dev-agent 使用 qwen3-coder-next 生成代码
```

### 2. 测试 trade-agent

```bash
# 切换到 trade 代理
openclaw use trade

# 测试数据查询
echo "查询贵州茅台今天的价格" | openclaw chat

# 预期：trade-agent 使用 akshare-stock 获取实时行情
```

### 3. 测试路由

```bash
# 使用 main 代理 (默认)
openclaw use main

# 测试自动路由
echo "帮我实现一个动量因子选股策略" | openclaw chat
# 预期：自动路由到 dev-agent

echo "回测一下双均线策略" | openclaw chat
# 预期：自动路由到 trade-agent
```

---

## 📊 性能优化建议

### 1. 模型选择

| 任务类型 | 推荐模型 | 理由 |
|---------|---------|------|
| 代码生成 | qwen3-coder-next | 编码专用，准确率更高 |
| 代码审查 | qwen3-coder-plus | 上下文窗口大 (1M) |
| 通用对话 | qwen3.5-plus | 平衡性能与成本 |
| 复杂推理 | qwen3-max-2026-01-23 | 推理能力最强 |

### 2. 缓存策略

```bash
# 启用语义缓存 (减少重复 API 调用)
openclaw config set agents.defaults.cache.enabled true
openclaw config set agents.defaults.cache.ttl 3600  # 1 小时
```

### 3. 并发控制

```bash
# 限制并发请求数 (避免 API 限流)
openclaw config set agents.defaults.concurrency 3
```

### 4. 日志记录

```bash
# 启用详细日志
openclaw config set logging.level debug
openclaw config set logging.file ~/.openclaw/logs/openclaw.log
```

---

## 🔒 安全注意事项

### 1. API Key 管理

- ✅ 使用 `.env` 文件存储密钥
- ✅ 设置文件权限：`chmod 600 ~/.openclaw/.env`
- ❌ 不要将密钥提交到 Git
- ❌ 不要在代码中硬编码密钥

### 2. 交易安全

- ✅ 模拟交易与实盘交易分开
- ✅ 大额交易需要用户确认
- ✅ 设置止损线并严格执行
- ❌ 不要将交易 API Key 存储在明文文件

### 3. 代码安全

- ✅ 代码审查必须经过人工确认
- ✅ 敏感操作 (rm、chmod 等) 需要审批
- ✅ 使用 Git 进行版本控制
- ❌ 不要执行来源不明的代码

---

## 📝 常见问题

### Q1: 如何切换代理？

```bash
# 临时切换
openclaw use dev

# 永久切换 (直到下次切换)
openclaw config set agents.default dev
```

### Q2: 如何查看当前代理配置？

```bash
openclaw agents show main
openclaw agents show dev
openclaw agents show trade
```

### Q3: 如何添加新的路由规则？

编辑 `~/.openclaw/openclaw.json` 的 `routing.rules` 数组，添加新规则。

### Q4: dev-agent 不使用 Claude Code CLI 怎么办？

检查 `BAILIAN_CODING_PLAN_KEY` 是否正确配置，并在 `dev/TOOLS.md` 中明确指定使用 `coding-agent`。

### Q5: trade-agent 无法获取金融数据？

1. 检查 `TUSHARE_TOKEN` 是否有效
2. 确认 akshare-stock 的 venv 环境已创建
3. 检查网络连接是否正常

---

## 📚 参考文档

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [阿里云百炼文档](https://help.aliyun.com/zh/dashscope/)
- [Tushare Pro API](https://tushare.pro/document/2)
- [AkShare 文档](https://akshare.akfamily.xyz/)
- [VectorBT 文档](https://vectorbt.dev/)

---

**最后更新**: 2026-03-13  
**维护者**: main-agent
