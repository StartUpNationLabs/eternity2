#!/usr/bin/env bash
# Vol-122 T2 — long bf_bw_schedule_hinted run (strict-canonical pipeline).
#
# This is the ONBOARDING §7 record-track pipeline. bf_bw_schedule_hinted
# runs the full Blackwood algorithm (schedule + break-index) at 84M nps
# WITH 5/5 hint pinning. Then ALNS basic from the partial.
#
# Sweep over many seed-offsets to explore the schedule space.

set +e
cd "$(dirname "$0")/.."

SEED_OFFSETS="${SEED_OFFSETS:-0 50 100 150 200 250 300 350 400 450 500 550 600 650 700 750}"
BF_BUDGET_MS="${BF_BUDGET_MS:-300000}"  # 5min per offset
BF_THREADS="${BF_THREADS:-8}"
SCHEDULE="${SCHEDULE:-v17a}"
ALNS_BUDGET_MS="${ALNS_BUDGET_MS:-300000}"
ALNS_SEEDS="${ALNS_SEEDS:-1 42}"
ALNS_OPS="${ALNS_OPS:-basic}"
TS="$(date +%Y%m%dT%H%M%S)"
OUT_DIR="${OUT_DIR:-output/vol-122/bf_schedule_long_${TS}}"

mkdir -p "$OUT_DIR"
echo "[vol-122 T2] OUT_DIR=$OUT_DIR"
echo "[vol-122 T2] SEED_OFFSETS=$SEED_OFFSETS"
echo "[vol-122 T2] BF: $SCHEDULE × ${BF_BUDGET_MS}ms × $BF_THREADS threads"
echo "[vol-122 T2] ALNS: ${ALNS_BUDGET_MS}ms × seeds=$ALNS_SEEDS, ops=$ALNS_OPS"

# Phase 1: sequential bf_bw_schedule_hinted
for OFF in $SEED_OFFSETS; do
    PARTIAL="$OUT_DIR/partial_off${OFF}.json"
    LOG="$OUT_DIR/bf_off${OFF}.log"
    echo "[vol-122 T2] bf_bw_schedule_hinted off=$OFF → $PARTIAL"
    ./target/release/bf_bw_schedule_hinted \
        --schedule "$SCHEDULE" \
        --seed-offset "$OFF" \
        --budget-ms "$BF_BUDGET_MS" \
        --threads "$BF_THREADS" \
        --dump-partial "$PARTIAL" \
        >"$LOG" 2>&1
    tail -5 "$LOG" | head -3
done

echo ""
echo "[vol-122 T2] Phase 2: ALNS"
JOBS=()
for OFF in $SEED_OFFSETS; do
    PARTIAL="$OUT_DIR/partial_off${OFF}.json"
    if [[ -f "$PARTIAL" ]]; then
        for ASEED in $ALNS_SEEDS; do
            JOBS+=("$OFF|$ASEED|$PARTIAL")
        done
    fi
done
echo "[vol-122 T2] ${#JOBS[@]} ALNS jobs"

run_alns() {
    local spec="$1"
    local off="${spec%%|*}"
    local rest="${spec#*|}"
    local aseed="${rest%%|*}"
    local partial="${rest#*|}"
    local log="$OUT_DIR/alns_off${off}_s${aseed}.log"
    local label="off${off}_s${aseed}"
    local out_json="$OUT_DIR/${label}_alns.json"
    if ./target/release/alns_only \
        --cp-board "$partial" \
        --alns-budget-ms "$ALNS_BUDGET_MS" \
        --seed "$aseed" \
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
echo "[vol-122 T2] Top scores:"
./target/release/verify_board "$OUT_DIR"/*_alns.json 2>&1 \
  | grep "_alns.json" | grep -v "expected" \
  | awk '{split($3, a, "/"); print a[1], $1, $5}' | sort -nr | head -20
