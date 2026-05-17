#!/bin/bash
# Vol-122 A1 batch — run border_to_csp_fill + alns_only basic on N borders.
#
# Usage: vol122_a1_batch.sh BORDER_DIR_OR_GLOB ALNS_BUDGET_MS SEEDS_CSV CONCURRENCY
#
# Example: vol122_a1_batch.sh "output/vol-122/mcgavin_perm_borders/mcgavin_perm_b0[0-2]*.json" 1800000 42 3

set -euo pipefail

PATTERN=${1:?usage: PATTERN ALNS_BUDGET_MS SEEDS_CSV CONCURRENCY}
ALNS_BUDGET=${2:-1800000}
SEEDS=${3:-42}
CONCUR=${4:-3}

OUT_DIR="output/vol-122/a1_batch_$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT_DIR"
echo "Batch output dir: $OUT_DIR"

# Collect borders
BORDERS=( $(ls -1 $PATTERN) )
echo "Borders: ${#BORDERS[@]} files"

# For each border, do CSP-fill (2min) → ALNS basic (budget) × each seed
launch() {
  local border=$1
  local seed=$2
  local stem=$(basename "$border" .json)
  local csp_out="$OUT_DIR/${stem}_csp.json"
  local log="$OUT_DIR/${stem}_s${seed}.log"

  # CSP fill + random fill remaining → complete board
  ./target/release/border_to_csp_fill \
    --board "$border" \
    --solver joe_depth150_bp_par \
    --budget-ms 120000 \
    --random-fill-remaining \
    --seed "$seed" \
    --out "$csp_out" > "${log}.csp" 2>&1

  # ALNS basic
  ./target/release/alns_only \
    --cp-board "$csp_out" \
    --alns-budget-ms "$ALNS_BUDGET" \
    --seed "$seed" \
    --ops basic > "$log" 2>&1

  echo "DONE: $stem seed=$seed"
}

export -f launch
IFS=',' read -ra SEED_ARRAY <<< "$SEEDS"

# Build job list
JOBS=()
for border in "${BORDERS[@]}"; do
  for seed in "${SEED_ARRAY[@]}"; do
    JOBS+=("$border:$seed")
  done
done
echo "Total jobs: ${#JOBS[@]}"

# Run with concurrency
ACTIVE=0
for job in "${JOBS[@]}"; do
  IFS=':' read -r border seed <<< "$job"
  launch "$border" "$seed" &
  ACTIVE=$((ACTIVE + 1))
  if [ $ACTIVE -ge $CONCUR ]; then
    wait -n
    ACTIVE=$((ACTIVE - 1))
  fi
done
wait
echo "All jobs done. Results in $OUT_DIR/"

# Summarize
echo ""
echo "=== Results ==="
for f in "$OUT_DIR"/*.log; do
  if [ -f "$f" ] && ! [[ "$f" == *.csp ]]; then
    match=$(grep -E "FINAL|matched" "$f" 2>/dev/null | tail -1)
    echo "$(basename $f .log): $match"
  fi
done
