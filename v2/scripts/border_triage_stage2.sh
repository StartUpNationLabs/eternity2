#!/usr/bin/env bash
# Stage 2: longer PT on a curated list of borders.
# Reads top-K border indices from stage 1 results and runs 300s PT × 4 replicas each.
# Usage: scripts/border_triage_stage2.sh <TOP_K> <PT_SECONDS>
set -euo pipefail

TOP_K=${1:-4}
PT_SECONDS=${2:-300}

RESULTS=output/v7_triage_results
SEED_DIR=output/v7_synth_seeds
STAGE2_DIR=output/v7_triage_stage2
mkdir -p "$STAGE2_DIR"

# Parse stage 1 results: extract (idx, score) pairs sorted by score desc
echo "=== STAGE 2: top-$TOP_K borders × ${PT_SECONDS}s ==="
echo "started at $(date)"
echo

TOP_LIST=()
for log in "$RESULTS"/border_*.log; do
    idx=$(basename "$log" .log | sed 's/border_0*//')
    best=$(grep -oE "best=[0-9]+/480" "$log" 2>/dev/null | tail -1 | grep -oE "[0-9]+" | head -1)
    echo "$idx $best"
done | sort -k2 -n -r | head -n "$TOP_K" > /tmp/stage2_top.txt

echo "top-$TOP_K candidates:"
cat /tmp/stage2_top.txt
echo

function run_stage2_one() {
    local idx=$1 best=$2
    echo "[stage2] border $idx (stage1=$best): running ${PT_SECONDS}s PT × 4 replicas..."
    local out_log="$STAGE2_DIR/border_$(printf '%03d' $idx).log"
    ./target/release/pt_e2 \
        --start-from "$SEED_DIR/border_top$((idx+1)).json" \
        --pin-perimeter \
        --pt-seconds "$PT_SECONDS" \
        --skip-sa-compare \
        --seed "$((200000 + idx))" \
        --n-replicas 4 \
        > "$out_log" 2>&1
    local new_best=$(grep -oE "best=[0-9]+/480" "$out_log" | tail -1 | grep -oE "[0-9]+" | head -1)
    echo "[stage2] border $idx: ${best} -> ${new_best}/480"
}
export -f run_stage2_one
export PT_SECONDS STAGE2_DIR SEED_DIR
# Run 2 borders in parallel (4 replicas × 2 ≈ 6 effective cores; we have 8)
awk '{print $1" "$2}' /tmp/stage2_top.txt | xargs -n 2 -P 2 bash -c 'run_stage2_one "$@"' _

echo
echo "=== STAGE 2 SUMMARY ==="
echo
for log in "$STAGE2_DIR"/border_*.log; do
    idx=$(basename "$log" .log | sed 's/border_0*//')
    best=$(grep -oE "best=[0-9]+/480" "$log" 2>/dev/null | tail -1 | grep -oE "[0-9]+" | head -1)
    echo "border $idx: ${best}/480"
done | sort -k3 -n -r
echo
echo "finished at $(date)"
