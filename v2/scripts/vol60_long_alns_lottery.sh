#!/bin/bash
# Vol-60 T1 — long-ALNS lottery on top-5 snapshots from vol-59.
# 5 snapshots × 8 seeds × 60min ALNS = 40 jobs ≈ 5h on 8 cores.

set -uo pipefail

ALNS_MS="${1:-3600000}"   # 1 hour default
N_SEEDS="${2:-8}"
PARALLEL="${3:-8}"

cd "$(dirname "$0")/.."
RES_DIR="output/vol-60/long_alns_lottery"
mkdir -p "$RES_DIR"

TOP_SNAPS=(
    "output/vol-56/snapshots/t601_s002_d207.json"
    "output/vol-56/snapshots/t606_s002_d211.json"
    "output/vol-56/snapshots/t601_s001_d206.json"
    "output/vol-56/snapshots/t600_s002_d212.json"
    "output/vol-56/snapshots/t602_s002_d207.json"
)

JOBS_FILE="$RES_DIR/jobs.txt"
: > "$JOBS_FILE"
for snap in "${TOP_SNAPS[@]}"; do
    name=$(basename "$snap" .json)
    for ((seed=1; seed<=N_SEEDS; seed++)); do
        out="$RES_DIR/result_${name}_seed${seed}.json"
        if [ -f "$out" ] && [ -s "$out" ]; then continue; fi
        echo "$snap $seed $out" >> "$JOBS_FILE"
    done
done

N_JOBS=$(wc -l < "$JOBS_FILE" | tr -d ' ')
echo "$(date +%H:%M:%S) Queued $N_JOBS jobs (parallel=$PARALLEL, alns_ms=$ALNS_MS = $((ALNS_MS/60000))min)"

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
    SAVED=$(grep "^saved:" "$LOG" | tail -1 | awk "{print \$2}")
    if [ -z "$SAVED" ] || [ ! -f "$SAVED" ]; then
        echo "[$(date +%H:%M:%S)] $NAME seed=$SEED NO SAVED"
        exit 0
    fi
    cp "$SAVED" "$OUT"
    SCORE=$(python3 -c "import json; print(json.load(open(\"$OUT\")).get(\"matched\", 0))" 2>/dev/null || echo "?")
    echo "[$(date +%H:%M:%S)] $NAME seed=$SEED → score=$SCORE  saved=$SAVED"
'

echo
echo "=== SUMMARY ==="
SUMMARY="$RES_DIR/SUMMARY.csv"
echo "snapshot,seed,score" > "$SUMMARY"
for r in "$RES_DIR"/result_*.json; do
    [ -f "$r" ] || continue
    name=$(basename "$r" .json | sed 's/result_//' | sed 's/_seed.*//')
    seed=$(basename "$r" .json | grep -oE 'seed[0-9]+' | grep -oE '[0-9]+')
    SCORE=$(python3 -c "import json; print(json.load(open('$r')).get('matched', 0))" 2>/dev/null || echo 0)
    echo "$name,$seed,$SCORE" >> "$SUMMARY"
done
echo "Top 10:"
sort -t',' -k3 -nr "$SUMMARY" | head -10
