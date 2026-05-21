#!/usr/bin/env bash
# V202 Stage 2: ALNS basic 30min × 4 seeds on top-N PILGRIM corpus partials.
# Usage: launch_alns.sh <vol-202-stamp-dir>

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

V202_DIR="${1:-}"
if [ -z "$V202_DIR" ]; then
  V202_DIR=$(ls -d output/vol-202/2026* | tail -1)
fi
echo "[v202-alns] V202_DIR=$V202_DIR"

MANIFEST="$V202_DIR/top_manifest.json"
[ -f "$MANIFEST" ] || { echo "missing $MANIFEST"; exit 1; }

OUT="$V202_DIR/alns_lifts"
mkdir -p "$OUT/logs"

SEEDS=(1 7 42 99)
BATCH=8

PATHS=$(uv run python -c "
import json
m = json.load(open('$MANIFEST'))
for r in m: print(r['out_path'])
")

n=0
for path in $PATHS; do
  bn=$(basename "$path" .json | head -c 40)
  for seed in "${SEEDS[@]}"; do
    log="$OUT/logs/alns_${bn}_s${seed}.log"
    nice -n 5 target/bench-fast/alns_only \
      --cp-board "$path" \
      --alns-budget-ms 1800000 \
      --seed "$seed" \
      --ops basic \
      --repair-kind sa --t 1.0 \
      > "$log" 2>&1 &
    n=$((n+1))
    if [ "$((n % BATCH))" = "0" ]; then
      wait
      echo "[v202-alns] $n ALNS at $(date)"
    fi
  done
done
wait

echo "[v202-alns] All done $(date)"
uv run python << EOF
import json, glob, re
hints = {135:138, 210:180, 34:207, 221:248, 45:254}
results = []
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
    tag = log.split('/')[-1].replace('.log','')
    results.append((score, hits, tag, path))
results.sort(reverse=True)
print(f'{len(results)} lifts. Top 30:')
for score, hits, tag, path in results[:30]:
    print(f'  {tag}: score={score} hints={hits}/5')
strict = [r for r in results if r[1] == 5]
strict.sort(reverse=True)
print(f'\\nTop 5/5-hint:')
for score, hits, tag, path in strict[:10]:
    print(f'  {tag}: score={score}')
if strict:
    print(f'\\nBEST 5/5-hint: {strict[0][0]} -> {strict[0][3]}')
EOF
