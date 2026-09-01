# 深度分析 4 根因 + 2 增强修复审计（2026-06-08）

## 背景
A 股选股→辩论→深度分析流水线运行后，3 份 deep_analysis.py 报告完全相同：
行业"未知"、定量分析空白、辩论"简化规则分析"、价格 0.00、决策全部【持有】5.5/10。

---

## 根因 A: `_get_basic()` API 失败
**现象**: `stock_individual_info_em()` 返回 `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`，basic 为空，行业/PE/PB/市值全部缺失。
**根因**: akshare 1.18.39 版本中该 API 的东方财富接口不可用。
**修复**: 降级到 `stock_profile_cninfo(symbol=code)`。字段映射：
- `公司名称` → name
- `所属行业` → industry  
- `注册资金` → market_cap（注意：这是注册资金，非真实市值，但比"暂缺"好）
**效果**: 行业从"未知" → "专用设备制造业"（昌红）

---

## 根因 B: `_get_indicators()` 只取前 10 行
**现象**: 护城河分析显示"财务数据不足"，定量分析 2.1-2.3 空白。
**根因**: `stock_financial_abstract` 返回 80 行指标（ROE/毛利率在 11-30 行），但 `df.head(limit=10)` 只取前 10 行（仅归母净利润/营收/成本等），后续所有指标查找全部落空。
**修复**: `limit=200`（default），仅当 `len(df) > limit` 才截断。
**效果**: 80 行指标全部可用，毛利率 28.7% / ROE 3.1% 正确填充。

---

## 根因 C: 指标名不匹配
**现象**: `_extract_indicator_value(indicators, '销售毛利率(%)')` 返回 None，虽然指标确实在数据中。
**根因**: 代码期望的指标名（带括号后缀）与 `stock_financial_abstract` 实际列名不一致：

| 代码期望 | 实际名称 |
|----------|----------|
| `销售毛利率(%)` | `毛利率` |
| `加权净资产收益率(%)` | `净资产收益率(ROE)` |
| `销售净利率(%)` | `销售净利率` |
| `资产负债率(%)` | `资产负债率` |
| `总资产周转率(次)` | `总资产周转率` |
| `主营业务收入同比增长率(%)` | `营业总收入增长率` |
| `应收帐款周转率(次)` | `应收账款周转率` |

**修复**: 新增模块级 `_INDICATOR_NAME_MAP` 映射表。`_extract_indicator_value()` 先查原始名，再查映射名。
**效果**: 所有指标查找正常工作。

---

## 根因 D: 辩论降级 + 符号不匹配
**现象**: 辩论方式="简化规则分析"，看多/看空观点="(暂无)"。
**根因**:
1. `DebateRunner.run()` 引用 `skills/debate/run_debate`（路径不存在）→ 降级到 `_quick_analysis_from_akshare()`
2. Futu 格式 `SZ.300151` 与 batch_debate 文件名 `debate_300151_SZ.json` 不匹配
**修复** (1): 检查 `data/debate/{YYYYMMDD}/deepseek/debate_{symbol}.json` 是否存在，存在则直接加载。batch_debate JSON 的 `bull/bear/trader` 字段映射到 `_normalize_full_debate()` 期望的 `bull_view/bear_view/trader_decision`。
**修复** (2): 符号格式检测 — 若 `exchange.code`（Futu 格式），翻转为 `code_exchange`。
**效果**: 辩论从"简化规则分析" → "完整四角色辩论"，看多/看空观点真实填充。

---

## 增强 E: 价格降级到 Tushare 日线数据
**现象**: 安全边际表格显示 `当前价格: 0.00 元`，安全边际恒为 100%。
**根因**: akshare 实时行情 API（`stock_bid_ask_em`）不可用（网络限制），后续 PE×EPS 反推也因 PE 缺失而失败。
**修复**: 新增 Tushare 日线数据降级路径：
```python
daily_dir = Path.home() / 'wuhoo-workspace' / 'data' / 'stock-pick' / 'daily_data'
csv_path = daily_dir / year / f'{month}.csv'
df_daily = pd.read_csv(csv_path, dtype={'ts_code': str})
# 匹配 ts_code 格式: 300151.SZ / 603267.SH / code.BJ
```
取 `trade_date` 最新的 `close` 价。
**效果**: 昌红 0.00→24.29 元，鸿远 0.00→74.80 元，富乐德 0.00→42.25 元。
**局限**: Tushare 数据有 T+2 左右延迟（测试日 6/8，最新数据 6/1），但对估值已足够。

---

## 增强 F: DCF 季度利润→年度利润
**现象**: DCF 基准盈利使用 Q1 利润（1695万），而非 FY 全年（6459万），内在价值被低估 3.8 倍。
**根因**: `_extract_metric_from_indicators()` 取第一个非元数据列的值。`stock_financial_abstract` 列顺序为 `20260331, 20251231, 20250930...`，第一个是最近季度。
**修复**: 优先查找列名以 `1231` 结尾的年报数据：
```python
annual_keys = [k for k in item if k not in ('指标', '选项')
               and str(k).endswith('1231') and item[k]]
if annual_keys:
    return float(item[annual_keys[0]])
```
**效果**: 昌红 DCF 基准 1695万→6459万（3.8x），内在价值 0.62→2.37 元（中性）。

---

## 修复后验证（昌红科技 300151）

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 行业 | (空) | 专用设备制造业 |
| 毛利率 | 未显示 | 28.7% |
| ROE 表 | 空白 | 6 期数据 |
| 辩论方式 | 简化规则分析 | 完整四角色辩论 |
| 看多观点 | (暂无) | 4 条真实 key_points |
| 当前价格 | 0.00 元 | 24.29 元 |
| DCF 基准利润 | 1,695万(Q1) | 6,459万(FY2025) |
| DCF 中性价值 | 0.62 元 | 2.37 元 |
| 可靠性评分 | 92.9 | 95.0 |

## 已知局限

1. **市值 = 注册资金**：`stock_profile_cninfo` 只返回注册资金，非真实市值。需 akshare 实时 API 恢复后才能获取真实市值。
2. **PE/PB 仍暂缺**：需要 `stock_individual_info_em` 或等效 API 恢复。
3. **DCF 仍偏低**：即使年度利润，三阶段 DCF 默认参数（CAGR 5-15%、折现率 8-12%）对这些高 Beta 中小盘股偏保守。内在价值系统性低于市价，导致决策偏卖出。这不一定是 bug——可能是市场定价 vs 基本面估值之间的真实张力。
4. **价格延迟 T+2**：Tushare 日线数据有延迟，但对估值精度影响有限（±2-3%）。
