#!/usr/bin/env bash
# V163 — Basin Atlas: massive from-scratch sweep using V155 K=256.
#
# Observation: V155 K=256 + sharp prior reaches 460 in ~4 sec.
# Therefore, in 1 hour we can do ~900 builds.
# Each seed × prior-threshold × scan-order gives a different beam trajectory.
# Most land in known basins. Some land in NEW basin families.
#
# Goal: build a corpus of 1000+ from-scratch 460-tier boards. Cluster by
# corner-perm + Hamming distance. Identify NEW basin families.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-163/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/boards"
echo "[v163] basin atlas, out=$OUT" | tee "$OUT/_meta.log"

# Configurations to sweep. K=256 is fast (~4 sec). We vary:
#   - prior threshold: high459, high460, high461 (3 options)
#   - scan order: row, col (2 options)
#   - seed: 1..N
N_SEEDS=80   # 3 × 2 × 80 = 480 builds. ~32 min total at 8 cores parallel.
BATCH=8      # cores

declare -a PRIORS=("high459" "high460" "high461")
declare -a SCANS=("row" "col")

n_launched=0
for prior in "${PRIORS[@]}"; do
  for scan in "${SCANS[@]}"; do
    for seed in $(seq 1 "$N_SEEDS"); do
      best="$OUT/boards/p${prior}_${scan}_s${seed}.json"
      log="$OUT/boards/p${prior}_${scan}_s${seed}.log"
      target/bench-fast/v155_weaving_prior \
        --beam-width 256 \
        --prior-file scripts/v155_prior/prior_matrix_${prior}.json \
        --dedup-path --dedup-recent 4 \
        --scan "$scan" \
        --seed "$seed" \
        --save-best "$best" \
        > "$log" 2>&1 &
      n_launched=$((n_launched + 1))
      # Throttle to BATCH parallel.
      if [ "$((n_launched % BATCH))" = "0" ]; then
        wait
        echo "[v163] $n_launched builds done ($(date))" | tee -a "$OUT/_meta.log"
      fi
    done
  done
done
wait
echo "[v163] all $n_launched builds done at $(date)" | tee -a "$OUT/_meta.log"

# Aggregate scores.
echo "[v163] score distribution:" | tee -a "$OUT/_meta.log"
for log in "$OUT/boards"/*.log; do
  grep -oE '"best_score":[0-9]+' "$log" | head -1 | cut -d: -f2
done | sort | uniq -c | sort -rn | tee -a "$OUT/_meta.log"

# Count unique corner perms among ≥460 boards.
echo "[v163] corner-perm distribution among ≥460:" | tee -a "$OUT/_meta.log"
uv run python -c "
import json
from pathlib import Path
from collections import Counter
out_dir = Path('$OUT/boards')
cp_count = Counter()
high_score_boards = []
for j in out_dir.glob('*.json'):
    try: d = json.load(open(j))
    except: continue
    m = d.get('matched', 0)
    if m < 460: continue
    pl = {e['pos']: e['piece_id'] for e in d['placement']}
    cp = (pl[0], pl[15], pl[240], pl[255])
    cp_count[cp] += 1
    high_score_boards.append((m, cp, j.name))
print(f'{len(high_score_boards)} boards ≥460')
for cp, cnt in cp_count.most_common(20):
    print(f'  cp={cp}: {cnt} boards')
" | tee -a "$OUT/_meta.log"

echo "[v163] done $(date)" | tee -a "$OUT/_meta.log"
