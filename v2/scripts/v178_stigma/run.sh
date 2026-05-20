#!/usr/bin/env bash
# V178 STIGMA — multi-scan + pheromone-guided beam search + ALNS lift.
#
# V178 builds at λ=1e-7 give +4-5 score over V175 baseline.
# This driver: 9 scans × 4 seeds × pheromone = 36 builds, then ALNS lift.
#
# Each build ~12s; total stage 1 ~60s at 8-way parallel.
# Each lift 5 min; total stage 2 ~22.5 min wallclock at 8-way.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-178/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/builds" "$OUT/logs"
echo "[v178] out=$OUT" | tee "$OUT/_meta.log"

SCANS=(row row_rev col col_rev zigzag zigzag_rev spiral_in spiral_out diagonal)
SEEDS=(1 7 42 99)
PRIOR=scripts/v155_prior/prior_matrix_high459.json
PHER=output/vol-178/pheromone_init.json
LAMBDA=1e-7
TEMP=0.05
BATCH=8

# Stage 1: V178 STIGMA builds.
echo "[v178] STAGE 1: $((${#SCANS[@]}*${#SEEDS[@]})) STIGMA builds" | tee -a "$OUT/_meta.log"
n=0
for scan in "${SCANS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    tag="${scan}_s${seed}"
    out_json="$OUT/builds/${tag}.json"
    log="$OUT/logs/build_${tag}.log"
    nice -n 5 target/bench-fast/v178_stigma \
      --beam-width 256 \
      --prior-file "$PRIOR" \
      --pheromone-file "$PHER" \
      --pheromone-weight "$LAMBDA" \
      --dedup-path --dedup-recent 4 \
      --scan "$scan" \
      --seed "$seed" \
      --stochastic-temperature "$TEMP" \
      --save-best "$out_json" \
      > "$log" 2>&1 &
    n=$((n + 1))
    if [ "$((n % BATCH))" = "0" ]; then
      wait
      echo "[v178] $n builds done at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

# Score + cp summary.
echo "" | tee -a "$OUT/_meta.log"
echo "[v178] Build scores:" | tee -a "$OUT/_meta.log"
uv run python -c "
import json, glob
from collections import Counter
boards = sorted(glob.glob('$OUT/builds/*.json'))
cps = Counter()
scores = []
for b in boards:
    try: d = json.load(open(b))
    except: continue
    m = d.get('matched', 0)
    pl = {e['pos']: e['piece_id'] for e in d['placement'] if e is not None}
    if not all(p in pl for p in (0, 15, 240, 255)): continue
    cps[(pl[0], pl[15], pl[240], pl[255])] += 1
    scores.append(m)
scores.sort()
print(f'  {len(scores)} builds; score range {scores[0]}-{scores[-1]} (median {scores[len(scores)//2]})')
print(f'  unique CPs: {len(cps)}')
for cp, n in cps.most_common(15):
    print(f'    cp={cp}: {n}')
" | tee -a "$OUT/_meta.log"

# Stage 2: ALNS lift each build, 5min × 8-way.
echo "" | tee -a "$OUT/_meta.log"
echo "[v178] STAGE 2: ALNS lift" | tee -a "$OUT/_meta.log"
n=0
for build in "$OUT/builds"/*.json; do
  base=$(basename "$build" .json)
  log="$OUT/logs/lift_${base}.log"
  nice -n 5 target/bench-fast/alns_only \
    --cp-board "$build" \
    --alns-budget-ms 300000 \
    --seed 42 \
    --ops basic_lkh \
    --prior-destroy "$PRIOR" \
    --lex-intaglio \
    --repair-kind sa --t 1.0 \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    echo "[v178] $n lifts done at $(date)" | tee -a "$OUT/_meta.log"
  fi
done
wait

# Results.
echo "" | tee -a "$OUT/_meta.log"
echo "[v178] LIFTED RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  base=$(basename "$log" .log)
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  echo "  $base: $m" | tee -a "$OUT/_meta.log"
done

echo "" | tee -a "$OUT/_meta.log"
echo "[v178] Score distribution:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1
done | sort -rn | uniq -c | tee -a "$OUT/_meta.log"

echo "[v178] done $(date)" | tee -a "$OUT/_meta.log"
