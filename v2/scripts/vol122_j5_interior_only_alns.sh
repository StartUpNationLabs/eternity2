#!/bin/bash
# Vol-122 J5 — interior-only ALNS with frozen border ring.
#
# Takes a CSP-filled board (e.g., output of border_to_csp_fill), freezes the
# 60 border positions via --extra-hint, runs ALNS basic. Compare result to
# the unfrozen baseline (A1).
#
# Usage: vol122_j5_interior_only_alns.sh BOARD.json OUT_TAG [BUDGET_MS=1800000] [SEED=42]

set -eo pipefail

BOARD=${1:?BOARD.json}
TAG=${2:?out tag}
BUDGET=${3:-1800000}
SEED=${4:-42}

# Compute border position list (positions on the 4 edges of 16x16).
SIDE=16
BORDER_POSITIONS=""
for r in $(seq 0 $((SIDE-1))); do
  for c in $(seq 0 $((SIDE-1))); do
    if [ $r -eq 0 ] || [ $r -eq $((SIDE-1)) ] || [ $c -eq 0 ] || [ $c -eq $((SIDE-1)) ]; then
      pos=$((r * SIDE + c))
      BORDER_POSITIONS="$BORDER_POSITIONS --extra-hint $pos"
    fi
  done
done

mkdir -p output/vol-122/j5_logs
LOG=output/vol-122/j5_logs/${TAG}_interior_only_s${SEED}.log

echo "Vol-122 J5: interior-only ALNS"
echo "  board: $BOARD"
echo "  freezing 60 border positions"
echo "  seed: $SEED, budget: ${BUDGET}ms (~$((BUDGET/60000))min)"
echo "  log: $LOG"

./target/release/alns_only \
  --cp-board "$BOARD" \
  --alns-budget-ms $BUDGET \
  --seed $SEED \
  --ops basic \
  $BORDER_POSITIONS \
  > "$LOG" 2>&1 &

PID=$!
echo "  PID: $PID"
