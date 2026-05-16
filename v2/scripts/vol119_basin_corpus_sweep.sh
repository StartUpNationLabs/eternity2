#!/usr/bin/env bash
# Vol-119 T1 — basin corpus enlargement sweep.
#
# Runs ALNS basic at multiple seeds on each high-quality vol-60 corner
# partial (≥206 placed cells). Goal: build a corpus of ≥10 distinct
# 459+ basins for vol-119 T2 basin-mix MIP.
#
# Sweep params (env-overridable):
#   PARTIALS   : space-separated p-codes to sweep (default: top 8)
#   SEEDS      : space-separated seeds (default: 1 2 7 42 100 200 300 999)
#   BUDGET_MS  : per-job ALNS budget (default: 60000)
#   THREADS    : concurrent jobs (default: 8)
#   OUT_DIR    : output base dir (auto-timestamped if unset)

set -euo pipefail
cd "$(dirname "$0")/.."

PARTIALS="${PARTIALS:-p04 p05 p06 p07 p14 p15 p20 p21}"
SEEDS="${SEEDS:-1 2 7 42 100 200 300 999}"
BUDGET_MS="${BUDGET_MS:-60000}"
THREADS="${THREADS:-8}"
TS="$(date +%Y%m%dT%H%M%S)"
OUT_DIR="${OUT_DIR:-output/vol-119/corpus_sweep_${TS}}"

mkdir -p "$OUT_DIR"
echo "[vol-119 T1] OUT_DIR=$OUT_DIR"
echo "[vol-119 T1] PARTIALS=$PARTIALS"
echo "[vol-119 T1] SEEDS=$SEEDS"
echo "[vol-119 T1] BUDGET_MS=$BUDGET_MS THREADS=$THREADS"

# Generate the job list: partial × seed
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

echo "[vol-119 T1] ${#JOBS[@]} jobs queued"

# Run one job — find produced file from the log line "saved: <path>"
run_job() {
    local spec="$1"
    local p="${spec%%|*}"
    local rest="${spec#*|}"
    local s="${rest%%|*}"
    local partial="${rest#*|}"
    local log="$OUT_DIR/${p}_s${s}.log"
    local label="${p}_s${s}"
    local out_json="$OUT_DIR/${label}_alns.json"

    # macOS doesn't ship `timeout`; alns_only respects --alns-budget-ms internally
    if ./target/release/alns_only \
        --cp-board "$partial" \
        --alns-budget-ms "$BUDGET_MS" \
        --seed "$s" \
        --ops basic \
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
export OUT_DIR BUDGET_MS

# Drive parallelism via xargs -P
printf '%s\n' "${JOBS[@]}" | xargs -I {} -P "$THREADS" bash -c 'run_job "$@"' _ {}

echo ""
echo "[vol-119 T1] Sweep complete. Output dir: $OUT_DIR"
echo "[vol-119 T1] Verifying produced boards..."
./target/release/verify_board "$OUT_DIR"/*_alns.json 2>&1 | head -100
