#!/usr/bin/env bash
# Vol-119 T1 v2 — basin corpus enlargement sweep with WINNING5 5-min ALNS.
#
# Aligns with vol-60's actual winning recipe:
#   p06 + vanilla_fast --pin-hints + ALNS winning5 5min seed=2 → 459
#
# Sweep over all 24 corner partials with the wider seed set + winning5
# ops + 5-min budget. Then we have the right operator + enough wall.

set -euo pipefail
cd "$(dirname "$0")/.."

PARTIALS="${PARTIALS:-p04 p05 p06 p07 p14 p15 p18 p20}"
SEEDS="${SEEDS:-2 7 42 100}"
BUDGET_MS="${BUDGET_MS:-300000}"  # 5 minutes — matches vol-60 winning recipe
OPS="${OPS:-winning5}"
THREADS="${THREADS:-8}"
TS="$(date +%Y%m%dT%H%M%S)"
OUT_DIR="${OUT_DIR:-output/vol-119/corpus_v2_${TS}}"

mkdir -p "$OUT_DIR"
echo "[vol-119 T1 v2] OUT_DIR=$OUT_DIR"
echo "[vol-119 T1 v2] PARTIALS=$PARTIALS"
echo "[vol-119 T1 v2] SEEDS=$SEEDS"
echo "[vol-119 T1 v2] BUDGET_MS=$BUDGET_MS OPS=$OPS THREADS=$THREADS"

JOBS=()
for P in $PARTIALS; do
    PARTIAL="output/vol-60/corner_sweep_v2_20260515T162511/${P}_best.json"
    if [[ ! -f "$PARTIAL" ]]; then
        echo "MISSING: $PARTIAL — skipping"
        continue
    fi
    for S in $SEEDS; do
        JOBS+=("$P|$S|$PARTIAL")
    done
done

echo "[vol-119 T1 v2] ${#JOBS[@]} jobs queued"

run_job() {
    local spec="$1"
    local p="${spec%%|*}"
    local rest="${spec#*|}"
    local s="${rest%%|*}"
    local partial="${rest#*|}"
    local log="$OUT_DIR/${p}_s${s}.log"
    local label="${p}_s${s}"
    local out_json="$OUT_DIR/${label}_alns.json"

    if ./target/release/alns_only \
        --cp-board "$partial" \
        --alns-budget-ms "$BUDGET_MS" \
        --seed "$s" \
        --ops "$OPS" \
        >"$log" 2>&1; then
        local saved_path
        saved_path=$(grep -E "^saved:" "$log" | tail -1 | awk '{print $2}')
        if [[ -n "$saved_path" && -f "$saved_path" ]]; then
            cp "$saved_path" "$out_json"
        fi
        echo "[ok] $label" >> "$OUT_DIR/_summary.log"
    else
        echo "[FAIL] $label" >> "$OUT_DIR/_summary.log"
    fi
}
export -f run_job
export OUT_DIR BUDGET_MS OPS

printf '%s\n' "${JOBS[@]}" | xargs -I {} -P "$THREADS" bash -c 'run_job "$@"' _ {}

echo ""
echo "[vol-119 T1 v2] Sweep complete. Output dir: $OUT_DIR"
echo "[vol-119 T1 v2] Top-score boards:"
./target/release/verify_board "$OUT_DIR"/*_alns.json 2>&1 \
  | grep "_alns.json" | grep -v "expected" \
  | awk '{split($3, a, "/"); print a[1], $1, $5}' | sort -nr | head -20
