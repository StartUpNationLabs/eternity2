#!/usr/bin/env bash
# V172 CHIASMUS — clean driver.
#
# Usage: ./run_clean.sh [input_glob]
#   Default input: V175 GAUNTLET lifted outputs (output/v17_alns_only/*).
#
# Pipeline:
#   1. gen_hybrids.py: top-N distinct-cp inputs → all-pairs × 4 schemes.
#   2. ALNS-fill each hybrid (5 min × 8-way parallel).
#   3. Report scores, cluster by output cp.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

# Default input pattern: V175 outputs (or whatever was passed)
INPUT_GLOB="${1:-output/vol-175/*/builds/*.json output/v17_alns_only/*.json}"
OUT=output/vol-172/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/hybrids" "$OUT/logs"
echo "[v172] out=$OUT" | tee "$OUT/_meta.log"
echo "[v172] input_glob=$INPUT_GLOB" | tee -a "$OUT/_meta.log"

# Stage 1: generate hybrids.
uv run python scripts/v172_chiasmus/gen_hybrids.py \
  --inputs $INPUT_GLOB \
  --out-dir "$OUT/hybrids" \
  --top-n 8 \
  --min-score 440 \
  2>&1 | tee -a "$OUT/_meta.log"

# Stage 2: ALNS-fill each hybrid.
echo "" | tee -a "$OUT/_meta.log"
echo "[v172] STAGE 2: ALNS-fill, 5min each, 8-way parallel" | tee -a "$OUT/_meta.log"
n=0
BATCH=8
PRIOR=scripts/v155_prior/prior_matrix_high459.json
for hyb in "$OUT/hybrids"/*.json; do
  base=$(basename "$hyb" .json)
  log="$OUT/logs/lift_${base}.log"
  nice -n 5 target/bench-fast/alns_only \
    --cp-board "$hyb" \
    --alns-budget-ms 300000 \
    --seed 42 \
    --ops basic_lkh \
    --prior-destroy "$PRIOR" \
    --repair-kind sa --t 1.5 \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    echo "[v172] $n lifts done at $(date)" | tee -a "$OUT/_meta.log"
  fi
done
wait

# Results.
echo "" | tee -a "$OUT/_meta.log"
echo "[v172] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  base=$(basename "$log" .log | sed 's/lift_//')
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  echo "  $base: $m" | tee -a "$OUT/_meta.log"
done

# Distribution.
echo "" | tee -a "$OUT/_meta.log"
echo "[v172] Score distribution:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1
done | sort -rn | uniq -c | tee -a "$OUT/_meta.log"

# Top 5.
echo "" | tee -a "$OUT/_meta.log"
echo "[v172] Top 5 lifts:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  base=$(basename "$log" .log | sed 's/lift_//')
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  echo "$m $base"
done | sort -rn | head -5 | tee -a "$OUT/_meta.log"

echo "[v172] done $(date)" | tee -a "$OUT/_meta.log"
