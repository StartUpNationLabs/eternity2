#!/usr/bin/env bash
# V161 — V155 time-budget scaling experiment.
#
# User question "What if we ran V155 for 1 min? 10 min?"
#
# Honest answer: V155 is deterministic given (K, prior). More time = more K.
# K scaling table:
#   K=1024  ~20s
#   K=4096  ~120s   (2 min)
#   K=8192  ~5 min
#   K=16384 ~10 min
#   K=32768 ~20 min
#
# Default-prior V155 saturates at 456 by K=4096. More K with default
# prior doesn't help.
#
# Sharp-prior (high459) V155 hit 460 at K=4096 (4 min). Untested: does
# K=8192, K=16384 with sharp prior break 460?
#
# This script runs 8 sharp-prior V155 variants in parallel, spanning K
# from 1024 to 32768. Total wallclock ~20 min on 8 cores.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-161/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT"
echo "[v161] out=$OUT" | tee "$OUT/_meta.log"
echo "[v161] running 8 V155 variants in parallel" | tee -a "$OUT/_meta.log"

declare -a CONFIGS=(
  # (K, prior-file, dedup-recent, scan)
  "1024  scripts/v155_prior/prior_matrix_high459.json 4  row"
  "2048  scripts/v155_prior/prior_matrix_high459.json 4  row"
  "4096  scripts/v155_prior/prior_matrix_high459.json 4  row"
  "8192  scripts/v155_prior/prior_matrix_high459.json 4  row"
  "16384 scripts/v155_prior/prior_matrix_high459.json 8  row"
  "4096  scripts/v155_prior/prior_matrix_high460.json 4  row"
  "4096  scripts/v155_prior/prior_matrix_high459.json 4  col"
  "8192  scripts/v155_prior/prior_matrix_high459.json 16 row"
)

for i in "${!CONFIGS[@]}"; do
  read -r K prior dedup scan <<< "${CONFIGS[$i]}"
  log="$OUT/v$(printf %02d "$i")_K${K}_$(basename "$prior" .json)_d${dedup}_${scan}.log"
  best="$OUT/v$(printf %02d "$i")_best.json"
  echo "[v161] launching #$i: K=$K prior=$prior dedup=$dedup scan=$scan" | tee -a "$OUT/_meta.log"
  target/bench-fast/v155_weaving_prior \
    --beam-width "$K" \
    --prior-file "$prior" \
    --dedup-path \
    --dedup-recent "$dedup" \
    --scan "$scan" \
    --save-best "$best" \
    > "$log" 2>&1 &
done

wait
echo "[v161] all done" | tee -a "$OUT/_meta.log"

# Aggregate.
echo "[v161] results:" | tee -a "$OUT/_meta.log"
for log in "$OUT"/v*.log; do
  base=$(basename "$log" .log)
  best=$(grep -oE '"best_score":[0-9]+' "$log" | head -1 | cut -d: -f2)
  elapsed=$(grep -oE '"elapsed_ms":[0-9]+' "$log" | head -1 | cut -d: -f2)
  if [ -n "$best" ]; then
    sec=$((elapsed / 1000))
    echo "  $base: best=$best elapsed=${sec}s" | tee -a "$OUT/_meta.log"
  fi
done
