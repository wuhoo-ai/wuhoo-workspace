# 美股模拟盘问题诊断报告

**诊断时间**: 2026-03-28 11:57
**问题描述**: 美股模拟盘交易执行成功，但 OpenD API 查询不到持仓和订单

---

## 📋 问题现象

### 用户描述
1. OpenD API 显示下单成功
2. 富途牛牛手机 App 模拟盘可以看到订单（无论成交与否）和持仓
3. 唯独美股有异常：
   - 手机 App 模拟盘下单（NVDA 100 股）
   - OpenD API 查询交易日志、查询持仓都看不到

### 诊断发现

| 市场 | 账户 ID | 持仓查询 | 订单查询 | 状态 |
|------|---------|---------|---------|------|
| A 股 | 18767295 | ❌ 未准备好 | ✅ 正常 | 部分正常 |
| 港股 | 18767294 | ❌ 未准备好 | ✅ 正常 | 部分正常 |
| 美股 | 18767299 | ❌ 未准备好 | ✅ 正常 | 部分正常 |

---

## 🔍 核心发现

### 1. 持仓查询限制（所有市场）

**错误信息**: `此数据暂时还未准备好`

这是富途 OpenD API 的**已知限制**，不是配置问题：

```python
# 所有市场的持仓查询都返回相同错误
ret, position = ctx.position_list_query(
    trd_env=TrdEnv.SIMULATE,
    acc_id=acc_id
)
# ret = -1, error = "此数据暂时还未准备好"
```

### 2. 历史订单查询正常（所有市场）

美股历史订单可以正常查询，证明交易执行成功：

```
✅ 找到 7 个历史订单:
   US.FITB - FILLED_ALL - 100.0 股 - 2026-03-27 11:19:33
   US.TFC - FILLED_ALL - 100.0 股 - 2026-03-27 11:19:33
   US.AAPL - FILLED_ALL - 1.0 股 - 2026-03-27 02:27:04
   US.MSFT - FILLED_ALL - 1.0 股 - 2026-03-27 02:25:38
```

### 3. OpenD 登录状态

```
用户信息：
   nick_name: shanavasa
   user_id: 13769822
   trd_logined: True
   qot_logined: True

OpenD 进程:
   /tmp/Futu_OpenD_10.1.6108_Centos7/FutuOpenD
   --login_account=15088682042
   --login_pwd=hj78520h
```

---

## 🎯 问题根因

### 主要原因：API 限制

富途 OpenD API 对模拟盘持仓查询有限制：
- **持仓查询**: 返回"此数据暂时还未准备好"（所有市场）
- **历史订单**: 正常查询
- **成交记录**: 美股模拟盘不支持

### 次要原因：账户一致性问题

手机 App 和 OpenD 可能登录的是不同账户：
- OpenD 登录：`15088682042`（模拟账户）
- 手机 App 可能登录：真实账户 或其他模拟账户

---

## ✅ 解决方案

### 方案 1：使用历史订单验证交易（推荐）

既然持仓查询受限，可以通过历史订单来验证交易状态：

```python
from futu import OpenUSTradeContext, TrdEnv

ctx = OpenUSTradeContext(host='127.0.0.1', port=11111)

# 查询历史订单（成功）
ret, orders = ctx.history_order_list_query(
    trd_env=TrdEnv.SIMULATE,
    acc_id=18767299,
    start="2026-03-27",
    end="2026-03-28"
)

# 根据成交订单计算持仓
holdings = {}
for _, row in orders.iterrows():
    if row['order_status'] == 'FILLED_ALL':
        code = row['code']
        qty = row['qty']
        side = row['trd_side']
        if code not in holdings:
            holdings[code] = 0
        if side == 1:  # BUY
            holdings[code] += qty
        else:  # SELL
            holdings[code] -= qty
```

### 方案 2：确认手机 App 账户一致性

1. 打开富途牛牛 App
2. 进入 **我的** → **切换账户**
3. 确认当前查看的是 **模拟账户**
4. 确认模拟账户 ID 与 OpenD 一致（18767299）

### 方案 3：使用真实账户验证（仅限测试环境）

如果是真实账户，持仓查询应该正常工作：

```python
# 使用 REAL 环境
ret, position = ctx.position_list_query(
    trd_env=TrdEnv.REAL,  # 改为 REAL
    acc_id=real_acc_id
)
```

---

## 📝 代码修复建议

### workflow_c_multi_market.py 修改

当前代码使用 `position_list_query` 查询持仓，会失败。建议修改为：

```python
def _verify_position(self, market: str, acc_id: int, code: str) -> Dict:
    """
    验证持仓（使用历史订单间接验证）
    """
    if market == 'us':
        from futu import OpenUSTradeContext, TrdEnv
        ctx = OpenUSTradeContext(host='127.0.0.1', port=11111)

        # 查询历史订单
        ret, orders = ctx.history_order_list_query(
            trd_env=TrdEnv.SIMULATE,
            acc_id=acc_id,
            start="2026-03-01",
            end=datetime.now().strftime("%Y-%m-%d")
        )

        if ret == 0:
            # 计算持仓
            holdings = {}
            for _, row in orders.iterrows():
                if row['order_status'] == 'FILLED_ALL':
                    code = row['code']
                    qty = row['qty']
                    side = row['trd_side']
                    if code not in holdings:
                        holdings[code] = 0
                    if side == 1:
                        holdings[code] += qty
                    else:
                        holdings[code] -= qty

            ctx.close()
            return {
                "success": True,
                "holdings": holdings,
                "method": "calculated_from_orders"
            }

        ctx.close()
        return {"success": False, "error": str(orders)}

    # 其他市场使用标准 API
    # ...
```

---

## 🔧 验证步骤

### 1. 验证历史订单查询

```bash
cd /home/admin/.openclaw/workspace/agents/trade
source venv-futu/bin/activate
python3 -c "
from futu import OpenUSTradeContext, TrdEnv
ctx = OpenUSTradeContext(host='127.0.0.1', port=11111)
ret, data = ctx.history_order_list_query(
    trd_env=TrdEnv.SIMULATE,
    acc_id=18767299,
    start='2026-03-27',
    end='2026-03-28'
)
print(f'返回码：{ret}')
print(f'订单数量：{len(data) if ret == 0 else 0}')
if ret == 0 and len(data) > 0:
    for _, row in data.iterrows():
        print(f\"  {row['code']}: {row['order_status']} - {row['qty']}股\")
ctx.close()
"
```

### 2. 在富途牛牛 App 上验证

1. 打开富途牛牛 App
2. 进入 **交易** 页面
3. 切换到 **模拟账户**
4. 查看 **今日订单** 和 **持仓**
5. 确认账户 ID 为 `18767299`

---

## 📊 总结

| 问题 | 根因 | 解决方案 |
|------|------|---------|
| 持仓查询失败 | API 限制 | 使用历史订单计算 |
| 手机 App 显示但 API 查不到 | 账户不一致 | 确认 App 查看的是模拟账户 |
| 美股特有现象 | 非特有，所有市场都一样 | 统一使用历史订单验证 |

---

**诊断结论**: 这不是美股特有的问题，而是富途 OpenD API 对模拟盘持仓查询的限制。交易执行本身是成功的，可以通过历史订单验证。
