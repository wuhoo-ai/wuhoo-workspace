#!/bin/bash
# MEMORY.md 自动维护脚本
# 用途：定期清理超过 90 天的活动时间线条目，防止文件无限增长

MEMORY_FILE="$HOME/.openclaw/workspace/agents/main/MEMORY.md"
MAX_AGE_DAYS=90

if [ ! -f "$MEMORY_FILE" ]; then
    echo "MEMORY.md 不存在：$MEMORY_FILE"
    exit 1
fi

echo "检查 MEMORY.md 活动时间线..."

# 提取活动时间线部分，清理超过 90 天的条目
# 活动时间线格式：| YYYY-MM-DD | 事件描述 |
today=$(date +%Y-%m-%d)
cutoff=$(date -d "$today - $MAX_AGE_DAYS days" +%Y-%m-%d 2>/dev/null || date -v-"${MAX_AGE_DAYS}d" +%Y-%m-%d 2>/dev/null)

if [ -z "$cutoff" ]; then
    echo "无法计算截止日期，跳过清理"
    exit 1
fi

echo "清理 $cutoff 之前的条目..."

# 创建临时文件，保留非活动时间线内容和较新的活动时间线
temp_file=$(mktemp)
in_timeline=false

while IFS= read -r line; do
    # 检测活动时间线部分
    if [[ "$line" == *"活动时间线"* ]]; then
        in_timeline=true
        echo "$line" >> "$temp_file"
        # 保留表头行
        read -r header1
        echo "$header1" >> "$temp_file"
        read -r header2
        echo "$header2" >> "$temp_file"
        continue
    fi

    # 检测活动时间线结束（下一个标题）
    if $in_timeline && [[ "$line" == "## "* ]]; then
        in_timeline=false
        echo "$line" >> "$temp_file"
        continue
    fi

    # 在活动时间线内，过滤旧条目
    if $in_timeline; then
        # 提取日期字段（格式：| YYYY-MM-DD | ...）
        entry_date=$(echo "$line" | grep -oP '\d{4}-\d{2}-\d{2}' | head -1)
        if [ -n "$entry_date" ] && [[ "$entry_date" > "$cutoff" || "$entry_date" == "$cutoff" ]]; then
            echo "$line" >> "$temp_file"
        fi
    else
        echo "$line" >> "$temp_file"
    fi
done < "$MEMORY_FILE"

# 备份原文件
cp "$MEMORY_FILE" "${MEMORY_FILE}.bak"

# 替换原文件
mv "$temp_file" "$MEMORY_FILE"

echo "MEMORY.md 维护完成"
echo "备份文件：${MEMORY_FILE}.bak"
