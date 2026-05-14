#!/usr/bin/env bash
# Vol-35 T1a — sweep thread_id offsets to discover new productive basin families.
#
# Each offset run: 8 threads × 8 minutes vanilla_fast with on-visit snapshots.
# Aggregates all snapshots into output/vol-35/sweep_all/, then post-processes
# to identify distinct thread_ids (= distinct basin families).
#
# Usage: ml/sweep_thread_ids.sh [OFFSETS] [BUDGET_MS]
#   OFFSETS: space-separated list of offsets (default "0 100 200 300 400 500 600 700 800 900")
#   BUDGET_MS: per-offset budget (default 480000 = 8 min)

set -euo pipefail
cd "$(dirname "$0")/.."

OFFSETS_DEFAULT="0 100 200 300 400 500 600 700 800 900"
OFFSETS="${OFFSETS:-$OFFSETS_DEFAULT}"
BUDGET_MS="${BUDGET_MS:-480000}"
ROOT="output/vol-35/sweep"

mkdir -p "$ROOT"

for off in $OFFSETS; do
    dir="$ROOT/offset_$(printf '%04d' "$off")"
    if [ -d "$dir" ] && [ "$(ls "$dir"/*.json 2>/dev/null | wc -l | tr -d ' ')" -gt 0 ]; then
        echo "[sweep] offset=$off: already has $(ls $dir/*.json | wc -l) snapshots, skipping"
        continue
    fi
    mkdir -p "$dir"
    echo "[sweep] offset=$off: starting at $(date +%H:%M:%S)"
    ./target/release/vanilla_fast \
        --threads 8 \
        --pin-hints \
        --budget-ms "$BUDGET_MS" \
        --snapshot-dir "$dir" \
        --snapshot-interval-ms 60000 \
        --snapshot-min-depth 200 \
        --snapshot-on-visit \
        --thread-id-offset "$off" \
        > "$dir/probe.log" 2>&1 || true
    nsnap=$(ls "$dir"/*.json 2>/dev/null | wc -l | tr -d ' ')
    tids=$(ls "$dir"/*.json 2>/dev/null | awk -F'/' '{print $NF}' | cut -c2-3 | sort -u | tr '\n' ' ')
    echo "[sweep] offset=$off done: $nsnap snapshots from threads ($tids)"
done

# Aggregate report
echo ""
echo "=== Sweep summary ==="
for off in $OFFSETS; do
    dir="$ROOT/offset_$(printf '%04d' "$off")"
    [ -d "$dir" ] || continue
    nsnap=$(ls "$dir"/*.json 2>/dev/null | wc -l | tr -d ' ')
    tids=$(ls "$dir"/*.json 2>/dev/null | awk -F'/' '{print $NF}' | cut -c2-3 | sort -u | tr '\n' ',')
    # Resolve thread_id (cut just gives within-offset index 00-07; add offset to get global tid)
    echo "  offset=$off: nsnap=$nsnap thread_idx_set={$tids} (add $off for global thread_id)"
done

echo ""
echo "All snapshots collected at $ROOT/. Use ml/cluster_basins.py to identify families."
