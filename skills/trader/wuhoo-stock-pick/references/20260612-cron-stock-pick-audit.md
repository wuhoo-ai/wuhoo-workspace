# 2026-06-12 Cron 每日选股审计

## 执行摘要

三市场选股完成，但发现两个重要问题需在 skill 中固化。

## 市场状态 (来自 market_regime)

| 市场 | Regime | Composite | Confidence | 策略 | 仓位 |
|------|--------|-----------|------------|------|------|
| US | BULL_TRENDING | 1.45 | 0.72 | trend_momentum | 100% |
| HK | RANGING | 0.40 | 0.20 | oversold_rebound | 80% |
| CN | RANGING | 0.30 | 0.15 | oversold_rebound | 80% |

## 问题 1：trend_momentum.py 无法实时选股

**症状**：对 US (BULL_TRENDING)，按路由规则应运行 `trend_momentum.py --market us --months 12`，预期输出 Top 10 选股。实际该脚本仅做历史回测（test dates 为每月 15 日，到 2026-05-15 为止），无 `--date` 参数也无实时选股模式。

**影响**：BULL_TRENDING / BULL_VOLATILE 市场无法通过 trend_momentum.py 获得当日选股结果，只能降级为 stock_pick.py 超跌反弹模型输出。

**处置**：本次用 stock_pick.py 替代，输出超跌反弹候选（低波 + 低动量）。但因子筛选方向与趋势动量相反（超跌反弹偏好低动量排序，趋势动量偏好高动量），结果不完全匹配策略意图。

**建议修复方向**：
- 扩展 trend_momentum.py 增加 `--date` 参数，输出当日动量排序 Top N
- 或在 market_regime 路由中明确 BULL_TRENDING → 仍用 stock_pick.py 但调整因子排序（momentum_10d 改为越高越好）

## 问题 2：HK stock_pick.py 名称显示 "N/A"

**症状**：`stock_pick.py --market hk` 的最终结果表中 `name` 列全为 NaN/N/A。因子计算正常（499/500 有效），但代码→名称映射失败。

**原因**：HK 的名称映射逻辑可能依赖 `stock_info_hk_top500.csv`，但文件中的 `code` 列格式与因子结果中的 `ts_code` 不完全匹配或匹配路径未执行。

**验证**：手动用 `stock_info_hk_top500.csv` 查表可正确获取名称。

**处置**：cron 报告阶段需手动查表补全名称（或用脚本自动补全）。

## 问题 3：CN 数据日期滞后

**症状**：target date = 2026-06-12，但 CN factor 计算使用的最近交易日为 2026-06-05。这是因为 A 股本地日线数据存在 T+N 入库延迟。

**影响**：CN 选股实际基于 7 天前的数据（对超跌反弹策略影响有限，因子窗口为 252d/20d）。

**处置**：正常现象，cron 报告中标注实际数据日期即可。

## US 选股输出（超跌反弹模型，非趋势动量）

```
BALL.US, RTX.US, ROST.US, KEY.US, TFC.US, CFG.US, HBAN.US, FITB.US
```
仅选出 8 只（Beta 阈值 P20 严格，美股低波动环境下筛选率仅 1.6%）。全部为银行/金融/工业股，Beta 0.46-0.80。

趋势动量回测参考（最近一期 2026-05-15）：AKAM, MU, DVA, GLW, SNDK, DOC, COHR, HPE, DELL, QCOM (+25.5%, 90% Win)。
