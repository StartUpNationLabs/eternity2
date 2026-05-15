#!/bin/bash
# Vol-56 basin lottery: run ALNS-PT on each snapshot from vol-56/snapshots/
# with multiple seeds, collect (score, file) tuples, find the best.
#
# Robustness fix: parse the "saved: " line from alns_only's stderr to find
# the exact output file (avoid race on `ls -t output/v17_alns_only/`).

set -uo pipefail

SNAP_DIR="${1:-output/vol-56/snapshots}"
RES_DIR="${2:-output/vol-56/recipe_runs}"
ALNS_MS="${3:-180000}"
SEEDS="${4:-4}"
PARALLEL="${5:-4}"

cd "$(dirname "$0")/.."
mkdir -p "$RES_DIR"

SNAPS=("$SNAP_DIR"/*.json)
echo "Found ${#SNAPS[@]} snapshots; running $SEEDS seeds each at ${ALNS_MS}ms ALNS budget; parallel=$PARALLEL"

JOBS_FILE="$RES_DIR/jobs.txt"
: > "$JOBS_FILE"
for snap in "${SNAPS[@]}"; do
    name=$(basename "$snap" .json)
    for ((seed=1; seed<=SEEDS; seed++)); do
        out="$RES_DIR/result_${name}_seed${seed}.json"
        if [ -f "$out" ] && [ -s "$out" ]; then continue; fi
        echo "$snap $seed $out" >> "$JOBS_FILE"
    done
done

N_JOBS=$(wc -l < "$JOBS_FILE" | tr -d ' ')
echo "Queued $N_JOBS jobs"

cat "$JOBS_FILE" | xargs -L 1 -P "$PARALLEL" bash -c '
    SNAP="$0"
    SEED="$1"
    OUT="$2"
    NAME=$(basename "$SNAP" .json)
    LOG="${OUT}.log"
    target/release/alns_only --cp-board "$SNAP" --alns-budget-ms '"$ALNS_MS"' \
        --seed "$SEED" --ops winning5 --t 1.0 > "$LOG" 2>&1
    EXIT=$?
    if [ $EXIT -ne 0 ]; then
        echo "[$(date +%H:%M:%S)] $NAME seed=$SEED FAILED exit=$EXIT"
        exit 0
    fi
    # Parse "saved: <path>" from alns_only stderr (which got merged to LOG)
    SAVED_PATH=$(grep "^saved:" "$LOG" | tail -1 | awk "{print \$2}")
    if [ -z "$SAVED_PATH" ] || [ ! -f "$SAVED_PATH" ]; then
        echo "[$(date +%H:%M:%S)] $NAME seed=$SEED NO SAVED LINE FOUND"
        exit 0
    fi
    cp "$SAVED_PATH" "$OUT"
    SCORE=$(python3 -c "import json; d=json.load(open(\"$OUT\")); print(d.get(\"matched\") or d.get(\"matched_best\") or d.get(\"score\", 0))" 2>/dev/null || echo "?")
    echo "[$(date +%H:%M:%S)] $NAME seed=$SEED → score=$SCORE  saved=$SAVED_PATH"
'

echo
echo "=== SUMMARY ==="
SUMMARY="$RES_DIR/SUMMARY.csv"
echo "snapshot,seed,score,file" > "$SUMMARY"
for r in "$RES_DIR"/result_*.json; do
    [ -f "$r" ] || continue
    name=$(basename "$r" .json | sed 's/result_//' | sed 's/_seed.*//')
    seed=$(basename "$r" .json | grep -oE 'seed[0-9]+' | grep -oE '[0-9]+')
    SCORE=$(python3 -c "import json; d=json.load(open('$r')); print(d.get('matched') or d.get('matched_best') or d.get('score', 0))" 2>/dev/null || echo 0)
    echo "$name,$seed,$SCORE,$r" >> "$SUMMARY"
done

echo "Best 10:"
sort -t',' -k3 -nr "$SUMMARY" | head -10
