#!/bin/bash
# Vol-61 prep — replay the SOTA pipeline (border-first DFS → ALNS minimal →
# ALNS basic seed sweep) on a chosen corner-pinned partial.
#
# This is the canonical record-attempt pipeline that produced the 459.
# Run it on the top-greedy-score perms (p07, p10, p11, p18, p19, p21)
# to see if 460+ is reachable on a different basin.
#
# Usage: vol61_sota_pipeline_replay.sh <perm_id> [seed_count]
#
# Stages:
#   1. vanilla_fast --pin-hints --extra-hint (corners) → CP partial
#   2. ALNS minimal × 5min seed=1 from CP partial → mid-quality
#   3. ALNS basic × 30min × seeds 1..N (parallel) → record attempt

set -uo pipefail

PERM_ID="${1:?usage: vol61_sota_pipeline_replay.sh PERM_ID [SEEDS]}"
N_SEEDS="${2:-8}"
PARALLEL="${3:-8}"

cd "$(dirname "$0")/.."
TS="$(date +%Y%m%dT%H%M%S)"
RES_DIR="output/vol-61/sota_replay_${PERM_ID}_${TS}"
mkdir -p "$RES_DIR"
echo "Run: $RES_DIR"

# Find the corner_partial file for this perm (auto-detects TL/TR/BL/BR)
PARTIAL=$(ls output/vol-60/corner_partials/${PERM_ID}_*.json 2>/dev/null | head -1)
if [ -z "$PARTIAL" ]; then
    echo "ERROR: no corner_partials/${PERM_ID}_*.json found"
    exit 1
fi
echo "Source partial: $PARTIAL"

# Extract corner pieces from filename
FN=$(basename "$PARTIAL" .json)
TL=$(echo "$FN" | grep -oE 'TL[0-9]+' | grep -oE '[0-9]+')
TR=$(echo "$FN" | grep -oE 'TR[0-9]+' | grep -oE '[0-9]+')
BL=$(echo "$FN" | grep -oE 'BL[0-9]+' | grep -oE '[0-9]+')
BR=$(echo "$FN" | grep -oE 'BR[0-9]+' | grep -oE '[0-9]+')
echo "Corners: TL=$TL TR=$TR BL=$BL BR=$BR"

# Stage 1 — vanilla_fast pin + corners, 5min, save snapshots and best partial
SAVE_BEST="$RES_DIR/stage1_cp_best.json"
SNAP_DIR="$RES_DIR/stage1_snaps"
mkdir -p "$SNAP_DIR"
echo ""
echo "$(date +%H:%M:%S) Stage 1: vanilla_fast CP 5min, pin hints + 4 corners"
target/release/vanilla_fast \
    --budget-ms 300000 \
    --threads 1 \
    --pin-hints \
    --extra-hint 0:${TL}:3 \
    --extra-hint 15:${TR}:0 \
    --extra-hint 240:${BL}:2 \
    --extra-hint 255:${BR}:1 \
    --snapshot-dir "$SNAP_DIR" \
    --snapshot-interval-ms 30000 \
    --snapshot-min-depth 100 \
    --save-best "$SAVE_BEST" \
    > "$RES_DIR/stage1.log" 2>&1
echo "  Stage 1 done."

# Merge in BL/BR if not present
/tmp/vol53_venv/bin/python3 - << EOF
import json
src = json.load(open("$SAVE_BEST"))
partial_src = json.load(open("$PARTIAL"))
out = list(src.get('placement', []))
# Ensure list of length 256
while len(out) < 256: out.append(None)
# Fill missing corners from partial
for pos in [0, 15, 240, 255]:
    if out[pos] is None and partial_src['placement'][pos] is not None:
        out[pos] = {"piece_id": partial_src['placement'][pos]['piece_id'],
                    "rotation": partial_src['placement'][pos]['rotation']}
json.dump({"placement": out}, open("$RES_DIR/stage1_merged.json", "w"))
print(f"merged: placed=" + str(sum(1 for x in out if x is not None)))
EOF
MERGED="$RES_DIR/stage1_merged.json"

# Stage 2 — ALNS minimal × 5min × seed=1 (single shot)
echo ""
echo "$(date +%H:%M:%S) Stage 2: ALNS minimal 5min seed=1 (pin corners)"
STAGE2_OUT="$RES_DIR/stage2_minimal.json"
target/release/alns_only \
    --cp-board "$MERGED" \
    --alns-budget-ms 300000 \
    --seed 1 --ops minimal --t 1.0 \
    --extra-hint 0 --extra-hint 15 --extra-hint 240 --extra-hint 255 \
    > "$RES_DIR/stage2.log" 2>&1 || true
SAVED2=$(grep "^saved:" "$RES_DIR/stage2.log" | tail -1 | awk '{print $2}')
if [ -n "$SAVED2" ] && [ -f "$SAVED2" ]; then
    cp "$SAVED2" "$STAGE2_OUT"
    SCORE2=$(/tmp/vol53_venv/bin/python3 -c "import json; print(json.load(open('$STAGE2_OUT')).get('matched', 0))" 2>/dev/null || echo "?")
    echo "  Stage 2 score=$SCORE2"
else
    echo "  Stage 2 FAILED"
    exit 1
fi

# Stage 3 — ALNS basic × 30min × N seeds in parallel
echo ""
echo "$(date +%H:%M:%S) Stage 3: ALNS basic 30min × $N_SEEDS seeds, parallel=$PARALLEL"
JOBS="$RES_DIR/jobs.txt"
: > "$JOBS"
for ((seed=1; seed<=N_SEEDS; seed++)); do
    OUT="$RES_DIR/stage3_basic_seed${seed}.json"
    echo "$STAGE2_OUT $seed $OUT" >> "$JOBS"
done

export RES_DIR
cat "$JOBS" | xargs -L 1 -P "$PARALLEL" bash -c '
    SRC="$0"; SEED="$1"; OUT="$2"
    LOG="${OUT}.log"
    target/release/alns_only --cp-board "$SRC" --alns-budget-ms 1800000 \
        --seed "$SEED" --ops basic --t 1.0 \
        --extra-hint 0 --extra-hint 15 --extra-hint 240 --extra-hint 255 \
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
echo "=== Final scores ==="
for r in "$RES_DIR"/stage3_basic_seed*.json; do
    [ -f "$r" ] || continue
    SEED=$(basename "$r" .json | grep -oE 'seed[0-9]+' | grep -oE '[0-9]+')
    SCORE=$(/tmp/vol53_venv/bin/python3 -c "import json; print(json.load(open('$r')).get('matched', 0))" 2>/dev/null || echo 0)
    echo "  seed=$SEED: $SCORE"
done | sort -t':' -k2 -nr
echo ""
echo "Run dir: $RES_DIR"
