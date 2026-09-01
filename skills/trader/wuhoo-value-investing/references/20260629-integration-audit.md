# wuhoo-value-investing 集成审计记录

> 2026-06-29 · Phase 1-8 全量实现 · 20/20 测试通过

## 市场阈值校准决策

### A股 ROE → 5%（非 8%）
ai-berkshire 原值 ROE<8% 排除，但中证1000 中位数 ROE 约 5-8%。不改会过滤 70%+ A 股。
- 决策：A 股阈值调至 5%
- 附加：保留「趋势改善豁免」（ROE 连续3年上升的放宽）

### 港股地产/公用事业 → 负债率 70%
ai-berkshire 原值 60%，但港地产/基建天然高杠杆。
- 决策：地产/基建负债率放宽至 70%
- 实现：`configs/quality_thresholds.yaml` 中 `industry_exemptions`

### 美股 → 保持原值
S&P 500 整体质量高，ROE<8%/负债率<60% 不变。

## 辩论方案决策

选择 **方案C（独立运行）** 而非 A（注入prompt）或 B（扩展角色）：
- 量化辩论（Bull/Bear/Trader）与价值辩论（段/巴/芒/李）并行
- 不耦合：量化视角侧重技术面，价值视角侧重基本面
- Trader 综合两者的 debate_summary.json + value_debate_summary.json

## Cron 任务设计

| 任务 | 频率 | 理由 |
|------|------|------|
| 质量预筛选 | 每日 9:00 | 在 8:00 数据更新 + 8:20 选股之后 |
| 组合审视 | 每周一 10:00 | 季度级别审视，周一给一周时间调整 |
| 论文追踪 | 每日 21:00 | 盘后检查，不影响盘中决策 |

## 测试覆盖

- financial_rigor.py: 5 个子命令全部通过
- report_audit.py: extract + verdict 通过
- quality_screen.py: S&P500 前5只全部通过（AAA级股票预期）
- investment_checklist.py: AAPL 6关执行
- value_deep_analysis.py: 7模块报告+JSON 产出
- industry_funnel.py: 扫描计划+报告模板生成
- portfolio_review.py: 组合审视流程（无持仓时优雅降级）
- thesis_tracker.py: add/check/list/close 全流程
- SKILL.md: 14 个文件结构完整

## 已知局限

1. quality_screen.py 的 FCF/OFC-NI/share-dilution 对 US/HK 依赖 yfinance 的 info dict（部分字段可能为 None）
2. value_debate.py 的 LLM 调用需 DEEPSEEK_API_KEY 环境变量
3. industry_funnel.py 的扫描层需 LLM Agent 执行 web_search，非独立脚本可完成
4. CN 财务数据依赖 akshare（akshare stock_financial_abstract），部分字段映射可能需要调试
