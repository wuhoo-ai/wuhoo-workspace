#!/bin/bash
# OpenClaw 统一消息推送脚本
# 使用已调试通过的单聊链路发送消息
#
# 用法: ./notify.sh "消息内容"

set -e

# 配置
DINGTALK_USER_ID="01443329476136537748"

# 参数
MESSAGE="${1:-}"

if [ -z "$MESSAGE" ]; then
    echo "错误: 消息内容不能为空"
    echo "用法: $0 \"消息内容\""
    exit 1
fi

# 使用 openclaw CLI 发送消息
if openclaw message send \
    --channel dingtalk \
    --target "$DINGTALK_USER_ID" \
    --message "$MESSAGE" 2>/dev/null; then
    echo "✅ 消息发送成功"
    exit 0
else
    echo "❌ 消息发送失败"
    exit 1
fi
