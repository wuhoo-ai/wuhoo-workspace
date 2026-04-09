#!/bin/bash
# OpenClaw 状态检查脚本

echo "=== OpenClaw 系统状态检查 ==="
echo ""

# 1. Gateway 状态
echo "1. Gateway 状态:"
if pgrep -f "openclaw-gateway" > /dev/null; then
    PID=$(pgrep -f "openclaw-gateway")
    echo "   ✅ Gateway 正在运行 (PID: $PID)"
    curl -s http://localhost:18789/ > /dev/null 2>&1 && echo "   ✅ Web UI 可访问" || echo "   ⚠️  Web UI 响应异常"
else
    echo "   ❌ Gateway 未运行"
fi
echo ""

# 2. OpenD 状态
echo "2. Futu OpenD 状态:"
if pgrep -f "FutuOpenD" > /dev/null; then
    COUNT=$(pgrep -f "FutuOpenD" | wc -l)
    echo "   ✅ OpenD 正在运行 ($COUNT 个进程)"
    ps aux | grep FutuOpenD | grep -v grep | awk '{print "      PID: "$2" CPU: "$3"% MEM: "$4"%"}'
else
    echo "   ❌ OpenD 未运行"
    echo "   提示：运行 ~/.openclaw/workspace/agents/trade/opend/start_opend.sh 启动"
fi
echo ""

# 3. 会话锁检查
echo "3. 会话锁检查:"
LOCK_FILES=$(ls ~/.openclaw/agents/main/sessions/*.lock 2>/dev/null | wc -l)
if [ "$LOCK_FILES" -eq 0 ]; then
    echo "   ✅ 无锁定的会话"
else
    echo "   ⚠️  发现 $LOCK_FILES 个锁定的会话"
    ls -la ~/.openclaw/agents/main/sessions/*.lock
    echo "   提示：运行 rm -f ~/.openclaw/agents/main/sessions/*.lock 清理"
fi
echo ""

# 4. 端口检查
echo "4. 端口检查:"
netstat -tlnp 2>/dev/null | grep -E "18789|11111" | while read line; do
    if echo "$line" | grep -q "18789"; then
        echo "   ✅ Gateway 端口 18789 已监听"
    fi
    if echo "$line" | grep -q "11111"; then
        echo "   ✅ OpenD 端口 11111 已监听"
    fi
done
echo ""

# 5. 磁盘空间
echo "5. 磁盘空间:"
DF_OUTPUT=$(df -h ~/.openclaw | tail -1)
USED=$(echo "$DF_OUTPUT" | awk '{print $5}')
if [ "${USED%?}" -lt 80 ]; then
    echo "   ✅ 磁盘使用率：$USED"
else
    echo "   ⚠️  磁盘使用率：$USED (建议清理)"
fi
echo ""

echo "=== 检查完成 ==="
