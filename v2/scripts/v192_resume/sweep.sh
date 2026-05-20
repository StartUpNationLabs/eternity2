#!/usr/bin/env bash
# V192 bf_resume sweep — crop to last clean row, DFS-extend with strict edges.
# 5s budget per partial, 8 parallel.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

IN_DIR=output/vol-190/20260520T202408_1h/partials
OUT=output/vol-192/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/resumed" "$OUT/logs"
echo "[v192] out=$OUT" | tee "$OUT/_meta.log"

BUDGET_MS=${BUDGET_MS:-5000}
BATCH=${BATCH:-8}
LIMIT=${LIMIT:-5000}

files=($(ls "$IN_DIR"/*.json | head -n "$LIMIT"))
N=${#files[@]}
echo "[v192] $N partials × $BUDGET_MS ms × $BATCH parallel" | tee -a "$OUT/_meta.log"

n=0
for f in "${files[@]}"; do
  bn=$(basename "$f")
  out_json="$OUT/resumed/$bn"
  log="$OUT/logs/${bn%.json}.log"
  nice -n 5 target/bench-fast/bf_resume \
    --input "$f" \
    --output "$out_json" \
    --budget-ms "$BUDGET_MS" \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    if [ "$((n % 200))" = "0" ]; then
      echo "[v192] $n / $N at $(date)" | tee -a "$OUT/_meta.log"
    fi
  fi
done
wait

echo "[v192] Stage 1 done $(date), $n partials" | tee -a "$OUT/_meta.log"

uv run python << EOF | tee -a "$OUT/_meta.log"
import json, glob, os, sys
sys.path.insert(0, 'scripts/v184_lighthouse')
from build_bidirectional2 import load_pieces, BORDER, is_border
pieces = load_pieces()
files = sorted(glob.glob('$OUT/resumed/*.json'))
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
    last_clean_row = d.get('last_clean_row', -1)
    placed_initial = d.get('input_placed', 0)
    off = int(os.path.basename(f).replace('p_off','').replace('.json',''))
    results.append({'off': off, 'placed': placed, 'mis': mis, 'score': score,
                    'last_clean': last_clean_row, 'placed_init': placed_initial})

print(f'\n{len(results)} partials')
clean = [r for r in results if r['mis'] == 0]
print(f'Clean (0 mismatches): {len(clean)} / {len(results)}')

if clean:
    from collections import Counter
    by_p = Counter(r['placed'] for r in clean)
    print(f'Placed distribution (top 10):')
    for p, n in sorted(by_p.items(), reverse=True)[:10]:
        print(f'  placed={p}: {n}')

    clean.sort(key=lambda r: (-r['placed'], -r['score']))
    print(f'\nTop 20 clean resumed partials:')
    for r in clean[:20]:
        print(f'  off={r["off"]:>6}: placed={r["placed"]} score={r["score"]} (last_clean={r["last_clean"]}, init={r["placed_init"]})')
EOF

echo "[v192] Done $(date), output: $OUT" | tee -a "$OUT/_meta.log"
