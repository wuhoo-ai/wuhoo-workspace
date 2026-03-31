# A 股通交易权限配置指南

**更新时间**: 2026-03-27
**状态**: ⚠️ 需要开通 A 股行情权限

---

## 问题诊断

### 当前账户状态

| 账户类型 | 账户 ID | 市场环境 | 状态 | 权限 |
|----------|---------|----------|------|------|
| A 股交易账户 | 18767295 | SIMULATE | ACTIVE | `[CN]` ✅ |
| 港股交易账户 | 18767294 | SIMULATE | ACTIVE | `[HK]` ✅ |
| 沪股通账户 | 281756468881005662 | REAL | DISABLED | `[HKCC]` ❌ |

### 测试结果

| 测试项目 | 结果 | 说明 |
|----------|------|------|
| A 股交易账户存在 | ✅ | 账户 18767295 可用 |
| A 股行情获取 | ❌ | "无权限获取 SH.603220 的行情" |
| A 股下单 | ❌ | 依赖行情数据获取 |

---

## 需要在富途牛牛 APP 开通的权限

### 1. A 股行情权限 (必需)

**路径**: 富途牛牛 APP → 我的 → 个人中心 → 行情权限

需要开通：
- ☑️ **A 股实时行情** (免费)
- ☑️ **沪深 Level-1 行情** (免费)

### 2. A 股通交易权限 (已开通)

**路径**: 富途牛牛 APP → 交易 → A 股通 → 设置

状态：✅ 已开通

---

## 开通后验证步骤

```bash
cd /home/admin/.openclaw/workspace/agents/trade
source venv-futu/bin/activate

# 测试 A 股行情
python3 << 'EOF'
from futu import OpenQuoteContext, RET_OK

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

# 测试几个 A 股股票
test_stocks = ['SH.603220', 'SZ.000001', 'SH.600000']
for code in test_stocks:
    ret, data = quote_ctx.get_market_snapshot(code)
    if ret == RET_OK:
        print(f"✅ {code}: OK - 最新价 {data['last_price'].iloc[0]}")
    else:
        print(f"❌ {code}: {data}")

quote_ctx.close()
EOF
```

---

## Workflow C A 股交易修正

### 代码修改点

当前代码使用 `OpenHKTradeContext` 交易 A 股，需要修改为 `OpenCNTradeContext`：

**文件**: `workflow_c_multi_market.py`

```python
# 修改前 (错误)
from futu import OpenHKTradeContext
trade_ctx = OpenHKTradeContext(host='127.0.0.1', port=11111)
trade_ctx.place_order(code='SH.603220', ...)  # 失败

# 修改后 (正确)
from futu import OpenCNTradeContext
trade_ctx = OpenCNTradeContext(host='127.0.0.1', port=11111)
trade_ctx.place_order(code='SH.603220', ...)  # 成功
```

---

## A 股交易注意事项

### 1. 股票代码格式
- ✅ 正确：`SH.603220` (富途格式)
- ❌ 错误：`603220.SH` (标准格式)

### 2. 最小交易单位
- A 股最小交易单位：**100 股** (1 手)
- 必须是 100 的整数倍

### 3. 交易时间
- 上午：9:30 - 11:30
- 下午：13:00 - 15:00
- 非交易时间下单会进入待成交状态

### 4. 交易规则
- T+1 交易 (当日买入次日才能卖出)
- 涨跌幅限制：±10% (科创板/创业板 ±20%)
- 无做空机制 (普通账户)

---

## 下一步

1. **在富途牛牛 APP 开通 A 股行情权限** (5 分钟)
2. **重新运行验证脚本** 确认行情权限正常
3. **修改 Workflow C 代码** 使用 OpenCNTradeContext
4. **测试 A 股模拟盘交易**

---

## 相关文件

- 账户权限检查脚本：`workspace/agents/trade/scripts/check_ashare_permissions.py`
- Workflow C 多市场版：`workflow_c_multi_market.py`
- 港股交易报告：`TRADE_EXECUTION_REPORT.md`
