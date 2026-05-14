#!/usr/bin/env bash
# Vol-35/36 — deep lottery from the vol-32 458-source partial.
#
# The partial output/vol-32/vanilla_fast_5min_best.json has 210 placed
# cells and produced the 458 record via ALNS. This is the basin most
# proximate to a 459+ break.
#
# Run 12 seeds × 4 ops × 5min ALNS = 48 runs on this partial. If 458
# is reproducible from this partial across multiple seeds, a non-trivial
# fraction of seeds may also find 459.
#
# Usage: ml/deep_458_basin_lottery.sh [out_dir] [budget_ms]

set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="${1:-output/vol-35/deep_458_basin}"
BUDGET_MS="${2:-300000}"
PARTIAL="output/vol-32/vanilla_fast_5min_best.json"
ALNS_BIN="${ALNS_BIN:-target/release/alns_only}"
SUMMARY="$OUT_DIR/summary.jsonl"

mkdir -p "$OUT_DIR/logs"
: > "$SUMMARY"

[ -f "$PARTIAL" ] || { echo "partial not found: $PARTIAL"; exit 1; }

SEEDS="${SEEDS:-1 2 3 4 5 6 7 8 9 10 11 12}"
OPS="${OPS:-winning5 mega_mix full diverse}"

RUN_FILE="$OUT_DIR/runs.txt"
: > "$RUN_FILE"
for ops in $OPS; do
    for s in $SEEDS; do
        echo "$ops $s" >> "$RUN_FILE"
    done
done
N=$(wc -l < "$RUN_FILE")
echo "[deep458] $N runs for $PARTIAL"

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
    echo "[deep458] ops=$ops seed=$seed -> logged=$logged rescore=$rescore"
}
export -f run_one
export PARTIAL ALNS_BIN BUDGET_MS OUT_DIR SUMMARY

cat "$RUN_FILE" | xargs -n2 -P8 bash -c 'run_one "$0" "$1"'

echo ""
echo "=== Final results sorted by rescore ==="
jq -s 'sort_by(-.rescore)[:20] | .[] | "  rescore=\(.rescore) ops=\(.ops) seed=\(.seed)"' -r "$SUMMARY"

HIGH=$(jq -s 'max_by(.rescore) | .rescore' "$SUMMARY")
echo ""
echo "[deep458] HIGHEST verified: $HIGH"
if [ "$HIGH" -ge 459 ] 2>/dev/null; then
    echo "[deep458] *** NEW RECORD: $HIGH > 458 ***"
elif [ "$HIGH" -ge 458 ] 2>/dev/null; then
    echo "[deep458] *** TIED 458 RECORD ***"
fi
