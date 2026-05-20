#!/usr/bin/env bash
# V181 KEYRING + V179 LARGE-K + V180 INTAGLIO-ATTACK combined sweep.
#
# Uses v181_keyring builder (patch prior + pheromone + corpus prior)
# with stochastic temperature for diversity, then 30min ALNS with the
# full V179+V180 op suite.
#
# 36 builds (9 scans × 4 seeds), top-8 by score → 30min ALNS each.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-181/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/builds" "$OUT/logs"
echo "[v181] out=$OUT" | tee "$OUT/_meta.log"

SCANS=(row row_rev col col_rev zigzag zigzag_rev spiral_in spiral_out diagonal)
SEEDS=(1 7 42 99)
PRIOR=scripts/v155_prior/prior_matrix_high459.json
PHER=output/vol-178/pheromone_init.json
PATCH=output/vol-181/patch_prior.json
PATCH_W=0.1
PHER_W=1e-7
TEMP=0.05
BATCH=8

# Stage 1: V181 KEYRING builds.
echo "[v181] STAGE 1: ${#SCANS[@]}*${#SEEDS[@]}=$((${#SCANS[@]}*${#SEEDS[@]})) builds with patch+pheromone+prior" | tee -a "$OUT/_meta.log"
n=0
for scan in "${SCANS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    tag="${scan}_s${seed}"
    out_json="$OUT/builds/${tag}.json"
    log="$OUT/logs/build_${tag}.log"
    nice -n 5 target/bench-fast/v181_keyring \
      --beam-width 256 \
      --prior-file "$PRIOR" \
      --pheromone-file "$PHER" \
      --pheromone-weight "$PHER_W" \
      --patch-file "$PATCH" \
      --patch-weight "$PATCH_W" \
      --dedup-path --dedup-recent 4 \
      --scan "$scan" \
      --seed "$seed" \
      --stochastic-temperature "$TEMP" \
      --save-best "$out_json" \
      > "$log" 2>&1 &
    n=$((n + 1))
    if [ "$((n % BATCH))" = "0" ]; then
      wait
      echo "[v181] $n builds done at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

# Pick top 8 by build score.
echo "" | tee -a "$OUT/_meta.log"
TOP_BUILDS=$(uv run python -c "
import json, glob
boards = sorted(glob.glob('$OUT/builds/*.json'))
scored = []
for b in boards:
    try: d = json.load(open(b))
    except: continue
    scored.append((d.get('matched', 0), b))
scored.sort(reverse=True)
for s, p in scored[:8]:
    print(p)
")
echo "Top 8 builds:" | tee -a "$OUT/_meta.log"
for b in $TOP_BUILDS; do
  s=$(jq -r '.matched' "$b")
  echo "  $s  $b" | tee -a "$OUT/_meta.log"
done

# Stage 2: 30min ALNS lifts on top 8.
echo "" | tee -a "$OUT/_meta.log"
echo "[v181] STAGE 2: 30min ALNS lifts × top 8" | tee -a "$OUT/_meta.log"
n=0
for build in $TOP_BUILDS; do
  base=$(basename "$build" .json)
  log="$OUT/logs/lift_${base}.log"
  nice -n 5 target/bench-fast/alns_only \
    --cp-board "$build" \
    --alns-budget-ms 1800000 \
    --seed 42 \
    --ops basic_lkh \
    --prior-destroy "$PRIOR" \
    --lex-intaglio \
    --repair-kind sa --t 1.0 \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    echo "[v181] $n lifts done at $(date)" | tee -a "$OUT/_meta.log"
  fi
done
wait

# Results.
echo "" | tee -a "$OUT/_meta.log"
echo "[v181] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  base=$(basename "$log" .log)
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  history=$(grep -c "iter=.*new_best" "$log")
  echo "  $base: best=$m  history=$history" | tee -a "$OUT/_meta.log"
done

echo "[v181] done $(date)" | tee -a "$OUT/_meta.log"
