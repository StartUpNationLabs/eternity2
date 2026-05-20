#!/usr/bin/env bash
# V171 MURMURATION — multi-basin 460 sampling.
#
# User insight (2026-05-20): "there can be 1000s of 460 if we look deep
# enough, being stuck on one is not really good news". The 460 plateau
# is a CORPUS BASIN attractor; we need to sample many distinct basins
# and find ones close to >460.
#
# Engine: V155 with --stochastic-temperature 0.1 (Gumbel-top-K beam).
# Each seed produces a genuinely different board. Then 5 min mini-ALNS
# lift on each. Outputs corner-perm + hash atlas.
#
# Budget plan:
# - 32 builds × ~12s each = ~6.4 min for builds (8-way parallel)
# - 32 × 5 min ALNS lifts = ~21 min (8-way parallel)
# - Total ~28 min wallclock.
#
# Configs swept:
#   priors:      {high457, high459, high460}        (3)
#   scans:       {row, col}                          (2)
#   seeds per:   8                                    (8)
#   T:           0.1                                  (1)
# Total: 3 × 2 × 8 = 48 builds.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-171/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/builds" "$OUT/lifted" "$OUT/logs"
echo "[v171] out=$OUT" | tee "$OUT/_meta.log"

PRIORS=(high457 high459 high460)
SCANS=(row col)
SEEDS=(1 2 3 7 13 42 99 142)
BATCH=8
TEMP=0.1

# Stage 1: builds.
echo "[v171] STAGE 1: $((${#PRIORS[@]}*${#SCANS[@]}*${#SEEDS[@]})) V155 builds, T=$TEMP" | tee -a "$OUT/_meta.log"
n=0
for prior in "${PRIORS[@]}"; do
  for scan in "${SCANS[@]}"; do
    for seed in "${SEEDS[@]}"; do
      tag="p${prior}_${scan}_s${seed}"
      out_json="$OUT/builds/${tag}.json"
      log="$OUT/logs/build_${tag}.log"
      target/bench-fast/v155_weaving_prior \
        --beam-width 256 \
        --prior-file "scripts/v155_prior/prior_matrix_${prior}.json" \
        --dedup-path --dedup-recent 4 \
        --scan "$scan" \
        --seed "$seed" \
        --stochastic-temperature "$TEMP" \
        --save-best "$out_json" \
        > "$log" 2>&1 &
      n=$((n + 1))
      if [ "$((n % BATCH))" = "0" ]; then
        wait
        echo "[v171] $n builds done at $(date)" | tee -a "$OUT/_meta.log"
      fi
    done
  done
done
wait
echo "[v171] STAGE 1 complete: $n builds" | tee -a "$OUT/_meta.log"

# Score summary.
echo "" | tee -a "$OUT/_meta.log"
echo "[v171] Build score distribution:" | tee -a "$OUT/_meta.log"
for b in "$OUT/builds"/*.json; do
  jq -r '.matched' "$b" 2>/dev/null
done | sort -n | uniq -c | tee -a "$OUT/_meta.log"

# Stage 2: ALNS lift 5min on each build.
echo "" | tee -a "$OUT/_meta.log"
echo "[v171] STAGE 2: ALNS 5min lift per build" | tee -a "$OUT/_meta.log"
n=0
for b in "$OUT/builds"/*.json; do
  base=$(basename "$b" .json)
  log="$OUT/logs/lift_${base}.log"
  target/bench-fast/alns_only \
    --cp-board "$b" \
    --alns-budget-ms 300000 \
    --seed 42 \
    --ops basic_lkh \
    --prior-destroy scripts/v155_prior/prior_matrix_high459.json \
    --repair-kind sa --t 1.0 \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    echo "[v171] $n lifts done at $(date)" | tee -a "$OUT/_meta.log"
  fi
done
wait
echo "[v171] STAGE 2 complete" | tee -a "$OUT/_meta.log"

# Lift results.
echo "" | tee -a "$OUT/_meta.log"
echo "[v171] Lifted score distribution:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  echo "$m"
done | sort -n | uniq -c | tee -a "$OUT/_meta.log"

# Cluster by corner_perm.
echo "" | tee -a "$OUT/_meta.log"
echo "[v171] Corner-perm clustering of lifted boards:" | tee -a "$OUT/_meta.log"
uv run python -c "
import json, glob, re
from collections import defaultdict
out = '$OUT'
clusters = defaultdict(list)
score_track = defaultdict(list)
# Find lifted board JSONs (alns_only writes to output/v17_alns_only/)
# Cross-reference via build tag.
for log_path in sorted(glob.glob(f'{out}/logs/lift_*.log')):
    with open(log_path) as f:
        log = f.read()
    m_match = re.search(r'matched=(\d+)/480', log)
    if not m_match:
        continue
    score = int(m_match.group(1))
    saved = re.search(r'saved: (output/v17_alns_only/[^\s]+)', log)
    if not saved:
        continue
    bp = saved.group(1)
    try:
        b = json.load(open(bp))
    except FileNotFoundError:
        continue
    pl = {e['pos']: e['piece_id'] for e in b['placement'] if e is not None}
    if not all(p in pl for p in (0, 15, 240, 255)):
        continue
    cp = (pl[0], pl[15], pl[240], pl[255])
    clusters[cp].append((score, bp))
    score_track[score].append(cp)
print(f'  {len(clusters)} unique corner-perms found')
print(f'  Top scoring clusters:')
ranked = sorted(clusters.items(), key=lambda kv: -max(s for s, _ in kv[1]))
for cp, items in ranked[:20]:
    top = max(s for s, _ in items)
    n = len(items)
    print(f'    cp={cp}: top={top}  ({n} build(s))')
" | tee -a "$OUT/_meta.log"

echo "[v171] done $(date)" | tee -a "$OUT/_meta.log"
