# MEMORY.md - Long-Term Memory

_最后更新: 2026-04-08_

---

## 🔑 核心知识

### 敏感信息存储
- **所有 API Key 和密码存储在 `~/.openclaw/.env`**（明文）
- `openclaw config get` 会 **redact 敏感字段**（`__OPENCLAW_REDACTED__`）
- 需要凭证时**优先读 `.env` 文件**，不要依赖 config get
- 已配置的 Key: JINA_API_KEY, TUSHARE_TOKEN, TAVILY_API_KEY, DINGTALK_*, WECOM_*, BAILIAN_API_KEY

### 搜索工具
- **主力搜索**: Jina Search（通过 exec curl 调用 `https://api.jina.ai/v1/search`）
- ~~web_search (Brave)~~ 已弃用
- web_fetch 配合 Jina 读取 URL 全文

### 渠道配置
- **WeChat**: 唯一通道，通过 openclaw-weixin 插件
- 审批消息通过消息队列文件传递，用户通过微信回复关键词

---

## 🏗️ 项目架构

### 三 Agent 架构
| Agent | 职责 | 模型 |
|-------|------|------|
| **main-agent** (当前) | 日常对话 + 信息检索 + 选股 + Workflow 调度 | qwen3.6-plus |
| **debate-agent** | 多空辩论分析 | (独立) |
| **trade-agent** | 交易执行 + 风控 | (独立) |

### 全链路 Pipeline
```
因子挖掘 (QuantaAlpha) → 选股 (Stock-Pick) → 辩论 (Debate) → 人工确认 → 交易执行 (VnPy/Futu) → 持仓管理
```

### Workflow 体系 (trade-agent)
| Workflow | 功能 | 状态 |
|----------|------|------|
| **Workflow A** | 因子挖掘 → 回测 | ✅ 完成 80% |
| **Workflow B v1** | 选股 → 辩论 → 投资策略报告 | ✅ 完成 90%（兼容版） |
| **Workflow B v2** | 定性→定量→估值→决策（整合 akshare） | ✅ 完成 100%（增强版） |
| **Workflow C** | 选股 → 分析 → 辩论 → 交易 → 持仓 | ✅ 完成 95% |

---

## 📊 交易经验与教训

### 富途 Futu 关键知识
1. **不同市场用不同的交易上下文**:
   - A 股: `OpenCNTradeContext`，账户 `18767295`，`time_in_force='DAY'`
   - 港股: `OpenHKTradeContext`，账户 `18767294`，`time_in_force='GTC'`
   - 美股: `OpenUSTradeContext`，账户 `18767299`（模拟盘）

2. **A 股行情权限问题**:
   - 富途 API 获取行情需要 A 股行情权限
   - 交易下单**不需要行情权限**，可直接指定限价
   - 无行情时用本地 CSV 数据或 Tushare 获取价格

3. **A 股交易规则**:
   - 最小交易单位: 100 股 (1 手)
   - 限价必须在涨跌停区间内（±10%）
   - 模拟盘 `DAY` 订单，不支持 `GTC`

4. **OpenD**:
   - 安装位置: `~/.openclaw/workspace/agents/trade/opend/`
   - 版本: 10.1.6108
   - 登录方式: 验证码登录（见 `opend/验证码登录解决方案.md`）
   - CentOS 修复记录: `trade/OPEND_CENTOS_FIX.md`

### 历史交易记录
| 日期 | 市场 | 股票 | 状态 |
|------|------|------|------|
| 2026-03-26 | 港股 | 3 只 | ✅ 下单 |
| 2026-03-27 | A 股 | 中贝通信(已成交)、电投绿能、意华股份 | ✅ 全链路 |
| 2026-03-27 | 美股 | TFC.US, FITB.US | ✅ 下单 |

### 用户持仓
- 东软集团: 6000 股（同花顺手动操作）
- 诺瓦星云: 600 股（同花顺手动操作）

---

## 🛠️ 工具与技能

### 已安装核心 Skills
- **企业级关键 Skill**（wuhoo- 冠名）:
  - `wuhoo-stock-deep-analysis`: Workflow B 增强版 — 单股深度分析（整合 akshare 财务 + 4 部分报告）
  - `wuhoo-stock-autopick-trade`: Workflow C — 多市场自动选股交易全链路
- `stock-pick`: 中证 1000 选股（残差波动率 + 换手率 + 动量 + Beta）
- `china-stock-analysis`: A 股价值投资分析
- `backtest`: VectorBT 回测
- `quantaalpha-skill`: 量化因子挖掘
- `jina_search`: Jina AI 搜索
- `tushare_search`: Tushare 股票数据（2120 积分）
- `futu-openapi`: 富途行情交易助手
- `futu-install-opend`: OpenD 安装助手
- `trendradar`: 热点趋势监控（42 平台）
- `wuhoo-news-rss`: RSS 资讯采集引擎（RSSHub + 原生 RSS，SQLite + FTS5）
- 其他: weather, file-search, get-tldr, technews, self-improving-agent 等

### 关键路径
```
选股数据: ~/workspace/agents/main/data/stock-pick/factors/
Workflow B 输出: ~/workspace/agents/trade/data/workflow_b/
Workflow C 输出: ~/workspace/agents/trade/data/workflow_c/
企业级 Skills: ~/.openclaw/skills/wuhoo-*/
QuantaAlpha: ~/workspace/agents/main/skills/quantaalpha-deep/
交易环境: ~/workspace/agents/trade/venv-futu/
```

### Python 环境
- 交易系统: `venv-futu` (Python 3.11)
- 依赖: VnPy 4.3.0, vnpy_futu 6.3.2808.0, futu-api 10.1.6108
- 选股/分析: 系统 Python 3.11

---

## 🔧 技能开发模式

### wuhoo- 企业级 Skills 持续迭代
- 这些 skill 正在通过 **Claude Code** 在后台持续迭代开发
- `install-futu-opend` / `futu-api` / `wuhoo-stock-autopick-trade` / `wuhoo-stock-deep-analysis` / `wuhoo-trade-diagnose`
- 需要时常关注它们的 SKILL.md 更新，学习新增功能和用法
- 不要随意删除这些 skill，即使当前看似未使用

---

## 📋 重要决策

### 2026-03-25: 全链路架构选型
- **选择 VnPy + vnpy_futu** 作为交易框架
- 理由: 国内最成熟开源量化框架，有官方富途接口
- 职责分离: main-agent 选股 → trade-agent 执行 → 用户确认

### 2026-03-13: 技能安全审查
- akshare-stock: ⚠️ 中高风险（subprocess 调用，需修复）
- china-stock-analysis / backtesting / backtest: ✅ 低风险

### 选股策略
- **中证 1000 成分股** 为基础
- 多因子: 252 日残差波动率 ≤50% → 5 日换手率 ≥50% → 5 日动量 ≥70% → 20 日 Beta ≥70%
- 按 10 日动量排序 Top10
- 逆向选择: 找短期回调后的机会

---

## ⚠️ 教训与注意事项

1. **凭证优先查 `.env`**，不要用 `openclaw config get` 拿敏感信息
2. **记忆维护**: MEMORY.md 需要定期更新，日志不能断
4. **数据问题**: 成分股文件曾被清空，注意数据完整性检查
5. **模拟盘优先**: 新策略必须先模拟盘验证

---

## 📅 活动时间线

| 日期 | 事件 |
|------|------|
| 03-11 | 批量安装 18 个 Skills，配置 API Keys |
| 03-13 | 安全审查 akshare 等股票技能，测试通过 |
| 03-24 | 中证 1000 选股（数据修复后重跑） |
| 03-25 | 全链路架构确定，VnPy 选型，OpenD 安装 |
| 03-26 | 港股首单，Workflow C 港股全链路打通 |
| 03-27 | A 股首单 + 美股首单，三市场全链路打通 |
| 03-28 | Workflow A/B/C 全部开发完成 |
| 03-31 | A 股选股继续执行 |
| 04-01 | A 股选股执行 |
| 04-07 | A 股 Workflow C 分析（10 只候选，全部未通过风控） |
| 04-08 | 模型切换到 qwen3.6-plus，记忆系统重建 |
| 04-09 | OpenClaw 升级至 2026.4.11，百炼 API 切换验证通过，wuhoo-news-rss 资讯引擎搭建（RSSHub + 24 源 + SQLite FTS5），清理可观测插件(497MB)+Trader Frontend+QuantaAlpha(~16GB)，磁盘 69%→44% |

---

## 🔄 待办

### 紧急
- [ ] 验证 WeChat 审批流程端到端可用性
- [ ] 重启 Gateway 使新配置生效

### 重要
- [ ] QuantaAlpha 因子挖掘集成到 Workflow A
- [ ] 实盘切换准备（小仓位测试）
- [ ] 数据完整性监控

### 长期
- [ ] 辩论 agent 完整实现（当前简化分析可用）
- [ ] 人工确认流程优化
- [ ] 回测模块完善
- [ ] 性能监控与告警
