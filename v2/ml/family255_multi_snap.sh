#!/usr/bin/env bash
# Vol-35 — ALNS 5 different family-255 depth-200 snapshots × 4 seeds.
# Tests whether different snapshots within the same family produce
# different score-recoverable ceilings.

set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="output/vol-35/family255_multi_snap"
mkdir -p "$OUT_DIR/logs"
SUMMARY="$OUT_DIR/summary.jsonl"
: > "$SUMMARY"

ALNS_BIN="${ALNS_BIN:-target/release/alns_only}"
BUDGET_MS="${BUDGET_MS:-300000}"

run_one() {
    local partial="$1"
    local seed="$2"
    local snap_name=$(basename "$partial" .json)
    local log="$OUT_DIR/logs/${snap_name}_seed${seed}.log"
    "$ALNS_BIN" --cp-board "$partial" --alns-budget-ms "$BUDGET_MS" \
        --seed "$seed" --ops winning5 --repair-kind sa > "$log" 2>&1 || true
    local logged=$(grep -oE "matched=[0-9]+/480" "$log" | tail -1 | cut -d= -f2 | cut -d/ -f1)
    logged=${logged:-0}
    local saved=$(grep saved: "$log" | tail -1 | awk '{print $2}')
    local rescore=0
    if [ -n "$saved" ] && [ -f "$saved" ]; then
        rescore=$(./target/release/rescore_board "$saved" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
    fi
    rescore=${rescore:-$logged}
    echo "{\"snap\":\"$snap_name\",\"seed\":$seed,\"logged\":$logged,\"rescore\":$rescore,\"saved\":\"$saved\"}" >> "$SUMMARY"
    echo "[multi] $snap_name seed=$seed logged=$logged rescore=$rescore"
}

export -f run_one
export ALNS_BIN BUDGET_MS OUT_DIR SUMMARY

RUN_FILE="$OUT_DIR/runs.txt"
: > "$RUN_FILE"
for snap in output/vol-35/sweep/offset_0250/t255_s000_d200.json \
            output/vol-35/sweep/offset_0250/t255_s001_d200.json \
            output/vol-35/sweep/offset_0250/t255_s002_d200.json \
            output/vol-35/sweep/offset_0250/t255_s003_d200.json \
            output/vol-35/sweep/offset_0250/t255_s004_d200.json; do
    for s in 1 2 3 4; do
        echo "$snap $s" >> "$RUN_FILE"
    done
done
N_RUNS=$(wc -l < "$RUN_FILE")
echo "[multi] $N_RUNS total runs"

cat "$RUN_FILE" | xargs -n2 -P8 bash -c 'run_one "$0" "$1"'

echo "[multi] DONE"
