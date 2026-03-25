#!/bin/bash
# Heartbeat 新闻推送脚本
# 推送时间：北京时间 09:00 / 12:00 / 16:00 / 20:00
# 推送渠道：仅钉钉 (01443329476136537748) 和企业微信 (haohaijiao)
# 特点：拆分成多条推送，保留原文超链接

set -e

# ==================== 配置 ====================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../logs/heartbeat-news.log"
TREND_DIR="/home/admin/.openclaw/workspace/projects/TrendRadar"
TREND_OUTPUT_DIR="/home/admin/.openclaw/data/trendradar/output"

# 推送白名单 (仅允许这两个用户)
DINGTALK_USER_ID="01443329476136537748"
WECOM_USER_ID="haohaijiao"

# 关键词配置
AI_KEYWORDS="AI,大模型，LLM,Agent，自动驾驶，机器学习"
TRADE_KEYWORDS="量化交易，AI-Trader，因子挖掘，多因子，选股策略"
TECH_KEYWORDS="科技，创业，融资，IPO，大模型"
COMMODITY_KEYWORDS="原油，黄金，铜，大豆，铁矿石，大宗商品"

# 推送配置
MAX_TITLE_LENGTH=50  # 标题最大长度

# ==================== 日志函数 ====================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ==================== 推送函数 ====================

send_to_dingtalk() {
    local message="$1"
    local user_id="$2"
    
    log "📱 发送钉钉消息到用户：$user_id"
    
    # 使用 OpenClaw message 工具推送 (markdown 格式)
    openclaw message send \
        --channel dingtalk \
        --target "$user_id" \
        --message "$message" \
        2>&1 | tee -a "$LOG_FILE"
    
    # 等待 1 秒避免频率限制
    sleep 1
}

send_to_wecom() {
    local message="$1"
    local user_id="$2"
    
    log "💼 发送企业微信消息到用户：$user_id"
    
    # 使用 OpenClaw message 工具推送 (markdown 格式)
    openclaw message send \
        --channel wecom \
        --target "$user_id" \
        --message "$message" \
        2>&1 | tee -a "$LOG_FILE"
    
    # 等待 1 秒避免频率限制
    sleep 1
}

# ==================== 获取 TrendRadar 热榜 ====================

get_trendradar_hotlist() {
    log "🔥 获取 TrendRadar 热榜..."
    
    cd "$TREND_DIR"
    
    # 执行 TrendRadar (热点模式)
    ./run-local.sh 2>&1 | tee -a "$LOG_FILE"
    
    # 读取最新输出
    TODAY=$(date '+%Y-%m-%d')
    OUTPUT_FILE="$TREND_OUTPUT_DIR/$TODAY/txt/$TODAY.txt"
    
    if [ -f "$OUTPUT_FILE" ]; then
        log "✅ 读取 TrendRadar 输出：$OUTPUT_FILE"
        cat "$OUTPUT_FILE"
    else
        log "⚠️  未找到 TrendRadar 输出文件"
        echo "(TrendRadar 数据暂不可用)"
    fi
}

# ==================== 获取主题新闻 (保留链接) ====================

get_theme_news_with_links() {
    local theme="$1"
    local keywords="$2"
    local limit="${3:-5}"
    
    log "🔍 搜索 $theme 主题新闻：$keywords"
    
    # 使用 Jina Search 搜索
    RESPONSE=$(curl -s -X POST "https://api.jina.ai/v1/search" \
        -H "Authorization: Bearer $JINA_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"q\": \"$keywords\",
            \"count\": $limit,
            \"freshness\": \"pd\"
        }" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$RESPONSE" ]; then
        # 解析 JSON 并格式化 (保留链接)
        echo "$RESPONSE" | /usr/bin/python3.11 << PYTHON
import sys, json

try:
    data = json.load(sys.stdin)
    hits = data.get('hits', [])[:$limit]
    
    for i, hit in enumerate(hits, 1):
        title = hit.get('title', '无标题')
        url = hit.get('url', '')
        snippet = hit.get('description', '')
        
        # 截断过长的标题
        if len(title) > $MAX_TITLE_LENGTH:
            title = title[:$MAX_TITLE_LENGTH-3] + '...'
        
        # 输出格式：标题 + 链接
        if url:
            print(f'{i}. [{title}]({url})')
        else:
            print(f'{i}. {title}')
            
        # 可选：显示摘要
        # if snippet:
        #     print(f'   {snippet[:100]}...')
except Exception as e:
    print(f'(搜索失败：{e})')
PYTHON
    else
        echo "(搜索失败)"
    fi
}

# ==================== 构建推送消息 (拆分成多条) ====================

send_trendradar_report() {
    local current_time=$(date '+%Y-%m-%d %H:%M:%S')
    local time_period=""
    
    # 判断时间段
    local hour=$(date '+%H')
    case $hour in
        09) time_period="早间" ;;
        12) time_period="午间" ;;
        16) time_period="下午" ;;
        20) time_period="晚间" ;;
        *) time_period="定时" ;;
    esac
    
    log "📊 构建 TrendRadar 热榜消息..."
    
    # 获取 TrendRadar 内容
    local trend_content=$(get_trendradar_hotlist)
    
    # 解析并格式化 (保留链接)
    local formatted_content=$(echo "$trend_content" | /usr/bin/python3.11 << 'PYTHON'
import sys

lines = sys.stdin.readlines()
formatted = []
current_platform = ""
count = 0

for line in lines:
    line = line.strip()
    
    # 检测平台行
    if ' | ' in line and not line.startswith(('1.','2.','3.','4.','5.')):
        if formatted and current_platform:
            formatted.append("")  # 空行分隔
        
        current_platform = line.split(' | ')[0]
        formatted.append(f"\n【{current_platform}】")
        count = 0
    
    # 检测新闻行 (保留链接)
    elif line.startswith(('1.','2.','3.','4.','5.')):
        if count < 5:
            # 提取新闻标题和可能的链接
            parts = line.split(' ', 1)
            if len(parts) > 1:
                num, content = parts
                formatted.append(f"{num}. {content}")
                count += 1

# 输出前 20 条
print('\n'.join(formatted[:50]))
PYTHON
)
    
    # 构建消息
    local message="📰 TrendRadar 热榜 Top20\n"
    message="$message\n时间：$current_time\n"
    message="$message\n推送时段：${time_period}新闻\n"
    message="$message\n$formatted_content"
    
    # 发送消息
    send_to_dingtalk "$message" "$DINGTALK_USER_ID"
    send_to_wecom "$message" "$WECOM_USER_ID"
    
    log "✅ TrendRadar 热榜已推送"
}

send_theme_news_report() {
    local current_time=$(date '+%Y-%m-%d %H:%M:%S')
    
    log "📊 构建主题新闻消息..."
    
    # 消息头
    local message="📰 主题新闻 Top20\n"
    message="$message\n时间：$current_time\n"
    
    # AI 主题
    message="$message\n🤖 AI 主题 Top5\n"
    local ai_news=$(get_theme_news_with_links "AI" "$AI_KEYWORDS" 5)
    message="$message\n$ai_news"
    
    # 量化交易
    message="$message\n\n📈 量化交易 Top5\n"
    local trade_news=$(get_theme_news_with_links "量化交易" "$TRADE_KEYWORDS" 5)
    message="$message\n$trade_news"
    
    # 科技主题
    message="$message\n\n💻 科技主题 Top5\n"
    local tech_news=$(get_theme_news_with_links "科技" "$TECH_KEYWORDS" 5)
    message="$message\n$tech_news"
    
    # 大宗商品
    message="$message\n\n🏭 大宗商品 Top5\n"
    local commodity_news=$(get_theme_news_with_links "大宗商品" "$COMMODITY_KEYWORDS" 5)
    message="$message\n$commodity_news"
    
    message="$message\n\n---\n"
    message="$message\n数据来源：Jina AI Search\n"
    message="$message\n推送渠道：钉钉、企业微信"
    
    # 发送消息
    send_to_dingtalk "$message" "$DINGTALK_USER_ID"
    send_to_wecom "$message" "$WECOM_USER_ID"
    
    log "✅ 主题新闻已推送"
}

# ==================== 主函数 ====================

main() {
    log "=========================================="
    log "🚀 Heartbeat 新闻推送开始"
    log "=========================================="
    
    # 检查环境变量
    if [ -z "$JINA_API_KEY" ]; then
        log "❌ JINA_API_KEY 未配置"
        exit 1
    fi
    
    # 推送 1: TrendRadar 热榜
    send_trendradar_report
    
    # 等待 2 秒
    sleep 2
    
    # 推送 2: 主题新闻
    send_theme_news_report
    
    log "✅ 所有推送完成"
    log "=========================================="
}

# 执行主函数
main "$@"
