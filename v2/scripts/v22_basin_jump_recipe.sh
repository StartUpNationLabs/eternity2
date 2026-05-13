#!/bin/bash
# Vol-22 basin-jump recipe:
# 1. Bound-ascent for N iters from input board (seed)
# 2. Hungarian-match the bound-ascended state to piece-uniqueness
# 3. ALNS-recover the matched board
# Output: a (score, bound) tuple, and the saved board

set -euo pipefail

BOARD="$1"
SEED="${2:-1}"
BOUND_ITERS="${3:-3000}"
ALNS_MS="${4:-60000}"
OUT="${5:-/tmp/basin_jump_$SEED}"

cd "$(dirname "$0")/.."

# Step 1: bound-ascent
echo ">>> Step 1: bound-ascent from $BOARD (iters=$BOUND_ITERS, seed=$SEED)"
./target/release/edge_bound_ascent --board "$BOARD" --iters "$BOUND_ITERS" --seed "$SEED" --acceptance greedy 2>&1 \
  | tail -5
ASCENT=$(ls -t output/v21_bound_ascent_b*.json | head -1)
echo "  ascent file: $ASCENT"

# Step 2: Hungarian match
echo ">>> Step 2: Hungarian match"
./target/release/edge_target_match --board "$ASCENT" 2>&1 | tail -5
HMATCH=$(ls -t output/v21_target_match_*.json | head -1)
echo "  hmatch file: $HMATCH"

# Compute bound of hmatch
HMATCH_BOUND=$(./target/release/edge_relax --board "$HMATCH" --max-iters 30 2>&1 | grep "Final score" | awk '{print $3}' | sed 's|/.*||')
HMATCH_SCORE=$(python3 -c "import json; d=json.load(open('$HMATCH')); print(d.get('matched_best') or d.get('matched') or d.get('score'))")
echo "  HMATCH: score=$HMATCH_SCORE, bound=$HMATCH_BOUND"

# Step 3: ALNS recovery
echo ">>> Step 3: ALNS recovery (budget=${ALNS_MS}ms)"
./target/release/alns_only --cp-board "$HMATCH" --alns-budget-ms "$ALNS_MS" --seed "$SEED" --ops winning5 --t 1.0 2>&1 \
  | grep -E "new_best|^Final|saved" | tail -5

# Get the last saved ALNS output
LATEST=$(ls -t output/v17_alns_only/*.json | head -1)
LATEST_SCORE=$(python3 -c "import json; d=json.load(open('$LATEST')); print(d.get('matched_best') or d.get('matched') or d.get('score'))")
LATEST_BOUND=$(./target/release/edge_relax --board "$LATEST" --max-iters 30 2>&1 | grep "Final score" | awk '{print $3}' | sed 's|/.*||')
echo
echo ">>> RESULT: score=$LATEST_SCORE, bound=$LATEST_BOUND, file=$LATEST"
