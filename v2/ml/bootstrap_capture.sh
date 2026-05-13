#!/usr/bin/env bash
# T2-bootstrap (novel vol-32 addition):
# Capture trajectories using LearnedOnTies (which reaches depth 174)
# rather than the EdgeBpMarginals baseline (depth 165). The student's
# imitation target is now a stronger composite teacher; potentially
# pushes the +9 plateau if the student can imitate the LearnedOnTies
# decision at depth 165..174.

set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${MODEL:-ml/runs/v4/model.onnx}"
SEEDS="${SEEDS:-1..51}"           # 50 seeds = ~145k samples at depth 174
BUDGET_MS="${BUDGET_MS:-90000}"   # 90s gives the engine room to push past 174 if it can
OUT="${OUT:-ml/data/canonical_traj_lot.jsonl}"
PARALLEL="${PARALLEL:-4}"

E2_LEARNED_MODEL="$MODEL" \
E2_ML_DEVICE=cpu \
E2_ML_THREADS=2 \
E2_LOT_EPS=0.05 \
E2_LOT_MAX_K=8 \
target/release/canonical-capture \
    --value-order learned_on_ties \
    --seeds "$SEEDS" \
    --budget-ms "$BUDGET_MS" \
    --parallel "$PARALLEL" \
    --out "$OUT"

echo
echo "=== bootstrap capture done -> $OUT ==="
wc -l "$OUT"
python3 -c "
import json
rows = [json.loads(l) for l in open('$OUT')]
from collections import Counter
depths = Counter(r['max_depth'] for r in rows)
print('max_depth distribution:')
for d in sorted(depths):
    print(f'  {d}: {depths[d]}')
"
