#!/usr/bin/env bash
# Vol-34 T3 — mass ALNS lottery from vanilla_fast snapshots.
#
# Usage: ml/run_t3_lottery.sh <snapshot-dir> <output-dir> [N_PARTIALS] [SEEDS_PER]
#   snapshot-dir:  e.g. output/vol-34/t1_probe
#   output-dir:    e.g. output/vol-34/t3_lottery
#   N_PARTIALS:    top-K partials by depth (default 100)
#   SEEDS_PER:     ALNS seeds per partial (default 4)
#
# Total runs = N_PARTIALS * SEEDS_PER, each 5 min, run in parallel
# batches of 8 (one per CPU core).

set -euo pipefail
cd "$(dirname "$0")/.."

SNAP_DIR="${1:-output/vol-34/t1_probe}"
OUT_DIR="${2:-output/vol-34/t3_lottery}"
N_PARTIALS="${3:-100}"
SEEDS_PER="${4:-4}"
ALNS_BUDGET_MS="${ALNS_BUDGET_MS:-300000}"
ALNS_BIN="${ALNS_BIN:-target/release/alns_only}"

mkdir -p "$OUT_DIR/logs"
SUMMARY="$OUT_DIR/summary.jsonl"
: > "$SUMMARY"

# Build alns_only release if not already.
if [ ! -x "$ALNS_BIN" ]; then
    echo "[build] $ALNS_BIN missing — building"
    source $HOME/.cargo/env
    cargo build --release --bin alns_only
fi

# Pick top-N partials by depth (extracted from filename: tNN_sNNN_dDDD.json)
mapfile -t TOP_PARTIALS < <(
    ls "$SNAP_DIR"/t*_s*_d*.json 2>/dev/null \
        | sed -E 's/.*_d([0-9]+)\.json$/\1\t&/' \
        | sort -k1 -nr -t$'\t' \
        | head -n "$N_PARTIALS" \
        | cut -f2
)
echo "[t3] found ${#TOP_PARTIALS[@]} partials, target N=$N_PARTIALS"
if [ "${#TOP_PARTIALS[@]}" -eq 0 ]; then
    echo "[t3] ERROR: no snapshots in $SNAP_DIR"
    exit 1
fi

# Sanity: report range.
HEAD_DEPTH=$(echo "${TOP_PARTIALS[0]}" | sed -E 's/.*_d([0-9]+)\.json$/\1/')
TAIL_DEPTH=$(echo "${TOP_PARTIALS[${#TOP_PARTIALS[@]}-1]}" | sed -E 's/.*_d([0-9]+)\.json$/\1/')
echo "[t3] depth range: $HEAD_DEPTH (top) → $TAIL_DEPTH (bottom)"

run_one() {
    local partial="$1"
    local seed="$2"
    local depth
    depth=$(basename "$partial" | sed -E 's/.*_d([0-9]+)\.json$/\1/')
    local stem
    stem=$(basename "$partial" .json)
    local log="$OUT_DIR/logs/${stem}_seed${seed}.log"
    "$ALNS_BIN" --cp-board "$partial" --alns-budget-ms "$ALNS_BUDGET_MS" \
        --seed "$seed" --ops winning5 --repair-kind sa \
        > "$log" 2>&1 || true
    local matched
    matched=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | cut -d= -f2 | cut -d/ -f1)
    matched="${matched:-0}"
    echo "{\"partial\":\"$partial\",\"seed\":$seed,\"depth\":$depth,\"matched\":$matched}" >> "$SUMMARY"
    echo "[t3]   $stem seed=$seed → $matched"
}

export -f run_one
export ALNS_BIN ALNS_BUDGET_MS OUT_DIR SUMMARY

# Build the run list (partial, seed) pairs.
RUN_FILE="$OUT_DIR/runs.txt"
: > "$RUN_FILE"
for p in "${TOP_PARTIALS[@]}"; do
    for s in $(seq 1 "$SEEDS_PER"); do
        echo "$p $s" >> "$RUN_FILE"
    done
done
N_RUNS=$(wc -l < "$RUN_FILE")
echo "[t3] $N_RUNS runs total ($(( N_RUNS * ALNS_BUDGET_MS / 1000 / 60 )) thread-minutes serial)"
echo "[t3] elapsed budget on 8 cores: ~$(( N_RUNS * ALNS_BUDGET_MS / 1000 / 60 / 8 )) min"

# Parallel execution: 8 cores.
cat "$RUN_FILE" | xargs -n2 -P8 bash -c 'run_one "$0" "$1"'

echo "[t3] done. Summary: $SUMMARY"
echo "[t3] sorted top scores:"
sort -t: -k4 -nr "$SUMMARY" | head -20

# Detect any score ≥ 459 → NEW RECORD
HIGH=$(jq -s 'max_by(.matched) | .matched' "$SUMMARY" 2>/dev/null || echo 0)
if [ "$HIGH" -ge 459 ] 2>/dev/null; then
    echo "[t3] 🎯 NEW RECORD: highest score = $HIGH (≥459)"
else
    echo "[t3] highest score = $HIGH (basin family caps at this level)"
fi
