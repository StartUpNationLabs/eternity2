#!/usr/bin/env bash
# V199 ALNS lifts on 11×457 strict-canonical DB bases.
# Proven vol-122 recipe: basic + sa t=1 lifted a 457 to 458.
# Target: 458-459 strict-canonical, possibly tying the DB 459.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-199/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v199] out=$OUT" | tee "$OUT/_meta.log"

# 11 strict-canonical 457 DB bases (verified 5/5 hints, no duplicate-pieces)
BASES=(
  "database-400-480/457_canonical_457_seed10_c5955e07.json"
  "database-400-480/457_canonical_457_seed4_3d97bbaf.json"
  "database-400-480/457_canonical_457_seed7_1d58be33.json"
  "database-400-480/457_pt_winning5_n4_t1_30_s2_b71f91c3.json"
  "database-400-480/457_REAL_RECORD_TIE_457_vol34_t1signal_seed1_e2f2a7cd.json"
  "database-400-480/457_RECORD_TIE_457_vol34_t3_t01_seed1_1c9b9e65.json"
  "database-400-480/457_winning5_sa_t1_s1_41bafab3.json"
)
# Note: skipping 3× 457_INVALID_DUP_PIECES (vol-35 found those have duplicate pieces).
# Also adding the 458 strict and 459 strict as warm-start bases.
EXTRA_BASES=(
  "database-400-480/458_basic_sa_t1_s42_357042000_p7627_60658d38.json"
  "database-400-480/459_basic_sa_t1_s7_904478000_p13705_3f916896.json"
)
BASES+=("${EXTRA_BASES[@]}")
SEEDS=(1 7 42 99)
BATCH=8

n=0
for base in "${BASES[@]}"; do
  bn=$(basename "$base" .json | head -c 40)
  for seed in "${SEEDS[@]}"; do
    tag="${bn}_s${seed}"
    log="$OUT/logs/alns_${tag}.log"
    nice -n 5 target/bench-fast/alns_only \
      --cp-board "$base" \
      --alns-budget-ms 1800000 \
      --seed "$seed" \
      --ops basic \
      --repair-kind sa --t 1.0 \
      > "$log" 2>&1 &
    n=$((n+1))
    if [ "$((n % BATCH))" = "0" ]; then
      wait
      echo "[v199] $n ALNS done at $(date)" | tee -a "$OUT/_meta.log"
    fi
  done
done
wait

echo "[v199] All done $(date)" | tee -a "$OUT/_meta.log"
echo "[v199] RESULTS:" | tee -a "$OUT/_meta.log"
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
print(f'{len(results)} ALNS lifts. Top 20:')
for score, hits, tag, path in results[:20]:
    print(f'  {tag}: score={score} hints={hits}/5')
strict5 = [r for r in results if r[1] == 5]
if strict5:
    strict5.sort(reverse=True)
    print(f'\nBest 5/5-hint strict: score={strict5[0][0]} -> {strict5[0][3]}')
EOF
