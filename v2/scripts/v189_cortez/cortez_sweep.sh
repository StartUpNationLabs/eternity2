#!/usr/bin/env bash
# V189 CORTEZ explicit cp-pinned sweep.
#
# For each of 5 target cps × 8 scans × 6 seeds × 2 temps = 480 builds.
# Filter top 2 per cp by build score → 10 ALNS lifts × 30min.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-189/cortez_$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/builds" "$OUT/logs"
echo "[v189-cortez] out=$OUT" | tee "$OUT/_meta.log"

# 5 target cps. The fifth (2,1,0,3) was NOT hit in wide sweep; pinning makes it tractable.
CPS=(
  "0,2,3,1"
  "1,3,0,2"
  "1,0,2,3"
  "2,0,1,3"
  "2,1,0,3"
)
TAGS=(cp0231 cp1302 cp1023 cp2013 cp2103)
SCANS=(row row_rev col col_rev zigzag zigzag_rev spiral_in spiral_out)
SEEDS=(1 7 13 42 99 211)
TEMPS=(0.05 0.10)
PRIOR=scripts/v155_prior/prior_matrix_high459.json
PHER=output/vol-178/pheromone_init.json
PATCH=output/vol-181/patch_prior.json
BATCH=8

echo "[v189-cortez] STAGE 1: ${#CPS[@]}×${#SCANS[@]}×${#SEEDS[@]}×${#TEMPS[@]}=$((${#CPS[@]} * ${#SCANS[@]} * ${#SEEDS[@]} * ${#TEMPS[@]})) builds" | tee -a "$OUT/_meta.log"
n=0
for idx in 0 1 2 3 4; do
  cp="${CPS[$idx]}"
  tag="${TAGS[$idx]}"
  for scan in "${SCANS[@]}"; do
    for seed in "${SEEDS[@]}"; do
      for t in "${TEMPS[@]}"; do
        suffix="${tag}_${scan}_s${seed}_t${t}"
        out_json="$OUT/builds/${suffix}.json"
        log="$OUT/logs/build_${suffix}.log"
        nice -n 5 target/bench-fast/v189_cortez \
          --beam-width 256 \
          --prior-file "$PRIOR" \
          --pheromone-file "$PHER" \
          --pheromone-weight 1e-7 \
          --patch-file "$PATCH" \
          --patch-weight 0.1 \
          --dedup-path --dedup-recent 4 \
          --scan "$scan" \
          --seed "$seed" \
          --stochastic-temperature "$t" \
          --target-cp "$cp" \
          --save-best "$out_json" \
          > "$log" 2>&1 &
        n=$((n + 1))
        if [ "$((n % BATCH))" = "0" ]; then
          wait
          if [ "$((n % 80))" = "0" ]; then
            echo "[v189-cortez] $n builds at $(date)" | tee -a "$OUT/_meta.log"
          fi
        fi
      done
    done
  done
done
wait
echo "[v189-cortez] STAGE 1 done $(date), $n builds" | tee -a "$OUT/_meta.log"

# Pick top 2 builds per cp.
echo "[v189-cortez] STAGE 2: pick top builds per cp" | tee -a "$OUT/_meta.log"
TOP_BUILDS=$(uv run python -c "
import json, glob
from collections import defaultdict
tags = ['cp0231', 'cp1302', 'cp1023', 'cp2013', 'cp2103']
by_tag = defaultdict(list)
for b in glob.glob('$OUT/builds/*.json'):
    try: d = json.load(open(b))
    except: continue
    score = d.get('matched', 0)
    for tag in tags:
        if f'/{tag}_' in b:
            by_tag[tag].append((score, b))
            break
for tag in tags:
    by_tag[tag].sort(reverse=True)
    print(f'TAG {tag}: max={by_tag[tag][0][0] if by_tag[tag] else \"N/A\"}', file=__import__('sys').stderr)
    for s, p in by_tag[tag][:2]:
        print(p)
" 2>&1)
# stderr lines come through too; the path lines we want are without slashes inside the cp
echo "$TOP_BUILDS" | tee -a "$OUT/_meta.log"

# Filter just the build paths.
TOP_PATHS=$(echo "$TOP_BUILDS" | grep -E "^output/.*\.json$")

echo "" | tee -a "$OUT/_meta.log"
echo "[v189-cortez] STAGE 3: ALNS lifts × top builds × 30min" | tee -a "$OUT/_meta.log"
n=0
for build in $TOP_PATHS; do
  base=$(basename "$build" .json)
  for seed in 1 42; do
    log="$OUT/logs/lift_${base}_s${seed}.log"
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
      echo "[v189-cortez] $n lifts at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

echo "" | tee -a "$OUT/_meta.log"
echo "[v189-cortez] All done $(date)" | tee -a "$OUT/_meta.log"
echo "[v189-cortez] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  base=$(basename "$log" .log)
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  history=$(grep -c "new_best" "$log" || echo 0)
  echo "  $base: $m  history=$history" | tee -a "$OUT/_meta.log"
done
