#!/usr/bin/env bash
# V190 STRICT-RAW SWEEP — 1h budget, no ALNS, lots of generation.
#
# 5000 bf_bw partials × 5.6s each, batched 8 parallel = ~3500s = ~58 min.
# Post-filter for 5/5 hint compliance. Report distribution.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-190/$(date +%Y%m%dT%H%M%S)_1h
mkdir -p "$OUT/partials" "$OUT/logs"
echo "[v190] out=$OUT" | tee "$OUT/_meta.log"

N_OFFSETS=5000
OFF_MIN=50
OFF_MAX=100000
OFFSETS=$(uv run python -c "
import numpy as np
arr = np.linspace($OFF_MIN, $OFF_MAX, $N_OFFSETS).astype(int).tolist()
print(' '.join(map(str, arr)))
")

BUDGET_MS=5600  # 5.6s per partial × 5000 / 8 cores = 3500s = ~58 min
BATCH=8

echo "[v190] Stage 1: ${N_OFFSETS} bf_bw partials × budget=${BUDGET_MS}ms" | tee -a "$OUT/_meta.log"
echo "[v190] Estimated wall: $((BUDGET_MS * N_OFFSETS / BATCH / 1000))s" | tee -a "$OUT/_meta.log"

n=0
for off in $OFFSETS; do
  out_json="$OUT/partials/p_off${off}.json"
  log="$OUT/logs/p_off${off}.log"
  nice -n 5 target/bench-fast/bf_bw \
    --budget-ms "$BUDGET_MS" \
    --seed-offset "$off" \
    --dump-partial "$out_json" \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    if [ "$((n % 200))" = "0" ]; then
      echo "[v190] $n / $N_OFFSETS partials at $(date)" | tee -a "$OUT/_meta.log"
    fi
  fi
done
wait

echo "[v190] Stage 1 done $(date), $n partials" | tee -a "$OUT/_meta.log"
echo "" | tee -a "$OUT/_meta.log"

echo "[v190] Stage 2: filter strict-canonical (5/5 hints) and report" | tee -a "$OUT/_meta.log"

uv run python -c "
import json, glob, os
from collections import Counter

HINTS = {135:138, 210:180, 34:207, 221:248, 45:254}

results = []
for f in sorted(glob.glob('$OUT/partials/*.json')):
    try: d = json.load(open(f))
    except: continue
    pl_raw = d.get('placement') or []
    pl = [None]*256
    for ent in pl_raw:
        pos = ent.get('pos')
        if pos is None: continue
        pl[pos] = ent.get('piece_id')
    placed = sum(1 for x in pl if x is not None)
    hits = sum(1 for p, e in HINTS.items() if pl[p] == e)
    score = d.get('score', 0)
    off = os.path.basename(f).replace('p_off','').replace('.json','')
    results.append((int(off), placed, hits, score, f))

print(f'Total partials: {len(results)}')

if not results:
    print('No partials!')
    exit()

# Distribution by hint compliance
hc = Counter(r[2] for r in results)
print(f'\\nHint compliance distribution:')
for h in sorted(hc, reverse=True):
    print(f'  {h}/5 hints: {hc[h]} partials ({100*hc[h]/len(results):.1f}%)')

# For each hint level, show score distribution
for required_hint in [5, 4, 3, 2, 1, 0]:
    matching = [r for r in results if r[2] == required_hint]
    if not matching:
        continue
    scores = [r[3] for r in matching]
    placed = [r[1] for r in matching]
    print(f'\\nHints=={required_hint}/5 ({len(matching)} partials):')
    print(f'  score: min={min(scores)} max={max(scores)} mean={sum(scores)/len(scores):.1f}')
    print(f'  placed: min={min(placed)} max={max(placed)} mean={sum(placed)/len(placed):.1f}')
    if required_hint >= 4:
        top = sorted(matching, key=lambda x: -x[3])[:20]
        print(f'  Top 20 (off, placed, hits, score):')
        for off, p, h, s, _ in top:
            print(f'    off={off}: placed={p} score={s}')

# Save the top-50 5/5 partials manifest
strict = sorted([r for r in results if r[2] == 5], key=lambda x: -x[3])[:50]
manifest = '$OUT/top50_strict.json'
with open(manifest, 'w') as fh:
    json.dump([{'offset': r[0], 'placed': r[1], 'score': r[3], 'path': r[4]} for r in strict], fh, indent=2)
print(f'\\nSaved {len(strict)} top strict-canonical partials to {manifest}')
" 2>&1 | tee -a "$OUT/_meta.log"

echo "[v190] Done $(date), output: $OUT" | tee -a "$OUT/_meta.log"
