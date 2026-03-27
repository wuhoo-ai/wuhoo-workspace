# TOOLS.md - trade-agent 工具笔记

## 核心工具

### 金融数据
- **tushare_search**: A 股数据查询 (Tushare Pro)
- **akshare-stock**: A 股实时行情 (AkShare)
- **china-stock-analysis**: A 股价值投资分析

### 回测工具
- **backtest**: VectorBT 快速回测
- **backtesting-frameworks**: 回测框架文档

### 信息搜索
- **web_search**: 网络搜索 (Brave)
- **web_fetch**: 网页内容提取
- **jina_search**: Jina AI 搜索
- **technews**: 科技新闻
- **agent-news**: AI 行业新闻

### 文件操作
- `file-search`: 本地文件搜索
- `glob/grep`: 内容搜索

## 模型配置

**主模型**: `bailian/qwen3.5-plus`  
**API**: `https://coding.dashscope.aliyuncs.com/v1`  
**API Key**: `$BAILIAN_API_KEY`

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

## 技能目录

### 全局技能 (~/.agents/skills/)
- `tushare_search` - A 股数据查询
- `akshare-stock` - A 股实时行情
- `china-stock-analysis` - A 股价值投资分析
- `backtest` - VectorBT 快速回测
- `backtesting-frameworks` - 回测框架
- `jina_search` - Jina AI 搜索
- `web_search` - 网络搜索
- `web_fetch` - 网页提取
- `technews` - 科技新闻
- `agent-news` - AI 行业新闻
- `quantaalpha-skill` - 因子挖掘 (main-agent)
- `stock-pick` - 中证 1000 选股 (main-agent)

### trade 专属技能 (~/.openclaw/workspace/agents/trade/skills/)
- `vnpy-futu-trader` - VnPy + 富途交易执行 (保留参考)
- `risk-manager` - 风控检查模块 🆕
- `debate-integration` - Debate 辩论集成 (开发中)

## 回测配置

### VectorBT
```bash
# 使用 backtest 技能
/backtest ema-crossover 600519 SSE D
/backtest rsi SBIN NSE D
/backtest supertrend NIFTY NFO 5m
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
~/.openclaw/workspace/projects/AI-Trader/data/agent_data/trade-agent/
├── position/
│   └── position.jsonl      # 当前持仓
└── log/
    └── {date}/
        └── log.jsonl       # 交易日志
```

### 绩效报告
- **日报**: 每日收盘后生成
- **周报**: 每周一生成
- **月报**: 每月归因分析

## 常用命令

### 启动服务
```bash
cd ~/.openclaw/workspace/projects/AI-Trader

# 启动所有 MCP 服务
python agent_tools/start_mcp_services.py

# 运行交易会话
python main.py --config configs/default_config.json
```

### 查看数据
```bash
# 查看持仓
cat data/agent_data/trade-agent/position/position.jsonl | tail -1 | jq

# 查看日志
tail -f data/agent_data/trade-agent/log/*/log.jsonl

# 计算收益
python tools/calculate_metrics.py --signature trade-agent

# 生成图表
python tools/plot_metrics.py --signature trade-agent
```

---

## 🆕 富途 OpenAPI 交易配置 (统一方案)

### 虚拟环境
```bash
# 使用现有虚拟环境
source ~/.openclaw/workspace/agents/trade/venv-futu/bin/activate

# 依赖已安装:
# - futu-api>=7.1.0
# - yfinance (美股价格)
# - pandas (数据处理)
```

### 富途 OpenD 配置
```
下载地址：https://www.futumm.com/OpenAPI
主机：127.0.0.1
端口：11111
市场：自动识别 (根据股票代码)
环境：SIMULATE (模拟) / REAL (实盘)
```

### 交易接口说明
| 市场 | 交易上下文 | 账户 | 订单类型 |
|------|-----------|------|----------|
| A 股 | OpenCNTradeContext | 18767295 | DAY (当日有效) |
| 港股 | OpenHKTradeContext | 18767294 | DAY (模拟盘) |
| 美股 | OpenUSTradeContext | 动态获取 | GTC |

### 环境变量
```bash
# ~/.openclaw/.env
FUTU_HOST=127.0.0.1
FUTU_PORT=11111
FUTU_ENV=SIMULATE
FUTU_TRADING_PASSWORD=<加密存储>
```

### 测试交易
```bash
cd ~/.openclaw/workspace/agents/trade

# 测试 A 股
python workflow_c_multi_market.py --market cn --date 2026-03-27

# 测试港股
python workflow_c_multi_market.py --market hk --date 2026-03-27

# 测试美股
python workflow_c_multi_market.py --market us --date 2026-03-27
```

### 全链路验证
```bash
# 运行完整验证测试
python test_workflow_c_full.py
```

---

## 📋 Pipeline 状态

| 模块 | 状态 | 负责人 |
|------|------|--------|
| QuantaAlpha (因子挖掘) | ✅ 已就绪 | main-agent |
| Stock-Pick (选股) | ✅ 已就绪 | main-agent |
| Debate (辩论) | ✅ 已就绪 | debate-agent |
| 人工确认 | ⚠️ 需用户确认 | main-agent |
| **Futu OpenAPI (交易)** | ✅ 已就绪 | trade-agent |
| Risk-Manager (风控) | 🚧 开发中 | trade-agent |

---

## 📝 架构决策

**交易接口**: 统一使用富途 OpenAPI (弃用 VnPy)

详见：`ARCHITECTURE_COMPARISON.md`, `VNPY_CLEANUP_REPORT.md`

---

*交易有风险，决策需谨慎*
