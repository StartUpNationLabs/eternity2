#!/bin/bash
# Vol-60 T3 v2 — corner-sweep via prune_restart on pre-built partials.
# For each of 24 corner-perm partials, run prune_restart --pin-all-from-start
# --max-score. CP fills remaining 247 cells optimizing matched edges.

set -uo pipefail

CP_MS="${1:-300000}"   # 5 min CP per perm
PARALLEL="${2:-8}"

cd "$(dirname "$0")/.."
PARTIALS_DIR="output/vol-60/corner_partials"
# Timestamped output dir — never overwrite previous runs.
TS="${VOL60_RUN_TAG:-$(date +%Y%m%dT%H%M%S)}"
RES_DIR="output/vol-60/corner_sweep_v2_${TS}"
mkdir -p "$RES_DIR"
echo "Run tag: $TS"
echo "Output dir: $RES_DIR"

JOBS_FILE="$RES_DIR/jobs.txt"
: > "$JOBS_FILE"
for partial in "$PARTIALS_DIR"/*.json; do
    [ -f "$partial" ] || continue
    pid=$(basename "$partial" .json | grep -oE 'p[0-9]+')
    OUT_DIR="$RES_DIR/${pid}"
    if [ -f "$OUT_DIR/round_1_board.json" ]; then continue; fi
    echo "$partial $pid $OUT_DIR" >> "$JOBS_FILE"
done

N=$(wc -l < "$JOBS_FILE" | tr -d ' ')
echo "$(date +%H:%M:%S) Queued $N perms (parallel=$PARALLEL, cp=${CP_MS}ms)"

cat "$JOBS_FILE" | xargs -L 1 -P "$PARALLEL" bash -c '
    PARTIAL="$0"
    PID="$1"
    OUT_DIR="$2"
    LOG="$OUT_DIR/run.log"
    mkdir -p "$OUT_DIR"
    target/release/prune_restart \
        --start "$PARTIAL" \
        --pin-all-from-start \
        --max-score \
        --cp-budget-ms '"$CP_MS"' \
        --rounds 1 \
        --seed 1 \
        --out-dir "$OUT_DIR" \
        > "$LOG" 2>&1
    EXIT=$?
    if [ $EXIT -ne 0 ]; then
        echo "[$(date +%H:%M:%S)] $PID FAILED exit=$EXIT"
        exit 0
    fi
    # Extract score from log
    SCORE=$(grep -oE "score=[0-9]+/480" "$LOG" | tail -1 | grep -oE "[0-9]+" | head -1)
    DEPTH=$(grep -oE "depth=[0-9]+" "$LOG" | tail -1 | grep -oE "[0-9]+")
    echo "[$(date +%H:%M:%S)] $PID depth=$DEPTH score=$SCORE  log=$LOG"
'

echo
echo "=== Summary ==="
SUMMARY="$RES_DIR/SUMMARY.csv"
echo "perm,depth,score" > "$SUMMARY"
for partial in "$PARTIALS_DIR"/*.json; do
    pid=$(basename "$partial" .json | grep -oE 'p[0-9]+')
    LOG="$RES_DIR/${pid}/run.log"
    if [ -f "$LOG" ]; then
        SCORE=$(grep -oE "score=[0-9]+/480" "$LOG" | tail -1 | grep -oE "[0-9]+" | head -1)
        DEPTH=$(grep -oE "depth=[0-9]+" "$LOG" | tail -1 | grep -oE "[0-9]+")
        echo "$pid,${DEPTH:-?},${SCORE:-?}" >> "$SUMMARY"
    fi
done

echo "Per-perm scores (sorted by score desc):"
sort -t',' -k3 -nr "$SUMMARY" | head -25
