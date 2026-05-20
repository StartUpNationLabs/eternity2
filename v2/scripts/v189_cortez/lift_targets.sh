#!/usr/bin/env bash
# Lift the highest-scoring V189 build in each target cp using 30min KEYRING+ALNS.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-189/lifts_$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v189-lift] out=$OUT" | tee "$OUT/_meta.log"

# Top builds per target cp (from sweep_20260520T170600 analysis):
BUILDS=(
  "output/vol-189/sweep_20260520T170600/builds/row_rev_s13_t0.10.json"      # cp=(0,2,3,1) 453
  "output/vol-189/sweep_20260520T170600/builds/col_rev_s521_t0.10.json"     # cp=(1,3,0,2) 450
  "output/vol-189/sweep_20260520T170600/builds/spiral_out_s313_t0.15.json"  # cp=(1,0,2,3) 442
  "output/vol-189/sweep_20260520T170600/builds/spiral_out_s727_t0.15.json"  # cp=(2,0,1,3) 439
)
TAGS=(cp0231_453 cp1302_450 cp1023_442 cp2013_439)
SEEDS=(42 1 7 99)
PRIOR=scripts/v155_prior/prior_matrix_high459.json

# 4 builds × 4 seeds = 16 ALNS jobs, 8 parallel.
BATCH=8
n=0
for i in 0 1 2 3; do
  build="${BUILDS[$i]}"
  tag="${TAGS[$i]}"
  base_score=$(uv run python -c "import json; print(json.load(open('$build')).get('matched',0))")
  echo "[v189-lift] base $tag: $build score=$base_score" | tee -a "$OUT/_meta.log"
  for seed in "${SEEDS[@]}"; do
    log="$OUT/logs/lift_${tag}_s${seed}.log"
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
      echo "[v189-lift] $n lifts at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

echo "[v189-lift] All done $(date)" | tee -a "$OUT/_meta.log"
echo "" | tee -a "$OUT/_meta.log"
echo "[v189-lift] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/*.log; do
  base=$(basename "$log" .log)
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  history=$(grep -c "new_best" "$log" || echo 0)
  echo "  $base: $m  history=$history" | tee -a "$OUT/_meta.log"
done
