# VnPy 迁移报告与混合方案说明

**日期**: 2026-03-27
**状态**: ✅ 混合方案已实现
**迁移范围**: `workflow_c_multi_market.py` Step 5 (交易执行)

---

## 执行摘要

本次迁移尝试将 Workflow C 的交易执行层从直接 Futu API 迁移到 VnPy + vnpy_futu 统一接口。

**测试结果**:
- ✅ 港股 (HK) - VnPy 完全支持，可正常使用
- ❌ A 股 (CN) - VnPy vnpy_futu 网关不支持 A 股交易账户隔离
- ✅ 混合方案 - 港股用 VnPy，A 股用直接 API

---

## 技术问题详述

### 1. VnPy 交易所映射缺失

**问题**: `vnpy_futu` 网关的 `EXCHANGE_VT2FUTU` 映射表缺少 A 股交易所定义

```python
# 原始映射 (vnpy_futu/futu_gateway.py)
EXCHANGE_VT2FUTU: Dict[Exchange, str] = {
    Exchange.SMART: "US",
    Exchange.SEHK: "HK",
    Exchange.HKFE: "HK_FUTURE",
}

# 已修复 (通过 patch_vnpy_ashare.py)
EXCHANGE_VT2FUTU: Dict[Exchange, str] = {
    Exchange.SMART: "US",
    Exchange.SEHK: "HK",
    Exchange.HKFE: "HK_FUTURE",
    Exchange.SSE: "SH",      # A 股上海
    Exchange.SZSE: "SZ",     # A 股深圳
}
```

**状态**: ✅ 已通过补丁修复

---

### 2. A 股交易账户隔离问题

**问题**: VnPy 网关使用单一市场连接，无法区分港股账户 (18767294) 和 A 股账户 (18767295)

**测试输出**:
```
2026-03-27 13:34:56.099 | INFO | FUTU | 委托失败：证券账户 18767294 不支持交易 SH.603220
```

**根本原因**:
- 富途 API 要求：A 股交易必须使用 `OpenCNTradeContext` 和账户 18767295
- VnPy 网关只使用单一交易上下文 (由 `market` 参数决定，如 `market='HK'`)
- vnpy_futu 网关没有为 A 股设计独立的交易上下文处理

**技术细节**:
```python
# VnPy 连接配置
gateway_setting = {
    "市场": "HK",  # 或 "US"、"SH"
    "环境": "SIMULATE"
}

# 问题：当 market='HK' 时，所有订单都通过 HK 账户执行
# A 股订单 (SH.603220) 会被路由到 HK 账户 18767294，导致失败
```

---

## 混合方案实现

### 设计决策

由于 VnPy 对 A 股支持的限制，采用**混合交易接口方案**:

| 市场 | 交易接口 | 账户 | 原因 |
|------|----------|------|------|
| **港股 (HK)** | VnPy + vnpy_futu | 18767294 | 完全支持，事件驱动 |
| **A 股 (CN)** | 直接 Futu API | 18767295 | 账户隔离要求 |
| **美股 (US)** | VnPy + vnpy_futu | - | 需要行情权限 |

### 代码结构

```python
# workflow_c_multi_market.py

def step5_execute_trades(self, recommendations: Dict) -> Dict:
    if self.market.lower() == 'cn':
        return self._execute_cn_trades_direct(recommendations, trade_results)
    elif self.market.lower() == 'hk':
        return self._execute_hk_trades_vnpy(recommendations, trade_results)

def _execute_cn_trades_direct(self, recommendations, trade_results):
    """A 股：使用 OpenCNTradeContext"""
    from futu import OpenCNTradeContext
    trade_ctx = OpenCNTradeContext(host='127.0.0.1', port=11111)
    acc_id = 18767295  # A 股账户
    time_in_force = 'DAY'
    # ...

def _execute_hk_trades_vnpy(self, recommendations, trade_results):
    """港股：使用 VnPy"""
    from vnpy_futu_skill import FutuTrader
    trader = FutuTrader(market='HK', env='SIMULATE')
    trader.connect()
    trader.place_order(code='HK.00700', action='BUY', price=300.0, volume=100)
    # ...
```

---

## 为什么 VnPy 不支持 A 股交易

### vnpy_futu 网关设计限制

1. **单一市场连接**: 网关在连接时指定 `market` 参数，决定使用哪个交易上下文
2. **账户绑定**: 交易上下文绑定特定账户 (HK 账户、US 账户等)
3. **无动态路由**: 订单发送时不会根据代码自动选择交易上下文

### 富途 OpenAPI 的账户模型

```
OpenD (127.0.0.1:11111)
├── OpenQuoteContext    # 行情上下文 (共享)
├── OpenHKTradeContext  # 港股交易 → 账户 18767294
├── OpenCNTradeContext  # A 股交易 → 账户 18767295
└── OpenUSTradeContext  # 美股交易 → 账户 18767296
```

VnPy 网关只连接一个交易上下文，无法同时支持多个账户。

---

## 混合方案的优缺点

### 优点

1. **实用性**: 立即可用，不阻塞 A 股和港股交易
2. **可维护性**: 代码清晰分离，便于调试
3. **向后兼容**: 保留已有 A 股直接 API 的成功经验
4. **渐进式迁移**: 为未来 VnPy 完全支持 A 股预留空间

### 缺点

1. **接口不统一**: 需要维护两套交易代码
2. **学习曲线**: 团队成员需要了解两种接口
3. **测试复杂度**: 需要分别测试两种接口

---

## 未来改进方向

### 方案 A: 扩展 VnPy 网关 (推荐)

修改 `vnpy_futu` 网关，支持多交易上下文:

```python
class MultiMarketFutuGateway(Gateway):
    def __init__(self):
        self.hk_context = OpenHKTradeContext(...)
        self.cn_context = OpenCNTradeContext(...)
        self.us_context = OpenUSTradeContext(...)

    def send_order(self, req):
        # 根据代码自动选择交易上下文
        if req.exchange == Exchange.SSE:
            return self.cn_context.place_order(...)
        elif req.exchange == Exchange.SEHK:
            return self.hk_context.place_order(...)
```

### 方案 B: 多网关实例

在 VnPy 中创建多个网关实例，每个市场一个:

```python
main_engine.add_gateway(FutuGateway)  # HK
main_engine.add_gateway(FutuGatewayCN)  # CN (需要新类)
```

### 方案 C: 等待官方支持

vnpy_futu 的未来版本可能会添加 A 股完整支持

---

## 相关文件修改

### 新增文件
- `patch_vnpy_ashare.py` - VnPy 网关 A 股补丁
- `test_vnpy_migration.py` - VnPy 迁移测试脚本
- `VNPY_MIGRATION_REPORT.md` - 本文档

### 修改文件
- `workflow_c_multi_market.py` - 实现混合交易方案
  - `step5_execute_trades()` - 主入口
  - `_execute_cn_trades_direct()` - A 股直接 API
  - `_execute_hk_trades_vnpy()` - 港股 VnPy

---

## 测试验证

### 港股测试 (VnPy)
```
✅ VnPy 连接成功
✅ 港股下单成功 - 订单 ID: FUTU.7548816
✅ 订单回调 - 00700 多 价格=300.0 数量=100.0 状态=未成交
```

### A 股测试 (直接 API)
```
✅ A 股连接成功 - 账户 18767295
✅ A 股下单成功 - 订单 ID: 7548820
✅ 订单状态 - SUBMITTED
```

---

## 结论

**混合方案是当前最优解**，原因：

1. A 股和港股交易都已验证可用
2. 不阻塞 Workflow C 的正常运行
3. 保留了 VnPy 在港股侧的事件驱动优势
4. 为未来技术演进留下空间

**建议**: 继续使用混合方案，同时关注 vnpy_futu 官方对 A 股支持的进展。

---

## 参考资源

- VnPy 文档：https://www.vnpy.com/docs/
- vnpy_futu 源码：`venv-futu/lib64/python3.11/site-packages/vnpy_futu/`
- 富途 OpenAPI: https://openapi.futunn.com/
- A 股交易报告：`CN_TRADE_FULL_CHAIN_REPORT.md`
