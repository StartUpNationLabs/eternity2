#!/usr/bin/env bash
# V193-T2 — 50K bf_bw source partials, 2s budget each.
# Goal: 10× variance over the 5000 sample → expect best-of-50K to push
# 244 → 248-252 after repair+fill.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-193/bfbw_50k_$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/partials" "$OUT/logs"
echo "[v193-50k] out=$OUT" | tee "$OUT/_meta.log"

N=50000
BUDGET_MS=${BUDGET_MS:-2000}
BATCH=${BATCH:-8}
echo "[v193-50k] N=$N budget=${BUDGET_MS}ms batch=$BATCH" | tee -a "$OUT/_meta.log"

OFFSETS=$(uv run python -c "
import numpy as np
arr = np.linspace(50, 500000, $N).astype(int).tolist()
print(' '.join(map(str, arr)))
")

n=0
for off in $OFFSETS; do
  out_json="$OUT/partials/p_off${off}.json"
  log="$OUT/logs/p_off${off}.log"
  nice -n 5 target/bench-fast/bf_bw \
    --budget-ms "$BUDGET_MS" \
    --seed-offset "$off" \
    --dump-partial "$out_json" \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    if [ "$((n % 1000))" = "0" ]; then
      echo "[v193-50k] $n / $N at $(date)" | tee -a "$OUT/_meta.log"
    fi
  fi
done
wait
echo "[v193-50k] generated $n partials $(date)" | tee -a "$OUT/_meta.log"
echo "[v193-50k] out=$OUT"
