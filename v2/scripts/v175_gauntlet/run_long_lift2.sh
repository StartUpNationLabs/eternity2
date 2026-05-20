#!/usr/bin/env bash
# V175 LONG-LIFT round 2 — on builds ranked 9-16 by score.
# Also adds multiple seeds per build (1, 42) for variance reporting.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

V175_DIR=output/vol-175/20260520T101243

OUT=output/vol-175/long_lift2_$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v175-long2] out=$OUT" | tee "$OUT/_meta.log"

PRIOR=scripts/v155_prior/prior_matrix_high459.json

# Top 9-16 builds.
BUILDS_RANK_9_16=$(uv run python -c "
import json, glob
boards = sorted(glob.glob('$V175_DIR/builds/*.json'))
scored = []
for b in boards:
    try: d = json.load(open(b))
    except: continue
    scored.append((d.get('matched', 0), b))
scored.sort(reverse=True)
for s, p in scored[8:16]:
    print(p)
")

# Also pull builds with rare cps not yet long-lifted.
TOP_RARE=$(uv run python -c "
import json, glob
from collections import defaultdict
boards = sorted(glob.glob('$V175_DIR/builds/*.json'))
by_cp = defaultdict(list)
for b in boards:
    try: d = json.load(open(b))
    except: continue
    m = d.get('matched', 0)
    pl = {e['pos']: e['piece_id'] for e in d['placement'] if e is not None}
    if not all(p in pl for p in (0, 15, 240, 255)): continue
    cp = (pl[0], pl[15], pl[240], pl[255])
    by_cp[cp].append((m, b))
# CPs not in top-8 (so we get DIVERSE inputs)
# Just take all and pick best per cp
chosen = sorted([(max(items)[0], max(items)[1], cp) for cp, items in by_cp.items()], reverse=True)
print('# cp diversity:')
for s, p, cp in chosen[:12]:
    print(p)
" | grep -v "^#")

# Combine + dedup
ALL_BUILDS=$(echo -e "$BUILDS_RANK_9_16\n$TOP_RARE" | sort -u | grep -v "^$")
echo "" | tee -a "$OUT/_meta.log"
echo "Selected builds:" | tee -a "$OUT/_meta.log"
for b in $ALL_BUILDS; do
  s=$(jq -r '.matched' "$b" 2>/dev/null)
  echo "  $s  $b" | tee -a "$OUT/_meta.log"
done

SEEDS=(42 1)
BATCH=8
n=0
echo "" | tee -a "$OUT/_meta.log"
echo "[v175-long2] STAGE 2: 30min ALNS × top builds × 2 seeds" | tee -a "$OUT/_meta.log"
for build in $ALL_BUILDS; do
  base=$(basename "$build" .json)
  for seed in "${SEEDS[@]}"; do
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
      echo "[v175-long2] $n done at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

# Results.
echo "" | tee -a "$OUT/_meta.log"
echo "[v175-long2] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  base=$(basename "$log" .log | sed 's/lift_//')
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  history=$(grep -c "iter=.*new_best" "$log")
  echo "  $base: best=$m  history=$history" | tee -a "$OUT/_meta.log"
done

# Top 5.
echo "" | tee -a "$OUT/_meta.log"
echo "[v175-long2] Top 5:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  base=$(basename "$log" .log)
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  if [ -n "$m" ]; then echo "$m $base"; fi
done | sort -rn | head -5 | tee -a "$OUT/_meta.log"

echo "[v175-long2] done $(date)" | tee -a "$OUT/_meta.log"
