#!/usr/bin/env bash
# V190 STRICT-RAW SWEEP — 1h budget, no ALNS.
#
# User directive: "No alns, just raw things." Generate bf_bw partials with
# many offsets, post-filter for 5/5 hint compliance, report score
# distribution.
#
# Stage 1 (10 min wall): generate ~500 bf_bw partials at offsets 50-5000.
#   - 500 partials × ~1.2s budget each, batched 8 in parallel = ~75s wall, but
#     longer budgets per partial give higher depth/score; tune for ~10min.
#   - With BATCH=8, target 500 partials × 9.6s budget each = 600s = 10min.
# Stage 2 (50 min wall): rerun the top-scoring 5/5-hint partials at much
#   longer budgets to push individual scores higher.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-190/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/partials" "$OUT/logs"
echo "[v190] out=$OUT" | tee "$OUT/_meta.log"

# 500 offsets evenly across 50..5000.
N_OFFSETS=500
OFF_MIN=50
OFF_MAX=5000
# Generate offsets as a python-list, take stride.
OFFSETS=$(uv run python -c "
import numpy as np
arr = np.linspace($OFF_MIN, $OFF_MAX, $N_OFFSETS).astype(int).tolist()
print(' '.join(map(str, arr)))
")

BUDGET_MS=9600  # ~9.6s per partial × 500 / 8 cores = 600s = 10 min wall
BATCH=8

echo "[v190] Stage 1: ${N_OFFSETS} bf_bw partials × budget=${BUDGET_MS}ms" | tee -a "$OUT/_meta.log"

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
    if [ "$((n % 80))" = "0" ]; then
      echo "[v190] $n partials at $(date)" | tee -a "$OUT/_meta.log"
    fi
  fi
done
wait

echo "[v190] Stage 1 done $(date), $n partials" | tee -a "$OUT/_meta.log"
echo "" | tee -a "$OUT/_meta.log"

echo "[v190] Stage 1.5: filter for 5/5 hint compliance and report" | tee -a "$OUT/_meta.log"

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

# Distribution: placed cells
plc = Counter(r[1] for r in results)
print(f'\\nPlaced cells: min={min(plc)} max={max(plc)}')

# Distribution by hint compliance
hc = Counter(r[2] for r in results)
print(f'\\nHint compliance distribution:')
for h in sorted(hc, reverse=True):
    print(f'  {h}/5 hints: {hc[h]} partials')

# Score distribution by hint level
for required_hint in [5, 4, 3, 0]:
    matching = [r for r in results if r[2] >= required_hint]
    if not matching:
        continue
    scores = [r[3] for r in matching]
    print(f'\\nWith hint>={required_hint}/5 ({len(matching)} partials):')
    print(f'  score min={min(scores)} max={max(scores)} mean={sum(scores)/len(scores):.1f}')
    top = sorted(matching, key=lambda x: -x[3])[:10]
    print(f'  Top 10 (off, placed, hits, score):')
    for off, p, h, s, _ in top:
        print(f'    off={off}: placed={p} hits={h}/5 score={s}')

# Save the top-20 5/5 partials to a manifest for stage 2
strict = sorted([r for r in results if r[2] == 5], key=lambda x: -x[3])[:20]
manifest = '$OUT/stage1_top20_strict.json'
with open(manifest, 'w') as fh:
    json.dump([{'offset': r[0], 'placed': r[1], 'score': r[3], 'path': r[4]} for r in strict], fh, indent=2)
print(f'\\nSaved {len(strict)} top-20 strict-canonical partials to {manifest}')
" 2>&1 | tee -a "$OUT/_meta.log"

echo "" | tee -a "$OUT/_meta.log"
echo "[v190] Stage 1 complete, output: $OUT" | tee -a "$OUT/_meta.log"
