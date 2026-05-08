# 美股分析师评级数据源参考

## 推荐数据源（按优先级排序）

| 数据源 | URL 模式 | 适用场景 | 备注 |
|--------|---------|---------|------|
| **MarketBeat** | `https://www.marketbeat.com/stocks/NASDAQ/{TICKER}/forecast/` | 快速获取共识目标价 | 覆盖美股最全，更新频繁 |
| **Public.com** | `https://public.com/stocks/{ticker}/forecast-price-target` | 分析师数量统计 + 共识 | 界面清晰，含评级分布 |
| **StockAnalysis** | `https://stockanalysis.com/stocks/{ticker}/forecast/` | 详细分析师列表 | 含 Strong Buy/Buy/Hold 分级 |
| **TipRanks** | `https://www.tipranks.com/stocks/{ticker}/forecast` | 分析师历史准确率 | 含分析师排名 |
| **Benzinga** | `https://www.benzinga.com/quote/{TICKER}/analyst-ratings` | 最新评级变更 | 含高/低目标价区间 |

## 搜索策略

```
# 基础搜索（覆盖面广）
"{ticker} stock analyst rating target price 2026"

# 最新变更（抓近期上调/下调）
"{ticker} price target raised OR lowered 2026"

# 具体券商更新
"{ticker} Morgan Stanley price target 2026"
"{ticker} BofA Goldman Sachs rating 2026"
```

## 实战数据（2026-05-03 会话验证）

| 数据源 | 获取指标 | 可靠性 |
|--------|---------|:---:|
| MarketBeat | 共识目标价、分析师数量 | ✅ 高 |
| Public.com | 评级分布（Buy/Hold/Sell 数量） | ✅ 高 |
| StockAnalysis | 详细评级文本（Strong Buy/Buy） | ✅ 高 |
| TipRanks | 近期研报标题、价格目标调整 | ✅ 高 |
| CNN Money | 近期研报摘要（含日期和券商名） | ✅ 中（信息密度高） |

## 注意事项

1. **数据时效性**：部分源（如 Zacks）可能显示过时数据，需交叉验证价格是否匹配当前行情
2. **Ticker 区分**：GOOG 和 GOOGL 虽然同一公司，但分析师覆盖数量不同（GOOGL 45位 vs GOOG 8位）
3. **共识 vs 近期**：优先使用近期（1个月内）上调/下调信息，而非静态共识
4. **研报日期**：注意研报发布日期，财报后 1-2 天的更新最有时效性
