#!/bin/bash
# Vol-59 T2 — follow-up on thread 601's rich basin.
# Run more seeds × longer ALNS on t601_s002_d207 (the 458-yielding snapshot).
#
# Usage: vol59_thread601_followup.sh <n_seeds> <alns_ms> <parallel>

set -uo pipefail

N_SEEDS="${1:-16}"
ALNS_MS="${2:-900000}"  # 15 min
PARALLEL="${3:-2}"      # Share with lottery; only use 2 cores

cd "$(dirname "$0")/.."
SNAP="output/vol-56/snapshots/t601_s002_d207.json"
RES_DIR="output/vol-59/thread601_followup"
mkdir -p "$RES_DIR"

JOBS_FILE="$RES_DIR/jobs.txt"
: > "$JOBS_FILE"
# Use a different seed range than lottery (vol-56 used 1-4); start at 100 to avoid overlap
for ((seed=100; seed<100+N_SEEDS; seed++)); do
    OUT="$RES_DIR/result_seed${seed}.json"
    if [ -f "$OUT" ] && [ -s "$OUT" ]; then continue; fi
    echo "$SNAP $seed $OUT" >> "$JOBS_FILE"
done

N_JOBS=$(wc -l < "$JOBS_FILE" | tr -d ' ')
echo "Queued $N_JOBS jobs (parallel=$PARALLEL, alns_ms=$ALNS_MS)"

cat "$JOBS_FILE" | xargs -L 1 -P "$PARALLEL" bash -c '
    SNAP="$0"
    SEED="$1"
    OUT="$2"
    LOG="${OUT}.log"
    target/release/alns_only --cp-board "$SNAP" --alns-budget-ms '"$ALNS_MS"' \
        --seed "$SEED" --ops winning5 --t 1.0 > "$LOG" 2>&1
    EXIT=$?
    if [ $EXIT -ne 0 ]; then
        echo "[$(date +%H:%M:%S)] seed=$SEED FAILED exit=$EXIT"
        exit 0
    fi
    SAVED=$(grep "^saved:" "$LOG" | tail -1 | awk "{print \$2}")
    if [ -z "$SAVED" ] || [ ! -f "$SAVED" ]; then
        echo "[$(date +%H:%M:%S)] seed=$SEED NO SAVED"
        exit 0
    fi
    cp "$SAVED" "$OUT"
    SCORE=$(python3 -c "import json; print(json.load(open(\"$OUT\")).get(\"matched\", 0))" 2>/dev/null || echo "?")
    echo "[$(date +%H:%M:%S)] seed=$SEED → score=$SCORE  saved=$SAVED"
'

echo
echo "=== Summary ==="
SUMMARY="$RES_DIR/SUMMARY.csv"
echo "seed,score,file" > "$SUMMARY"
for r in "$RES_DIR"/result_*.json; do
    [ -f "$r" ] || continue
    seed=$(basename "$r" .json | grep -oE 'seed[0-9]+' | grep -oE '[0-9]+')
    SCORE=$(python3 -c "import json; print(json.load(open('$r')).get('matched', 0))" 2>/dev/null || echo 0)
    echo "$seed,$SCORE,$r" >> "$SUMMARY"
done
echo "Best 5:"
sort -t',' -k2 -nr "$SUMMARY" | head -5
