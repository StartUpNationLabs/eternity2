#!/bin/bash
# Multi-round ES training loop.
# Each round: perturb base model N times, run episodes, compute update, save.
# Next round uses prior round's updated_model.pt as base.

set -e
cd "$(dirname "$0")"

BASE=runs/v3/model.pt
OUT_ROOT=runs/es_run_001
N_ROUNDS=${N_ROUNDS:-8}
N_PER_ROUND=${N_PER_ROUND:-8}
SIGMA=${SIGMA:-0.2}
LR=${LR:-0.05}
BUDGET_MS=${BUDGET_MS:-60000}
PARALLEL=${PARALLEL:-4}

source .venv/bin/activate

mkdir -p "$OUT_ROOT"
current_base="$BASE"

for r in $(seq 1 "$N_ROUNDS"); do
  out="$OUT_ROOT/r$(printf '%03d' $r)"
  echo "=== ES Round $r: base=$current_base out=$out ==="
  python3 es_round.py \
    --base "$current_base" \
    --out "$out" \
    --n "$N_PER_ROUND" \
    --sigma "$SIGMA" \
    --lr "$LR" \
    --budget-ms "$BUDGET_MS" \
    --parallel "$PARALLEL" \
    --round-seed "$r" \
    --reward matched
  current_base="$out/updated_model.pt"
  echo ""
  echo "Round $r done. Updated model: $current_base"
done

echo "ALL DONE."
echo "Final model: $current_base"
