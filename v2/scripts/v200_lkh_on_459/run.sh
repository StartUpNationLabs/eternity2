#!/usr/bin/env bash
# V200 ALNS basic_lkh + prior + intaglio on DB 459 strict base.
# 8 seeds × 30min × 8 parallel. Goal: lift 459 → 460+ strict-canonical.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-200/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v200] out=$OUT" | tee "$OUT/_meta.log"

BASE=database-400-480/459_basic_sa_t1_s7_904478000_p13705_3f916896.json
SEEDS=(1 7 13 42 99 211 313 419)
PRIOR=scripts/v155_prior/prior_matrix_high459.json

n=0
for seed in "${SEEDS[@]}"; do
  log="$OUT/logs/alns_basic_lkh_s${seed}.log"
  nice -n 5 target/bench-fast/alns_only \
    --cp-board "$BASE" \
    --alns-budget-ms 1800000 \
    --seed "$seed" \
    --ops basic_lkh \
    --prior-destroy "$PRIOR" \
    --lex-intaglio \
    --repair-kind sa --t 1.0 \
    > "$log" 2>&1 &
  n=$((n+1))
done
wait
echo "[v200] all done $(date)" | tee -a "$OUT/_meta.log"

echo "[v200] RESULTS:" | tee -a "$OUT/_meta.log"
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
    tag = log.split('/')[-1].replace('.log','')
    print(f'  {tag}: score={score} hints={hits}/5')
EOF
