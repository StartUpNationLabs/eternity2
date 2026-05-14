#!/usr/bin/env bash
# Vol-35 — deep lottery on a single basin family.
#
# Given a representative partial from a high-bound family,
# run multiple ALNS seeds × multiple ops presets to find the
# family's true ALNS-recoverable ceiling.
#
# Usage: ml/deep_family_lottery.sh <partial.json> [out_dir] [budget_ms]

set -euo pipefail
cd "$(dirname "$0")/.."

PARTIAL="${1:?usage: $0 <partial.json> [out_dir] [budget_ms]}"
OUT_DIR="${2:-output/vol-35/deep_family}"
BUDGET_MS="${3:-300000}"
ALNS_BIN="${ALNS_BIN:-target/release/alns_only}"
SUMMARY="$OUT_DIR/summary.jsonl"

mkdir -p "$OUT_DIR/logs"
: > "$SUMMARY"

[ -f "$PARTIAL" ] || { echo "partial not found: $PARTIAL"; exit 1; }

SEEDS="${SEEDS:-1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16}"
OPS="${OPS:-winning5 mega_mix full mega hingeonly}"

RUN_FILE="$OUT_DIR/runs.txt"
: > "$RUN_FILE"
for ops in $OPS; do
    for s in $SEEDS; do
        echo "$ops $s" >> "$RUN_FILE"
    done
done
N=$(wc -l < "$RUN_FILE")
echo "[deep] $N runs for $PARTIAL"

run_one() {
    local ops="$1"
    local seed="$2"
    local log="$OUT_DIR/logs/${ops}_seed${seed}.log"
    "$ALNS_BIN" --cp-board "$PARTIAL" --alns-budget-ms "$BUDGET_MS" \
        --seed "$seed" --ops "$ops" --repair-kind sa > "$log" 2>&1 || true
    local saved
    saved=$(grep -h 'saved: ' "$log" | awk '{print $2}' | tail -1)
    local rescore=""
    if [ -n "$saved" ] && [ -f "$saved" ]; then
        rescore=$(./target/release/rescore_board "$saved" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
    fi
    local logged
    logged=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | cut -d= -f2 | cut -d/ -f1)
    echo "{\"ops\":\"$ops\",\"seed\":$seed,\"logged\":${logged:-0},\"rescore\":${rescore:-0},\"saved\":\"${saved:-}\"}" >> "$SUMMARY"
    echo "[deep] ops=$ops seed=$seed -> logged=$logged rescore=$rescore"
}
export -f run_one
export PARTIAL ALNS_BIN BUDGET_MS OUT_DIR SUMMARY

cat "$RUN_FILE" | xargs -n2 -P8 bash -c 'run_one "$0" "$1"'

echo ""
echo "=== Final results sorted by rescore ==="
jq -s 'sort_by(-.rescore)[:20] | .[] | "  rescore=\(.rescore) ops=\(.ops) seed=\(.seed)"' -r "$SUMMARY"

HIGH=$(jq -s 'max_by(.rescore) | .rescore' "$SUMMARY")
echo ""
echo "[deep] HIGHEST verified: $HIGH"
if [ "$HIGH" -ge 458 ] 2>/dev/null; then
    echo "[deep] *** TIED/BROKE 458 RECORD! ***"
fi
