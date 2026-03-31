# 美股账户配置修复

**修复时间**: 2026-03-27 23:50
**问题**: 美股订单在 App 上看不到，但 A 股/港股显示正常

---

## 问题原因

1. **账户配置缺失**: `MARKET_CONFIG['us']` 没有配置固定的 `acc_id`
2. **动态获取账户**: 代码使用 `get_acc_list()` 获取第一个账户，导致账户不固定
3. **多账户混淆**: 美股模拟盘有两个账户：
   - `18767299` (ACTIVE, MARGIN) ← 实际使用的账户
   - `18767292` (ACTIVE, MARGIN)

## 修复内容

### 1. 配置固定账户

```python
MARKET_CONFIG = {
    'us': {
        'name': '美股 (Top 500)',
        'gateway': 'Futu OpenAPI',
        'acc_id': 18767299,  # 美股模拟账户 (固定配置)
        # ...
    },
}
```

### 2. 修改交易执行逻辑

**修改前**:
```python
elif self.market.lower() == 'us':
    # 美股账户需要动态获取
    return self._execute_trades_direct(
        recommendations, trade_results,
        market='us',
        acc_id=None,  # 动态获取
        time_in_force='DAY'
    )
```

**修改后**:
```python
elif self.market.lower() == 'us':
    # 使用配置的美股账户
    acc_id = self.config.get('acc_id')
    print(f"美股账户：{acc_id}")
    return self._execute_trades_direct(
        recommendations, trade_results,
        market='us',
        acc_id=acc_id,
        time_in_force='DAY'
    )
```

### 3. 移除动态获取账户逻辑

```python
# 删除了这段代码:
# if acc_id is None:
#     ret, data = trade_ctx.get_acc_list()
#     if ret == 0 and len(data) > 0:
#         acc_id = int(data['acc_id'].iloc[0])
#         print(f"自动获取账户 ID: {acc_id}")
#     else:
#         raise Exception("无法获取账户列表")
```

---

## 账户对比

| 市场 | 账户 ID | 类型 | 状态 |
|------|---------|------|------|
| A 股 | 18767295 | CASH | ACTIVE |
| 港股 | 18767294 | CASH | ACTIVE |
| 港股 | 18767296 | MARGIN | ACTIVE |
| **美股** | **18767299** | **MARGIN** | **ACTIVE** ← 使用此账户 |
| 美股 | 18767292 | MARGIN | ACTIVE |

---

## 在富途牛牛 App 上查看美股订单

### 方法 1: 切换账户

1. 打开富途牛牛 App
2. 进入 **交易** 页面
3. 点击顶部的 **账户选择器** (通常显示当前账户名称)
4. 在账户列表中找到 **账户 18767299** 或 **模拟账户 9**
5. 切换后查看：
   - **今日订单** → 应显示 TFC.US 和 FITB.US 的已成交订单
   - **持仓** → 应显示 TFC.US 和 FITB.US 各 100 股

### 方法 2: 查看所有账户

如果找不到账户 18767299，可能是因为：
- 账户名称被自定义修改过
- 需要在模拟账户列表中查找

请检查：
- **我的** → **切换账户** → **模拟账户**
- 查找有最近订单记录的账户

---

## 验证订单

```bash
source venv-futu/bin/activate
python3 << 'EOF'
from futu import OpenUSTradeContext, TrdEnv

trade_ctx = OpenUSTradeContext(host='127.0.0.1', port=11111)
acc_id = 18767299

# 查询订单
ret, data = trade_ctx.order_list_query(trd_env=TrdEnv.SIMULATE, acc_id=acc_id)
if ret == 0 and len(data) > 0:
    print(data[['code', 'stock_name', 'order_status', 'dealt_qty', 'dealt_avg_price']].to_string())
else:
    print(f'查询失败：{data}')

trade_ctx.close()
EOF
```

---

## 已成交订单

| 代码 | 名称 | 状态 | 数量 | 成交价 | 成交时间 |
|------|------|------|------|--------|----------|
| US.TFC | Truist Financial | FILLED_ALL | 100 | $44.58 | 2026-03-27 11:19:37 |
| US.FITB | Fifth Third Bancorp | FILLED_ALL | 100 | $44.93 | 2026-03-27 11:19:38 |

**总成交金额**: $8,951

---

## 后续建议

1. **统一账户命名**: 在富途牛牛中为模拟账户设置易识别的名称
2. **定期检查**: 运行 Workflow C 前确认账户配置正确
3. **文档更新**: 将美股账户 18767299 添加到 CLAUDE.md 或 SOUL.md 中

---

## 文件修改

- `workflow_c_multi_market.py`:
  - 第 61 行：添加 `'acc_id': 18767299`
  - 第 593-601 行：修改美股交易执行逻辑
  - 第 631 行：更新打印信息
  - 第 640-647 行：删除动态获取账户逻辑
