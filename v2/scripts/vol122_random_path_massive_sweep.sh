#!/usr/bin/env bash
# Vol-122 T1 — massive random-path basin discovery.
#
# Uses vol-121 T2 invention (vanilla_path --path-mode border-first-random
# --path-seed N). Each path-seed produces a structurally distinct CSP
# tree → different basin reachable.
#
# Pipeline per path-seed:
#   1. vanilla_path border-first-random 5min × 8 threads (~85M pp/s × 8 = 680M pp/s)
#   2. ALNS basic 5min on resulting partial
#
# Sweep params (env-overridable):
#   PATH_SEEDS    : space-separated list (default: 1 2 3 5 7 11 13 17 19 23 29 31 37 41 43 47)
#   VANILLA_BUDGET_MS : default 300000 (5min)
#   ALNS_BUDGET_MS    : default 300000 (5min)
#   ALNS_SEEDS    : per partial; default 1 42
#   ALNS_OPS      : default basic

set +e
cd "$(dirname "$0")/.."

PATH_SEEDS="${PATH_SEEDS:-1 2 3 5 7 11 13 17 19 23 29 31 37 41 43 47}"
VANILLA_BUDGET_MS="${VANILLA_BUDGET_MS:-300000}"
VANILLA_THREADS="${VANILLA_THREADS:-8}"
ALNS_BUDGET_MS="${ALNS_BUDGET_MS:-300000}"
ALNS_SEEDS="${ALNS_SEEDS:-1 42}"
ALNS_OPS="${ALNS_OPS:-basic}"
TS="$(date +%Y%m%dT%H%M%S)"
OUT_DIR="${OUT_DIR:-output/vol-122/random_path_massive_${TS}}"

mkdir -p "$OUT_DIR"
echo "[vol-122 T1] OUT_DIR=$OUT_DIR"
echo "[vol-122 T1] PATH_SEEDS=$PATH_SEEDS"
echo "[vol-122 T1] VANILLA_BUDGET=${VANILLA_BUDGET_MS}ms × $VANILLA_THREADS threads"
echo "[vol-122 T1] ALNS_BUDGET=${ALNS_BUDGET_MS}ms × seeds=$ALNS_SEEDS, ops=$ALNS_OPS"

# Phase 1: sequential vanilla_path with each --path-seed (each uses all cores).
for PSEED in $PATH_SEEDS; do
    PARTIAL="$OUT_DIR/partial_pseed${PSEED}.json"
    LOG="$OUT_DIR/vanilla_pseed${PSEED}.log"
    echo "[vol-122 T1] vanilla_path border-first-random --path-seed=$PSEED → $PARTIAL"
    ./target/release/vanilla_path \
        --path-mode border-first-random \
        --path-seed "$PSEED" \
        --budget-ms "$VANILLA_BUDGET_MS" \
        --threads "$VANILLA_THREADS" \
        --save-best "$PARTIAL" \
        >"$LOG" 2>&1
    grep -E "(best-partial|saved|max_depth)" "$LOG" | tail -2
done

echo ""
echo "[vol-122 T1] Phase 2: ALNS basic ${ALNS_BUDGET_MS}ms × seeds=$ALNS_SEEDS per partial"

JOBS=()
for PSEED in $PATH_SEEDS; do
    PARTIAL="$OUT_DIR/partial_pseed${PSEED}.json"
    if [[ -f "$PARTIAL" ]]; then
        for ASEED in $ALNS_SEEDS; do
            JOBS+=("$PSEED|$ASEED|$PARTIAL")
        done
    fi
done
echo "[vol-122 T1] ${#JOBS[@]} ALNS jobs"

run_alns() {
    local spec="$1"
    local pseed="${spec%%|*}"
    local rest="${spec#*|}"
    local aseed="${rest%%|*}"
    local partial="${rest#*|}"
    local log="$OUT_DIR/alns_pseed${pseed}_as${aseed}.log"
    local label="pseed${pseed}_as${aseed}"
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
echo "[vol-122 T1] Sweep complete. Top scores:"
./target/release/verify_board "$OUT_DIR"/*_alns.json 2>&1 \
  | grep "_alns.json" | grep -v "expected" \
  | awk '{split($3, a, "/"); print a[1], $1, $5}' | sort -nr | head -20
