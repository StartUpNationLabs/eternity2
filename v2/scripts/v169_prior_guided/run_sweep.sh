#!/usr/bin/env bash
# V169 — PRIOR-GUIDED ALNS sweep on V155→ALNS 460 boards.
#
# Hypothesis (vol-169 2026-05-20): standard ALNS plateaued at 460 because
# its destroy ops don't see corpus-support. PriorDestroy with β > 0
# (escape mode) targets corpus-anchored cells, breaking out of the 460
# basin attractor.
#
# Probe finding: V155→ALNS 460 has 186-191 unsupported cells, but the
# remaining ~65 supported cells are what keep us in the 460 basin.
# PriorDestroy targets those.
#
# Sweep: 2 bases × 8 seeds = 16 jobs. 30 min each. 8-way parallel = 60min.
# Compare against vol-156 round-2 baseline (basic_lkh, same bases).

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-169/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/boards" "$OUT/logs"
echo "[v169] out=$OUT" | tee "$OUT/_meta.log"

PRIOR=scripts/v155_prior/prior_matrix_high459.json
BASES=(
  "output/vol-155/RECORD_460_alns_from_456_seed1_lkh.json:s1cp0321"
  "output/vol-155/RECORD_460_alns_from_456_seed13_lkh.json:s13cp0312"
)

BUDGET_MS=1800000  # 30 min
SEEDS=(1 7 13 42 99 142 200 333)
BATCH=8

n=0
for base_pair in "${BASES[@]}"; do
  base="${base_pair%%:*}"
  tag="${base_pair##*:}"
  for seed in "${SEEDS[@]}"; do
    out_json="$OUT/boards/${tag}_seed${seed}.json"
    log="$OUT/logs/${tag}_seed${seed}.log"
    echo "[v169] launching $tag seed=$seed -> $log" | tee -a "$OUT/_meta.log"
    nice -n 5 target/bench-fast/alns_only \
      --cp-board "$base" \
      --alns-budget-ms "$BUDGET_MS" \
      --seed "$seed" \
      --ops basic_lkh \
      --prior-destroy "$PRIOR" \
      --repair-kind sa --t 1.0 \
      > "$log" 2>&1 &
    n=$((n + 1))
    if [ "$((n % BATCH))" = "0" ]; then
      wait
      echo "[v169] batch of $BATCH done at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

echo "[v169] all $n jobs done at $(date)" | tee -a "$OUT/_meta.log"

# Aggregate.
echo "" | tee -a "$OUT/_meta.log"
echo "[v169] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/*.log; do
  tag=$(basename "$log" .log)
  best=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  echo "  $tag: best=$best" | tee -a "$OUT/_meta.log"
done

# Distribution.
echo "" | tee -a "$OUT/_meta.log"
echo "[v169] score distribution:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/*.log; do
  grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1
done | sort -n | uniq -c | tee -a "$OUT/_meta.log"

# Op invocation summary (sanity check ops fired).
echo "" | tee -a "$OUT/_meta.log"
echo "[v169] PriorDestroy invocation summary:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/*.log; do
  tag=$(basename "$log" .log)
  esc05=$(grep -E "prior_escape_b0.5" "$log" | grep -oE 'inv=[0-9]+' | grep -oE '[0-9]+')
  esc20=$(grep -E "prior_escape_b2.0" "$log" | grep -oE 'inv=[0-9]+' | grep -oE '[0-9]+')
  att=$(grep -E "prior_attract" "$log" | grep -oE 'inv=[0-9]+' | grep -oE '[0-9]+')
  echo "  $tag: esc0.5=$esc05 esc2.0=$esc20 att=$att" | tee -a "$OUT/_meta.log"
done

echo "[v169] done $(date)" | tee -a "$OUT/_meta.log"
