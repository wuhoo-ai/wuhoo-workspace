#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-Trader Integration - 与 AI-Trader 系统集成

将辩论结果传递给 AI-Trader 执行交易。
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class AITraderIntegration:
    """
    AI-Trader 集成器
    
    功能:
    - 将辩论结果转换为 AI-Trader 格式
    - 调用 AI-Trader 执行交易
    - 同步持仓状态
    """
    
    def __init__(self, ai_trader_path: Optional[str] = None):
        """
        初始化
        
        Args:
            ai_trader_path: AI-Trader 项目路径
        """
        if ai_trader_path is None:
            possible_paths = [
                Path.home() / ".openclaw/workspace/projects/AI-Trader",
                Path("/home/admin/.openclaw/workspace/projects/AI-Trader")
            ]
            
            for path in possible_paths:
                if path.exists():
                    self.ai_trader_path = path
                    break
            else:
                self.ai_trader_path = None
        
        self.position_file = None
        if self.ai_trader_path:
            # AI-Trader 持仓文件路径
            self.position_file = self.ai_trader_path / "data/agent_data/trade-agent/position/position.jsonl"
    
    def is_available(self) -> bool:
        """检查 AI-Trader 是否可用"""
        return self.ai_trader_path is not None and self.ai_trader_path.exists()
    
    def execute_trade(self, debate_record: Dict, approval_result: Dict) -> Dict:
        """
        执行交易
        
        Args:
            debate_record: 完整辩论记录
            approval_result: Portfolio Manager 审批结果
        
        Returns:
            执行结果
        """
        if not self.is_available():
            return {
                "status": "error",
                "reason": "AI-Trader not available",
                "message": "AI-Trader 项目路径未找到"
            }
        
        if approval_result.get("action") not in ["approve", "execute"]:
            return {
                "status": "skipped",
                "reason": "Not approved",
                "message": "交易未获批准"
            }
        
        # 提取交易信息
        trader_decision = debate_record.get("trader_decision", {})
        action = trader_decision.get("action", {})
        
        trade_order = {
            "symbol": debate_record.get("symbol"),
            "side": action.get("side", "buy"),
            "quantity": action.get("quantity", 0),
            "order_type": action.get("order_type", "limit"),
            "price": action.get("limit_price", action.get("stop_loss")),
            "stop_loss": action.get("stop_loss"),
            "take_profit": action.get("take_profit"),
            "reason": trader_decision.get("reasoning", ""),
            "debate_id": debate_record.get("debate_id"),
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存到 AI-Trader 待执行队列
        result = self._submit_to_ai_trader(trade_order)
        
        return result
    
    def _submit_to_ai_trader(self, trade_order: Dict) -> Dict:
        """提交交易到 AI-Trader"""
        # 简化实现：写入待执行文件
        # 实际应该调用 AI-Trader 的 API 或写入特定目录
        
        orders_dir = self.ai_trader_path / "orders"
        orders_dir.mkdir(parents=True, exist_ok=True)
        
        filename = "order_{}.json".format(datetime.now().strftime("%Y%m%d_%H%M%S"))
        filepath = orders_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(trade_order, f, indent=2, ensure_ascii=False)
        
        return {
            "status": "success",
            "message": "交易订单已提交",
            "order_file": str(filepath),
            "order": trade_order
        }
    
    def update_position(self, symbol: str, action: str, quantity: int, price: float) -> Dict:
        """
        更新持仓
        
        Args:
            symbol: 股票代码
            action: buy/sell
            quantity: 数量
            price: 价格
        
        Returns:
            更新结果
        """
        if not self.position_file or not self.position_file.exists():
            # 创建持仓文件
            self.position_file.parent.mkdir(parents=True, exist_ok=True)
        
        position_entry = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "value": quantity * price
        }
        
        # 追加到持仓文件
        with open(self.position_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(position_entry, ensure_ascii=False) + "\n")
        
        return {
            "status": "success",
            "message": "持仓已更新",
            "entry": position_entry
        }
    
    def get_current_positions(self) -> Dict:
        """
        获取当前持仓
        
        Returns:
            持仓数据
        """
        if not self.position_file or not self.position_file.exists():
            return {"positions": [], "total_value": 0}
        
        positions = {}
        total_value = 0
        
        with open(self.position_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    symbol = entry.get("symbol")
                    
                    if symbol not in positions:
                        positions[symbol] = {
                            "symbol": symbol,
                            "quantity": 0,
                            "avg_price": 0,
                            "total_value": 0
                        }
                    
                    if entry.get("action") == "buy":
                        positions[symbol]["quantity"] += entry.get("quantity", 0)
                        total_value += entry.get("value", 0)
                    elif entry.get("action") == "sell":
                        positions[symbol]["quantity"] -= entry.get("quantity", 0)
                        total_value -= entry.get("value", 0)
        
        return {
            "positions": list(positions.values()),
            "total_value": total_value,
            "count": len(positions)
        }
    
    def get_status(self) -> Dict:
        """获取集成状态"""
        return {
            "available": self.is_available(),
            "ai_trader_path": str(self.ai_trader_path) if self.ai_trader_path else None,
            "position_file": str(self.position_file) if self.position_file else None,
            "position_file_exists": self.position_file and self.position_file.exists()
        }


# 使用示例
if __name__ == "__main__":
    integration = AITraderIntegration()
    
    print("AI-Trader 集成状态:")
    print(json.dumps(integration.get_status(), indent=2, ensure_ascii=False))
    
    # 模拟执行交易
    debate_record = {
        "debate_id": "debate_20260317_120000_600519SH",
        "symbol": "600519.SH",
        "trader_decision": {
            "decision": "BUY",
            "action": {
                "side": "buy",
                "quantity": 100,
                "order_type": "limit",
                "limit_price": 1380,
                "stop_loss": 1350,
                "take_profit": 1500
            },
            "reasoning": "Bull 观点更有说服力"
        }
    }
    
    approval_result = {
        "action": "approve"
    }
    
    result = integration.execute_trade(debate_record, approval_result)
    print("\n交易执行结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
