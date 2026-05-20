#!/usr/bin/env bash
# V175 GAUNTLET LONG-LIFT — 30-min ALNS lift on top GAUNTLET outputs.
#
# Stage 2 of V175 used 5min ALNS lifts; max score 455. Hypothesis: with
# 30min lifts (same as V156 original pipeline), the diverse GAUNTLET
# starts may reach 460+ in NEW basins.
#
# Strategy: take top-K builds by score, 30min × multiple seeds each.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

# Find latest V175 dir
V175_DIR=$(ls -dt output/vol-175/2*/ 2>/dev/null | head -1)
if [ -z "$V175_DIR" ]; then
  echo "ERROR: no V175 dir found"
  exit 1
fi
echo "V175 dir: $V175_DIR"

OUT=output/vol-175/long_lift_$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v175-long] out=$OUT" | tee "$OUT/_meta.log"

PRIOR=scripts/v155_prior/prior_matrix_high459.json

# Find top-8 V175 builds by build-score.
TOP_BUILDS=$(uv run python -c "
import json, glob
boards = sorted(glob.glob('$V175_DIR/builds/*.json'))
scored = []
for b in boards:
    try: d = json.load(open(b))
    except: continue
    scored.append((d.get('matched', 0), b))
scored.sort(reverse=True)
for s, p in scored[:8]:
    print(p)
")

echo "Top 8 V175 builds by score:" | tee -a "$OUT/_meta.log"
for b in $TOP_BUILDS; do
  s=$(jq -r '.matched' "$b")
  echo "  $s  $b" | tee -a "$OUT/_meta.log"
done

# Stage 1: 30min ALNS × 1 seed per top-8 build (8 jobs = 8 cores × 30min)
SEEDS=(42)
BATCH=8
n=0
for build in $TOP_BUILDS; do
  base=$(basename "$build" .json)
  for seed in "${SEEDS[@]}"; do
    log="$OUT/logs/lift_${base}_s${seed}.log"
    echo "[v175-long] launching $base seed=$seed" | tee -a "$OUT/_meta.log"
    nice -n 5 target/bench-fast/alns_only \
      --cp-board "$build" \
      --alns-budget-ms 1800000 \
      --seed "$seed" \
      --ops basic_lkh \
      --prior-destroy "$PRIOR" \
      --lex-intaglio \
      --repair-kind sa --t 1.0 \
      > "$log" 2>&1 &
    n=$((n + 1))
    if [ "$((n % BATCH))" = "0" ]; then
      wait
      echo "[v175-long] $n done at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

# Report.
echo "" | tee -a "$OUT/_meta.log"
echo "[v175-long] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  base=$(basename "$log" .log | sed 's/lift_//')
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  history=$(grep -A 30 "best_score_history" "$log" | grep "iter=" | wc -l | tr -d ' ')
  echo "  $base: best=$m  history_entries=$history" | tee -a "$OUT/_meta.log"
done

echo "[v175-long] done $(date)" | tee -a "$OUT/_meta.log"
