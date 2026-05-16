#!/usr/bin/env bash
# Vol-121 T1b — vanilla_path border-first WITHOUT --pin-hints.
#
# T1a discovery: --pin-hints + border-first has CSP depth wall at 86
# (30min × 8t = 938G placements still depth 86). Cross-machine SOTA
# 459 record has only 4/5 hints, so SOTA pipeline did NOT use --pin-hints.
#
# Drop the flag, otherwise same setup.

set +e  # tolerate ILLEGAL verify exit
cd "$(dirname "$0")/.."

THREAD_OFFSET_A="${THREAD_OFFSET_A:-0}"
THREAD_OFFSET_B="${THREAD_OFFSET_B:-8}"
VANILLA_BUDGET_MS="${VANILLA_BUDGET_MS:-1800000}"
VANILLA_THREADS="${VANILLA_THREADS:-8}"
ALNS_BUDGET_MS="${ALNS_BUDGET_MS:-1800000}"
ALNS_SEEDS="${ALNS_SEEDS:-1 42}"
ALNS_OPS="${ALNS_OPS:-basic}"
TS="$(date +%Y%m%dT%H%M%S)"
OUT_DIR="${OUT_DIR:-output/vol-121/nopin_${TS}}"

mkdir -p "$OUT_DIR"
echo "[vol-121 T1b] OUT_DIR=$OUT_DIR"
echo "[vol-121 T1b] NO --pin-hints; budgets ${VANILLA_BUDGET_MS}ms × $VANILLA_THREADS threads × 2 offsets"
echo "[vol-121 T1b] ALNS budget: ${ALNS_BUDGET_MS}ms × seeds=$ALNS_SEEDS, ops=$ALNS_OPS"

for OFF in $THREAD_OFFSET_A $THREAD_OFFSET_B; do
    PARTIAL="$OUT_DIR/partial_off${OFF}.json"
    LOG="$OUT_DIR/vanilla_off${OFF}.log"
    echo "[vol-121 T1b] vanilla_path offset=$OFF (NO pin-hints) → $PARTIAL"
    ./target/release/vanilla_path \
        --budget-ms "$VANILLA_BUDGET_MS" \
        --path-mode border-first \
        --threads "$VANILLA_THREADS" \
        --thread-id-offset "$OFF" \
        --save-best "$PARTIAL" \
        >"$LOG" 2>&1
    grep -E "(matched_total|best-partial|saved|max_depth)" "$LOG" | tail -3
    ./target/release/verify_board "$PARTIAL" 2>&1 | head -3 || true
done

echo ""
echo "[vol-121 T1b] Phase 2: ALNS"

JOBS=()
for OFF in $THREAD_OFFSET_A $THREAD_OFFSET_B; do
    PARTIAL="$OUT_DIR/partial_off${OFF}.json"
    if [[ -f "$PARTIAL" ]]; then
        for S in $ALNS_SEEDS; do
            JOBS+=("$OFF|$S|$PARTIAL")
        done
    fi
done
echo "[vol-121 T1b] ${#JOBS[@]} ALNS jobs"

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

printf '%s\n' "${JOBS[@]}" | xargs -I {} -P 4 bash -c 'run_alns "$@"' _ {}

echo ""
echo "[vol-121 T1b] Sweep complete. Final ranking:"
./target/release/verify_board "$OUT_DIR"/*_alns.json 2>&1 \
  | grep "_alns.json" | grep -v "expected" \
  | awk '{split($3, a, "/"); print a[1], $1, $5}' | sort -nr | head -20
