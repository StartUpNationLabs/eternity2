#!/usr/bin/env bash
# V189 CORTEZ wide sweep — run V181 KEYRING with diverse seeds + stochastic-T
# to maximise corner-perm diversity.
#
# Target cps (5 unexplored ≥460):
#   (1,0,2,3), (2,1,0,3), (2,0,1,3), (1,3,0,2), (0,2,3,1)
#
# 8 scans × 12 seeds × T={0.05, 0.10, 0.15} = 288 builds.
# Filter: keep builds matching any target cp.
# Then ALNS-lift the highest-scoring builds in each target cp.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-189/sweep_$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/builds" "$OUT/logs"
echo "[v189] out=$OUT" | tee "$OUT/_meta.log"

SCANS=(row row_rev col col_rev zigzag zigzag_rev spiral_in spiral_out)
SEEDS=(1 7 13 42 99 137 211 313 419 521 619 727)
TEMPS=(0.05 0.10 0.15)
PRIOR=scripts/v155_prior/prior_matrix_high459.json
PHER=output/vol-178/pheromone_init.json
PATCH=output/vol-181/patch_prior.json
PATCH_W=0.1
PHER_W=1e-7
BATCH=8

echo "[v189] STAGE 1: ${#SCANS[@]}*${#SEEDS[@]}*${#TEMPS[@]}=$((${#SCANS[@]} * ${#SEEDS[@]} * ${#TEMPS[@]})) builds" | tee -a "$OUT/_meta.log"
n=0
for scan in "${SCANS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    for t in "${TEMPS[@]}"; do
      tag="${scan}_s${seed}_t${t}"
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
        --stochastic-temperature "$t" \
        --save-best "$out_json" \
        > "$log" 2>&1 &
      n=$((n + 1))
      if [ "$((n % BATCH))" = "0" ]; then
        wait
        echo "[v189] $n builds at $(date)" | tee -a "$OUT/_meta.log"
      fi
    done
  done
done
wait
echo "[v189] STAGE 1 done $(date), $n builds" | tee -a "$OUT/_meta.log"

# Analyze cps
echo "" | tee -a "$OUT/_meta.log"
echo "[v189] STAGE 2: analyze cps and keep highest in each target" | tee -a "$OUT/_meta.log"

uv run python -c "
import json, glob, sys
from pathlib import Path
target_cps = [(1,0,2,3),(2,1,0,3),(2,0,1,3),(1,3,0,2),(0,2,3,1)]
target_set = set(target_cps)
boards = sorted(glob.glob('$OUT/builds/*.json'))
best_per_cp = {}
all_cps = {}
for b in boards:
    try: d = json.load(open(b))
    except: continue
    pl_raw = d.get('placement')
    if not pl_raw: continue
    pl = [None]*256
    for i, ent in enumerate(pl_raw):
        if isinstance(ent, dict):
            pos = ent.get('pos', i)
            pl[pos] = ent.get('piece_id')
    if pl[0] is None: continue
    cp = (pl[0], pl[15], pl[240], pl[255])
    score = d.get('matched', 0)
    all_cps[cp] = max(all_cps.get(cp, 0), score)
    if cp in target_set:
        if cp not in best_per_cp or best_per_cp[cp][0] < score:
            best_per_cp[cp] = (score, b)
print(f'Unique cps across all builds: {len(all_cps)}')
print(f'Target cps hit: {len(best_per_cp)} / {len(target_set)}')
for cp in target_cps:
    if cp in best_per_cp:
        s, p = best_per_cp[cp]
        print(f'  TARGET cp={cp}: best score {s} at {p}')
    else:
        print(f'  TARGET cp={cp}: NOT HIT')
# Print top 20 cps overall
print()
print('All cps (top 20 by max score):')
for cp, ms in sorted(all_cps.items(), key=lambda x: -x[1])[:20]:
    marker = '★' if cp in target_set else ' '
    print(f'  {marker} {cp}: max {ms}')
" 2>&1 | tee -a "$OUT/_meta.log"

echo "[v189] Done $(date)" | tee -a "$OUT/_meta.log"
echo "out=$OUT"
