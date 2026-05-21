#!/usr/bin/env bash
# V198 ALNS lifts on V198 50K-CSP-fill 244-class partials.
# 2 boards × 8 seeds × 30min × basic_lkh = 16 jobs.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-198/alns_244s_$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v198-alns] out=$OUT" | tee "$OUT/_meta.log"

BASES=(
  "output/vol-198/holefilled_50k_20260521T013401/p_off214192.json"
  "output/vol-198/holefilled_50k_20260521T013401/p_off115340.json"
)
SEEDS=(1 7 13 42 99 211 313 419)
PRIOR=scripts/v155_prior/prior_matrix_high459.json
BATCH=8

n=0
for base in "${BASES[@]}"; do
  bn=$(basename "$base" .json | sed 's/^p_//')
  for seed in "${SEEDS[@]}"; do
    tag="${bn}_s${seed}"
    log="$OUT/logs/alns_${tag}.log"
    nice -n 5 target/bench-fast/alns_only \
      --cp-board "$base" \
      --alns-budget-ms 1800000 \
      --seed "$seed" \
      --ops basic_lkh \
      --prior-destroy "$PRIOR" \
      --lex-intaglio \
      --repair-kind sa --t 1.0 \
      > "$log" 2>&1 &
    n=$((n+1))
    if [ "$((n % BATCH))" = "0" ]; then
      wait
      echo "[v198-alns] $n ALNS at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

echo "[v198-alns] Done $(date)" | tee -a "$OUT/_meta.log"
echo "" | tee -a "$OUT/_meta.log"
for f in $OUT/logs/*.log; do
  bn=$(basename $f .log)
  m=$(grep -oE 'matched=[0-9]+/480' $f | tail -1 | grep -oE '[0-9]+' | head -1)
  hist=$(grep -c "new_best" $f 2>/dev/null)
  echo "  $bn: $m history=$hist" | tee -a "$OUT/_meta.log"
done
