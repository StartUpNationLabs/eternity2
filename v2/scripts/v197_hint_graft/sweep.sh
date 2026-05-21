#!/usr/bin/env bash
# V197 HINT-GRAFT SWEEP: graft canonical hints onto V194 460s, then ALNS lift.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-197/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/grafted" "$OUT/logs"
echo "[v197] out=$OUT" | tee "$OUT/_meta.log"

# Find all V194 460-boards
V194_DIR=output/vol-194/20260520T221102
SOURCES=()
for log in $V194_DIR/logs/basic_lkh_s*.log $V194_DIR/logs/basic_s*.log; do
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  if [ "$m" = "460" ]; then
    saved=$(grep "saved:" "$log" | tail -1 | awk '{print $2}')
    if [ -n "$saved" ] && [ -f "$saved" ]; then
      SOURCES+=("$saved")
    fi
  fi
done
echo "[v197] Found ${#SOURCES[@]} V194 460-boards to graft" | tee -a "$OUT/_meta.log"

# Stage 1: graft each
echo "[v197] STAGE 1: graft canonical hints" | tee -a "$OUT/_meta.log"
n=0
for src in "${SOURCES[@]}"; do
  n=$((n+1))
  out_grafted="$OUT/grafted/grafted_${n}.json"
  uv run python scripts/v197_hint_graft/hint_graft.py --in "$src" --out "$out_grafted" 2>&1 | tail -3 | head -2
done

# Stage 2: ALNS basic 30min × 4 seeds on each grafted board
echo "" | tee -a "$OUT/_meta.log"
echo "[v197] STAGE 2: ALNS basic 30min × 4 seeds" | tee -a "$OUT/_meta.log"
SEEDS=(1 7 42 99)
n=0
for src in $OUT/grafted/*.json; do
  base=$(basename "$src" .json)
  for seed in "${SEEDS[@]}"; do
    tag="${base}_s${seed}"
    log="$OUT/logs/alns_${tag}.log"
    nice -n 5 target/bench-fast/alns_only \
      --cp-board "$src" \
      --alns-budget-ms 1800000 \
      --seed "$seed" \
      --ops basic \
      --repair-kind sa --t 1.0 \
      > "$log" 2>&1 &
    n=$((n+1))
    if [ "$((n % 8))" = "0" ]; then
      wait
      echo "[v197] $n ALNS done at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

# Stage 3: harvest
echo "" | tee -a "$OUT/_meta.log"
echo "[v197] RESULTS:" | tee -a "$OUT/_meta.log"
uv run python << EOF | tee -a "$OUT/_meta.log"
import json, glob, re
hints = {135:138, 210:180, 34:207, 221:248, 45:254}
results = []
for log in sorted(glob.glob('$OUT/logs/alns_*.log')):
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
        pos = ent.get('pos')
        if pos is None: continue
        pl[pos] = ent.get('piece_id')
    hits = sum(1 for hp, he in hints.items() if pl[hp] == he)
    tag = log.split('/')[-1].replace('.log','')
    results.append((score, hits, tag, path))
results.sort(reverse=True)
print(f'{len(results)} ALNS lifts')
print(f'\nTop 20 by score:')
for score, hits, tag, path in results[:20]:
    marker = '✓5/5' if hits == 5 else f'{hits}/5'
    print(f'  {tag}: score={score} hints={marker}')
strict5 = [r for r in results if r[1] == 5]
print(f'\n5/5-hint count: {len(strict5)}')
strict5.sort(reverse=True)
print(f'5/5-hint top:')
for score, hits, tag, path in strict5[:10]:
    print(f'  {tag}: score={score}/480 -> {path}')
EOF
