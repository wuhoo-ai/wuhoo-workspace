#!/bin/bash
# skills → wuhoo-skills 发布镜像同步(白名单导出, 单向: workspace → publish)
# 用法: bash scripts/sync_skills_to_publish.sh [skill_name ...]   不带参数=全部白名单
set -eu
SRC=/home/admin/wuhoo-workspace/skills
DST=/home/admin/wuhoo-skills/skills
# 白名单 = 可对外发布件(手动维护; infra 属内部运维知识不发布)
WHITELIST=(
  wuhoo-debate wuhoo-futuapi wuhoo-futures-pick wuhoo-futures-trade
  wuhoo-lottery-ssq wuhoo-stock-deep-analysis wuhoo-stock-pick
  wuhoo-trade wuhoo-trade-diagnose wuhoo-value-investing
  wuhoo-news-rss wuhoo-rss-briefing wuhoo-football-predictor
  wuhoo-art-pipeline wuhoo-game-arch wuhoo-game-art wuhoo-game-audio
  wuhoo-game-balance wuhoo-game-ci wuhoo-game-debug wuhoo-game-exec
  wuhoo-game-gates wuhoo-game-gpu wuhoo-game-plan wuhoo-game-review
  wuhoo-game-scene wuhoo-game-voice wuhoo-sprite-pipeline wuhoo-ui-ugui
  wuhoo-unity-headless wuhoo-unity-reference wuhoo-skill-testing
)
names=("$@")
[ ${#names[@]} -eq 0 ] && names=("${WHITELIST[@]}")
mkdir -p "$DST"
for n in "${names[@]}"; do
  src=$(find "$SRC" -maxdepth 2 -type d -name "$n" | head -1)
  if [ -z "$src" ]; then echo "MISS $n"; continue; fi
  rm -rf "$DST/$n"
  cp -r "$src" "$DST/$n"
  find "$DST/$n" -type d \( -name data -o -name __pycache__ -o -name .hermes -o -name .venv \) -prune -exec rm -rf {} + 2>/dev/null || true
  echo "sync $n ($(basename $(dirname $src))/)"
done
cd /home/admin/wuhoo-skills
git add -A skills
if git diff --cached --quiet; then echo "publish repo no change"; else
  git commit -m "sync: $(date +%F) skills export from workspace" -q
  git push -q origin HEAD 2>/dev/null || git push -q
  echo "publish repo pushed"
fi
