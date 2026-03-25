#!/bin/bash
# OpenClaw 渠道默认设置快速应用脚本
# 用法：./set-channel-defaults.sh [webchat|telegram|discord]

CHANNEL="${1:-webchat}"

case "$CHANNEL" in
  webchat|web)
    echo "📍 WebChat 默认设置:"
    echo "   /think high /verbose on /reasoning off"
    echo ""
    echo "✅ 已复制到剪贴板 (需要手动粘贴到 OpenClaw)"
    echo "/think high /verbose on /reasoning off" | xclip -selection clipboard 2>/dev/null || echo "/think high /verbose on /reasoning off"
    ;;
  
  telegram|tg)
    echo "📍 Telegram 默认设置:"
    echo "   /think high /verbose on /reasoning on"
    echo ""
    echo "✅ 已复制到剪贴板 (需要手动粘贴到 OpenClaw)"
    echo "/think high /verbose on /reasoning on" | xclip -selection clipboard 2>/dev/null || echo "/think high /verbose on /reasoning on"
    ;;
  
  discord|ds)
    echo "📍 Discord 默认设置:"
    echo "   /think high /verbose on /reasoning on"
    echo ""
    echo "✅ 已复制到剪贴板 (需要手动粘贴到 OpenClaw)"
    echo "/think high /verbose on /reasoning on" | xclip -selection clipboard 2>/dev/null || echo "/think high /verbose on /reasoning on"
    ;;
  
  *)
    echo "❌ 未知渠道：$CHANNEL"
    echo ""
    echo "可用渠道：webchat, telegram, discord"
    exit 1
    ;;
esac

echo ""
echo "💡 提示：在 OpenClaw 中使用 /new 开始新会话后，执行上述命令。"
