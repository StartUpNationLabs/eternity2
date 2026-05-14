#!/usr/bin/env bash
# Vol-35 T1b — for each productive basin family discovered by the
# thread-id sweep, run an ALNS lottery to find the family's
# ALNS-recoverable ceiling.
#
# Input: output/vol-35/sweep/offset_NNNN/*.json (snapshots per offset)
# Pick the DEEPEST snapshot per family as the representative.
# Run SEEDS_PER ALNS seeds × BUDGET each.
#
# Usage: ml/sweep_family_lottery.sh [SEEDS_PER] [BUDGET_MS]

set -euo pipefail
cd "$(dirname "$0")/.."

SEEDS_PER="${1:-2}"
BUDGET_MS="${2:-300000}"  # 5 min default
ALNS_BIN="${ALNS_BIN:-target/release/alns_only}"
SWEEP_ROOT="output/vol-35/sweep"
OUT_DIR="output/vol-35/family_lottery"
SUMMARY="$OUT_DIR/summary.jsonl"

mkdir -p "$OUT_DIR/logs"
: > "$SUMMARY"

# Build alns_only if missing
if [ ! -x "$ALNS_BIN" ]; then
    echo "[build] $ALNS_BIN missing"
    source $HOME/.cargo/env
    cargo build --release --bin alns_only
fi

# For each offset dir, pick the deepest snapshot (by filename pattern _dNNN)
# as the family representative.
PICKED=()
for d in "$SWEEP_ROOT"/offset_*; do
    [ -d "$d" ] || continue
    offset=$(basename "$d" | sed 's/offset_//')
    # For each productive thread within this offset, pick its deepest snapshot
    for tid in $(ls "$d"/*.json 2>/dev/null | awk -F/ '{print $NF}' | sed -E 's/^t([0-9]+)_.*/\1/' | sort -u); do
        # Find the deepest snapshot for this tid
        deepest=$(ls "$d"/t${tid}_s*_d*.json 2>/dev/null | sort -t_ -k3 -nr | head -1)
        if [ -n "$deepest" ]; then
            depth=$(basename "$deepest" | sed -E 's/.*_d([0-9]+)\.json$/\1/')
            # tid already contains the full global thread_id (e.g. "103",
            # "165") because vanilla_fast names files with the full id.
            global_tid=$((10#$tid))
            PICKED+=("$global_tid:$depth:$deepest")
        fi
    done
done

echo "[lottery] $(echo "${PICKED[@]}" | tr ' ' '\n' | wc -l | tr -d ' ') families to test"

# Build a flat (partial, seed) run list
RUN_FILE="$OUT_DIR/runs.txt"
: > "$RUN_FILE"
for entry in "${PICKED[@]}"; do
    family=$(echo "$entry" | cut -d: -f1)
    depth=$(echo "$entry" | cut -d: -f2)
    partial=$(echo "$entry" | cut -d: -f3)
    for s in $(seq 1 "$SEEDS_PER"); do
        echo "$family:$depth:$partial $s" >> "$RUN_FILE"
    done
done
N_RUNS=$(wc -l < "$RUN_FILE")
echo "[lottery] $N_RUNS total runs"

run_one() {
    local entry="$1"
    local seed="$2"
    local family=$(echo "$entry" | cut -d: -f1)
    local depth=$(echo "$entry" | cut -d: -f2)
    local partial=$(echo "$entry" | cut -d: -f3)
    local log="$OUT_DIR/logs/family${family}_d${depth}_seed${seed}.log"
    "$ALNS_BIN" --cp-board "$partial" --alns-budget-ms "$BUDGET_MS" \
        --seed "$seed" --ops winning5 --repair-kind sa > "$log" 2>&1 || true
    # Verify via rescore on the saved board
    local saved
    saved=$(grep -h 'saved: ' "$log" | awk '{print $2}' | tail -1)
    local rescore=""
    if [ -n "$saved" ] && [ -f "$saved" ]; then
        rescore=$(./target/release/rescore_board "$saved" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
    fi
    local logged
    logged=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | cut -d= -f2 | cut -d/ -f1)
    echo "{\"family\":$family,\"depth\":$depth,\"seed\":$seed,\"logged\":${logged:-0},\"rescore\":${rescore:-0},\"saved\":\"${saved:-}\"}" >> "$SUMMARY"
    echo "[lottery] family=$family d=$depth seed=$seed → logged=$logged rescore=$rescore"
}
export -f run_one
export ALNS_BIN BUDGET_MS OUT_DIR SUMMARY

cat "$RUN_FILE" | xargs -n2 -P8 bash -c 'run_one "$0" "$1"'

echo ""
echo "=== TOP-15 verified results ==="
jq -s 'sort_by(-.rescore)[:15] | .[] | "\(.rescore)  family=\(.family) d=\(.depth) seed=\(.seed) (logged=\(.logged))"' -r "$SUMMARY"

HIGH=$(jq -s 'max_by(.rescore // 0) | .rescore' "$SUMMARY")
echo ""
echo "[lottery] highest VERIFIED score: $HIGH"
if [ "$HIGH" -ge 458 ] 2>/dev/null; then
    echo "[lottery] *** TIED or BROKE 458 record! ***"
fi
