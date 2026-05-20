#!/usr/bin/env bash
# V174 PERTURBATION CURVE — measure ALNS recovery as a function of
# perturbation distance from a corpus-anchored 460 board.
#
# Run 5min ALNS on each perturbed board; record post-ALNS score, basin (cp).
# Reveals: does ALNS recover to 460 (basin trapped)? Lift to >460
# (basin escape)? Or collapse to <460 (too far gone)?

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

# Use existing perturbation set or rebuild.
PERT_DIR=output/vol-174/perturbations
if [ ! -d "$PERT_DIR" ] || [ -z "$(ls -A $PERT_DIR 2>/dev/null)" ]; then
  uv run python scripts/v174_perturbation_curve/probe.py \
    --base output/vol-155/best_high459.json \
    --out-dir "$PERT_DIR"
fi

OUT=output/vol-174/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/logs"
echo "[v174] out=$OUT" | tee "$OUT/_meta.log"

# Run 5min ALNS on each perturbation, 8-way parallel.
n=0
BATCH=8
for pert in "$PERT_DIR"/*.json; do
  base=$(basename "$pert" .json)
  log="$OUT/logs/${base}.log"
  target/bench-fast/alns_only \
    --cp-board "$pert" \
    --alns-budget-ms 300000 \
    --seed 42 \
    --ops basic_lkh \
    --prior-destroy scripts/v155_prior/prior_matrix_high459.json \
    --repair-kind sa --t 1.0 \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    echo "[v174] $n done at $(date)" | tee -a "$OUT/_meta.log"
  fi
done
wait

# Results: K → recovered score.
echo "" | tee -a "$OUT/_meta.log"
echo "[v174] K-vs-recovered-score:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/k*.log; do
  base=$(basename "$log" .log)  # k010_s1
  k=$(echo "$base" | sed -E 's/k([0-9]+)_.*/\1/')
  s=$(echo "$base" | sed -E 's/k[0-9]+_s([0-9]+)/\1/')
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  echo "  K=$k seed=$s -> $m" | tee -a "$OUT/_meta.log"
done

# Aggregate by K.
echo "" | tee -a "$OUT/_meta.log"
echo "[v174] Aggregate (min/median/max per K):" | tee -a "$OUT/_meta.log"
uv run python -c "
import re, glob
from collections import defaultdict
data = defaultdict(list)
for log_path in glob.glob('$OUT/logs/k*.log'):
    name = log_path.split('/')[-1].replace('.log', '')
    m = re.match(r'k(\d+)_s(\d+)', name)
    if not m: continue
    k = int(m.group(1))
    with open(log_path) as f:
        text = f.read()
    score_m = re.findall(r'matched=(\d+)/480', text)
    if not score_m: continue
    data[k].append(int(score_m[-1]))
for k in sorted(data):
    scores = sorted(data[k])
    n = len(scores)
    med = scores[n // 2]
    print(f'  K={k:>3}: min={scores[0]} med={med} max={scores[-1]} (n={n})')
" | tee -a "$OUT/_meta.log"

echo "[v174] done $(date)" | tee -a "$OUT/_meta.log"
