#!/usr/bin/env bash
# V162 — seed-randomized V155 sweep.
#
# V155 with --seed N randomizes tie-breaking when (score, prior_sum) ties
# at the beam K-cutoff. Different seeds → different beam survivors →
# different final boards.
#
# Best known V155 config: K=4096 + high459-prior + path-dedup-4 → 460.
# Run this with 16 different seeds in parallel (2 batches of 8) to see
# distribution of final scores.
#
# Hypothesis: most seeds → 460 (deterministic). Maybe 1-2 seeds → 461
# by lucky tie-breaks finding a slightly different basin.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-162/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT"
echo "[v162] out=$OUT" | tee "$OUT/_meta.log"

# Best config: K=4096 + high459-prior + path-dedup-4.
PRIOR=scripts/v155_prior/prior_matrix_high459.json
K=4096
DEDUP=4

# 16 seeds, 2 batches of 8 in parallel.
for batch_start in 1 9; do
  echo "[v162] batch starting seed $batch_start" | tee -a "$OUT/_meta.log"
  for s in $(seq "$batch_start" $((batch_start+7))); do
    log="$OUT/seed${s}.log"
    best="$OUT/seed${s}_best.json"
    target/bench-fast/v155_weaving_prior \
      --beam-width "$K" \
      --prior-file "$PRIOR" \
      --dedup-path --dedup-recent "$DEDUP" \
      --seed "$s" \
      --save-best "$best" \
      > "$log" 2>&1 &
  done
  wait
  echo "[v162] batch starting $batch_start done at $(date)" | tee -a "$OUT/_meta.log"
done

# Aggregate.
echo "[v162] all seeds done, aggregating" | tee -a "$OUT/_meta.log"
echo "[v162] results:" | tee -a "$OUT/_meta.log"
for log in "$OUT"/seed*.log; do
  s=$(basename "$log" .log)
  best=$(grep -oE '"best_score":[0-9]+' "$log" | head -1 | cut -d: -f2)
  elapsed=$(grep -oE '"elapsed_ms":[0-9]+' "$log" | head -1 | cut -d: -f2)
  if [ -n "$best" ]; then
    sec=$((elapsed / 1000))
    echo "  $s: best=$best elapsed=${sec}s" | tee -a "$OUT/_meta.log"
  fi
done

# Summary stats.
echo "" | tee -a "$OUT/_meta.log"
echo "[v162] score distribution:" | tee -a "$OUT/_meta.log"
for log in "$OUT"/seed*.log; do
  grep -oE '"best_score":[0-9]+' "$log" | head -1 | cut -d: -f2
done | sort | uniq -c | tee -a "$OUT/_meta.log"
