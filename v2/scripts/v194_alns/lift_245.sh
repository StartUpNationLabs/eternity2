#!/usr/bin/env bash
# V194 ALNS lifts on the 245 clean partial.
# Multi-seed × multi-ops × 30min budget.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

BASE=output/vol-193/multistart_20260520T215848/BEST_placed245_score441.json
OUT=output/vol-194/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v194] out=$OUT" | tee "$OUT/_meta.log"
echo "[v194] base: $BASE (245 placed, score 441 raw)" | tee -a "$OUT/_meta.log"

SEEDS=(1 7 13 42 99 211 313 419)
OPSETS=(basic basic_lkh)
BUDGET_MS=1800000  # 30 min
BATCH=8

n=0
for ops in "${OPSETS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    tag="${ops}_s${seed}"
    log="$OUT/logs/${tag}.log"
    nice -n 5 target/bench-fast/alns_only \
      --cp-board "$BASE" \
      --alns-budget-ms "$BUDGET_MS" \
      --seed "$seed" \
      --ops "$ops" \
      --repair-kind sa --t 1.0 \
      > "$log" 2>&1 &
    n=$((n + 1))
    if [ "$((n % BATCH))" = "0" ]; then
      wait
      echo "[v194] $n lifts at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

echo "[v194] All done $(date)" | tee -a "$OUT/_meta.log"
echo "[v194] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/*.log; do
  base=$(basename "$log" .log)
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  history=$(grep -c "new_best" "$log" || true)
  echo "  $base: $m  history=$history" | tee -a "$OUT/_meta.log"
done

uv run python -c "
import json, glob, re
for log in sorted(glob.glob('$OUT/logs/*.log')):
    with open(log) as f: content = f.read()
    m = re.search(r'matched=(\d+)/480', content)
    sm = re.findall(r'saved:\s*(\S+)', content)
    if m and sm:
        print(f'{log.split(\"/\")[-1]}: matched={m.group(1)} saved={sm[-1]}')
" 2>&1 | tee -a "$OUT/_meta.log"

echo "[v194] done" | tee -a "$OUT/_meta.log"
