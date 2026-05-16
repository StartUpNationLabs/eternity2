#!/usr/bin/env bash
# Vol-121 T2 — random-path basin diversity sweep.
#
# For each --path-seed in PATH_SEEDS, run vanilla_path border-first-random for
# VANILLA_BUDGET_MS (8 threads), then ALNS basic for ALNS_BUDGET_MS at one
# fixed ALNS seed.
#
# Goal: measure basin diversity from random path-order. If different seeds
# produce structurally distinct ≥455 basins, randomized path-order is a
# real lever for the vol-119/120 corpus enlargement problem.
#
# Per CLAUDE.md rule #4: variance is mandatory — sweep ≥8 seeds.

set +e
cd "$(dirname "$0")/.."

PATH_MODE="${PATH_MODE:-border-first-random}"
PATH_SEEDS="${PATH_SEEDS:-1 2 3 7 13 42 100 200}"
VANILLA_BUDGET_MS="${VANILLA_BUDGET_MS:-300000}"   # 5min per seed
VANILLA_THREADS="${VANILLA_THREADS:-8}"
ALNS_BUDGET_MS="${ALNS_BUDGET_MS:-300000}"         # 5min ALNS
ALNS_SEED="${ALNS_SEED:-42}"
ALNS_OPS="${ALNS_OPS:-basic}"
TS="$(date +%Y%m%dT%H%M%S)"
OUT_DIR="${OUT_DIR:-output/vol-121/random_path_${TS}}"

mkdir -p "$OUT_DIR"
echo "[vol-121 T2] OUT_DIR=$OUT_DIR"
echo "[vol-121 T2] PATH_MODE=$PATH_MODE  PATH_SEEDS=$PATH_SEEDS"
echo "[vol-121 T2] VANILLA_BUDGET=${VANILLA_BUDGET_MS}ms × $VANILLA_THREADS threads"
echo "[vol-121 T2] ALNS_BUDGET=${ALNS_BUDGET_MS}ms  ALNS_SEED=$ALNS_SEED  OPS=$ALNS_OPS"

# Phase 1: sequential vanilla_path with each --path-seed (each uses all cores).
for PSEED in $PATH_SEEDS; do
    PARTIAL="$OUT_DIR/partial_pseed${PSEED}.json"
    LOG="$OUT_DIR/vanilla_pseed${PSEED}.log"
    echo "[vol-121 T2] vanilla_path --path-seed=$PSEED → $PARTIAL"
    ./target/release/vanilla_path \
        --path-mode "$PATH_MODE" \
        --path-seed "$PSEED" \
        --budget-ms "$VANILLA_BUDGET_MS" \
        --threads "$VANILLA_THREADS" \
        --save-best "$PARTIAL" \
        >"$LOG" 2>&1
    grep -E "(best-partial|saved|max_depth)" "$LOG" | tail -2
done

echo ""
echo "[vol-121 T2] Phase 2: ALNS basic ${ALNS_BUDGET_MS}ms on each partial"

JOBS=()
for PSEED in $PATH_SEEDS; do
    PARTIAL="$OUT_DIR/partial_pseed${PSEED}.json"
    if [[ -f "$PARTIAL" ]]; then
        JOBS+=("$PSEED|$ALNS_SEED|$PARTIAL")
    fi
done
echo "[vol-121 T2] ${#JOBS[@]} ALNS jobs"

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
echo "[vol-121 T2] Sweep complete. Final ranking:"
./target/release/verify_board "$OUT_DIR"/*_alns.json 2>&1 \
  | grep "_alns.json" | grep -v "expected" \
  | awk '{split($3, a, "/"); print a[1], $1, $5}' | sort -nr | head -20

echo ""
echo "[vol-121 T2] Distinct basins (Hamming ≥ 30):"
python3 scripts/vol119_dedup_basin_corpus.py "$OUT_DIR"/*_alns.json --hamming-K 30 2>/dev/null | head -30 || true
