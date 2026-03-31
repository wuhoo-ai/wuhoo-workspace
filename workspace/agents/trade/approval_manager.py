#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易审批管理模块

支持渠道:
- DingTalk (已验证)
- WeChat (待验证)

功能:
1. 发送交易审批请求
2. 处理用户回复
3. 超时检查与自动处理
4. 审批记录持久化
"""

import os
import sys
import json
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# 审批记录存储目录
APPROVAL_DATA_DIR = Path(__file__).parent / "data" / "approvals"
APPROVAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 审批超时配置 (小时)
APPROVAL_TIMEOUT_HOURS = 24

# DingTalk 配置
DINGTALK_USER_ID = os.environ.get('DINGTALK_USER_ID', '01443329476136537748')


@dataclass
class ApprovalRecord:
    """审批记录"""
    approval_id: str
    created_at: str
    status: str  # pending/approved/rejected/expired/auto_executed
    market: str
    code: str
    name: str
    action: str  # BUY/SELL
    price: float
    position_ratio: float
    quantity: int
    amount: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""
    user_reply: Optional[str] = None
    replied_at: Optional[str] = None
    executed_at: Optional[str] = None
    modified_position_ratio: Optional[float] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ApprovalRecord':
        return cls(**data)


class ApprovalManager:
    """审批管理器"""

    def __init__(self):
        self.data_file = APPROVAL_DATA_DIR / "pending_approvals.json"
        self.history_file = APPROVAL_DATA_DIR / "approval_history.jsonl"
        self.pending: Dict[str, ApprovalRecord] = self._load_pending()

    def _load_pending(self) -> Dict[str, ApprovalRecord]:
        """加载待审批列表"""
        if not self.data_file.exists():
            return {}
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {k: ApprovalRecord.from_dict(v) for k, v in data.items()}
        except Exception as e:
            print(f"加载待审批列表失败：{e}")
            return {}

    def _save_pending(self):
        """保存待审批列表"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump({k: v.to_dict() for k, v in self.pending.items()}, f, ensure_ascii=False, indent=2)

    def _append_history(self, record: ApprovalRecord):
        """追加审批历史"""
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + '\n')

    def generate_approval_id(self, market: str) -> str:
        """生成审批 ID"""
        date_str = datetime.now().strftime("%Y%m%d")
        # 计算今日序号
        today_count = sum(1 for r in self.pending.values() if r.created_at.startswith(date_str))
        today_count += self._get_history_count_today(date_str)
        return f"APV{date_str}{today_count + 1:03d}_{market.upper()}"

    def _get_history_count_today(self, date_str: str) -> int:
        """获取今日历史审批数量"""
        if not self.history_file.exists():
            return 0
        count = 0
        with open(self.history_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if data.get('created_at', '').startswith(date_str):
                        count += 1
        return count

    def send_approval(self, recommendation: Dict, market: str = "HK") -> Dict:
        """
        发送交易审批请求

        Args:
            recommendation: 投资建议
                {code, name, action, price, position_ratio, confidence, reason, bull_points, bear_points}
            market: 市场 (CN/HK/US)

        Returns:
            {approval_id, status, sent_at}
        """
        # 生成审批 ID
        approval_id = self.generate_approval_id(market)

        # 计算交易细节
        price = recommendation.get('price', 0.0)
        position_ratio = recommendation.get('position_ratio', 0.05)

        # 估算仓位金额 (假设总资金 100 万)
        total_capital = 1000000
        amount = total_capital * position_ratio
        quantity = int(amount / price) if price > 0 else 0

        # 计算止盈止损
        if price > 0:
            stop_loss = price * 0.92  # -8%
            take_profit = price * 1.20  # +20%
        else:
            stop_loss = take_profit = 0.0

        # 创建审批记录
        record = ApprovalRecord(
            approval_id=approval_id,
            created_at=datetime.now().isoformat(),
            status="pending",
            market=market,
            code=recommendation.get('code', ''),
            name=recommendation.get('name', ''),
            action=recommendation.get('action', 'BUY'),
            price=price,
            position_ratio=position_ratio,
            quantity=quantity,
            amount=amount,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=recommendation.get('reason', ''),
        )

        # 生成审批消息
        message = self._generate_approval_message(record)

        # 发送消息
        success = self._send_message(message)

        if success:
            # 保存到待审批列表
            self.pending[approval_id] = record
            self._save_pending()

            print(f"✅ 审批请求已发送：{approval_id}")
            return {
                "approval_id": approval_id,
                "status": "pending",
                "sent_at": datetime.now().isoformat()
            }
        else:
            print(f"❌ 消息发送失败")
            return {
                "approval_id": approval_id,
                "status": "failed",
                "error": "消息发送失败"
            }

    def _generate_approval_message(self, rec: ApprovalRecord) -> str:
        """生成审批消息"""

        # 计算数量显示
        if rec.market.upper() == 'US':
            qty_str = f"{rec.quantity} 股"
        elif rec.market.upper() == 'HK':
            qty_str = f"{rec.quantity} 股"
        else:  # CN
            qty_str = f"{rec.quantity} 股 (1 手={int(rec.quantity/100)} 手)" if rec.quantity >= 100 else f"{rec.quantity} 股"

        # 构建多空观点摘要
        bull_bear_summary = rec.reason if rec.reason else "基于因子分析和多空辩论"

        message = f"""【📊 交易确认】

📈 股票：{rec.code} {rec.name}
🔹 操作：{rec.action}
💰 价格：{rec.price:.2f} {self._get_currency(rec.market)}
📦 数量：{qty_str}
📊 仓位：{rec.position_ratio*100:.1f}%
💵 金额：{rec.amount:,.2f} {self._get_currency(rec.market)}

🛡️ 止损：{rec.stop_loss:.2f} ({(rec.stop_loss/rec.price-1)*100:.1f}%)
🎯 止盈：{rec.take_profit:.2f} ({(rec.take_profit/rec.price-1)*100:.1f}%)

📋 理由：
{bull_bear_summary}

─────────────────
⏰ 请在 24 小时内回复：
• 「确认」执行交易
• 「取消」拒绝交易
• 「3%」修改仓位比例"""

        return message

    def _get_currency(self, market: str) -> str:
        """获取市场对应货币符号"""
        market = market.upper()
        if market == 'CN':
            return 'CNY'
        elif market == 'HK':
            return 'HKD'
        elif market == 'US':
            return 'USD'
        return ''

    def _send_message(self, message: str) -> bool:
        """发送消息到 DingTalk"""
        try:
            # 使用 notify.py 脚本发送
            notify_script = Path.home() / '.openclaw' / 'scripts' / 'notify.py'
            if not notify_script.exists():
                print(f"notify.py 不存在：{notify_script}")
                return False

            result = subprocess.run(
                ["python3", str(notify_script), message],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            if result.returncode == 0:
                return True
            else:
                stderr = result.stderr.decode('utf-8') if result.stderr else ""
                print(f"发送失败：{stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("发送超时")
            return False
        except Exception as e:
            print(f"发送异常：{e}")
            return False

    def handle_reply(self, user_reply: str, approval_id: str = None) -> Dict:
        """
        处理用户回复

        Args:
            user_reply: 用户回复内容
            approval_id: 审批 ID (可选，如果从消息解析则不需要)

        Returns:
            {action: "approve"/"reject"/"modify"/"error", approval_id, ...}
        """
        reply = user_reply.strip()

        # 尝试从回复中提取 approval_id (如果用户引用了消息)
        if not approval_id:
            match = re.search(r'APV\d+_\w+', reply)
            if match:
                approval_id = match.group()
                reply = reply.replace(approval_id, '').strip()
            else:
                # 默认使用最新的待审批
                if self.pending:
                    approval_id = list(self.pending.keys())[-1]
                else:
                    return {"action": "error", "message": "未找到待审批记录"}

        # 验证 approval_id
        if approval_id not in self.pending:
            return {"action": "error", "message": f"审批 ID 不存在：{approval_id}"}

        record = self.pending[approval_id]
        reply_lower = reply.lower()

        # 确认
        if reply_lower in ['确认', 'confirm', 'yes', 'y', '同意', 'execute', '执行']:
            record.status = 'approved'
            record.user_reply = reply
            record.replied_at = datetime.now().isoformat()
            self._move_to_history(record)
            del self.pending[approval_id]
            self._save_pending()

            return {
                "action": "approve",
                "approval_id": approval_id,
                "record": record
            }

        # 取消
        elif reply_lower in ['取消', 'cancel', 'no', 'n', '拒绝', 'reject']:
            record.status = 'rejected'
            record.user_reply = reply
            record.replied_at = datetime.now().isoformat()
            self._move_to_history(record)
            del self.pending[approval_id]
            self._save_pending()

            return {
                "action": "reject",
                "approval_id": approval_id,
                "record": record
            }

        # 修改仓位
        else:
            # 尝试解析仓位比例 (如 "3%", "0.03", "3")
            position_ratio = self._parse_position_ratio(reply)
            if position_ratio:
                if position_ratio > 1:  # 如输入 3 代表 3%
                    position_ratio = position_ratio / 100
                if position_ratio > 1:  # 超过 100% 无效
                    return {"action": "error", "message": "仓位比例无效，请输入 0-100 之间的数字"}

                record.status = 'approved'
                record.user_reply = reply
                record.replied_at = datetime.now().isoformat()
                record.modified_position_ratio = position_ratio
                self._move_to_history(record)
                del self.pending[approval_id]
                self._save_pending()

                return {
                    "action": "modify",
                    "approval_id": approval_id,
                    "new_position_ratio": position_ratio,
                    "record": record
                }
            else:
                return {
                    "action": "error",
                    "message": "无法识别回复，请回复「确认」「取消」或仓位比例（如「3%」）"
                }

    def _parse_position_ratio(self, reply: str) -> Optional[float]:
        """解析仓位比例"""
        # 尝试百分比格式 (3%, 5.5%, etc)
        match = re.match(r'^(\d+(?:\.\d+)?)\s*%$', reply)
        if match:
            return float(match.group(1)) / 100

        # 尝试小数格式 (0.03, 0.05, etc)
        match = re.match(r'^(\d+(?:\.\d+)?)$', reply)
        if match:
            value = float(match.group(1))
            if value < 1:
                return value
            elif value <= 100:
                return value / 100

        return None

    def _move_to_history(self, record: ApprovalRecord):
        """将审批记录移到历史"""
        self._append_history(record)

    def check_timeout_approvals(self) -> List[ApprovalRecord]:
        """
        检查超时审批

        Returns:
            超时的审批记录列表
        """
        timeout_records = []
        now = datetime.now()

        for approval_id, record in list(self.pending.items()):
            created_at = datetime.fromisoformat(record.created_at)
            age_hours = (now - created_at).total_seconds() / 3600

            if age_hours > APPROVAL_TIMEOUT_HOURS:
                # 超时处理
                if record.action == 'SELL':
                    # 卖出超时，自动执行
                    record.status = 'auto_executed'
                    record.executed_at = now.isoformat()
                    print(f"⚠️  卖出审批超时，自动执行：{approval_id}")
                else:
                    # 买入超时，标记过期
                    record.status = 'expired'
                    print(f"⚠️  买入审批超时，已过期：{approval_id}")

                self._move_to_history(record)
                del self.pending[approval_id]
                timeout_records.append(record)

        if timeout_records:
            self._save_pending()

        return timeout_records

    def get_pending_count(self) -> int:
        """获取待审批数量"""
        return len(self.pending)

    def get_pending_list(self) -> List[ApprovalRecord]:
        """获取待审批列表"""
        return list(self.pending.values())

    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        """获取审批记录"""
        return self.pending.get(approval_id)


# ============= 与 Workflow C 集成的函数 =============

def send_trade_approval(recommendation: Dict, market: str = "HK") -> Dict:
    """
    发送交易审批 (Workflow C 调用)

    Args:
        recommendation: 投资建议
        market: 市场

    Returns:
        审批结果
    """
    manager = ApprovalManager()
    return manager.send_approval(recommendation, market)


def wait_for_approval(approval_id: str, timeout_minutes: int = 60, poll_interval: int = 30) -> Dict:
    """
    等待审批结果 (轮询模式)

    Args:
        approval_id: 审批 ID
        timeout_minutes: 超时时间 (分钟)
        poll_interval: 轮询间隔 (秒)

    Returns:
        审批结果
    """
    import time

    manager = ApprovalManager()
    start_time = datetime.now()

    while True:
        # 检查是否超时
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        if elapsed > timeout_minutes:
            return {"status": "timeout", "approval_id": approval_id}

        # 检查待审批列表
        record = manager.get_approval(approval_id)
        if record is None:
            # 记录不存在，可能已被处理
            # 检查历史文件
            if manager.history_file.exists():
                with open(manager.history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        data = json.loads(line)
                        if data.get('approval_id') == approval_id:
                            return {
                                "status": "completed",
                                "action": data.get('status'),
                                "approval_id": approval_id,
                                "modified_position_ratio": data.get('modified_position_ratio'),
                                "record": ApprovalRecord.from_dict(data)
                            }
            return {"status": "unknown", "approval_id": approval_id}

        # 检查是否已回复
        if record.replied_at:
            if record.status == 'approved':
                return {
                    "status": "approved",
                    "approval_id": approval_id,
                    "modified_position_ratio": record.modified_position_ratio,
                    "record": record
                }
            elif record.status == 'rejected':
                return {"status": "rejected", "approval_id": approval_id, "record": record}

        # 等待下一次轮询
        time.sleep(poll_interval)


if __name__ == "__main__":
    # 测试
    manager = ApprovalManager()

    # 测试发送审批
    test_rec = {
        "code": "HK.00700",
        "name": "腾讯控股",
        "action": "BUY",
        "price": 300.0,
        "position_ratio": 0.05,
        "reason": "多头观点：BUY (置信度 0.75)",
        "confidence": 0.75
    }

    result = manager.send_approval(test_rec, "HK")
    print(f"审批结果：{result}")
