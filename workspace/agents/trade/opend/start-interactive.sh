#!/bin/bash
# 富途 OpenD 交互式启动脚本 (支持验证码输入)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 加载环境变量
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 默认配置
HOST=${FUTU_HOST:-127.0.0.1}
PORT=${FUTU_PORT:-11111}
MARKET=${FUTU_MARKET:-HK}
ENV=${FUTU_ENV:-SIMULATE}
USERNAME=${FUTU_USERNAME}
PASSWORD=${FUTU_PASSWORD}

echo -e "${BLUE}=========================================="
echo -e "  富途 OpenD 交互式启动脚本"
echo -e "==========================================${NC}"
echo "主机：$HOST"
echo "端口：$PORT"
echo "市场：$MARKET"
echo "环境：$ENV"
echo "账号：$USERNAME"
echo -e "${BLUE}==========================================${NC}"
echo ""

# 检查密码是否配置
if [ "$PASSWORD" = "YOUR_FUTU_PASSWORD" ] || [ -z "$PASSWORD" ]; then
    echo -e "${RED}❌ 错误：请先配置 .env 文件中的 FUTU_PASSWORD${NC}"
    exit 1
fi

# 检查 OpenD 是否已运行
if pgrep -f "FutuOpenD" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  检测到 OpenD 已在运行${NC}"
    read -p "是否先停止现有进程？(y/n): " stop_choice
    if [ "$stop_choice" = "y" ]; then
        pkill -f FutuOpenD
        sleep 2
        echo -e "${GREEN}✅ 已停止现有进程${NC}"
    else
        echo "退出脚本"
        exit 0
    fi
fi

# 清理旧的验证码图片
VERIFY_CODE_DIR="$HOME/.com.futunn.FutuOpenD/F3CNN"
if [ -d "$VERIFY_CODE_DIR" ]; then
    rm -f "$VERIFY_CODE_DIR"/PicVerifyCode*.png 2>/dev/null
fi

echo -e "${BLUE}🚀 启动富途 OpenD...${NC}"
echo ""

# 后台启动 OpenD
nohup ./FutuOpenD \
    -host=$HOST \
    -port=$PORT \
    -market=$MARKET \
    -env=$ENV \
    -login_account="$USERNAME" \
    -login_pwd="$PASSWORD" \
    > openD.log 2>&1 &

OPEND_PID=$!
echo -e "${GREEN}✅ OpenD 已启动 (PID: $OPEND_PID)${NC}"
echo ""

# 等待验证码生成
echo -e "${YELLOW}⏳ 等待验证码生成...${NC}"
sleep 5

# 检查验证码图片
MAX_WAIT=60
WAIT_COUNT=0
VERIFY_CODE_PATH=""

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if [ -d "$VERIFY_CODE_DIR" ]; then
        VERIFY_CODE_PATH=$(find "$VERIFY_CODE_DIR" -name "PicVerifyCode*.png" 2>/dev/null | head -1)
        if [ -n "$VERIFY_CODE_PATH" ]; then
            break
        fi
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    echo -ne "\r  已等待 ${WAIT_COUNT}s..."
done

echo ""

if [ -z "$VERIFY_CODE_PATH" ]; then
    echo -e "${RED}❌ 未找到验证码图片${NC}"
    echo ""
    echo "可能原因:"
    echo "  1. OpenD 启动失败 - 查看日志：tail -f openD.log"
    echo "  2. 账号已登录 - 无需验证码"
    echo ""
    
    # 检查端口是否监听
    if netstat -tlnp 2>/dev/null | grep -q ":$PORT"; then
        echo -e "${GREEN}✅ 端口 $PORT 正在监听，可能已登录成功${NC}"
        echo ""
        echo "测试连接:"
        echo "  cd ~/.openclaw/workspace/agents/trade"
        echo "  source venv-futu/bin/activate"
        echo "  python -c \"from futu import *; print(OpenQuoteContext(host='127.0.0.1', port=$PORT).get_global_state())\""
    else
        echo -e "${RED}❌ 端口 $PORT 未监听，OpenD 可能启动失败${NC}"
        echo ""
        echo "查看日志：tail -f openD.log"
    fi
    exit 1
fi

echo -e "${GREEN}✅ 找到验证码图片${NC}"
echo ""
echo -e "${BLUE}=========================================="
echo -e "  验证码信息"
echo -e "==========================================${NC}"
echo "图片路径：$VERIFY_CODE_PATH"
echo "查看方式:"
echo "  1. 使用图片查看器：eog \"$VERIFY_CODE_PATH\" &"
echo "  2. 复制到本地查看：scp $VERIFY_CODE_PATH 本地路径"
echo "  3. 转换为 Base64: base64 \"$VERIFY_CODE_PATH\""
echo -e "${BLUE}==========================================${NC}"
echo ""

# 提供查看验证码的选项
echo "请选择查看验证码的方式:"
echo "  1. 使用 eog 查看 (如果有图形界面)"
echo "  2. 输出 Base64 编码 (可解码查看)"
echo "  3. 跳过，直接测试连接 (可能已自动登录)"
echo "  4. 退出"
echo ""
read -p "请输入选择 (1-4): " view_choice

case $view_choice in
    1)
        if command -v eog &> /dev/null; then
            eog "$VERIFY_CODE_PATH" &
            echo -e "${GREEN}✅ 已打开图片查看器${NC}"
        else
            echo -e "${YELLOW}⚠️  未找到 eog，尝试其他查看方式${NC}"
            echo "  安装：sudo yum install eog"
        fi
        ;;
    2)
        echo ""
        echo "Base64 编码:"
        echo "----------------------------------------"
        base64 "$VERIFY_CODE_PATH"
        echo "----------------------------------------"
        echo ""
        echo "解码方法:"
        echo "  echo 'BASE64_STRING' | base64 -d > verify.png"
        ;;
    3)
        echo -e "${YELLOW}⏭️  跳过验证码输入${NC}"
        ;;
    4)
        echo "退出脚本"
        exit 0
        ;;
esac

echo ""

# 输入验证码
echo -e "${BLUE}=========================================="
echo -e "  输入验证码"
echo -e "==========================================${NC}"
echo ""
echo "请输入验证码图片中的字符 (不区分大小写):"
echo "(如果看不到图片，请打开 $VERIFY_CODE_PATH)"
echo ""
read -p "验证码：VERIFY_CODE

if [ -n "$VERIFY_CODE" ]; then
    echo ""
    echo -e "${YELLOW}⚠️  注意：OpenD 命令行版本不支持直接输入验证码${NC}"
    echo ""
    echo "请使用以下方法之一完成登录:"
    echo ""
    echo "方法 1: 使用 GUI 版本"
    echo "  下载 GUI 版本并在有图形界面的环境登录"
    echo ""
    echo "方法 2: 使用富途牛牛 APP"
    echo "  1. 打开富途牛牛 APP"
    echo "  2. 搜索「OpenAPI」或「量化交易」"
    echo "  3. 完成 API 合规确认"
    echo "  4. 登录后返回继续"
    echo ""
    echo "方法 3: 等待自动登录"
    echo "  有时 OpenD 会自动使用缓存的登录状态"
    echo ""
    
    read -p "是否重新生成验证码？(y/n): " regen_choice
    if [ "$regen_choice" = "y" ]; then
        echo "重启 OpenD..."
        pkill -f FutuOpenD
        sleep 2
        exec $0  # 重新执行本脚本
    fi
else
    echo -e "${YELLOW}⏭️  跳过验证码输入${NC}"
fi

echo ""
echo -e "${BLUE}=========================================="
echo -e "  检查连接状态"
echo -e "==========================================${NC}"
echo ""

# 等待 OpenD 完全启动
sleep 3

# 检查端口
if netstat -tlnp 2>/dev/null | grep -q ":$PORT" || ss -tlnp 2>/dev/null | grep -q ":$PORT"; then
    echo -e "${GREEN}✅ 端口 $PORT 正在监听${NC}"
    
    # 检查进程
    OPEND_RUNNING=$(pgrep -f "FutuOpenD" | wc -l)
    if [ $OPEND_RUNNING -gt 0 ]; then
        echo -e "${GREEN}✅ OpenD 进程运行中 (PID: $(pgrep -f FutuOpenD | tr '\n' ' '))${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}=========================================="
    echo -e "  OpenD 启动成功!"
    echo -e "==========================================${NC}"
    echo ""
    echo "下一步:"
    echo "  1. 测试 VnPy 连接:"
    echo "     cd ~/.openclaw/workspace/agents/trade"
    echo "     source venv-futu/bin/activate"
    echo "     python -c \"from futu import *; print(OpenQuoteContext(host='127.0.0.1', port=$PORT).get_global_state())\""
    echo ""
    echo "  2. 查看 OpenD 日志:"
    echo "     tail -f openD.log"
    echo ""
    echo "  3. 停止 OpenD:"
    echo "     pkill -f FutuOpenD"
    echo ""
else
    echo -e "${RED}❌ 端口 $PORT 未监听${NC}"
    echo ""
    echo "可能原因:"
    echo "  1. 验证码未输入 - 需要使用 GUI 版本登录"
    echo "  2. 账号密码错误 - 检查 .env 配置"
    echo "  3. 网络问题 - 检查服务器网络"
    echo ""
    echo "查看日志:"
    echo "  tail -f openD.log"
    echo ""
    echo "日志最后 10 行:"
    echo "----------------------------------------"
    tail -10 openD.log
    echo "----------------------------------------"
fi

echo ""
