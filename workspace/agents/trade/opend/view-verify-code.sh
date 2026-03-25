#!/bin/bash
# 富途 OpenD 验证码查看工具

VERIFY_CODE_DIR="$HOME/.com.futunn.FutuOpenD/F3CNN"

echo "=========================================="
echo "  富途 OpenD 验证码查看工具"
echo "=========================================="
echo ""

# 查找最新的验证码图片
if [ -d "$VERIFY_CODE_DIR" ]; then
    LATEST_VERIFY=$(find "$VERIFY_CODE_DIR" -name "PicVerifyCode*.png" -type f 2>/dev/null | sort -r | head -1)
    
    if [ -n "$LATEST_VERIFY" ]; then
        echo "✅ 找到验证码图片:"
        echo "   路径：$LATEST_VERIFY"
        echo "   大小：$(du -h "$LATEST_VERIFY" | cut -f1)"
        echo "   修改时间：$(stat -c %y "$LATEST_VERIFY" 2>/dev/null || stat -f %Sm "$LATEST_VERIFY" 2>/dev/null)"
        echo ""
        
        echo "查看方式:"
        echo ""
        echo "1. 使用图片查看器 (如果有图形界面):"
        echo "   eog \"$LATEST_VERIFY\" &"
        echo "   display \"$LATEST_VERIFY\" &"
        echo ""
        
        echo "2. 输出 Base64 编码 (可复制到本地解码):"
        echo "   base64 \"$LATEST_VERIFY\""
        echo ""
        
        echo "3. 复制到本地查看:"
        echo "   scp $LATEST_VERIFY 本地路径"
        echo ""
        
        echo "4. 转换为 ASCII 艺术 (简单预览):"
        echo "   (需要安装：pip install term-image)"
        echo ""
        
        # 提供快速操作
        echo "=========================================="
        echo "快速操作:"
        echo "=========================================="
        echo ""
        read -p "是否输出 Base64 编码？(y/n): " output_choice
        
        if [ "$output_choice" = "y" ]; then
            echo ""
            echo "Base64 编码:"
            echo "----------------------------------------"
            base64 "$LATEST_VERIFY"
            echo "----------------------------------------"
            echo ""
            echo "解码方法 (在本地电脑):"
            echo "  echo '上面的 BASE64 字符串' | base64 -d > verify.png"
            echo "  然后用图片查看器打开 verify.png"
        fi
    else
        echo "❌ 未找到验证码图片"
        echo ""
        echo "可能原因:"
        echo "  1. OpenD 未启动"
        echo "  2. OpenD 已登录，无需验证码"
        echo "  3. 验证码目录不存在"
        echo ""
        echo "解决方法:"
        echo "  1. 启动 OpenD: ./start-interactive.sh"
        echo "  2. 检查 OpenD 状态：ps aux | grep FutuOpenD"
        echo "  3. 查看 OpenD 日志：tail -f openD.log"
    fi
else
    echo "❌ 验证码目录不存在:"
    echo "   $VERIFY_CODE_DIR"
    echo ""
    echo "请先启动 OpenD:"
    echo "  ./start-interactive.sh"
fi

echo ""
