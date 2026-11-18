#!/usr/bin/env bash
# WP6 daily intel pipeline (B轨 shadow): fetch → embed+cluster → brief(top10) → portal → publish web。
# deliver local，不推微信；A/B 双轨切换待 WP7 盲评 + 用户拍板 (D3-A)。flock 防并发。
# 裸 python3.11（避免 /usr/bin/python3.11 触发 lifecycle guard ELF 崩溃）。
# 2026-11-17 P0-1: brief 前源健康闸门 — 覆盖率<0.70 时告警+等300s重采一次(有界单重试),
# 仍降级则 brief 自动在 HTML/微信文本标注"源覆盖降级"(intel.py read_coverage)。
# 2026-11-17 门户: $1=edition(morning默认/evening), brief 后跑 portal.py build(13类目+兴趣深挖+热榜交叉)。
set -uo pipefail
INTEL=/home/admin/wuhoo-workspace/skills/default/wuhoo-news-intel
SRC="$INTEL/src"
EDITION="${1:-morning}"
STAMP=$(date +%Y-%m-%d)
LOG="$INTEL/data/pipeline_${STAMP//-/}.log"
LOCK=/tmp/wuhoo_news_intel_daily.lock
mkdir -p "$INTEL/data"
exec 9>"$LOCK"
if ! flock -n 9; then echo "$(date '+%F %T') SKIP daily lock-busy" >> "$LOG"; exit 0; fi
{
  echo "=== $(date '+%F %T %Z') daily intel pipeline START edition=$EDITION ==="
  bash "$INTEL/scripts/rss_hourly_fetch.sh"; echo "fetch rc=$?"
  RATIO=$(python3.11 -c "import json;print(json.load(open('$INTEL/data/source_coverage.json')).get('ratio',1))" 2>/dev/null || echo 1)
  if python3.11 -c "exit(0 if float('$RATIO' or 1) < 0.70 else 1)"; then
    echo "$(date '+%F %T') ALERT 源覆盖率 $RATIO < 0.70, 300s 后重采一次(有界单重试)" >> "$INTEL/data/ops_alerts.log"
    echo "ALERT 源覆盖率 $RATIO < 0.70, sleep 300 重采"
    sleep 300
    bash "$INTEL/scripts/rss_hourly_fetch.sh"; echo "refetch rc=$?"
  fi
  python3.11 "$SRC/event_center.py" run --window 72; echo "event_run rc=$?"
  python3.11 "$SRC/intel.py" brief --top 10 --date "$STAMP" --format web --budget 60000; echo "brief rc=$?"
  python3.11 "$SRC/portal.py" build --edition "$EDITION" --budget 120000; echo "portal rc=$?"
  echo "=== $(date '+%F %T %Z') DONE ==="
} >> "$LOG" 2>&1
tail -n 22 "$LOG"
