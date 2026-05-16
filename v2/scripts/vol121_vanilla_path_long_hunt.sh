#!/usr/bin/env bash
# Vol-121 — long vanilla_path basin hunt (cross-machine SOTA replay).
#
# Cross-machine SOTA recipe (from ONBOARDING):
#   vanilla_path border-first × 9 threads × 30 min → ~403 partial
#   ALNS minimal × 5min seed=1 → 452
#   ALNS basic × 30min seed=42 from 454 → 459
#
# Vol-121 replicates this with multiple thread-id-offsets to maximize
# basin diversity.

set -euo pipefail
cd "$(dirname "$0")/.."

# Two distinct offsets to seed different basins; total 16 threads × 30min.
# Then ALNS basic 30min on each partial × 4 seeds.
THREAD_OFFSET_A="${THREAD_OFFSET_A:-0}"
THREAD_OFFSET_B="${THREAD_OFFSET_B:-8}"
VANILLA_BUDGET_MS="${VANILLA_BUDGET_MS:-1800000}"  # 30 min
VANILLA_THREADS="${VANILLA_THREADS:-8}"
ALNS_BUDGET_MS="${ALNS_BUDGET_MS:-1800000}"        # 30 min per seed
ALNS_SEEDS="${ALNS_SEEDS:-1 42}"                   # 2 seeds for first pass
ALNS_OPS="${ALNS_OPS:-basic}"
TS="$(date +%Y%m%dT%H%M%S)"
OUT_DIR="${OUT_DIR:-output/vol-121/long_hunt_${TS}}"

mkdir -p "$OUT_DIR"
echo "[vol-121] OUT_DIR=$OUT_DIR"
echo "[vol-121] vanilla offsets: $THREAD_OFFSET_A, $THREAD_OFFSET_B"
echo "[vol-121] vanilla budget: ${VANILLA_BUDGET_MS}ms × $VANILLA_THREADS threads"
echo "[vol-121] ALNS budget: ${ALNS_BUDGET_MS}ms × seeds=$ALNS_SEEDS, ops=$ALNS_OPS"

# Phase 1: run vanilla_path at two distinct offsets SEQUENTIALLY (each
# uses all 8 threads). Total wall: ~60min.
for OFF in $THREAD_OFFSET_A $THREAD_OFFSET_B; do
    PARTIAL="$OUT_DIR/partial_off${OFF}.json"
    LOG="$OUT_DIR/vanilla_off${OFF}.log"
    echo "[vol-121] vanilla_path offset=$OFF (8 threads × ${VANILLA_BUDGET_MS}ms) → $PARTIAL"
    ./target/release/vanilla_path \
        --budget-ms "$VANILLA_BUDGET_MS" \
        --path-mode border-first \
        --threads "$VANILLA_THREADS" \
        --thread-id-offset "$OFF" \
        --pin-hints \
        --save-best "$PARTIAL" \
        >"$LOG" 2>&1
    grep "matched_total\|best-partial\|saved" "$LOG" | tail -3
    ./target/release/verify_board "$PARTIAL" 2>&1 | head -3
done

echo ""
echo "[vol-121] Phase 2: ALNS on partials"

JOBS=()
for OFF in $THREAD_OFFSET_A $THREAD_OFFSET_B; do
    PARTIAL="$OUT_DIR/partial_off${OFF}.json"
    if [[ -f "$PARTIAL" ]]; then
        for S in $ALNS_SEEDS; do
            JOBS+=("$OFF|$S|$PARTIAL")
        done
    fi
done
echo "[vol-121] ${#JOBS[@]} ALNS jobs"

run_alns() {
    local spec="$1"
    local off="${spec%%|*}"
    local rest="${spec#*|}"
    local s="${rest%%|*}"
    local partial="${rest#*|}"
    local log="$OUT_DIR/alns_off${off}_s${s}.log"
    local label="off${off}_s${s}"
    local out_json="$OUT_DIR/${label}_alns.json"
    if ./target/release/alns_only \
        --cp-board "$partial" \
        --alns-budget-ms "$ALNS_BUDGET_MS" \
        --seed "$s" \
        --ops "$ALNS_OPS" \
        >"$log" 2>&1; then
        local saved_path
        saved_path=$(grep -E "^saved:" "$log" | tail -1 | awk '{print $2}')
        if [[ -n "$saved_path" && -f "$saved_path" ]]; then
            cp "$saved_path" "$out_json"
        fi
        echo "[ok] $label" >> "$OUT_DIR/_alns_summary.log"
    else
        echo "[FAIL] $label" >> "$OUT_DIR/_alns_summary.log"
    fi
}
export -f run_alns
export OUT_DIR ALNS_BUDGET_MS ALNS_OPS

# Run ALNS jobs 4-wide (each is single-threaded; reserve some cores)
printf '%s\n' "${JOBS[@]}" | xargs -I {} -P 4 bash -c 'run_alns "$@"' _ {}

echo ""
echo "[vol-121] Sweep complete. Final ranking:"
./target/release/verify_board "$OUT_DIR"/*_alns.json 2>&1 \
  | grep "_alns.json" | grep -v "expected" \
  | awk '{split($3, a, "/"); print a[1], $1, $5}' | sort -nr | head -20
