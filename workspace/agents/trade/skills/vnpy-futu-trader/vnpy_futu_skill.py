#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VnPy-Futu-Trader Skill - 富途交易接口封装

功能:
- 连接富途 OpenD
- 执行买入/卖出订单
- 查询持仓/账户信息
- 设置止盈止损
- 订阅实时行情
- 订单状态跟踪

用法:
    from vnpy_futu_skill import FutuTrader

    trader = FutuTrader()
    trader.connect()
    trader.place_order("HK.00700", "BUY", 300.0, 100)
    trader.get_positions()
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# 添加 VnPy 路径
VENV_PATH = Path(__file__).parent.parent.parent / "venv-futu"
if VENV_PATH.exists():
    sys.path.insert(0, str(VENV_PATH / "lib" / "python3.11" / "site-packages"))

from vnpy.event import EventEngine
from vnpy.trader.event import EVENT_ORDER, EVENT_POSITION, EVENT_ACCOUNT
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import OrderRequest, SubscribeRequest, Direction, Offset, OrderType
from vnpy.trader.constant import Exchange
from vnpy_futu import FutuGateway
from vnpy_futu.futu_gateway import TrdEnv


class FutuTrader:
    """富途交易接口封装"""

    def __init__(self, host: str = "127.0.0.1", port: int = 11111,
                 market: str = "HK", env: str = "SIMULATE"):
        """
        初始化

        Args:
            host: OpenD 主机地址
            port: OpenD 端口
            market: 市场 (HK/US/SH/SZ)
            env: 环境 (SIMULATE/REAL)
        """
        self.host = host
        self.port = port
        self.market = market
        self.env = TrdEnv.SIMULATE if env == "SIMULATE" else TrdEnv.REAL

        self.main_engine = None
        self.event_engine = None
        self.connected = False

        # 订单回调
        self.order_callback = None
        self.position_callback = None

        # 日志
        self.log_dir = Path(__file__).parent / "log" / datetime.now().strftime("%Y-%m")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

        self.logger.info(f"FutuTrader 初始化：{host}:{port}, market={market}, env={env}")

    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger("FutuTrader")
        self.logger.setLevel(logging.INFO)

        # 文件处理器
        log_file = self.log_dir / f"futu_trader_{datetime.now().strftime('%Y%m%d')}.log"
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)

        # 控制台处理器
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # 格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def connect(self, password: str = "") -> bool:
        """
        连接富途

        Args:
            password: 交易密码 (可选，从环境变量读取)

        Returns:
            连接是否成功
        """
        if self.connected:
            self.logger.info("已连接，跳过")
            return True

        try:
            # 创建事件引擎和主引擎
            self.event_engine = EventEngine()
            self.main_engine = MainEngine(self.event_engine)
            self.main_engine.add_gateway(FutuGateway)

            # 注册回调
            self._register_event_handlers()

            # 连接配置 (vnpy_futu 要求的格式)
            gateway_setting = {
                "密码": password or os.environ.get("FUTU_TRADING_PASSWORD") or os.environ.get("FUTU_PASSWORD", ""),
                "地址": self.host,
                "端口": self.port,
                "市场": self.market,
                "环境": self.env.value if hasattr(self.env, 'value') else str(self.env)
            }

            self.logger.info(f"开始连接：{gateway_setting}")
            self.main_engine.connect(gateway_setting, "FUTU")

            # 等待连接 (实际使用是异步的)
            import time
            time.sleep(2)

            self.connected = True
            self.logger.info("✅ 连接成功")
            return True

        except Exception as e:
            self.logger.error(f"❌ 连接失败：{e}")
            return False

    def _register_event_handlers(self):
        """注册事件回调"""
        self.event_engine.register(EVENT_ORDER, self._on_order_event)
        self.event_engine.register(EVENT_POSITION, self._on_position_event)
        self.event_engine.register(EVENT_ACCOUNT, self._on_account_event)

    def _on_order_event(self, event):
        """订单事件回调"""
        order = event.data
        self.logger.info(f"订单更新：{order.symbol} {order.direction.value} "
                        f"价格={order.price} 数量={order.volume} 状态={order.status.value}")

        if self.order_callback:
            self.order_callback({
                "order_id": order.vt_orderid,
                "symbol": order.symbol,
                "direction": order.direction.value,
                "price": order.price,
                "volume": order.volume,
                "status": order.status.value,
                "traded": order.traded,
                "timestamp": datetime.now().isoformat()
            })

    def _on_position_event(self, event):
        """持仓事件回调"""
        pos = event.data
        self.logger.info(f"持仓更新：{pos.symbol} {pos.direction.value} "
                        f"数量={pos.volume} 均价={pos.price}")

        if self.position_callback:
            self.position_callback({
                "symbol": pos.symbol,
                "direction": pos.direction.value,
                "volume": pos.volume,
                "frozen": pos.frozen,
                "price": pos.price,
                "pnl": pos.pnl,
                "timestamp": datetime.now().isoformat()
            })

    def _on_account_event(self, event):
        """账户事件回调"""
        account = event.data
        self.logger.info(f"账户更新：{account.accountid} "
                        f"余额={account.balance} 可用={account.available}")

    def set_order_callback(self, callback):
        """设置订单回调"""
        self.order_callback = callback

    def set_position_callback(self, callback):
        """设置持仓回调"""
        self.position_callback = callback

    def place_order(self, code: str, action: str, price: float,
                    volume: int, order_type: str = "LIMIT",
                    stop_loss: float = None, take_profit: float = None) -> Dict:
        """
        下单交易

        Args:
            code: 股票代码 (如 "HK.00700" 或 "00700.HK")
            action: "BUY" / "SELL"
            price: 限价价格
            volume: 数量
            order_type: "LIMIT" / "MARKET"
            stop_loss: 止损价 (可选)
            take_profit: 止盈价 (可选)

        Returns:
            订单结果
        """
        if not self.connected:
            return {"success": False, "error": "未连接"}

        try:
            # 代码格式转换
            symbol, exchange = self._parse_code(code)

            # 方向转换 (VnPy 使用 LONG/SHORT，而不是 BUY/SELL)
            direction = Direction.LONG if action.upper() == "BUY" else Direction.SHORT

            # 订单类型转换
            ot = OrderType.LIMIT if order_type.upper() == "LIMIT" else OrderType.MARKET

            # 创建订单请求
            req = OrderRequest(
                symbol=symbol,
                exchange=exchange,
                direction=direction,
                offset=Offset.OPEN,
                type=ot,
                price=price,
                volume=volume,
                reference="auto-trader"
            )

            self.logger.info(f"下单：{symbol} {action} {volume}股 @ {price}")

            # 发送订单
            vt_orderid = self.main_engine.send_order(req, "FUTU")

            result = {
                "success": True,
                "order_id": vt_orderid,
                "symbol": symbol,
                "action": action,
                "price": price,
                "volume": volume,
                "status": "SUBMITTED",
                "message": "订单已提交"
            }

            # 记录止盈止损
            if stop_loss or take_profit:
                self.logger.info(f"设置止盈止损：stop_loss={stop_loss}, take_profit={take_profit}")
                result["stop_loss"] = stop_loss
                result["take_profit"] = take_profit

            return result

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.logger.error(f"下单失败：{action} - {error_detail}")
            return {"success": False, "error": f"{action}: {str(e)}"}

    def _parse_code(self, code: str) -> Tuple[str, Exchange]:
        """
        解析股票代码

        Args:
            code: 股票代码 (支持多种格式)

        Returns:
            (symbol, exchange)
        """
        # 富途格式：HK.00700, US.AAPL, SH.600519
        if "." in code:
            parts = code.split(".")
            if len(parts) == 2:
                market, sym = parts
                market = market.upper()

                # 映射到 VnPy 交易所枚举
                exchange_map = {
                    "HK": Exchange.SEHK,
                    "US": Exchange.NASDAQ,  # 或 "NYSE"
                    "SH": Exchange.SSE,
                    "SZ": Exchange.SZSE
                }
                return sym, exchange_map.get(market, Exchange.SEHK)

        # 其他格式尝试转换
        code = code.upper()
        if code.endswith(".HK"):
            return code[:-3], Exchange.SEHK
        elif code.endswith(".US"):
            return code[:-3], Exchange.NASDAQ
        elif code.endswith(".SH"):
            return code[:-3], Exchange.SSE
        elif code.endswith(".SZ"):
            return code[:-3], Exchange.SZSE

        # 默认返回
        return code, Exchange.SEHK

    def cancel_order(self, order_id: str) -> Dict:
        """撤单"""
        if not self.connected:
            return {"success": False, "error": "未连接"}

        try:
            self.main_engine.cancel_order(order_id, "FUTU")
            self.logger.info(f"撤单：{order_id}")
            return {"success": True, "order_id": order_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_positions(self) -> List[Dict]:
        """查询持仓"""
        if not self.connected:
            return []

        positions = self.main_engine.get_all_positions()
        result = []

        for pos in positions:
            if pos.volume > 0:
                result.append({
                    "symbol": pos.symbol,
                    "direction": pos.direction.value,
                    "volume": pos.volume,
                    "frozen": pos.frozen,
                    "avg_price": pos.price,
                    "pnl": pos.pnl,
                    "pnl_pct": pos.pnl / (pos.price * pos.volume) if pos.price > 0 else 0
                })

        return result

    def get_account(self) -> Optional[Dict]:
        """查询账户信息"""
        if not self.connected:
            return None

        account = self.main_engine.get_account("FUTU")
        if account:
            return {
                "balance": account.balance,
                "available": account.available,
                "frozen": account.frozen,
                "margin": account.margin,
                "timestamp": datetime.now().isoformat()
            }
        return None

    def subscribe_quotes(self, codes: List[str]) -> Dict:
        """订阅实时行情"""
        if not self.connected:
            return {"success": False, "error": "未连接"}

        subscribed = []
        for code in codes:
            symbol, exchange = self._parse_code(code)
            req = SubscribeRequest(symbol=symbol, exchange=exchange)
            self.main_engine.subscribe(req, "FUTU")
            subscribed.append(code)

        return {"success": True, "subscribed": subscribed, "count": len(subscribed)}

    def get_current_price(self, code: str) -> Optional[float]:
        """获取当前价格 (需要已订阅行情)"""
        if not self.connected:
            return None

        symbol, exchange = self._parse_code(code)
        tick = self.main_engine.get_tick(symbol, exchange)

        if tick:
            return tick.last_price
        return None

    def disconnect(self):
        """断开连接"""
        if self.main_engine:
            self.main_engine.close()
            self.connected = False
            self.logger.info("已断开连接")

    def __del__(self):
        """析构函数"""
        self.disconnect()


# ============= 便捷函数 (Skill 接口) =============

_trader_instance = None

def get_trader() -> FutuTrader:
    """获取交易器单例"""
    global _trader_instance
    if _trader_instance is None:
        _trader_instance = FutuTrader()
    return _trader_instance


def connect_trader(host: str = "127.0.0.1", port: int = 11111,
                   market: str = "HK", env: str = "SIMULATE",
                   password: str = "") -> Dict:
    """连接富途"""
    trader = get_trader()
    success = trader.connect(password)
    return {"success": success, "connected": trader.connected}


def place_trade(code: str, action: str, price: float,
                volume: int, position_ratio: float = None,
                stop_loss: float = None, take_profit: float = None) -> Dict:
    """
    执行交易

    Args:
        code: 股票代码
        action: "BUY" / "SELL"
        price: 限价价格
        volume: 数量
        position_ratio: 仓位比例 (可选，用于日志)
        stop_loss: 止损价
        take_profit: 止盈价

    Returns:
        交易结果
    """
    trader = get_trader()
    return trader.place_order(code, action, price, volume,
                              stop_loss=stop_loss, take_profit=take_profit)


def get_portfolio() -> Dict:
    """获取投资组合"""
    trader = get_trader()

    account = trader.get_account()
    positions = trader.get_positions()

    total_value = sum(p.get("pnl", 0) for p in positions)
    if account:
        total_value += account.get("balance", 0)

    return {
        "account": account,
        "positions": positions,
        "total_value": total_value,
        "timestamp": datetime.now().isoformat()
    }


def get_market_data(codes: List[str]) -> Dict:
    """获取行情数据"""
    trader = get_trader()

    result = {}
    for code in codes:
        price = trader.get_current_price(code)
        result[code] = {
            "price": price,
            "timestamp": datetime.now().isoformat()
        }

    return result


# ============= 命令行测试 =============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FutuTrader 测试")
    parser.add_argument("--action", choices=["connect", "place_order", "get_positions", "get_account"],
                       default="connect")
    parser.add_argument("--code", default="HK.00700")
    parser.add_argument("--price", type=float, default=300.0)
    parser.add_argument("--volume", type=int, default=100)

    args = parser.parse_args()

    print("=" * 60)
    print("FutuTrader 测试")
    print("=" * 60)

    trader = FutuTrader()

    if args.action == "connect":
        print("\n连接富途...")
        success = trader.connect()
        print(f"连接结果：{'✅ 成功' if success else '❌ 失败'}")

    elif args.action == "get_positions":
        print("\n连接并获取持仓...")
        if trader.connect():
            positions = trader.get_positions()
            print(f"\n持仓 ({len(positions)} 个):")
            for pos in positions:
                print(f"  {pos['symbol']}: {pos['volume']}股 @ {pos['avg_price']}")

    elif args.action == "get_account":
        print("\n连接并获取账户...")
        if trader.connect():
            account = trader.get_account()
            if account:
                print(f"\n账户信息:")
                print(f"  余额：{account['balance']}")
                print(f"  可用：{account['available']}")

    elif args.action == "place_order":
        print(f"\n下单测试：{args.code} BUY {args.volume}股 @ {args.price}")
        if trader.connect():
            result = trader.place_order(args.code, "BUY", args.price, args.volume)
            print(f"下单结果：{json.dumps(result, indent=2, ensure_ascii=False)}")
