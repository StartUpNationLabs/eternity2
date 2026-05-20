#!/usr/bin/env bash
# V190 NOBREAK SWEEP — bf_bw with break-count=0 → clean partials, no errors.
#
# User insight: the 5-8 errors in the V190 partials were all in the last
# ~20 placed cells, caused by the Blackwood schedule's break-indexes.
# Disable breaks: --break-first 300 --break-count 0 → pure DFS with the
# heuristic-side schedule; no relaxation.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-190/nobreak_$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/partials" "$OUT/logs"
echo "[nobreak] out=$OUT" | tee "$OUT/_meta.log"

N=500
BUDGET_MS=5600
BATCH=8

OFFSETS=$(uv run python -c "
import numpy as np
arr = np.linspace(50, 100000, $N).astype(int).tolist()
print(' '.join(map(str, arr)))
")

n=0
for off in $OFFSETS; do
  out_json="$OUT/partials/p_off${off}.json"
  log="$OUT/logs/p_off${off}.log"
  nice -n 5 target/bench-fast/bf_bw \
    --budget-ms "$BUDGET_MS" \
    --seed-offset "$off" \
    --break-first 300 --break-count 0 \
    --dump-partial "$out_json" \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    if [ "$((n % 100))" = "0" ]; then
      echo "[nobreak] $n / $N at $(date)" | tee -a "$OUT/_meta.log"
    fi
  fi
done
wait

echo "[nobreak] Stage 1 done $(date), $n partials" | tee -a "$OUT/_meta.log"

uv run python << EOF | tee -a "$OUT/_meta.log"
import json, glob, os, sys
sys.path.insert(0, 'scripts/v184_lighthouse')
from build_bidirectional2 import load_pieces, BORDER, is_border
pieces = load_pieces()
files = sorted(glob.glob('$OUT/partials/*.json'))
results = []
for f in files:
    try: d = json.load(open(f))
    except: continue
    pl_raw = d.get('placement') or []
    pl = [None]*256
    for ent in pl_raw:
        pos = ent.get('pos')
        if pos is None: continue
        pl[pos] = (ent['piece_id'], ent.get('rotation', 0))
    placed = sum(1 for x in pl if x is not None)
    mis = 0
    for pos in range(256):
        if pl[pos] is None: continue
        r, c = pos // 16, pos % 16
        pid, rot = pl[pos]
        edges = pieces[(pid, rot)]
        if c < 15 and pl[pos+1] is not None:
            if edges[1] != pieces[pl[pos+1]][3] and not is_border(edges[1]): mis += 1
        if r < 15 and pl[pos+16] is not None:
            if edges[2] != pieces[pl[pos+16]][0] and not is_border(edges[2]): mis += 1
    score = d.get('score', 0)
    off = int(os.path.basename(f).replace('p_off','').replace('.json',''))
    results.append({'off': off, 'placed': placed, 'mis': mis, 'score': score, 'path': f})

print(f'\n{len(results)} partials')
from collections import Counter
mis_dist = Counter(r['mis'] for r in results)
print(f'\nMismatch distribution: {dict(sorted(mis_dist.items()))}')

clean = [r for r in results if r['mis'] == 0]
print(f'\nClean partials (0 mismatches): {len(clean)}/{len(results)}')

# Best by placed cell count (then score)
clean.sort(key=lambda x: (-x['placed'], -x['score']))
print(f'\nTop 20 CLEAN partials by placed-count:')
for r in clean[:20]:
    print(f'  off={r["off"]:>6}: placed={r["placed"]} score={r["score"]}  {os.path.basename(r["path"])}')

# Save the top 10 to a manifest
manifest = '$OUT/top10_clean.json'
with open(manifest, 'w') as fh:
    json.dump([{'off': r['off'], 'placed': r['placed'], 'score': r['score'], 'path': r['path']} for r in clean[:10]], fh, indent=2)
print(f'\nSaved top-10 clean partials to {manifest}')
EOF

echo "[nobreak] Done $(date), output: $OUT" | tee -a "$OUT/_meta.log"
