#!/usr/bin/env bash
# V196 STRICT-ALNS — from 5/5-hint partials, run ALNS basic to lift toward 458-460 strict-canonical.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-196/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v196] out=$OUT" | tee "$OUT/_meta.log"

# Generate 8 bf_bw_hinted partials at different time-points / seeds (currently deterministic; use varied budget for diversity).
BUDGETS=(30000 45000 60000 75000 90000 105000 120000 150000)
echo "[v196] STAGE 1: generate bf_bw_hinted partials at varied budgets" | tee -a "$OUT/_meta.log"
n=0
for ms in "${BUDGETS[@]}"; do
  out="$OUT/bfh_b${ms}.json"
  log="$OUT/logs/bfh_b${ms}.log"
  nice -n 5 target/bench-fast/bf_bw_hinted --budget-ms "$ms" --dump-partial "$out" > "$log" 2>&1 &
  n=$((n+1))
  if [ "$((n % 8))" = "0" ]; then wait; fi
done
wait

echo "[v196] STAGE 1 done $(date)" | tee -a "$OUT/_meta.log"
for ms in "${BUDGETS[@]}"; do
  f="$OUT/bfh_b${ms}.json"
  placed=$(uv run python -c "
import json
b = json.load(open('$f'))
print(sum(1 for ent in b['placement'] if ent.get('pos') is not None))")
  echo "  bfh_b${ms}: placed=$placed" | tee -a "$OUT/_meta.log"
done

# STAGE 2: ALNS basic on each 5/5-hint partial × 4 seeds × 30min = 32 jobs, 8 parallel = 4 batches.
echo "[v196] STAGE 2: ALNS basic 30min × 4 seeds × 8 partials = 32 jobs" | tee -a "$OUT/_meta.log"
SEEDS=(1 7 42 99)
n=0
for ms in "${BUDGETS[@]}"; do
  partial="$OUT/bfh_b${ms}.json"
  for seed in "${SEEDS[@]}"; do
    tag="b${ms}_s${seed}"
    log="$OUT/logs/alns_${tag}.log"
    nice -n 5 target/bench-fast/alns_only \
      --cp-board "$partial" \
      --alns-budget-ms 1800000 \
      --seed "$seed" \
      --ops basic \
      --repair-kind sa --t 1.0 \
      > "$log" 2>&1 &
    n=$((n+1))
    if [ "$((n % 8))" = "0" ]; then
      wait
      echo "[v196] $n / 32 ALNS done at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

echo "[v196] All done $(date)" | tee -a "$OUT/_meta.log"
echo "[v196] RESULTS:" | tee -a "$OUT/_meta.log"
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
print(f'\nTop 20 by score, with hint compliance:')
for score, hits, tag, path in results[:20]:
    print(f'  {tag}: score={score} hints={hits}/5  -> {path}')
strict5 = [r for r in results if r[1] == 5]
print(f'\n5/5-hint results ({len(strict5)}):')
strict5.sort(reverse=True)
for score, hits, tag, path in strict5[:10]:
    print(f'  {tag}: score={score} (STRICT-CANONICAL)')
if strict5:
    print(f'\nBEST STRICT-CANONICAL: score={strict5[0][0]}/480 at {strict5[0][3]}')
EOF
