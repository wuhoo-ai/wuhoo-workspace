# WeChat 审批流程设计

**版本**: v1.0
**创建时间**: 2026-03-26
**状态**: 待实现

---

## 📋 需求确认

- **渠道**: OpenClaw-Weixin
- **大额阈值**: 15% 仓位
- **买入超时**: 不处理（等待用户主动确认）
- **卖出超时**: 自动处理（安全第一）

---

## 🎯 设计方案（方案 A - 回复关键词）

### 审批消息格式

```
【交易确认】

股票：HK.00700 腾讯控股
操作：买入
价格：300.00 HKD
数量：100 股
仓位：5.0%
金额：30,000.00 HKD

止损：276.00 (-8.0%)
止盈：360.00 (+20.0%)

理由：
- 多头观点：BUY (置信度 0.75)
- 空头观点：HOLD (置信度 0.45)
- Trader 决策：BUY (仓位 5%)
- 风控审批：APPROVE (风险评分 0.35)

---
回复「确认」执行交易
回复「取消」拒绝交易
回复仓位比例修改（如「3%」）
```

### 用户回复处理

| 回复 | 处理 |
|------|------|
| `确认` / `yes` / `y` | 执行交易 |
| `取消` / `no` / `n` | 拒绝交易，记录原因 |
| `3%` / `0.03` | 修改仓位后执行 |
| 超时（24 小时） | 买入-不处理，卖出-自动执行 |

---

## 🔧 实现代码

### 审批发送函数

```python
def send_wechat_approval(recommendation: Dict) -> Dict:
    """
    发送 WeChat 审批请求

    Args:
        recommendation: 投资建议
            {code, name, action, price, position_ratio,
             stop_loss, take_profit, needs_approval, reason}

    Returns:
        approval_id, status
    """
    # 生成审批消息
    message = generate_approval_message(recommendation)

    # 通过 WeChat 插件发送
    approval_id = generate_approval_id()

    # 保存到待审批列表
    save_pending_approval(approval_id, recommendation)

    # 发送消息
    send_to_wechat(message)

    return {
        "approval_id": approval_id,
        "status": "pending",
        "sent_at": datetime.now().isoformat()
    }
```

### 消息生成函数

```python
def generate_approval_message(rec: Dict) -> str:
    """生成审批消息"""

    message = f"""【交易确认】

股票：{rec['code']} {rec['name']}
操作：{rec['action']}
价格：{rec['price']:.2f} HKD
数量：{calculate_volume(rec['price'], rec['position_ratio'])} 股
仓位：{rec['position_ratio']*100:.1f}%
金额：{rec['price'] * calculate_volume(rec['price'], rec['position_ratio']):,.2f} HKD

止损：{rec['stop_loss']:.2f} ({(rec['stop_loss']/rec['price']-1)*100:.1f}%)
止盈：{rec['take_profit']:.2f} ({(rec['take_profit']/rec['price']-1)*100:.1f}%)

理由：
{rec['reason']}

---
回复「确认」执行交易
回复「取消」拒绝交易
回复仓位比例修改（如「3%」）
"""
    return message
```

### 回复处理函数

```python
def handle_wechat_reply(user_reply: str, approval_id: str) -> Dict:
    """
    处理用户回复

    Args:
        user_reply: 用户回复内容
        approval_id: 审批 ID

    Returns:
        {action: "approve"/"reject"/"modify", ...}
    """
    reply = user_reply.strip().lower()

    # 确认
    if reply in ['确认', 'yes', 'y', 'confirm']:
        return {"action": "approve", "approval_id": approval_id}

    # 取消
    elif reply in ['取消', 'no', 'n', 'cancel']:
        return {"action": "reject", "approval_id": approval_id}

    # 修改仓位
    else:
        # 尝试解析仓位比例
        position_ratio = parse_position_ratio(reply)
        if position_ratio:
            return {
                "action": "modify",
                "approval_id": approval_id,
                "new_position_ratio": position_ratio
            }
        else:
            return {
                "action": "error",
                "message": "无法识别回复，请回复「确认」「取消」或仓位比例（如「3%」）"
            }
```

---

## 📁 数据结构

### 审批记录

```json
{
  "approval_id": "APV20260326001",
  "created_at": "2026-03-26T10:30:00+08:00",
  "status": "pending",  // pending/approved/rejected/expired
  "recommendation": {
    "code": "HK.00700",
    "name": "腾讯控股",
    "action": "BUY",
    "price": 300.0,
    "position_ratio": 0.05,
    "stop_loss": 276.0,
    "take_profit": 360.0,
    "reason": "..."
  },
  "user_reply": null,
  "replied_at": null,
  "executed_at": null
}
```

---

## ⏰ 超时处理

```python
def check_timeout_approvals():
    """检查超时审批"""
    pending_approvals = get_pending_approvals()

    for approval in pending_approvals:
        age_hours = (datetime.now() - approval['created_at']).total_seconds() / 3600

        if age_hours > 24:
            if approval['recommendation']['action'] == 'SELL':
                # 卖出超时，自动执行
                execute_trade(approval['approval_id'])
                update_approval_status(approval['approval_id'], 'auto_executed')
            else:
                # 买入超时，标记为已过期
                update_approval_status(approval['approval_id'], 'expired')
```

---

## 🔗 与 Workflow C 集成

```python
# Workflow C Step 6: 人工确认
def step6_human_approval(recommendations: List[Dict]) -> List[Dict]:
    """人工确认环节"""

    approved_list = []

    for rec in recommendations:
        # 检查是否需要审批
        if rec.get('needs_approval'):
            # 发送 WeChat 审批
            approval_result = send_wechat_approval(rec)

            # 等待回复（轮询或回调）
            while True:
                status = check_approval_status(approval_result['approval_id'])

                if status['status'] == 'approved':
                    approved_list.append({
                        **rec,
                        'position_ratio': status.get('new_position_ratio', rec['position_ratio'])
                    })
                    break
                elif status['status'] == 'rejected':
                    print(f"{rec['code']} 已拒绝")
                    break
                elif status['status'] == 'expired':
                    if rec['action'] == 'SELL':
                        approved_list.append(rec)  # 卖出自动执行
                    break

                time.sleep(60)  # 每分钟检查一次
        else:
            # 无需审批，直接通过
            approved_list.append(rec)

    return approved_list
```

---

## 📝 待办事项

- [ ] 实现 WeChat 消息发送接口
- [ ] 实现回复处理回调
- [ ] 实现超时检查定时任务
- [ ] 与 Workflow C 集成测试
