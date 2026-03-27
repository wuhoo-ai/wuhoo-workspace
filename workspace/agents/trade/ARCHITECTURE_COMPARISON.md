# 交易架构对比分析：VnPy vs 直接富途 API

**日期**: 2026-03-27
**目的**: 评估是否回退到直接富途 API，弃用 VnPy

---

## 执行摘要

**建议：回退到直接富途 API，弃用 VnPy**

原因：
1. VnPy 需要补丁才能支持 A 股/美股，维护成本高
2. 直接 API 方案简单、直接、可控
3. 当前业务场景不需要 VnPy 的事件驱动特性
4. 混合方案增加复杂度，不利于长期维护

---

## 架构方案对比

### 方案 A: 直接富途 API (当前备份方案)

```
┌─────────────────────────────────────────────────────┐
│  workflow_c_multi_market.py                         │
├─────────────────────────────────────────────────────┤
│  step5_execute_trades()                             │
│    ├─ CN: OpenCNTradeContext.place_order()          │
│    ├─ HK: OpenHKTradeContext.place_order()          │
│    └─ US: OpenUSTradeContext.place_order()          │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │   富途 OpenD (127.0.0.1:11111) │
         └────────────────────────────────┘
```

**优点**:
- ✅ 简单直接，无依赖
- ✅ 每个市场独立控制，账户隔离清晰
- ✅ 无需补丁，官方 API 稳定
- ✅ 代码易于理解和维护
- ✅ 新人上手快

**缺点**:
- ❌ 无事件驱动（实际交易场景影响有限）
- ❌ 需要分别管理多个交易上下文
- ❌ 无统一持仓视图（需要自行聚合）

---

### 方案 B: VnPy + vnpy_futu (当前尝试方案)

```
┌─────────────────────────────────────────────────────┐
│  workflow_c_multi_market.py                         │
├─────────────────────────────────────────────────────┤
│  step5_execute_trades()                             │
│    ├─ CN: _execute_cn_trades_direct() ← 直接 API   │
│    └─ HK: _execute_hk_trades_vnpy() ← VnPy         │
└─────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
┌─────────────────────┐   ┌─────────────────────────┐
│  OpenCNTradeContext │   │  VnPy MainEngine        │
│  (直接 API)         │   │  └─ FutuGateway         │
└─────────────────────┘   │     └─ TradeContext     │
                          └─────────────────────────┘
```

**优点**:
- ✅ 事件驱动，订单状态自动推送
- ✅ 统一接口设计（理论上）
- ✅ 有持仓管理和账户视图

**缺点**:
- ❌ 需要补丁支持 A 股/美股（维护负担）
- ❌ 混合方案增加代码复杂度
- ❌ 学习曲线陡峭
- ❌ 账户隔离问题未解决
- ❌ 依赖 vnpy_futu 社区更新

---

### 方案 C: 纯 VnPy (理想方案，未实现)

```
┌─────────────────────────────────────────────────────┐
│  workflow_c_multi_market.py                         │
├─────────────────────────────────────────────────────┤
│  step5_execute_trades()                             │
│    └─ trader.place_order() ← 统一接口              │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │  VnPy MainEngine               │
         │  ├─ FutuGateway (HK)           │
         │  ├─ FutuGateway (CN) ← 需开发  │
         │  └─ FutuGateway (US) ← 需开发  │
         └────────────────────────────────┘
```

**状态**: 需要开发多网关支持，工作量大

---

## 技术债务清单

### VnPy 方案需要维护的补丁

| 补丁文件 | 修改内容 | 维护成本 |
|---------|---------|---------|
| `patch_vnpy_ashare.py` | 添加 A 股交易所映射 (SSE/SZSE) | 中 |
| `patch_vnpy_us.py` | 添加美股交易所映射 (NASDAQ/NYSE) | 中 |
| 网关多账户支持 | 支持同时连接 HK/CN/US 账户 | 高 |

**风险**: 每次 vnpy_futu 升级都需要重新应用补丁

---

## 业务场景分析

### Workflow C 交易流程需求

```
选股 → 分析 → 辩论 → 风控 → 交易 → 持仓监控
```

**交易环节需求**:
1. 下单执行 (BUY/SELL)
2. 订单状态查询
3. 持仓查询
4. 止盈止损设置

**VnPy 提供的额外价值**:
- 事件驱动订单推送 → 非必需（可轮询）
- 统一持仓视图 → 非必需（可自行聚合）
- 技术分析和因子框架 → 已在选股/分析环节实现

**结论**: VnPy 的核心价值在当前 Workflow C 中利用率低

---

## 代码复杂度对比

### 直接 API 方案

```python
# 港股下单
from futu import OpenHKTradeContext, TrdSide

ctx = OpenHKTradeContext(host='127.0.0.1', port=11111)
ctx.place_order(
    code='HK.00700',
    price=300.0,
    qty=100,
    trd_side=TrdSide.BUY,
    acc_id=18767294
)
ctx.close()
```

**代码行数**: ~10 行
**依赖**: futu-api
**理解难度**: ⭐⭐ (初级 Python 开发者)

---

### VnPy 方案

```python
# 港股下单
from vnpy_futu_skill import FutuTrader

trader = FutuTrader(market='HK', env='SIMULATE')
trader.connect()
trader.place_order(
    code='HK.00700',
    action='BUY',
    price=300.0,
    volume=100
)
```

**代码行数**: ~8 行
**依赖**: vnpy, vnpy_futu, + 补丁
**理解难度**: ⭐⭐⭐⭐ (需要了解 VnPy 架构)

---

## 维护成本估算

| 项目 | 直接 API | VnPy 方案 |
|------|---------|----------|
| 初始开发 | 1 天 | 3 天 |
| 补丁维护 | 0 | 2 天/月 |
| 新人培训 | 1 小时 | 4 小时 |
| 故障排查 | 简单 | 复杂 |
| 依赖升级风险 | 低 | 高 |

---

## 迁移建议

### 推荐方案：回退到直接富途 API

**迁移步骤**:

1. **清理 VnPy 依赖**
   ```bash
   # 保留 vnpy_futu_skill.py 作为参考
   # 移除 workflow_c_multi_market.py 中的 VnPy 调用
   ```

2. **统一直接 API 接口**
   ```python
   # 重构为统一的市场适配器模式
   class FutuTradeAdapter:
       def place_order(self, code, action, price, qty):
           if code.startswith('SH.') or code.startswith('SZ.'):
               return self._cn_place_order(...)
           elif code.startswith('HK.'):
               return self._hk_place_order(...)
           elif code.startswith('US.'):
               return self._us_place_order(...)
   ```

3. **文档更新**
   - 更新 `PRICE_DATA_STRATEGY.md`
   - 更新 `AUTOMATION_PIPELINE.md`
   - 移除 VnPy 相关文档

**预计工作量**: 0.5 天

---

### 备选方案：保留 VnPy 用于特定场景

如果未来有以下需求，可考虑保留 VnPy：

1. **高频交易需求** - 事件驱动低延迟
2. **多账户组合管理** - 统一持仓视图
3. **复杂衍生品交易** - VnPy 的期权/期货支持
4. **量化策略回测** - VnPy 的回测框架

**当前 Workflow C 不需要以上功能**

---

## 决策矩阵

| 评估维度 | 直接 API | VnPy | 权重 |
|---------|---------|------|------|
| 开发效率 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 25% |
| 维护成本 | ⭐⭐⭐⭐⭐ | ⭐⭐ | 25% |
| 功能满足 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 20% |
| 学习曲线 | ⭐⭐⭐⭐⭐ | ⭐⭐ | 15% |
| 扩展性 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 15% |
| **加权得分** | **4.4** | **2.6** | - |

---

## 最终建议

### ✅ 推荐：回退到直接富途 API

**理由**:
1. 简单就是美 - 少依赖、少补丁、少问题
2. 业务匹配 - Workflow C 不需要 VnPy 的高级特性
3. 维护友好 - 新人易上手，故障易排查
4. 成本最优 - 开发和运维成本都更低

### 后续行动

1. 移除 `workflow_c_multi_market.py` 中的 VnPy 代码
2. 统一为直接 API 的适配器模式
3. 更新文档，说明架构决策
4. 保留 `vnpy_futu_skill.py` 作为未来参考

---

## 附录：测试记录

### A 股测试 (直接 API)
```
✅ 下单成功 - 订单 ID: 7548850
代码：SH.603220 中贝通信
价格：24.1 CNY, 数量：100 股
```

### 港股测试 (VnPy)
```
✅ 下单成功 - 订单 ID: FUTU.7548855
代码：HK.00700 腾讯控股
价格：501.57 HKD, 数量：100 股
状态：FILLED_ALL
```

### 美股测试 (VnPy - 补丁后)
```
待验证 - 需要美股模拟账户
```

---

**结论**: 基于当前业务需求和技术评估，建议回退到直接富途 API 方案。
