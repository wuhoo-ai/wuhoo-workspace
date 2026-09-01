# 2026-06-08 深度分析退化审计

## 触发场景

A 股选股 → 辩论 → 深度分析流水线。选股产出 10 只，辩论 10/10 成功（BUY=2, SELL=1, HOLD=7）。随后对 3 只信号最明确的股票（昌红科技 300151 BUY、鸿远电子 603267 BUY、富乐德 301297 SELL）运行 `deep_analysis.py`。

## 退化表现

三份报告**完全一致**，无视股票差异：

| 字段 | 实际输出 | 应输出 |
|------|----------|--------|
| 行业 | "未知" | akshare 返回的实际行业 |
| 定量分析 2.1-2.3 | **完全空白** | ROE/毛利率/资产负债率等 |
| 当前价格 | 0.00 元 | 实时行情 |
| 安全边际 | 恒为 100% | 基于实际价格的合理值 |
| 辩论方式 | "简化规则分析" | 应加载 batch_debate.py 产出的 JSON |
| 看多/看空观点 | "(暂无)" | 实际辩论观点 |
| 最终决策 | 全部「持有 + 5.5分」 | 应反映辩论的 BUY/SELL 信号 |
| 审计可靠性 | 全部 92.9/100 (A) | 应随数据质量差异化 |

## 根因分析

1. **akshare 数据解析→报告映射缺失**：akshare 实际数据在嵌套字段（`stock_industry.industry`, `financial_indicators.net_profit`），但报告模板使用了错误的 key path
2. **辩论模块降级过于激进**：`deep_analysis.py` 内置的辩论降级逻辑无法找到 `data/debate/{date}/deepseek/debate_{symbol}.json`，直接退化到纯规则推理
3. **价格获取失败无 fallback**：无实时行情时降级到 0.00 而非报错或使用最近收盘价
4. **审计评分虚假偏高**：92.9 分对一份几乎全占位符的报告完全不匹配

## 当前建议

- **不要依赖 `deep_analysis.py` 的 `decision_report.md`**
- 以 `batch_debate.py` 产出的辩论 JSON 为决策依据
- 如需基本面数据，使用 web_search + web_extract 手动获取
- 待修复后再重新启用深度分析

## 相关

- Skill 主文件已添加 🚨 当前状态警告
- 修复方向：① akshare key path 映射 ② 辩论 JSON 加载路径修复 ③ 价格获取 fallback 链
