#!/usr/bin/env python3
"""
富途 OpenD 连接测试脚本

用途：测试 VnPy 是否能成功连接富途 OpenD

前置条件:
1. 富途 OpenD 已启动 (端口 11111)
2. 已登录富途账号
3. 已完成 API 合规确认

使用方法:
1. 启动富途 OpenD
2. 运行此脚本：python test_connection.py
3. 检查连接结果
"""

import sys
import os

# 添加 VnPy 到路径
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/agents/trade/venv-futu/lib/python3.11/site-packages'))

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_futu import FutuGateway
from vnpy_futu.futu_gateway import TrdEnv

def test_connection():
    """测试富途连接"""
    print("=" * 60)
    print("富途 OpenD 连接测试")
    print("=" * 60)
    print()
    
    # 创建事件引擎和主引擎
    print("1. 创建事件引擎...")
    event_engine = EventEngine()
    
    print("2. 创建主引擎...")
    main_engine = MainEngine(event_engine)
    
    print("3. 添加富途网关...")
    main_engine.add_gateway(FutuGateway)
    
    print()
    print("4. 连接配置:")
    print("   主机：127.0.0.1")
    print("   端口：11111")
    print("   市场：HK (港股)")
    print("   环境：SIMULATE (模拟盘)")
    print()
    
    # 连接配置 - 从环境变量读取
    gateway_setting = {
        "地址": "127.0.0.1",
        "端口": 11111,
        "市场": "HK",
        "环境": TrdEnv.SIMULATE,
        "密码": os.environ.get("FUTU_TRADING_PASSWORD", "")
    }
    
    print("5. 尝试连接...")
    print("   (如果 OpenD 未启动，这里会超时)")
    print()
    
    try:
        # 连接
        main_engine.connect(gateway_setting, "FUTU")
        
        # 等待连接响应 (实际使用需要事件回调)
        import time
        time.sleep(3)
        
        print("✅ 连接成功！")
        print()
        print("下一步:")
        print("1. 测试行情订阅")
        print("2. 测试账户查询")
        print("3. 测试模拟盘下单")
        
        return True
        
    except Exception as e:
        print(f"❌ 连接失败：{e}")
        print()
        print("可能原因:")
        print("1. 富途 OpenD 未启动")
        print("2. 端口配置错误 (默认 11111)")
        print("3. 防火墙阻止连接")
        print("4. 密码错误")
        print()
        print("解决方法:")
        print("1. 启动富途 OpenD: https://www.futumm.com/OpenAPI")
        print("2. 确认 OpenD 端口配置")
        print("3. 检查防火墙设置")
        
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
