#!/usr/bin/env bash
# V175 GAUNTLET — multi-scan-direction beam search + ALNS lift.
#
# Built 2026-05-20. Reverse / zigzag / spiral / diagonal scans yield
# DIFFERENT corner-perms vs forward V155. Each one a distinct basin
# candidate for ALNS lift to 460+.
#
# Pipeline:
#   Stage 1: V175 GAUNTLET builds (7 scans × N seeds × 1 prior).
#   Stage 2: 5min ALNS lift per build with prior-escape + basic_lkh ops.
#   Stage 3: cluster outputs by corner-perm; identify novel basins.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-175/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/builds" "$OUT/logs"
echo "[v175] out=$OUT" | tee "$OUT/_meta.log"

SCANS=(row row_rev col col_rev zigzag zigzag_rev spiral_in spiral_out diagonal)
SEEDS=(1 7 42 99)
PRIOR=scripts/v155_prior/prior_matrix_high459.json
TEMP=0.05
BATCH=8

# Stage 1: builds.
echo "[v175] STAGE 1: $((${#SCANS[@]}*${#SEEDS[@]})) GAUNTLET builds, T=$TEMP" | tee -a "$OUT/_meta.log"
n=0
for scan in "${SCANS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    tag="${scan}_s${seed}"
    out_json="$OUT/builds/${tag}.json"
    log="$OUT/logs/build_${tag}.log"
    nice -n 5 target/bench-fast/v175_gauntlet \
      --beam-width 256 \
      --prior-file "$PRIOR" \
      --dedup-path --dedup-recent 4 \
      --scan "$scan" \
      --seed "$seed" \
      --stochastic-temperature "$TEMP" \
      --save-best "$out_json" \
      > "$log" 2>&1 &
    n=$((n + 1))
    if [ "$((n % BATCH))" = "0" ]; then
      wait
      echo "[v175] $n builds done at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait
echo "[v175] STAGE 1 complete: $n builds" | tee -a "$OUT/_meta.log"

# Score summary + cp diversity.
echo "" | tee -a "$OUT/_meta.log"
echo "[v175] Build (score, cp) distribution:" | tee -a "$OUT/_meta.log"
uv run python -c "
import json, glob
from collections import Counter
boards = sorted(glob.glob('$OUT/builds/*.json'))
print(f'  {len(boards)} builds')
scores = []
cps = Counter()
for b in boards:
    try: d = json.load(open(b))
    except: continue
    m = d.get('matched', 0)
    pl = {e['pos']: e['piece_id'] for e in d['placement'] if e is not None}
    if not all(p in pl for p in (0, 15, 240, 255)): continue
    cp = (pl[0], pl[15], pl[240], pl[255])
    scores.append(m)
    cps[cp] += 1
scores.sort()
print(f'  score range: {scores[0]}-{scores[-1]}, median {scores[len(scores)//2]}')
print(f'  unique corner-perms: {len(cps)}')
for cp, n in cps.most_common(20):
    print(f'    cp={cp}: {n}')
" | tee -a "$OUT/_meta.log"

# Stage 2: ALNS lift, 5 min each.
echo "" | tee -a "$OUT/_meta.log"
echo "[v175] STAGE 2: ALNS lift" | tee -a "$OUT/_meta.log"
n=0
for build in "$OUT/builds"/*.json; do
  base=$(basename "$build" .json)
  log="$OUT/logs/lift_${base}.log"
  target/bench-fast/alns_only \
    --cp-board "$build" \
    --alns-budget-ms 300000 \
    --seed 42 \
    --ops basic_lkh \
    --prior-destroy "$PRIOR" \
    --repair-kind sa --t 1.0 \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    echo "[v175] $n lifts done at $(date)" | tee -a "$OUT/_meta.log"
  fi
done
wait

# Results.
echo "" | tee -a "$OUT/_meta.log"
echo "[v175] LIFTED RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  base=$(basename "$log" .log)
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  echo "  $base: $m" | tee -a "$OUT/_meta.log"
done

# Lifted distribution.
echo "" | tee -a "$OUT/_meta.log"
echo "[v175] Lifted score distribution:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1
done | sort -n | uniq -c | tee -a "$OUT/_meta.log"

echo "[v175] done $(date)" | tee -a "$OUT/_meta.log"
