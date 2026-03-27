# VnPy-Futu-Trader Skill

**版本**: v2.0
**创建时间**: 2026-03-26
**状态**: ✅ 开发完成

---

## 📋 描述

基于 VnPy 框架和 vnpy_futu 接口，连接富途证券（模拟盘）执行量化交易。

**使用场景**:
- 执行买入/卖出订单
- 设置止盈止损
- 查询持仓/账户信息
- 订阅实时行情
- 订单状态跟踪

---

## 🔧 环境配置

### Python 虚拟环境

```bash
# 虚拟环境位置
~/.openclaw/workspace/agents/trade/venv-futu/

# Python 版本
Python 3.11+

# 依赖安装
source ~/.openclaw/workspace/agents/trade/venv-futu/bin/activate
pip install vnpy>=3.9.0
pip install vnpy-futu>=6.3.2808.0
pip install futu-api>=7.1.0
```

### 富途 OpenD 配置

1. **下载 OpenD**: https://www.futumm.com/OpenAPI
2. **启动 OpenD**:
   - 主机：`127.0.0.1`
   - 端口：`11111`
   - 市场：`HK` / `US` / `SH` / `SZ`
   - 环境：`SIMULATE` (模拟) / `REAL` (实盘)

3. **登录**:
   - 使用富途账号登录
   - 首次使用需完成 API 合规确认

### 环境变量

```bash
# ~/.openclaw/workspace/agents/trade/.env
FUTU_HOST=127.0.0.1
FUTU_PORT=11111
FUTU_MARKET=HK
FUTU_ENV=SIMULATE
FUTU_PASSWORD=xxx  # 加密存储
```

---

## 📡 API 接口

### 1. 连接富途

```python
from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine
from vnpy_futu import FutuGateway

def connect_futu(host="127.0.0.1", port=11111, market="HK", env="SIMULATE"):
    """连接富途交易接口"""
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(FutuGateway)

    # 连接配置
    gateway_setting = {
        "地址": f"{host}:{port}",
        "市场": market,
        "环境": env,
        "密码": get_password()  # 从加密存储获取
    }

    main_engine.connect(gateway_setting, "FUTU")
    return main_engine
```

### 2. 下单交易

```python
from vnpy.trader.object import OrderRequest, Direction, Offset, OrderType

def place_order(main_engine, code, action, price, volume, stop_loss=None, take_profit=None):
    """
    下单交易

    Args:
        code: 股票代码 (如 "603220.SH")
        action: "BUY" / "SELL"
        price: 限价价格
        volume: 数量
        stop_loss: 止损价 (可选)
        take_profit: 止盈价 (可选)

    Returns:
        dict: {order_id, status, message}
    """
    # 方向转换
    direction = Direction.BUY if action == "BUY" else Direction.SELL

    # 创建订单请求
    req = OrderRequest(
        symbol=code,
        exchange=parse_exchange(code),  # 解析交易所
        direction=direction,
        offset=Offset.OPEN,
        type=OrderType.LIMIT,
        price=price,
        volume=volume,
        reference="auto-trader"
    )

    # 发送订单
    vt_orderid = main_engine.send_order(req, "FUTU")

    # 设置止盈止损 (VnPy 3.9+ 支持)
    if stop_loss or take_profit:
        main_engine.write_log(f"设置止盈止损：stop_loss={stop_loss}, take_profit={take_profit}")

    return {
        "order_id": vt_orderid,
        "status": "SUBMITTED",
        "message": "订单已提交"
    }
```

### 3. 查询持仓

```python
def get_positions(main_engine):
    """查询当前持仓"""
    positions = main_engine.get_all_positions()

    result = []
    for pos in positions:
        if pos.volume > 0:
            result.append({
                "code": pos.symbol,
                "name": get_stock_name(pos.symbol),
                "volume": pos.volume,
                "avg_price": pos.price,
                "market_value": pos.volume * get_current_price(pos.symbol),
                "pnl": calculate_pnl(pos)
            })

    return result
```

### 4. 查询账户

```python
def get_account(main_engine):
    """查询账户信息"""
    account = main_engine.get_account("FUTU")

    if account:
        return {
            "balance": account.balance,
            "available": account.available,
            "frozen": account.frozen,
            "margin": account.margin
        }
    return None
```

### 5. 订阅实时行情

```python
from vnpy.trader.object import SubscribeRequest

def subscribe_quotes(main_engine, codes):
    """订阅实时行情"""
    for code in codes:
        req = SubscribeRequest(
            symbol=code,
            exchange=parse_exchange(code)
        )
        main_engine.subscribe(req, "FUTU")

    return {"subscribed": codes, "count": len(codes)}
```

### 6. 订单回调处理

```python
from vnpy.event import EVENT_ORDER

def on_order(event):
    """订单状态更新回调"""
    order = event.data

    log_message = f"订单更新：{order.symbol} {order.direction.value} " \
                  f"价格={order.price} 数量={order.volume} " \
                  f"状态={order.status.value}"

    # 发送到 DingTalk / WebChat
    send_notification(log_message)

    # 记录到日志
    write_trade_log({
        "timestamp": datetime.now().isoformat(),
        "event": "ORDER_UPDATE",
        "data": {
            "order_id": order.vt_orderid,
            "symbol": order.symbol,
            "status": order.status.value,
            "price": order.price,
            "volume": order.volume
        }
    })
```

---

## 📝 使用示例

### 示例 1: 买入股票

```python
# 输入
{
  "action": "execute_trade",
  "params": {
    "code": "603220.SH",
    "action": "BUY",
    "position_ratio": 0.03,
    "limit_price": 12.50,
    "stop_loss": 11.50,
    "take_profit": 14.00,
    "account": "SIMULATE"
  }
}

# 输出
{
  "success": true,
  "order_id": "VT20260325001",
  "filled_price": 12.48,
  "filled_volume": 300,
  "status": "FILLED",
  "stop_loss_set": 11.50,
  "take_profit_set": 14.00
}
```

### 示例 2: 查询持仓

```python
# 输入
{
  "action": "get_positions"
}

# 输出
{
  "positions": [
    {
      "code": "603220.SH",
      "name": "中贝通信",
      "volume": 300,
      "avg_price": 12.48,
      "current_price": 12.65,
      "market_value": 3795.00,
      "pnl": 51.00,
      "pnl_pct": 1.36
    }
  ],
  "total_value": 100000.00,
  "cash": 96205.00
}
```

### 示例 3: 设置止盈止损

```python
# 输入
{
  "action": "set_stop_loss_take_profit",
  "params": {
    "code": "603220.SH",
    "stop_loss": 11.50,
    "take_profit": 14.00
  }
}

# 输出
{
  "success": true,
  "message": "止盈止损已设置",
  "stop_loss": 11.50,
  "take_profit": 14.00
}
```

---

## ⚠️ 注意事项

### 安全

1. **密码管理**: 交易密码使用加密存储，不要明文写在代码中
2. **环境隔离**: 模拟盘和实盘使用不同的配置文件
3. **权限控制**: 实盘交易需要用户确认

### 风控

1. **仓位限制**: 单股票 ≤ 20% 总仓位
2. **止损纪律**: 触及止损线必须执行
3. **现金储备**: 保持 ≥ 10% 现金

### 技术

1. **OpenD 守护**: 确保 OpenD 进程持续运行
2. **网络重连**: 实现断线自动重连逻辑
3. **日志审计**: 所有交易操作记录留痕

---

## 🔗 相关文档

- [VnPy 官方文档](https://www.vnpy.com/docs/)
- [vnpy_futu GitHub](https://github.com/veighna-global/vnpy_futu)
- [富途 OpenAPI 文档](https://openapi.futumm.com/futu-api-doc/)
- [全链路 Pipeline](~/openclaw/workspace/agents/trade/AUTOMATION_PIPELINE.md)

---

## 📋 开发清单

- [x] 创建 Python 虚拟环境 (2026-03-25)
- [x] 安装 VnPy + vnpy_futu (2026-03-25)
- [x] 创建安装测试脚本 (2026-03-25)
- [x] 配置富途 OpenD (2026-03-26)
- [x] 测试模拟盘连接 (2026-03-26)
- [x] 实现下单接口 (2026-03-26)
- [x] 实现持仓查询 (2026-03-26)
- [x] 实现止盈止损 (2026-03-26)
- [ ] 集成风控检查
- [ ] 添加日志记录
- [ ] 测试完整链路
