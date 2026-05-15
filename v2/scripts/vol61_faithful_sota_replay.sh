#!/bin/bash
# Vol-61 T1 — FAITHFUL SOTA pipeline replay.
#
# This is the exact pipeline that produced the cross-machine 459, ported
# to our machine. No corner pinning — let border-first DFS find its own
# basin.
#
# Stages (per the source notes):
#   1. vanilla_path --path-mode border-first × 9 threads × 30 min → ~403
#   2. alns_only --ops minimal --seed 1 × 5 min → ~452
#   3. alns_only --ops basic --seed N × 30 min × N seeds parallel → 459+
#
# Usage: vol61_faithful_sota_replay.sh [n_seeds]
#
# Total wall time: ~70 min on 8 cores.

set -uo pipefail

N_SEEDS="${1:-8}"
cd "$(dirname "$0")/.."
TS="$(date +%Y%m%dT%H%M%S)"
RES="output/vol-61/faithful_sota_${TS}"
mkdir -p "$RES"
echo "Run: $RES"
echo "Seeds for stage 3: $N_SEEDS"

# Stage 1: vanilla_path border-first × 9 threads × 30 min
echo ""
echo "$(date +%H:%M:%S) STAGE 1: vanilla_path border-first × 9 threads × 30min"
target/release/vanilla_path \
    --budget-ms 1800000 \
    --threads 9 \
    --path-mode border-first \
    --puzzle ../data/puzzles/size_16_official_eternity.csv \
    --save-best "$RES/stage1_best.json" \
    > "$RES/stage1.log" 2>&1
echo "  Stage 1 done."

# Parse score from log
SCORE1=$(grep -oE "matched_total=[0-9]+/480" "$RES/stage1.log" | tail -1 | grep -oE "[0-9]+" | head -1)
echo "  Stage 1 best partial score: $SCORE1"

# Stage 2: ALNS minimal × 5min × seed=1
echo ""
echo "$(date +%H:%M:%S) STAGE 2: alns_only --ops minimal × 5min × seed=1"
target/release/alns_only \
    --cp-board "$RES/stage1_best.json" \
    --alns-budget-ms 300000 \
    --seed 1 --ops minimal --t 1.0 \
    > "$RES/stage2.log" 2>&1
SAVED2=$(grep "^saved:" "$RES/stage2.log" | tail -1 | awk "{print \$2}")
if [ -z "$SAVED2" ] || [ ! -f "$SAVED2" ]; then
    echo "  Stage 2 FAILED — no saved output"
    exit 1
fi
cp "$SAVED2" "$RES/stage2_minimal.json"
SCORE2=$(/tmp/vol53_venv/bin/python3 -c "import json; print(json.load(open('$RES/stage2_minimal.json')).get('matched', 0))" 2>/dev/null || echo "?")
echo "  Stage 2 score=$SCORE2"

# Stage 3: ALNS basic × 30min × $N_SEEDS seeds parallel
echo ""
echo "$(date +%H:%M:%S) STAGE 3: alns_only --ops basic × 30min × $N_SEEDS seeds (parallel=8)"

# Use the source SOTA's specific seed (42) plus a few others to maximize basin coverage.
# The source notes say: seed=42 reached 459; seed=4 reached only 458; sweep 1..200 for replication.
SEEDS_TO_TRY=(42 4 1 2 3 17 100 200)
JOBS="$RES/jobs.txt"
: > "$JOBS"
for ((i=0; i<N_SEEDS && i<${#SEEDS_TO_TRY[@]}; i++)); do
    seed="${SEEDS_TO_TRY[$i]}"
    out="$RES/stage3_seed${seed}.json"
    echo "$RES/stage2_minimal.json $seed $out" >> "$JOBS"
done

cat "$JOBS" | xargs -L 1 -P 8 bash -c '
    SRC="$0"; SEED="$1"; OUT="$2"
    LOG="${OUT}.log"
    target/release/alns_only --cp-board "$SRC" --alns-budget-ms 1800000 \
        --seed "$SEED" --ops basic --t 1.0 \
        > "$LOG" 2>&1
    SAVED=$(grep "^saved:" "$LOG" | tail -1 | awk "{print \$2}")
    if [ -n "$SAVED" ] && [ -f "$SAVED" ]; then
        cp "$SAVED" "$OUT"
        SCORE=$(/tmp/vol53_venv/bin/python3 -c "import json; print(json.load(open(\"$OUT\")).get(\"matched\", 0))" 2>/dev/null || echo "?")
        echo "[$(date +%H:%M:%S)] seed=$SEED → score=$SCORE"
    else
        echo "[$(date +%H:%M:%S)] seed=$SEED FAILED"
    fi
'

echo ""
echo "=== FINAL SUMMARY ==="
for r in "$RES"/stage3_seed*.json; do
    [ -f "$r" ] || continue
    SEED=$(basename "$r" .json | grep -oE 'seed[0-9]+' | grep -oE '[0-9]+')
    SCORE=$(/tmp/vol53_venv/bin/python3 -c "import json; print(json.load(open('$r')).get('matched', 0))" 2>/dev/null || echo 0)
    echo "  seed=$SEED → $SCORE"
done | sort -t'>' -k2 -nr
echo ""
echo "Run dir: $RES"
echo "Any record-breaks (≥459):"
./scripts/verify_records.sh "$RES"/stage3_seed*.json 2>&1 | grep -E "459|460|461|462|463|464|465|466|467|468|469|470" || echo "  (no records above 458 found)"
