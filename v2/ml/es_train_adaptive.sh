#!/bin/bash
# Adaptive-sigma ES training loop (vol-49).
# Bumps sigma when std drops below MIN_STD threshold (= ES collapse).

set -e
cd "$(dirname "$0")"

BASE=runs/v3/model.pt
OUT_ROOT=runs/es_run_002_adaptive
N_ROUNDS=${N_ROUNDS:-8}
N_PER_ROUND=${N_PER_ROUND:-8}
SIGMA_START=${SIGMA_START:-0.2}
SIGMA_MAX=${SIGMA_MAX:-1.0}
SIGMA_BUMP_FACTOR=${SIGMA_BUMP_FACTOR:-2.0}
MIN_STD=${MIN_STD:-0.5}      # below this, ES is collapsing → bump sigma
LR=${LR:-0.05}
BUDGET_MS=${BUDGET_MS:-60000}
PARALLEL=${PARALLEL:-4}

source .venv/bin/activate

mkdir -p "$OUT_ROOT"
current_base="$BASE"
current_sigma="$SIGMA_START"

for r in $(seq 1 "$N_ROUNDS"); do
  out="$OUT_ROOT/r$(printf '%03d' $r)"
  echo "=== ES Round $r: base=$current_base sigma=$current_sigma ==="
  python3 es_round.py \
    --base "$current_base" \
    --out "$out" \
    --n "$N_PER_ROUND" \
    --sigma "$current_sigma" \
    --lr "$LR" \
    --budget-ms "$BUDGET_MS" \
    --parallel "$PARALLEL" \
    --round-seed "$r" \
    --reward matched

  # Read std from rewards.json, decide if we need to bump sigma.
  std=$(python3 -c "
import json
d=json.load(open('$out/rewards.json'))
rewards=d['rewards']
import statistics
print(statistics.stdev(rewards) if len(rewards)>1 else 0.0)
")
  mean=$(python3 -c "
import json, statistics
d=json.load(open('$out/rewards.json'))
print(statistics.mean(d['rewards']))
")
  echo "Round $r: mean=$mean std=$std sigma_used=$current_sigma"

  # Sigma update logic.
  if (( $(echo "$std < $MIN_STD" | bc -l) )); then
    new_sigma=$(python3 -c "print(min($current_sigma * $SIGMA_BUMP_FACTOR, $SIGMA_MAX))")
    echo "  std<$MIN_STD: bumping sigma $current_sigma → $new_sigma"
    current_sigma="$new_sigma"
  fi

  current_base="$out/updated_model.pt"
  echo ""
done

echo "ALL DONE."
echo "Final model: $current_base"
echo "Final sigma: $current_sigma"
