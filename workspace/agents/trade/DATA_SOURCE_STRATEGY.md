# 数据源策略文档

**版本**: v1.0
**更新时间**: 2026-03-26
**状态**: 设计 → 实施中

---

## 📊 数据源优先级总览

### 整体优先级（用户确认）

```
富途 OpenAPI > Tushare Pro > AkShare > efinance > AlphaVantage
```

### 按数据类别划分

| 数据类别 | P0 (首选) | P1 (备选) | P2 (降级) | P3 (模拟) |
|----------|-----------|-----------|-----------|-----------|
| **港股/美股行情** | 富途 OpenAPI | - | AlphaVantage | 模拟数据 |
| **港股/美股基本面** | 富途 OpenAPI | - | 行业估计 | 模拟数据 |
| **A 股行情** | Tushare Pro | AkShare | efinance | 模拟数据 |
| **A 股基本面** | Tushare Pro | AkShare | Qlib/行业估计 | 模拟数据 |
| **A 股因子** | QuantaAlpha (Qlib) | - | - | - |
| **舆情数据** | Web Search (Jina/Tavily) | TrendRadar | 热点估计 | 模拟数据 |

---

## 🔍 各数据源详细评估

### 1. 富途 OpenAPI (Futu OpenD)

**状态**: ✅ 已连接 (模拟盘)

| 项目 | 状态 | 说明 |
|------|------|------|
| 连接状态 | ✅ | OpenD 已运行，端口 11111 |
| 行情接口 | ✅ | 支持港股/美股/A 股 |
| 交易接口 | 🟡 | 模拟盘密码待配置 |
| 数据品质 | ⭐⭐⭐⭐⭐ | 交易所级别数据 |

**支持的市场**:
- 港股 (HK) - 完整支持
- 美股 (US) - 完整支持
- A 股 (SH/SZ) - 仅行情，不支持交易

**可用数据**:
- 实时行情 (报价、K 线)
- 成分股数据 (指数板块)
- 财务数据 (PE/PB 等)
- 模拟盘交易

**限制**:
- A 股仅能看行情，不能交易
- 模拟盘和实盘需切换配置

---

### 2. Tushare Pro

**状态**: 🟡 需要配置 Token

| 项目 | 状态 | 说明 |
|------|------|------|
| Token 配置 | ⚠️ | 需要 `TUSHARE_TOKEN` 环境变量 |
| 数据品质 | ⭐⭐⭐⭐ | 专业金融数据 |
| 覆盖范围 | ⭐⭐⭐⭐ | A 股为主，部分港美股 |
| 限流情况 | 中等 | 根据积分等级 |

**可用数据**:
- A 股日线行情
- 基本面指标 (PE/PB/PS 等)
- 财务数据
- 指数成分股

**建议**:
- 用于 A 股数据 P0 源
- 需确认 Token 积分等级

---

### 3. AkShare

**状态**: ✅ 已安装 (python3.11)

| 项目 | 状态 | 说明 |
|------|------|------|
| 安装状态 | ✅ | python3.11 环境 |
| 数据品质 | ⭐⭐⭐ | 免费开源数据 |
| 稳定性 | ⭐⭐⭐ | 依赖爬虫，可能不稳定 |
| 限流情况 | 低 | 免费但可能限 IP |

**可用数据**:
- A 股实时行情
- 技术指标计算
- 资金流向
- 宏观经济数据

**限制**:
- 需要 subprocess 调用 python3.11
- 数据质量依赖源网站

---

### 4. QuantaAlpha (Qlib)

**状态**: ✅ 因子数据可用

| 项目 | 状态 | 说明 |
|------|------|------|
| 数据位置 | ✅ | `quantaalpha-deep/data/qlib/` |
| 因子数量 | ✅ | 190 个因子库 |
| 数据品质 | ⭐⭐⭐⭐ | 经过 IC/IR 验证 |
| 更新频率 | 🟡 | 需要定期更新 |

**可用数据**:
- 190 个 Alpha 因子值
- 因子 IC/IR 分析
- 历史回测结果

---

### 5. TrendRadar

**状态**: 🟡 数据目录未找到

| 项目 | 状态 | 说明 |
|------|------|------|
| 数据目录 | ❌ | 未找到有效路径 |
| MCP 服务 | 🟡 | 运行状态未知 |
| 数据品质 | ⭐⭐ | 热点覆盖有限 |

**建议**:
- 降低优先级至 P2
- 主要依赖 Web Search 获取舆情

---

### 6. Web Search (Jina/Tavily)

**状态**: ✅ 已配置

| 项目 | 状态 | 说明 |
|------|------|------|
| Jina API | ✅ | 已配置 |
| Tavily | ✅ | 已配置 |
| 数据品质 | ⭐⭐⭐ | 依赖搜索质量 |
| 实时性 | ⭐⭐⭐⭐ | 最新新闻 |

---

## 📋 降级策略

### 数据降级流程

```
1. 尝试 P0 数据源
   ↓ 失败
2. 尝试 P1 数据源
   ↓ 失败
3. 尝试 P2 数据源
   ↓ 失败
4. 使用 P3 模拟数据 (明确标注 degraded)
```

### 数据质量标识

所有数据返回必须包含:

```python
{
    "data_source": "tushare|akshare|futu|degraded",
    "data_quality": "real|degraded",
    "warning": "⚠️ 降级数据提示 (仅 degraded 时)"
}
```

### 交易限制

| 数据质量 | 可用于 | 不可用于 |
|----------|--------|----------|
| real (富途/Tushare) | 模拟盘 + 实盘 | - |
| degraded (模拟/估计) | 分析参考 | 真实交易 |

---

## 🛠️ 数据源配置检查清单

### 富途 OpenD
- [x] OpenD 进程运行
- [x] 端口 11111 配置
- [ ] 交易密码配置 (`FUTU_PASSWORD`)
- [ ] 模拟盘账号确认

### Tushare
- [ ] Token 配置 (`TUSHARE_TOKEN`)
- [ ] 积分等级确认

### AkShare
- [x] python3.11 环境安装
- [x] 可用性测试

### QuantaAlpha
- [x] Qlib 数据目录存在
- [ ] 因子数据更新

---

## 📊 市场覆盖总结

| 市场 | 行情 | 基本面 | 交易 | 选股 |
|------|------|--------|------|------|
| 港股 | ✅ 富途 | ✅ 富途 | ✅ 富途模拟 | ✅ 富途 |
| 美股 | ✅ 富途 | ✅ 富途 | ✅ 富途模拟 | ✅ 富途 |
| A 股 | ✅ Tushare | ✅ Tushare | ❌ 不支持 | ✅ Tushare |

**策略**: 使用港股/美股进行全链路模拟交易验证 (富途支持模拟盘)

---

## 🔄 舆情数据整合方案

### 优先级调整

根据用户反馈，TrendRadar 不如预期强大，调整优先级:

```
P0: Web Search (Jina + Tavily) - 实时新闻搜索
P1: TrendRadar - 热点话题
P2: 模拟数据 - 降级方案
```

### 整合逻辑

```python
def get_combined_sentiment(symbol, company_name):
    # 1. 尝试 Web Search (实时新闻)
    web_news = web_search.search(f"{company_name} {symbol} 新闻 分析")

    # 2. 尝试 TrendRadar (热点话题)
    trend_topics = trendradar.get_related_topics(symbol)

    # 3. 综合评分
    if web_news and len(web_news) > 0:
        sentiment = analyze_sentiment(web_news)
        return {"score": sentiment, "source": "web_search"}
    elif trend_topics:
        return {"score": trend_topics.sentiment, "source": "trendradar"}
    else:
        return {"score": 0, "source": "mock", "warning": "降级数据"}
```

---

## 📈 后续优化方向

1. **数据质量监控**: 记录各数据源成功率，动态调整优先级
2. **缓存策略优化**: 行情数据 5 分钟，基本面数据 1 小时
3. **故障自动切换**: 数据源失败自动降级，记录告警
4. **数据对比验证**: 多数据源交叉验证数据准确性
