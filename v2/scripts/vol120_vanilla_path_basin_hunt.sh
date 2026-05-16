#!/usr/bin/env bash
# Vol-120 — vanilla_path border-first basin hunt.
#
# Cross-machine SOTA used: vanilla_path border-first × 9 threads × 30 min → ~403
# Then ALNS basic from 403 → 452 → 459.
#
# This vol: use the SAME recipe with MULTIPLE thread-id-offsets to discover
# new starting partials → run ALNS → collect 458+ basins.
#
# Sweep params (env-overridable):
#   THREAD_OFFSETS : comma-separated list of offsets (default: 0,8,16,24)
#   PATH_MODE      : default border-first-mrv
#   VANILLA_BUDGET : ms per vanilla_path run (default 60000 = 1min)
#   ALNS_BUDGET    : ms per ALNS run (default 300000 = 5min)
#   ALNS_SEEDS     : comma-separated (default 1,2,7,42)
#   ALNS_OPS       : default basic

set -euo pipefail
cd "$(dirname "$0")/.."

THREAD_OFFSETS="${THREAD_OFFSETS:-0 8 16 24 32}"
PATH_MODE="${PATH_MODE:-border-first-mrv}"
VANILLA_BUDGET="${VANILLA_BUDGET:-60000}"
ALNS_BUDGET="${ALNS_BUDGET:-300000}"
ALNS_SEEDS="${ALNS_SEEDS:-1 2 7 42}"
ALNS_OPS="${ALNS_OPS:-basic}"
TS="$(date +%Y%m%dT%H%M%S)"
OUT_DIR="${OUT_DIR:-output/vol-120/vanilla_path_${TS}}"

mkdir -p "$OUT_DIR"
echo "[vol-120] OUT_DIR=$OUT_DIR"
echo "[vol-120] THREAD_OFFSETS=$THREAD_OFFSETS"
echo "[vol-120] PATH_MODE=$PATH_MODE VANILLA_BUDGET=$VANILLA_BUDGET"
echo "[vol-120] ALNS_BUDGET=$ALNS_BUDGET SEEDS=$ALNS_SEEDS OPS=$ALNS_OPS"

# Phase 1: produce partials via vanilla_path at each thread-offset
for OFF in $THREAD_OFFSETS; do
    PARTIAL="$OUT_DIR/partial_off${OFF}.json"
    LOG="$OUT_DIR/vanilla_off${OFF}.log"
    echo "[vol-120] vanilla_path offset=$OFF → $PARTIAL"
    ./target/release/vanilla_path \
        --budget-ms "$VANILLA_BUDGET" \
        --path-mode "$PATH_MODE" \
        --threads 1 \
        --thread-id-offset "$OFF" \
        --pin-hints \
        --save-best "$PARTIAL" \
        >"$LOG" 2>&1
    grep "matched_total\|best-partial" "$LOG" | tail -2
done

# Phase 2: ALNS on each partial × seeds
echo "[vol-120] Phase 2: ALNS"
JOBS=()
for OFF in $THREAD_OFFSETS; do
    PARTIAL="$OUT_DIR/partial_off${OFF}.json"
    if [[ -f "$PARTIAL" ]]; then
        for S in $ALNS_SEEDS; do
            JOBS+=("$OFF|$S|$PARTIAL")
        done
    fi
done
echo "[vol-120] ${#JOBS[@]} ALNS jobs queued"

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
        --alns-budget-ms "$ALNS_BUDGET" \
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
export OUT_DIR ALNS_BUDGET ALNS_OPS

printf '%s\n' "${JOBS[@]}" | xargs -I {} -P 8 bash -c 'run_alns "$@"' _ {}

echo ""
echo "[vol-120] Sweep complete. Top scores:"
./target/release/verify_board "$OUT_DIR"/*_alns.json 2>&1 \
  | grep "_alns.json" | grep -v "expected" \
  | awk '{split($3, a, "/"); print a[1], $1, $5}' | sort -nr | head -20
