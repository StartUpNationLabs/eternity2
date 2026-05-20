#!/usr/bin/env bash
# V195 PILGRIM — 12-hour blank-canvas DFS with restarts.
# Constraint: zero errors throughout (strict edge match).
# 5/5 canonical hints pinned. Each restart shuffles the value-order seed.
# 8 cores parallel = 8 independent search streams.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

OUT=output/vol-195/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT"
echo "[pilgrim-12h] out=$OUT"

BUDGET_MS=${BUDGET_MS:-43200000}  # 12h
RESTART_MS=${RESTART_MS:-30000}    # 30s per restart
THREADS=${THREADS:-8}

echo "[pilgrim-12h] budget=$BUDGET_MS ms = $((BUDGET_MS/3600000)) hours"
echo "[pilgrim-12h] restart_after=$RESTART_MS ms"
echo "[pilgrim-12h] threads=$THREADS"
echo "[pilgrim-12h] starting_label='blank canvas (5 hints only)'"

# Launch
nice -n 5 target/bench-fast/bf_pilgrim \
  --budget-ms "$BUDGET_MS" \
  --restart-after-ms "$RESTART_MS" \
  --threads "$THREADS" \
  --out "$OUT/best.json" \
  --log "$OUT/progress.log" \
  > "$OUT/run.stdout" 2> "$OUT/run.stderr"
echo "[pilgrim-12h] done $(date)"
