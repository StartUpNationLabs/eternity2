#!/usr/bin/env bash
# V169-v2 — PriorDestroy on V155-DIRECT 460 (the corpus-locked basin).
#
# V169-v1 (run_sweep.sh) tested on V155→ALNS 460 boards which had
# 186-191 unsupported cells out of 256 — already corpus-orthogonal,
# so PriorDestroy escape (β>0) had nothing to escape from.
#
# This v2 targets V155-direct best_high459.json which has ONLY 5
# unsupported cells. PriorDestroy β>0 should aggressively destroy the
# corpus-anchored placements; repair lands in (potentially novel) basins.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-169/v2_$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v169-v2] out=$OUT" | tee "$OUT/_meta.log"

BASE=output/vol-155/best_high459.json
PRIOR=scripts/v155_prior/prior_matrix_high459.json

BUDGET_MS=1800000  # 30 min
SEEDS=(1 7 13 42 99 142 200 333)
BATCH=8

for seed in "${SEEDS[@]}"; do
  log="$OUT/logs/seed${seed}.log"
  echo "[v169-v2] launching seed=$seed -> $log" | tee -a "$OUT/_meta.log"
  nice -n 5 target/bench-fast/alns_only \
    --cp-board "$BASE" \
    --alns-budget-ms "$BUDGET_MS" \
    --seed "$seed" \
    --ops basic_lkh \
    --prior-destroy "$PRIOR" \
    --repair-kind sa --t 1.0 \
    > "$log" 2>&1 &
done
wait
echo "[v169-v2] all jobs done at $(date)" | tee -a "$OUT/_meta.log"

echo "" | tee -a "$OUT/_meta.log"
echo "[v169-v2] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/*.log; do
  base=$(basename "$log" .log)
  best=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  history=$(grep -A 20 "best_score_history" "$log" | grep "iter=" | wc -l | tr -d ' ')
  echo "  $base: best=$best  history_entries=$history" | tee -a "$OUT/_meta.log"
done

echo "[v169-v2] done $(date)" | tee -a "$OUT/_meta.log"
