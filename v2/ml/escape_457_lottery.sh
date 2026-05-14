#!/usr/bin/env bash
# Vol-35/vol-36 — try to ESCAPE a 457 lock via large-K ALNS destroys.
#
# Take each of the 5 distinct 457 cluster reps as the STARTING BOARD
# (not a partial — a fully-placed 457 board), run ALNS with winning5
# ops (K=80 ConflictDriven, K=4 WorstBand). Does any seed escape to 458+?
#
# This directly tests if our largest current destroy moves can break
# the 457 attractor.

set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="${1:-output/vol-35/escape_457}"
BUDGET_MS="${2:-180000}"
ALNS_BIN="${ALNS_BIN:-target/release/alns_only}"
SUMMARY="$OUT_DIR/summary.jsonl"

mkdir -p "$OUT_DIR/logs"
: > "$SUMMARY"

declare -a REPS=(
    "A:output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json"
    "B:output/vol-32/RECORD_TIE_457_blackwood_mrv_30min_seed4.json"
    "C:output/vol-34/t3_signal/REAL_RECORD_TIE_457_vol34_t1signal_seed1.json"
    "D:output/vol-34/t3_signal/RECORD_TIE_457_vol34_t3_t01_seed1.json"
    "E:output/vol-35/records/RECORD_TIE_457_vol35_family255_seed1.json"
)

SEEDS="${SEEDS:-1 2 3 4}"
OPS="${OPS:-winning5}"

RUN_FILE="$OUT_DIR/runs.txt"
: > "$RUN_FILE"
for entry in "${REPS[@]}"; do
    label="${entry%%:*}"
    path="${entry#*:}"
    for s in $SEEDS; do
        echo "$label $path $s" >> "$RUN_FILE"
    done
done
N=$(wc -l < "$RUN_FILE")
echo "[escape457] $N runs"

run_one() {
    local label="$1"
    local board="$2"
    local seed="$3"
    local log="$OUT_DIR/logs/${label}_seed${seed}.log"
    "$ALNS_BIN" --cp-board "$board" --alns-budget-ms "$BUDGET_MS" \
        --seed "$seed" --ops "$OPS" --repair-kind sa > "$log" 2>&1 || true
    local saved
    saved=$(grep -h 'saved: ' "$log" | awk '{print $2}' | tail -1)
    local rescore=""
    if [ -n "$saved" ] && [ -f "$saved" ]; then
        rescore=$(./target/release/rescore_board "$saved" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
    fi
    local logged
    logged=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | cut -d= -f2 | cut -d/ -f1)
    echo "{\"label\":\"$label\",\"seed\":$seed,\"logged\":${logged:-0},\"rescore\":${rescore:-0},\"saved\":\"${saved:-}\"}" >> "$SUMMARY"
    echo "[escape457] $label seed=$seed -> logged=$logged rescore=$rescore"
}
export -f run_one
export ALNS_BIN BUDGET_MS OPS OUT_DIR SUMMARY

cat "$RUN_FILE" | xargs -n3 -P8 bash -c 'run_one "$0" "$1" "$2"'

echo ""
echo "=== Final sorted by rescore ==="
jq -s 'sort_by(-.rescore) | .[] | "  label=\(.label) seed=\(.seed) rescore=\(.rescore)"' -r "$SUMMARY"

HIGH=$(jq -s 'max_by(.rescore) | .rescore' "$SUMMARY")
echo ""
echo "[escape457] HIGHEST: $HIGH"
if [ "$HIGH" -ge 458 ] 2>/dev/null; then
    echo "[escape457] *** TIED/BROKE 458 RECORD ***"
fi
