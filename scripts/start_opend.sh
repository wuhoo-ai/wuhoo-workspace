#!/bin/bash
# OpenD 启动管理脚本 — 命令行参数模式，不依赖 FutuOpenD.xml 配置文件
# 凭证通过环境变量注入：FUTU_USERNAME, FUTU_LOGIN_PASSWORD, FUTU_TRADING_PASSWORD

set -euo pipefail

# ─── 路径配置 ───
OPEND_DIR="/home/admin/wuhoo-workspace/tools/opend/Futu_OpenD_10.3.6308_Centos7/Futu_OpenD_10.3.6308_Centos7"
OPEND_BIN="${OPEND_DIR}/FutuOpenD"
PID_FILE="/tmp/futu_opend.pid"
LOG_DIR="/home/admin/wuhoo-workspace/tools/opend/logs"
LOG_FILE="${LOG_DIR}/stdout.log"

# ─── 环境变量验证 ───
ENV_FILE="${HOME}/.hermes/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

if [[ -z "${FUTU_USERNAME:-}" ]]; then
    echo "错误: FUTU_USERNAME 未设置 (从 $ENV_FILE 加载失败)"
    exit 1
fi
if [[ -z "${FUTU_LOGIN_PASSWORD:-}" ]]; then
    echo "错误: FUTU_LOGIN_PASSWORD 未设置"
    exit 1
fi
if [[ -z "${FUTU_TRADING_PASSWORD:-}" ]]; then
    echo "错误: FUTU_TRADING_PASSWORD 未设置"
    exit 1
fi

# ─── 辅助函数 ───
get_pid() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        fi
    fi
    # 备用: 通过进程名查找
    pgrep -f "FutuOpenD" 2>/dev/null | head -1 || true
}

compute_pwd_md5() {
    echo -n "$1" | md5sum | awk '{print $1}'
}

start_opend() {
    local existing_pid
    existing_pid=$(get_pid)
    if [[ -n "$existing_pid" ]]; then
        echo "OpenD 已在运行 (PID: $existing_pid)"
        echo "使用 '$0 restart' 重启"
        return 0
    fi

    mkdir -p "$LOG_DIR"

    local login_pwd_md5
    login_pwd_md5=$(compute_pwd_md5 "$FUTU_LOGIN_PASSWORD")

    echo "=== 启动 OpenD ==="
    echo "  版本:     $(strings "$OPEND_BIN" | grep -oP '10\.\d+\.\d+' | head -1)"
    echo "  账户:     $FUTU_USERNAME"
    echo "  密码模式: 明文 (login_pwd)"
    echo "  模拟盘:   enable"
    echo "  API端口:  11111"
    echo ""

    # 命令行参数启动，不依赖 XML 配置文件
    # 使用 -login_pwd 明文模式（-login_pwd_md5 在部分版本会登录失败）
    nohup "$OPEND_BIN" \
        -login_account="$FUTU_USERNAME" \
        -login_pwd="$FUTU_LOGIN_PASSWORD" \
        -api_ip=127.0.0.1 \
        -api_port=11111 \
        -simulate_trade=enable \
        -lang=chs \
        -log_level=info \
        -log_path="$LOG_DIR" \
        -websocket_ip=127.0.0.1 \
        -websocket_port=22222 \
        -remember=0 \
        -no_monitor=1 \
        > "$LOG_FILE" 2>&1 &

    local new_pid=$!
    echo "$new_pid" > "$PID_FILE"
    echo "OpenD 已启动 (PID: $new_pid)"
    echo "等待初始化..."

    # 等待端口监听
    for i in $(seq 1 30); do
        sleep 1
        if ss -tlnp | grep -q ':11111' 2>/dev/null; then
            echo "OpenD 端口 11111 已监听"
            return 0
        fi
    done

    echo "警告: OpenD 启动超时，检查日志: $LOG_FILE"
    echo "=== 最新日志 ==="
    tail -20 "$LOG_FILE"
    return 1
}

stop_opend() {
    local pid
    pid=$(get_pid)
    if [[ -n "$pid" ]]; then
        echo "停止 OpenD (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 3
        if kill -0 "$pid" 2>/dev/null; then
            echo "强制终止..."
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
        fi
        rm -f "$PID_FILE"
        echo "OpenD 已停止"
    else
        echo "OpenD 未运行"
    fi
}

status_opend() {
    local pid
    pid=$(get_pid)
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        echo "OpenD 运行中 (PID: $pid)"
        ss -tlnp | grep ':11111' || echo "  端口 11111 未监听"
    else
        echo "OpenD 未运行"
    fi
}

# ─── 主逻辑 ───
case "${1:-status}" in
    start)
        start_opend
        ;;
    stop)
        stop_opend
        ;;
    restart)
        stop_opend
        sleep 2
        start_opend
        ;;
    status)
        status_opend
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
