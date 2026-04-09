# Workflow C 与 OpenClaw 集成说明

## 概述

Workflow C 是一个独立的多市场交易自动化执行脚本，它与 OpenClaw 的集成是**松耦合**的，主要通过以下方式实现：

## 信息传递机制

### 1. JSON 文件数据交换（主要方式）

Workflow C 在每个执行步骤中生成 JSON 文件，OpenClaw 通过读取这些文件获取执行结果：

```
workspace/agents/trade/data/workflow_c/{MARKET}_{DATE}/
├── 01_selected_stocks.json      # 选股结果
├── 02_analysis_results.json     # 分析结果
├── 03_debate_results.json       # 多空辩论结果
├── 04_recommendations.json      # 推荐列表
└── 05_trade_results.json        # 交易执行结果
```

**示例数据结构**:

```json
// 01_selected_stocks.json
{
  "date": "2026-03-31",
  "market": "HK",
  "selected_count": 10,
  "stocks": [...]
}

// 05_trade_results.json
{
  "count": 2,
  "trade_results": [
    {
      "code": "HK.00700",
      "action": "BUY",
      "price": 300.0,
      "qty": 100,
      "status": "pending_approval"
    }
  ]
}
```

### 2. 审批管理器模块集成

`approval_manager.py` 提供函数供 Workflow C 调用：

```python
from approval_manager import send_trade_approval, wait_for_approval

# Workflow C 中调用
result = send_trade_approval(recommendation, market="HK")
# 返回：{approval_id, status, sent_at}

# 等待用户回复
approval_result = wait_for_approval(approval_id, timeout_minutes=60)
# 返回：{status: "approved"/"rejected"/"timeout", ...}
```

### 3. 风控检查模块集成

`risk_manager.py` 提供风控检查函数：

```python
from risk_manager import risk_check, get_position

# 执行风控检查
result = risk_check(order, position)
# 返回：{passed, checks, warnings, block_reason, requires_confirmation}
```

### 4. 每日复盘报告生成

`daily_review.py` 读取 Workflow C 生成的 JSON 文件生成报告：

```python
from daily_review import generate_daily_review

# 生成每日复盘报告
report = generate_daily_review(date="2026-03-31")
# 输出：daily_review.json + daily_review.md
```

## OpenClaw 如何调用 Workflow C

OpenClaw 通过 `exec` 工具调用 Workflow C 脚本：

```
python workflow_c_multi_market.py --market HK --date 2026-03-31
```

脚本执行流程：
1. OpenClaw 调用 `workflow_c_multi_market.py`
2. 脚本依次执行：选股 → 分析 → 辩论 → 推荐 → 交易
3. 每一步生成 JSON 结果文件
4. 需要审批时调用 `approval_manager.send_approval()`
5. OpenClaw 等待用户回复（通过钉钉/企业微信）
6. 用户回复后，脚本继续执行交易

## 是否需要 MD 说明文件？

**不需要**。Workflow C 的运行不依赖 MD 文件，但 MD 文档有以下用途：

### 现有文档列表

| 文档 | 用途 |
|------|------|
| `AUTOMATION_PIPELINE.md` | 完整自动化流程设计 |
| `WORKFLOW_C_US_INTEGRATION.md` | 美股市场集成说明 |
| `WECHAT_APPROVAL_DESIGN.md` | 微信审批设计 |
| `DATA_SOURCE_STRATEGY.md` | 数据源策略 |
| `PRICE_DATA_STRATEGY.md` | 价格数据策略 |

### 新增文档建议

如需增强 Workflow C 与 OpenClaw 的集成可维护性，建议添加：

- `WORKFLOW_C_INTEGRATION.md` - 集成接口文档
- `data/workflow_c/README.md` - 数据文件格式说明

## 数据目录结构

```
~/.openclaw/workspace/agents/trade/
├── workflow_c_multi_market.py    # 主执行脚本
├── approval_manager.py           # 审批管理
├── risk_manager.py               # 风控检查
├── daily_review.py               # 每日复盘
├── data/
│   └── workflow_c/
│       ├── HK_2026-03-31/        # 按市场 + 日期组织
│       │   ├── 01_selected_stocks.json
│       │   ├── ...
│       │   └── daily_review.json
│       └── US_2026-03-31/
└── logs/                         # 日志文件
```

## 会话状态管理

OpenClaw 通过 JSONL 文件记录 Workflow C 执行状态：

```
~/.openclaw/agents/main/sessions/{session_id}.jsonl
```

每条记录包含：
- toolCall: `exec` 调用 Workflow C 脚本
- toolResult: 脚本执行输出
- message: 用户交互消息

## 故障恢复

如果 Workflow C 执行中断：
1. 删除会话锁文件：`rm ~/.openclaw/agents/main/sessions/*.lock`
2. 检查 OpenD 状态：`ps aux | grep FutuOpenD`
3. 重启 OpenD: `./start_opend.sh`
4. 重新执行 Workflow C

## 总结

Workflow C 与 OpenClaw 的集成特点：
- **数据驱动**: JSON 文件作为主要数据交换格式
- **模块化**: 审批、风控、复盘都是独立模块
- **松耦合**: Workflow C 可独立运行，不依赖 OpenClaw
- **可追溯**: 所有执行结果持久化到文件

**无需额外 MD 文件**，当前文档已足够支持维护和理解。
