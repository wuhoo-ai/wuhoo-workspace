#!/usr/bin/env bash
# WP2 hourly 采集 wrapper — flock 防并发写锁，与每日08:00简报采集串行化。
# 用法: bash rss_hourly_fetch.sh   (cron no_agent 每小时调用; 每日简报 step1 也调用同一脚本)
set -uo pipefail
SKILL=/home/admin/wuhoo-workspace/skills/default/wuhoo-news-rss
INTEL=/home/admin/wuhoo-workspace/skills/default/wuhoo-news-intel
LOCK=/tmp/wuhoo_rss_fetch.lock
LOG="$INTEL/data/hourly_fetch.log"
mkdir -p "$INTEL/data"
cd "$SKILL" || { echo "$(date '+%F %T') ERR cd skill" >> "$LOG"; exit 1; }
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date '+%F %T') SKIP lock-busy(另一采集进行中)" >> "$LOG"
  exit 0
fi
echo "$(date '+%F %T') START fetch" >> "$LOG"
python3.11 src/fetcher.py --fetch >> "$LOG" 2>&1
rc=$?
echo "$(date '+%F %T') END rc=$rc" >> "$LOG"
# 日志滚动保留最近 3000 行
tail -n 3000 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
exit $rc
