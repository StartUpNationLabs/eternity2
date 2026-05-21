#!/usr/bin/env bash
# V201 ALNS lifts on NEW 458 strict basins (cp=(0,2,1,3) and cp=(0,3,2,1)).
# Goal: discover 459 strict in a new basin (would tie DB but in NEW family) or 460+.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-201/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v201] out=$OUT" | tee "$OUT/_meta.log"

BASES=(
  "output/vol-199/RECORD_458_STRICT_NEW_BASIN_cp0213.json"
  "output/vol-199/RECORD_458_STRICT_NEW_BASIN_cp0321.json"
)
# 8 seeds × 2 op sets × 2 bases = 32 jobs
SEEDS=(1 7 13 42 99 211 313 419)
OPS=(basic basic_lkh)
PRIOR=scripts/v155_prior/prior_matrix_high459.json
BATCH=8

n=0
for base in "${BASES[@]}"; do
  bn=$(basename "$base" .json | head -c 40)
  for ops in "${OPS[@]}"; do
    for seed in "${SEEDS[@]}"; do
      tag="${bn}_${ops}_s${seed}"
      log="$OUT/logs/alns_${tag}.log"
      if [ "$ops" = "basic_lkh" ]; then
        nice -n 5 target/bench-fast/alns_only \
          --cp-board "$base" \
          --alns-budget-ms 1800000 \
          --seed "$seed" \
          --ops "$ops" \
          --prior-destroy "$PRIOR" \
          --lex-intaglio \
          --repair-kind sa --t 1.0 \
          > "$log" 2>&1 &
      else
        nice -n 5 target/bench-fast/alns_only \
          --cp-board "$base" \
          --alns-budget-ms 1800000 \
          --seed "$seed" \
          --ops "$ops" \
          --repair-kind sa --t 1.0 \
          > "$log" 2>&1 &
      fi
      n=$((n+1))
      if [ "$((n % BATCH))" = "0" ]; then
        wait
        echo "[v201] $n done at $(date)" | tee -a "$OUT/_meta.log"
      fi
    done
  done
done
wait

echo "[v201] All done $(date)" | tee -a "$OUT/_meta.log"
echo "[v201] RESULTS:" | tee -a "$OUT/_meta.log"
uv run python << EOF | tee -a "$OUT/_meta.log"
import json, glob, re
hints = {135:138, 210:180, 34:207, 221:248, 45:254}
for log in sorted(glob.glob('$OUT/logs/*.log')):
    with open(log) as f: content = f.read()
    m = re.search(r'matched=(\d+)/480', content)
    sm = re.findall(r'saved:\s*(\S+)', content)
    if not m or not sm: continue
    score = int(m.group(1))
    path = sm[-1]
    try: b = json.load(open(path))
    except: continue
    pl = [None]*256
    for ent in b['placement']:
        if ent is None: continue
        pos = ent.get('pos')
        if pos is None: continue
        pl[pos] = ent.get('piece_id')
    hits = sum(1 for hp, he in hints.items() if pl[hp] == he)
    cp = tuple(pl[p] for p in [0, 15, 240, 255])
    tag = log.split('/')[-1].replace('.log','')
    print(f'  {tag}: score={score} hints={hits}/5 cp={cp}')
EOF
