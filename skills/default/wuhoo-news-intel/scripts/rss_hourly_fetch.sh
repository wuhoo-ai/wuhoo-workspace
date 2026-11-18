#!/usr/bin/env bash
# WP2 hourly 采集 wrapper — flock 防并发写锁，与每日08:00简报采集串行化。
# 用法: bash rss_hourly_fetch.sh   (cron no_agent 每小时调用; 每日简报 step1 也调用同一脚本)
# 2026-11-17 P0-1: 每轮写 source_coverage.json + RSSHub 挂死自动重启
# (Connection refused ≥10 源连续2轮 → podman restart rsshub, 记 ops_alerts.log; 有界幂等)。
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

# ---- P0-1 源覆盖统计 + RSSHub 挂死自动恢复 ----
python3.11 "$INTEL/src/intel.py" coverage >> "$LOG" 2>&1
REFUSED=$(python3.11 -c "import json;print(json.load(open('$INTEL/data/source_coverage.json')).get('refused',0))" 2>/dev/null || echo 0)
STREAK_FILE="$INTEL/data/refused_streak.txt"
STREAK=$(cat "$STREAK_FILE" 2>/dev/null || echo 0)
case "$STREAK" in (*[!0-9]*|'') STREAK=0;; esac
if [ "$REFUSED" -ge 10 ]; then
  STREAK=$((STREAK + 1))
else
  STREAK=0
fi
echo "$STREAK" > "$STREAK_FILE"
if [ "$STREAK" -ge 2 ]; then
  echo "$(date '+%F %T') ALERT rsshub connection-refused=$REFUSED 连续${STREAK}轮 → podman restart rsshub" >> "$INTEL/data/ops_alerts.log"
  podman restart rsshub >> "$INTEL/data/ops_alerts.log" 2>&1
  echo "$(date '+%F %T') rsshub restart rc=$? (下轮采集验证恢复)" >> "$INTEL/data/ops_alerts.log"
  echo 0 > "$STREAK_FILE"
fi

# 日志滚动保留最近 3000 行
tail -n 3000 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
exit $rc
