#!/usr/bin/env bash
# update_stock_data.sh — 盘后增量更新 A 股 + 港股数据
#
# 用法:
#   bash ~/wuhoo-workspace/scripts/update_stock_data.sh          # 增量更新
#   bash ~/wuhoo-workspace/scripts/update_stock_data.sh --full   # 全量重建
#
# 建议 cron: 每个交易日 16:00 (A 股收盘后) 执行
#   0 16 * * 1-5 cd /home/admin/wuhoo-workspace/skills/wuhoo-stock-pick && PYTHONUNBUFFERED=1 bash ~/wuhoo-workspace/scripts/update_stock_data.sh >> /tmp/stock_data_update.log 2>&1

set -euo pipefail

cd /home/admin/wuhoo-workspace/skills/wuhoo-stock-pick

MODE="${1:---incremental}"

# Load environment variables
ENV_FILE="$HOME/.hermes/.env"
if [ -f "$ENV_FILE" ]; then
    echo "[env] 加载环境变量: $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
fi

echo "========================================"
echo "盘后数据更新 $(date '+%Y-%m-%d %H:%M:%S')"
echo "模式: $MODE"
echo "========================================"

# ---------- A 股 ----------
echo ""
echo "[A 股] 开始更新..."
source venv/bin/activate
if [ "$MODE" = "--full" ]; then
    PYTHONUNBUFFERED=1 python fetch_cn_data.py --full --force
else
    PYTHONUNBUFFERED=1 python fetch_cn_data.py --incremental
fi

# ---------- 港股 ----------
echo ""
echo "[港股] 开始更新..."
source # 使用系统 python3.11 (venv 已安装依赖)
if [ "$MODE" = "--full" ]; then
    PYTHONUNBUFFERED=1 python fetch_hk_data.py --full --force
else
    PYTHONUNBUFFERED=1 python fetch_hk_data.py --incremental
fi

echo ""
echo "========================================"
echo "更新完成 $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
