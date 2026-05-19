#!/usr/bin/env bash
# V160 — quick-from-scratch + ALNS pipeline.
#
# Tests whether a CHEAP V151/V155 K=64 build (1 sec) + 30min ALNS reaches
# similar scores as the expensive K=4096 + 30min ALNS that hit 460.
#
# Launch via: bash scripts/v160_quick_pipeline/run.sh

set -u

REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-160/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT"
echo "[v160] out=$OUT" | tee "$OUT/_meta.log"

# Stage 1: 3 quick builds (each 1-5 seconds).
echo "[v160] stage 1: quick builds" | tee -a "$OUT/_meta.log"

target/bench-fast/v151_weaving_beam --beam-width 64 > "$OUT/build_v151_k64.log" 2>&1 || true
# v151 doesn't have --save-best; skip and use v155 with k=64 instead.

target/bench-fast/v155_weaving_prior --beam-width 64 --prior-file scripts/v155_prior/prior_matrix.json --dedup-path --dedup-recent 4 --save-best "$OUT/k64_plain.json" > "$OUT/build_k64_plain.log" 2>&1
target/bench-fast/v155_weaving_prior --beam-width 256 --prior-file scripts/v155_prior/prior_matrix.json --dedup-path --dedup-recent 4 --save-best "$OUT/k256_plain.json" > "$OUT/build_k256_plain.log" 2>&1
target/bench-fast/v155_weaving_prior --beam-width 64 --prior-file scripts/v155_prior/prior_matrix_high459.json --dedup-path --dedup-recent 4 --save-best "$OUT/k64_high459.json" > "$OUT/build_k64_high459.log" 2>&1
target/bench-fast/v155_weaving_prior --beam-width 256 --prior-file scripts/v155_prior/prior_matrix_high459.json --dedup-path --dedup-recent 4 --save-best "$OUT/k256_high459.json" > "$OUT/build_k256_high459.log" 2>&1

# Rescore each.
echo "[v160] build results:" | tee -a "$OUT/_meta.log"
for f in "$OUT"/k*.json; do
  if [ -f "$f" ]; then
    score=$(target/bench-fast/rescore_board "$f" | tail -1 | awk '{print $3}')
    echo "  $(basename "$f"): $score" | tee -a "$OUT/_meta.log"
  fi
done

# Stage 2: ALNS each build × 4 seeds × basic_lkh (best ops from V156 round 1).
echo "[v160] stage 2: ALNS each build" | tee -a "$OUT/_meta.log"
mkdir -p "$OUT/alns"

for build_file in "$OUT"/k*.json; do
  [ -f "$build_file" ] || continue
  base=$(basename "$build_file" .json)
  for seed in 1 7 13 42; do
    log="$OUT/alns/${base}_s${seed}_lkh.log"
    target/bench-fast/alns_only \
      --cp-board "$build_file" \
      --ops basic_lkh \
      --alns-budget-ms 1800000 \
      --seed "$seed" \
      > "$log" 2>&1 &
  done
done

# Wait. 4 builds × 4 seeds = 16 ALNS jobs, on 10 cores → throttled but OK.
echo "[v160] waiting for $(jobs -p | wc -l) ALNS jobs..." | tee -a "$OUT/_meta.log"
wait
echo "[v160] all ALNS jobs done" | tee -a "$OUT/_meta.log"

# Aggregate ALNS results.
echo "[v160] ALNS results:" | tee -a "$OUT/_meta.log"
for log in "$OUT/alns"/*.log; do
  base=$(basename "$log" .log)
  best=$(grep -oE "new_best=[0-9]+" "$log" | sort -t= -k2 -n | tail -1 | cut -d= -f2)
  echo "  $base: best=$best" | tee -a "$OUT/_meta.log"
done

echo "[v160] done $(date)" | tee -a "$OUT/_meta.log"
