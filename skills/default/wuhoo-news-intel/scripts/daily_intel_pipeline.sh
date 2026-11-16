#!/usr/bin/env bash
# WP6 daily intel pipeline (B轨 shadow): fetch → embed+cluster → brief(top10) → publish web。
# deliver local，不推微信；A/B 双轨切换待 WP7 盲评 + 用户拍板 (D3-A)。flock 防并发。
# 裸 python3.11（避免 /usr/bin/python3.11 触发 lifecycle guard ELF 崩溃）。
set -uo pipefail
INTEL=/home/admin/wuhoo-workspace/skills/default/wuhoo-news-intel
SRC="$INTEL/src"
STAMP=$(date +%Y-%m-%d)
LOG="$INTEL/data/pipeline_${STAMP//-/}.log"
LOCK=/tmp/wuhoo_news_intel_daily.lock
mkdir -p "$INTEL/data"
exec 9>"$LOCK"
if ! flock -n 9; then echo "$(date '+%F %T') SKIP daily lock-busy" >> "$LOG"; exit 0; fi
{
  echo "=== $(date '+%F %T %Z') daily intel pipeline START ==="
  bash "$INTEL/scripts/rss_hourly_fetch.sh"; echo "fetch rc=$?"
  python3.11 "$SRC/event_center.py" run --window 72; echo "event_run rc=$?"
  python3.11 "$SRC/intel.py" brief --top 10 --date "$STAMP" --format web --budget 60000; echo "brief rc=$?"
  echo "=== $(date '+%F %T %Z') DONE ==="
} >> "$LOG" 2>&1
tail -n 14 "$LOG"
