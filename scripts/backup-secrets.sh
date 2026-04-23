#!/bin/bash
set -e

BACKUP_DIR=~/wuhoo-workspace/data/backups/secrets
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 检查是否设置了公钥
if [ -z "$AGE_PUBLIC_KEY" ]; then
    echo "⚠️  AGE_PUBLIC_KEY 未设置，使用本地备份模式（不加密）"
    ENCRYPT_CMD="cp"
    ENCRYPT_EXT=""
else
    echo "✓ 使用 age 加密备份"
    ENCRYPT_CMD="age -r $AGE_PUBLIC_KEY"
    ENCRYPT_EXT=".enc"
fi

mkdir -p $BACKUP_DIR

# 敏感文件列表
declare -a FILES=(
    "$HOME/.hermes/.env"
    "$HOME/.openclaw/openclaw.json"
    "$HOME/.openclaw/workspace/trader-shanavasa-host.pem"
    "$HOME/.ssh/id_rsa"
    "$HOME/.openclaw/workspace/projects/AI-Trader/.env"
    "$HOME/.openclaw/data/ai-trader/.env"
    "$HOME/.openclaw/data/ai-trader/configs/.env"
    "$HOME/.openclaw/workspace/projects/TrendRadar/docker/.env"
    "$HOME/.openclaw/data/v2ray/config.json"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        # 生成安全文件名
        safe_name=$(echo "$file" | sed 's/^\//_/' | sed 's/\//_/g')
        if [ -n "$ENCRYPT_EXT" ]; then
            age -r "$AGE_PUBLIC_KEY" "$file" > "$BACKUP_DIR/${safe_name}.${TIMESTAMP}${ENCRYPT_EXT}"
        else
            cp "$file" "$BACKUP_DIR/${safe_name}.${TIMESTAMP}"
        fi
        echo "✓ Backed up: $file"
    else
        echo "⚠️  Not found: $file"
    fi
done

# 清理 30 天前的备份
find $BACKUP_DIR -type f -mtime +30 -delete 2>/dev/null || true

echo ""
echo "Backup completed at $TIMESTAMP"
echo "Backup location: $BACKUP_DIR"
