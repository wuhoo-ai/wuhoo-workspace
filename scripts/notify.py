#!/usr/bin/env python3
"""
OpenClaw 统一消息推送模块
使用已调试通过的单聊链路发送消息

用法:
    python notify.py "消息内容"
    
或者作为模块导入:
    from notify import send_message
    send_message("Hello")
"""

import os
import sys
import subprocess

# 配置
DINGTALK_USER_ID = "01443329476136537748"


def send_message(message: str) -> bool:
    """
    发送消息到 DingTalk 单聊
    
    Args:
        message: 消息内容
        
    Returns:
        bool: 是否发送成功
    """
    if not message:
        print("错误: 消息内容不能为空", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [
                "openclaw", "message", "send",
                "--channel", "dingtalk",
                "--target", DINGTALK_USER_ID,
                "--message", message
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ 消息发送成功")
            return True
        else:
            stderr = result.stderr.decode('utf-8') if result.stderr else ""
            print(f"❌ 消息发送失败: {stderr}", file=sys.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 发送超时", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ 发送失败: {e}", file=sys.stderr)
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='OpenClaw 消息推送工具')
    parser.add_argument('message', help='消息内容')
    
    args = parser.parse_args()
    
    success = send_message(args.message)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
